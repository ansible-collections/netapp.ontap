# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_vscan_scanner_pool """

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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_vscan_scanner_pool \
    import NetAppOntapVscanScannerPool as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always'
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    'scanner_pool_info': (200, {"records": [
        {
            "name": "Scanner1",
            "servers": [
                "10.193.78.219",
                "10.193.78.221"
            ],
            "privileged_users": [
                "cifs\\user1",
                "cifs\\user2"
            ],
            "role": "primary"
        }
    ]}, None),
    'svm_uuid': (200, {"records": [
        {
            'uuid': '5ec77839-b9b9-11ee-8084-005056b3d69a'
        }
    ], "num_records": 1}, None)
})


svm_uuid = '5ec77839-b9b9-11ee-8084-005056b3d69a'
scanner_pool_name = 'Scanner1'


def test_successful_create():
    ''' Test successful rest create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['empty_records']),
        ('POST', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['empty_good']),
    ])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'hostnames': ['10.193.78.219', '10.193.78.221'],
        'scanner_policy': 'primary',
        'privileged_users': ['cifs\\user1', 'cifs\\user2'],
        'scanner_pool': 'Scanner1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_successful_create_idempotency():
    ''' Test successful rest create idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['scanner_pool_info']),
    ])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'hostnames': ['10.193.78.219', '10.193.78.221'],
        'scanner_policy': 'primary',
        'privileged_users': ['cifs\\user1', 'cifs\\user2'],
        'scanner_pool': 'Scanner1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed'] is False


def test_successful_delete():
    ''' Test successful rest delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['scanner_pool_info']),
        ('DELETE', 'protocols/vscan/%s/scanner-pools/%s' % (svm_uuid, scanner_pool_name), SRR['success']),
    ])
    args = {
        'state': 'absent',
        'vserver': 'ansibleSVM',
        'scanner_pool': 'Scanner1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_successful_delete_idempotency():
    ''' Test successful rest delete idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['empty_records']),
    ])
    args = {
        'state': 'absent',
        'vserver': 'ansibleSVM',
        'scanner_pool': 'Scanner1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed'] is False


def test_successful_modify():
    ''' Test successful rest modify '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['scanner_pool_info']),
        ('PATCH', 'protocols/vscan/%s/scanner-pools/%s' % (svm_uuid, scanner_pool_name), SRR['success']),
    ])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'hostnames': ['10.193.78.219'],
        'scanner_policy': 'idle',
        'privileged_users': ['cifs\\user1'],
        'scanner_pool': 'Scanner1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_error_get():
    ''' Test error rest get '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['generic_error']),
    ]),
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'hostnames': ['10.193.78.219', '10.193.78.221'],
        'scanner_policy': 'primary',
        'privileged_users': ['cifs\\user1', 'cifs\\user2'],
        'scanner_pool': 'Scanner1'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error searching for Vscan Scanner Pool' in error


def test_error_create():
    ''' Test error rest create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['empty_records']),
        ('POST', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['generic_error']),
    ]),
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'hostnames': ['10.193.78.219', '10.193.78.221'],
        'scanner_policy': 'primary',
        'privileged_users': ['cifs\\user1', 'cifs\\user2'],
        'scanner_pool': 'Scanner1'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error creating Vscan Scanner Pool' in error


def test_error_modify():
    ''' Test error rest modify '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['scanner_pool_info']),
        ('PATCH', 'protocols/vscan/%s/scanner-pools/%s' % (svm_uuid, scanner_pool_name), SRR['generic_error']),
    ])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'hostnames': ['10.193.78.219'],
        'scanner_policy': 'idle',
        'privileged_users': ['cifs\\user1'],
        'scanner_pool': 'Scanner1'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error modifying Vscan Scanner Pool' in error


def test_error_delete():
    ''' Test error rest delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/%s/scanner-pools' % (svm_uuid), SRR['scanner_pool_info']),
        ('DELETE', 'protocols/vscan/%s/scanner-pools/%s' % (svm_uuid, scanner_pool_name), SRR['generic_error']),
    ])
    args = {
        'state': 'absent',
        'vserver': 'ansibleSVM',
        'scanner_pool': 'Scanner1'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error deleting Vscan Scanner Pool' in error


def test_error_ontap96():
    ''' Test error module supported from 9.6 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'hostnames': ['10.193.78.219', '10.193.78.221'],
        'scanner_policy': 'primary',
        'privileged_users': ['cifs\\user1', 'cifs\\user2'],
        'scanner_pool': 'Scanner1'
    }
    msg = 'REST requires ONTAP 9.6 or later for /protocols/vscan/{{svm.uuid}}/scanner-pools APIs'
    assert msg in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']


def test_missing_options_scanner_pool():
    ''' Test error missing option scanner_pool '''
    register_responses([])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'hostnames': ['10.193.78.219', '10.193.78.221'],
        'scanner_policy': 'primary',
        'privileged_users': ['cifs\\user1', 'cifs\\user2'],
    }
    error = create_module(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'missing required arguments: scanner_pool' in error
