# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_mav_config """

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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_mav_config \
    import NetAppOntapMAVConfig as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'state': 'present',
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    "multi_admin_approval": (200, {
        "records": [{
            "approval_groups": [],
            "required_approvers": 1,
            "enabled": False,
            "execution_expiry": "PT1H",
            "approval_expiry": "PT1H"
        }]
    }, None),
    "multi_admin_approval_enabled": (200, {
        "records": [{
            "approval_groups": [
                "group1",
                "group2"
            ],
            "required_approvers": 1,
            "enabled": True,
            "execution_expiry": "P14D",
            "approval_expiry": "P14D"
        }]
    }, None),
})


def test_successful_modify():
    ''' Test successful modify multi-admin approval config '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify', SRR['multi_admin_approval']),
        ('PATCH', 'security/multi-admin-verify', SRR['success']),
    ])
    module_args = {
        'enabled': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify_idempotency():
    ''' Test successful modify timeout value idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify', SRR['multi_admin_approval_enabled']),
    ])
    module_args = {
        'enabled': True,
        'approval_groups': [
            'group1',
            'group2'
        ],
        'required_approvers': 1,
        'execution_expiry': 'P14D',
        'approval_expiry': 'P14D'
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_all_methods_catch_exception():
    ''' Test exception in get/modify timeout value '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        # GET/PATCH error
        ('GET', 'security/multi-admin-verify', SRR['generic_error']),
        ('PATCH', 'security/multi-admin-verify', SRR['generic_error'])
    ])
    module_args = {
        'enabled': True
    }
    mav_config = create_module(my_module, DEFAULT_ARGS, module_args)
    error = 'Error fetching multi-admin-verify global settings:'
    assert error in expect_and_capture_ansible_exception(mav_config.get_mav_settings, 'fail')['msg']
    error = 'Error modifying multi-admin-verify global settings:'
    assert error in expect_and_capture_ansible_exception(mav_config.modify_mav_settings, 'fail', module_args)['msg']


def test_error_ontap9_11():
    ''' Test error module supported from 9.11.1 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    module_args = {
        'enabled': True
    }
    assert 'requires ONTAP 9.11.1 or later' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
