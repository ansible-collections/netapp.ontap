# (c) 2020-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_snmp_traphosts """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snmp_traphosts \
    import NetAppONTAPSnmpTraphosts as traphost_module  # module under test

# REST API canned responses when mocking send_request
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'snmp_record': (
        200,
        {
            "records": [
                {
                    "host": "example.com",
                }
            ],
            "num_records": 1
        }, None
    ),
    "no_record": (
        200,
        {"num_records": 0},
        None)
})


ARGS_REST = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
    'host': 'example.com'
}


def test_rest_error_get():
    '''Test error rest get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'support/snmp/traphosts', SRR['generic_error']),
    ])
    error = create_and_apply(traphost_module, ARGS_REST, fail=True)['msg']
    msg = "Error on fetching snmp traphosts info:"
    assert msg in error


def test_rest_create():
    '''Test create snmp traphost'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'support/snmp/traphosts', SRR['empty_records']),
        ('POST', 'support/snmp/traphosts', SRR['empty_good']),
    ])
    assert create_and_apply(traphost_module, ARGS_REST)


def test_rest_error_create():
    '''Test error create snmp traphost'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'support/snmp/traphosts', SRR['empty_records']),
        ('POST', 'support/snmp/traphosts', SRR['generic_error']),
    ])
    error = create_and_apply(traphost_module, ARGS_REST, fail=True)['msg']
    msg = "Error creating traphost:"
    assert msg in error


def test_rest_delete():
    '''Test delete snmp traphost'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'support/snmp/traphosts', SRR['snmp_record']),
        ('DELETE', 'support/snmp/traphosts/example.com', SRR['empty_good']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(traphost_module, ARGS_REST, module_args)


def test_rest_error_delete():
    '''Test error delete snmp traphost'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'support/snmp/traphosts', SRR['snmp_record']),
        ('DELETE', 'support/snmp/traphosts/example.com', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent'
    }
    error = create_and_apply(traphost_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error deleting traphost:"
    assert msg in error


def test_create_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'support/snmp/traphosts', SRR['snmp_record'])
    ])
    module_args = {
        'state': 'present'
    }
    assert not create_and_apply(traphost_module, ARGS_REST, module_args)['changed']


def test_delete_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'support/snmp/traphosts', SRR['empty_records'])
    ])
    module_args = {
        'state': 'absent'
    }
    assert not create_and_apply(traphost_module, ARGS_REST, module_args)['changed']


def test_ontap_version_rest():
    ''' Test ONTAP version '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    module_args = {'use_rest': 'always'}
    error = create_module(traphost_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error: na_ontap_snmp_traphosts only supports REST, and requires ONTAP 9.7.0 or later."
    assert msg in error
