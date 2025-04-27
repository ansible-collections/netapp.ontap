# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_mav_rule """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_mav_rule \
    import NetAppOntapMAVRule as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'state': 'present',
    'operation': 'volume delete'
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    "volume_rule": (200, {
        "records": [{
            "operation": "volume delete",
            "auto_request_create": False,
            "required_approvers": 1,
            "approval_groups": [
                {
                    "name": "group1"
                },
                {
                    "name": "group2"
                }
            ],
            "create_time": "2024-12-18T05:51:32-05:00",
            "system_defined": False,
            "execution_expiry": "P1D",
            "approval_expiry": "P1D",
            "owner": {
                "uuid": "ad082be3-8d43-11ef-b748-005056b359d4",
                "name": "cluster1"
            }
        }]
    }, None),
    "volume_rule_updated": (200, {
        "records": [{
            "operation": "volume delete",
            "auto_request_create": False,
            "query": "-vserver svm1",
            "required_approvers": 1,
            "approval_groups": [
                {
                    "name": "group1"
                },
                {
                    "name": "group2"
                }
            ],
            "create_time": "2024-12-18T05:51:32-05:00",
            "system_defined": False,
            "execution_expiry": "P1D",
            "approval_expiry": "P1D",
            "owner": {
                "uuid": "ad082be3-8d43-11ef-b748-005056b359d4",
                "name": "cluster1"
            }
        }]
    }, None),
})


def test_get_mav_rule_none():
    ''' Test module no records '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['zero_records']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_mav_rule() is None


def test_get_mav_rule_error():
    ''' Test module GET method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching multi-admin-verify rule for volume delete: calling: security/multi-admin-verify/rules: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.get_mav_rule, 'fail')['msg']


def test_get_mav_rule():
    ''' Test GET record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['volume_rule']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_mav_rule() is not None


def test_create_mav_rule():
    ''' Test creating a MAV rule with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['empty_records']),
        ('POST', 'security/multi-admin-verify/rules', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['volume_rule'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_create_mav_rule_error():
    ''' Test module POST method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['empty_records']),
        ('POST', 'security/multi-admin-verify/rules', SRR['generic_error'])
    ])
    msg = 'Error creating multi-admin-verify rule for volume delete: calling: '\
          'security/multi-admin-verify/rules: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, fail=True)['msg']


def test_modify_mav_rule():
    ''' Test modifying MAV rule with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['volume_rule']),
        ('PATCH', 'security/multi-admin-verify/rules', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['volume_rule_updated'])
    ])
    module_args = {
        'query': '-vserver svm1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_mav_rule_error():
    ''' Test module PATCH method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['volume_rule']),
        ('PATCH', 'security/multi-admin-verify/rules', SRR['generic_error']),
    ])
    module_args = {
        'query': '-vserver svm1'
    }
    msg = 'Error modifying multi-admin-verify rule for volume delete: calling: '\
          'security/multi-admin-verify/rules: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_delete_mav_rule():
    ''' Test deleting MAV rule with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['volume_rule']),
        ('DELETE', 'security/multi-admin-verify/rules', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['empty_records'])
    ])
    module_args = {
        'state': 'absent',
        'operation': 'volume delete'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_mav_rule_error():
    ''' Test module DELETE method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/rules', SRR['volume_rule']),
        ('DELETE', 'security/multi-admin-verify/rules', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent',
        'operation': 'volume delete'
    }
    msg = 'Error deleting multi-admin-verify rule for volume delete: calling: '\
          'security/multi-admin-verify/rules: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_earlier_version():
    ''' Test module supported from 9.11.1 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    assert 'requires ONTAP 9.11.1 or later' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


def test_missing_option():
    ''' Test error missing options '''
    register_responses([

    ])
    DEFAULT_ARGS.pop('operation')
    msg = 'missing required arguments: operation'
    assert msg in create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
