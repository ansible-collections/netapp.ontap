# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_cli_timeout """

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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cli_timeout \
    import NetAppOntapCliTimeout as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'state': 'present'
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    'cli_timeout': (200, {
        'timeout': 30
    }, None),
})


def test_successful_modify():
    ''' Test successful modify timeout value '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/system/timeout', SRR['cli_timeout']),  # get timeout value
        ('PATCH', 'private/cli/system/timeout', SRR['success']),  # modify timeout value
    ])
    args = {
        'timeout': 0
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_successful_modify_idempotency():
    ''' Test successful modify timeout value idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/system/timeout', SRR['cli_timeout']),  # get timeout value
    ])
    args = {
        'timeout': 30
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_all_methods_catch_exception():
    ''' Test exception in get/modify timeout value '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        # GET/PATCH error
        ('GET', 'private/cli/system/timeout', SRR['generic_error']),
        ('PATCH', 'private/cli/system/timeout', SRR['generic_error'])
    ])
    args = {
        'timeout': 15
    }
    cli_timeout = create_module(my_module, DEFAULT_ARGS, args)
    error = 'Error fetching CLI sessions timeout value'
    assert error in expect_and_capture_ansible_exception(cli_timeout.get_timeout_value_rest, 'fail')['msg']
    error = 'Error modifying CLI sessions timeout value'
    assert error in expect_and_capture_ansible_exception(cli_timeout.modify_timeout_value_rest, 'fail', args)['msg']


def test_missing_options():
    ''' Test error missing required option timeout '''
    register_responses([])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'missing required arguments: timeout' in error


def test_error_ontap96():
    ''' Test error module supported from 9.6 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    args = {
        'timeout': 15
    }
    assert 'requires ONTAP 9.6.0 or later' in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']
