# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_export_policy_rule \
    import NetAppontapExportRule as policy_rule  # module under test

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
    'get_export_policy_rules': (
        200,
        {
            "records": [
                {
                    "rw_rule": [
                        "any"
                    ],
                    "_links": {
                        "self": {
                            "href": "/api/resourcelink"
                        }
                    },
                    "ro_rule": [
                        "any"
                    ],
                    "allow_suid": True,
                    "chown_mode": "restricted",
                    "index": 10,
                    "superuser": [
                        "any"
                    ],
                    "protocols": [
                        "any"
                    ],
                    "anonymous_user": "string",
                    "clients": [
                        {
                            "match": "0.0.0.0/0"
                        }
                    ],
                    "ntfs_unix_security": "fail",
                    "allow_device_creation": True
                }
            ],
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
        self.data = data
        self.xml_in = None
        self.xml_out = None


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.server = MockONTAPConnection()
        self.mock_rule = {
            'name': 'test',
            'protocol': 'nfs',
            'client_match': ['1.1.1.0', '0.0.0.0/0'],
            'rule_index': 10,
            'anonymous_user_id': '65534',
            'super_user_security': ['any'],
        }

    def mock_rule_args(self, rest=False):
        if rest:
            return {
                'name': self.mock_rule['name'],
                'client_match': self.mock_rule['client_match'],
                'vserver': 'test',
                'protocol': self.mock_rule['protocol'],
                'rule_index': self.mock_rule['rule_index'],
                'anonymous_user_id': self.mock_rule['anonymous_user_id'],
                'super_user_security': self.mock_rule['super_user_security'],
                'ro_rule': 'any',
                'rw_rule': 'any',
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'use_rest': 'always'
            }

    def get_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_firewall_policy object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_firewall_policy object
        """
        obj = policy_rule()
        return obj

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create_rule(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_rule_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],  # Get policy
            SRR['no_record'],  # Get Rules
            SRR['get_uuid_policy_id_export_policy'],  # Get Policy
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_get_policy(self, mock_request):
        '''Test error rest get'''
        data = self.mock_rule_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on fetching export policy: calling: protocols/nfs/export-policies: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_get_rule(self, mock_request):
        '''Test error rest create'''
        data = self.mock_rule_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        print(exc.value.args[0]['msg'])
        assert 'Error on fetching export policy rule: calling: protocols/nfs/export-policies/123/rules/10: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_create(self, mock_request):
        '''Test error rest create'''
        data = self.mock_rule_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['no_record'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        print(exc.value.args[0]['msg'])
        assert 'Error on creating export policy Rule: calling: protocols/nfs/export-policies/123/rules: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_delete_rule(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_rule_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            # the module under test modifies record directly, and may cause other tests to fail
            copy.deepcopy(SRR['get_export_policy_rules']),
            SRR['get_uuid_policy_id_export_policy'],
            SRR['no_record'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_delete(self, mock_request):
        '''Test error rest create'''
        data = self.mock_rule_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            copy.deepcopy(SRR['get_export_policy_rules']),
            SRR['get_uuid_policy_id_export_policy'],
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        print(exc.value.args[0]['msg'])
        assert 'Error on deleting export policy Rule: calling: protocols/nfs/export-policies/123/rules/10: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create_policy_and_rule(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_rule_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Policy
            SRR['no_record'],  # Get policy
            SRR['no_record'],  # Get Rules
            SRR['get_uuid_policy_id_export_policy'],  # Get Policy
            SRR['empty_good'],
            SRR['end_of_sequence']

        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_creating_policy(self, mock_request):
        '''Test error rest create'''
        data = self.mock_rule_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Policy
            SRR['no_record'],  # Get policy
            SRR['generic_error'],  # error creating policy,

        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        print(exc.value.args[0]['msg'])
        assert 'Error on creating export policy: calling: protocols/nfs/export-policies: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_modify(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_rule_args(rest=True)
        data['anonymous_user_id'] = '1234'
        data['protocol'] = 'nfs4'
        data['super_user_security'] = 'krb5i'
        data['client_match'] = ['1.1.1.3', '1.1.0.3']
        data['ro_rule'] = ['never']
        data['rw_rule'] = ['never']
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],  # Get Policy
            copy.deepcopy(SRR['get_export_policy_rules']),  # Get rules
            SRR['get_uuid_policy_id_export_policy'],  # Get Policy
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_modify(self, mock_request):
        '''Test error rest create'''
        data = self.mock_rule_args(rest=True)
        data['anonymous_user_id'] = '1234'
        data['protocol'] = 'nfs4'
        data['super_user_security'] = 'krb5i'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            copy.deepcopy(SRR['get_export_policy_rules']),
            SRR['get_uuid_policy_id_export_policy'],
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        print(exc.value.args[0]['msg'])
        assert 'Error on modifying export policy Rule: calling: protocols/nfs/export-policies/123/rules/10: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_get_rule_with_no_index(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_rule_args(rest=True)
        data.pop('rule_index')
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],  # Get policy
            copy.deepcopy(SRR['get_export_policy_rules']),  # Get Rules
            SRR['get_uuid_policy_id_export_policy'],  # Get Policy
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_get_rule_with_no_index(self, mock_request):
        '''Test error rest create'''
        data = self.mock_rule_args(rest=True)
        data.pop('rule_index')
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid_policy_id_export_policy'],
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        print(exc.value.args[0]['msg'])
        assert 'Error on fetching export policy rule: calling: protocols/nfs/export-policies/123/rules: got Expected error.' in exc.value.args[0]['msg']
