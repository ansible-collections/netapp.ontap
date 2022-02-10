# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_user '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_user \
    import NetAppOntapUser as my_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_records': (200, {'num_records': 0}, None),
    'end_of_sequence': (500, None, "Ooops, the UT needs one more SRR response"),
    'generic_error': (400, None, "Expected error"),
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
}


def set_default_args_rest_zapi():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'name': 'user_name',
        'vserver': 'vserver',
        'applications': 'http',
        'authentication_method': 'password',
        'role_name': 'vsadmin',
        'lock_user': True,
    })


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None, parm1=None, parm2=None):
        ''' save arguments '''
        self.type = kind
        self.parm1 = parm1
        self.parm2 = parm2
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'user':
            xml = self.build_user_info(self.parm1, self.parm2)
        elif self.type == 'user_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        elif self.type == 'user_not_found':
            raise netapp_utils.zapi.NaApiError(code='16034', message="This exception should not be seen")
        elif self.type == 'internal_error':
            raise netapp_utils.zapi.NaApiError(code='13114', message="Forcing an internal error")
        elif self.type == 'repeated_password':
            # python3.9/site-packages/netapp_lib/api/zapi/errors.py
            raise netapp_utils.zapi.NaApiError(code='13214', message="New password must be different than last 6 passwords.")
        self.xml_out = xml
        return xml

    @staticmethod
    def set_vserver(vserver):
        '''mock set vserver'''

    @staticmethod
    def build_user_info(locked, role_name):
        ''' build xml data for user-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1,
                'attributes-list': {
                    'security-login-account-info': {
                        'is-locked': locked, 'role-name': role_name, 'application': 'console', 'authentication-method': 'password'}}}

        xml.translate_struct(data)
        print(xml.to_string())
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.server = MockONTAPConnection()
        self.onbox = False

    def set_default_args(self, rest=False):
        if self.onbox:
            hostname = '10.10.10.10'
            user_name = 'test'
            vserver = 'ansible_test'
        else:
            hostname = 'hostname'
            user_name = 'name'
            vserver = 'vserver'
        password = 'password'
        username = 'username'
        application = 'console'
        authentication_method = 'password'
        use_rest = 'auto' if rest else 'never'
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'use_rest': use_rest,
            'name': user_name,
            'vserver': vserver,
            'applications': application,
            'authentication_method': authentication_method
        })

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_user_get_called(self):
        ''' a more interesting test '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['role_name'] = 'test'
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.server = self.server
        # app = dict(application='testapp', authentication_methods=['testam'])
        user_info = my_obj.get_user()
        print('Info: test_user_get: %s' % repr(user_info))
        assert user_info is None

    def test_ensure_user_get_called_not_found(self):
        ''' a more interesting test '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['role_name'] = 'test'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user_not_found', 'false')
        # app = dict(application='testapp', authentication_methods=['testam'])
        user_info = my_obj.get_user()
        print('Info: test_user_get: %s' % repr(user_info))
        assert user_info is None

    def test_ensure_user_apply_called(self):
        ''' creating user and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_ensure_user_sp_apply_called(self):
        ''' creating user with service_processor application and idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test'
        module_args['application'] = 'service-processor'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_sp: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_sp: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        module_args['application'] = 'service_processor'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_sp: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_sp: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_ensure_user_apply_for_delete_called(self):
        ''' deleting user and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false', 'test')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        module_args['state'] = 'absent'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false', 'test')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_delete: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_ensure_user_lock_called(self):
        ''' changing user_lock to True and checking idempotency'''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test'
        module_args['lock_user'] = 'false'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false', 'test')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        module_args['lock_user'] = 'true'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_lock: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_ensure_user_unlock_called(self):
        ''' changing user_lock to False and checking idempotency'''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test'
        module_args['lock_user'] = 'false'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false', 'test')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        module_args['lock_user'] = 'false'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'true', 'test')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_unlock: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_ensure_user_set_password_called(self):
        ''' set password '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test'
        module_args['set_password'] = '123456'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'true')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_set_password_internal_error(self):
        ''' set password '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test'
        module_args['set_password'] = '123456'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('internal_error', 'true')
        assert not my_obj.change_password()

    def test_set_password_reused(self):
        ''' set password '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test'
        module_args['set_password'] = '123456'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('repeated_password', 'true')
        assert not my_obj.change_password()

    def test_ensure_user_role_update_called(self):
        ''' set password '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test123'
        module_args['set_password'] = '123456'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'true')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_ensure_user_role_update_additional_application_called(self):
        ''' set password '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test123'
        module_args['application'] = 'http'
        module_args['set_password'] = '123456'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'true')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args()
        data.update({'role_name': 'test'})
        set_module_args(data)
        my_obj = my_module()
        app = dict(application='console', authentication_methods=['password'])
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.get_user()
        assert 'Error getting user ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_user(app)
        assert 'Error creating user ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.lock_given_user()
        assert 'Error locking user ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.unlock_given_user()
        assert 'Error unlocking user ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.delete_user(app)
        assert 'Error removing user ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.change_password()
        assert 'Error setting password for user ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_user(app, ['password'])
        assert 'Error modifying user ' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_create_user_with_usm_auth(self, mock_request):
        data = self.set_default_args(rest=True)
        data.update({'applications': 'snmp'})
        data.update({'authentication_method': 'usm'})
        data.update({'name': 'create'})
        data.update({'role_name': 'test123'})
        data.update({'set_password': '123456'})
        data.update({'remote_switch_ipaddress': '12.34.56.78'})
        data.update({'authentication_password': 'auth_pwd'})
        data.update({'authentication_protocol': 'md5'})
        data.update({'privacy_password': 'auth_pwd'})
        data.update({'privacy_protocol': 'des'})
        data.update({'engine_id': 'engine_123'})
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        my_obj.server = MockONTAPConnection('user', 'true')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_applications_snmp(self, mock_request):
        data = self.set_default_args(rest=True)
        data.update({'applications': 'snmp'})
        data.update({'name': 'create'})
        data.update({'role_name': 'test123'})
        data.update({'set_password': '123456'})
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            my_module()
        assert exc.value.args[0]['msg'] == "snmp as application is not supported in REST."


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_user_get_rest_called(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args_rest_zapi())
    my_obj = my_module()
    assert my_obj.get_user_rest() is not None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_create_user_rest_called(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_records'],            # get
        SRR['empty_good'],              # create
        SRR['end_of_sequence']
    ]
    data = {'set_password': 'xfjjttjwll`1'}
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_user_rest_called(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['get_user_rest'],
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'state': 'absent',
    }
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_modify_user_rest_called(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['get_user_rest'],
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'application': 'ssh',
    }
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_lock_unlock_user_rest_called(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['empty_good'],      # modify
        SRR['empty_good'],      # lock
        SRR['end_of_sequence']
    ]
    data = {
        'lock_user': 'newvalue',
    }
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']
    print(mock_request.mock_calls)
    # kwargs requires 2.7 or >= 3.8
    if sys.version_info == (2, 7) or sys.version_info >= (3, 8):
        print(mock_request.mock_calls[4].kwargs)
        assert 'json' in mock_request.mock_calls[4].kwargs
        assert 'locked' in mock_request.mock_calls[4].kwargs['json']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_change_password_user_rest_called(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['empty_good'],  # password
        SRR['end_of_sequence']
    ]
    data = {
        'set_password': 'newvalue',
    }
    data.update(set_default_args_rest_zapi())
    data.pop('applications')
    data.pop('authentication_method')
    data['lock_user'] = False
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']
    print(mock_request.mock_calls)
    # kwargs requires 2.7 or >= 3.8
    if sys.version_info == (2, 7) or sys.version_info >= (3, 8):
        print(mock_request.mock_calls[3].kwargs)
        assert 'json' in mock_request.mock_calls[3].kwargs
        assert 'password' in mock_request.mock_calls[3].kwargs['json']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_change_password_user_rest_check_mode(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['end_of_sequence']
    ]
    data = {
        'set_password': 'newvalue',
    }
    data.update(set_default_args_rest_zapi())
    data.pop('applications')
    data.pop('authentication_method')
    data['lock_user'] = False
    set_module_args(data)
    my_obj = my_module()
    my_obj.module.check_mode = True
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_existing_password(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['repeated_password'],  # password
        SRR['end_of_sequence']
    ]
    data = {
        'set_password': 'newvalue',
    }
    data.update(set_default_args_rest_zapi())
    data.pop('applications')
    data.pop('authentication_method')
    data['lock_user'] = False
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    # kwargs requires 2.7 or >= 3.8
    if sys.version_info == (2, 7) or sys.version_info >= (3, 8):
        print(mock_request.mock_calls[3].kwargs)
        assert 'json' in mock_request.mock_calls[3].kwargs
        assert 'password' in mock_request.mock_calls[3].kwargs['json']
    assert not exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_rest_unsupported_property(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    data = {
        'privacy_password': 'value',
        'use_rest': 'always',
    }
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = "REST API currently does not support 'privacy_password'"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_negative_zapi_missing_netapp_lib(mock_has, mock_request):
    mock_request.side_effect = [
        SRR['is_zapi'],
        SRR['end_of_sequence']
    ]
    mock_has.return_value = False
    data = {
    }
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = "Error: the python NetApp-Lib module is required.  Import error: None"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_zapi_missing_apps(mock_request):
    mock_request.side_effect = [
        SRR['is_zapi'],
        SRR['end_of_sequence']
    ]
    data = {}
    data.update(set_default_args_rest_zapi())
    data.pop('applications')
    data.pop('authentication_method')
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = "application_dicts or application_strs is a required parameter with ZAPI"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_rest_error_on_get_user(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    data = {}
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_main()
    msg = "Error while fetching user info: Expected error"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_rest_error_on_get_user_multiple(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest_multiple'],
        SRR['end_of_sequence']
    ]
    data = {}
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_main()
    msg = "Error while fetching user info, found multiple entries:"
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_rest_error_on_get_user_details(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    data = {}
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_main()
    msg = "Error while fetching user details: Expected error"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_rest_error_on_delete(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    data = {'state': 'absent'}
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_main()
    msg = "Error while deleting user: Expected error"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_rest_error_on_unlocking(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['empty_good'],              # modify
        SRR['generic_error'],           # unlock
        SRR['end_of_sequence']
    ]
    data = {}
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_main()
    print(mock_request.mock_calls)
    msg = "Error while locking/unlocking user: Expected error"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_rest_error_on_unlocking_no_password(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest_no_pwd'],
        SRR['end_of_sequence']
    ]
    data = {}
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_main()
    msg = "Error: cannot modify lock state if password is not set."
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_rest_error_on_changing_password(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['empty_good'],              # modify
        SRR['generic_error'],           # password
        SRR['end_of_sequence']
    ]
    data = {'set_password': '12345'}
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_main()
    msg = "Error while updating user password: Expected error"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_rest_error_on_modify(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['generic_error'],           # modify
        SRR['end_of_sequence']
    ]
    data = {'set_password': '12345'}
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_main()
    msg = "Error while modifying user details: Expected error"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_unlocking_with_password(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest_no_pwd'],
        SRR['empty_good'],              # modify
        SRR['empty_good'],              # password
        SRR['empty_good'],              # lock
        SRR['end_of_sequence']
    ]
    data = {
        'set_password': 'ansnssnajj12%'
    }
    data.update(set_default_args_rest_zapi())
    set_module_args(data)
    with pytest.raises(AnsibleExitJson) as exc:
        my_main()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed']
    assert len(mock_request.mock_calls) == 6


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_create_validations(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_records'],            # get
        SRR['is_rest'],
        SRR['zero_records'],            # get
        SRR['is_rest'],
        SRR['zero_records'],            # get
        SRR['end_of_sequence']
    ]
    data = {}
    data.update(set_default_args_rest_zapi())
    data.pop('role_name')
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = 'Error: missing required parameter for create: role_name.'
    assert msg == exc.value.args[0]['msg']
    data.pop('applications')
    data.pop('authentication_method')
    data['role_name'] = 'role'
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = 'Error: missing required parameter for create: application_dicts or application_strs.'
    assert msg == exc.value.args[0]['msg']
    data.pop('role_name')
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = 'Error: missing required parameters for create: role_name and: application_dicts or application_strs.'
    assert msg == exc.value.args[0]['msg']
