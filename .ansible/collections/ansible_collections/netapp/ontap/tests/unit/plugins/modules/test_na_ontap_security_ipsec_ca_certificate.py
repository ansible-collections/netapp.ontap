# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_and_apply, create_module, expect_and_capture_ansible_exception, call_main, assert_warning_was_raised, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_ipsec_ca_certificate \
    import NetAppOntapSecurityCACertificate as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'cert1',
    'use_rest': 'always'
}


SRR = rest_responses({
    'ipsec_ca_svm_scope': (200, {"records": [{
        'name': 'cert1',
        'svm': {'name': 'svm4'},
        'uuid': '380a12f7'
    }], "num_records": 1}, None),
    'ipsec_ca_cluster_scope': (200, {"records": [{
        'name': 'cert2',
        'scope': 'cluster',
        'uuid': '878eaa35'}], "num_records": 1}, None),
    'error_ipsec_ca_not_exist': (404, None, {'code': 4, 'message': "entry doesn't exist"}),
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "name"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_create_security_ipsec_ca_certificate_svm():
    ''' create ipsec ca certificates in svm '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['ipsec_ca_svm_scope']),                           # get certificate uuid.
        ('GET', 'security/ipsec/ca-certificates/380a12f7', SRR['error_ipsec_ca_not_exist']),   # ipsec ca does not exist.
        ('POST', 'security/ipsec/ca-certificates', SRR['success']),                            # create.
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['ipsec_ca_svm_scope']),                           # get certificate uuid.
        ('GET', 'security/ipsec/ca-certificates/380a12f7', SRR['ipsec_ca_svm_scope']),         # ipsec ca does not exist.
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'svm': 'svm4'})['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, {'svm': 'svm4'})['changed']


def test_create_security_ipsec_ca_certificate_cluster():
    ''' create ipsec ca certificates in cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['ipsec_ca_cluster_scope']),
        ('GET', 'security/ipsec/ca-certificates/878eaa35', SRR['error_ipsec_ca_not_exist']),
        ('POST', 'security/ipsec/ca-certificates', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['ipsec_ca_cluster_scope']),
        ('GET', 'security/ipsec/ca-certificates/878eaa35', SRR['ipsec_ca_cluster_scope'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'name': 'cert1'})['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, {'name': 'cert1'})['changed']


def test_error_certificate_not_exist():
    ''' error if certificate not present '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['empty_records']),
        # do not throw error if certificate not exist and state is absent.
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['empty_records'])
    ])
    error = "Error: certificate cert1 is not installed"
    assert error in create_and_apply(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert not create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_delete_security_ipsec_ca_certificate():
    ''' test delete ipsec ca certificate '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['ipsec_ca_cluster_scope']),
        ('GET', 'security/ipsec/ca-certificates/878eaa35', SRR['ipsec_ca_cluster_scope']),
        ('DELETE', 'security/ipsec/ca-certificates/878eaa35', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['ipsec_ca_cluster_scope']),
        ('GET', 'security/ipsec/ca-certificates/878eaa35', SRR['empty_records'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_all_methods_catch_exception():
    ''' test exception in get/create/modify/delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        # GET/POST/DELETE error.
        ('GET', 'security/certificates', SRR['generic_error']),
        ('GET', 'security/certificates', SRR['ipsec_ca_cluster_scope']),
        ('GET', 'security/ipsec/ca-certificates/878eaa35', SRR['generic_error']),
        ('POST', 'security/ipsec/ca-certificates', SRR['generic_error']),
        ('DELETE', 'security/ipsec/ca-certificates/878eaa35', SRR['generic_error'])
    ])
    ca_obj = create_module(my_module, DEFAULT_ARGS)
    assert 'Error fetching uuid for certificate' in expect_and_capture_ansible_exception(ca_obj.get_certificate_uuid, 'fail')['msg']
    assert 'Error fetching security IPsec CA certificate' in expect_and_capture_ansible_exception(ca_obj.get_ipsec_ca_certificate, 'fail')['msg']
    assert 'Error adding security IPsec CA certificate' in expect_and_capture_ansible_exception(ca_obj.create_ipsec_ca_certificate, 'fail')['msg']
    assert 'Error deleting security IPsec CA certificate' in expect_and_capture_ansible_exception(ca_obj.delete_ipsec_ca_certificate, 'fail')['msg']


def test_error_ontap9_9_1():
    ''' test module supported from 9.10.1 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1'])
    ])
    assert 'requires ONTAP 9.10.1 or later' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']
