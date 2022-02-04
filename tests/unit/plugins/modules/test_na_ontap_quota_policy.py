# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_quota_policy '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_quota_policy \
    import NetAppOntapQuotaPolicy as quota_policy_module  # module under test

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
        if self.kind == 'quota':
            xml = self.build_quota_policy_info(self.params, True)
        if self.kind == 'quota_not_assigned':
            xml = self.build_quota_policy_info(self.params, False)
        elif self.kind == 'zapi_error':
            error = netapp_utils.zapi.NaApiError('test', 'error')
            raise error
        self.xml_out = xml
        return xml

    @staticmethod
    def build_quota_policy_info(params, assigned):
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {'num-records': 1,
                      'attributes-list': {
                          'quota-policy-info': {
                              'policy-name': params['name']},
                          'vserver-info': {
                              'quota-policy': params['name'] if assigned else 'default'}
                      }}
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_quota_policy '''

    def setUp(self):
        self.mock_quota_policy = {
            'state': 'present',
            'vserver': 'test_vserver',
            'name': 'test_policy'
        }

    def mock_args(self):
        return {
            'state': self.mock_quota_policy['state'],
            'vserver': self.mock_quota_policy['vserver'],
            'name': self.mock_quota_policy['name'],
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_quota_policy_mock_object(self, kind=None):
        policy_obj = quota_policy_module()
        if kind is None:
            policy_obj.server = MockONTAPConnection()
        else:
            policy_obj.server = MockONTAPConnection(kind=kind, data=self.mock_quota_policy)
        return policy_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            quota_policy_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_successfully_create(self):
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_quota_policy_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_create_idempotency(self):
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_quota_policy_mock_object('quota').apply()
        assert not exc.value.args[0]['changed']

    def test_cannot_delete(self):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_quota_policy_mock_object('quota').apply()
        msg = 'Error policy test_policy cannot be deleted as it is assigned to the vserver test_vserver'
        assert msg == exc.value.args[0]['msg']

    def test_successfully_delete(self):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_quota_policy_mock_object('quota_not_assigned').apply()
        assert exc.value.args[0]['changed']

    def test_delete_idempotency(self):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_quota_policy_mock_object().apply()
        assert not exc.value.args[0]['changed']

    def test_successfully_assign(self):
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_quota_policy_mock_object('quota_not_assigned').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_quota_policy.NetAppOntapQuotaPolicy.get_quota_policy')
    def test_successful_rename(self, get_volume):
        data = self.mock_args()
        data['name'] = 'new_policy'
        data['from_name'] = 'test_policy'
        set_module_args(data)
        current = {
            'name': 'test_policy'
        }
        get_volume.side_effect = [
            None,
            current
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_quota_policy_mock_object('quota').apply()
        assert exc.value.args[0]['changed']

    def test_error(self):
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_quota_policy_mock_object('zapi_error').get_quota_policy()
        assert exc.value.args[0]['msg'] == 'Error fetching quota policy test_policy: NetApp API failed. Reason - test:error'
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_quota_policy_mock_object('zapi_error').create_quota_policy()
        assert exc.value.args[0]['msg'] == 'Error creating quota policy test_policy: NetApp API failed. Reason - test:error'
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_quota_policy_mock_object('zapi_error').delete_quota_policy()
        assert exc.value.args[0]['msg'] == 'Error deleting quota policy test_policy: NetApp API failed. Reason - test:error'
        data['name'] = 'new_policy'
        data['from_name'] = 'test_policy'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_quota_policy_mock_object('zapi_error').rename_quota_policy()
        assert exc.value.args[0]['msg'] == 'Error renaming quota policy test_policy: NetApp API failed. Reason - test:error'
