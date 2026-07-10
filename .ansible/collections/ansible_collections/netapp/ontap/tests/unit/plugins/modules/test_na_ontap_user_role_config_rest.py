# (c) 2026, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_user_role_config """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_and_apply, create_module, call_main, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_user_role_config \
    import NetAppOntapUserRoleConfiguration as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'state': 'present',
    'vserver': 'vserver',
    'role': 'role'
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    'user_role_config': (200, {
        'username_minlength': 3,
        'username_alphanum': False,
        'passwd_minlength': 8,
        'passwd_alphanum': True,
        'passwd_min_special_chars': 0,
        'passwd_expiry_time': -1,
        'require_initial_passwd_update': False,
        'max_failed_login_attempts': 5,
        'disallowed_reuse': 6,
        'change_delay': 0,
        'delay_after_failed_login': 4,
        'passwd_min_lowercase_chars': 0,
        'passwd_min_uppercase_chars': 0,
        'passwd_min_digits': 0,
        'passwd_expiry_warn_time': -1,
        'account_expiry_time': -1,
        'account_inactive_limit': -1,
        'account_lockout_duration': 'PT1H'
    }, None),
})


def test_successful_modify():
    ''' Test successful modify account restrictions '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/security/login/role/config', SRR['user_role_config']),  # get account restrictions
        ('PATCH', 'private/cli/security/login/role/config', SRR['empty_good']),  # modify account restrictions
    ])
    args = {
        'username_minlength': 4,
        'username_alphanum': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_all_methods_catch_exception():
    ''' Test exception in get/modify account restrictions '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        # GET/PATCH error
        ('GET', 'private/cli/security/login/role/config', SRR['generic_error']),
        ('PATCH', 'private/cli/security/login/role/config', SRR['generic_error'])
    ])
    args = {
        'username_minlength': 4
    }
    user_role_config = create_module(my_module, DEFAULT_ARGS, args)
    error = 'Error fetching user account configurations for role'
    assert error in expect_and_capture_ansible_exception(user_role_config.get_user_role_config, 'fail')['msg']
    error = 'Error modifying user account configurations for role'
    assert error in expect_and_capture_ansible_exception(user_role_config.modify_user_role_config, 'fail', args)['msg']


def test_missing_options():
    ''' Test error missing required option timeout '''
    register_responses([])
    args = DEFAULT_ARGS.copy()
    del args['role']
    error = create_module(my_module, args, fail=True)['msg']
    assert 'missing required arguments: role' in error


def test_error_ontap96():
    ''' Test error module supported from 9.6 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    args = {
        'username_minlength': 4
    }
    assert 'requires ONTAP 9.6.0 or later' in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']
