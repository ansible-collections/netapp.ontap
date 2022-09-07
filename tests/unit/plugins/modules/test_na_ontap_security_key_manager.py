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
        'ip_address': '0.1.2.3',
        'use_rest': 'never'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_modify_key_manager():
    ''' Test successfully add key manager'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'security-key-manager-setup', ZRR['success']),
        ('ZAPI', 'security-key-manager-get-iter', ZRR['security_key_info']),
    ])
    module_args = {
        'ip_address': '1.2.3.4',
        'use_rest': 'never'
    }
    error = "Error, cannot modify existing configuraton: modify is not supported with ZAPI, new values: {'ip_address': '1.2.3.4'}, current values:"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


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


def test_rest_is_required():
    '''report error if external or onboard are used with ZAPI'''
    register_responses([
    ])
    module_args = {
        'onboard': {
            'synchronize': True
        },
        'use_rest': 'never',
    }
    error = 'Error: REST is required for onboard option.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args = {
        'external': {
            'servers': ['0.1.2.3:5696'],
            'client_certificate': 'client_certificate',
            'server_ca_certificates': ['server_ca_certificate']
        },
        'use_rest': 'never',
        'vserver': 'svm_name',
    }
    error = 'options.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'one_external_seckey_record': (200, {
        'records': [{
            'uuid': 'a1b2c3',
            'external': {
                'servers': [{'server': '0.1.2.3:5696'}]
            }}],
        'num_records': 1
    }, None),
    'one_external_seckey_record_2_servers': (200, {
        'records': [{
            'uuid': 'a1b2c3',
            'external': {
                'servers': [
                    {'server': '1.2.3.4:5696'},
                    {'server': '0.1.2.3:5696'}]
            },
            'onboard': {'enabled': False}}],
        'num_records': 1
    }, None),
    'one_onboard_seckey_record': (200, {
        'records': [{
            'uuid': 'a1b2c3',
            'onboard': {
                'enabled': True,
                'key_backup': "certificate",
            }}],
        'num_records': 1
    }, None),
    'one_security_certificate_record': (200, {
        'records': [{'uuid': 'a1b2c3'}],
        'num_records': 1
    }, None),
    'error_duplicate': (400, None, {'message': 'New passphrase cannot be same as the old passphrase.'}),
    'error_incorrect': (400, None, {'message': 'Cluster-wide passphrase is incorrect.'}),
    'error_svm_not_found': (400, None, {'message': 'SVM "svm_name" does not exist'}),
    'error_already_present': (400, None, {'message': 'already has external key management configured'}),
}, False)


def test_successfully_add_key_manager_old_style_rest():
    ''' Test successfully add key manager'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['zero_records']),
        ('POST', 'security/key-managers', SRR['success']),
        # idempotency
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_external_seckey_record']),
    ])
    module_args = {
        'ip_address': '0.1.2.3',
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_add_key_manager_external_rest():
    ''' Test successfully add key manager'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
        ('POST', 'security/key-managers', SRR['success']),
        # idempotency
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_external_seckey_record']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
    ])
    module_args = {
        'external': {
            'servers': ['0.1.2.3:5696'],
            'client_certificate': 'client_certificate',
            'server_ca_certificates': ['server_ca_certificate']
        },
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_add_key_manager_external_rest_svm():
    ''' Test successfully add key manager'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
        ('POST', 'security/key-managers', SRR['success']),
        # idempotency
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_external_seckey_record']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
    ])
    module_args = {
        'external': {
            'servers': ['0.1.2.3:5696'],
            'client_certificate': 'client_certificate',
            'server_ca_certificates': ['server_ca_certificate']
        },
        'vserver': 'svm_name',
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_add_key_manager_onboard_rest():
    ''' Test successfully add key manager'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['zero_records']),
        ('POST', 'security/key-managers', SRR['success']),
        # idempotency
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_duplicate']),
    ])
    module_args = {
        'onboard': {
            'passphrase': 'passphrase_too_short',
            'from_passphrase': 'ignored on create',
        },
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_add_key_manager_onboard_svm_rest():
    ''' Test successfully add key manager'''
    register_responses([
    ])
    module_args = {
        'onboard': {
            'passphrase': 'passphrase_too_short',
            'from_passphrase': 'ignored on create',
        },
        'vserver': 'svm_name',
        'use_rest': 'always'
    }
    error = 'parameters are mutually exclusive:'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_successfully_delete_key_manager_rest():
    ''' Test successfully add key manager'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('DELETE', 'security/key-managers/a1b2c3', SRR['success']),
        # idempotency
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['zero_records']),
    ])
    module_args = {
        'state': 'absent',
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_change_passphrase_onboard_key_manager_rest():
    ''' Test successfully add key manager'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_incorrect']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_duplicate']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        # both passphrases are incorrect
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_incorrect']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_incorrect']),
        # unexpected success on check passphrase
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_duplicate']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        # unexpected success on check passphrase
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_incorrect']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        # unexpected success on check passphrase
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        # unexpected error on check passphrase
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['generic_error']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_duplicate']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        # unexpected error on check passphrase
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_incorrect']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['generic_error']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        # unexpected error on check passphrase
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['generic_error']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['generic_error']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        # idempotency
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_duplicate']),
    ])
    module_args = {
        'onboard': {
            'passphrase': 'passphrase_too_short',
            'from_passphrase': 'passphrase_too_short'
        },
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    error = 'Error: neither from_passphrase nor passphrase match installed passphrase:'
    error = rest_error_message('Error: neither from_passphrase nor passphrase match installed passphrase',
                               'security/key-managers/a1b2c3',
                               got="got {'message': 'Cluster-wide passphrase is incorrect.'}.")
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    # success
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # ignored error
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # idempotency
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_change_passphrase_and_sync_onboard_key_manager_rest():
    ''' Test successfully modify onboard key manager'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_incorrect']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_duplicate']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
        # idempotency - sync is always sent!
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['error_duplicate']),
        ('PATCH', 'security/key-managers/a1b2c3', SRR['success']),
    ])
    module_args = {
        'onboard': {
            'passphrase': 'passphrase_too_short',
            'from_passphrase': 'passphrase_too_short',
            'synchronize': True
        },
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # idempotency
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_change_external_key_manager_rest():
    ''' Test successfully add key manager'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_external_seckey_record_2_servers']),
        ('DELETE', 'security/key-managers/a1b2c3/key-servers/1.2.3.4:5696', SRR['success']),
        ('DELETE', 'security/key-managers/a1b2c3/key-servers/0.1.2.3:5696', SRR['success']),
        ('POST', 'security/key-managers/a1b2c3/key-servers', SRR['success']),
        ('POST', 'security/key-managers/a1b2c3/key-servers', SRR['success']),
        # same servers but different order
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_external_seckey_record_2_servers']),
        # idempotency
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_external_seckey_record_2_servers']),
    ])
    module_args = {
        'external': {
            'servers': ['0.1.2.3:5697', '1.2.3.4:5697']
        },
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # same servers but different order
    module_args = {
        'external': {
            'servers': ['0.1.2.3:5696', '1.2.3.4:5696']
        },
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # idempotency
    module_args = {
        'external': {
            'servers': ['1.2.3.4:5696', '0.1.2.3:5696']
        },
        'use_rest': 'always'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_external_key_manager_rest():
    ''' Test error add key manager'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['generic_error']),
        ('GET', 'security/certificates', SRR['generic_error']),
        ('POST', 'security/key-managers', SRR['generic_error']),
        ('PATCH', 'security/key-managers/123', SRR['generic_error']),
        ('DELETE', 'security/key-managers/123', SRR['generic_error']),
        ('POST', 'security/key-managers/123/key-servers', SRR['generic_error']),
        ('DELETE', 'security/key-managers/123/key-servers/server_name', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = rest_error_message('Error fetching key manager info for cluster', 'security/key-managers')
    assert error in expect_and_capture_ansible_exception(my_obj.get_key_manager, 'fail')['msg']
    error = rest_error_message('Error fetching security certificate info for name of type: type on cluster', 'security/certificates')
    assert error in expect_and_capture_ansible_exception(my_obj.get_security_certificate_uuid_rest, 'fail', 'name', 'type')['msg']
    error = rest_error_message('Error creating key manager for cluster', 'security/key-managers')
    assert error in expect_and_capture_ansible_exception(my_obj.create_key_manager_rest, 'fail')['msg']
    my_obj.uuid = '123'
    error = rest_error_message('Error modifying key manager for cluster', 'security/key-managers/123')
    assert error in expect_and_capture_ansible_exception(my_obj.modify_key_manager_rest, 'fail', {'onboard': {'xxxx': 'yyyy'}})['msg']
    error = rest_error_message('Error deleting key manager for cluster', 'security/key-managers/123')
    assert error in expect_and_capture_ansible_exception(my_obj.delete_key_manager_rest, 'fail')['msg']
    error = rest_error_message('Error adding external key server server_name', 'security/key-managers/123/key-servers')
    assert error in expect_and_capture_ansible_exception(my_obj.add_external_server_rest, 'fail', 'server_name')['msg']
    error = rest_error_message('Error removing external key server server_name', 'security/key-managers/123/key-servers/server_name')
    assert error in expect_and_capture_ansible_exception(my_obj.remove_external_server_rest, 'fail', 'server_name')['msg']


def test_get_security_certificate_uuid_rest_by_name_then_common_name():
    ''' Use name first, then common_name'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
        # not found
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['zero_records']),
        # with 9.7 or earlier, name is not supported
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_security_certificate_uuid_rest('name', 'type') is not None
    assert_warning_was_raised('certificate name not found, retrying with common_name and type type.')
    # not found, neither with name nor common_name
    error = 'Error fetching security certificate info for name of type: type on cluster: not found.'
    assert error in expect_and_capture_ansible_exception(my_obj.get_security_certificate_uuid_rest, 'fail', 'name', 'type')['msg']
    # 9.7
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_security_certificate_uuid_rest('name', 'type') is not None
    assert_warning_was_raised('name is not supported in 9.6 or 9.7, using common_name name and type type.')


def test_get_security_certificate_uuid_rest_by_name_then_common_name_svm():
    ''' With SVM, retry at cluster scope if not found or error at SVM scope '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
        # not found
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['generic_error']),
        ('GET', 'security/certificates', SRR['zero_records']),
        # with 9.7 or earlier, name is not supported
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
    ])
    module_args = {
        'use_rest': 'always',
        'vserver': 'svm_name'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_security_certificate_uuid_rest('name', 'type') is not None
    assert_warning_was_raised('certificate name not found, retrying with common_name and type type.')
    # not found, neither with name nor common_name
    error = 'Error fetching security certificate info for name of type: type on vserver: svm_name: not found.'
    assert error in expect_and_capture_ansible_exception(my_obj.get_security_certificate_uuid_rest, 'fail', 'name', 'type')['msg']
    # 9.7
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_security_certificate_uuid_rest('name', 'type') is not None
    assert_warning_was_raised('name is not supported in 9.6 or 9.7, using common_name name and type type.')


def test_warn_when_onboard_exists_and_only_one_passphrase_present():
    ''' Warn if only one passphrase is present '''
    register_responses([
        # idempotency
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        # idempotency
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
    ])
    module_args = {
        'onboard': {
            'passphrase': 'passphrase_too_short',
        },
        'use_rest': 'always'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert_warning_was_raised('passphrase is ignored')
    module_args = {
        'onboard': {
            'from_passphrase': 'passphrase_too_short',
        },
        'use_rest': 'always'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert_warning_was_raised('from_passphrase is ignored')


def test_error_cannot_change_key_manager_type_rest():
    ''' Warn if only one passphrase is present '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_external_seckey_record']),
    ])
    module_args = {
        'external': {
            'servers': ['0.1.2.3:5697', '1.2.3.4:5697']
        },
        'use_rest': 'always'
    }
    error = 'Error, cannot modify existing configuraton: onboard key-manager is already installed, it needs to be deleted first.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args = {
        'onboard': {
            'from_passphrase': 'passphrase_too_short',
        },
        'use_rest': 'always'
    }
    error = 'Error, cannot modify existing configuraton: external key-manager is already installed, it needs to be deleted first.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_error_sync_repquires_passphrase_rest():
    ''' Warn if only one passphrase is present '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['one_onboard_seckey_record']),
    ])
    module_args = {
        'onboard': {
            'synchronize': True
        },
        'use_rest': 'always'
    }
    error = 'Error: passphrase is required for synchronize.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_return_not_present_when_svm_not_found_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['error_svm_not_found']),
    ])
    module_args = {
        'state': 'absent',
        'vserver': 'svm_name',
        'use_rest': 'always'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_retry_on_create_error(dont_sleep):
    """ when no key server is present, REST does not return a record """
    ''' Test successfully add key manager'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/key-managers', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
        ('GET', 'security/certificates', SRR['one_security_certificate_record']),
        ('POST', 'security/key-managers', SRR['error_already_present']),
        ('DELETE', 'security/key-managers', SRR['success']),
        # we only retry once, erroring out
        ('POST', 'security/key-managers', SRR['error_already_present']),

    ])
    module_args = {
        'external': {
            'servers': ['0.1.2.3:5696'],
            'client_certificate': 'client_certificate',
            'server_ca_certificates': ['server_ca_certificate']
        },
        'vserver': 'svm_name',
        'use_rest': 'always'
    }
    error = 'Error creating key manager for cluster:'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_update_key_server_list():
    ''' Validate servers are added/removed '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # add/remove
        ('DELETE', 'security/key-managers/123/key-servers/s1', SRR['success']),
        ('DELETE', 'security/key-managers/123/key-servers/s3', SRR['success']),
        ('POST', 'security/key-managers/123/key-servers', SRR['success']),
        ('POST', 'security/key-managers/123/key-servers', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    # no requested change
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    current = {
        'external': {
            'servers': [
                {'server': 's1'},
                {'server': 's2'},
                {'server': 's3'},
            ]
        }
    }
    # idempotent
    assert my_obj.update_key_server_list(current) is None
    my_obj.parameters['external'] = {
        'servers': [
            {'server': 's1'},
            {'server': 's2'},
            {'server': 's3'},
        ]
    }
    assert my_obj.update_key_server_list(current) is None
    # delete/add
    my_obj.parameters['external'] = {
        'servers': [
            {'server': 's4'},
            {'server': 's2'},
            {'server': 's5'},
        ]
    }
    my_obj.uuid = '123'
    assert my_obj.update_key_server_list(current) is None
