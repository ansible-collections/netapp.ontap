# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_volume_export_policy '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_export_policy \
    import NetAppONTAPExportPolicy as policy_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'get_uuid_policy_id_export_policy': (
        200,
        {
            "records": [{
                "svm": {
                    "uuid": "uuid",
                    "name": "svm"},
                "id": 123,
                "name": "ansible"
            }],
            "num_records": 1}, None),
    "no_record": (
        200,
        {"num_records": 0},
        None)
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

    def __init__(self, kind=None, data=None):
        ''' save arguments '''
        self.kind = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.kind == 'export_policy':
            xml = self.build_export_policy_info(self.params)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_export_policy_info(export_policy_details):
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1,
                'attributes-list': {'export-policy-info': {'name': export_policy_details['name']
                                                           }}}
        xml.translate_struct(data)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_job_schedule '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_export_policy = {
            'name': 'test_policy',
            'vserver': 'test_vserver'
        }

    def mock_args(self, rest=False):
        if rest:
            return {
                'vserver': self.mock_export_policy['vserver'],
                'name': self.mock_export_policy['name'],
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!'
            }
        else:
            return {
                'vserver': self.mock_export_policy['vserver'],
                'name': self.mock_export_policy['name'],
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'use_rest': 'never'
            }

    def get_export_policy_mock_object(self, cx_type='zapi', kind=None):
        policy_obj = policy_module()
        if cx_type == 'zapi':
            if kind is None:
                policy_obj.server = MockONTAPConnection()
            elif kind == 'export_policy':
                policy_obj.server = MockONTAPConnection(kind='export_policy', data=self.mock_export_policy)
        return policy_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            policy_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_export_policy.NetAppONTAPExportPolicy.create_export_policy')
    def test_successful_create(self, create_export_policy):
        ''' Test successful create '''
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_export_policy_mock_object().apply()
        assert exc.value.args[0]['changed']
        create_export_policy.assert_called_with(uuid=None)

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_export_policy.NetAppONTAPExportPolicy.get_export_policy')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_export_policy.NetAppONTAPExportPolicy.rename_export_policy')
    def test_successful_rename(self, rename_export_policy, get_export_policy):
        ''' Test successful rename '''
        data = self.mock_args()
        data['from_name'] = 'old_policy'
        set_module_args(data)
        get_export_policy.side_effect = [
            None,
            {'policy-name': 'old_policy'}
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_export_policy_mock_object().apply()
        assert exc.value.args[0]['changed']
        rename_export_policy.assert_called_with(policy_id=None)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['no_record'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_export_policy_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_delete(self, mock_request):
        '''Test successful rest delete'''
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_export_policy_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_rename(self, mock_request):
        '''Test successful rest rename'''
        data = self.mock_args(rest=True)
        data['from_name'] = 'ansible'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['no_record'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_export_policy_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_create(self, mock_request):
        '''Test error rest create'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['no_record'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_export_policy_mock_object(cx_type='rest').apply()
        assert 'Error on creating export policy: Expected error' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_delete(self, mock_request):
        '''Test error rest delete'''
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_export_policy_mock_object(cx_type='rest').apply()
        assert 'Error on deleting export policy: Expected error' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_rename(self, mock_request):
        '''Test error rest rename'''
        data = self.mock_args(rest=True)
        data['from_name'] = 'ansible'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['no_record'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_export_policy_mock_object(cx_type='rest').apply()
        assert 'Error on renaming export policy: Expected error' in exc.value.args[0]['msg']
