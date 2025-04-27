# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_vscan_scanner_pool '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_efficiency_policy \
    import NetAppOntapEfficiencyPolicy as efficiency_module  # module under test
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'state': 'present',
    'vserver': 'svm3',
    'policy_name': 'test_policy',
    'comment': 'This policy is for x and y',
    'enabled': True,
    'qos_policy': 'background',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'never'
}


threshold_info = {
    'num-records': 1,
    'attributes-list': {
        'sis-policy-info': {
            'changelog-threshold-percent': 10,
            'comment': 'This policy is for x and y',
            'enabled': 'true',
            'policy-name': 'test_policy',
            'policy-type': 'threshold',
            'qos-policy': 'background',
            'vserver': 'svm3'
        }
    }
}

schedule_info = {
    'num-records': 1,
    'attributes-list': {
        'sis-policy-info': {
            'comment': 'This policy is for x and y',
            'duration': 10,
            'enabled': 'true',
            'policy-name': 'test_policy',
            'policy-type': 'scheduled',
            'qos-policy': 'background',
            'vserver': 'svm3'
        }
    }
}

ZRR = zapi_responses({
    'threshold_info': build_zapi_response(threshold_info),
    'schedule_info': build_zapi_response(schedule_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        efficiency_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_get_nonexistent_efficiency_policy():
    register_responses([
        ('sis-policy-get-iter', ZRR['empty'])
    ])
    efficiency_obj = create_module(efficiency_module, DEFAULT_ARGS)
    result = efficiency_obj.get_efficiency_policy()
    assert not result


def test_get_existing_efficiency_policy():
    register_responses([
        ('sis-policy-get-iter', ZRR['threshold_info'])
    ])
    efficiency_obj = create_module(efficiency_module, DEFAULT_ARGS)
    result = efficiency_obj.get_efficiency_policy()
    assert result


def test_successfully_create():
    register_responses([
        ('sis-policy-get-iter', ZRR['empty']),
        ('sis-policy-create', ZRR['success'])
    ])
    args = {'policy_type': 'threshold'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed']


def test_create_idempotency():
    register_responses([
        ('sis-policy-get-iter', ZRR['threshold_info'])
    ])
    args = {'policy_type': 'threshold'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS)['changed'] is False


def test_threshold_duration_failure():
    register_responses([
        ('sis-policy-get-iter', ZRR['threshold_info'])
    ])
    args = {'duration': 1}
    msg = create_and_apply(efficiency_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert "duration cannot be set if policy_type is threshold" == msg


def test_threshold_schedule_failure():
    register_responses([
        ('sis-policy-get-iter', ZRR['threshold_info'])
    ])
    args = {'schedule': 'test_job_schedule'}
    msg = create_and_apply(efficiency_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert "schedule cannot be set if policy_type is threshold" == msg


def test_scheduled_threshold_percent_failure():
    register_responses([
        ('sis-policy-get-iter', ZRR['schedule_info'])
    ])
    args = {'changelog_threshold_percent': 30}
    msg = create_and_apply(efficiency_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert "changelog_threshold_percent cannot be set if policy_type is scheduled" == msg


def test_successfully_delete():
    register_responses([
        ('sis-policy-get-iter', ZRR['threshold_info']),
        ('sis-policy-delete', ZRR['success'])
    ])
    args = {'state': 'absent'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed']


def test_delete_idempotency():
    register_responses([
        ('sis-policy-get-iter', ZRR['empty'])
    ])
    args = {'state': 'absent'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed'] is False


def test_successful_modify():
    register_responses([
        ('sis-policy-get-iter', ZRR['schedule_info']),
        ('sis-policy-modify', ZRR['success'])
    ])
    args = {'policy_type': 'threshold'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('sis-policy-get-iter', ZRR['error']),
        ('sis-policy-create', ZRR['error']),
        ('sis-policy-modify', ZRR['error']),
        ('sis-policy-delete', ZRR['error'])
    ])
    module_args = {
        'schedule': 'test_job_schedule'
    }

    my_obj = create_module(efficiency_module, DEFAULT_ARGS, module_args)

    error = expect_and_capture_ansible_exception(my_obj.get_efficiency_policy, 'fail')['msg']
    assert 'Error searching for efficiency policy test_policy: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.create_efficiency_policy, 'fail')['msg']
    assert 'Error creating efficiency policy test_policy: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.modify_efficiency_policy, 'fail', modify={'schedule': 'test_job_schedule'})['msg']
    assert 'Error modifying efficiency policy test_policy: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.delete_efficiency_policy, 'fail')['msg']
    assert 'Error deleting efficiency policy test_policy: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error


def test_switch_to_zapi():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('sis-policy-get-iter', ZRR['schedule_info'])
    ])
    args = {'use_rest': 'auto'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed'] is False


SRR = rest_responses({
    'threshold_policy_info': (200, {"records": [
        {
            "uuid": "d0845ae1-a8a8-11ec-aa26-005056b323e5",
            "svm": {"name": "svm3"},
            "name": "test_policy",
            "type": "threshold",
            "start_threshold_percent": 30,
            "qos_policy": "background",
            "enabled": True,
            "comment": "This policy is for x and y"
        }
    ], "num_records": 1}, None),
    'scheduled_policy_info': (200, {"records": [
        {
            "uuid": "0d1f0860-a8a9-11ec-aa26-005056b323e5",
            "svm": {"name": "svm3"},
            "name": "test_policy",
            "type": "scheduled",
            "duration": 5,
            "schedule": {"name": "daily"},
            "qos_policy": "background",
            "enabled": True,
            "comment": "This policy is for x and y"
        }
    ], "num_records": 1}, None),
})


def test_successful_create_rest():
    ''' Test successful create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['empty_records']),
        ('POST', 'storage/volume-efficiency-policies', SRR['success'])
    ])
    args = {'policy_type': 'threshold', 'use_rest': 'always'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)


def test_create_idempotency_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['threshold_policy_info'])
    ])
    args = {'policy_type': 'threshold', 'use_rest': 'always'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed'] is False


def test_threshold_duration_failure_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['threshold_policy_info'])
    ])
    args = {'duration': 1, 'use_rest': 'always'}
    msg = create_and_apply(efficiency_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert "duration cannot be set if policy_type is threshold" == msg


def test_threshold_schedule_failure_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['threshold_policy_info'])
    ])
    args = {'schedule': 'test_job_schedule', 'use_rest': 'always'}
    msg = create_and_apply(efficiency_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert "schedule cannot be set if policy_type is threshold" == msg


def test_scheduled_threshold_percent_failure_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['scheduled_policy_info'])
    ])
    args = {'changelog_threshold_percent': 30, 'use_rest': 'always'}
    msg = create_and_apply(efficiency_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert "changelog_threshold_percent cannot be set if policy_type is scheduled" == msg


def test_successfully_delete_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['scheduled_policy_info']),
        ('DELETE', 'storage/volume-efficiency-policies/0d1f0860-a8a9-11ec-aa26-005056b323e5', SRR['success'])
    ])
    args = {'state': 'absent', 'use_rest': 'always'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed']


def test_delete_idempotency_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['empty_records'])
    ])
    args = {'state': 'absent', 'use_rest': 'always'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed'] is False


def test_successful_modify_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['scheduled_policy_info']),
        ('PATCH', 'storage/volume-efficiency-policies/0d1f0860-a8a9-11ec-aa26-005056b323e5', SRR['success'])
    ])
    args = {'policy_type': 'threshold', 'use_rest': 'always'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed']


def test_successful_modify_duration_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['scheduled_policy_info']),
        ('PATCH', 'storage/volume-efficiency-policies/0d1f0860-a8a9-11ec-aa26-005056b323e5', SRR['success'])
    ])
    args = {'duration': 10, 'use_rest': 'always'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed']


def test_successful_modify_duration_set_hyphen_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['scheduled_policy_info']),
        ('PATCH', 'storage/volume-efficiency-policies/0d1f0860-a8a9-11ec-aa26-005056b323e5', SRR['success'])
    ])
    args = {'duration': "-", 'use_rest': 'always'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed']


def test_successful_modify_changelog_threshold_percent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['threshold_policy_info']),
        ('PATCH', 'storage/volume-efficiency-policies/d0845ae1-a8a8-11ec-aa26-005056b323e5', SRR['success'])
    ])
    args = {'changelog_threshold_percent': 40, 'use_rest': 'always'}
    assert create_and_apply(efficiency_module, DEFAULT_ARGS, args)['changed']


def test_if_all_methods_catch_exception_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volume-efficiency-policies', SRR['generic_error']),
        ('POST', 'storage/volume-efficiency-policies', SRR['generic_error']),
        ('PATCH', 'storage/volume-efficiency-policies', SRR['generic_error']),
        ('DELETE', 'storage/volume-efficiency-policies', SRR['generic_error'])
    ])
    module_args = {
        'schedule': 'test_job_schedule',
        'use_rest': 'always'
    }

    my_obj = create_module(efficiency_module, DEFAULT_ARGS, module_args)

    error = expect_and_capture_ansible_exception(my_obj.get_efficiency_policy, 'fail')['msg']
    assert 'calling: storage/volume-efficiency-policies: got Expected error.' in error

    error = expect_and_capture_ansible_exception(my_obj.create_efficiency_policy, 'fail')['msg']
    assert 'calling: storage/volume-efficiency-policies: got Expected error.' in error

    error = expect_and_capture_ansible_exception(my_obj.modify_efficiency_policy, 'fail', modify={'schedule': 'test_job_schedule'})['msg']
    assert 'calling: storage/volume-efficiency-policies: got Expected error.' in error

    error = expect_and_capture_ansible_exception(my_obj.delete_efficiency_policy, 'fail')['msg']
    assert 'calling: storage/volume-efficiency-policies: got Expected error.' in error


def test_module_error_ontap_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])
    ])
    module_args = {'use_rest': 'always'}
    msg = create_module(efficiency_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Error: REST requires ONTAP 9.8 or later for efficiency_policy APIs.' == msg


def test_module_error_duration_in_threshold():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    module_args = {
        'use_rest': 'always',
        'policy_type': 'threshold',
        'duration': 1
    }
    msg = create_module(efficiency_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'duration cannot be set if policy_type is threshold' == msg


def test_module_error_schedule_in_threshold():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    module_args = {
        'use_rest': 'always',
        'policy_type': 'threshold',
        'schedule': 'daily'
    }
    msg = create_module(efficiency_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'schedule cannot be set if policy_type is threshold' == msg


def test_module_error_changelog_threshold_percent_in_schedule():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    module_args = {
        'use_rest': 'always',
        'policy_type': 'scheduled',
        'changelog_threshold_percent': 20
    }
    msg = create_module(efficiency_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'changelog_threshold_percent cannot be set if policy_type is scheduled' == msg
