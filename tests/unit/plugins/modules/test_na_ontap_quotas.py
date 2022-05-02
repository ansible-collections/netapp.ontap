''' unit tests ONTAP Ansible module: na_ontap_quotas '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_warning_was_raised, call_main, patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_error, build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_quotas \
    import NetAppONTAPQuotas as my_module, main as my_main

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

quota_policy = {
    'num-records': 1,
    'attributes-list': {'quota-entry': {'volume': 'ansible', 'policy-name': 'policy_name', 'perform-user-mapping': 'true',
                                        'file-limit': '-', 'disk-limit': '-', 'quota-target': '/vol/ansible',
                                        'soft-file-limit': '-', 'soft-disk-limit': '-', 'threshold': '-'}},
}

quota_policies = {
    'num-records': 2,
    'attributes-list': [{'quota-policy-info': {'policy-name': 'p1'}},
                        {'quota-policy-info': {'policy-name': 'p2'}}],
}

ZRR = zapi_responses({
    'quota_policy': build_zapi_response(quota_policy, 1),
    'quota_on': build_zapi_response({'status': 'on'}, 1),
    'quota_off': build_zapi_response({'status': 'off'}, 1),
    'quota_policies': build_zapi_response(quota_policies, 1),
    'quota_fail': build_zapi_error('TEST', 'This exception is from the unit test'),
    'quota_fail_13001': build_zapi_error('13001', 'success'),
    'quota_fail_14958': build_zapi_error('14958', 'No valid quota rules found'),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'volume': 'ansible',
    'vserver': 'ansible',
    'quota_target': '/vol/ansible',
    'type': 'user'
}


def test_module_fail_when_required_args_missing():
    error = create_module(my_module, fail=True)['msg']
    assert 'missing required arguments:' in error


def test_ensure_get_called():
    register_responses([
        ('ZAPI', 'quota-list-entries-iter', ZRR['empty']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    quotas = my_obj.get_quotas()
    print('QUOTAS', quotas)
    assert quotas is None


def test_ensure_get_quota_not_called():
    args = dict(DEFAULT_ARGS)
    args.pop('quota_target')
    args.pop('type')
    my_obj = create_module(my_module, args)
    assert my_obj.get_quotas() is None


def test_ensure_get_called_existing():
    register_responses([
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    quotas = my_obj.get_quotas()
    print('QUOTAS', quotas)
    assert quotas


def test_successful_create():
    ''' creating quota and testing idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['no_records']),
        ('ZAPI', 'quota-status', ZRR['quota_on']),
        ('ZAPI', 'quota-set-entry', ZRR['success']),
        ('ZAPI', 'quota-resize', ZRR['success']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
        ('ZAPI', 'quota-status', ZRR['quota_on']),
    ])
    module_args = {
        'file_limit': '3',
        'disk_limit': '4',
        'perform_user_mapping': False,
        'policy': 'policy',
        'soft_file_limit': '3',
        'soft_disk_limit': '4',
        'threshold': '10',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_successful_delete():
    ''' deleting quota and testing idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
        ('ZAPI', 'quota-status', ZRR['quota_on']),
        ('ZAPI', 'quota-delete-entry', ZRR['success']),
        ('ZAPI', 'quota-resize', ZRR['success']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['no_records']),
        ('ZAPI', 'quota-status', ZRR['quota_on']),
    ])
    module_args = {
        'policy': 'policy',
        'state': 'absent'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_successful_modify(dont_sleep):
    ''' modifying quota and testing idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
        ('ZAPI', 'quota-status', ZRR['quota_on']),
        ('ZAPI', 'quota-modify-entry', ZRR['success']),
        ('ZAPI', 'quota-off', ZRR['success']),
        ('ZAPI', 'quota-on', ZRR['success']),
    ])
    module_args = {
        'activate_quota_on_change': 'reinitialize',
        'file_limit': '3',
        'policy': 'policy',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_quota_on_off():
    ''' quota set on or off '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
        ('ZAPI', 'quota-status', ZRR['quota_off']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
        ('ZAPI', 'quota-status', ZRR['quota_on']),
        ('ZAPI', 'quota-off', ZRR['success']),
    ])
    module_args = {'set_quota_status': False}
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('ZAPI', 'quota-status', ZRR['quota_fail']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_fail']),
        ('ZAPI', 'quota-set-entry', ZRR['quota_fail']),
        ('ZAPI', 'quota-delete-entry', ZRR['quota_fail']),
        ('ZAPI', 'quota-modify-entry', ZRR['quota_fail']),
        ('ZAPI', 'quota-on', ZRR['quota_fail']),
        ('ZAPI', 'quota-policy-get-iter', ZRR['quota_fail']),
        ('ZAPI', 'quota-resize', ZRR['quota_fail']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    assert 'Error fetching quotas status info' in expect_and_capture_ansible_exception(my_obj.get_quota_status, 'fail')['msg']
    assert 'Error fetching quotas info' in expect_and_capture_ansible_exception(my_obj.get_quotas, 'fail')['msg']
    assert 'Error adding/modifying quota entry' in expect_and_capture_ansible_exception(my_obj.quota_entry_set, 'fail')['msg']
    assert 'Error deleting quota entry' in expect_and_capture_ansible_exception(my_obj.quota_entry_delete, 'fail')['msg']
    assert 'Error modifying quota entry' in expect_and_capture_ansible_exception(my_obj.quota_entry_modify, 'fail', {})['msg']
    assert 'Error setting quota-on for ansible' in expect_and_capture_ansible_exception(my_obj.on_or_off_quota, 'fail', 'quota-on')['msg']
    assert 'Error fetching quota policies' in expect_and_capture_ansible_exception(my_obj.get_quota_policies, 'fail')['msg']
    assert 'Error setting quota-resize for ansible:' in expect_and_capture_ansible_exception(my_obj.resize_quota, 'fail')['msg']


def test_get_quota_policies():
    register_responses([
        ('ZAPI', 'quota-policy-get-iter', ZRR['quota_policies']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    policies = my_obj.get_quota_policies()
    assert len(policies) == 2


def test_debug_quota_get_error_fail():
    register_responses([
        ('ZAPI', 'quota-policy-get-iter', ZRR['quota_policies']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.debug_quota_get_error, 'fail', 'dummy error')['msg']
    assert error.startswith('Error fetching quotas info: dummy error - current vserver policies: ')


def test_debug_quota_get_error_success():
    register_responses([
        ('ZAPI', 'quota-policy-get-iter', ZRR['quota_policy']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    quotas = my_obj.debug_quota_get_error('dummy error')
    print('QUOTAS', quotas)
    assert quotas


def test_get_no_quota_retry_on_13001():
    register_responses([
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_fail_13001']),
    ])
    module_args = {'policy': 'policy'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.get_quotas, 'fail')['msg']
    assert error.startswith('Error fetching quotas info for policy policy')


def test_get_quota_retry_on_13001():
    register_responses([
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_fail_13001']),
        ('ZAPI', 'quota-policy-get-iter', ZRR['quota_policy']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    quotas = my_obj.get_quotas()
    print('QUOTAS', quotas)
    assert quotas


def test_resize_warning():
    ''' warning as resize is not allowed if all rules were deleted '''
    register_responses([
        ('ZAPI', 'quota-resize', ZRR['quota_fail_14958']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.resize_quota('delete')
    assert_warning_was_raised('Last rule deleted, but quota is on as resize is not allowed.')


def test_quota_on_warning():
    ''' warning as quota-on is not allowed if all rules were deleted '''
    register_responses([
        ('ZAPI', 'quota-on', ZRR['quota_fail_14958']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.on_or_off_quota('quota-on', 'delete')
    print_warnings()
    assert_warning_was_raised('Last rule deleted, quota is off.')


def test_convert_size_format():
    module_args = {'disk_limit': '10MB'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.convert_to_kb('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == '10240'
    my_obj.parameters['disk_limit'] = '10'
    assert my_obj.convert_to_kb('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == '10'
    my_obj.parameters['disk_limit'] = '10tB'
    assert my_obj.convert_to_kb('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == str(10 * 1024 * 1024 * 1024)
    my_obj.parameters['disk_limit'] = ''
    assert not my_obj.convert_to_kb('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == ''


def test_error_convert_size_format():
    module_args = {
        'disk_limit': '10MBi',
        'quota_target': ''
    }
    error = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert error.startswith('disk_limit input string is not a valid size format')
    module_args = {
        'soft_disk_limit': 'MBi',
        'quota_target': ''
    }
    error = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert error.startswith('soft_disk_limit input string is not a valid size format')
    module_args = {
        'soft_disk_limit': '10MB10',
        'quota_target': ''
    }
    error = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert error.startswith('soft_disk_limit input string is not a valid size format')


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_has_netapp_lib(has_netapp_lib):
    has_netapp_lib.return_value = False
    assert call_main(my_main, DEFAULT_ARGS, fail=True)['msg'] == 'Error: the python NetApp-Lib module is required.  Import error: None'


def create_from_main():
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'quota-list-entries-iter', ZRR['no_records']),
        ('ZAPI', 'quota-status', ZRR['quota_on']),
        ('ZAPI', 'quota-set-entry', ZRR['success']),
    ])
    assert call_main(my_main, DEFAULT_ARGS)['changed']
