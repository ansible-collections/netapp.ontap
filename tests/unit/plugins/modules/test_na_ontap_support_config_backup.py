# (c) 2025, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_support_config_backup """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    patch_ansible, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_support_config_backup \
    import NetAppOntapSupportConfigBackup as my_module     # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


SRR = rest_responses({
    'backup_record': (200, {"records": [
        {
            "username": "ftpuser",
            "url": "http://10.10.10.10/uploads",
            "validate_certificate": False,
        }
    ], "num_records": 1}, None),
    'backup_update': (200, {"records": [
        {
            "username": "netapp_user",
            "url": "https://10.10.20.10/uploads",
            "validate_certificate": True,
        }
    ], "num_records": 1}, None),
})

ARGS_REST = {
    'hostname': 'hostname',
    'username': 'admin',
    'password': 'password',
    'url': 'http://10.10.10.10/uploads',
    'validate_certificate': False,
    'name': 'netapp_user',
    'use_rest': 'always',
}


def test_error_get_config_backup_settings_rest():
    ''' Test get error with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'support/configuration-backup', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error fetching configuration backup settings' in error


def test_ontap_rest():
    ''' Test ONTAP version '''
    register_responses([
    ])
    module_args = {'use_rest': 'Never'}
    error = create_module(my_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error: na_ontap_support_config_backup is only supported with REST API"
    assert msg in error


def test_modify_url_method_rest():
    ''' Test modify with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'support/configuration-backup', SRR['backup_record']),
        ('PATCH', 'support/configuration-backup', SRR['empty_good']),
    ])
    module_args = {
        "username": "ftpuser",
        'url': 'https://10.10.10.10/uploads',
        'validate_certificate': True,
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_modify_username_rest():
    ''' Test modify with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'support/configuration-backup', SRR['backup_record']),
        ('PATCH', 'support/configuration-backup', SRR['empty_good']),
    ])
    module_args = {
        "username": "ftpuser"
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_error_get_modify_rest():
    ''' Test modify idempotency with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'support/configuration-backup', SRR['backup_record']),
        ('PATCH', 'support/configuration-backup', SRR['generic_error']),
    ])
    module_args = {
        'username': 'testuser'
    }
    msg = 'Error updating the configuration backup settings'
    assert create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg'] == msg


def test_successful_modify_idempotency():
    ''' Test successful rest modify idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'support/configuration-backup', SRR['backup_update']),
    ])
    module_args = {
        'url': 'https://10.10.20.10/uploads',
        'validate_certificate': 'True',
    }
    assert not create_and_apply(my_module, ARGS_REST, module_args)['changed']
