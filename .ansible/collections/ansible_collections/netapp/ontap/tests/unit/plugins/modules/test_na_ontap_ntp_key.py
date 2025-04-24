# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ntp_key \
    import NetAppOntapNTPKey as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'ntp_key': (200, {
        "records": [
            {
                "id": 1,
                "digest_type": "sha1",
                "value": "addf120b430021c36c232c99ef8d926aea2acd6b"
            }],
        "num_records": 1
    }, None),
    'svm_uuid': (200, {"records": [
        {
            'uuid': 'e3cb5c7f-cd20'
        }], "num_records": 1}, None)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always'
}


def test_get_ntp_key_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster/ntp/keys', SRR['empty_records'])
    ])
    module_args = {'id': 1, 'digest_type': 'sha1', 'value': 'test'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_ntp_key() is None


def test_get_ntp_key_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster/ntp/keys', SRR['generic_error'])
    ])
    module_args = {'id': 1, 'digest_type': 'sha1', 'value': 'test'}
    my_module_object = create_module(my_module, DEFAULT_ARGS, module_args)
    msg = 'Error fetching key with id 1: calling: cluster/ntp/keys: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_ntp_key, 'fail')['msg']


def test_create_ntp_key():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster/ntp/keys', SRR['empty_records']),
        ('POST', 'cluster/ntp/keys', SRR['empty_good'])
    ])
    module_args = {'id': 1, 'digest_type': 'sha1', 'value': 'test'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_ntp_key_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('POST', 'cluster/ntp/keys', SRR['generic_error'])
    ])
    module_args = {'id': 1, 'digest_type': 'sha1', 'value': 'test'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.create_ntp_key, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error creating key with id 1: calling: cluster/ntp/keys: got Expected error.' == error


def test_delete_ntp_key():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster/ntp/keys', SRR['ntp_key']),
        ('DELETE', 'cluster/ntp/keys/1', SRR['empty_good'])
    ])
    module_args = {'state': 'absent', 'id': 1, 'digest_type': 'sha1', 'value': 'test'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_ntp_key_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('DELETE', 'cluster/ntp/keys/1', SRR['generic_error'])
    ])
    module_args = {'id': 1, 'digest_type': 'sha1', 'value': 'test', 'state': 'absent'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.delete_ntp_key, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error deleting key with id 1: calling: cluster/ntp/keys/1: got Expected error.' == error


def test_modify_ntp_key():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster/ntp/keys', SRR['ntp_key']),
        ('PATCH', 'cluster/ntp/keys/1', SRR['empty_good'])
    ])
    module_args = {'id': 1, 'digest_type': 'sha1', 'value': 'test2'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ntp_key_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/ntp/keys', SRR['ntp_key']),
        ('PATCH', 'cluster/ntp/keys/1', SRR['generic_error'])
    ])
    module_args = {'id': 1, 'digest_type': 'sha1', 'value': 'test2'}
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    assert 'Error modifying key with id 1: calling: cluster/ntp/keys/1: got Expected error.' == error
