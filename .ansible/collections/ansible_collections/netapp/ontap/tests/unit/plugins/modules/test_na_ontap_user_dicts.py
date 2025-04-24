# (c) 2018 - 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_user '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, print_requests, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_error_message, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    expect_and_capture_ansible_exception, call_main, create_module, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_user import NetAppOntapUser as my_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    'invalid_value_error': (400, None, {'message': "invalid value service_processor"}),
    'get_user_rest': (200,
                      {'num_records': 1,
                       'records': [{'owner': {'uuid': 'ansible_vserver'},
                                    'name': 'abcd'}]}, None),
    'get_user_details_rest': (200,
                              {'role': {'name': 'vsadmin'},
                               'applications': [{'application': 'http', 'authentication-method': 'password', 'second_authentication_method': 'none'}],
                               'locked': False}, None)
})


def login_info(locked, role_name, apps):
    attributes_list = []
    for app in apps:
        if app in ('console', 'service-processor',):
            attributes_list.append(
                {'security-login-account-info': {
                 'is-locked': locked, 'role-name': role_name, 'application': app, 'authentication-method': 'password'}}
            )
        if app in ('ssh',):
            attributes_list.append(
                {'security-login-account-info': {
                 'is-locked': locked, 'role-name': role_name, 'application': 'ssh', 'authentication-method': 'publickey',
                 'second-authentication-method': 'password'}},
            )
        if app in ('http',):
            attributes_list.extend([
                {'security-login-account-info': {
                 'is-locked': locked, 'role-name': role_name, 'application': 'http', 'authentication-method': 'password'}},
                {'security-login-account-info': {
                 'is-locked': locked, 'role-name': role_name, 'application': 'http', 'authentication-method': 'saml'}},
            ])
    return {
        'num-records': len(attributes_list),
        'attributes-list': attributes_list
    }


ZRR = zapi_responses({
    'login_locked_user': build_zapi_response(login_info("true", 'user', ['console', 'ssh'])),
    'login_unlocked_user': build_zapi_response(login_info("False", 'user', ['console', 'ssh'])),
    'login_unlocked_user_console': build_zapi_response(login_info("False", 'user', ['console'])),
    'login_unlocked_user_service_processor': build_zapi_response(login_info("False", 'user', ['service-processor'])),
    'login_unlocked_user_ssh': build_zapi_response(login_info("False", 'user', ['ssh'])),
    'login_unlocked_user_http': build_zapi_response(login_info("False", 'user', ['http']))
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'user_name',
    'vserver': 'vserver',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    module_args = {
        "use_rest": "never"
    }
    print('Info: %s' % call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'])


def test_module_fail_when_application_name_is_repeated():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    module_args = {
        "use_rest": "never",
        "application_dicts": [
            {'application': 'ssh', 'authentication_methods': ['cert']},
            {'application': 'ssh', 'authentication_methods': ['password']}]
    }
    error = 'Error: repeated application name: ssh.  Group all authentication methods under a single entry.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_ensure_user_get_called():
    ''' a more interesting test '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user_http']),
    ])
    module_args = {
        "use_rest": "never",
        'role_name': 'test',
        'applications': 'console',
        'authentication_method': 'password',
        'replace_existing_apps_and_methods': 'always'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    user_info = my_obj.get_user()
    print('Info: test_user_get: %s' % repr(user_info))
    assert 'saml' in user_info['applications'][0]['authentication_methods']


def test_ensure_user_apply_called_replace():
    ''' creating user and checking idempotency '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['no_records']),
        ('ZAPI', 'security-login-create', ZRR['success']),
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
    ])
    module_args = {
        "use_rest": "never",
        'name': 'create',
        'role_name': 'user',
        'applications': 'console',
        'authentication_method': 'password',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_apply_called_using_dict():
    ''' creating user and checking idempotency '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['no_records']),
        ('ZAPI', 'security-login-create', ZRR['success']),
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user_ssh']),
    ])
    module_args = {
        "use_rest": "never",
        'name': 'create',
        'role_name': 'user',
        'application_dicts': [{
            'application': 'ssh',
            'authentication_methods': ['publickey'],
            'second_authentication_method': 'password'
        }]
    }

    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # BUG: SSH is not idempotent with SSH and replace_existing_apps_and_methods == 'auto'
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_apply_called_add():
    ''' creating user and checking idempotency '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['no_records']),
        ('ZAPI', 'security-login-create', ZRR['success']),
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-modify', ZRR['success']),
        ('ZAPI', 'security-login-delete', ZRR['success']),
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user_console']),
    ])
    module_args = {
        "use_rest": "never",
        'name': 'create',
        'role_name': 'user',
        'application_dicts':
            [dict(application='console', authentication_methods=['password'])],
        'replace_existing_apps_and_methods': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_sp_apply_called():
    ''' creating user with service_processor application and idempotency '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['no_records']),
        ('ZAPI', 'security-login-create', ZRR['success']),
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user_service_processor']),
        ('ZAPI', 'security-login-get-iter', ZRR['no_records']),
        ('ZAPI', 'security-login-create', ZRR['success']),
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user_service_processor']),
    ])
    module_args = {
        "use_rest": "never",
        'name': 'create',
        'role_name': 'user',
        'application_dicts':
            [dict(application='service-processor', authentication_methods=['password'])],
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['application_dicts'] = [dict(application='service_processor', authentication_methods=['password'])]
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_apply_for_delete_called():
    ''' deleting user and checking idempotency '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-delete', ZRR['success']),
        ('ZAPI', 'security-login-delete', ZRR['success']),
        ('ZAPI', 'security-login-get-iter', ZRR['no_records']),
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
        'name': 'create',
        'role_name': 'user',
        'application_dicts':
            [dict(application='console', authentication_methods=['password'])],
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_lock_called():
    ''' changing user_lock to True and checking idempotency'''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-lock', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never",
        "lock_user": False,
        'name': 'create',
        'role_name': 'user',
        'application_dicts': [
            dict(application='console', authentication_methods=['password']),
            dict(application='ssh', authentication_methods=['publickey'], second_authentication_method='password')
        ],
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['lock_user'] = True
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_unlock_called():
    ''' changing user_lock to False and checking idempotency'''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_locked_user']),
        ('ZAPI', 'security-login-get-iter', ZRR['login_locked_user']),
        ('ZAPI', 'security-login-unlock', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never",
        "lock_user": True,
        'name': 'create',
        'role_name': 'user',
        'application_dicts': [
            dict(application='console', authentication_methods=['password']),
            dict(application='ssh', authentication_methods=['publickey'], second_authentication_method='password')
        ],
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['lock_user'] = False
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_set_password_called():
    ''' set password '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-modify-password', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never",
        'name': 'create',
        'role_name': 'user',
        'application_dicts': [
            dict(application='console', authentication_methods=['password']),
            dict(application='ssh', authentication_methods=['publickey'], second_authentication_method='password')
        ],
        'set_password': '123456',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_role_update_called():
    ''' set password '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-modify', ZRR['success']),
        ('ZAPI', 'security-login-modify', ZRR['success']),
        ('ZAPI', 'security-login-modify-password', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never",
        'name': 'create',
        'role_name': 'test123',
        'application_dicts': [
            dict(application='console', authentication_methods=['password']),
            dict(application='ssh', authentication_methods=['publickey'], second_authentication_method='password')
        ],
        'set_password': '123456',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_role_update_additional_application_called():
    ''' set password '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-create', ZRR['success']),
        ('ZAPI', 'security-login-delete', ZRR['success']),
        ('ZAPI', 'security-login-delete', ZRR['success']),
        ('ZAPI', 'security-login-modify-password', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never",
        'name': 'create',
        'role_name': 'test123',
        'application_dicts':
            [dict(application='http', authentication_methods=['password'])],
        'set_password': '123456',
        'replace_existing_apps_and_methods': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_role_update_additional_method_called():
    ''' set password '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-create', ZRR['success']),
        ('ZAPI', 'security-login-delete', ZRR['success']),
        ('ZAPI', 'security-login-delete', ZRR['success']),
        ('ZAPI', 'security-login-modify-password', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never",
        'name': 'create',
        'role_name': 'test123',
        'application_dicts':
            [dict(application='console', authentication_methods=['domain'])],
        'set_password': '123456',
        'replace_existing_apps_and_methods': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['error']),
        ('ZAPI', 'security-login-create', ZRR['error']),
        ('ZAPI', 'security-login-lock', ZRR['error']),
        ('ZAPI', 'security-login-unlock', ZRR['error']),
        ('ZAPI', 'security-login-delete', ZRR['error']),
        ('ZAPI', 'security-login-modify-password', ZRR['error']),
        ('ZAPI', 'security-login-modify', ZRR['error']),
    ])
    module_args = {
        "use_rest": "never",
        'name': 'create',
        'role_name': 'test123',
        'application_dicts':
            [dict(application='console', authentication_methods=['password'])],
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    app = dict(application='console', authentication_methods=['password'])
    assert zapi_error_message('Error getting user create') in expect_and_capture_ansible_exception(my_obj.get_user, 'fail')['msg']
    assert zapi_error_message('Error creating user create') in expect_and_capture_ansible_exception(my_obj.create_user, 'fail', app)['msg']
    assert zapi_error_message('Error locking user create') in expect_and_capture_ansible_exception(my_obj.lock_given_user, 'fail')['msg']
    assert zapi_error_message('Error unlocking user create') in expect_and_capture_ansible_exception(my_obj.unlock_given_user, 'fail')['msg']
    assert zapi_error_message('Error removing user create') in expect_and_capture_ansible_exception(my_obj.delete_user, 'fail', app)['msg']
    assert zapi_error_message('Error setting password for user create') in expect_and_capture_ansible_exception(my_obj.change_password, 'fail')['msg']
    assert zapi_error_message('Error modifying user create') in expect_and_capture_ansible_exception(my_obj.modify_user, 'fail', app, ['password'])['msg']


def test_rest_error_applications_snmp():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['get_user_rest']),
    ])
    module_args = {
        "use_rest": "always",
        'role_name': 'test123',
        'application_dicts':
            [dict(application='snmp', authentication_methods=['usm'])],
        'set_password': '123456',
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == "snmp as application is not supported in REST."


def test_ensure_user_get_rest_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
    ])
    module_args = {
        "use_rest": "always",
        'role_name': 'vsadmin',
        'application_dicts':
            [dict(application='http', authentication_methods=['password']),
             dict(application='ontapi', authentication_methods=['password'])],
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_user_rest() is not None


def test_ensure_create_user_rest_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['zero_records']),
        ('POST', 'security/accounts', SRR['empty_good']),
    ])
    module_args = {
        "use_rest": "always",
        'role_name': 'vsadmin',
        'application_dicts':
            [dict(application='http', authentication_methods=['password']),
             dict(application='ontapi', authentication_methods=['password'])],
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_delete_user_rest_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
        ('DELETE', 'security/accounts/ansible_vserver/abcd', SRR['empty_good']),
    ])
    module_args = {
        "use_rest": "always",
        'state': 'absent',
        'role_name': 'vsadmin',
        'application_dicts':
            [dict(application='http', authentication_methods=['password']),
             dict(application='ontapi', authentication_methods=['password'])],
        'vserver': None
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_modify_user_rest_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['empty_good']),
    ])
    module_args = {
        "use_rest": "always",
        'role_name': 'vsadmin',
        'application_dicts': [dict(application='service_processor', authentication_methods=['usm'])]
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_lock_unlock_user_rest_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['empty_good']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['empty_good']),
    ])
    module_args = {
        "use_rest": "always",
        'role_name': 'vsadmin',
        'application_dicts':
            [dict(application='http', authentication_methods=['password'])],
        'lock_user': True,
    }
    print_requests()
    # TODO: a single PATCH should be enough ?
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_change_password_user_rest_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['empty_good']),
    ])
    module_args = {
        "use_rest": "always",
        'role_name': 'vsadmin',
        'application_dicts':
            [dict(application='http', authentication_methods=['password'])],
        'password': 'newvalue',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_sp_retry():
    """simulate error in create_user_rest and retry"""
    register_responses([
        # retry followed by error
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['zero_records']),
        ('POST', 'security/accounts', SRR['invalid_value_error']),
        ('POST', 'security/accounts', SRR['generic_error']),
        # retry followed by success
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['zero_records']),
        ('POST', 'security/accounts', SRR['invalid_value_error']),
        ('POST', 'security/accounts', SRR['success']),
    ])
    module_args = {
        "use_rest": "always",
        'role_name': 'vsadmin',
        'application_dicts': [
            dict(application='service_processor', authentication_methods=['usm'])
        ]
    }
    assert 'invalid value' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']

    module_args['application_dicts'] = [dict(application='service-processor', authentication_methods=['usm'])]
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_validate_application():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    module_args = {
        "use_rest": "always",
        'role_name': 'vsadmin',
        'application_dicts':
            [dict(application='http', authentication_methods=['password'])],
        'password': 'newvalue',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert 'second_authentication_method' in my_obj.parameters['applications'][0]
    my_obj.parameters['applications'][0].pop('second_authentication_method')
    my_obj.validate_applications()
    assert 'second_authentication_method' in my_obj.parameters['applications'][0]
    assert my_obj.parameters['applications'][0]['second_authentication_method'] is None


def test_sp_transform():
    current = {'applications': []}
    sp_app_u = 'service_processor'
    sp_app_d = 'service-processor'
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
    ])
    # 1. no change using underscore
    module_args = {
        "use_rest": "always",
        'role_name': 'vsadmin',
        'application_dicts': [
            {'application': sp_app_u, 'authentication_methods': ['password']}
        ],
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    my_obj.change_sp_application([])
    sp_apps = [application['application'] for application in my_obj.parameters['applications'] if application['application'].startswith('service')]
    assert sp_apps == [sp_app_u]
    # 2. change underscore -> dash
    my_obj.change_sp_application([{'application': sp_app_d}])
    sp_apps = [application['application'] for application in my_obj.parameters['applications'] if application['application'].startswith('service')]
    assert sp_apps == [sp_app_d]
    # 3. no change using dash
    module_args['application_dicts'] = [{'application': sp_app_d, 'authentication_methods': ['password']}]
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    my_obj.change_sp_application([])
    sp_apps = [application['application'] for application in my_obj.parameters['applications'] if application['application'].startswith('service')]
    assert sp_apps == [sp_app_d]
    # 4. change dash -> underscore
    my_obj.change_sp_application([{'application': sp_app_u}])
    sp_apps = [application['application'] for application in my_obj.parameters['applications'] if application['application'].startswith('service')]
    assert sp_apps == [sp_app_u]
