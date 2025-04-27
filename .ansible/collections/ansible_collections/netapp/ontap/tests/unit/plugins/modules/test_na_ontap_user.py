# (c) 2018-2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_user '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_error, build_zapi_response, zapi_error_message, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    call_main, create_module, expect_and_capture_ansible_exception, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_user import NetAppOntapUser as my_module, main as my_main   # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    'repeated_password': (400, None, {'message': "New password must be different than the old password."}),
    'get_uuid': (200, {'owner': {'uuid': 'ansible'}}, None),
    'get_user_rest': (200,
                      {'num_records': 1,
                       'records': [{'owner': {'uuid': 'ansible_vserver'},
                                    'name': 'abcd'}]}, None),
    'get_user_rest_multiple': (200,
                               {'num_records': 2,
                                'records': [{'owner': {'uuid': 'ansible_vserver'},
                                             'name': 'abcd'},
                                            {}]}, None),
    'get_user_details_rest': (200,
                              {'role': {'name': 'vsadmin'},
                               'applications': [{'application': 'http'}],
                               'locked': False}, None),
    'get_user_details_rest_no_pwd': (200,       # locked is absent if no password was set
                                     {'role': {'name': 'vsadmin'},
                                      'applications': [{'application': 'http'}],
                                      }, None)
}, True)


def login_info(locked, role_name, apps):
    attributes_list = []
    for app in apps:
        if app in ('console', 'service-processor'):
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
            ])
    return {
        'num-records': len(attributes_list),
        'attributes-list': attributes_list
    }


ZRR = zapi_responses({
    'login_locked_user': build_zapi_response(login_info("true", 'user', ['console', 'ssh'])),
    'login_unlocked_user': build_zapi_response(login_info("False", 'user', ['console', 'ssh'])),
    'login_unlocked_user_http': build_zapi_response(login_info("False", 'user', ['http'])),
    'login_unlocked_user_service_processor': build_zapi_response(login_info("False", 'user', ['service-processor'])),
    'user_not_found': build_zapi_error('16034', "This exception should not be seen"),
    'internal_error': build_zapi_error('13114', "Forcing an internal error"),
    'reused_password': build_zapi_error('13214', "New password must be different than last 6 passwords."),
}, True)


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
        'use_rest': 'never',
    }
    print('Info: %s' % call_main(my_main, {}, module_args, fail=True)['msg'])


def test_module_fail_when_vserver_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never',
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'name': 'user_name',
    }
    assert 'Error: vserver is required' in call_main(my_main, {}, module_args, fail=True)['msg']


def test_ensure_user_get_called():
    ''' a more interesting test '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'role_name': 'test',
        'applications': 'http',
        'authentication_method': 'password',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    # app = dict(application='testapp', authentication_methods=['testam'])
    user_info = my_obj.get_user()
    print('Info: test_user_get: %s' % repr(user_info))
    assert user_info is None


def test_ensure_user_get_called_not_found():
    ''' a more interesting test '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['user_not_found']),
    ])
    module_args = {
        'use_rest': 'never',
        'role_name': 'test',
        'applications': 'http',
        'authentication_method': 'password',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    # app = dict(application='testapp', authentication_methods=['testam'])
    user_info = my_obj.get_user()
    print('Info: test_user_get: %s' % repr(user_info))
    assert user_info is None


def test_ensure_user_apply_called():
    ''' creating user and checking idempotency '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['success']),
        ('ZAPI', 'security-login-create', ZRR['success']),
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user_http']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'create',
        'role_name': 'user',
        'applications': 'http',
        'authentication_method': 'password',
    }
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
        'use_rest': 'never',
        'name': 'create',
        'role_name': 'user',
        'applications': 'service-processor',
        'authentication_method': 'password',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['applications'] = 'service_processor'
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_apply_for_delete_called():
    ''' deleting user and checking idempotency '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-delete', ZRR['success']),
        ('ZAPI', 'security-login-get-iter', ZRR['no_records']),
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
        'name': 'create',
        'role_name': 'user',
        'applications': 'console',
        'authentication_method': 'password',
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
        'applications': 'console',
        'authentication_method': 'password',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['lock_user'] = 'true'
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
        'applications': 'console',
        'authentication_method': 'password',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['lock_user'] = 'false'
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_user_set_password_called():
    ''' set password '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-modify-password', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'create',
        'role_name': 'user',
        'applications': 'console',
        'authentication_method': 'password',
        'set_password': '123456',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_set_password_internal_error():
    ''' set password '''
    register_responses([
        ('ZAPI', 'security-login-modify-password', ZRR['internal_error']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'create',
        'role_name': 'user',
        'applications': 'console',
        'authentication_method': 'password',
        'set_password': '123456',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert not my_obj.change_password()


def test_set_password_reused():
    ''' set password '''
    register_responses([
        ('ZAPI', 'security-login-modify-password', ZRR['reused_password'])
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'create',
        'role_name': 'user',
        'applications': 'console',
        'authentication_method': 'password',
        'set_password': '123456',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert not my_obj.change_password()


def test_ensure_user_role_update_called():
    ''' set password '''
    register_responses([
        ('ZAPI', 'security-login-get-iter', ZRR['login_unlocked_user']),
        ('ZAPI', 'security-login-modify', ZRR['success']),
        ('ZAPI', 'security-login-modify-password', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'create',
        'role_name': 'test123',
        'applications': 'console',
        'authentication_method': 'password',
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
        'use_rest': 'never',
        'name': 'create',
        'role_name': 'test123',
        'applications': 'http',
        'authentication_method': 'password',
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
        'use_rest': 'never',
        'role_name': 'test',
        'applications': 'console',
        'authentication_method': 'password',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    app = dict(application='console', authentication_methods=['password'])
    assert zapi_error_message('Error getting user user_name') in expect_and_capture_ansible_exception(my_obj.get_user, 'fail')['msg']
    assert zapi_error_message('Error creating user user_name') in expect_and_capture_ansible_exception(my_obj.create_user, 'fail', app)['msg']
    assert zapi_error_message('Error locking user user_name') in expect_and_capture_ansible_exception(my_obj.lock_given_user, 'fail')['msg']
    assert zapi_error_message('Error unlocking user user_name') in expect_and_capture_ansible_exception(my_obj.unlock_given_user, 'fail')['msg']
    assert zapi_error_message('Error removing user user_name') in expect_and_capture_ansible_exception(my_obj.delete_user, 'fail', app)['msg']
    assert zapi_error_message('Error setting password for user user_name') in expect_and_capture_ansible_exception(my_obj.change_password, 'fail')['msg']
    assert zapi_error_message('Error modifying user user_name') in expect_and_capture_ansible_exception(my_obj.modify_user, 'fail', app, ['password'])['msg']
    err_msg = 'vserver is required with ZAPI'
    assert err_msg in create_module(my_module, DEFAULT_ARGS, {'use_rest': 'never', 'svm': None}, fail=True)['msg']


def test_create_user_with_usm_auth():
    ''' switching back to ZAPI '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('ZAPI', 'security-login-get-iter', ZRR['no_records']),
        ('ZAPI', 'security-login-create', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'auto',
        'applications': 'snmp',
        'authentication_method': 'usm',
        'name': 'create',
        'role_name': 'test123',
        'set_password': '123456',
        'remote_switch_ipaddress': '12.34.56.78',
        'authentication_password': 'auth_pwd',
        'authentication_protocol': 'md5',
        'privacy_password': 'auth_pwd',
        'privacy_protocol': 'des',
        'engine_id': 'engine_123',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_applications_snmp():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    module_args = {
        'use_rest': 'always',
        'applications': 'snmp',
        'authentication_method': 'usm',
        'name': 'create',
        'role_name': 'test123',
        'set_password': '123456',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == "snmp as application is not supported in REST."


def test_ensure_user_get_rest_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
    ])
    module_args = {
        "use_rest": "always",
        'role_name': 'vsadmin',
        'applications': ['http', 'ontapi'],
        'authentication_method': 'password',
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
        'applications': ['http', 'ontapi'],
        'authentication_method': 'password',
        'set_password': 'xfjjttjwll`1',
        'lock_user': True
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_create_cluster_user_rest_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['zero_records']),
        ('POST', 'security/accounts', SRR['empty_good']),
    ])
    module_args = {
        "hostname": "hostname",
        "username": "username",
        "password": "password",
        "name": "user_name",
        "use_rest": "always",
        'role_name': 'vsadmin',
        'applications': ['http', 'ontapi'],
        'authentication_method': 'password',
        'set_password': 'xfjjttjwll`1',
        'lock_user': True
    }
    assert call_main(my_main, module_args)['changed']


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
        'applications': ['http', 'ontapi'],
        'authentication_method': 'password',
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
        'application': 'ssh',
        'authentication_method': 'password',
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
        'applications': 'http',
        'authentication_method': 'password',
        'lock_user': True,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_change_password_user_rest_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['empty_good']),
    ])
    module_args = {
        'set_password': 'newvalue',
        'use_rest': 'always',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_change_password_user_rest_check_mode():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
    ])
    module_args = {
        'set_password': 'newvalue',
        'use_rest': 'always',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    my_obj.module.check_mode = True
    assert expect_and_capture_ansible_exception(my_obj.apply, 'exit')['changed']


def test_existing_password():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['repeated_password']),  # password
    ])
    module_args = {
        'set_password': 'newvalue',
        'use_rest': 'always',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_negative_rest_unsupported_property():
    register_responses([
    ])
    module_args = {
        'privacy_password': 'value',
        'use_rest': 'always',
    }
    msg = "REST API currently does not support 'privacy_password'"
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_negative_zapi_missing_netapp_lib(mock_has):
    register_responses([
    ])
    mock_has.return_value = False
    module_args = {
        'use_rest': 'never',
    }
    msg = "Error: the python NetApp-Lib module is required.  Import error: None"
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_zapi_missing_apps():
    register_responses([
    ])
    module_args = {
        'use_rest': 'never',
    }
    msg = "application_dicts or application_strs is a required parameter with ZAPI"
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_rest_error_on_get_user():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    msg = "Error while fetching user info: Expected error"
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_rest_error_on_get_user_multiple():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest_multiple']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    msg = "Error while fetching user info, found multiple entries:"
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_rest_error_on_get_user_details():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    msg = "Error while fetching user details: Expected error"
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_rest_error_on_delete():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
        ('DELETE', 'security/accounts/ansible_vserver/abcd', SRR['generic_error']),
    ])
    module_args = {
        "use_rest": "always",
        'state': 'absent',
        'role_name': 'vsadmin',
    }
    msg = "Error while deleting user: Expected error"
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_rest_error_on_unlocking():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
        'lock_user': True
    }
    msg = "Error while locking/unlocking user: Expected error"
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_rest_error_on_unlocking_no_password():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest_no_pwd']),
    ])
    module_args = {
        'use_rest': 'always',
        'lock_user': True
    }
    msg = "Error: cannot modify lock state if password is not set."
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_rest_error_on_changing_password():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['generic_error']),
    ])
    module_args = {
        'set_password': '12345',
        'use_rest': 'always',
    }
    msg = "Error while updating user password: Expected error"
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_rest_error_on_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['generic_error']),
    ])
    module_args = {
        'role_name': 'vsadmin2',
        'use_rest': 'always',
        'applications': ['http', 'ontapi'],
        'authentication_method': 'password',
    }
    msg = "Error while modifying user details: Expected error"
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_unlocking_with_password():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['get_user_rest']),
        ('GET', 'security/accounts/ansible_vserver/abcd', SRR['get_user_details_rest_no_pwd']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['success']),
        ('PATCH', 'security/accounts/ansible_vserver/abcd', SRR['success']),
    ])
    module_args = {
        'set_password': 'ansnssnajj12%',
        'use_rest': 'always',
        'lock_user': True
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_negative_create_validations():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['zero_records']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['zero_records']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/accounts', SRR['zero_records']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    msg = 'Error: missing required parameters for create: role_name and: application_dicts or application_strs.'
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['role_name'] = 'role'
    msg = 'Error: missing required parameter for create: application_dicts or application_strs.'
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args.pop('role_name')
    module_args['applications'] = 'http'
    module_args['authentication_method'] = 'password'
    msg = 'Error: missing required parameter for create: role_name.'
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
