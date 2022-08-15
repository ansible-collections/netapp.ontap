# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP FlexCache Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, build_zapi_error, zapi_error_message, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_warning_was_raised, call_main, create_module, expect_and_capture_ansible_exception, patch_ansible, print_warnings

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_flexcache import NetAppONTAPFlexCache as my_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


flexcache_info = {
    'vserver': 'vserver',
    'origin-vserver': 'ovserver',
    'origin-volume': 'ovolume',
    'origin-cluster': 'ocluster',
    'volume': 'flexcache_volume',
}

flexcache_get_info = {
    'attributes-list': [{
        'flexcache-info': flexcache_info
    }]
}

flexcache_get_info_double = {
    'attributes-list': [
        {
            'flexcache-info': flexcache_info
        },
        {
            'flexcache-info': flexcache_info
        }
    ]
}


def results_info(status):
    return {
        'result-status': status,
        'result-jobid': 'job12345',
    }


def job_info(state, error):
    return {
        'num-records': 1,
        'attributes': {
            'job-info': {
                'job-state': state,
                'job-progress': 'progress',
                'job-completion': error,
            }
        }
    }


ZRR = zapi_responses({
    'flexcache_get_info': build_zapi_response(flexcache_get_info, 1),
    'flexcache_get_info_double': build_zapi_response(flexcache_get_info_double, 2),
    'job_running': build_zapi_response(job_info('running', None)),
    'job_success': build_zapi_response(job_info('success', None)),
    'job_error': build_zapi_response(job_info('failure', 'failure')),
    'job_error_no_completion': build_zapi_response(job_info('failure', None)),
    'job_other': build_zapi_response(job_info('other', 'other')),
    'result_async': build_zapi_response(results_info('in_progress')),
    'result_error': build_zapi_response(results_info('whatever')),
    'error_160': build_zapi_error(160, 'Volume volume on Vserver ansibleSVM must be unmounted before being taken offline or restricted'),
    'error_13001': build_zapi_error(13001, 'Volume volume in Vserver ansibleSVM must be offline to be deleted'),
    'error_15661': build_zapi_error(15661, 'Job not found'),
    'error_size': build_zapi_error('size', 'Size "50MB" ("52428800B") is too small.  Minimum size is "80MB" ("83886080B")'),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'volume': 'flexcache_volume',
    'vserver': 'vserver',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never'
    }
    error = 'missing required arguments:'
    assert error in call_main(my_main, {}, module_args, fail=True)['msg']


def test_missing_parameters():
    ''' fail if origin volume and origin verser are missing '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    error = 'Missing parameters:'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_missing_parameter():
    ''' fail if origin verser parameter is missing '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
        'origin_volume': 'origin_volume',
    }
    error = 'Missing parameter: origin_vserver'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_get_flexcache():
    ''' get flexcache info '''
    register_responses([
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'origin_volume': 'origin_volume',
        'origin_cluster': 'origin_cluster',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    info = my_obj.flexcache_get()
    assert info
    assert 'origin_cluster' in info


def test_get_flexcache_double():
    ''' get flexcache info returns 2 entries! '''
    register_responses([
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info_double']),
    ])
    module_args = {
        'use_rest': 'never',
        'origin_volume': 'origin_volume',

    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = 'Error fetching FlexCache info: Multiple records found for %s:' % DEFAULT_ARGS['volume']
    assert error in expect_and_capture_ansible_exception(my_obj.flexcache_get, 'fail')['msg']


def test_create_flexcache():
    ''' create flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
        ('ZAPI', 'flexcache-create-async', ZRR['result_async']),
        ('ZAPI', 'job-get', ZRR['job_success']),
    ])
    module_args = {
        'use_rest': 'never',
        'size': '90',       # 80MB minimum
        'size_unit': 'mb',  # 80MB minimum
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_flexcach_no_wait():
    ''' create flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
        ('ZAPI', 'flexcache-create-async', ZRR['result_async']),
    ])
    module_args = {
        'use_rest': 'never',
        'size': '90',       # 80MB minimum
        'size_unit': 'mb',  # 80MB minimum
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
        'time_out': 0
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_create_flexcache():
    ''' create flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
        ('ZAPI', 'flexcache-create-async', ZRR['result_error']),
        # 2nd run
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
        ('ZAPI', 'flexcache-create-async', ZRR['result_async']),
        ('ZAPI', 'job-get', ZRR['error']),
        # 3rd run
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
        ('ZAPI', 'flexcache-create-async', ZRR['result_async']),
        ('ZAPI', 'job-get', ZRR['job_error']),
    ])
    module_args = {
        'use_rest': 'never',
        'size': '90',       # 80MB minimum
        'size_unit': 'mb',  # 80MB minimum
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
    }
    error = 'Unexpected error when creating flexcache: results is:'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    error = zapi_error_message('Error fetching job info')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    error = 'Error when creating flexcache'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_create_flexcache_idempotent():
    ''' create flexcache - already exists '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'aggr_list': 'aggr1',
        'origin_volume': 'ovolume',
        'origin_vserver': 'ovserver',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_flexcache_autoprovision():
    ''' create flexcache with autoprovision'''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
        ('ZAPI', 'flexcache-create-async', ZRR['result_async']),
        ('ZAPI', 'job-get', ZRR['job_success']),
    ])
    module_args = {
        'use_rest': 'never',
        'size': '90',       # 80MB minimum
        'size_unit': 'mb',  # 80MB minimum
        'auto_provision_as': 'flexgroup',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_flexcache_autoprovision_idempotent():
    ''' create flexcache with autoprovision - already exists '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'origin_volume': 'ovolume',
        'origin_vserver': 'ovserver',
        'auto_provision_as': 'flexgroup',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_flexcache_multiplier():
    ''' create flexcache with aggregate multiplier'''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
        ('ZAPI', 'flexcache-create-async', ZRR['result_async']),
        ('ZAPI', 'job-get', ZRR['job_success']),
    ])
    module_args = {
        'use_rest': 'never',
        'size': '90',       # 80MB minimum
        'size_unit': 'mb',  # 80MB minimum
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
        'aggr_list_multiplier': 2,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_flexcache_multiplier_idempotent():
    ''' create flexcache with aggregate multiplier - already exists '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'aggr_list': 'aggr1',
        'origin_volume': 'ovolume',
        'origin_vserver': 'ovserver',
        'aggr_list_multiplier': 2,
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete_flexcache_exists_no_force():
    ''' delete flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
        ('ZAPI', 'flexcache-destroy-async', ZRR['error_13001']),
    ])
    module_args = {
        'use_rest': 'never',
        'state': 'absent'
    }
    error = zapi_error_message('Error deleting FlexCache', 13001, 'Volume volume in Vserver ansibleSVM must be offline to be deleted')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_delete_flexcache_exists_with_force():
    ''' delete flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
        ('ZAPI', 'volume-offline', ZRR['success']),
        ('ZAPI', 'flexcache-destroy-async', ZRR['result_async']),
        ('ZAPI', 'job-get', ZRR['job_success']),
    ])
    module_args = {
        'use_rest': 'never',
        'force_offline': 'true',
        'state': 'absent'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete_flexcache_exists_with_force_no_wait():
    ''' delete flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
        ('ZAPI', 'volume-offline', ZRR['success']),
        ('ZAPI', 'flexcache-destroy-async', ZRR['result_async']),
    ])
    module_args = {
        'use_rest': 'never',
        'force_offline': 'true',
        'time_out': 0,
        'state': 'absent'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete_flexcache_exists_junctionpath_no_force():
    ''' delete flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
        ('ZAPI', 'volume-offline', ZRR['success']),
        ('ZAPI', 'flexcache-destroy-async', ZRR['error_160']),
    ])
    module_args = {
        'use_rest': 'never',
        'force_offline': 'true',
        'junction_path': 'jpath',
        'state': 'absent'
    }
    error = zapi_error_message('Error deleting FlexCache', 160,
                               'Volume volume on Vserver ansibleSVM must be unmounted before being taken offline or restricted')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_delete_flexcache_exists_junctionpath_with_force():
    ''' delete flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
        ('ZAPI', 'volume-unmount', ZRR['success']),
        ('ZAPI', 'volume-offline', ZRR['success']),
        ('ZAPI', 'flexcache-destroy-async', ZRR['result_async']),
        ('ZAPI', 'job-get', ZRR['job_success']),
    ])
    module_args = {
        'use_rest': 'never',
        'force_offline': 'true',
        'junction_path': 'jpath',
        'force_unmount': 'true',
        'state': 'absent'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete_flexcache_not_exist():
    ''' delete flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
        'state': 'absent'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_delete_flexcache_exists_with_force():
    ''' delete flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
        ('ZAPI', 'volume-offline', ZRR['success']),
        ('ZAPI', 'flexcache-destroy-async', ZRR['result_error']),
        # 2nd run
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
        ('ZAPI', 'volume-offline', ZRR['success']),
        ('ZAPI', 'flexcache-destroy-async', ZRR['result_async']),
        ('ZAPI', 'job-get', ZRR['error']),
        # 3rd run
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['flexcache_get_info']),
        ('ZAPI', 'volume-offline', ZRR['success']),
        ('ZAPI', 'flexcache-destroy-async', ZRR['result_async']),
        ('ZAPI', 'job-get', ZRR['job_error']),
    ])
    module_args = {
        'use_rest': 'never',
        'force_offline': 'true',
        'state': 'absent'
    }
    error = 'Unexpected error when deleting flexcache: results is:'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    error = zapi_error_message('Error fetching job info')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    error = 'Error when deleting flexcache'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_create_flexcache_size_error():
    ''' create flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
        ('ZAPI', 'flexcache-create-async', ZRR['error_size']),
    ])
    module_args = {
        'use_rest': 'never',
        'size': '50',       # 80MB minimum
        'size_unit': 'mb',  # 80MB minimum
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
    }
    error = zapi_error_message('Error creating FlexCache', 'size', 'Size "50MB" ("52428800B") is too small.  Minimum size is "80MB" ("83886080B")')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_create_flexcache_time_out(dont_sleep):
    ''' create flexcache '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'flexcache-get-iter', ZRR['no_records']),
        ('ZAPI', 'flexcache-create-async', ZRR['result_async']),
        ('ZAPI', 'job-get', ZRR['job_running']),
    ])
    module_args = {
        'use_rest': 'never',
        'size': '50',       # 80MB minimum
        'size_unit': 'mb',  # 80MB minimum
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
        'time_out': '2',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = 'Error when creating flexcache: job completion exceeded expected timer of: 2 seconds'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_error_zapi():
    ''' error in ZAPI calls '''
    register_responses([
        ('ZAPI', 'flexcache-get-iter', ZRR['error']),
        ('ZAPI', 'volume-offline', ZRR['error']),
        ('ZAPI', 'volume-unmount', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = zapi_error_message('Error fetching FlexCache info')
    assert error in expect_and_capture_ansible_exception(my_obj.flexcache_get, 'fail')['msg']
    error = zapi_error_message('Error offlining FlexCache volume')
    assert error in expect_and_capture_ansible_exception(my_obj.volume_offline, 'fail', None)['msg']
    error = zapi_error_message('Error unmounting FlexCache volume')
    assert error in expect_and_capture_ansible_exception(my_obj.volume_unmount, 'fail', None)['msg']


def test_check_job_status():
    ''' check_job_status '''
    register_responses([
        # job not found
        ('ZAPI', 'job-get', ZRR['error_15661']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'job-get', ZRR['error_15661']),
        # cserver job not found
        ('ZAPI', 'job-get', ZRR['error_15661']),
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'job-get', ZRR['error_15661']),
        # missing job-completion
        ('ZAPI', 'job-get', ZRR['job_error_no_completion']),
        # bad status
        ('ZAPI', 'job-get', ZRR['job_other']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    # error = zapi_error_message('Error fetching FlexCache info')
    error = 'cannot locate job with id: 1'
    assert error in my_obj.check_job_status('1')
    assert error in my_obj.check_job_status('1')
    assert 'progress' in my_obj.check_job_status('1')
    error = 'Unexpected job status in:'
    assert error in expect_and_capture_ansible_exception(my_obj.check_job_status, 'fail', '1')['msg']


# REST API canned responses when mocking send_request
SRR = rest_responses({
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'one_flexcache_record': (200, dict(records=[
        dict(uuid='a1b2c3',
             name='flexcache_volume',
             svm=dict(name='vserver'),
             )
    ], num_records=1), None),
    'one_flexcache_record_with_path': (200, dict(records=[
        dict(uuid='a1b2c3',
             name='flexcache_volume',
             svm=dict(name='vserver'),
             path='path'
             )
    ], num_records=1), None),
})


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_netapp_lib_error(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    module_args = {
        "use_rest": "never"
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_missing_arguments():
    ''' create flexcache '''
    register_responses([

    ])
    args = dict(DEFAULT_ARGS)
    del args['hostname']
    module_args = {
        'use_rest': 'always',
    }
    error = 'missing required arguments: hostname'
    assert error in call_main(my_main, args, module_args, fail=True)['msg']


def test_rest_create():
    ''' create flexcache '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['zero_record']),
        ('POST', 'storage/flexcache/flexcaches', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        'size': '50',       # 80MB minimum
        'size_unit': 'mb',  # 80MB minimum
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
        'origin_cluster': 'ocluster',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_create_no_action():
    ''' create flexcache idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record']),
    ])
    module_args = {
        'use_rest': 'always',
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_delete_no_action():
    ''' delete flexcache '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['zero_record']),
    ])
    module_args = {
        'use_rest': 'always',
        'state': 'absent'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_delete():
    ''' delete flexcache '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record']),
        ('DELETE', 'storage/flexcache/flexcaches/a1b2c3', SRR['empty_good']),
    ])
    module_args = {
        'use_rest': 'always',
        'state': 'absent'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_delete_with_force():
    ''' delete flexcache, since there is no path, unmount is not called '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record']),
        ('DELETE', 'storage/flexcache/flexcaches/a1b2c3', SRR['empty_good']),
    ])
    module_args = {
        'use_rest': 'always',
        'force_unmount': True,
        'state': 'absent'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_delete_with_force_and_path():
    ''' delete flexcache with unmount '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record_with_path']),
        ('PATCH', 'storage/volumes/a1b2c3', SRR['empty_good']),
        ('DELETE', 'storage/flexcache/flexcaches/a1b2c3', SRR['empty_good']),
    ])
    module_args = {
        'use_rest': 'always',
        'force_unmount': True,
        'state': 'absent'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_delete_with_force2_and_path():
    ''' delete flexcache  with unmount and offline'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record_with_path']),
        ('PATCH', 'storage/volumes/a1b2c3', SRR['empty_good']),
        ('PATCH', 'storage/volumes/a1b2c3', SRR['empty_good']),
        ('DELETE', 'storage/flexcache/flexcaches/a1b2c3', SRR['empty_good']),
    ])
    module_args = {
        'use_rest': 'always',
        'force_offline': True,
        'force_unmount': True,
        'state': 'absent'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_modify_prepopulate_no_action():
    ''' modify flexcache '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record']),
    ])
    module_args = {
        'use_rest': 'always',
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
        'prepopulate': {
            'dir_paths': ['/'],
            'force_prepopulate_if_already_created': False
        }
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_modify_prepopulate():
    ''' modify flexcache '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record']),
        ('PATCH', 'storage/flexcache/flexcaches/a1b2c3', SRR['empty_good']),
    ])
    module_args = {
        'use_rest': 'always',
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
        'prepopulate': {
            'dir_paths': ['/'],
            'force_prepopulate_if_already_created': True
        }
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_modify_prepopulate_default():
    ''' modify flexcache '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record']),
        ('PATCH', 'storage/flexcache/flexcaches/a1b2c3', SRR['empty_good']),
    ])
    module_args = {
        'use_rest': 'always',
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
        'prepopulate': {
            'dir_paths': ['/'],
        }
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_modify_prepopulate_and_mount():
    ''' modify flexcache '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record']),
        ('PATCH', 'storage/volumes/a1b2c3', SRR['empty_good']),
        ('PATCH', 'storage/flexcache/flexcaches/a1b2c3', SRR['empty_good']),
    ])
    module_args = {
        'use_rest': 'always',
        'aggr_list': 'aggr1',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
        'prepopulate': {
            'dir_paths': ['/'],
        },
        'path': '/mount_path'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_modify():
    ''' create flexcache idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record']),
    ])
    module_args = {
        'use_rest': 'always',
        'aggr_list': 'aggr1',
        'volume': 'flexcache_volume2',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
    }
    error = 'FlexCache properties cannot be modified by this module.  modify:'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_warn_prepopulate():
    ''' create flexcache idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/flexcache/flexcaches', SRR['one_flexcache_record']),
        ('PATCH', 'storage/volumes/a1b2c3', SRR['success']),
        ('PATCH', 'storage/flexcache/flexcaches/a1b2c3', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        'aggr_list': 'aggr1',
        'volume': 'flexcache_volume',
        'origin_volume': 'fc_vol_origin',
        'origin_vserver': 'ansibleSVM',
        'prepopulate': {
            'dir_paths': ['/'],
            'force_prepopulate_if_already_created': True
        },
        'junction_path': ''
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised('na_ontap_flexcache is not idempotent when prepopulate is present and force_prepopulate_if_already_created=true')
    assert_warning_was_raised('prepopulate requires the FlexCache volume to be mounted')


def test_error_missing_uuid():
    module_args = {
        'use_rest': 'akway',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    current = {}
    error_template = 'Error in %s: Error, no uuid in current: {}'
    error = error_template % 'rest_offline_volume'
    assert error in expect_and_capture_ansible_exception(my_obj.rest_offline_volume, 'fail', current)['msg']
    error = error_template % 'rest_mount_volume'
    assert error in expect_and_capture_ansible_exception(my_obj.rest_mount_volume, 'fail', current, 'path')['msg']
    error = error_template % 'flexcache_rest_delete'
    assert error in expect_and_capture_ansible_exception(my_obj.flexcache_rest_delete, 'fail', current)['msg']


def test_prepopulate_option_checks():
    ''' create flexcache idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'use_rest': 'always',
        'prepopulate': {
            'dir_paths': ['/'],
            'force_prepopulate_if_already_created': True,
            'exclude_dir_paths': ['/']
        },
    }
    error = 'Error: using prepopulate requires ONTAP 9.8 or later and REST must be enabled - ONTAP version: 9.7.0.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    error = 'Error: using prepopulate: exclude_dir_paths requires ONTAP 9.9 or later and REST must be enabled - ONTAP version: 9.8.0.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
