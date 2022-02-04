# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_fcp \
    import NetAppOntapFCP as fcp  # module under test

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'fcp_record': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansibleSVM"
                    },
                    "enabled": True,
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    }
                }
            ],
            "num_records": 1
        }, None
    ),
    'fcp_record_disabled': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansibleSVM"
                    },
                    "enabled": False,
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    }
                }
            ],
            "num_records": 1
        }, None
    ),
    "no_record": (
        200,
        {"num_records": 0},
        None)
}


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
        self.server = MockONTAPConnection()
        self.mock_rule = {}

    def mock_args(self, rest=False):
        if rest:
            return {
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'use_rest': 'always',
                'vserver': 'test_vserver',
            }

    def get_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_firewall_policy object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_firewall_policy object
        """
        obj = fcp()
        return obj

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_get(self, mock_request):
        '''Test error rest create'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on fetching fcp: calling: protocols/san/fcp/services: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],
            SRR['empty_good']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_create(self, mock_request):
        '''Test error rest create'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on creating fcp: calling: protocols/san/fcp/services: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_delete(self, mock_request):
        '''Test successful rest delete'''
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            # the module under test modifies record directly, and may cause other tests to fail
            copy.deepcopy(SRR['fcp_record']),
            SRR['empty_good'],
            SRR['empty_good']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_delete(self, mock_request):
        '''Test error rest delete'''
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            copy.deepcopy(SRR['fcp_record']),
            SRR['empty_good'],
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on deleting fcp policy: calling: ' + \
               'protocols/san/fcp/services/671aa46e-11ad-11ec-a267-005056b30cfa: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_disable(self, mock_request):
        '''Test successful rest disable'''
        data = self.mock_args(rest=True)
        data['status'] = 'down'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            copy.deepcopy(SRR['fcp_record']),
            SRR['empty_good'],

        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_enable(self, mock_request):
        '''Test successful rest enable'''
        data = self.mock_args(rest=True)
        data['status'] = 'up'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            copy.deepcopy(SRR['fcp_record_disabled']),
            SRR['empty_good'],

        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_enabled_change(self, mock_request):
        '''Test error rest change'''
        data = self.mock_args(rest=True)
        data['status'] = 'down'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            copy.deepcopy(SRR['fcp_record']),
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on modifying fcp: calling: ' + \
               'protocols/san/fcp/services/671aa46e-11ad-11ec-a267-005056b30cfa: ' + \
               'got Expected error.' in exc.value.args[0]['msg']
