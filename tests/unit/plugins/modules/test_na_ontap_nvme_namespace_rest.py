# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_aggregate when using REST """

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_nvme_namespace \
    import NetAppONTAPNVMENamespace as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'nvme_namespace': (200, {
        "name": "/vol/test/disk1",
        "uuid": "81068ae6-4674-4d78-a8b7-dadb23f67edf",
        "svm": {
            "name": "ansibleSVM"
        },
        "enabled": True
    }, None)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'vserver': 'ansibleSVM',
    'ostype': 'linux',
    'path': '/vol/test/disk1',
    'size': 10,
    'size_unit': 'mb',
    'block_size': 4096
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "path", "vserver"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_get_namespace_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/namespaces', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_namespace_rest() is None


def test_get_namespace_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/namespaces', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching namespace info for vserver: ansibleSVM'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_namespace_rest, 'fail')['msg']


def test_create_namespace():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/namespaces', SRR['empty_records']),
        ('POST', 'storage/namespaces', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_create_namespace_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('POST', 'storage/namespaces', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.create_namespace_rest, 'fail')['msg']
    msg = 'Error creating namespace for vserver ansibleSVM: calling: storage/namespaces: got Expected error.'
    assert msg == error


def test_delete_namespace():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace']),
        ('DELETE', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_namespace_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('DELETE', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.namespace_uuid = '81068ae6-4674-4d78-a8b7-dadb23f67edf'
    error = expect_and_capture_ansible_exception(my_obj.delete_namespace_rest, 'fail')['msg']
    msg = 'Error deleting namespace for vserver ansibleSVM: calling: storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf: got Expected error.'
    assert msg == error
