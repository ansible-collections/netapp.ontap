# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_ntfs_dacl'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ntfs_dacl \
    import NetAppOntapNtfsDacl as dacl_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')
HAS_NETAPP_ZAPI_MSG = "pip install netapp_lib is required"


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""
    pass


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""
    pass


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

    def __init__(self, kind=None, data=None):
        ''' save arguments '''
        self.kind = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        request = xml.to_string().decode('utf-8')
        if self.kind == 'error':
            raise netapp_utils.zapi.NaApiError('test', 'expect error')
        elif request.startswith("<ems-autosupport-log>"):
            xml = None  # or something that may the logger happy, and you don't need @patch anymore
            # or
            # xml = build_ems_log_response()
        elif request.startswith("<file-directory-security-ntfs-dacl-get-iter>"):
            if self.kind == 'create':
                xml = self.build_dacl_info()
            else:
                xml = self.build_dacl_info(self.params)
        elif request.startswith("<file-directory-security-ntfs-dacl-modify>"):
            xml = self.build_dacl_info(self.params)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_dacl_info(data=None):
        xml = netapp_utils.zapi.NaElement('xml')
        vserver = 'vserver'
        attributes = {'num-records': '0',
                      'attributes-list': {'file-directory-security-ntfs-dacl': {'vserver': vserver}}}

        if data is not None:
            attributes['num-records'] = '1'
            if data.get('access_type'):
                attributes['attributes-list']['file-directory-security-ntfs-dacl']['access-type'] = data['access_type']
            if data.get('account'):
                attributes['attributes-list']['file-directory-security-ntfs-dacl']['account'] = data['account']
            if data.get('rights'):
                attributes['attributes-list']['file-directory-security-ntfs-dacl']['rights'] = data['rights']
            if data.get('advanced_rights'):
                attributes['attributes-list']['file-directory-security-ntfs-dacl']['advanced-rights'] = data['advanced_rights']
            if data.get('apply_to'):
                tmp = []
                for target in data['apply_to']:
                    tmp.append({'inheritance-level': target})
                attributes['attributes-list']['file-directory-security-ntfs-dacl']['apply-to'] = tmp
            if data.get('security_descriptor'):
                attributes['attributes-list']['file-directory-security-ntfs-dacl']['ntfs-sd'] = data['security_descriptor']
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_ntfs_dacl '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)

    def mock_args(self):
        return {
            'vserver': 'vserver',
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_dacl_mock_object(self, type='zapi', kind=None, status=None):
        dacl_obj = dacl_module()
        dacl_obj.autosupport_log = Mock(return_value=None)
        if type == 'zapi':
            if kind is None:
                dacl_obj.server = MockONTAPConnection()
            else:
                dacl_obj.server = MockONTAPConnection(kind=kind, data=status)
        return dacl_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            dacl_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_dacl_error(self):
        data = self.mock_args()
        data['access_type'] = 'allow'
        data['account'] = 'acc_test'
        data['rights'] = 'full_control'
        data['security_descriptor'] = 'sd_test'
        data['apply_to'] = 'this_folder,files'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_dacl_mock_object('zapi', 'error', data).apply()
        msg = 'Error fetching allow DACL for account acc_test for security descriptor sd_test: NetApp API failed. Reason - test:expect error'
        assert exc.value.args[0]['msg'] == msg

    def test_successfully_create_dacl(self):
        data = self.mock_args()
        data['access_type'] = 'allow'
        data['account'] = 'acc_test'
        data['rights'] = 'full_control'
        data['security_descriptor'] = 'sd_test'
        data['apply_to'] = 'this_folder,files'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dacl_mock_object('zapi', 'create', data).apply()
        assert exc.value.args[0]['changed']

    def test_create_dacl_idempotency(self):
        data = self.mock_args()
        data['access_type'] = 'allow'
        data['account'] = 'acc_test'
        data['rights'] = 'full_control'
        data['security_descriptor'] = 'sd_test'
        data['apply_to'] = ['this_folder', 'files']
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dacl_mock_object('zapi', 'create_idempotency', data).apply()
        assert not exc.value.args[0]['changed']

    def test_successfully_modify_dacl(self):
        data = self.mock_args()
        data['access_type'] = 'allow'
        data['account'] = 'acc_test'
        data['rights'] = 'full_control'
        data['security_descriptor'] = 'sd_test'
        data['apply_to'] = ['this_folder', 'files']
        set_module_args(data)
        data['advanced_rights'] = 'read_data,write_data'
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dacl_mock_object('zapi', 'create', data).apply()
        assert exc.value.args[0]['changed']

    def test_modify_dacl_idempotency(self):
        data = self.mock_args()
        data['access_type'] = 'allow'
        data['account'] = 'acc_test'
        data['rights'] = 'full_control'
        data['security_descriptor'] = 'sd_test'
        data['apply_to'] = ['this_folder', 'files']
        set_module_args(data)
        data['rights'] = 'full_control'
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dacl_mock_object('zapi', 'modify_idempotency', data).apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ntfs_dacl.NetAppOntapNtfsDacl.get_dacl')
    def test_modify_error(self, get_info):
        data = self.mock_args()
        data['access_type'] = 'allow'
        data['account'] = 'acc_test'
        data['rights'] = 'full_control'
        data['security_descriptor'] = 'sd_test'
        set_module_args(data)
        get_info.side_effect = [
            {
                'access_type': 'allow',
                'account': 'acc_test',
                'security_descriptor': 'sd_test',
                'rights': 'modify',
                'apply_to': ['this_folder', 'files']
            }
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_dacl_mock_object('zapi', 'error', data).apply()
        msg = 'Error modifying allow DACL for account acc_test for security descriptor sd_test: NetApp API failed. Reason - test:expect error'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ntfs_dacl.NetAppOntapNtfsDacl.get_dacl')
    def test_create_error(self, get_info):
        data = self.mock_args()
        data['access_type'] = 'allow'
        data['account'] = 'acc_test'
        data['rights'] = 'full_control'
        data['security_descriptor'] = 'sd_test'
        set_module_args(data)
        get_info.side_effect = [
            None
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_dacl_mock_object('zapi', 'error', data).apply()
        msg = 'Error adding allow DACL for account acc_test for security descriptor sd_test: NetApp API failed. Reason - test:expect error'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ntfs_dacl.NetAppOntapNtfsDacl.get_dacl')
    def test_delete_error(self, get_info):
        data = self.mock_args()
        data['access_type'] = 'allow'
        data['account'] = 'acc_test'
        data['rights'] = 'full_control'
        data['security_descriptor'] = 'sd_test'
        data['state'] = 'absent'
        set_module_args(data)
        get_info.side_effect = [
            {
                'access_type': 'allow',
                'account': 'acc_test',
                'security_descriptor': 'sd_test',
                'rights': 'modify'
            }
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_dacl_mock_object('zapi', 'error', data).apply()
        msg = 'Error deleting allow DACL for account acc_test for security descriptor sd_test: NetApp API failed. Reason - test:expect error'
        assert exc.value.args[0]['msg'] == msg
