# (c) 2018-2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_iscsi_security '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_and_apply, create_module, expect_and_capture_ansible_exception, call_main, assert_warning_was_raised, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_iscsi_security \
    import NetAppONTAPIscsiSecurity as iscsi_object, main as iscsi_module_main      # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'get_uuid': (200, {"records": [{"uuid": "e2e89ccc-db35-11e9"}]}, None),
    'get_initiator': (200, {"records": [
        {
            "svm": {
                "uuid": "e2e89ccc-db35-11e9",
                "name": "test_ansible"
            },
            "initiator": "eui.0123456789abcdef",
            "authentication_type": "chap",
            "chap": {
                "inbound": {
                    "user": "test_user_1"
                },
                "outbound": {
                    "user": "test_user_2"
                }
            },
            "initiator_address": {
                "ranges": [
                    {
                        "start": "10.125.10.0",
                        "end": "10.125.10.10",
                        "family": "ipv4"
                    },
                    {
                        "start": "10.10.10.7",
                        "end": "10.10.10.7",
                        "family": "ipv4"
                    }
                ]
            }
        }], "num_records": 1}, None),
    'get_initiator_no_user': (200, {"records": [
        {
            "svm": {
                "uuid": "e2e89ccc-db35-11e9",
                "name": "test_ansible"
            },
            "initiator": "eui.0123456789abcdef",
            "authentication_type": "chap",
            "chap": {
            },
            "initiator_address": {
                "ranges": [
                ]
            }
        }], "num_records": 1}, None),
    'get_initiator_none': (200, {"records": [
        {
            "svm": {
                "uuid": "e2e89ccc-db35-11e9",
                "name": "test_ansible"
            },
            "initiator": "eui.0123456789abcdef",
            "authentication_type": "none"
        }], "num_records": 1}, None),
})


DEFAULT_ARGS = {
    'initiator': "eui.0123456789abcdef",
    'inbound_username': "test_user_1",
    'inbound_password': "123",
    'outbound_username': "test_user_2",
    'outbound_password': "321",
    'auth_type': "chap",
    'address_ranges': ["10.125.10.0-10.125.10.10", "10.10.10.7"],
    'hostname': 'test',
    'vserver': 'test_vserver',
    'username': 'test_user',
    'password': 'test_pass!'
}


def test_rest_successful_create():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['get_uuid']),
        ('GET', 'protocols/san/iscsi/credentials', SRR['zero_records']),
        ('POST', 'protocols/san/iscsi/credentials', SRR['success']),
        # idempotent check
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['get_uuid']),
        ('GET', 'protocols/san/iscsi/credentials', SRR['get_initiator']),
    ])
    assert create_and_apply(iscsi_object, DEFAULT_ARGS)['changed']
    assert not create_and_apply(iscsi_object, DEFAULT_ARGS)['changed']


def test_rest_successful_modify_address():
    '''Test successful rest modify'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['get_uuid']),
        ('GET', 'protocols/san/iscsi/credentials', SRR['get_initiator']),
        ('PATCH', 'protocols/san/iscsi/credentials/e2e89ccc-db35-11e9/eui.0123456789abcdef', SRR['success'])
    ])
    args = {'address_ranges': ['10.10.10.8']}
    assert create_and_apply(iscsi_object, DEFAULT_ARGS, args)['changed']


def test_rest_successful_modify_inbound_user():
    '''Test successful rest modify'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['get_uuid']),
        ('GET', 'protocols/san/iscsi/credentials', SRR['get_initiator']),
        ('PATCH', 'protocols/san/iscsi/credentials/e2e89ccc-db35-11e9/eui.0123456789abcdef', SRR['success'])
    ])
    args = {'inbound_username': 'test_user_3'}
    assert create_and_apply(iscsi_object, DEFAULT_ARGS, args)['changed']


def test_rest_successful_modify_outbound_user():
    '''Test successful rest modify'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['get_uuid']),
        ('GET', 'protocols/san/iscsi/credentials', SRR['get_initiator']),
        ('PATCH', 'protocols/san/iscsi/credentials/e2e89ccc-db35-11e9/eui.0123456789abcdef', SRR['success'])
    ])
    args = {'outbound_username': 'test_user_3'}
    assert create_and_apply(iscsi_object, DEFAULT_ARGS, args)['changed']


def test_rest_successful_modify_chap_no_user():
    '''Test successful rest modify'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['get_uuid']),
        ('GET', 'protocols/san/iscsi/credentials', SRR['get_initiator_no_user']),
        ('PATCH', 'protocols/san/iscsi/credentials/e2e89ccc-db35-11e9/eui.0123456789abcdef', SRR['success'])
    ])
    assert create_and_apply(iscsi_object, DEFAULT_ARGS)['changed']


def test_rest_successful_modify_chap():
    '''Test successful rest modify'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['get_uuid']),
        ('GET', 'protocols/san/iscsi/credentials', SRR['get_initiator_none']),
        ('PATCH', 'protocols/san/iscsi/credentials/e2e89ccc-db35-11e9/eui.0123456789abcdef', SRR['success'])
    ])
    assert call_main(iscsi_module_main, DEFAULT_ARGS)['changed']


def test_all_methods_catch_exception():
    ''' test exception in get/create/modify/delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['get_uuid']),
        ('GET', 'svm/svms', SRR['generic_error']),
        ('GET', 'svm/svms', SRR['empty_records']),
        # GET/POST/PATCH error.
        ('GET', 'protocols/san/iscsi/credentials', SRR['generic_error']),
        ('POST', 'protocols/san/iscsi/credentials', SRR['generic_error']),
        ('PATCH', 'protocols/san/iscsi/credentials/e2e89ccc-db35-11e9/eui.0123456789abcdef', SRR['generic_error']),
        ('DELETE', 'protocols/san/iscsi/credentials/e2e89ccc-db35-11e9/eui.0123456789abcdef', SRR['generic_error'])
    ])
    sec_obj = create_module(iscsi_object, DEFAULT_ARGS)
    assert 'Error on fetching svm uuid' in expect_and_capture_ansible_exception(sec_obj.get_svm_uuid, 'fail')['msg']
    assert 'Error on fetching svm uuid, SVM not found' in expect_and_capture_ansible_exception(sec_obj.get_svm_uuid, 'fail')['msg']
    assert 'Error on fetching initiator' in expect_and_capture_ansible_exception(sec_obj.get_initiator, 'fail')['msg']
    assert 'Error on creating initiator' in expect_and_capture_ansible_exception(sec_obj.create_initiator, 'fail')['msg']
    assert 'Error on modifying initiator' in expect_and_capture_ansible_exception(sec_obj.modify_initiator, 'fail', {}, {})['msg']
    assert 'Error on deleting initiator' in expect_and_capture_ansible_exception(sec_obj.delete_initiator, 'fail')['msg']
