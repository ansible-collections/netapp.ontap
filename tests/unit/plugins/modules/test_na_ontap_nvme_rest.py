# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_aggregate when using REST """

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_nvme \
    import NetAppONTAPNVMe as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'nvme_service': (200, {
        "svm": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "enabled": True
    }, None)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'vserver': 'svm1'
}


def test_get_nvme_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/services', SRR['empty_records'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    assert my_obj.get_nvme_rest() is None


def test_get_nvme_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/services', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching nvme info for vserver: svm1'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_nvme_rest, 'fail')['msg']


def test_create_nvme():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/services', SRR['empty_records']),
        ('POST', 'protocols/nvme/services', SRR['empty_good'])
    ])
    module_args = {'status_admin': True}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_nvme_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('POST', 'protocols/nvme/services', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['status_admin'] = True
    error = expect_and_capture_ansible_exception(my_obj.create_nvme_rest, 'fail')['msg']
    msg = 'Error creating nvme for vserver svm1: calling: protocols/nvme/services: got Expected error.'
    assert msg == error


def test_delete_nvme():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/services', SRR['nvme_service']),
        ('PATCH', 'protocols/nvme/services/02c9e252-41be-11e9-81d5-00a0986138f7', SRR['empty_good']),
        ('DELETE', 'protocols/nvme/services/02c9e252-41be-11e9-81d5-00a0986138f7', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_nvme_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('DELETE', 'protocols/nvme/services/02c9e252-41be-11e9-81d5-00a0986138f7', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.svm_uuid = '02c9e252-41be-11e9-81d5-00a0986138f7'
    error = expect_and_capture_ansible_exception(my_obj.delete_nvme_rest, 'fail')['msg']
    msg = 'Error deleting nvme for vserver svm1: calling: protocols/nvme/services/02c9e252-41be-11e9-81d5-00a0986138f7: got Expected error.'
    assert msg == error


def test_modify_nvme():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/services', SRR['nvme_service']),
        ('PATCH', 'protocols/nvme/services/02c9e252-41be-11e9-81d5-00a0986138f7', SRR['empty_good'])
    ])
    module_args = {'status_admin': False}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_nvme_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('PATCH', 'protocols/nvme/services/02c9e252-41be-11e9-81d5-00a0986138f7', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['status_admin'] = False
    my_obj.svm_uuid = '02c9e252-41be-11e9-81d5-00a0986138f7'
    error = expect_and_capture_ansible_exception(my_obj.modify_nvme_rest, 'fail', {'status': False})['msg']
    msg = 'Error modifying nvme for vserver: svm1'
    assert msg == error
