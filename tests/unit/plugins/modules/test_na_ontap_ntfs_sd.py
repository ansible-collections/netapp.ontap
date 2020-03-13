# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_ntfs_sd'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ntfs_sd \
    import NetAppOntapNtfsSd as sd_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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
        elif request.startswith("<file-directory-security-ntfs-get-iter>"):
            if self.kind == 'create':
                xml = self.build_sd_info()
            else:
                xml = self.build_sd_info(self.params)
        elif request.startswith("<file-directory-security-ntfs-modify>"):
            xml = self.build_sd_info(self.params)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_sd_info(data=None):
        xml = netapp_utils.zapi.NaElement('xml')
        vserver = 'vserver'
        attributes = {'num-records': 1,
                      'attributes-list': {'file-directory-security-ntfs': {'vserver': vserver}}}
        if data is not None:
            if data.get('name'):
                attributes['attributes-list']['file-directory-security-ntfs']['ntfs-sd'] = data['name']
            if data.get('owner'):
                attributes['attributes-list']['file-directory-security-ntfs']['owner'] = data['owner']
            if data.get('group'):
                attributes['attributes-list']['file-directory-security-ntfs']['group'] = data['group']
            if data.get('control_flags_raw'):
                attributes['attributes-list']['file-directory-security-ntfs']['control-flags-raw'] = str(data['control_flags_raw'])
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_ntfs_sd '''

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

    def get_sd_mock_object(self, type='zapi', kind=None, status=None):
        sd_obj = sd_module()
        netapp_utils.ems_log_event = Mock(return_value=None)
        if type == 'zapi':
            if kind is None:
                sd_obj.server = MockONTAPConnection()
            else:
                sd_obj.server = MockONTAPConnection(kind=kind, data=status)
        return sd_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            sd_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_successfully_create_sd(self):
        data = self.mock_args()
        data['name'] = 'sd_test'
        data['owner'] = 'user_test'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_sd_mock_object('zapi', 'create', data).apply()
        assert exc.value.args[0]['changed']

    def test_create_sd_idempotency(self):
        data = self.mock_args()
        data['name'] = 'sd_test'
        data['owner'] = 'user_test'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_sd_mock_object('zapi', 'create_idempotency', data).apply()
        assert not exc.value.args[0]['changed']

    def test_successfully_modify_sd(self):
        data = self.mock_args()
        data['name'] = 'sd_test'
        data['owner'] = 'user_test'
        data['control_flags_raw'] = 1
        set_module_args(data)
        data['control_flags_raw'] = 2
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_sd_mock_object('zapi', 'create', data).apply()
        assert exc.value.args[0]['changed']

    def test_modify_sd_idempotency(self):
        data = self.mock_args()
        data['name'] = 'sd_test'
        data['owner'] = 'user_test'
        data['control_flags_raw'] = 2
        set_module_args(data)
        data['control_flags_raw'] = 2
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_sd_mock_object('zapi', 'modify_idempotency', data).apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ntfs_sd.NetAppOntapNtfsSd.get_ntfs_sd')
    def test_modify_error(self, get_info):
        data = self.mock_args()
        data['name'] = 'sd_test'
        data['owner'] = 'user_test'
        data['control_flags_raw'] = 2
        set_module_args(data)
        get_info.side_effect = [
            {
                'name': 'sd_test',
                'control_flags_raw': 1
            }
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_sd_mock_object('zapi', 'error', data).apply()
        print(exc)
        assert exc.value.args[0]['msg'] == 'Error modifying NTFS security descriptor sd_test: NetApp API failed. Reason - test:expect error'

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ntfs_sd.NetAppOntapNtfsSd.get_ntfs_sd')
    def test_create_error(self, get_info):
        data = self.mock_args()
        data['name'] = 'sd_test'
        data['owner'] = 'user_test'
        set_module_args(data)
        get_info.side_effect = [
            None
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_sd_mock_object('zapi', 'error', data).apply()
        print(exc)
        assert exc.value.args[0]['msg'] == 'Error creating NTFS security descriptor sd_test: NetApp API failed. Reason - test:expect error'

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ntfs_sd.NetAppOntapNtfsSd.get_ntfs_sd')
    def test_delete_error(self, get_info):
        data = self.mock_args()
        data['name'] = 'sd_test'
        data['owner'] = 'user_test'
        data['state'] = 'absent'
        set_module_args(data)
        get_info.side_effect = [
            {
                'name': 'sd_test',
                'owner': 'user_test'
            }
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_sd_mock_object('zapi', 'error', data).apply()
        print(exc)
        assert exc.value.args[0]['msg'] == 'Error deleting NTFS security descriptor sd_test: NetApp API failed. Reason - test:expect error'
