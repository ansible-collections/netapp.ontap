# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_vscan_scanner_pool '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_efficiency_policy \
    import NetAppOntapEfficiencyPolicy as efficiency_module  # module under test

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
        if self.kind == 'threshold':
            xml = self.build_threshold_info(self.params)
        elif self.kind == 'scheduled':
            xml = self.build_schedule_info(self.params)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_threshold_info(details):
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {'num-records': 1,
                      'attributes-list': {
                          'sis-policy-info': {
                              'changelog-threshold-percent': 10,
                              'comment': details['comment'],
                              'enabled': 'true',
                              'policy-name': details['policy_name'],
                              'policy-type': 'threshold',
                              'qos-policy': details['qos_policy'],
                              'vserver': details['vserver']
                          }
                      }
                      }
        xml.translate_struct(attributes)
        return xml

    @staticmethod
    def build_schedule_info(details):
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {'num-records': 1,
                      'attributes-list': {
                          'sis-policy-info': {
                              'comment': details['comment'],
                              'duration': 10,
                              'enabled': 'true',
                              'policy-name': details['policy_name'],
                              'policy-type': 'scheduled',
                              'qos-policy': details['qos_policy'],
                              'vserver': details['vserver']
                          }
                      }
                      }
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_efficiency_policy '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_efficiency_policy = {
            'state': 'present',
            'vserver': 'test_vserver',
            'policy_name': 'test_policy',
            'comment': 'This policy is for x and y',
            'enabled': True,
            'qos_policy': 'background'
        }

    def mock_args(self):
        return {
            'state': self.mock_efficiency_policy['state'],
            'vserver': self.mock_efficiency_policy['vserver'],
            'policy_name': self.mock_efficiency_policy['policy_name'],
            'comment': self.mock_efficiency_policy['comment'],
            'enabled': self.mock_efficiency_policy['enabled'],
            'qos_policy': self.mock_efficiency_policy['qos_policy'],
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_efficiency_mock_object(self, kind=None):
        efficiency_obj = efficiency_module()
        if kind is None:
            efficiency_obj.server = MockONTAPConnection()
        elif kind == 'threshold':
            efficiency_obj.server = MockONTAPConnection(kind='threshold', data=self.mock_efficiency_policy)
        elif kind == 'scheduled':
            efficiency_obj.server = MockONTAPConnection(kind='scheduled', data=self.mock_efficiency_policy)
        return efficiency_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            efficiency_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_nonexistent_efficiency_policy(self):
        set_module_args(self.mock_args())
        result = self.get_efficiency_mock_object().get_efficiency_policy()
        assert not result

    def test_get_existing_scanner(self):
        set_module_args(self.mock_args())
        result = self.get_efficiency_mock_object('threshold').get_efficiency_policy()
        assert result

    def test_successfully_create(self):
        data = self.mock_args()
        data['policy_type'] = 'threshold'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_efficiency_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_create_idempotency(self):
        data = self.mock_args()
        data['policy_type'] = 'threshold'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_efficiency_mock_object('threshold').apply()
        assert not exc.value.args[0]['changed']

    def test_threshold_duration_failure(self):
        data = self.mock_args()
        data['duration'] = 1
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_efficiency_mock_object('threshold').apply()
        assert exc.value.args[0]['msg'] == "duration cannot be set if policy_type is threshold"

    def test_threshold_schedule_failure(self):
        data = self.mock_args()
        data['schedule'] = 'test_job_schedule'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_efficiency_mock_object('threshold').apply()
        assert exc.value.args[0]['msg'] == "schedule cannot be set if policy_type is threshold"

    def test_scheduled_threshold_percent_failure(self):
        data = self.mock_args()
        data['changelog_threshold_percent'] = 30
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_efficiency_mock_object('scheduled').apply()
        assert exc.value.args[0]['msg'] == "changelog_threshold_percent cannot be set if policy_type is scheduled"

    def test_successfully_delete(self):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_efficiency_mock_object('threshold').apply()
        assert exc.value.args[0]['changed']

    def test_delete_idempotency(self):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_efficiency_mock_object().apply()
        assert not exc.value.args[0]['changed']

    def test_successful_modify(self):
        data = self.mock_args()
        data['policy_type'] = 'threshold'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_efficiency_mock_object('scheduled').apply()
        assert exc.value.args[0]['changed']
