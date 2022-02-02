# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP Ansible module na_ontap_active_directory '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
from functools import partial
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.tests.unit.framework.ansible_mocks import \
    set_module_args, AnsibleExitJson, AnsibleFailJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_active_directory \
    import NetAppOntapActiveDirectory as my_module, main as my_main         # module under test
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

# not available on 2.6 anymore
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def default_args():
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
    }


if netapp_utils.has_netapp_lib():
    def zapi_response(contents, num_records=None):
        if num_records is not None:
            contents['num-records'] = str(num_records)
        response = netapp_utils.zapi.NaElement('xml')
        response.translate_struct(contents)
        response.add_attr('status', 'passed')
        return response

    def zapi_error(errno, reason):
        response = netapp_utils.zapi.NaElement('xml')
        response.add_attr('errno', str(errno))
        response.add_attr('reason', reason)
        return response

    ZRR = {
        'success': zapi_response({}),
        'version': zapi_response({'version': 'zapi_version'}),
        'cserver': zapi_response({
            'attributes-list': {
                'vserver-info': {
                    'vserver-name': 'vserver'
                }
            }}),
        'ad': zapi_response({
            'attributes-list': {
                'active-directory-account-config': {
                    'account-name': 'account_name',
                    'domain': 'current.domain',
                    'organizational-unit': 'current.ou',
                }
            }}, 1),
        'error': zapi_error(13123, 'forcing an error for test purposes')
    }


def print_zapi_calls(calls):
    for call in calls:
        try:
            print(call.args[0].to_string())
        except AttributeError:
            print(call)


def mock_invoke_elem(responses, xml, tunneling):
    print('INVOKE', xml.to_string())
    zapi = xml.get_name()
    if not responses:
        print('Error: unexpected call to %s' % zapi)
        raise KeyError(zapi)
    expected, response = responses.pop(0)
    if expected == zapi:
        print('RESPONSE', response.to_string())
        return response
    print('Error: unmatched call to %s, expected: %s' % (zapi, expected))
    raise KeyError(zapi)


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
def test_success_create(mock_invoke):
    ''' test get'''
    args = dict(default_args())
    args['domain'] = 'some.domain'
    args['force_account_overwrite'] = True
    args['organizational_unit'] = 'some.OU'
    set_module_args(args)
    responses = [
        # list of tuples: (expected ZAPI, response)
        ('vserver-get-iter', ZRR['cserver']),
        ('ems-autosupport-log', ZRR['success']),
        ('active-directory-account-get-iter', ZRR['success']),
        ('active-directory-account-create', ZRR['success']),
    ]
    mock_invoke.side_effect = partial(mock_invoke_elem, responses)

    with pytest.raises(AnsibleExitJson) as exc:
        my_main()
    print('Info: %s' % exc.value.args[0])
    print_zapi_calls(mock_invoke.mock_calls)
    assert not responses    # all calls were consumed


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
def test_fail_create_zapi_error(mock_invoke):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    responses = [
        # list of tuples: (expected ZAPI, response)
        ('vserver-get-iter', ZRR['cserver']),
        ('ems-autosupport-log', ZRR['success']),
        ('active-directory-account-get-iter', ZRR['success']),
        ('active-directory-account-create', ZRR['error']),
    ]
    mock_invoke.side_effect = partial(mock_invoke_elem, responses)

    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print_zapi_calls(mock_invoke.mock_calls)
    assert not responses    # all calls were consumed
    msg = 'Error creating vserver Active Directory account_name: NetApp API failed. Reason - 13123:forcing an error for test purposes'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
def test_success_delete(mock_invoke):
    ''' test get'''
    args = dict(default_args())
    args['state'] = 'absent'
    set_module_args(args)
    responses = [
        # list of tuples: (expected ZAPI, response)
        ('vserver-get-iter', ZRR['cserver']),
        ('ems-autosupport-log', ZRR['success']),
        ('active-directory-account-get-iter', ZRR['ad']),
        ('active-directory-account-delete', ZRR['success']),
    ]
    mock_invoke.side_effect = partial(mock_invoke_elem, responses)

    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print_zapi_calls(mock_invoke.mock_calls)
    assert not responses    # all calls were consumed


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
def test_fail_delete_zapi_error(mock_invoke):
    ''' test get'''
    args = dict(default_args())
    args['state'] = 'absent'
    set_module_args(args)
    responses = [
        # list of tuples: (expected ZAPI, response)
        ('vserver-get-iter', ZRR['cserver']),
        ('ems-autosupport-log', ZRR['success']),
        ('active-directory-account-get-iter', ZRR['ad']),
        ('active-directory-account-delete', ZRR['error']),
    ]
    mock_invoke.side_effect = partial(mock_invoke_elem, responses)

    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print_zapi_calls(mock_invoke.mock_calls)
    assert not responses    # all calls were consumed
    msg = 'Error deleting vserver Active Directory account_name: NetApp API failed. Reason - 13123:forcing an error for test purposes'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
def test_success_modify(mock_invoke):
    ''' test get'''
    args = dict(default_args())
    args['domain'] = 'some.other.domain'
    args['force_account_overwrite'] = True
    set_module_args(args)
    responses = [
        # list of tuples: (expected ZAPI, response)
        ('vserver-get-iter', ZRR['cserver']),
        ('ems-autosupport-log', ZRR['success']),
        ('active-directory-account-get-iter', ZRR['ad']),
        ('active-directory-account-modify', ZRR['success']),
    ]
    mock_invoke.side_effect = partial(mock_invoke_elem, responses)

    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print_zapi_calls(mock_invoke.mock_calls)
    assert not responses    # all calls were consumed


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
def test_fail_modify_zapi_error(mock_invoke):
    ''' test get'''
    args = dict(default_args())
    args['domain'] = 'some.other.domain'
    set_module_args(args)
    responses = [
        # list of tuples: (expected ZAPI, response)
        ('vserver-get-iter', ZRR['cserver']),
        ('ems-autosupport-log', ZRR['success']),
        ('active-directory-account-get-iter', ZRR['ad']),
        ('active-directory-account-modify', ZRR['error']),
    ]
    mock_invoke.side_effect = partial(mock_invoke_elem, responses)

    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print_zapi_calls(mock_invoke.mock_calls)
    assert not responses    # all calls were consumed
    msg = 'Error modifying vserver Active Directory account_name: NetApp API failed. Reason - 13123:forcing an error for test purposes'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
def test_fail_modify_on_ou(mock_invoke):
    ''' test get'''
    args = dict(default_args())
    args['organizational_unit'] = 'some.other.OU'
    set_module_args(args)
    responses = [
        # list of tuples: (expected ZAPI, response)
        ('vserver-get-iter', ZRR['cserver']),
        ('ems-autosupport-log', ZRR['success']),
        ('active-directory-account-get-iter', ZRR['ad']),
    ]
    mock_invoke.side_effect = partial(mock_invoke_elem, responses)

    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print_zapi_calls(mock_invoke.mock_calls)
    assert not responses    # all calls were consumed
    msg = "Error: organizational_unit cannot be modified; found {'organizational_unit': 'some.other.OU'}."
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_fail_on_get_zapi_error(mock_request, mock_invoke):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    responses = [
        # list of tuples: (expected ZAPI, response)
        ('vserver-get-iter', ZRR['cserver']),
        ('ems-autosupport-log', ZRR['success']),
        ('active-directory-account-get-iter', ZRR['error']),
    ]
    mock_invoke.side_effect = partial(mock_invoke_elem, responses)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_invoke.mock_calls)
    print(mock_request.mock_calls)
    msg = 'Error searching for Active Directory account_name: NetApp API failed. Reason - 13123:forcing an error for test purposes'
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
