# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_active_directory_preferred_domain_controllers """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import create_and_apply, \
    patch_ansible, call_main
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_active_directory_domain_controllers \
    import NetAppOntapActiveDirectoryDC as my_module, main as my_main  # module under test

# REST API canned responses when mocking send_request
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'DC_record': (
        200,
        {
            "records": [
                {
                    "fqdn": "example.com",
                    "server_ip": "10.10.10.10",
                    'svm': {"uuid": "3d52ad89-c278-11ed-a7b0-005056b3ed56"},
                }
            ],
            "num_records": 1
        }, None
    ),
    'svm_record': (
        200,
        {
            "records": [
                {
                    "uuid": "3d52ad89-c278-11ed-a7b0-005056b3ed56",
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
    'vserver': 'ansible',
    'fqdn': 'example.com',
    'server_ip': '10.10.10.10'
}


def test_rest_error_get_svm():
    '''Test error rest get svm'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_0']),
        ('GET', 'svm/svms', SRR['generic_error']),
    ])
    error = call_main(my_main, ARGS_REST, fail=True)['msg']
    msg = "Error fetching vserver ansible: calling: svm/svms: got Expected error."
    assert msg in error


def test_rest_error_get():
    '''Test error rest get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_0']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers', SRR['generic_error']),
    ])
    error = call_main(my_main, ARGS_REST, fail=True)['msg']
    msg = "Error on fetching Active Directory preferred DC configuration of an SVM:"
    assert msg in error


def test_rest_error_create_active_directory_preferred_domain_controllers():
    '''Test error rest create active_directory preferred domain_controllers'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_0']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers', SRR['empty_records']),
        ('POST', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers', SRR['generic_error']),
    ])
    error = call_main(my_main, ARGS_REST, fail=True)['msg']
    msg = "Error on adding Active Directory preferred DC configuration to an SVM:"
    assert msg in error


def test_rest_create_active_directory_preferred_domain_controllers():
    '''Test rest create active_directory preferred domain_controllers'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_0']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers', SRR['empty_records']),
        ('POST', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers', SRR['empty_good']),
    ])
    module_args = {
        'fqdn': 'example.com',
        'server_ip': '10.10.10.10'
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_rest_delete_active_directory_preferred_domain_controllers():
    '''Test rest delete active_directory preferred domain_controllers'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_0']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers', SRR['DC_record']),
        ('DELETE', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers/example.com/10.10.10.10', SRR['empty_good']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed']


def test_rest_error_delete_active_directory_preferred_domain_controllers():
    '''Test error rest delete active_directory preferred domain_controllers'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_0']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers', SRR['DC_record']),
        ('DELETE', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers/example.com/10.10.10.10',
         SRR['generic_error']),
    ])
    module_args = {
        'fqdn': 'example.com',
        'server_ip': '10.10.10.10',
        'state': 'absent'
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on deleting Active Directory preferred DC configuration of an SVM:"
    assert msg in error


def test_create_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_0']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers', SRR['DC_record']),
    ])
    module_args = {
        'state': 'present',
        'fqdn': 'example.com',
        'server_ip': '10.10.10.10'
    }
    assert not call_main(my_main, ARGS_REST, module_args)['changed']


def test_delete_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_0']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'protocols/active-directory/3d52ad89-c278-11ed-a7b0-005056b3ed56/preferred-domain-controllers', SRR['empty_records']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert not call_main(my_main, ARGS_REST, module_args)['changed']
