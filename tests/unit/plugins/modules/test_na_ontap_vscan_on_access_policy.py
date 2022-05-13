# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_vscan_scanner_pool '''

from __future__ import (absolute_import, division, print_function)
from ansible_collections.netapp.ontap.tests.unit.plugins.modules.test_na_ontap_qos_policy_group import DEFAULT_ARGS
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible,\
    create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_vscan_on_access_policy \
    import NetAppOntapVscanOnAccessPolicy as policy_module  # module under test
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


DEFAULT_ARGS = {
    'state': 'present',
    'vserver': 'test_vserver',
    'policy_name': 'test_carchi',
    'max_file_size': 2147483648 + 1,     # 2GB + 1
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!'
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
            'is-policy-enabled': 'true'
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
