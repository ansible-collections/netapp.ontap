# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP Kerberos Realm module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys
import pytest
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_kerberos_realm \
    import NetAppOntapKerberosRealm as my_module  # module under test
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible,\
    create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')

DEFAULT_ARGS = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'https': True,
    'validate_certs': False,
    'use_rest': 'never',
    'realm': 'NETAPP.COM',
    'vserver': 'vserver1',
    'kdc_ip': '192.168.0.1',
    'kdc_vendor': 'other'
}

kerberos_info = {
    'num-records': "1",
    'attributes-list': {
        'kerberos-realm': {
            'admin-server-ip': "192.168.0.1",
            'admin-server-port': "749",
            'clock-skew': "5",
            'kdc-ip': "192.168.0.1",
            'kdc-port': "88",
            'kdc-vendor': "other",
            'password-server-ip': "192.168.0.1",
            'password-server-port': "464",
            "permitted-enc-types": {
                "string": ["des", "des3", "aes_128", "aes_256"]
            },
            'realm': "NETAPP.COM",
            'vserver-name': "vserver1"
        }
    }
}


ZRR = zapi_responses({
    'kerberos_info': build_zapi_response(kerberos_info)
})


SRR = rest_responses({
    'kerberos_info': (200, {"records": [{
        "svm": {
            "uuid": "89368b07",
            "name": "svm3"
        },
        "name": "name1",
        "kdc": {
            "vendor": "microsoft",
            "ip": "10.193.115.116",
            "port": 88
        },
        "comment": "mohan",
        "ad_server": {
            "name": "netapp",
            "address": "10.193.115.116"
        }
    }], "num_records": 1}, None)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "realm", "vserver"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_module_fail_when_state_present_required_args_missing():
    ''' required arguments are reported as errors '''
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['kdc_ip']
    del DEFAULT_ARGS_COPY['kdc_vendor']
    error = "state is present but all of the following are missing: kdc_vendor, kdc_ip"
    assert error in create_module(my_module, DEFAULT_ARGS_COPY, fail=True)['msg']


def test_get_existing_realm():
    ''' Test if get_krbrealm returns details for existing kerberos realm '''
    register_responses([
        ('kerberos-realm-get-iter', ZRR['kerberos_info'])
    ])
    kerb_obj = create_module(my_module, DEFAULT_ARGS)
    assert kerb_obj.get_krbrealm()


def test_successfully_modify_realm():
    ''' Test modify realm successful for modifying kdc_ip. '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('kerberos-realm-get-iter', ZRR['kerberos_info']),
        ('kerberos-realm-modify', ZRR['success'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'kdc_ip': '10.1.1.20'})


def test_successfully_delete_realm():
    ''' Test successfully delete realm '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('kerberos-realm-get-iter', ZRR['kerberos_info']),
        ('kerberos-realm-delete', ZRR['success'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})


def test_successfully_create_realm():
    ''' Test successfully create realm '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('kerberos-realm-get-iter', ZRR['no_records']),
        ('kerberos-realm-create', ZRR['success'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)


def test_required_if():
    ''' required arguments are reported as errors '''
    error = "kdc_vendor is microsoft but all of the following are missing: ad_server_ip, ad_server_name"
    assert error in create_module(my_module, DEFAULT_ARGS, {'kdc_vendor': 'microsoft'}, fail=True)['msg']

    error = "kdc_vendor is microsoft but all of the following are missing: ad_server_name"
    args = {'kdc_vendor': 'microsoft', 'ad_server_ip': '10.0.0.1'}
    assert error in create_module(my_module, DEFAULT_ARGS, args, fail=True)['msg']


def test_if_all_methods_catch_exception():
    register_responses([
        ('kerberos-realm-get-iter', ZRR['error']),
        ('kerberos-realm-create', ZRR['error']),
        ('kerberos-realm-modify', ZRR['error']),
        ('kerberos-realm-delete', ZRR['error']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/nfs/kerberos/realms', SRR['generic_error']),
        ('POST', 'protocols/nfs/kerberos/realms', SRR['generic_error']),
        ('PATCH', 'protocols/nfs/kerberos/realms/89368b07/NETAPP.COM', SRR['generic_error']),
        ('DELETE', 'protocols/nfs/kerberos/realms/89368b07/NETAPP.COM', SRR['generic_error'])
    ])
    kerb_obj = create_module(my_module, DEFAULT_ARGS)
    assert 'Error fetching kerberos realm' in expect_and_capture_ansible_exception(kerb_obj.get_krbrealm, 'fail')['msg']
    assert 'Error creating Kerberos Realm' in expect_and_capture_ansible_exception(kerb_obj.create_krbrealm, 'fail')['msg']
    assert 'Error modifying Kerberos Realm' in expect_and_capture_ansible_exception(kerb_obj.modify_krbrealm, 'fail', {})['msg']
    assert 'Error deleting Kerberos Realm' in expect_and_capture_ansible_exception(kerb_obj.delete_krbrealm, 'fail')['msg']

    kerb_obj = create_module(my_module, DEFAULT_ARGS, {'use_rest': 'always'})
    kerb_obj.svm_uuid = '89368b07'
    assert 'Error fetching kerberos realm' in expect_and_capture_ansible_exception(kerb_obj.get_krbrealm, 'fail')['msg']
    assert 'Error creating Kerberos Realm' in expect_and_capture_ansible_exception(kerb_obj.create_krbrealm, 'fail')['msg']
    assert 'Error modifying Kerberos Realm' in expect_and_capture_ansible_exception(kerb_obj.modify_krbrealm, 'fail', {})['msg']
    assert 'Error deleting Kerberos Realm' in expect_and_capture_ansible_exception(kerb_obj.delete_krbrealm, 'fail')['msg']


def test_successfully_create_realm_rest():
    ''' Test successfully create realm '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/nfs/kerberos/realms', SRR['empty_records']),
        ('POST', 'protocols/nfs/kerberos/realms', SRR['success']),
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'use_rest': 'always'})


def test_successfully_modify_realm_rest():
    ''' Test modify realm successful for modifying kdc_ip. '''
    register_responses([
        # modify ip.
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/nfs/kerberos/realms', SRR['kerberos_info']),
        ('PATCH', 'protocols/nfs/kerberos/realms/89368b07/NETAPP.COM', SRR['success']),
        # modify port.
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/nfs/kerberos/realms', SRR['kerberos_info']),
        ('PATCH', 'protocols/nfs/kerberos/realms/89368b07/NETAPP.COM', SRR['success']),
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'use_rest': 'always', 'kdc_ip': '10.1.1.20'})
    assert create_and_apply(my_module, DEFAULT_ARGS, {'use_rest': 'always', 'kdc_port': '8088'})


def test_successfully_delete_realm_rest():
    ''' Test successfully delete realm '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/nfs/kerberos/realms', SRR['kerberos_info']),
        ('DELETE', 'protocols/nfs/kerberos/realms/89368b07/NETAPP.COM', SRR['success'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'use_rest': 'always', 'state': 'absent'})
