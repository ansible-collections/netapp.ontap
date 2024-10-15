# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_file_directory_policy '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_file_directory_policy \
    import NetAppOntapFilePolicy as policy_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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
        elif request.startswith("<file-directory-security-policy-get-iter>"):
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
        attributes = {}
        if data is not None:
            attributes = {'num-records': 1,
                          'attributes-list': {'file-directory-security-policy': {'policy-name': data['policy_name']}}}
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_file_directory_policy '''

    def mock_args(self):
        return {
            'vserver': 'vserver',
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_policy_mock_object(self, type='zapi', kind=None, status=None):
        policy_obj = policy_module()
        if type == 'zapi':
            if kind is None:
                policy_obj.server = MockONTAPConnection()
            else:
                policy_obj.server = MockONTAPConnection(kind=kind, data=status)
        return policy_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            policy_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_successfully_create_policy(self):
        data = self.mock_args()
        data['policy_name'] = 'test_policy'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_policy_mock_object('zapi', 'create', data).apply()
        assert exc.value.args[0]['changed']

    def test_error(self):
        data = self.mock_args()
        data['policy_name'] = 'test_policy'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_policy_mock_object('zapi', 'error', data).get_policy_iter()
        assert exc.value.args[0]['msg'] == 'Error fetching file-directory policy test_policy: NetApp API failed. Reason - test:expect error'

        with pytest.raises(AnsibleFailJson) as exc:
            self.get_policy_mock_object('zapi', 'error', data).create_policy()
        assert exc.value.args[0]['msg'] == 'Error creating file-directory policy test_policy: NetApp API failed. Reason - test:expect error'

        with pytest.raises(AnsibleFailJson) as exc:
            self.get_policy_mock_object('zapi', 'error', data).remove_policy()
        assert exc.value.args[0]['msg'] == 'Error removing file-directory policy test_policy: NetApp API failed. Reason - test:expect error'

        data['path'] = '/vol'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_policy_mock_object('zapi', 'error', data).get_task_iter()
        assert exc.value.args[0]['msg'] == 'Error fetching task from file-directory policy test_policy: NetApp API failed. Reason - test:expect error'

        with pytest.raises(AnsibleFailJson) as exc:
            self.get_policy_mock_object('zapi', 'error', data).add_task_to_policy()
        assert exc.value.args[0]['msg'] == 'Error adding task to file-directory policy test_policy: NetApp API failed. Reason - test:expect error'

        with pytest.raises(AnsibleFailJson) as exc:
            self.get_policy_mock_object('zapi', 'error', data).remove_task_from_policy()
        assert exc.value.args[0]['msg'] == 'Error removing task from file-directory policy test_policy: NetApp API failed. Reason - test:expect error'

        with pytest.raises(AnsibleFailJson) as exc:
            self.get_policy_mock_object('zapi', 'error', data).modify_task(dict())
        assert exc.value.args[0]['msg'] == 'Error modifying task in file-directory policy test_policy: NetApp API failed. Reason - test:expect error'

        with pytest.raises(AnsibleFailJson) as exc:
            self.get_policy_mock_object('zapi', 'error', data).set_sd()
        assert exc.value.args[0]['msg'] == 'Error applying file-directory policy test_policy: NetApp API failed. Reason - test:expect error'
