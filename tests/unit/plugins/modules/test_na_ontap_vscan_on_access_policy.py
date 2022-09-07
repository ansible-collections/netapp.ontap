# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_vscan_scanner_pool '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible,\
    create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_vscan_on_access_policy \
    import NetAppOntapVscanOnAccessPolicy as policy_module  # module under test
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'state': 'present',
    'vserver': 'test_vserver',
    'policy_name': 'test_carchi',
    'max_file_size': 2147483648 + 1,     # 2GB + 1
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'never'
}


vscan_info = {
    'num-records': 1,
    'attributes-list': {
        'vscan-on-access-policy-info': {
            'policy-name': 'test_carchi',
            'vserver': 'test_vserver',
            'max-file-size': 2147483648 + 1,
            'is-scan-mandatory': 'false',
            'scan-files-with-no-ext': 'true',
            'is-policy-enabled': 'true',
            'file-ext-to-include': ['py']
        }
    }
}


ZRR = zapi_responses({
    'vscan_info': build_zapi_response(vscan_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "policy_name", "vserver"]
    error = create_module(policy_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_get_nonexistent_policy():
    register_responses([
        ('vscan-on-access-policy-get-iter', ZRR['empty'])
    ])
    policy_obj = create_module(policy_module, DEFAULT_ARGS)
    result = policy_obj.get_on_access_policy()
    assert result is None


def test_get_existing_scanner():
    register_responses([
        ('vscan-on-access-policy-get-iter', ZRR['vscan_info'])
    ])
    policy_obj = create_module(policy_module, DEFAULT_ARGS)
    result = policy_obj.get_on_access_policy()
    assert result


def test_successfully_create():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('vscan-on-access-policy-get-iter', ZRR['empty']),
        ('vscan-on-access-policy-create', ZRR['success'])
    ])
    assert create_and_apply(policy_module, DEFAULT_ARGS)['changed']


def test_create_idempotency():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('vscan-on-access-policy-get-iter', ZRR['vscan_info'])
    ])
    assert create_and_apply(policy_module, DEFAULT_ARGS)['changed'] is False


def test_successfully_delete():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('vscan-on-access-policy-get-iter', ZRR['vscan_info']),
        ('vscan-on-access-policy-delete', ZRR['success'])
    ])
    assert create_and_apply(policy_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_delete_idempotency():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('vscan-on-access-policy-get-iter', ZRR['empty'])
    ])
    assert create_and_apply(policy_module, DEFAULT_ARGS, {'state': 'absent'})['changed'] is False


def test_successfully_create_and_enable_policy():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('vscan-on-access-policy-get-iter', ZRR['empty']),
        ('vscan-on-access-policy-create', ZRR['success']),
        ('vscan-on-access-policy-status-modify', ZRR['success'])
    ])
    args = {'policy_status': True}
    assert create_and_apply(policy_module, DEFAULT_ARGS, args)['changed']


def test_disable_policy_and_delete():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('vscan-on-access-policy-get-iter', ZRR['vscan_info']),
        ('vscan-on-access-policy-status-modify', ZRR['success']),
        ('vscan-on-access-policy-delete', ZRR['success'])
    ])
    args = {'policy_status': False, 'state': 'absent'}
    assert create_and_apply(policy_module, DEFAULT_ARGS, args)['changed']


def test_modify_policy():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('vscan-on-access-policy-get-iter', ZRR['vscan_info']),
        ('vscan-on-access-policy-modify', ZRR['success'])
    ])
    args = {'max_file_size': 2147483650}
    assert create_and_apply(policy_module, DEFAULT_ARGS, args)['changed']


def test_modify_files_to_incluse_empty_error():
    args = {'file_ext_to_include': []}
    msg = 'Error: The value for file_ext_include cannot be empty'
    assert msg in create_module(policy_module, DEFAULT_ARGS, args, fail=True)['msg']


def module_error_disable_policy():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('vscan-on-access-policy-get-iter', ZRR['vscan_info']),
        ('vscan-on-access-policy-status-modify', ZRR['error'])
    ])
    args = {'policy_status': False}
    error = create_and_apply(policy_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error modifying status Vscan on Access Policy' in error


def test_if_all_methods_catch_exception():
    register_responses([
        ('vscan-on-access-policy-get-iter', ZRR['error']),
        ('vscan-on-access-policy-create', ZRR['error']),
        ('vscan-on-access-policy-modify', ZRR['error']),
        ('vscan-on-access-policy-delete', ZRR['error']),
    ])

    policy_obj = create_module(policy_module, DEFAULT_ARGS)

    error = expect_and_capture_ansible_exception(policy_obj.get_on_access_policy, 'fail')['msg']
    assert 'Error searching Vscan on Access Policy' in error

    error = expect_and_capture_ansible_exception(policy_obj.create_on_access_policy, 'fail')['msg']
    assert 'Error creating Vscan on Access Policy' in error

    error = expect_and_capture_ansible_exception(policy_obj.modify_on_access_policy, 'fail')['msg']
    assert 'Error Modifying Vscan on Access Policy' in error

    error = expect_and_capture_ansible_exception(policy_obj.delete_on_access_policy, 'fail')['msg']
    assert 'Error Deleting Vscan on Access Policy' in error


DEFAULT_ARGS_REST = {
    "policy_name": "custom_CIFS",
    "policy_status": True,
    "file_ext_to_exclude": ["exe", "yml", "py"],
    "file_ext_to_include": ['txt', 'json'],
    "scan_readonly_volumes": True,
    "only_execute_access": False,
    "is_scan_mandatory": True,
    "paths_to_exclude": ['\folder1', '\folder2'],
    "scan_files_with_no_ext": True,
    "max_file_size": 2147483648,
    "vserver": "vscan-test",
    "hostname": "test",
    "username": "test_user",
    "password": "test_pass",
    "use_rest": "always"
}


SRR = rest_responses({
    'vscan_on_access_policy': (200, {"records": [
        {
            "svm": {"name": "vscan-test"},
            "name": "custom_CIFS",
            "enabled": True,
            "mandatory": True,
            "scope": {
                "max_file_size": 2147483648,
                "exclude_paths": ["\folder1", "\folder2"],
                "include_extensions": ["txt", "json"],
                "exclude_extensions": ["exe", "yml", "py"],
                "scan_without_extension": True,
                "scan_readonly_volumes": True,
                "only_execute_access": False
            }
        }
    ], "num_records": 1}, None),
    'svm_uuid': (200, {"records": [
        {
            'uuid': 'e3cb5c7f-cd20'
        }], "num_records": 1}, None)
})


def test_successfully_create_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies', SRR['empty_records']),
        ('POST', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies', SRR['success'])
    ])
    assert create_and_apply(policy_module, DEFAULT_ARGS_REST)['changed']


def test_successfully_create_rest_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies', SRR['vscan_on_access_policy'])
    ])
    assert create_and_apply(policy_module, DEFAULT_ARGS_REST)['changed'] is False


def test_modify_policy_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies', SRR['vscan_on_access_policy']),
        ('PATCH', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies/custom_CIFS', SRR['success'])
    ])
    args = {
        "policy_status": False,
        "file_ext_to_exclude": ['yml'],
        "file_ext_to_include": ['json'],
        "scan_readonly_volumes": False,
        "only_execute_access": True,
        "is_scan_mandatory": False,
        "paths_to_exclude": ['\folder1'],
        "scan_files_with_no_ext": False,
        "max_file_size": 2147483649
    }
    assert create_and_apply(policy_module, DEFAULT_ARGS_REST, args)['changed']


def test_disable_and_delete_policy_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies', SRR['vscan_on_access_policy']),
        ('PATCH', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies/custom_CIFS', SRR['success']),
        ('DELETE', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies/custom_CIFS', SRR['success'])
    ])
    args = {
        'state': 'absent',
        'policy_status': False
    }
    assert create_and_apply(policy_module, DEFAULT_ARGS_REST, args)['changed']


def test_delete_idempotent():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies', SRR['empty_records'])
    ])
    args = {
        'state': 'absent'
    }
    assert create_and_apply(policy_module, DEFAULT_ARGS_REST, args)['changed'] is False


def test_get_vserver_not_found():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['empty_records'])
    ])
    msg = 'Error vserver vscan-test not found'
    assert msg in create_and_apply(policy_module, DEFAULT_ARGS_REST, fail=True)['msg']


def test_invalid_option_error_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    args = {'paths_to_exclude': [""]}
    msg = 'Error: Invalid value specified for option(s)'
    assert msg in create_module(policy_module, DEFAULT_ARGS_REST, args, fail=True)['msg']


def test_get_error_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies', SRR['generic_error'])
    ])
    msg = 'Error searching Vscan on Access Policy'
    assert msg in create_and_apply(policy_module, DEFAULT_ARGS_REST, fail=True)['msg']


def test_if_all_methods_catch_exception_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['generic_error']),
        ('POST', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies', SRR['generic_error']),
        ('PATCH', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies/custom_CIFS', SRR['generic_error']),
        ('DELETE', 'protocols/vscan/e3cb5c7f-cd20/on-access-policies/custom_CIFS', SRR['generic_error'])
    ])

    policy_obj = create_module(policy_module, DEFAULT_ARGS_REST)
    policy_obj.svm_uuid = "e3cb5c7f-cd20"

    msg = 'calling: svm/svms: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(policy_obj.get_svm_uuid, 'fail')['msg']

    msg = 'Error creating Vscan on Access Policy'
    assert msg in expect_and_capture_ansible_exception(policy_obj.create_on_access_policy_rest, 'fail')['msg']

    msg = 'Error Modifying Vscan on Access Policy'
    assert msg in expect_and_capture_ansible_exception(policy_obj.modify_on_access_policy_rest, 'fail', {"policy_status": False})['msg']

    msg = 'Error Deleting Vscan on Access Policy'
    assert msg in expect_and_capture_ansible_exception(policy_obj.delete_on_access_policy_rest, 'fail')['msg']
