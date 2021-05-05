# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_user '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

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


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


def exit_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


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

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
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
                'attributes-list': {
                    'security-login-account-info': {
                        'is-locked': locked, 'role-name': role_name, 'application': 'console', 'authentication-method': 'password'}}}

        xml.translate_struct(data)
        print(xml.to_string())
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.server = MockONTAPConnection()
        self.onbox = False

    def set_default_args(self, rest=False):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            user_name = 'test'
            vserver = 'ansible_test'
            application = 'console'
            authentication_method = 'password'
        else:
            hostname = 'hostname'
            username = 'username'
            password = 'password'
            user_name = 'name'
            vserver = 'vserver'
            application = 'console'
            authentication_method = 'password'
        if rest:
            use_rest = 'auto'
        else:
            use_rest = 'never'

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
        module_args.update({'role_name': 'test'})
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.server = self.server
        user_info = my_obj.get_user()
        print('Info: test_user_get: %s' % repr(user_info))
        assert user_info is None

    def test_ensure_user_apply_called(self):
        ''' creating user and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args.update({'name': 'create'})
        module_args.update({'role_name': 'test'})
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
        module_args.update({'name': 'create'})
        module_args.update({'role_name': 'test'})
        module_args.update({'application': 'service-processor'})
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
        # creating user with service_processor application and idempotency
        module_args.update({'application': 'service_processor'})
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
        module_args.update({'name': 'create'})
        module_args.update({'role_name': 'test'})
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false', 'test')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        module_args.update({'state': 'absent'})
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
        module_args.update({'name': 'create'})
        module_args.update({'role_name': 'test'})
        module_args.update({'lock_user': 'false'})
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false', 'test')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        module_args.update({'lock_user': 'true'})
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
        module_args.update({'name': 'create'})
        module_args.update({'role_name': 'test'})
        module_args.update({'lock_user': 'false'})
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('user', 'false', 'test')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_user_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        module_args.update({'lock_user': 'false'})
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
        module_args.update({'name': 'create'})
        module_args.update({'role_name': 'test'})
        module_args.update({'set_password': '123456'})
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
        module_args.update({'name': 'create'})
        module_args.update({'role_name': 'test123'})
        module_args.update({'set_password': '123456'})
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
        module_args.update({'name': 'create'})
        module_args.update({'role_name': 'test123'})
        module_args.update({'application': 'http'})
        module_args.update({'set_password': '123456'})
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


@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_user_get_rest_called(mock_request, mock_fail):
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_user_rest'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args_rest())
    my_obj = my_module()
    assert my_obj.get_user_rest() is not None


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_create_user_rest_called(mock_request, mock_fail, mock_exit):
    mock_fail.side_effect = fail_json
    mock_exit.side_effect = exit_json
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


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_user_rest_called(mock_request, mock_fail, mock_exit):
    mock_fail.side_effect = fail_json
    mock_exit.side_effect = exit_json
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
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_modify_user_rest_called(mock_request, mock_fail, mock_exit):
    mock_fail.side_effect = fail_json
    mock_exit.side_effect = exit_json
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


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_lock_unlock_user_rest_called(mock_request, mock_fail, mock_exit):
    mock_fail.side_effect = fail_json
    mock_exit.side_effect = exit_json
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


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_change_password_user_rest_called(mock_request, mock_fail, mock_exit):
    mock_fail.side_effect = fail_json
    mock_exit.side_effect = exit_json
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


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_sp_retry(mock_request, mock_fail, mock_exit):
    """simulate error in create_user_rest and retry"""
    mock_fail.side_effect = fail_json
    mock_exit.side_effect = exit_json
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
    data.update({
        'application_dicts': [app],
    })
    print(data)
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert 'service_processor' in repr(mock_request.mock_calls[-1])
    assert exc.value.args[0]['changed']
