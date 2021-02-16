''' unit tests ONTAP Ansible module: na_ontap_security_config '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_config \
    import NetAppOntapSecurityConfig as security_config_module  # module under test


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
    'security_config_record': (200, {
        "records": [{
            "interface": "ssl",
            "is_fips_enabled": False,
            "supported_protocols": ['TLSv1.2', 'TLSv1.1'],
            "supported_ciphers": 'ALL:!LOW:!aNULL:!EXP:!eNULL:!3DES:!DES:!RC4'
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
        if self.type == 'security_config':
            xml = self.build_security_config_info()
        elif self.type == 'security_config_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_security_config_info():
        ''' build xml data for cluster-security-config-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes': {
                'security-config-info': {
                    "interface": "ssl",
                    "is-fips-enabled": "false",
                    "supported-protocols": [
                        {"string": 'TLSv1.2'},
                        {"string": 'TLSv1.1'}
                    ],
                    "supported-ciphers": 'ALL:!LOW:!aNULL:!EXP:!eNULL:!3DES:!DES:!RC4'
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
            name = 'ssl'
            is_fips_enabled = False
            supported_protocols = ["TLSv1.2", "TLSv1.1"]
        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            name = 'ssl'
            is_fips_enabled = False
            supported_protocols = ["TLSv1.2", "TLSv1.1"]

        args = dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'name': name,
            'is_fips_enabled': is_fips_enabled,
            'supported_protocols': supported_protocols
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_security_config_mock_object(cx_type='zapi', kind=None):
        security_config_obj = security_config_module()
        if cx_type == 'zapi':
            if kind is None:
                security_config_obj.server = MockONTAPConnection()
            else:
                security_config_obj.server = MockONTAPConnection(kind=kind)
        return security_config_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            security_config_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_security_config for non-existent config'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = security_config_module()
        my_obj.server = self.server
        assert my_obj.get_security_config is not None

    def test_ensure_get_called_existing(self):
        ''' test get_security_config for existing config'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = security_config_module()
        my_obj.server = MockONTAPConnection(kind='security_config')
        assert my_obj.get_security_config()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_config.NetAppOntapSecurityConfig.modify_security_config')
    def test_successful_modify(self, modify_security_config):
        ''' modifying security_config and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['is_fips_enabled'] = True  # Modify to True
        set_module_args(data)
        my_obj = security_config_module()
        my_obj.ems_log_event = Mock(return_value=None)

        if not self.onbox:
            my_obj.server = MockONTAPConnection('security_config')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']

        #  reset na_helper from remembering the previous 'changed' value
        data['is_fips_enabled'] = False
        set_module_args(data)
        my_obj = security_config_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('security_config')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = security_config_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('security_config_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_security_config()
        assert 'Error modifying security config ' in exc.value.args[0]['msg']

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
            self.get_security_config_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['name'] = 'ssl'
        data['is_fips_enabled'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['security_config_record'],  # get
            SRR['empty_good'],  # delete
            SRR['empty_good'],  # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_security_config_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['name'] = 'ssl'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['security_config_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_security_config_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']
