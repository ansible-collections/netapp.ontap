# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_volume_snaplock """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_snaplock \
    import NetAppOntapVolumeSnaplock as snaplock_module  # module under test

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
        self.type = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'snaplock':
            xml = self.build_snaplock_info(self.params)
        elif self.type == 'zapi_error':
            error = netapp_utils.zapi.NaApiError('test', 'error')
            raise error
        self.xml_out = xml
        return xml

    @staticmethod
    def build_snaplock_info(data):
        ''' build xml data for vserser-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {'snaplock-attrs': {
                      'snaplock-attrs-info': {
                          'autocommit-period': data['autocommit_period'],
                          'default-retention-period': data['default_retention_period'],
                          'maximum-retention-period': data['maximum_retention_period'],
                          'minimum-retention-period': data['minimum_retention_period'],
                          'is-volume-append-mode-enabled': data['is_volume_append_mode_enabled']
                      }
                      }}
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_snaplock = {
            'autocommit_period': '10days',
            'default_retention_period': '1years',
            'maximum_retention_period': '2years',
            'minimum_retention_period': '6months',
            'is_volume_append_mode_enabled': 'false'
        }

    def mock_args(self):
        return {
            'name': 'test_volume',
            'autocommit_period': self.mock_snaplock['autocommit_period'],
            'default_retention_period': self.mock_snaplock['default_retention_period'],
            'maximum_retention_period': self.mock_snaplock['maximum_retention_period'],
            'minimum_retention_period': self.mock_snaplock['minimum_retention_period'],
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'vserver': 'test_vserver'
        }

    def get_snaplock_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_volume_snaplock object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_volume_snaplock object
        """
        snaplock_obj = snaplock_module()
        netapp_utils.ems_log_event = Mock(return_value=None)
        if kind is None:
            snaplock_obj.server = MockONTAPConnection()
        else:
            snaplock_obj.server = MockONTAPConnection(kind=kind, data=self.mock_snaplock)
        return snaplock_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            snaplock_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_existing_snaplock(self):
        set_module_args(self.mock_args())
        result = self.get_snaplock_mock_object(kind='snaplock').get_volume_snaplock_attrs()
        assert result['autocommit_period'] == self.mock_snaplock['autocommit_period']
        assert result['default_retention_period'] == self.mock_snaplock['default_retention_period']
        assert result['is_volume_append_mode_enabled'] is False
        assert result['maximum_retention_period'] == self.mock_snaplock['maximum_retention_period']

    def test_modify_snaplock(self):
        data = self.mock_args()
        data['maximum_retention_period'] = '5years'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_snaplock_mock_object('snaplock').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_snaplock.NetAppOntapVolumeSnaplock.get_volume_snaplock_attrs')
    def test_modify_snaplock_error(self, get_volume_snaplock_attrs):
        data = self.mock_args()
        data['maximum_retention_period'] = '5years'
        set_module_args(data)
        get_volume_snaplock_attrs.side_effect = [self.mock_snaplock]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_snaplock_mock_object('zapi_error').apply()
        assert exc.value.args[0]['msg'] == 'Error setting snaplock attributes for volume test_volume : NetApp API failed. Reason - test:error'
