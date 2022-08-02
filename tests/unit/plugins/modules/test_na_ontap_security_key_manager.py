# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_error_message, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_warning_was_raised, call_main, create_module, expect_and_capture_ansible_exception, patch_ansible, print_warnings

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_key_manager import\
    NetAppOntapSecurityKeyManager as my_module, main as my_main    # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


security_key_info = {
    'attributes-list': {
        'key-manager-info': {
            'key-manager-ip-address': '0.1.2.3',
            'key-manager-server-status': 'available',
            'key-manager-tcp-port': '5696',
            'node-name': 'test_node'
        }
    }
}

ZRR = zapi_responses({
    'security_key_info': build_zapi_response(security_key_info, 1)
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never'
    }
    error = 'missing required arguments:'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_get_nonexistent_key_manager():
    ''' Test if get_key_manager() returns None for non-existent key manager '''
    register_responses([
        ('ZAPI', 'security-key-manager-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'ip_address': '1.2.3.4',
        'use_rest': 'never'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    result = my_obj.get_key_manager()
    assert result is None


def test_get_existing_key_manager():
    ''' Test if get_key_manager() returns details for existing key manager '''
    register_responses([
        ('ZAPI', 'security-key-manager-get-iter', ZRR['security_key_info']),
    ])
    module_args = {
        'ip_address': '1.2.3.4',
        'use_rest': 'never'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    result = my_obj.get_key_manager()
    assert result['ip_address'] == '0.1.2.3'


def test_successfully_add_key_manager():
    ''' Test successfully add key manager'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'security-key-manager-setup', ZRR['success']),
        ('ZAPI', 'security-key-manager-get-iter', ZRR['no_records']),
        ('ZAPI', 'security-key-manager-add', ZRR['success']),
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'security-key-manager-setup', ZRR['success']),
        ('ZAPI', 'security-key-manager-get-iter', ZRR['security_key_info']),
    ])
    module_args = {
        'ip_address': '1.2.3.4',
        'use_rest': 'never'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_delete_key_manager():
    ''' Test successfully delete key manager'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'security-key-manager-setup', ZRR['success']),
        ('ZAPI', 'security-key-manager-get-iter', ZRR['security_key_info']),
        ('ZAPI', 'security-key-manager-delete', ZRR['success']),
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'security-key-manager-setup', ZRR['success']),
        ('ZAPI', 'security-key-manager-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'ip_address': '1.2.3.4',
        'state': 'absent',
        'use_rest': 'never',
        'node': 'some_node'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised('The option "node" is deprecated and should not be used.')
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_netapp_lib_error(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    module_args = {
        'ip_address': '1.2.3.4',
        'use_rest': 'never',
        'node': 'some_node'
    }
    error = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    print_warnings()
    assert_warning_was_raised('The option "node" is deprecated and should not be used.')


def test_error_handling():
    ''' test error handling on ZAPI calls '''
    register_responses([
        ('ZAPI', 'security-key-manager-setup', ZRR['error']),
        ('ZAPI', 'security-key-manager-get-iter', ZRR['error']),
        ('ZAPI', 'security-key-manager-add', ZRR['error']),
        ('ZAPI', 'security-key-manager-delete', ZRR['error']),

    ])
    module_args = {
        'ip_address': '1.2.3.4',
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = zapi_error_message('Error setting up key manager')
    assert error in expect_and_capture_ansible_exception(my_obj.key_manager_setup, 'fail')['msg']
    error = zapi_error_message('Error fetching key manager')
    assert error in expect_and_capture_ansible_exception(my_obj.get_key_manager, 'fail')['msg']
    error = zapi_error_message('Error creating key manager')
    assert error in expect_and_capture_ansible_exception(my_obj.create_key_manager, 'fail')['msg']
    error = zapi_error_message('Error deleting key manager')
    assert error in expect_and_capture_ansible_exception(my_obj.delete_key_manager, 'fail')['msg']
