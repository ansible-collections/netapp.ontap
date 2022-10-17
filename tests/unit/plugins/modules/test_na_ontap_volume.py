# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    assert_warning_was_raised, call_main, create_module, create_and_apply, expect_and_capture_ansible_exception, patch_ansible, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import \
    get_mock_record, patch_request_and_invoke, print_requests, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_error, build_zapi_response, zapi_error_message, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume \
    import NetAppOntapVolume as vol_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
}

MOCK_VOL = {
    'name': 'test_vol',
    'aggregate': 'test_aggr',
    'junction_path': '/test',
    'vserver': 'test_vserver',
    'size': 20971520,
    'unix_permissions': '755',
    'user_id': 100,
    'group_id': 1000,
    'snapshot_policy': 'default',
    'qos_policy_group': 'performance',
    'qos_adaptive_policy_group': 'performance',
    'percent_snapshot_space': 60,
    'language': 'en',
    'vserver_dr_protection': 'unprotected',
    'uuid': 'UUID'
}


def volume_info(style, vol_details=None, remove_keys=None, encrypt='false'):
    if not vol_details:
        vol_details = MOCK_VOL
    info = copy.deepcopy({
        'num-records': 1,
        'attributes-list': {
            'volume-attributes': {
                'encrypt': encrypt,
                'volume-id-attributes': {
                    'aggr-list': vol_details['aggregate'],
                    'containing-aggregate-name': vol_details['aggregate'],
                    'flexgroup-uuid': 'uuid',
                    'junction-path': vol_details['junction_path'],
                    'style-extended': style,
                    'type': 'rw'
                },
                'volume-comp-aggr-attributes': {
                    'tiering-policy': 'snapshot-only'
                },
                'volume-language-attributes': {
                    'language-code': 'en'
                },
                'volume-export-attributes': {
                    'policy': 'default'
                },
                'volume-performance-attributes': {
                    'is-atime-update-enabled': 'true'
                },
                'volume-state-attributes': {
                    'state': "online",
                    'is-nvfail-enabled': 'true'
                },
                'volume-inode-attributes': {
                    'files-total': '2000',
                },
                'volume-space-attributes': {
                    'space-guarantee': 'none',
                    'size': vol_details['size'],
                    'percentage-snapshot-reserve': vol_details['percent_snapshot_space'],
                    'space-slo': 'thick'
                },
                'volume-snapshot-attributes': {
                    'snapshot-policy': vol_details['snapshot_policy']
                },
                'volume-security-attributes': {
                    'volume-security-unix-attributes': {
                        'permissions': vol_details['unix_permissions'],
                        'group-id': vol_details['group_id'],
                        'user-id': vol_details['user_id']
                    },
                    'style': 'unix',
                },
                'volume-vserver-dr-protection-attributes': {
                    'vserver-dr-protection': vol_details['vserver_dr_protection'],
                },
                'volume-qos-attributes': {
                    'policy-group-name': vol_details['qos_policy_group'],
                    'adaptive-policy-group-name': vol_details['qos_adaptive_policy_group']
                },
                'volume-snapshot-autodelete-attributes': {
                    'commitment': 'try',
                    'is-autodelete-enabled': 'true',
                }
            }
        }
    })
    if remove_keys:
        for key in remove_keys:
            if key == 'is_online':
                del info['attributes-list']['volume-attributes']['volume-state-attributes']['state']
            else:
                raise KeyError('unexpected key %s' % key)
    return info


def vol_encryption_conversion_status(status):
    return {
        'num-records': 1,
        'attributes-list': {
            'volume-encryption-conversion-info': {
                'status': status
            }
        }
    }


def vol_move_status(status):
    return {
        'num-records': 1,
        'attributes-list': {
            'volume-move-info': {
                'state': status,
                'details': 'some info'
            }
        }
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


def results_info(status):
    return {
        'result-status': status,
        'result-jobid': 'job12345',
    }


def modify_async_results_info(status, error=None):
    list_name = 'failure-list' if error else 'success-list'
    info = {
        list_name: {
            'volume-modify-iter-async-info': {
                'status': status,
                'jobid': '1234'
            }
        }
    }
    if error:
        info[list_name]['volume-modify-iter-async-info']['error-message'] = error
    return info


def sis_info():
    return {
        'num-records': 1,
        'attributes-list': {
            'sis-status-info': {
                'policy': 'test',
                'is-compression-enabled': 'true',
                'sis-status-completion': 'false',
            }
        }
    }


ZRR = zapi_responses({
    'get_flexgroup': build_zapi_response(volume_info('flexgroup')),
    'get_flexvol': build_zapi_response(volume_info('flexvol')),
    'get_flexvol_encrypted': build_zapi_response(volume_info('flexvol', encrypt='true')),
    'get_flexvol_no_online_key': build_zapi_response(volume_info('flexvol', remove_keys=['is_online'])),
    'job_failure': build_zapi_response(job_info('failure', 'failure')),
    'job_other': build_zapi_response(job_info('other', 'other_error')),
    'job_running': build_zapi_response(job_info('running', None)),
    'job_success': build_zapi_response(job_info('success', None)),
    'job_time_out': build_zapi_response(job_info('running', 'time_out')),
    'job_no_completion': build_zapi_response(job_info('failure', None)),
    'async_results': build_zapi_response(results_info('in_progress')),
    'failed_results': build_zapi_response(results_info('failed')),
    'modify_async_result_success': build_zapi_response(modify_async_results_info('in_progress')),
    'modify_async_result_failure': build_zapi_response(modify_async_results_info('failure', 'error_in_modify')),
    'vol_encryption_conversion_status_running': build_zapi_response(vol_encryption_conversion_status('running')),
    'vol_encryption_conversion_status_idle': build_zapi_response(vol_encryption_conversion_status('Not currently going on.')),
    'vol_encryption_conversion_status_error': build_zapi_response(vol_encryption_conversion_status('other')),
    'vol_move_status_running': build_zapi_response(vol_move_status('healthy')),
    'vol_move_status_idle': build_zapi_response(vol_move_status('done')),
    'vol_move_status_error': build_zapi_response(vol_move_status('failed')),
    'insufficient_privileges': build_zapi_error(12346, 'Insufficient privileges: user USERID does not have read access to this resource'),
    'get_sis_info': build_zapi_response(sis_info()),
    'error_15661': build_zapi_error(15661, 'force job not found error'),
    'error_tiering_94': build_zapi_error(94, 'volume-comp-aggr-attributes')
})


MINIMUM_ARGS = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'name': 'test_vol',
    'vserver': 'test_vserver',
    'use_rest': 'never'
}


DEFAULT_ARGS = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'name': 'test_vol',
    'vserver': 'test_vserver',
    'policy': 'default',
    'language': 'en',
    'is_online': True,
    'unix_permissions': '---rwxr-xr-x',
    'user_id': 100,
    'group_id': 1000,
    'snapshot_policy': 'default',
    'qos_policy_group': 'performance',
    'qos_adaptive_policy_group': 'performance',
    'size': 20,
    'size_unit': 'mb',
    'junction_path': '/test',
    'percent_snapshot_space': 60,
    'type': 'rw',
    'nvfail_enabled': True,
    'space_slo': 'thick',
    'use_rest': 'never'
}


ZAPI_ERROR = 'NetApp API failed. Reason - 12345:synthetic error for UT purpose'


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    error = create_module(vol_module, {}, fail=True)
    print('Info: %s' % error['msg'])
    assert 'missing required arguments:' in error['msg']


def test_get_nonexistent_volume():
    ''' Test if get_volume returns None for non-existent volume '''
    register_responses([
        ('ZAPI', 'volume-get-iter', ZRR['success']),
    ])
    assert create_module(vol_module, DEFAULT_ARGS).get_volume() is None


def test_get_error():
    ''' Test if get_volume handles error '''
    register_responses([
        ('ZAPI', 'volume-get-iter', ZRR['error']),
    ])
    error = 'Error fetching volume test_vol : %s' % ZAPI_ERROR
    assert expect_and_capture_ansible_exception(create_module(vol_module, DEFAULT_ARGS).get_volume, 'fail')['msg'] == error


def test_get_existing_volume():
    ''' Test if get_volume returns details for existing volume '''
    register_responses([
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
    ])
    volume_info = create_module(vol_module, DEFAULT_ARGS).get_volume()
    assert volume_info is not None
    assert 'aggregate_name' in volume_info


def test_create_error_missing_param():
    ''' Test if create throws an error if aggregate_name is not specified'''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'size': 20,
        'encrypt': True,
    }
    msg = 'Error provisioning volume test_vol: aggregate_name is required'
    assert msg == create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_successful_create():
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-create', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'aggregate_name': MOCK_VOL['aggregate'],
        'size': 20,
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_successful_create_with_completion(dont_sleep):
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-create', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),     # wait for online
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),     # wait for online
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),    # wait for online
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'aggregate_name': MOCK_VOL['aggregate'],
        'size': 20,
        'wait_for_completion': True
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_error_timeout_create_with_completion(dont_sleep):
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-create', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),     # wait for online
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),     # wait for online
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),     # wait for online
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),     # wait for online
    ])
    module_args = {
        'aggregate_name': MOCK_VOL['aggregate'],
        'size': 20,
        'time_out': 42,
        'wait_for_completion': True
    }
    error = "Error waiting for volume test_vol to come online: ['Timeout after 42 seconds']"
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


@patch('time.sleep')
def test_error_timeout_keyerror_create_with_completion(dont_sleep):
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-create', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),                     # wait for online
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),                     # wait for online
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol_no_online_key']),      # wait for online
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),                     # wait for online
    ])
    module_args = {
        'aggregate_name': MOCK_VOL['aggregate'],
        'size': 20,
        'time_out': 42,
        'wait_for_completion': True
    }
    error_py3x = '''Error waiting for volume test_vol to come online: ["KeyError('is_online')", 'Timeout after 42 seconds']'''
    error_py27 = '''Error waiting for volume test_vol to come online: ["KeyError('is_online',)", 'Timeout after 42 seconds']'''
    error = create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('error', error)
    assert error == error_py3x or error == error_py27


def test_error_create():
    ''' Test error on create '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-create', ZRR['error']),
    ])
    module_args = {
        'aggregate_name': MOCK_VOL['aggregate'],
        'size': 20,
        'encrypt': True,
    }
    error = 'Error provisioning volume test_vol of size 20971520: %s' % ZAPI_ERROR
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_create_idempotency():
    ''' Test create idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
    ])
    assert not create_and_apply(vol_module, DEFAULT_ARGS)['changed']


def test_successful_delete():
    ''' Test delete existing volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-destroy', ZRR['success']),
    ])
    module_args = {
        'state': 'absent',
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


def test_error_delete():
    ''' Test delete existing volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-destroy', ZRR['error']),
        ('ZAPI', 'volume-destroy', ZRR['error']),
    ])
    module_args = {
        'state': 'absent',
    }
    error = 'Error deleting volume test_vol:'
    msg = create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert error in msg
    error = 'volume delete failed with unmount-and-offline option: %s' % ZAPI_ERROR
    assert error in msg
    error = 'volume delete failed without unmount-and-offline option: %s' % ZAPI_ERROR
    assert error in msg


def test_error_delete_async():
    ''' Test delete existing volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexgroup']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-unmount', ZRR['error']),
        ('ZAPI', 'volume-offline-async', ZRR['error']),
        ('ZAPI', 'volume-destroy-async', ZRR['error']),
    ])
    module_args = {
        'state': 'absent',

    }
    error = 'Error deleting volume test_vol: %s' % ZAPI_ERROR
    msg = create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert error in msg
    error = 'Error unmounting volume test_vol: %s' % ZAPI_ERROR
    assert error in msg
    error = 'Error changing the state of volume test_vol to offline: %s' % ZAPI_ERROR
    assert error in msg


def test_delete_idempotency():
    ''' Test delete idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'state': 'absent',
    }
    assert not create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify_size():
    ''' Test successful modify size '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-size', ZRR['success']),
    ])
    module_args = {
        'size': 200,
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<new-size>209715200', 3)


def test_modify_idempotency():
    ''' Test modify idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
    ])
    assert not create_and_apply(vol_module, DEFAULT_ARGS)['changed']


def test_modify_error():
    ''' Test modify idempotency '''
    register_responses([
        ('ZAPI', 'volume-modify-iter', ZRR['error']),
    ])
    msg = 'Error modifying volume test_vol: %s' % ZAPI_ERROR
    assert msg == expect_and_capture_ansible_exception(create_module(vol_module, DEFAULT_ARGS).volume_modify_attributes, 'fail', {})['msg']


def test_mount_volume():
    ''' Test mount volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-mount', ZRR['success']),
    ])
    module_args = {
        'junction_path': '/test123',
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


def test_error_mount_volume():
    ''' Test mount volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-mount', ZRR['error']),
    ])
    module_args = {
        'junction_path': '/test123',
    }
    error = 'Error mounting volume test_vol on path /test123: %s' % ZAPI_ERROR
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_unmount_volume():
    ''' Test unmount volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-unmount', ZRR['success']),
    ])
    module_args = {
        'junction_path': '',
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


def test_error_unmount_volume():
    ''' Test unmount volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-unmount', ZRR['error']),
    ])
    module_args = {
        'junction_path': '',
    }
    error = 'Error unmounting volume test_vol: %s' % ZAPI_ERROR
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_successful_modify_space():
    ''' Test successful modify space '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    args = dict(DEFAULT_ARGS)
    del args['space_slo']
    module_args = {
        'space_guarantee': 'volume',
    }
    assert create_and_apply(vol_module, args, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<space-guarantee>volume', 3)


def test_successful_modify_unix_permissions():
    ''' Test successful modify unix_permissions '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    module_args = {
        'unix_permissions': '---rw-r-xr-x',
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<permissions>---rw-r-xr-x', 3)


def test_successful_modify_volume_security_style():
    ''' Test successful modify volume_security_style '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    module_args = {
        'volume_security_style': 'mixed',
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<style>mixed</style>', 3)


def test_successful_modify_max_files_and_encrypt():
    ''' Test successful modify unix_permissions '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
        ('ZAPI', 'volume-encryption-conversion-start', ZRR['success']),
    ])
    module_args = {
        'encrypt': True,
        'max_files': '3000',
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<files-total>3000', 3)


def test_successful_modify_snapshot_policy():
    ''' Test successful modify snapshot_policy '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    module_args = {
        'snapshot_policy': 'default-1weekly',
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<snapshot-policy>default-1weekly', 3)


def test_successful_modify_efficiency_policy():
    ''' Test successful modify efficiency_policy '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'sis-enable', ZRR['success']),
        ('ZAPI', 'sis-set-config', ZRR['success']),
    ])
    module_args = {
        'efficiency_policy': 'test',
        'inline_compression': True
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<policy-name>test', 4)


def test_successful_modify_efficiency_policy_idempotent():
    ''' Test successful modify efficiency_policy '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['get_sis_info']),
    ])
    module_args = {
        'efficiency_policy': 'test',
        'compression': True
    }
    assert not create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify_efficiency_policy_async():
    ''' Test successful modify efficiency_policy '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexgroup']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'sis-enable-async', ZRR['success']),
        ('ZAPI', 'sis-set-config-async', ZRR['success']),
    ])
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'efficiency_policy': 'test',
        'compression': True,
        'wait_for_completion': True,
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<policy-name>test', 4)


def test_error_set_efficiency_policy():
    register_responses([
        ('ZAPI', 'sis-enable', ZRR['error']),
    ])
    module_args = {'efficiency_policy': 'test_policy'}
    msg = 'Error enable efficiency on volume test_vol: %s' % ZAPI_ERROR
    assert msg == expect_and_capture_ansible_exception(create_module(vol_module, MINIMUM_ARGS, module_args).set_efficiency_config, 'fail')['msg']


def test_error_modify_efficiency_policy():
    ''' Test error modify efficiency_policy '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'sis-enable', ZRR['success']),
        ('ZAPI', 'sis-set-config', ZRR['error']),
    ])
    module_args = {
        'efficiency_policy': 'test',
    }
    error = 'Error setting up efficiency attributes on volume test_vol: %s' % ZAPI_ERROR
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_error_set_efficiency_policy_async():
    register_responses([
        ('ZAPI', 'sis-enable-async', ZRR['error']),
    ])
    module_args = {'efficiency_policy': 'test_policy'}
    msg = 'Error enable efficiency on volume test_vol: %s' % ZAPI_ERROR
    assert msg == expect_and_capture_ansible_exception(create_module(vol_module, MINIMUM_ARGS, module_args).set_efficiency_config_async, 'fail')['msg']


def test_error_modify_efficiency_policy_async():
    ''' Test error modify efficiency_policy '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexgroup']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'sis-enable-async', ZRR['success']),
        ('ZAPI', 'sis-set-config-async', ZRR['error']),
    ])
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'efficiency_policy': 'test',
    }
    error = 'Error setting up efficiency attributes on volume test_vol: %s' % ZAPI_ERROR
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_successful_modify_percent_snapshot_space():
    ''' Test successful modify percent_snapshot_space '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    module_args = {
        'percent_snapshot_space': 90,
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<percentage-snapshot-reserve>90', 3)


def test_successful_modify_qos_policy_group():
    ''' Test successful modify qos_policy_group '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    module_args = {
        'qos_policy_group': 'extreme',
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<policy-group-name>extreme', 3)


def test_successful_modify_qos_adaptive_policy_group():
    ''' Test successful modify qos_adaptive_policy_group '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    module_args = {
        'qos_adaptive_policy_group': 'extreme',
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<adaptive-policy-group-name>extreme', 3)


def test_successful_move():
    ''' Test successful modify aggregate '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-move-start', ZRR['success']),
        ('ZAPI', 'volume-move-get-iter', ZRR['vol_move_status_idle']),
    ])
    module_args = {
        'aggregate_name': 'different_aggr',
        'cutover_action': 'abort_on_failure',
        'encrypt': True,
        'wait_for_completion': True
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


def test_unencrypt_volume():
    ''' Test successful modify aggregate '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol_encrypted']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-move-start', ZRR['success']),
        ('ZAPI', 'volume-move-get-iter', ZRR['vol_move_status_idle']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol_encrypted']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-move-start', ZRR['success']),
        ('ZAPI', 'volume-move-get-iter', ZRR['vol_move_status_idle']),
    ])
    # without aggregate
    module_args = {
        'encrypt': False,
        'wait_for_completion': True
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    # with aggregate.
    module_args['aggregate_name'] = 'test_aggr'
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


def test_error_move():
    ''' Test error modify aggregate '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-move-start', ZRR['error']),
    ])
    module_args = {
        'aggregate_name': 'different_aggr',
    }
    error = 'Error moving volume test_vol: %s -  Retry failed with REST error: False' % ZAPI_ERROR
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def setup_rename(is_isinfinite=None):
    module_args = {
        'from_name': MOCK_VOL['name'],
        'name': 'new_name',
        'time_out': 20
    }
    current = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'name': MOCK_VOL['name'],
        'uuid': MOCK_VOL['uuid'],
        'vserver': MOCK_VOL['vserver'],
    }
    if is_isinfinite is not None:
        module_args['is_infinite'] = is_isinfinite
        current['is_infinite'] = is_isinfinite
    return module_args, current


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_successful_rename(get_volume):
    ''' Test successful rename volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-rename', ZRR['success']),
    ])
    module_args, current = setup_rename()
    get_volume.side_effect = [
        None,
        current
    ]
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_error_rename(get_volume):
    ''' Test error rename volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-rename', ZRR['error']),
    ])
    module_args, current = setup_rename()
    get_volume.side_effect = [
        None,
        current
    ]
    error = 'Error renaming volume new_name: %s' % ZAPI_ERROR
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_error_rename_no_from(get_volume):
    ''' Test error rename volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
    ])
    module_args, current = setup_rename()
    get_volume.side_effect = [
        None,
        None
    ]
    error = 'Error renaming volume: cannot find %s' % MOCK_VOL['name']
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_successful_rename_async(get_volume):
    ''' Test successful rename volume '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-rename-async', ZRR['success']),
    ])
    module_args, current = setup_rename(is_isinfinite=True)
    get_volume.side_effect = [
        None,
        current
    ]
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_helper():
    register_responses([
        ('ZAPI', 'volume-unmount', ZRR['success']),
        ('ZAPI', 'volume-offline', ZRR['success']),
    ])
    module_args = {'is_online': False}
    modify = {
        'is_online': False,
        'junction_path': 'something'
    }
    assert create_module(vol_module, DEFAULT_ARGS, module_args).modify_volume(modify, True) is None


def test_compare_chmod_value_true_1():
    module_args = {'unix_permissions': '------------'}
    current = {
        'unix_permissions': '0'
    }
    vol_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert vol_obj.na_helper.compare_chmod_value(current['unix_permissions'], module_args['unix_permissions'])


def test_compare_chmod_value_true_2():
    module_args = {'unix_permissions': '---rwxrwxrwx'}
    current = {
        'unix_permissions': '777'
    }
    vol_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert vol_obj.na_helper.compare_chmod_value(current['unix_permissions'], module_args['unix_permissions'])


def test_compare_chmod_value_true_3():
    module_args = {'unix_permissions': '---rwxr-xr-x'}
    current = {
        'unix_permissions': '755'
    }
    vol_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert vol_obj.na_helper.compare_chmod_value(current['unix_permissions'], module_args['unix_permissions'])


def test_compare_chmod_value_true_4():
    module_args = {'unix_permissions': '755'}
    current = {
        'unix_permissions': '755'
    }
    vol_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert vol_obj.na_helper.compare_chmod_value(current['unix_permissions'], module_args['unix_permissions'])


def test_compare_chmod_value_false_1():
    module_args = {'unix_permissions': '---rwxrwxrwx'}
    current = {
        'unix_permissions': '0'
    }
    vol_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert not vol_obj.na_helper.compare_chmod_value(current['unix_permissions'], module_args['unix_permissions'])


def test_compare_chmod_value_false_2():
    module_args = {'unix_permissions': '---rwxrwxrwx'}
    current = None
    vol_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert not vol_obj.na_helper.compare_chmod_value(current, module_args['unix_permissions'])


def test_compare_chmod_value_invalid_input_1():
    module_args = {'unix_permissions': '---xwrxwrxwr'}
    current = {
        'unix_permissions': '777'
    }
    vol_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert not vol_obj.na_helper.compare_chmod_value(current['unix_permissions'], module_args['unix_permissions'])


def test_compare_chmod_value_invalid_input_2():
    module_args = {'unix_permissions': '---rwx-wx--a'}
    current = {
        'unix_permissions': '0'
    }
    vol_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert not vol_obj.na_helper.compare_chmod_value(current['unix_permissions'], module_args['unix_permissions'])


def test_compare_chmod_value_invalid_input_3():
    module_args = {'unix_permissions': '---'}
    current = {
        'unix_permissions': '0'
    }
    vol_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert not vol_obj.na_helper.compare_chmod_value(current['unix_permissions'], module_args['unix_permissions'])


def test_compare_chmod_value_invalid_input_4():
    module_args = {'unix_permissions': 'rwx---rwxrwx'}
    current = {
        'unix_permissions': '0'
    }
    vol_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert not vol_obj.na_helper.compare_chmod_value(current['unix_permissions'], module_args['unix_permissions'])


def test_successful_create_flex_group_manually():
    ''' Test successful create flexGroup manually '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['empty']),
        ('ZAPI', 'volume-create-async', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexgroup']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter-async', ZRR['modify_async_result_success']),
        ('ZAPI', 'job-get', ZRR['job_success']),
    ])
    args = copy.deepcopy(DEFAULT_ARGS)
    del args['space_slo']
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'space_guarantee': 'file',
        'time_out': 20
    }
    assert create_and_apply(vol_module, args, module_args)['changed']


def test_error_create_flex_group_manually():
    ''' Test error create flexGroup manually '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['empty']),
        ('ZAPI', 'volume-create-async', ZRR['error']),
    ])
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'time_out': 20
    }
    error = 'Error provisioning volume test_vol of size 20971520: %s' % ZAPI_ERROR
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_partial_error_create_flex_group_manually():
    ''' Test error create flexGroup manually '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['empty']),
        ('ZAPI', 'volume-create-async', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexgroup']),
        ('ZAPI', 'sis-get-iter', ZRR['insufficient_privileges']),                   # ignored but raises a warning
        ('ZAPI', 'volume-modify-iter-async', ZRR['modify_async_result_failure']),
    ])
    args = copy.deepcopy(DEFAULT_ARGS)
    del args['space_slo']
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'space_guarantee': 'file',
        'time_out': 20,
        'use_rest': 'auto'
    }
    error = 'Volume created with success, with missing attributes: Error modifying volume test_vol: error_in_modify'
    assert create_and_apply(vol_module, args, module_args, fail=True)['msg'] == error
    print_warnings()
    assert_warning_was_raised('cannot read volume efficiency options (as expected when running as vserver): '
                              'NetApp API failed. Reason - 12346:Insufficient privileges: user USERID does not have read access to this resource')


def test_successful_create_flex_group_auto_provision():
    ''' Test successful create flexGroup auto provision '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['empty']),
        ('ZAPI', 'volume-create-async', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexgroup']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'auto_provision_as': 'flexgroup',
        'time_out': 20
    }
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_successful_delete_flex_group(get_volume):
    ''' Test successful delete flexGroup '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-unmount', ZRR['success']),
        ('ZAPI', 'volume-offline-async', ZRR['job_success']),
        ('ZAPI', 'volume-destroy-async', ZRR['job_success']),
    ])
    module_args = {
        'state': 'absent',
    }
    current = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'name': MOCK_VOL['name'],
        'vserver': MOCK_VOL['vserver'],
        'style_extended': 'flexgroup',
        'unix_permissions': '755',
        'is_online': True,
        'uuid': 'uuid'
    }
    get_volume.return_value = current
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


def setup_resize():
    module_args = {
        'size': 400,
        'size_unit': 'mb'
    }
    current = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'name': MOCK_VOL['name'],
        'vserver': MOCK_VOL['vserver'],
        'style_extended': 'flexgroup',
        'size': 20971520,
        'unix_permissions': '755',
        'uuid': '1234'
    }
    return module_args, current


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_successful_resize_flex_group(get_volume):
    ''' Test successful reszie flexGroup '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-size-async', ZRR['job_success']),
    ])
    module_args, current = setup_resize()
    get_volume.return_value = current
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_error_resize_flex_group(get_volume):
    ''' Test error reszie flexGroup '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-size-async', ZRR['error']),
    ])
    module_args, current = setup_resize()
    get_volume.return_value = current
    error = 'Error re-sizing volume test_vol: %s' % ZAPI_ERROR
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.check_job_status')
@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_successful_modify_unix_permissions_flex_group(get_volume, check_job_status):
    ''' Test successful modify unix permissions flexGroup '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-modify-iter-async', ZRR['modify_async_result_success']),
    ])
    module_args = {
        'unix_permissions': '---rw-r-xr-x',
        'time_out': 20
    }
    current = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'name': MOCK_VOL['name'],
        'vserver': MOCK_VOL['vserver'],
        'style_extended': 'flexgroup',
        'unix_permissions': '777',
        'uuid': '1234'
    }
    get_volume.return_value = current
    check_job_status.return_value = None
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_successful_modify_unix_permissions_flex_group_0_time_out(get_volume):
    ''' Test successful modify unix permissions flexGroup '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-modify-iter-async', ZRR['modify_async_result_success']),
    ])
    module_args = {
        'unix_permissions': '---rw-r-xr-x',
        'time_out': 0
    }
    current = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'name': MOCK_VOL['name'],
        'vserver': MOCK_VOL['vserver'],
        'style_extended': 'flexgroup',
        'unix_permissions': '777',
        'uuid': '1234'
    }
    get_volume.return_value = current
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_successful_modify_unix_permissions_flex_group_0_missing_result(get_volume):
    ''' Test successful modify unix permissions flexGroup '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-modify-iter-async', ZRR['job_running']),       # bad response
    ])
    module_args = {
        'unix_permissions': '---rw-r-xr-x',
        'time_out': 0
    }
    current = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'name': MOCK_VOL['name'],
        'vserver': MOCK_VOL['vserver'],
        'style_extended': 'flexgroup',
        'unix_permissions': '777',
        'uuid': '1234'
    }
    get_volume.return_value = current
    # check_job_status.side_effect = ['job_error']
    error = create_and_apply(vol_module, DEFAULT_ARGS, module_args, 'fail')
    assert error['msg'].startswith('Unexpected error when modifying volume: result is:')


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.check_job_status')
@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_error_modify_unix_permissions_flex_group(get_volume, check_job_status):
    ''' Test error modify unix permissions flexGroup '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-modify-iter-async', ZRR['modify_async_result_success']),
    ])
    module_args = {
        'unix_permissions': '---rw-r-xr-x',
        'time_out': 20
    }
    current = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'name': MOCK_VOL['name'],
        'vserver': MOCK_VOL['vserver'],
        'style_extended': 'flexgroup',
        'unix_permissions': '777',
        'uuid': '1234'
    }
    get_volume.return_value = current
    check_job_status.side_effect = ['job_error']
    error = create_and_apply(vol_module, DEFAULT_ARGS, module_args, 'fail')
    assert error['msg'] == 'Error when modifying volume: job_error'


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_failure_modify_unix_permissions_flex_group(get_volume):
    ''' Test failure modify unix permissions flexGroup '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-modify-iter-async', ZRR['modify_async_result_failure']),
    ])
    module_args = {
        'unix_permissions': '---rw-r-xr-x',
        'time_out': 20
    }
    current = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'name': MOCK_VOL['name'],
        'vserver': MOCK_VOL['vserver'],
        'style_extended': 'flexgroup',
        'unix_permissions': '777',
        'uuid': '1234'
    }
    get_volume.return_value = current
    error = create_and_apply(vol_module, DEFAULT_ARGS, module_args, 'fail')
    assert error['msg'] == 'Error modifying volume test_vol: error_in_modify'


def setup_offline_state():
    module_args = {'is_online': False}
    current = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'name': MOCK_VOL['name'],
        'vserver': MOCK_VOL['vserver'],
        'style_extended': 'flexgroup',
        'is_online': True,
        'junction_path': 'anything',
        'unix_permissions': '755',
        'uuid': '1234'
    }
    return module_args, current


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_successful_offline_state_flex_group(get_volume):
    ''' Test successful offline flexGroup state '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-unmount', ZRR['success']),
        ('ZAPI', 'volume-offline-async', ZRR['async_results']),
        ('ZAPI', 'job-get', ZRR['job_success']),
    ])
    module_args, current = setup_offline_state()
    get_volume.return_value = current
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_error_offline_state_flex_group(get_volume):
    ''' Test error offline flexGroup state '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-unmount', ZRR['success']),
        ('ZAPI', 'volume-offline-async', ZRR['error']),
    ])
    module_args, current = setup_offline_state()
    get_volume.return_value = current
    error = 'Error changing the state of volume test_vol to offline: %s' % ZAPI_ERROR
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_error_unmounting_offline_state_flex_group(get_volume):
    ''' Test error offline flexGroup state '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-unmount', ZRR['error']),
        ('ZAPI', 'volume-offline-async', ZRR['error']),
    ])
    module_args, current = setup_offline_state()
    get_volume.return_value = current
    error = 'Error changing the state of volume test_vol to offline: %s' % ZAPI_ERROR
    msg = create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert error in msg
    errpr = 'Error unmounting volume test_vol: %s' % ZAPI_ERROR
    assert error in msg


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_successful_online_state_flex_group(get_volume):
    ''' Test successful online flexGroup state '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-online-async', ZRR['async_results']),
        ('ZAPI', 'job-get', ZRR['job_success']),
        ('ZAPI', 'volume-modify-iter-async', ZRR['modify_async_result_success']),
        ('ZAPI', 'job-get', ZRR['job_success']),
        ('ZAPI', 'volume-mount', ZRR['success']),
    ])
    current = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'name': MOCK_VOL['name'],
        'vserver': MOCK_VOL['vserver'],
        'style_extended': 'flexgroup',
        'is_online': False,
        'junction_path': 'anything',
        'unix_permissions': '755',
        'uuid': '1234'
    }
    get_volume.return_value = current
    assert create_and_apply(vol_module, DEFAULT_ARGS)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<group-id>', 3)
    assert get_mock_record().is_text_in_zapi_request('<user-id>', 3)
    assert get_mock_record().is_text_in_zapi_request('<percentage-snapshot-reserve>', 3)
    assert get_mock_record().is_text_in_zapi_request('<junction-path>/test</junction-path>', 5)


def test_check_job_status_error():
    ''' Test check job status error '''
    register_responses([
        ('ZAPI', 'job-get', ZRR['error']),
    ])
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'time_out': 0
    }
    error = 'Error fetching job info: %s' % ZAPI_ERROR
    assert expect_and_capture_ansible_exception(create_module(vol_module, MINIMUM_ARGS, module_args).check_job_status, 'fail', '123')['msg'] == error


@patch('time.sleep')
def test_check_job_status_not_found(skip_sleep):
    ''' Test check job status error '''
    register_responses([
        ('ZAPI', 'job-get', ZRR['error_15661']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'job-get', ZRR['error_15661']),
    ])
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'time_out': 50
    }
    error = 'cannot locate job with id: 123'
    assert create_module(vol_module, MINIMUM_ARGS, module_args).check_job_status('123') == error


@patch('time.sleep')
def test_check_job_status_failure(skip_sleep):
    ''' Test check job status error '''
    register_responses([
        ('ZAPI', 'job-get', ZRR['job_running']),
        ('ZAPI', 'job-get', ZRR['job_running']),
        ('ZAPI', 'job-get', ZRR['job_failure']),
        ('ZAPI', 'job-get', ZRR['job_running']),
        ('ZAPI', 'job-get', ZRR['job_running']),
        ('ZAPI', 'job-get', ZRR['job_no_completion']),
    ])
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'time_out': 20
    }
    msg = 'failure'
    assert msg == create_module(vol_module, MINIMUM_ARGS, module_args).check_job_status('123')
    msg = 'progress'
    assert msg == create_module(vol_module, MINIMUM_ARGS, module_args).check_job_status('123')


def test_check_job_status_time_out_is_0():
    ''' Test check job status time out is 0'''
    register_responses([
        ('ZAPI', 'job-get', ZRR['job_time_out']),
    ])
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'time_out': 0
    }
    msg = 'job completion exceeded expected timer of: 0 seconds'
    assert msg == create_module(vol_module, MINIMUM_ARGS, module_args).check_job_status('123')


def test_check_job_status_unexpected():
    ''' Test check job status unexpected state '''
    register_responses([
        ('ZAPI', 'job-get', ZRR['job_other']),
    ])
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'time_out': 20
    }
    msg = 'Unexpected job status in:'
    assert msg in expect_and_capture_ansible_exception(create_module(vol_module, MINIMUM_ARGS, module_args).check_job_status, 'fail', '123')['msg']


def test_successful_modify_tiering_policy():
    ''' Test successful modify tiering policy '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    module_args = {'tiering_policy': 'auto'}
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<tiering-policy>auto</tiering-policy>', 3)


def test_error_modify_tiering_policy():
    ''' Test successful modify tiering policy '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['error']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['error_tiering_94']),
    ])
    module_args = {'tiering_policy': 'auto'}
    error = zapi_error_message('Error modifying volume test_vol')
    assert error in create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    error = zapi_error_message('Error modifying volume test_vol', 94, 'volume-comp-aggr-attributes', '. Added info: tiering option requires 9.4 or later.')
    assert error in create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_successful_modify_vserver_dr_protection():
    ''' Test successful modify vserver_dr_protection '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    module_args = {'vserver_dr_protection': 'protected'}
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<vserver-dr-protection>protected</vserver-dr-protection>', 3)


def test_successful_group_id():
    ''' Test successful modify group_id '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    module_args = {'group_id': 1001}
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<group-id>1001</group-id>', 3)


def test_successful_modify_user_id():
    ''' Test successful modify user_id '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    module_args = {'user_id': 101}
    assert create_and_apply(vol_module, DEFAULT_ARGS, module_args)['changed']
    print_requests()
    assert get_mock_record().is_text_in_zapi_request('<user-id>101</user-id>', 3)


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume.NetAppOntapVolume.get_volume')
def test_successful_modify_snapshot_auto_delete(get_volume):
    ''' Test successful modify unix permissions flexGroup '''
    register_responses([
        # One ZAPI call for each option!
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapshot-autodelete-set-option', ZRR['success']),
        ('ZAPI', 'snapshot-autodelete-set-option', ZRR['success']),
        ('ZAPI', 'snapshot-autodelete-set-option', ZRR['success']),
        ('ZAPI', 'snapshot-autodelete-set-option', ZRR['success']),
        ('ZAPI', 'snapshot-autodelete-set-option', ZRR['success']),
        ('ZAPI', 'snapshot-autodelete-set-option', ZRR['success']),
        ('ZAPI', 'snapshot-autodelete-set-option', ZRR['success']),
        ('ZAPI', 'snapshot-autodelete-set-option', ZRR['success']),
    ])
    module_args = {
        'snapshot_auto_delete': {
            'delete_order': 'oldest_first', 'destroy_list': 'lun_clone,vol_clone',
            'target_free_space': 20, 'prefix': 'test', 'commitment': 'try',
            'state': 'on', 'trigger': 'snap_reserve', 'defer_delete': 'scheduled'}}
    current = {
        'name': MOCK_VOL['name'],
        'vserver': MOCK_VOL['vserver'],
        'snapshot_auto_delete': {
            'delete_order': 'newest_first', 'destroy_list': 'lun_clone,vol_clone',
            'target_free_space': 30, 'prefix': 'test', 'commitment': 'try',
            'state': 'on', 'trigger': 'snap_reserve', 'defer_delete': 'scheduled'},
        'uuid': '1234'
    }
    get_volume.return_value = current
    assert create_and_apply(vol_module, MINIMUM_ARGS, module_args)['changed']


def test_error_modify_snapshot_auto_delete():
    register_responses([
        ('ZAPI', 'snapshot-autodelete-set-option', ZRR['error']),
    ])
    module_args = {'snapshot_auto_delete': {
        'delete_order': 'oldest_first', 'destroy_list': 'lun_clone,vol_clone',
        'target_free_space': 20, 'prefix': 'test', 'commitment': 'try',
        'state': 'on', 'trigger': 'snap_reserve', 'defer_delete': 'scheduled'}}
    msg = 'Error setting snapshot auto delete options for volume test_vol: %s' % ZAPI_ERROR
    assert msg == expect_and_capture_ansible_exception(create_module(vol_module, MINIMUM_ARGS, module_args).set_snapshot_auto_delete, 'fail')['msg']


def test_successful_volume_rehost():
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-rehost', ZRR['success']),
    ])
    module_args = {
        'from_vserver': 'source_vserver',
        'auto_remap_luns': False,
    }
    assert create_and_apply(vol_module, MINIMUM_ARGS, module_args)['changed']


def test_error_volume_rehost():
    register_responses([
        ('ZAPI', 'volume-rehost', ZRR['error']),
    ])
    module_args = {
        'from_vserver': 'source_vserver',
        'force_unmap_luns': False,
    }
    msg = 'Error rehosting volume test_vol: %s' % ZAPI_ERROR
    assert msg == expect_and_capture_ansible_exception(create_module(vol_module, MINIMUM_ARGS, module_args).rehost_volume, 'fail')['msg']


def test_successful_volume_restore():
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'snapshot-restore-volume', ZRR['success']),
    ])
    module_args = {
        'snapshot_restore': 'snapshot_copy',
        'force_restore': True,
        'preserve_lun_ids': True
    }
    assert create_and_apply(vol_module, MINIMUM_ARGS, module_args)['changed']


def test_error_volume_restore():
    register_responses([
        ('ZAPI', 'snapshot-restore-volume', ZRR['error']),
    ])
    module_args = {'snapshot_restore': 'snapshot_copy'}
    msg = 'Error restoring volume test_vol: %s' % ZAPI_ERROR
    assert msg == expect_and_capture_ansible_exception(create_module(vol_module, MINIMUM_ARGS, module_args).snapshot_restore_volume, 'fail')['msg']


def test_error_modify_flexvol_to_flexgroup():
    ''' Test successful modify vserver_dr_protection '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
    ])
    module_args = {'auto_provision_as': 'flexgroup'}
    msg = 'Error: changing a volume from one backend to another is not allowed.  Current: flexvol, desired: flexgroup.'
    assert msg == create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_error_modify_flexgroup_to_flexvol():
    ''' Changing the style from flexgroup to flexvol is not allowed '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexgroup']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
    ])
    module_args = {'aggregate_name': 'nothing'}
    msg = 'Error: aggregate_name option cannot be used with FlexGroups.'
    assert msg == create_and_apply(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_error_snaplock_not_supported_with_zapi():
    ''' Test successful modify vserver_dr_protection '''
    module_args = {'snaplock': {'retention': {'default': 'P30TM'}}}
    msg = 'Error: snaplock option is not supported with ZAPI.  It can only be used with REST.  use_rest: never.'
    assert msg == create_module(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_wait_for_task_completion_no_records():
    register_responses([
        ('ZAPI', 'results', ZRR['no_records']),
    ])
    # using response to build a request
    zapi_iter, valid = build_zapi_response({'fake-iter': 'any'})
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    assert my_obj.wait_for_task_completion(zapi_iter, lambda: True) is None


def test_wait_for_task_completion_no_records():
    register_responses([
        ('ZAPI', 'results', ZRR['no_records']),
    ])
    # using response to build a request
    zapi_iter, valid = build_zapi_response({'fake-iter': 'any'})
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    assert my_obj.wait_for_task_completion(zapi_iter, lambda x: True) is None


def test_wait_for_task_completion_one_response():
    register_responses([
        ('ZAPI', 'results', ZRR['one_record_no_data']),
    ])
    # using response to build a request
    zapi_iter, valid = build_zapi_response({'fake-iter': 'any'})
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    assert my_obj.wait_for_task_completion(zapi_iter, lambda x: False) is None


@patch('time.sleep')
def test_wait_for_task_completion_loop(skip_sleep):
    register_responses([
        ('ZAPI', 'results', ZRR['one_record_no_data']),
        ('ZAPI', 'results', ZRR['one_record_no_data']),
        ('ZAPI', 'results', ZRR['one_record_no_data']),
    ])

    def check_state(x):
        check_state.counter += 1
        # True continues the wait loop
        # False exits the loop
        return (True, True, False)[check_state.counter - 1]

    check_state.counter = 0

    # using response to build a request
    zapi_iter, valid = build_zapi_response({'fake-iter': 'any'})
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    assert my_obj.wait_for_task_completion(zapi_iter, check_state) is None


@patch('time.sleep')
def test_wait_for_task_completion_loop_with_recoverable_error(skip_sleep):
    register_responses([
        ('ZAPI', 'results', ZRR['one_record_no_data']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['one_record_no_data']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['one_record_no_data']),
    ])

    def check_state(x):
        check_state.counter += 1
        return (True, True, False)[check_state.counter - 1]

    check_state.counter = 0

    # using response to build a request
    zapi_iter, valid = build_zapi_response({'fake-iter': 'any'})
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    assert my_obj.wait_for_task_completion(zapi_iter, check_state) is None


@patch('time.sleep')
def test_wait_for_task_completion_loop_with_non_recoverable_error(skip_sleep):
    register_responses([
        ('ZAPI', 'results', ZRR['one_record_no_data']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['one_record_no_data']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['error']),
        ('ZAPI', 'results', ZRR['error']),
    ])

    # using response to build a request
    zapi_iter, valid = build_zapi_response({'fake-iter': 'any'})
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    assert str(my_obj.wait_for_task_completion(zapi_iter, lambda x: True)) == ZAPI_ERROR


@patch('time.sleep')
def test_start_encryption_conversion(skip_sleep):
    register_responses([
        ('ZAPI', 'volume-encryption-conversion-start', ZRR['success']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['vol_encryption_conversion_status_running']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['vol_encryption_conversion_status_running']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['vol_encryption_conversion_status_idle']),
    ])
    module_args = {
        'wait_for_completion': True,
        'max_wait_time': 120
    }
    my_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    assert my_obj.start_encryption_conversion(True) is None


@patch('time.sleep')
def test_error_on_wait_for_start_encryption_conversion(skip_sleep):
    register_responses([
        ('ZAPI', 'volume-encryption-conversion-start', ZRR['success']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['vol_encryption_conversion_status_running']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['vol_encryption_conversion_status_running']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
    ])
    module_args = {
        'wait_for_completion': True,
        'max_wait_time': 280
    }
    my_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.start_encryption_conversion, 'fail', True)['msg']
    assert error == 'Error getting volume encryption_conversion status: %s' % ZAPI_ERROR


def test_error_start_encryption_conversion():
    register_responses([
        ('ZAPI', 'volume-encryption-conversion-start', ZRR['error']),
    ])
    module_args = {
        'wait_for_completion': True
    }
    my_obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.start_encryption_conversion, 'fail', True)['msg']
    assert error == 'Error enabling encryption for volume test_vol: %s' % ZAPI_ERROR


@patch('time.sleep')
def test_wait_for_volume_encryption_conversion_with_non_recoverable_error(skip_sleep):
    register_responses([
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['vol_encryption_conversion_status_running']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['vol_encryption_conversion_status_running']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
    ])
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.wait_for_volume_encryption_conversion, 'fail')['msg']
    assert error == 'Error getting volume encryption_conversion status: %s' % ZAPI_ERROR


@patch('time.sleep')
def test_wait_for_volume_encryption_conversion(skip_sleep):
    register_responses([
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['vol_encryption_conversion_status_running']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['error']),
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['vol_encryption_conversion_status_idle']),
    ])
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    assert my_obj.wait_for_volume_encryption_conversion() is None


def test_wait_for_volume_encryption_conversion_bad_status():
    register_responses([
        ('ZAPI', 'volume-encryption-conversion-get-iter', ZRR['vol_encryption_conversion_status_error']),
    ])
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.wait_for_volume_encryption_conversion, 'fail')['msg']
    assert error == 'Error converting encryption for volume test_vol: other'


@patch('time.sleep')
def test_wait_for_volume_move_with_non_recoverable_error(skip_sleep):
    register_responses([
        ('ZAPI', 'volume-move-get-iter', ZRR['vol_move_status_running']),
        ('ZAPI', 'volume-move-get-iter', ZRR['error']),
        ('ZAPI', 'volume-move-get-iter', ZRR['error']),
        ('ZAPI', 'volume-move-get-iter', ZRR['error']),
        ('ZAPI', 'volume-move-get-iter', ZRR['vol_move_status_running']),
        ('ZAPI', 'volume-move-get-iter', ZRR['error']),
        ('ZAPI', 'volume-move-get-iter', ZRR['error']),
        ('ZAPI', 'volume-move-get-iter', ZRR['error']),
        ('ZAPI', 'volume-move-get-iter', ZRR['error']),
    ])
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.wait_for_volume_move, 'fail')['msg']
    assert error == 'Error getting volume move status: %s' % ZAPI_ERROR


@patch('time.sleep')
def test_wait_for_volume_move(skip_sleep):
    register_responses([
        ('ZAPI', 'volume-move-get-iter', ZRR['vol_move_status_running']),
        ('ZAPI', 'volume-move-get-iter', ZRR['error']),
        ('ZAPI', 'volume-move-get-iter', ZRR['error']),
        ('ZAPI', 'volume-move-get-iter', ZRR['error']),
        ('ZAPI', 'volume-move-get-iter', ZRR['vol_move_status_idle']),
    ])
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    assert my_obj.wait_for_volume_move() is None


def test_wait_for_volume_move_bad_status():
    register_responses([
        ('ZAPI', 'volume-move-get-iter', ZRR['vol_move_status_error']),
    ])
    my_obj = create_module(vol_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.wait_for_volume_move, 'fail')['msg']
    assert error == 'Error moving volume test_vol: some info'


def test_error_validate_snapshot_auto_delete():
    module_args = {
        'snapshot_auto_delete': {
            'commitment': 'whatever',
            'unknown': 'unexpected option'
        }
    }
    error = "snapshot_auto_delete option 'unknown' is not valid."
    assert create_module(vol_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_get_snapshot_auto_delete_attributes():
    register_responses([
        ('ZAPI', 'volume-get-iter', ZRR['get_flexgroup']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
    ])
    result = create_module(vol_module, DEFAULT_ARGS).get_volume()
    assert 'snapshot_auto_delete' in result
    assert 'is_autodelete_enabled' not in result['snapshot_auto_delete']
    assert result['snapshot_auto_delete']['state'] == 'on'


def test_error_on_get_efficiency_info():
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['no_records']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['error']),
    ])
    error = 'Error fetching efficiency policy for volume test_vol: %s' % ZAPI_ERROR
    assert call_main(my_main, DEFAULT_ARGS, fail=True)['msg'] == error


def test_create_volume_from_main():
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['no_records']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-create', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-unmount', ZRR['success']),
        ('ZAPI', 'volume-offline', ZRR['success']),
        ('ZAPI', 'volume-modify-iter', ZRR['success']),
    ])
    args = dict(DEFAULT_ARGS)
    del args['space_slo']
    module_args = {
        'aggregate_name': MOCK_VOL['aggregate'],
        'comment': 'some comment',
        'is_online': False,
        'space_guarantee': 'file',
        'tiering_policy': 'snapshot-only',
        'volume_security_style': 'unix',
        'vserver_dr_protection': 'unprotected',
    }
    assert call_main(my_main, args, module_args)['changed']


def test_error_create_volume_change_in_type():
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['no_records']),
        ('ZAPI', 'volume-get-iter', ZRR['no_records']),
        ('ZAPI', 'volume-create', ZRR['success']),
        ('ZAPI', 'volume-get-iter', ZRR['get_flexvol']),
        ('ZAPI', 'sis-get-iter', ZRR['no_records']),
    ])
    args = dict(DEFAULT_ARGS)
    module_args = {
        'aggregate_name': MOCK_VOL['aggregate'],
        'type': 'dp',
    }
    error = 'Error: volume type was not set properly at creation time.  Current: rw, desired: dp.'
    assert call_main(my_main, args, module_args, fail=True)['msg'] == error


def test_create_volume_attribute():
    obj = create_module(vol_module, DEFAULT_ARGS)
    # str
    obj.parameters['option_name'] = 'my_option'
    parent = netapp_utils.zapi.NaElement('results')
    obj.create_volume_attribute(None, parent, 'zapi_name', 'option_name')
    print(parent.to_string())
    assert parent['zapi_name'] == 'my_option'
    # int - fail, unless converted
    obj.parameters['option_name'] = 123
    expect_and_capture_ansible_exception(obj.create_volume_attribute, TypeError, None, parent, 'zapi_name', 'option_name')
    parent = netapp_utils.zapi.NaElement('results')
    obj.create_volume_attribute(None, parent, 'zapi_name', 'option_name', int)
    assert parent['zapi_name'] == '123'
    # boolmodify_volume_efficiency_config
    obj.parameters['option_name'] = False
    parent = netapp_utils.zapi.NaElement('results')
    obj.create_volume_attribute(None, parent, 'zapi_name', 'option_name', bool)
    assert parent['zapi_name'] == 'false'
    # parent->attrs->attr
    # create child
    parent = netapp_utils.zapi.NaElement('results')
    obj.create_volume_attribute('child', parent, 'zapi_name', 'option_name', bool)
    assert parent['child']['zapi_name'] == 'false'
    # use existing child in parent
    obj.create_volume_attribute('child', parent, 'zapi_name2', 'option_name', bool)
    assert parent['child']['zapi_name2'] == 'false'
    # pass child
    parent = netapp_utils.zapi.NaElement('results')
    child = netapp_utils.zapi.NaElement('child')
    obj.create_volume_attribute(child, parent, 'zapi_name', 'option_name', bool)
    assert parent['child']['zapi_name'] == 'false'


def test_check_invoke_result():
    register_responses([
        # 3rd run
        ('ZAPI', 'job-get', ZRR['job_success']),
        # 3th run
        ('ZAPI', 'job-get', ZRR['job_failure']),
    ])
    module_args = {
        'time_out': 0
    }
    obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    # 1 - operation failed immediately
    error = 'Operation failed when testing volume.'
    assert error in expect_and_capture_ansible_exception(obj.check_invoke_result, 'fail', ZRR['failed_results'][0], 'testing')['msg']
    # 2 - operation in progress - exit immediately as time_out is 0
    assert obj.check_invoke_result(ZRR['async_results'][0], 'testing') is None
    module_args = {
        'time_out': 10
    }
    # 3 - operation in progress - job reported success
    obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    error = 'Error when testing volume: failure'
    assert obj.check_invoke_result(ZRR['async_results'][0], 'testing') is None
    # 4 - operation in progress - job reported a failure
    obj = create_module(vol_module, DEFAULT_ARGS, module_args)
    error = 'Error when testing volume: failure'
    assert error in expect_and_capture_ansible_exception(obj.check_invoke_result, 'fail', ZRR['async_results'][0], 'testing')['msg']
