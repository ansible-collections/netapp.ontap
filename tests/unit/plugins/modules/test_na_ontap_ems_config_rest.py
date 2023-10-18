# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_ems_config """

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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ems_config \
    import NetAppOntapEmsConfig as my_module, main as my_main  # module under test

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
    'ems_config': (200, {
        'mail_from': 'administrator@mycompany.com',
        'mail_server': 'mail.mycompany.com',
        'pubsub_enabled': True
    }, None),
    'ems_config_modified': (200, {
        'mail_from': 'admin@mycompany.com',
        'mail_server': 'mail.mycompany.com',
        'proxy_url': 'http://proxyserver.mycompany.com',
        'proxy_user': 'proxy_user',
        'pubsub_enabled': False
    }, None),
})


def test_successful_modify():
    ''' Test successful rest modify ems config with idempotency check'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems', SRR['ems_config']),  # get ems config
        ('PATCH', 'support/ems', SRR['success']),  # modify ems config

        ('GET', 'cluster', SRR['is_rest_9_10_1']),  # get ems config
        ('GET', 'support/ems', SRR['ems_config_modified']),  # modify ems config
    ])
    args = {
        'mail_from': 'admin@mycompany.com',
        'mail_server': 'mail.mycompany.com',
        'pubsub_enabled': 'false'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_all_methods_catch_exception():
    ''' Test exception in get/modify ems config '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        # GET/PATCH error
        ('GET', 'support/ems', SRR['generic_error']),
        ('PATCH', 'support/ems', SRR['generic_error'])
    ])
    modify_args = {
        'pubsub_enabled': 'false'
    }
    ems_config = create_module(my_module, DEFAULT_ARGS)
    assert 'Error fetching EMS config' in expect_and_capture_ansible_exception(ems_config.get_ems_config_rest, 'fail')['msg']
    assert 'Error modifying EMS config' in expect_and_capture_ansible_exception(ems_config.modify_ems_config_rest, 'fail', modify_args)['msg']


def test_error_ontap96():
    ''' Test module supported from 9.6 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    assert 'requires ONTAP 9.6.0 or later' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


def test_version_error_with_pubsub_enabled():
    ''' Test version error for pubsub_enabled '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])
    ])
    args = {
        'pubsub_enabled': 'false'
    }
    error = create_module(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Minimum version of ONTAP for pubsub_enabled is (9, 10, 1)' in error
