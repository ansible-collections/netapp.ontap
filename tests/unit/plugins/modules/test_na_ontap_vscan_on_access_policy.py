# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_vscan_scanner_pool '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_vscan_on_access_policy \
    import NetAppOntapVscanOnAccessPolicy as policy_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')
HAS_NETAPP_ZAPI_MSG = "pip install netapp_lib is required"


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
        if self.kind == 'policy':
            xml = self.build_access_policy_info(self.params)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_access_policy_info(policy_details):
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {'num-records': 1,
                      'attributes-list': {'vscan-on-access-policy-info': {'policy-name': policy_details['policy_name']}}}
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_job_schedule '''

    def setUp(self):
        self.mock_access_policy = {
            'state': 'present',
            'vserver': 'test_vserver',
            'policy_name': 'test_carchi',
            'max_file_size': 2147483648 + 1     # 2GB + 1
        }

    def mock_args(self):
        return {
            'state': self.mock_access_policy['state'],
            'vserver': self.mock_access_policy['vserver'],
            'policy_name': self.mock_access_policy['policy_name'],
            'max_file_size': self.mock_access_policy['max_file_size'],
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_policy_mock_object(self, kind=None):
        policy_obj = policy_module()
        if kind is None:
            policy_obj.server = MockONTAPConnection()
        else:
            policy_obj.server = MockONTAPConnection(kind='policy', data=self.mock_access_policy)
        return policy_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            policy_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_nonexistent_policy(self):
        set_module_args(self.mock_args())
        result = self.get_policy_mock_object().exists_access_policy()
        assert not result

    def test_get_existing_scanner(self):
        set_module_args(self.mock_args())
        result = self.get_policy_mock_object('policy').exists_access_policy()
        assert result

    def test_successfully_create(self):
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_policy_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_create_idempotency(self):
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_policy_mock_object('policy').apply()
        assert exc.value.args[0]['changed']

    def test_successfully_delete(self):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_policy_mock_object('policy').apply()
        assert exc.value.args[0]['changed']

    def test_delete_idempotency(self):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_policy_mock_object().apply()
        assert not exc.value.args[0]['changed']
