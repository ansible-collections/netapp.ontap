# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_user '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_user \
    import NetAppOntapUser as my_module  # module under test

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
    'invalid_value_error': (400, None, {'message': "invalid value service_processor"}),
    'get_uuid': (200, {'owner': {'uuid': 'ansible'}}, None),
    'get_user_rest': (200,
                      {'num_records': 1,
                       'records': [{'owner': {'uuid': 'ansible_vserver'},
                                    'name': 'abcd'}]}, None),
    'get_user_details_rest': (200,
                              {'role': {'name': 'vsadmin'},
                               'applications': [{'application': 'http', 'second_authentication_method': 'none'}, ],
                               'locked': False}, None)
}


def set_default_args_rest():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'name': 'user_name',
        'vserver': 'vserver',
        'application_dicts':
            [dict(application='http', authentication_methods=['password']),
             dict(application='ontapi', authentication_methods=['password'])],
        'role_name': 'vsadmin',
        'lock_user': 'True',
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
        self.zapis = []

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        self.zapis.append(xml.to_string())
        if self.type == 'user':
            xml = self.build_user_info(self.parm1, self.parm2)
        elif self.type == 'user_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
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
                'attributes-list': [
                    {'security-login-account-info': {
                        'is-locked': locked, 'role-name': role_name, 'application': 'console', 'authentication-method': 'password'}},
                    {'security-login-account-info': {
                        'is-locked': locked, 'role-name': role_name, 'application': 'console', 'authentication-method': 'other'}},
                ]}

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
        user_info = my_obj.get_user()
        print('Info: test_user_get: %s' % repr(user_info))
        assert user_info is None

    def test_ensure_user_apply_called_replace(self):
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
        print(self.server.zapis)

    def test_ensure_user_apply_called_using_dict(self):
        ''' creating user and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test'
        module_args.pop('applications')
        module_args.pop('authentication_method')
        application = {
            'application': 'ssh',
            'authentication_methods': ['publickey'],
            'second_authentication_method': 'password'
        }
        module_args['application_dicts'] = [application]
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
        print(self.server.zapis)

    def test_ensure_user_apply_called_add(self):
        ''' creating user and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test'
        module_args['replace_existing_apps_and_methods'] = 'always'
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
        print(self.server.zapis)

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
        module_args['applications'] = 'http'
        module_args['set_password'] = '123456'
        module_args['replace_existing_apps_and_methods'] = 'always'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'true')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_ensure_user_role_update_additional_method_called(self):
        ''' set password '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['name'] = 'create'
        module_args['role_name'] = 'test123'
        module_args['applications'] = 'console'
        module_args['authentication_method'] = 'domain'
        module_args['set_password'] = '123456'
        module_args['replace_existing_apps_and_methods'] = 'always'
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
    set_module_args(set_default_args_rest())
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
    set_module_args(set_default_args_rest())
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
    data.update(set_default_args_rest())
    data['vserver'] = None
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
    app = dict(application='service_processor', authentication_methods=['usm'])
    data = set_default_args_rest()
    data.update({
        'application_dicts': [app],
    })
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
        SRR['get_user_rest'],
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'lock_user': 'newvalue',
    }
    data.update(set_default_args_rest())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_change_password_user_rest_called(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['get_user_details_rest'],
        SRR['get_user_rest'],
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'password': 'newvalue',
    }
    data.update(set_default_args_rest())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_sp_retry(mock_request):
    """simulate error in create_user_rest and retry"""
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_records'],            # get
        SRR['invalid_value_error'],    # create
        SRR['generic_error'],           # create
        SRR['end_of_sequence']
    ]
    app = dict(application='service_processor', authentication_methods=['usm'])
    data = dict(set_default_args_rest())
    data.update({
        'application_dicts': [app],
    })
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert 'invalid value' in exc.value.args[0]['msg']
    assert 'service-processor' in repr(mock_request.mock_calls[-1])

    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_records'],            # get
        SRR['invalid_value_error'],     # create
        SRR['empty_good'],              # create
        SRR['end_of_sequence']
    ]
    app = dict(application='service-processor', authentication_methods=['usm'])
    data['application_dicts'] = [app]
    print(data)
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert 'service_processor' in repr(mock_request.mock_calls[-1])
    assert exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_validate_application(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    data = dict(set_default_args_rest())
    set_module_args(data)
    my_obj = my_module()
    assert 'second_authentication_method' in my_obj.parameters['applications'][0]
    my_obj.parameters['applications'][0].pop('second_authentication_method')
    my_obj.validate_applications()
    assert 'second_authentication_method' in my_obj.parameters['applications'][0]
    assert my_obj.parameters['applications'][0]['second_authentication_method'] is None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_sp_transform(mock_request):
    current = {'applications': []}
    sp_app_u = 'service_processor'
    sp_app_d = 'service-processor'
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    # 1. no change using underscore
    data = dict(set_default_args_rest())
    data['application_dicts'].append({'application': sp_app_u, 'authentication_methods': ['password']})
    set_module_args(data)
    my_obj = my_module()
    my_obj.change_sp_application([])
    sp_apps = [application['application'] for application in my_obj.parameters['applications'] if application['application'].startswith('service')]
    assert sp_apps == [sp_app_u]
    # 2. change underscore -> dash
    my_obj.change_sp_application([{'application': sp_app_d}])
    sp_apps = [application['application'] for application in my_obj.parameters['applications'] if application['application'].startswith('service')]
    assert sp_apps == [sp_app_d]
    # 3. no change using dash
    data = dict(set_default_args_rest())
    data['application_dicts'].append({'application': sp_app_d, 'authentication_methods': ['password']})
    set_module_args(data)
    my_obj = my_module()
    my_obj.change_sp_application([])
    sp_apps = [application['application'] for application in my_obj.parameters['applications'] if application['application'].startswith('service')]
    assert sp_apps == [sp_app_d]
    # 4. change dash -> underscore
    my_obj.change_sp_application([{'application': sp_app_u}])
    sp_apps = [application['application'] for application in my_obj.parameters['applications'] if application['application'].startswith('service')]
    assert sp_apps == [sp_app_u]
