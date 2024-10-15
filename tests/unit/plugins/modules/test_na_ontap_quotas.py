# (c) 2019-2024, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_quotas '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import assert_no_warnings, \
    assert_warning_was_raised, call_main, patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_error, build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_quotas \
    import NetAppONTAPQuotas as my_module, main as my_main

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


SRR = rest_responses({
    # module specific responses
    'quota_record': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansible"
                    },
                    "files": {
                        "hard_limit": "100",
                        "soft_limit": "80"
                    },
                    "qtree": {
                        "id": "1",
                        "name": "qt1"
                    },
                    "space": {
                        "hard_limit": "1222800",
                        "soft_limit": "51200"
                    },
                    "type": "user",
                    "user_mapping": False,
                    "users": [{"name": "quota_user"}],
                    "uuid": "264a9e0b-2e03-11e9-a610-005056a7b72d",
                    "volume": {"name": "fv", "uuid": "264a9e0b-2e03-11e9-a610-005056a7b72da"},
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    },
                },
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansible"
                    },
                    "files": {
                        "hard_limit": "100",
                        "soft_limit": "80"
                    },
                    "qtree": {
                        "id": "1",
                        "name": "qt1"
                    },
                    "space": {
                        "hard_limit": "1222800",
                        "soft_limit": "51200"
                    },
                    "type": "user",
                    "user_mapping": False,
                    "users": [{"id": "757"}],
                    "uuid": "264a9e0b-2e03-11e9-a610-005056a7b72d",
                    "volume": {"name": "fv", "uuid": "264a9e0b-2e03-11e9-a610-005056a7b72da"},
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    },
                }
            ],
            "num_records": 1
        }, None
    ),
    'quota_record_0_empty_limits': (200, {"records": [{
        "svm": {"name": "ansible"},
        "files": {"hard_limit": 0},
        "qtree": {"id": "1", "name": "qt1"},
        "space": {"hard_limit": 0},
        "type": "user",
        "user_mapping": False,
        "users": [{"name": "quota_user"}],
        "uuid": "264a9e0b-2e03-11e9-a610-005056a7b72d",
        "volume": {"name": "fv", "uuid": "264a9e0b-2e03-11e9-a610-005056a7b72da"},
        "target": {"name": "20:05:00:50:56:b3:0c:fa"},
    }], "num_records": 1}, None),
    'quota_status': (
        200,
        {
            "records": [
                {
                    "quota": {"state": "off"}
                }
            ],
            "num_records": 1
        }, None
    ),
    'quota_on': (
        200,
        {
            "records": [
                {
                    "quota": {"state": "on"}
                }
            ],
            "num_records": 1
        }, None
    ),
    "no_record": (
        200,
        {"num_records": 0},
        None),
    "error_5308572": (409, None, {'code': 5308572, 'message': 'Expected delete error'}),
    "error_5308569": (409, None, {'code': 5308569, 'message': 'Expected delete error'}),
    "error_5308568": (409, None, {'code': 5308568, 'message': 'Expected create error'}),
    "error_5308571": (409, None, {'code': 5308571, 'message': 'Expected create error'}),
    "error_5308567": (409, None, {'code': 5308567, 'message': 'Expected modify error'}),
    'error_rest': (404, None, {"message": "temporarily locked from changes", "code": "4", "target": "uuid"}),
    "volume_uuid": (200, {"records": [{
        'uuid': 'sdgthfd'
    }], 'num_records': 1}, None),
    'job_info': (200, {
        "job": {
            "uuid": "d78811c1-aebc-11ec-b4de-005056b30cfa",
            "_links": {"self": {"href": "/api/cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa"}}
        }}, None),
    'job_not_found': (404, "", {"message": "entry doesn't exist", "code": "4", "target": "uuid"})
})


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
    'type': 'user',
    'use_rest': 'never'
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
        ('ZAPI', 'quota-list-entries-iter', ZRR['no_records']),
        ('ZAPI', 'quota-status', ZRR['quota_on']),
        ('ZAPI', 'quota-set-entry', ZRR['success']),
        ('ZAPI', 'quota-resize', ZRR['success']),
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
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
        ('ZAPI', 'quota-status', ZRR['quota_on']),
        ('ZAPI', 'quota-delete-entry', ZRR['success']),
        ('ZAPI', 'quota-resize', ZRR['success']),
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
        ('ZAPI', 'quota-list-entries-iter', ZRR['quota_policy']),
        ('ZAPI', 'quota-status', ZRR['quota_off']),
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
    assert my_obj.convert_to_kb_or_bytes('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == '10240'
    my_obj.parameters['disk_limit'] = '10'
    assert my_obj.convert_to_kb_or_bytes('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == '10'
    my_obj.parameters['disk_limit'] = '10tB'
    assert my_obj.convert_to_kb_or_bytes('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == str(10 * 1024 * 1024 * 1024)
    my_obj.parameters['disk_limit'] = ''
    assert not my_obj.convert_to_kb_or_bytes('disk_limit')
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
        ('ZAPI', 'quota-list-entries-iter', ZRR['no_records']),
        ('ZAPI', 'quota-status', ZRR['quota_on']),
        ('ZAPI', 'quota-set-entry', ZRR['success']),
    ])
    assert call_main(my_main, DEFAULT_ARGS)['changed']


ARGS_REST = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
    'volume': 'ansible',
    'vserver': 'ansible',
    'quota_target': 'quota_user',
    'qtree': 'qt1',
    'type': 'user'
}


def test_rest_error_get():
    '''Test error rest get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on getting quota rule info' in error


def test_rest_successful_create():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('POST', 'storage/quota/rules', SRR['empty_good']),
    ])
    assert create_and_apply(my_module, ARGS_REST)


def test_rest_successful_create_default_user_quota_rule():
    '''Test successful rest create default quota rule'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('POST', 'storage/quota/rules', SRR['empty_good']),
    ])
    module_args = {
        "quota_target": "",
        "type": "user"
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_successful_create_userid():
    '''Test successful rest create with users.id with idempotency check'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('POST', 'storage/quota/rules', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_status']),
    ])
    module_args = {
        "quota_target": "757",
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed'] is False


@patch('time.sleep')
def test_rest_successful_create_job_error(sleep):
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('POST', 'storage/quota/rules', SRR['job_info']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'storage/volumes', SRR['volume_uuid'])
    ])
    assert create_and_apply(my_module, ARGS_REST)
    print_warnings()
    assert_warning_was_raised('Ignoring job status, assuming success.')


def test_rest_error_create():
    '''Test error rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('POST', 'storage/quota/rules', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on creating quotas rule:' in error


def test_delete_rest():
    ''' Test delete with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('DELETE', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['empty_good']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_error_delete_rest():
    ''' Test error delete with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('DELETE', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent'
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on deleting quotas rule:' in error


def test_modify_files_limit_rest():
    ''' Test modify with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_on']),
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['empty_good']),
    ])
    module_args = {
        "file_limit": "122", "soft_file_limit": "90"
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_modify_space_limit_rest():
    ''' Test modify with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_on']),
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['empty_good']),
    ])
    module_args = {
        "disk_limit": "1024", "soft_disk_limit": "80"
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_modify_rest_error():
    ''' Test negative modify with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['generic_error']),
    ])
    module_args = {
        'perform_user_mapping': True
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on modifying quotas rule:' in error


@patch('time.sleep')
def test_modify_rest_temporary_locked_error(sleep):
    ''' Test negative modify with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        # wait for 60s if we get temporary locl error.
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_rest']),
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_rest']),
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['success']),

        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        # error persist even after 60s
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_rest']),
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_rest']),
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_rest']),

        # wait 60s in create for temporary locked error.
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('POST', 'storage/quota/rules', SRR['error_rest']),
        ('POST', 'storage/quota/rules', SRR['success']),
    ])
    module_args = {
        'perform_user_mapping': True
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed']
    assert 'Error on modifying quotas rule:' in create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed']


def test_rest_successful_create_idempotency():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record_0_empty_limits']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record_0_empty_limits']),
        ('GET', 'storage/volumes', SRR['quota_status'])
    ])
    assert create_and_apply(my_module, ARGS_REST)['changed'] is False
    module_args = {
        "disk_limit": "0", "soft_disk_limit": "-", "file_limit": 0, "soft_file_limit": "-"
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed'] is False
    module_args = {
        "disk_limit": "0", "soft_disk_limit": "-1", "file_limit": "0", "soft_file_limit": "-1"
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed'] is False


def test_rest_successful_delete_idempotency():
    '''Test successful rest delete'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_status']),
    ])
    module_args = {'use_rest': 'always', 'state': 'absent'}
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed'] is False


def test_modify_quota_status_rest():
    ''' Test modify quota status and error with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('PATCH', 'storage/volumes/264a9e0b-2e03-11e9-a610-005056a7b72da', SRR['empty_good'])
    ])
    module_args = {"set_quota_status": "on"}
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_error_convert_size_format_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
    ])
    module_args = {
        'disk_limit': '10MBi',
        'quota_target': ''
    }
    error = create_module(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert error.startswith('disk_limit input string is not a valid size format')
    module_args = {
        'soft_disk_limit': 'MBi',
        'quota_target': ''
    }
    error = create_module(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert error.startswith('soft_disk_limit input string is not a valid size format')
    module_args = {
        'soft_disk_limit': '10MB10',
        'quota_target': ''
    }
    error = create_module(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert error.startswith('soft_disk_limit input string is not a valid size format')


def test_convert_size_format_rest():
    module_args = {'disk_limit': '10MB'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.convert_to_kb_or_bytes('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == '10240'
    my_obj.parameters['disk_limit'] = '10'
    assert my_obj.convert_to_kb_or_bytes('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == '10'
    my_obj.parameters['disk_limit'] = '10tB'
    assert my_obj.convert_to_kb_or_bytes('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == str(10 * 1024 * 1024 * 1024)
    my_obj.parameters['disk_limit'] = ''
    assert not my_obj.convert_to_kb_or_bytes('disk_limit')
    print(my_obj.parameters)
    assert my_obj.parameters['disk_limit'] == ''


def test_warning_rest_delete_5308572():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('DELETE', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_5308572'])
    ])
    assert create_and_apply(my_module, ARGS_REST, {'state': 'absent'})['changed']
    # assert 'Error on deleting quotas rule:' in error
    msg = "Quota policy rule delete opertation succeeded. However the rule is still being enforced. To stop enforcing, "\
          "reinitialize(disable and enable again) the quota for volume ansible in SVM ansible."
    assert_warning_was_raised(msg)


@patch('time.sleep')
def test_no_warning_rest_delete_5308572(sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_on']),
        ('DELETE', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_5308572']),
        ('PATCH', 'storage/volumes/264a9e0b-2e03-11e9-a610-005056a7b72da', SRR['success']),
        ('PATCH', 'storage/volumes/264a9e0b-2e03-11e9-a610-005056a7b72da', SRR['success'])
    ])
    assert create_and_apply(my_module, ARGS_REST, {'state': 'absent', 'activate_quota_on_change': 'reinitialize'})['changed']
    assert_no_warnings()


def test_warning_rest_delete_5308569():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('DELETE', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_5308569'])
    ])
    assert create_and_apply(my_module, ARGS_REST, {'state': 'absent'})['changed']
    # assert 'Error on deleting quotas rule:' in error
    msg = "Quota policy rule delete opertation succeeded. However quota resize failed due to an internal error. To make quotas active, "\
          "reinitialize(disable and enable again) the quota for volume ansible in SVM ansible."
    assert_warning_was_raised(msg)


@patch('time.sleep')
def test_no_warning_rest_delete_5308569(sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_on']),
        ('DELETE', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_5308569']),
        ('PATCH', 'storage/volumes/264a9e0b-2e03-11e9-a610-005056a7b72da', SRR['success']),
        ('PATCH', 'storage/volumes/264a9e0b-2e03-11e9-a610-005056a7b72da', SRR['success'])
    ])
    assert create_and_apply(my_module, ARGS_REST, {'state': 'absent', 'activate_quota_on_change': 'reinitialize'})['changed']
    assert_no_warnings()


def test_warning_rest_create_5308568():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('POST', 'storage/quota/rules', SRR['error_5308568']),
        ('GET', 'storage/volumes', SRR['volume_uuid'])
    ])
    assert create_and_apply(my_module, ARGS_REST)['changed']
    msg = "Quota policy rule create opertation succeeded. However quota resize failed due to an internal error. To make quotas active, "\
          "reinitialize(disable and enable again) the quota for volume ansible in SVM ansible."
    assert_warning_was_raised(msg)


@patch('time.sleep')
def test_no_warning_rest_create_5308568(sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_on']),
        ('POST', 'storage/quota/rules', SRR['error_5308568']),
        ('GET', 'storage/volumes', SRR['volume_uuid']),
        ('PATCH', 'storage/volumes/sdgthfd', SRR['success']),
        ('PATCH', 'storage/volumes/sdgthfd', SRR['success'])
    ])
    assert create_and_apply(my_module, ARGS_REST, {'activate_quota_on_change': 'reinitialize'})['changed']
    assert_no_warnings()


def test_warning_rest_create_5308571():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_status']),
        ('POST', 'storage/quota/rules', SRR['error_5308571']),
        ('GET', 'storage/volumes', SRR['volume_uuid'])
    ])
    assert create_and_apply(my_module, ARGS_REST)['changed']
    msg = "Quota policy rule create opertation succeeded. but quota resize is skipped. To make quotas active, "\
          "reinitialize(disable and enable again) the quota for volume ansible in SVM ansible."
    assert_warning_was_raised(msg)


@patch('time.sleep')
def test_no_warning_rest_create_5308571(sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['quota_on']),
        ('POST', 'storage/quota/rules', SRR['error_5308568']),
        ('GET', 'storage/volumes', SRR['volume_uuid']),
        ('PATCH', 'storage/volumes/sdgthfd', SRR['success']),
        ('PATCH', 'storage/volumes/sdgthfd', SRR['success'])
    ])
    assert create_and_apply(my_module, ARGS_REST, {'activate_quota_on_change': 'reinitialize'})['changed']
    assert_no_warnings()


def test_warning_rest_modify_5308567():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_on']),
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_5308567']),
    ])
    module_args = {"soft_file_limit": "100"}
    assert create_and_apply(my_module, ARGS_REST, module_args)
    msg = "Quota policy rule modify opertation succeeded. However quota resize failed due to an internal error. To make quotas active, "\
          "reinitialize(disable and enable again) the quota for volume ansible in SVM ansible."
    assert_warning_was_raised(msg)


@patch('time.sleep')
def test_no_warning_rest_modify_5308567(sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/quota/rules', SRR['quota_record']),
        ('GET', 'storage/volumes', SRR['quota_on']),
        ('PATCH', 'storage/quota/rules/264a9e0b-2e03-11e9-a610-005056a7b72d', SRR['error_5308567']),
        ('PATCH', 'storage/volumes/264a9e0b-2e03-11e9-a610-005056a7b72da', SRR['success']),
        ('PATCH', 'storage/volumes/264a9e0b-2e03-11e9-a610-005056a7b72da', SRR['success'])
    ])
    module_args = {"soft_file_limit": "100", 'activate_quota_on_change': 'reinitialize'}
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed']
    assert_no_warnings()


def test_if_all_methods_catch_exception_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/quota/rules', SRR['generic_error']),
        ('GET', 'storage/volumes', SRR['generic_error']),
        ('GET', 'storage/volumes', SRR['generic_error']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('POST', 'storage/quota/rules', SRR['generic_error']),
        ('DELETE', 'storage/quota/rules/abdcdef', SRR['generic_error']),
        ('PATCH', 'storage/quota/rules/abdcdef', SRR['generic_error']),
        ('PATCH', 'storage/volumes/ghijklmn', SRR['generic_error']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),

    ])
    my_obj = create_module(my_module, ARGS_REST)
    my_obj.quota_uuid = 'abdcdef'
    my_obj.volume_uuid = 'ghijklmn'
    assert 'Error on getting quota rule info' in expect_and_capture_ansible_exception(my_obj.get_quotas_rest, 'fail')['msg']
    assert 'Error on getting quota status info' in expect_and_capture_ansible_exception(my_obj.get_quota_status_or_volume_id_rest, 'fail')['msg']
    assert 'Error on getting volume' in expect_and_capture_ansible_exception(my_obj.get_quota_status_or_volume_id_rest, 'fail', True)['msg']
    assert 'does not exist' in expect_and_capture_ansible_exception(my_obj.get_quota_status_or_volume_id_rest, 'fail', True)['msg']
    assert 'Error on creating quotas rule' in expect_and_capture_ansible_exception(my_obj.quota_entry_set_rest, 'fail')['msg']
    assert 'Error on deleting quotas rule' in expect_and_capture_ansible_exception(my_obj.quota_entry_delete_rest, 'fail')['msg']
    assert 'Error on modifying quotas rule' in expect_and_capture_ansible_exception(my_obj.quota_entry_modify_rest, 'fail', {})['msg']
    assert 'Error setting quota-on for ansible' in expect_and_capture_ansible_exception(my_obj.on_or_off_quota_rest, 'fail', 'quota-on')['msg']
    error = "Error: Qtree cannot be specified for a tree type rule"
    assert error in create_module(my_module, ARGS_REST, {'qtree': 'qtree1', 'type': 'tree'}, fail=True)['msg']
