# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_job_schedule '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_job_schedule \
    import NetAppONTAPJob as job_module, main as uut_main   # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'name': 'test_job',
    'job_minutes': [25],
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'never'
}


cron_info = {
    'num-records': 1,
    'attributes-list': {
        'job-schedule-cron-info': {
            'job-schedule-cluster': 'cluster1',
            'job-schedule-name': 'test_job',
            'job-schedule-cron-minute': {'cron-minute': 25}
        }
    }
}


multiple_cron_info = {
    'num-records': 1,
    'attributes-list': {
        'job-schedule-cron-info': {
            'job-schedule-cluster': 'cluster1',
            'job-schedule-name': 'test_job',
            'job-schedule-cron-minute': [
                {'cron-minute': '25'},
                {'cron-minute': '35'}
            ],
            'job-schedule-cron-month': [
                {'cron-month': '5'},
                {'cron-month': '10'}
            ]
        }
    }
}


multiple_cron_minutes_info = {
    'num-records': 1,
    'attributes-list': {
        'job-schedule-cron-info': {
            'job-schedule-cluster': 'cluster1',
            'job-schedule-name': 'test_job',
            'job-schedule-cron-minute': [{'cron-minute': str(x)} for x in range(60)],
            'job-schedule-cron-month': [
                {'cron-month': '5'},
                {'cron-month': '10'}
            ]
        }
    }
}


ZRR = zapi_responses({
    'cron_info': build_zapi_response(cron_info),
    'multiple_cron_info': build_zapi_response(multiple_cron_info),
    'multiple_cron_minutes_info': build_zapi_response(multiple_cron_minutes_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors
        with python 2.6, dictionaries are not ordered
    '''
    fragments = ["missing required arguments:", "hostname", "name"]
    error = create_module(job_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_get_nonexistent_job():
    ''' Test if get_job_schedule returns None for non-existent job '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['no_records'])
    ])
    job_obj = create_module(job_module, DEFAULT_ARGS)
    assert job_obj.get_job_schedule() is None


def test_get_existing_job():
    ''' Test if get_job_schedule retuns job details for existing job '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['cron_info'])
    ])
    job_obj = create_module(job_module, DEFAULT_ARGS)
    result = job_obj.get_job_schedule()
    assert result['name'] == DEFAULT_ARGS['name']
    assert result['job_minutes'] == DEFAULT_ARGS['job_minutes']


def test_get_existing_job_multiple_minutes():
    # sourcery skip: class-extract-method
    ''' Test if get_job_schedule retuns job details for existing job '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['multiple_cron_info'])
    ])
    job_obj = create_module(job_module, DEFAULT_ARGS)
    result = job_obj.get_job_schedule()
    assert result['name'] == DEFAULT_ARGS['name']
    assert result['job_minutes'] == [25, 35]
    assert result['job_months'] == [5, 10]


def test_get_existing_job_multiple_minutes_0_offset():
    ''' Test if get_job_schedule retuns job details for existing job '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['multiple_cron_info'])
    ])
    job_obj = create_module(job_module, DEFAULT_ARGS, {'month_offset': 0})
    result = job_obj.get_job_schedule()
    assert result['name'] == DEFAULT_ARGS['name']
    assert result['job_minutes'] == [25, 35]
    assert result['job_months'] == [5, 10]


def test_get_existing_job_multiple_minutes_1_offset():
    ''' Test if get_job_schedule retuns job details for existing job '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['multiple_cron_info'])
    ])
    job_obj = create_module(job_module, DEFAULT_ARGS, {'month_offset': 1})
    result = job_obj.get_job_schedule()
    assert result['name'] == DEFAULT_ARGS['name']
    assert result['job_minutes'] == [25, 35]
    assert result['job_months'] == [5 + 1, 10 + 1]


def test_create_error_missing_param():
    ''' Test if create throws an error if job_minutes is not specified'''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['no_records'])
    ])
    args = DEFAULT_ARGS.copy()
    del args['job_minutes']
    error = 'Error: missing required parameter job_minutes for create'
    assert error in create_and_apply(job_module, args, fail=True)['msg']


def test_successful_create():
    ''' Test successful create '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['no_records']),
        ('job-schedule-cron-create', ZRR['success'])
    ])
    assert create_and_apply(job_module, DEFAULT_ARGS)['changed']


def test_successful_create_0_offset():
    ''' Test successful create '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['no_records']),
        ('job-schedule-cron-create', ZRR['success'])
    ])
    args = {'month_offset': 0, 'job_months': [0, 8]}
    assert create_and_apply(job_module, DEFAULT_ARGS, args)['changed']


def test_successful_create_1_offset():
    ''' Test successful create '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['no_records']),
        ('job-schedule-cron-create', ZRR['success'])
    ])
    args = {'month_offset': 1, 'job_months': [1, 9], 'cluster': 'cluster1'}
    assert create_and_apply(job_module, DEFAULT_ARGS, args)['changed']


def test_create_idempotency():
    ''' Test create idempotency '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['cron_info'])
    ])
    assert not create_and_apply(job_module, DEFAULT_ARGS)['changed']


def test_successful_delete():
    ''' Test delete existing job '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['cron_info']),
        ('job-schedule-cron-destroy', ZRR['success'])
    ])
    assert create_and_apply(job_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_delete_idempotency():
    ''' Test delete idempotency '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['no_records'])
    ])
    assert not create_and_apply(job_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_successful_modify():
    ''' Test successful modify job_minutes '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['cron_info']),
        ('job-schedule-cron-modify', ZRR['success'])
    ])
    assert create_and_apply(job_module, DEFAULT_ARGS, {'job_minutes': '20'})['changed']


def test_modify_idempotency():
    ''' Test modify idempotency '''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['cron_info'])
    ])
    assert not create_and_apply(job_module, DEFAULT_ARGS)['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_negative_no_netapp_lib(mock_has):
    mock_has.return_value = False
    error = 'the python NetApp-Lib module is required'
    assert error in create_module(job_module, DEFAULT_ARGS, fail=True)['msg']


def test_zapi_get_all_minutes():
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['multiple_cron_minutes_info'])
    ])
    job_obj = create_module(job_module, DEFAULT_ARGS)
    schedule = job_obj.get_job_schedule()
    assert schedule
    assert 'job_minutes' in schedule
    assert schedule['job_minutes'] == [-1]


def test_if_all_methods_catch_exception_zapi():
    ''' test error zapi - get/create/modify/delete'''
    register_responses([
        ('job-schedule-cron-get-iter', ZRR['error']),
        ('job-schedule-cron-create', ZRR['error']),
        ('job-schedule-cron-modify', ZRR['error']),
        ('job-schedule-cron-destroy', ZRR['error'])
    ])
    job_obj = create_module(job_module, DEFAULT_ARGS)

    assert 'Error fetching job schedule' in expect_and_capture_ansible_exception(job_obj.get_job_schedule, 'fail')['msg']
    assert 'Error creating job schedule' in expect_and_capture_ansible_exception(job_obj.create_job_schedule, 'fail')['msg']
    assert 'Error modifying job schedule' in expect_and_capture_ansible_exception(job_obj.modify_job_schedule, 'fail', {}, {})['msg']
    assert 'Error deleting job schedule' in expect_and_capture_ansible_exception(job_obj.delete_job_schedule, 'fail')['msg']


SRR = rest_responses({
    'get_schedule': (200, {"records": [
        {
            "uuid": "010df156-e0a9-11e9-9f70-005056b3df08",
            "name": "test_job",
            "cron": {
                "minutes": [25],
                "hours": [0],
                "weekdays": [0],
                "months": [5, 6]
            }
        }
    ], "num_records": 1}, None),
    'get_all_minutes': (200, {"records": [
        {
            "uuid": "010df156-e0a9-11e9-9f70-005056b3df08",
            "name": "test_job",
            "cron": {
                "minutes": range(60),
                "hours": [0],
                "weekdays": [0],
                "months": [5, 6]
            }
        }
    ], "num_records": 1}, None)
})


DEFAULT_ARGS_REST = {
    'name': 'test_job',
    'job_minutes': [25],
    'job_hours': [0],
    'job_days_of_week': [0],
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always'
}


def test_rest_successful_create():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['zero_records']),
        ('POST', 'cluster/schedules', SRR['success']),
    ])
    assert create_and_apply(job_module, DEFAULT_ARGS_REST)['changed']


def test_rest_create_idempotency():
    '''Test rest create idempotency'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['get_schedule'])
    ])
    assert not create_and_apply(job_module, DEFAULT_ARGS_REST)['changed']


def test_rest_get_0_offset():
    '''Test rest get using month offset'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['get_schedule'])
    ])
    job_obj = create_module(job_module, DEFAULT_ARGS_REST, {'month_offset': 0})
    record = job_obj.get_job_schedule_rest()
    assert record
    assert record['job_months'] == [x - 1 for x in SRR['get_schedule'][1]['records'][0]['cron']['months']]


def test_rest_get_1_offset():
    '''Test rest get using month offset'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['get_schedule'])
    ])
    job_obj = create_module(job_module, DEFAULT_ARGS_REST, {'month_offset': 1})
    record = job_obj.get_job_schedule_rest()
    assert record
    assert record['job_months'] == SRR['get_schedule'][1]['records'][0]['cron']['months']


def test_rest_create_all_minutes():
    '''Test rest create using month offset'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['zero_records']),
        ('POST', 'cluster/schedules', SRR['success'])
    ])
    assert create_and_apply(job_module, DEFAULT_ARGS_REST, {'job_minutes': [-1]})['changed']


def test_rest_create_0_offset():
    '''Test rest create using month offset'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['zero_records']),
        ('POST', 'cluster/schedules', SRR['success'])
    ])
    args = {'month_offset': 0, 'job_months': [0, 8]}
    assert create_and_apply(job_module, DEFAULT_ARGS_REST, args)['changed']


def test_rest_create_1_offset():
    '''Test rest create using month offset'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['zero_records']),
        ('POST', 'cluster/schedules', SRR['success'])
    ])
    args = {'month_offset': 1, 'job_months': [1, 9]}
    assert create_and_apply(job_module, DEFAULT_ARGS_REST, args)['changed']


def test_rest_modify_0_offset():
    '''Test rest modify using month offset'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['get_schedule']),
        ('PATCH', 'cluster/schedules/010df156-e0a9-11e9-9f70-005056b3df08', SRR['success'])
    ])
    args = {'month_offset': 0, 'job_months': [0, 8]}
    assert create_and_apply(job_module, DEFAULT_ARGS_REST, args)['changed']


def test_rest_modify_1_offset():
    '''Test rest modify using month offset'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['get_schedule']),
        ('PATCH', 'cluster/schedules/010df156-e0a9-11e9-9f70-005056b3df08', SRR['success'])
    ])
    args = {'month_offset': 1, 'job_months': [1, 9], 'cluster': 'cluster1'}
    assert create_and_apply(job_module, DEFAULT_ARGS_REST, args)['changed']


def test_negative_month_of_0():
    '''Test rest modify using month offset'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    args = {'month_offset': 1, 'job_months': [0, 9]}
    error = 'Error: 0 is not a valid value in months if month_offset is set to 1'
    assert error in create_module(job_module, DEFAULT_ARGS_REST, args, fail=True)['msg']


def test_rest_get_all_minutes():
    '''Test rest modify using month offset'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['get_all_minutes'])
    ])
    args = {'month_offset': 1, 'job_months': [1, 9]}
    job_obj = create_module(job_module, DEFAULT_ARGS_REST, args)
    schedule = job_obj.get_job_schedule()
    assert schedule
    assert 'job_minutes' in schedule
    assert schedule['job_minutes'] == [-1]


def test_if_all_methods_catch_exception_rest():
    ''' test error zapi - get/create/modify/delete'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster/schedules', SRR['generic_error']),
        ('POST', 'cluster/schedules', SRR['generic_error']),
        ('PATCH', 'cluster/schedules/abcd', SRR['generic_error']),
        ('DELETE', 'cluster/schedules/abcd', SRR['generic_error'])
    ])
    job_obj = create_module(job_module, DEFAULT_ARGS_REST)
    job_obj.uuid = 'abcd'
    assert 'Error fetching job schedule' in expect_and_capture_ansible_exception(job_obj.get_job_schedule, 'fail')['msg']
    assert 'Error creating job schedule' in expect_and_capture_ansible_exception(job_obj.create_job_schedule, 'fail')['msg']
    assert 'Error modifying job schedule' in expect_and_capture_ansible_exception(job_obj.modify_job_schedule, 'fail', {}, {})['msg']
    assert 'Error deleting job schedule' in expect_and_capture_ansible_exception(job_obj.delete_job_schedule, 'fail')['msg']
