# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_mav_approval_group """

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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_mav_approval_group \
    import NetAppOntapMAVApprovalGroup as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'state': 'present',
    'name': 'group1',
    'approvers': ['admin1', 'admin2']
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    "approval_group_info": (200, {
        "records": [{
            "name": "group1",
            "approvers": [
                "admin1",
                "admin2"
            ],
            "email": [
                "group1@domain.com"
            ],
            "owner": {
                "uuid": "ad082be3-8d43-11ef-b748-005056b359d4",
                "name": "cluster1"
            }
        }]
    }, None),
    "approval_group_info_updated": (200, {
        "records": [{
            "name": "group1",
            "approvers": [
                "admin1",
                "admin2"
            ],
            "email": [
                "group1.email@domain.com"
            ],
            "owner": {
                "uuid": "ad082be3-8d43-11ef-b748-005056b359d4",
                "name": "cluster1"
            }
        }]
    }, None),
})


def test_get_approval_group_none():
    ''' Test module no records '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['zero_records']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_approval_group() is None


def test_get_approval_group_error():
    ''' Test module GET method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching multi-admin-verify approval group named group1: calling: security/multi-admin-verify/approval-groups: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.get_approval_group, 'fail')['msg']


def test_get_approval_group():
    ''' Test GET record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['approval_group_info']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_approval_group() is not None


def test_create_approval_group():
    ''' Test creating an approval group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['empty_records']),
        ('POST', 'security/multi-admin-verify/approval-groups', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['approval_group_info'])
    ])
    module_args = {
        'email': ['group1@domain.com']
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_approval_group_error():
    ''' Test module POST method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['empty_records']),
        ('POST', 'security/multi-admin-verify/approval-groups', SRR['generic_error'])
    ])
    module_args = {
        'email': ['group1@domain.com']
    }
    msg = 'Error creating multi-admin-verify approval group group1: calling: '\
          'security/multi-admin-verify/approval-groups: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_modify_approval_group():
    ''' Test modifying approval group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['approval_group_info']),
        ('PATCH', 'security/multi-admin-verify/approval-groups/ad082be3-8d43-11ef-b748-005056b359d4/group1', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['approval_group_info_updated'])
    ])
    module_args = {
        'email': ['group1.email@domain.com']
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_approval_group_error():
    ''' Test module PATCH method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['approval_group_info']),
        ('PATCH', 'security/multi-admin-verify/approval-groups/ad082be3-8d43-11ef-b748-005056b359d4/group1', SRR['generic_error']),
    ])
    module_args = {
        'email': ['group1.email@domain.com']
    }
    msg = 'Error modifying multi-admin-verify approval group group1: calling: '\
          'security/multi-admin-verify/approval-groups/ad082be3-8d43-11ef-b748-005056b359d4/group1: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_delete_approval_group():
    ''' Test deleting approval group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['approval_group_info']),
        ('DELETE', 'security/multi-admin-verify/approval-groups/ad082be3-8d43-11ef-b748-005056b359d4/group1', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['empty_records'])
    ])
    module_args = {
        'state': 'absent',
        'name': 'group1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_approval_group_error():
    ''' Test module DELETE method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/multi-admin-verify/approval-groups', SRR['approval_group_info']),
        ('DELETE', 'security/multi-admin-verify/approval-groups/ad082be3-8d43-11ef-b748-005056b359d4/group1', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent',
        'name': 'group1'
    }
    msg = 'Error deleting multi-admin-verify approval group group1: calling: '\
          'security/multi-admin-verify/approval-groups/ad082be3-8d43-11ef-b748-005056b359d4/group1: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_earlier_version():
    ''' Test module supported from 9.11.1 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    module_args = {
        'email': ['group1.email@domain.com']
    }
    assert 'requires ONTAP 9.11.1 or later' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_missing_option():
    ''' Test error missing options '''
    register_responses([

    ])
    DEFAULT_ARGS.pop('approvers')
    msg = 'state is present but all of the following are missing: approvers'
    assert msg in create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
