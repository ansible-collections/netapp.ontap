# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_snmp_config """

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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snmp_config \
    import NetAppOntapSNMPConfig as my_module, main as my_main  # module under test

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
    'snmp_config': (200, {
        'auth_traps_enabled': False,
        'enabled': True,
        'traps_enabled': False,
    }, None),
    'snmp_config_disabled': (200, {
        'enabled': False
    }, None),
    'snmp_config_modified': (200, {
        'auth_traps_enabled': True,
        'traps_enabled': True
    }, None),
})


def test_successful_disable_snmp():
    ''' Test successful rest modify SNMP config with idempotency check'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'support/snmp', SRR['snmp_config']),  # get SNMP config
        ('PATCH', 'support/snmp', SRR['success']),  # update SNMP config

        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'support/snmp', SRR['snmp_config_disabled']),  # get SNMP config
    ])
    args = {
        'enabled': 'false'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_successful_modify_snmp_config():
    ''' Test successful rest modify SNMP config with idempotency check'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/snmp', SRR['snmp_config']),  # get SNMP config
        ('PATCH', 'support/snmp', SRR['success']),  # update SNMP config

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/snmp', SRR['snmp_config_modified']),  # get SNMP config
    ])
    args = {
        'auth_traps_enabled': True,
        'traps_enabled': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_all_methods_catch_exception():
    ''' Test exception in get/modify SNMP config '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        # GET/PATCH error
        ('GET', 'support/snmp', SRR['generic_error']),
        ('PATCH', 'support/snmp', SRR['generic_error'])
    ])
    modify_args = {
        'enabled': 'false'
    }
    snmp_config = create_module(my_module, DEFAULT_ARGS)
    assert 'Error fetching SNMP config' in expect_and_capture_ansible_exception(snmp_config.get_snmp_config_rest, 'fail')['msg']
    assert 'Error modifying SNMP config' in expect_and_capture_ansible_exception(snmp_config.modify_snmp_config_rest, 'fail', modify_args)['msg']


def test_error_ontap97():
    ''' Test module supported from 9.7 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    assert 'requires ONTAP 9.7.0 or later' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


def test_partially_supported_options_rest():
    ''' Test REST version error for parameters '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    args = {
        'traps_enabled': 'true'
    }
    error = create_module(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Minimum version of ONTAP for traps_enabled is (9, 10, 1)' in error
