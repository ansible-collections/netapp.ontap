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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_ipsec_policy \
    import NetAppOntapSecurityIPsecPolicy as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'ipsec_policy',
    'use_rest': 'always',
    'local_endpoint': {
        'address': '10.23.43.23',
        'netmask': '24',
        'port': '201'
    },
    'remote_endpoint': {
        'address': '10.23.43.13',
        'netmask': '24'
    },
    'protocol': 'tcp'
}


def form_rest_response(args=None):
    response = {
        "uuid": "6c025f9b",
        "name": "ipsec1",
        "scope": "svm",
        "svm": {"name": "ansibleSVM"},
        "local_endpoint": {
            "address": "10.23.43.23",
            "netmask": "24",
            "port": "201-201"
        },
        "remote_endpoint": {
            "address": "10.23.43.13",
            "netmask": "24",
            "port": "0-0"
        },
        "protocol": "tcp",
        "local_identity": "ing",
        "remote_identity": "ing",
        "action": "discard",
        "enabled": False,
        "authentication_method": "none"
    }
    if args:
        response.update(args)
    return response


SRR = rest_responses({
    'ipsec_auth_none': (200, {"records": [form_rest_response()], "num_records": 1}, None),
    'ipsec_auth_psk': (200, {"records": [form_rest_response({
        "action": "esp_transport",
        "authentication_method": "psk"
    })], "num_records": 1}, None),
    'ipsec_auth_pki': (200, {"records": [form_rest_response({
        "action": "esp_transport",
        "authentication_method": "pki",
        "certificate": {"name": "ca_cert"}
    })], "num_records": 1}, None),
    'ipsec_modify': (200, {"records": [form_rest_response({
        "local_endpoint": {"address": "10.23.43.24", "netmask": "24"},
        "remote_endpoint": {"address": "10.23.43.14", "netmask": "24", "port": "200-200"},
        "protocol": "udp",
    })], "num_records": 1}, None),
    'ipsec_ipv6': (200, {"records": [form_rest_response({
        "local_endpoint": {"address": "2402:940::45", "netmask": "64", "port": "120-120"},
        "remote_endpoint": {"address": "2402:940::55", "netmask": "64", "port": "200-200"},
        "protocol": "udp",
    })], "num_records": 1}, None),
    'ipsec_ipv6_modify': (200, {"records": [form_rest_response({
        "local_endpoint": {"address": "2402:940::46", "netmask": "64", "port": "120-120"},
        "remote_endpoint": {"address": "2402:940::56", "netmask": "64", "port": "200-200"},
        "protocol": "udp",
    })], "num_records": 1}, None)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "name"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_create_security_ipsec_policy_certificate():
    ''' create ipsec policy with certificates '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ipsec/policies', SRR['empty_records']),
        ('POST', 'security/ipsec/policies', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ipsec/policies', SRR['ipsec_auth_pki']),
    ])
    args = {
        "action": "esp_transport",
        "authentication_method": "pki",
        "certificate": "ca_cert"
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_create_security_ipsec_policy_psk():
    ''' create ipsec policy with pre-shared keys '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ipsec/policies', SRR['empty_records']),
        ('POST', 'security/ipsec/policies', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ipsec/policies', SRR['ipsec_auth_psk']),
    ])
    args = {
        "action": "esp_transport",
        "authentication_method": "psk",
        "secret_key": "QDFRTGJUOJDE4RFGDSDW"
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_create_security_ipsec_policy():
    ''' create ipsec policy without authentication method in 9.8 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec/policies', SRR['empty_records']),
        ('POST', 'security/ipsec/policies', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec/policies', SRR['ipsec_auth_none']),
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_modify_security_ipsec_policy():
    ''' modify ipsec policy '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec/policies', SRR['ipsec_auth_none']),
        ('PATCH', 'security/ipsec/policies/6c025f9b', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec/policies', SRR['ipsec_modify'])
    ])
    args = {
        "local_endpoint": {"address": "10.23.43.24", "netmask": "255.255.255.0"},
        "remote_endpoint": {"address": "10.23.43.14", "netmask": "255.255.255.0", "port": "200"},
        "protocol": "udp"
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_warnings_raised():
    ''' test warnings raised '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    args = {"certificate": "new_Cert", "authentication_method": "pki", "action": "discard"}
    create_module(my_module, DEFAULT_ARGS, args)
    warning = "The IPsec action is discard"
    print_warnings()
    assert_warning_was_raised(warning, partial_match=True)

    args = {"secret_key": "AEDFGJTUSHNFGKGLFD", "authentication_method": "psk", "action": "bypass"}
    create_module(my_module, DEFAULT_ARGS, args)
    warning = "The IPsec action is bypass"
    print_warnings()
    assert_warning_was_raised(warning, partial_match=True)


def test_modify_security_ipsec_policy_ipv6():
    ''' test modify ipv6 address '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec/policies', SRR['ipsec_ipv6']),
        ('PATCH', 'security/ipsec/policies/6c025f9b', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec/policies', SRR['ipsec_ipv6_modify'])
    ])
    args = {
        "local_endpoint": {"address": "2402:0940:000:000:00:00:0000:0046", "netmask": "64"},
        "remote_endpoint": {"address": "2402:0940:000:000:00:00:0000:0056", "netmask": "64", "port": "200"},
        "protocol": "17",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_delete_security_ipsec_policy():
    ''' test delete ipsec policy '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec/policies', SRR['ipsec_auth_none']),
        ('DELETE', 'security/ipsec/policies/6c025f9b', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec/policies', SRR['empty_records'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_all_methods_catch_exception():
    ''' test exception in get/create/modify/delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # GET/POST/PATCH/DELETE error.
        ('GET', 'security/ipsec/policies', SRR['generic_error']),
        ('POST', 'security/ipsec/policies', SRR['generic_error']),
        ('PATCH', 'security/ipsec/policies/6c025f9b', SRR['generic_error']),
        ('DELETE', 'security/ipsec/policies/6c025f9b', SRR['generic_error'])
    ])
    sec_obj = create_module(my_module, DEFAULT_ARGS)
    sec_obj.uuid = '6c025f9b'
    assert 'Error fetching security ipsec policy' in expect_and_capture_ansible_exception(sec_obj.get_security_ipsec_policy, 'fail')['msg']
    assert 'Error creating security ipsec policy' in expect_and_capture_ansible_exception(sec_obj.create_security_ipsec_policy, 'fail')['msg']
    assert 'Error modifying security ipsec policy' in expect_and_capture_ansible_exception(sec_obj.modify_security_ipsec_policy, 'fail', {})['msg']
    assert 'Error deleting security ipsec policy' in expect_and_capture_ansible_exception(sec_obj.delete_security_ipsec_policy, 'fail')['msg']


def test_modify_error():
    ''' test modify error '''
    register_responses([
        # Error if try to modify certificate for auth_method none.
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ipsec/policies', SRR['ipsec_auth_none']),
        # Error if try to modify action and authentication_method
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ipsec/policies', SRR['ipsec_auth_none'])

    ])
    args = {'certificate': 'cert_new'}
    assert 'Error: cannot set certificate for IPsec policy' in create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    args = {'authentication_method': 'psk', 'action': 'esp_udp', 'secret_key': 'secretkey'}
    assert 'Error: cannot modify options' in create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']


def test_error_ontap97():
    ''' test module supported from 9.8 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97'])
    ])
    assert 'requires ONTAP 9.8.0 or later' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']
