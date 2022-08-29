# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_error_message, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    call_main, create_module, expect_and_capture_ansible_exception, patch_ansible


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_export_policy_rule import NetAppontapExportRule as my_module, main as my_main

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


policy = {
    'attributes-list': {
        'export-policy-info': {
            'policy-name': 'name',
            'policy-id': '345'
        }}}

policy_rule = {
    'attributes-list': {
        'export-rule-info': {
            'policy-name': 'policy_name',
            'client-match': 'client_match',
            'ro-rule': [{
                'security-flavor': 'any'
            }],
            'rw-rule': [{
                'security-flavor': 'any'
            }],
            'protocol': [{
                'access-protocol': 'protocol'
            }],
            'super-user-security': {
                'security-flavor': 'any'
            },
            'is-allow-set-uid-enabled': 'false',
            'rule-index': 123,
            'anonymous-user-id': 'anonymous_user_id',
        }}}

policy_rule_two_records = {
    'attributes-list': [
        {'export-rule-info': {
            'policy-name': 'policy_name',
            'client-match': 'client_match1,client_match2',
            'ro-rule': [{
                'security-flavor': 'any'
            }],
            'rw-rule': [{
                'security-flavor': 'any'
            }],
            'protocol': [{
                'access-protocol': 'protocol'
            }],
            'super-user-security': {
                'security-flavor': 'any'
            },
            'is-allow-set-uid-enabled': 'false',
            'rule-index': 123,
            'anonymous-user-id': 'anonymous_user_id',
        }},
        {'export-rule-info': {
            'policy-name': 'policy_name',
            'client-match': 'client_match2,client_match1',
            'ro-rule': [{
                'security-flavor': 'any'
            }],
            'rw-rule': [{
                'security-flavor': 'any'
            }],
            'protocol': [{
                'access-protocol': 'protocol'
            }],
            'super-user-security': {
                'security-flavor': 'any'
            },
            'is-allow-set-uid-enabled': 'false',
            'rule-index': 123,
            'anonymous-user-id': 'anonymous_user_id',
        }}]
}


ZRR = zapi_responses({
    'one_policy_record': build_zapi_response(policy, 1),
    'one_bad_policy_record': build_zapi_response({'error': 'no_policy_id'}, 1),
    'one_rule_record': build_zapi_response(policy_rule, 1),
    'two_rule_records': build_zapi_response(policy_rule_two_records, 2),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'never',
    'policy_name': 'policy_name',
    'vserver': 'vserver',

}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('vserver')
    error = 'missing required arguments:'
    assert error in call_main(my_main, args, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_netapp_lib_error(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    error = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert error in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


def test_get_nonexistent_rule():
    ''' Test if get_export_policy_rule returns None for non-existent policy '''
    register_responses([
        ('ZAPI', 'export-rule-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'rule_index': 3
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_export_policy_rule(3) is None


def test_get_nonexistent_policy():
    ''' Test if get_export_policy returns None for non-existent policy '''
    register_responses([
        ('ZAPI', 'export-policy-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'rule_index': 3
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.set_export_policy_id() is None


def test_get_existing_rule():
    ''' Test if get_export_policy_rule returns rule details for existing policy '''
    register_responses([
        ('ZAPI', 'export-rule-get-iter', ZRR['one_rule_record']),
    ])
    module_args = {
        'rule_index': 3
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    result = my_obj.get_export_policy_rule(3)
    assert result
    assert result['name'] == 'policy_name'
    assert result['client_match'] == ['client_match']
    assert result['ro_rule'] == ['any']


def test_get_existing_policy():
    ''' Test if get_export_policy returns policy details for existing policy '''
    register_responses([
        ('ZAPI', 'export-policy-get-iter', ZRR['one_policy_record']),
    ])
    module_args = {
        'rule_index': 3
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    my_obj.set_export_policy_id()
    assert my_obj.policy_id == '345'


def test_create_missing_param_error():
    ''' Test validation error from create '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'export-rule-get-iter', ZRR['no_records']),
        ('ZAPI', 'export-rule-get-iter', ZRR['no_records']),
        ('ZAPI', 'export-policy-get-iter', ZRR['one_policy_record']),
    ])
    module_args = {
        'client_match': 'client_match',
        'rw_rule': 'any',
        'rule_index': 3
    }
    msg = 'Error: Missing required option for creating export policy rule: ro_rule'
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_successful_create_with_index():
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'export-rule-get-iter', ZRR['no_records']),
        ('ZAPI', 'export-rule-get-iter', ZRR['no_records']),
        ('ZAPI', 'export-policy-get-iter', ZRR['no_records']),
        ('ZAPI', 'export-policy-create', ZRR['success']),
        ('ZAPI', 'export-policy-get-iter', ZRR['one_policy_record']),
        ('ZAPI', 'export-rule-create', ZRR['success']),
    ])
    module_args = {
        'client_match': 'client_match',
        'rw_rule': 'any',
        'ro_rule': 'any',
        'rule_index': 123
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_create_no_index():
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'export-rule-get-iter', ZRR['no_records']),
        ('ZAPI', 'export-policy-get-iter', ZRR['one_policy_record']),
        ('ZAPI', 'export-rule-create', ZRR['success']),
    ])
    module_args = {
        'client_match': 'client_match',
        'rw_rule': 'any',
        'ro_rule': 'any'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_idempotency():
    ''' Test create idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'export-rule-get-iter', ZRR['one_rule_record']),
    ])
    module_args = {
        'client_match': 'client_match',
        'rw_rule': 'any',
        'ro_rule': 'any'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete():
    ''' Test delete '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'export-rule-get-iter', ZRR['one_rule_record']),
        ('ZAPI', 'export-policy-get-iter', ZRR['one_policy_record']),
        ('ZAPI', 'export-rule-destroy', ZRR['success']),
    ])
    module_args = {
        'state': 'absent',
        'rule_index': 3
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete_idempotency():
    ''' Test delete idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'export-rule-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'state': 'absent',
        'rule_index': 3
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify():
    ''' Test successful modify protocol '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'export-rule-get-iter', ZRR['one_rule_record']),
        ('ZAPI', 'export-policy-get-iter', ZRR['one_policy_record']),
        ('ZAPI', 'export-rule-modify', ZRR['success']),
    ])
    module_args = {
        'protocol': ['cifs'],
        'allow_suid': True,
        'rule_index': 3
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_on_ambiguous_delete():
    ''' Test error if multiple entries match for a delete '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'export-rule-get-iter', ZRR['two_rule_records']),
    ])
    module_args = {
        'state': 'absent',
        'client_match': 'client_match1,client_match2',
        'rw_rule': 'any',
        'ro_rule': 'any'
    }
    error = "Error multiple records exist for query:"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_helper_query_parameters():
    ''' Test helper method set_query_parameters() '''
    register_responses([
    ])
    module_args = {
        'client_match': 'client_match1,client_match2',
        'rw_rule': 'any',
        'ro_rule': 'any'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    result = my_obj.set_query_parameters(10)
    print(result)
    assert 'query' in result
    assert 'export-rule-info' in result['query']
    assert result['query']['export-rule-info']['rule-index'] == 10
    result = my_obj.set_query_parameters(None)
    print(result)
    assert 'client-match' not in result['query']['export-rule-info']
    assert result['query']['export-rule-info']['rw-rule'] == [{'security-flavor': 'any'}]


def test_error_calling_zapis():
    ''' Test error handing '''
    register_responses([
        ('ZAPI', 'export-rule-get-iter', ZRR['error']),
        ('ZAPI', 'export-policy-get-iter', ZRR['error']),
        ('ZAPI', 'export-policy-get-iter', ZRR['one_bad_policy_record']),
        ('ZAPI', 'export-rule-create', ZRR['error']),
        ('ZAPI', 'export-policy-create', ZRR['error']),
        ('ZAPI', 'export-rule-destroy', ZRR['error']),
        ('ZAPI', 'export-rule-modify', ZRR['error']),
        ('ZAPI', 'export-rule-set-index', ZRR['error']),
    ])
    module_args = {
        'client_match': 'client_match1,client_match2',
        'rw_rule': 'any',
        'ro_rule': 'any',
        'from_rule_index': 123,
        'rule_index': 124,
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = zapi_error_message('Error getting export policy rule policy_name')
    assert error in expect_and_capture_ansible_exception(my_obj.get_export_policy_rule, 'fail', None)['msg']
    error = zapi_error_message('Error getting export policy policy_name')
    assert error in expect_and_capture_ansible_exception(my_obj.set_export_policy_id, 'fail')['msg']
    error = 'Error getting export policy id for policy_name: got'
    assert error in expect_and_capture_ansible_exception(my_obj.set_export_policy_id, 'fail')['msg']
    error = zapi_error_message('Error creating export policy rule policy_name')
    assert error in expect_and_capture_ansible_exception(my_obj.create_export_policy_rule, 'fail')['msg']
    error = zapi_error_message('Error creating export policy policy_name')
    assert error in expect_and_capture_ansible_exception(my_obj.create_export_policy, 'fail')['msg']
    error = zapi_error_message('Error deleting export policy rule policy_name')
    assert error in expect_and_capture_ansible_exception(my_obj.delete_export_policy_rule, 'fail', 123)['msg']
    error = zapi_error_message('Error modifying export policy rule index 123')
    assert error in expect_and_capture_ansible_exception(my_obj.modify_export_policy_rule, 'fail', {'rw_rule': ['any']}, 123)['msg']
    error = zapi_error_message('Error reindexing export policy rule index 123')
    assert error in expect_and_capture_ansible_exception(my_obj.modify_export_policy_rule, 'fail', {'rule_index': 123}, 123, True)['msg']


def test_index_existing_entry():
    """ validate entry can be found without index, and add index """
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'export-rule-get-iter', ZRR['no_records']),
        ('ZAPI', 'export-rule-get-iter', ZRR['one_rule_record']),
        ('ZAPI', 'export-policy-get-iter', ZRR['one_policy_record']),
        ('ZAPI', 'export-rule-set-index', ZRR['success']),
    ])
    module_args = {
        'client_match': 'client_match',
        'rw_rule': 'any',
        'ro_rule': 'any',
        'rule_index': 124,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete_no_index():
    """ validate entry can be found without index, and deleted """
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'export-rule-get-iter', ZRR['two_rule_records']),
        ('ZAPI', 'export-policy-get-iter', ZRR['one_policy_record']),
        ('ZAPI', 'export-rule-destroy', ZRR['success']),
    ])
    module_args = {
        'client_match': 'client_match2,client_match1',
        'rw_rule': 'any',
        'ro_rule': 'any',
        'state': 'absent',
        'force_delete_on_first_match': True,
        'allow_suid': False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
