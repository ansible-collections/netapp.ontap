# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    call_main, patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_export_policy_rule \
    import NetAppontapExportRule as policy_rule, main as my_main    # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    'get_uuid_policy_id_export_policy': (200, {"records": [
        {
            "svm": {"uuid": "uuid", "name": "svm"},
            "id": 123,
            "name": "ansible"
        }], "num_records": 1}, None),
    'get_export_policy_rules': (200, {"records": [
        {
            "rw_rule": ["any"],
            "_links": {"self": {"href": "/api/resourcelink"}},
            "ro_rule": ["any"],
            "allow_suid": True,
            "chown_mode": "restricted",
            "index": 10,
            "superuser": ["any"],
            "protocols": ["any"],
            "anonymous_user": "1234",
            "clients": [{"match": "10.10.0.0/16"}, {"match": "10.0.0.0/16"}, {"match": "10.20.0.0/16"}],
            "ntfs_unix_security": "fail",
            "allow_device_creation": True
        }], "num_records": 1}, None),
    'get_export_policy_two_rules': (200, {"records": [
        {
            "rw_rule": ["any"],
            "_links": {"self": {"href": "/api/resourcelink"}},
            "ro_rule": ["any"],
            "allow_suid": True,
            "chown_mode": "restricted",
            "index": 10,
            "superuser": ["any"],
            "protocols": ["any"],
            "anonymous_user": "1234",
            "clients": [{"match": "0.0.0.0/0"}],
            "ntfs_unix_security": "fail",
            "allow_device_creation": True
        },
        {
            "rw_rule": ["any"],
            "ro_rule": ["any"],
            "allow_suid": True,
            "chown_mode": "restricted",
            "index": 11,
            "superuser": ["any"],
            "protocols": ["any"],
            "anonymous_user": "1234",
            "clients": [{"match": "0.0.0.0/0"}],
            "ntfs_unix_security": "fail",
            "allow_device_creation": True
        }], "num_records": 2}, None),
    'create_export_policy_rules': (200, {"records": [
        {
            "rw_rule": ["any"],
            "_links": {"self": {"href": "/api/resourcelink"}},
            "ro_rule": ["any"],
            "allow_suid": True,
            "chown_mode": "restricted",
            "index": 1,
            "superuser": ["any"],
            "protocols": ["any"],
            "anonymous_user": "1234",
            "clients": [{"match": "0.0.0.0/0"}],
            "ntfs_unix_security": "fail",
            "allow_device_creation": True
        }], "num_records": 1}, None),
    'error_does_not_exist': (400, None, {'message': "entry doesn't exist"})
})


DEFAULT_ARGS = {
    'name': 'test',
    'client_match': ['1.1.1.0', '0.0.0.0/0'],
    'vserver': 'test',
    'protocol': 'nfs',
    'anonymous_user_id': '65534',
    'super_user_security': ['any'],
    'ntfs_unix_security': 'fail',
    'ro_rule': 'any',
    'rw_rule': 'any',
    'allow_device_creation': True,
    'allow_suid': True,
    'chown_mode': 'restricted',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
}


def test_rest_successful_create_rule():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/10', SRR['empty_records']),
        ('GET', 'protocols/nfs/export-policies/123/rules', SRR['empty_records']),
        ('POST', 'protocols/nfs/export-policies/123/rules?return_records=true', SRR['create_export_policy_rules']),
        ('PATCH', 'protocols/nfs/export-policies/123/rules/1', SRR['empty_records'])
    ])
    assert create_and_apply(policy_rule, DEFAULT_ARGS, {'rule_index': 10})['changed']


def test_rest_error_get_policy():
    '''Test error rest get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['generic_error'])
    ])
    my_module_object = create_module(policy_rule, DEFAULT_ARGS)
    msg = 'Error on fetching export policy: calling: protocols/nfs/export-policies: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_export_policy_rule_rest, 'fail', 1)['msg']


def test_rest_error_get_rule():
    '''Test error rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/10', SRR['generic_error']),
        # 2nd try - this time without index
        ('GET', 'protocols/nfs/export-policies/123/rules', SRR['generic_error']),
        # 3rd try
        ('GET', 'protocols/nfs/export-policies/123/rules', SRR['error_does_not_exist']),
        # 4thtry
        ('GET', 'protocols/nfs/export-policies/123/rules', SRR['get_export_policy_two_rules']),
    ])
    module_args = {
        'anonymous_user_id': '1234',
        'protocol': 'any',
        'super_user_security': 'any',
        'client_match': ['0.0.0.0/0'],
        'ntfs_unix_security': 'fail',
        'ro_rule': ['any'],
        'rw_rule': ['any'],
        'rule_index': 10
    }
    my_module_object = create_module(policy_rule, DEFAULT_ARGS, module_args)
    msg = rest_error_message('Error on fetching export policy rule', 'protocols/nfs/export-policies/123/rules/10')
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_export_policy_rule, 'fail', 10)['msg']
    # error with no index
    msg = rest_error_message('Error on fetching export policy rules', 'protocols/nfs/export-policies/123/rules')
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_export_policy_rule, 'fail', None)['msg']
    # does not exist error is ignored
    assert my_module_object.get_export_policy_rule(None) is None
    # multiple entries error
    msg = 'Error multiple records exist for query:'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_export_policy_rule, 'fail', None)['msg']


def test_rest_error_create_rule():
    '''Test error rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/10', SRR['empty_records']),
        ('GET', 'protocols/nfs/export-policies/123/rules', SRR['empty_records']),
        ('POST', 'protocols/nfs/export-policies/123/rules?return_records=true', SRR['generic_error']),
        # 2nd call
        ('GET', 'protocols/nfs/export-policies/123/rules/10', SRR['empty_records']),
        ('GET', 'protocols/nfs/export-policies/123/rules', SRR['empty_records']),
        ('POST', 'protocols/nfs/export-policies/123/rules?return_records=true', SRR['empty_records'])
    ])
    my_module_object = create_module(policy_rule, DEFAULT_ARGS, {'rule_index': 10})
    msg = rest_error_message('Error on creating export policy rule', 'protocols/nfs/export-policies/123/rules?return_records=true')
    assert msg in expect_and_capture_ansible_exception(my_module_object.apply, 'fail')['msg']
    msg = 'Error on creating export policy rule, returned response is invalid:'
    assert msg in expect_and_capture_ansible_exception(my_module_object.apply, 'fail')['msg']


def test_rest_successful_delete_rule():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/10', copy.deepcopy(SRR['get_export_policy_rules'])),
        ('DELETE', 'protocols/nfs/export-policies/123/rules/10', SRR['empty_good'])
    ])
    assert create_and_apply(policy_rule, DEFAULT_ARGS, {'rule_index': 10, 'state': 'absent'})['changed']


def test_rest_error_delete():
    '''Test error rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/10', copy.deepcopy(SRR['get_export_policy_rules'])),
        ('DELETE', 'protocols/nfs/export-policies/123/rules/10', SRR['generic_error'])
    ])
    my_module_object = create_module(policy_rule, DEFAULT_ARGS, {'rule_index': 10, 'state': 'absent'})
    msg = 'Error on deleting export policy Rule: calling: protocols/nfs/export-policies/123/rules/10: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.apply, 'fail')['msg']


def test_rest_successful_create_policy_and_rule():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['empty_records']),
        ('GET', 'protocols/nfs/export-policies', SRR['empty_records']),
        ('GET', 'protocols/nfs/export-policies', SRR['empty_records']),
        ('POST', 'protocols/nfs/export-policies', SRR['empty_good']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('POST', 'protocols/nfs/export-policies/123/rules?return_records=true', SRR['create_export_policy_rules']),
        ('PATCH', 'protocols/nfs/export-policies/123/rules/1', SRR['empty_records'])
    ])
    assert create_and_apply(policy_rule, DEFAULT_ARGS, {'rule_index': 10})['changed']


def test_rest_error_creating_policy():
    '''Test error rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['empty_records']),
        ('GET', 'protocols/nfs/export-policies', SRR['empty_records']),
        ('POST', 'protocols/nfs/export-policies', SRR['generic_error']),
    ])
    my_module_object = create_module(policy_rule, DEFAULT_ARGS)
    msg = 'Error on creating export policy: calling: protocols/nfs/export-policies: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.apply, 'fail')['msg']


def test_rest_successful_modify():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/10', copy.deepcopy(SRR['get_export_policy_rules'])),
        ('PATCH', 'protocols/nfs/export-policies/123/rules/10', SRR['empty_good'])
    ])
    module_args = {
        'anonymous_user_id': '1234',
        'protocol': 'nfs4',
        'super_user_security': 'krb5i',
        'client_match': ['1.1.1.3', '1.1.0.3'],
        'ntfs_unix_security': 'ignore',
        'ro_rule': ['never'],
        'rw_rule': ['never'],
        'rule_index': 10,
        'allow_device_creation': False,
        'allow_suid': False,
        'chown_mode': 'unrestricted'
    }
    assert create_and_apply(policy_rule, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_modify():
    '''Test error rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/10', copy.deepcopy(SRR['get_export_policy_rules'])),
        ('PATCH', 'protocols/nfs/export-policies/123/rules/10', SRR['generic_error'])
    ])
    module_args = {
        'anonymous_user_id': '1234',
        'protocol': 'nfs4',
        'super_user_security': 'krb5i',
        'rule_index': 10
    }

    my_module_object = create_module(policy_rule, DEFAULT_ARGS, module_args)
    msg = 'Error on modifying export policy Rule: calling: protocols/nfs/export-policies/123/rules/10: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.apply, 'fail')['msg']


def test_rest_successful_rename():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/2', SRR['empty_records']),
        ('GET', 'protocols/nfs/export-policies/123/rules/10', copy.deepcopy(SRR['get_export_policy_rules'])),
        ('PATCH', 'protocols/nfs/export-policies/123/rules/10', SRR['empty_records'])
    ])
    module_args = {
        'anonymous_user_id': '1234',
        'protocol': 'nfs4',
        'super_user_security': 'krb5i',
        'client_match': ['1.1.1.3', '1.1.0.3'],
        'ntfs_unix_security': 'ignore',
        'ro_rule': ['never'],
        'rw_rule': ['never'],
        'rule_index': 2,
        'from_rule_index': 10,
        'allow_device_creation': False,
        'allow_suid': False,
        'chown_mode': 'unrestricted'
    }
    assert create_and_apply(policy_rule, DEFAULT_ARGS, module_args)['changed']


def test_rest_successful_rename_no_from_index():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/2', SRR['error_does_not_exist']),
        ('GET', 'protocols/nfs/export-policies/123/rules', copy.deepcopy(SRR['get_export_policy_rules'])),
        ('PATCH', 'protocols/nfs/export-policies/123/rules/10', SRR['empty_records'])
    ])
    module_args = {
        'anonymous_user_id': '1234',
        'protocol': 'any',
        'super_user_security': 'any',
        'client_match': ["10.10.0.0/16", "10.20.0.0/16", "10.0.0.0/16"],
        'ntfs_unix_security': 'fail',
        'ro_rule': ['any'],
        'rw_rule': ['any'],
        'rule_index': 2
    }
    assert create_and_apply(policy_rule, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_rename_with_from_index_not_found():
    """ rename is requested but from rule is not found """
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/3', SRR['error_does_not_exist']),
        ('GET', 'protocols/nfs/export-policies/123/rules/2', SRR['error_does_not_exist']),
    ])
    module_args = {
        'anonymous_user_id': '1234',
        'protocol': 'nfs4',
        'super_user_security': 'krb5i',
        'client_match': ['1.1.1.3', '1.1.0.3'],
        'ntfs_unix_security': 'ignore',
        'ro_rule': ['never'],
        'rw_rule': ['never'],
        'rule_index': 3,
        'from_rule_index': 2,
    }
    msg = 'Error reindexing: export policy rule 2 does not exist.'
    assert msg in create_and_apply(policy_rule, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_delete_no_index_multiple():
    """ delete is requested but 2 rules are found """
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules', SRR['get_export_policy_two_rules']),
        # 2nd run
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules', SRR['get_export_policy_two_rules']),
        ('DELETE', 'protocols/nfs/export-policies/123/rules/10', SRR['success'])
    ])
    module_args = {
        'anonymous_user_id': '1234',
        'protocol': 'any',
        'super_user_security': 'any',
        'client_match': ['0.0.0.0/0'],
        'ntfs_unix_security': 'fail',
        'ro_rule': ['any'],
        'rw_rule': ['any'],
        'state': 'absent'
    }
    msg = 'Error multiple records exist for query:'
    assert msg in create_and_apply(policy_rule, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['force_delete_on_first_match'] = True
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
