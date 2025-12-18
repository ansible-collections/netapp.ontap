# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_autoupdate_config """

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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_autoupdate_config \
    import NetAppOntapAutoUpdateConfig as my_module, main as my_main  # module under test

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
    'security_category_config': (200, {
        "records": [{
            "uuid": "8548a096-2cce-11f0-9916-005056b3a1c2",
            "category": "security",
            "description": {
                "message": "Security Files",
                "code": "131072404"
            },
            "action": "confirm",
        }]
    }, None),
    'updated_security_category_config': (200, {
        "records": [{
            "uuid": "8548a096-2cce-11f0-9916-005056b3a1c2",
            "category": "security",
            "description": {
                "message": "Security Files",
                "code": "131072404"
            },
            "action": "automatic",
        }]
    }, None),
})


def test_get_autoupdate_config_none():
    ''' Test module no records '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/auto-update/configurations', SRR['zero_records']),
    ])
    args = {'category': 'non-existent'}
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    assert my_obj.get_autoupdate_config_rest() is None


def test_get_autoupdate_config_error():
    ''' Test module GET method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/auto-update/configurations', SRR['generic_error']),
    ])
    args = {'category': 'security'}
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    msg = 'Error retrieving auto-update settings for security: calling: support/auto-update/configurations: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.get_autoupdate_config_rest, 'fail')['msg']


def test_get_autoupdate_config():
    ''' Test GET record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/auto-update/configurations', SRR['security_category_config']),
    ])
    args = {'category': 'security'}
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    assert my_obj.get_autoupdate_config_rest() is not None


def test_modify_autoupdate_config():
    ''' Test module PATCH method with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/auto-update/configurations', SRR['security_category_config']),
        ('PATCH', 'support/auto-update/configurations/8548a096-2cce-11f0-9916-005056b3a1c2', SRR['success']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/auto-update/configurations', SRR['updated_security_category_config']),
    ])
    args = {'category': 'security', 'action': 'automatic'}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_modify_autoupdate_config_error():
    ''' Test module PATCH method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/auto-update/configurations', SRR['security_category_config']),
        ('PATCH', 'support/auto-update/configurations/8548a096-2cce-11f0-9916-005056b3a1c2', SRR['generic_error']),
    ])
    args = {'category': 'security', 'action': 'automatic'}
    msg = 'Error modifying auto-update settings for security: calling: '\
          'support/auto-update/configurations/8548a096-2cce-11f0-9916-005056b3a1c2: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']


def test_missing_options():
    ''' Test error missing required option category '''
    register_responses([])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'missing required arguments: category' in error


def test_error_ontap_version():
    ''' Test error module supported from ONTAP 9.10.1 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    args = {'category': 'security'}
    assert 'requires ONTAP 9.10.1 or later' in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']
