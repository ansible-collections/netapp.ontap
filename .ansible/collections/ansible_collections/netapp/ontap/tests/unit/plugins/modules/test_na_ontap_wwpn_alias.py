# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_wwpn_alias '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_wwpn_alias \
    import NetAppOntapWwpnAlias as alias_module  # module under test

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'get_alias': (
        200,
        {"records": [{
            "svm": {
                "uuid": "uuid",
                "name": "svm"},
            "alias": "host1",
            "wwpn": "01:02:03:04:0a:0b:0c:0d"}],
         "num_records": 1}, None),
    'get_svm_uuid': (
        200,
        {"records": [{
            "uuid": "test_uuid"
        }]}, None),
    "no_record": (
        200,
        {"num_records": 0},
        None)
}


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_wwpn_alias '''

    def setUp(self):
        self.mock_alias = {
            'name': 'host1',
            'vserver': 'test_vserver'
        }

    def mock_args(self):
        return {
            'vserver': self.mock_alias['vserver'],
            'name': self.mock_alias['name'],
            "wwpn": "01:02:03:04:0a:0b:0c:0d",
            'hostname': 'test_host',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_alias_mock_object(self):
        alias_obj = alias_module()
        return alias_obj

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_svm_uuid'],
            SRR['no_record'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_create_idempotency(self, mock_request):
        '''Test rest create idempotency'''
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_svm_uuid'],
            SRR['get_alias'],
            SRR['no_record'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_create_error(self, mock_request):
        '''Test rest create error'''
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_svm_uuid'],
            SRR['no_record'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_alias_mock_object().apply()
        assert exc.value.args[0]['msg'] == "Error on creating wwpn alias: Expected error."

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_modify(self, mock_request):
        '''Test rest modify error'''
        data = self.mock_args()
        data['wwpn'] = "01:02:03:04:0a:0b:0c:0e"
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_svm_uuid'],
            SRR['get_alias'],
            SRR['empty_good'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_modify_error_delete(self, mock_request):
        '''Test rest modify error'''
        data = self.mock_args()
        data['wwpn'] = "01:02:03:04:0a:0b:0c:0e"
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_svm_uuid'],
            SRR['get_alias'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_alias_mock_object().apply()
        assert exc.value.args[0]['msg'] == "Error on modifying wwpn alias when trying to delete alias: Expected error."

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_modify_error_create(self, mock_request):
        '''Test rest modify error'''
        data = self.mock_args()
        data['wwpn'] = "01:02:03:04:0a:0b:0c:0e"
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_svm_uuid'],
            SRR['get_alias'],
            SRR['empty_good'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_alias_mock_object().apply()
        assert exc.value.args[0]['msg'] == "Error on modifying wwpn alias when trying to re-create alias: Expected error."

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_delete_error(self, mock_request):
        '''Test rest delete error'''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_svm_uuid'],
            SRR['get_alias'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_alias_mock_object().apply()
        assert exc.value.args[0]['msg'] == "Error on deleting wwpn alias: Expected error."
