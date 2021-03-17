''' unit tests ONTAP Ansible module: na_ontap_cifs_local_user_modify '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_user_modify \
    import NetAppOntapCifsLocalUserModify as cifs_user_module  # module under test


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Ooops, the UT needs one more SRR response"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'cifs_user_record': (200, {
        "records": [{
            'vserver': 'ansible',
            'user_name': 'ANSIBLE\\Administrator',
            'is_account_disabled': False,
            'full_name': 'test user',
            'description': 'builtin admin'
        }]
    }, None)
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


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'local_user':
            xml = self.build_local_user_info()
        elif self.type == 'local_user_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_local_user_info():
        ''' build xml data for cifs-local-user '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes-list': {
                'cifs-local-user': {
                    'user-name': 'ANSIBLE\\Administrator',
                    'is-account-disabled': 'false',
                    'vserver': 'ansible',
                    'full-name': 'test user',
                    'description': 'builtin admin'
                }
            }
        }
        xml.translate_struct(data)
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

    def set_default_args(self, use_rest=None):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'ansible'
            name = 'ANSIBLE\\Administrator'
            is_account_disabled = False

        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'ansible'
            name = 'ANSIBLE\\Administrator'
            is_account_disabled = False

        args = dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'vserver': vserver,
            'name': name,
            'is_account_disabled': is_account_disabled
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_local_user_mock_object(cx_type='zapi', kind=None):
        local_user_obj = cifs_user_module()
        if cx_type == 'zapi':
            if kind is None:
                local_user_obj.server = MockONTAPConnection()
            else:
                local_user_obj.server = MockONTAPConnection(kind=kind)
        return local_user_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            cifs_user_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_cifs_local_user_modify for non-existent user'''
        set_module_args(self.set_default_args(use_rest='Never'))
        print('starting')
        my_obj = cifs_user_module()
        print('use_rest:', my_obj.use_rest)
        my_obj.server = self.server
        assert my_obj.get_cifs_local_user is not None

    def test_ensure_get_called_existing(self):
        ''' test get_cifs_local_user_modify for existing user'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = cifs_user_module()
        my_obj.server = MockONTAPConnection(kind='local_user')
        assert my_obj.get_cifs_local_user()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_user_modify.NetAppOntapCifsLocalUserModify.modify_cifs_local_user')
    def test_successful_modify(self, modify_cifs_local_user):
        ''' enabling local cifs user and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['is_account_disabled'] = True
        set_module_args(data)
        my_obj = cifs_user_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('local_user')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # to reset na_helper from remembering the previous 'changed' value
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = cifs_user_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('local_user')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = cifs_user_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('local_user_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_cifs_local_user(modify={})
        assert 'Error modifying local CIFS user' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_local_user_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['is_account_disabled'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['cifs_user_record'],  # get
            SRR['empty_good'],  # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_local_user_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_modify_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['cifs_user_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_local_user_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']
