# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP Ansible module na_ontap_active_directory '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    set_module_args, AnsibleExitJson, AnsibleFailJson, patch_ansible, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import zapi_responses, build_zapi_response
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_active_directory \
    import NetAppOntapActiveDirectory as my_module, main as my_main         # module under test
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

# not available on 2.6 anymore
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def default_args(use_rest='never'):
    return {
        'hostname': '10.10.10.10',
        'username': 'admin',
        'https': 'true',
        'validate_certs': 'false',
        'password': 'password',
        'account_name': 'account_name',
        'vserver': 'vserver',
        'admin_password': 'admin_password',
        'admin_username': 'admin_username',
        'use_rest': use_rest
    }


ad_info = {
    'attributes-list': {
        'active-directory-account-config': {
            'account-name': 'account_name',
            'domain': 'current.domain',
            'organizational-unit': 'current.ou',
        }
    }
}


ZRR = zapi_responses(
    {'ad': build_zapi_response(ad_info, 1)}
)

SRR = rest_responses({
    'ad_1': (200, {"records": [{
        "fqdn": "server1.com",
        "name": "account_name",
        "organizational_unit": "CN=Test",
        "svm": {"name": "svm1", "uuid": "02c9e252"}
    }], "num_records": 1}, None),
    'ad_2': (200, {"records": [{
        "fqdn": "server2.com",
        "name": "account_name",
        "organizational_unit": "CN=Test",
        "svm": {"name": "svm1", "uuid": "02c9e252"}
    }], "num_records": 1}, None)
})


def test_success_create():
    ''' test get'''
    args = dict(default_args())
    args['domain'] = 'some.domain'
    args['force_account_overwrite'] = True
    args['organizational_unit'] = 'some.OU'
    set_module_args(args)
    register_responses([
        # list of tuples: (expected ZAPI, response)
        ('active-directory-account-get-iter', ZRR['success']),
        ('active-directory-account-create', ZRR['success']),
    ])

    with pytest.raises(AnsibleExitJson) as exc:
        my_main()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed']


def test_fail_create_zapi_error():
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    register_responses([
        # list of tuples: (expected ZAPI, response)
        ('active-directory-account-get-iter', ZRR['success']),
        ('active-directory-account-create', ZRR['error']),
    ])

    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error creating vserver Active Directory account_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg == exc.value.args[0]['msg']


def test_success_delete():
    ''' test get'''
    args = dict(default_args())
    args['state'] = 'absent'
    set_module_args(args)
    register_responses([
        # list of tuples: (expected ZAPI, response)
        ('active-directory-account-get-iter', ZRR['ad']),
        ('active-directory-account-delete', ZRR['success']),
    ])

    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed']


def test_fail_delete_zapi_error():
    ''' test get'''
    args = dict(default_args())
    args['state'] = 'absent'
    set_module_args(args)
    register_responses([
        # list of tuples: (expected ZAPI, response)
        ('active-directory-account-get-iter', ZRR['ad']),
        ('active-directory-account-delete', ZRR['error']),
    ])

    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error deleting vserver Active Directory account_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg == exc.value.args[0]['msg']


def test_success_modify():
    ''' test get'''
    args = dict(default_args())
    args['domain'] = 'some.other.domain'
    args['force_account_overwrite'] = True
    set_module_args(args)
    register_responses([
        # list of tuples: (expected ZAPI, response)
        ('active-directory-account-get-iter', ZRR['ad']),
        ('active-directory-account-modify', ZRR['success']),
    ])

    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed']


def test_fail_modify_zapi_error():
    ''' test get'''
    args = dict(default_args())
    args['domain'] = 'some.other.domain'
    set_module_args(args)
    register_responses([
        # list of tuples: (expected ZAPI, response)
        ('active-directory-account-get-iter', ZRR['ad']),
        ('active-directory-account-modify', ZRR['error']),
    ])

    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error modifying vserver Active Directory account_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg == exc.value.args[0]['msg']


def test_fail_modify_on_ou():
    ''' test get'''
    args = dict(default_args())
    args['organizational_unit'] = 'some.other.OU'
    set_module_args(args)
    register_responses([
        # list of tuples: (expected ZAPI, response)
        ('active-directory-account-get-iter', ZRR['ad']),
    ])

    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: organizational_unit cannot be modified; found {'organizational_unit': 'some.other.OU'}."
    assert msg == exc.value.args[0]['msg']


def test_fail_on_get_zapi_error():
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    register_responses([
        # list of tuples: (expected ZAPI, response)
        ('active-directory-account-get-iter', ZRR['error']),
    ])
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error searching for Active Directory account_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_netapp_lib_error(mock_has_netapp_lib):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    mock_has_netapp_lib.return_value = False
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' == exc.value.args[0]['msg']


def test_fail_on_rest():
    ''' test error with rest versions less than 9.12.1'''
    args = dict(default_args('always'))
    set_module_args(args)
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_0'])
    ])
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    assert 'Error: REST requires ONTAP 9.12.1 or later' in exc.value.args[0]['msg']


def test_success_create_rest():
    ''' test create'''
    args = dict(default_args('always'))
    args['domain'] = 'server1.com'
    args['force_account_overwrite'] = True
    args['organizational_unit'] = 'CN=Test'
    set_module_args(args)
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
        ('GET', 'protocols/active-directory', SRR['empty_records']),
        ('POST', 'protocols/active-directory', SRR['success']),
    ])

    with pytest.raises(AnsibleExitJson) as exc:
        my_main()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed']


def test_success_delete_rest():
    ''' test delete rest'''
    args = dict(default_args('always'))
    args['state'] = 'absent'
    set_module_args(args)
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
        ('GET', 'protocols/active-directory', SRR['ad_1']),
        ('DELETE', 'protocols/active-directory/02c9e252', SRR['success']),
    ])

    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed']


def test_success_modify_rest():
    ''' test modify rest'''
    args = dict(default_args('always'))
    args['domain'] = 'some.other.domain'
    args['force_account_overwrite'] = True
    set_module_args(args)
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
        ('GET', 'protocols/active-directory', SRR['ad_1']),
        ('PATCH', 'protocols/active-directory/02c9e252', SRR['success']),
    ])

    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
        ('GET', 'protocols/active-directory', SRR['generic_error']),
        ('POST', 'protocols/active-directory', SRR['generic_error']),
        ('PATCH', 'protocols/active-directory/02c9e252', SRR['generic_error']),
        ('DELETE', 'protocols/active-directory/02c9e252', SRR['generic_error'])
    ])
    ad_obj = create_module(my_module, default_args('always'))
    ad_obj.svm_uuid = '02c9e252'
    assert 'Error searching for Active Directory' in expect_and_capture_ansible_exception(ad_obj.get_active_directory_rest, 'fail')['msg']
    assert 'Error creating vserver Active Directory' in expect_and_capture_ansible_exception(ad_obj.create_active_directory_rest, 'fail')['msg']
    assert 'Error modifying vserver Active Directory' in expect_and_capture_ansible_exception(ad_obj.modify_active_directory_rest, 'fail')['msg']
    assert 'Error deleting vserver Active Directory' in expect_and_capture_ansible_exception(ad_obj.delete_active_directory_rest, 'fail')['msg']
