# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_metrocluster '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_metrocluster_dr_group \
    import NetAppONTAPMetroClusterDRGroup as mcc_dr_pairs_module  # module under test

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'get_mcc_dr_pair_with_no_results': (200, {'records': [], 'num_records': 0}, None),
    'get_mcc_dr_pair_with_results': (200, {'records': [{'partner_cluster': {'name': 'rha2-b2b1_siteB'},
                                                        'dr_pairs': [{'node': {'name': 'rha17-a2'},
                                                                      'partner': {'name': 'rha17-b2'}},
                                                                     {'node': {'name': 'rha17-b2'},
                                                                      'partner': {'name': 'rha17-b1'}}],
                                                        'id': '2'}],
                                           'num_records': 1}, None),
    'mcc_dr_pair_post': (200, {'job': {
        'uuid': 'fde79888-692a-11ea-80c2-005056b39fe7',
        '_links': {
            'self': {
                'href': '/api/cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7'}}}
    }, None),
    'get_mcc_dr_node': (200, {'records': [{'dr_group_id': '1'}], 'num_records': 1}, None),
    'get_mcc_dr_node_none': (200, {'records': [], 'num_records': 0}, None),
    'job': (200, {
        "uuid": "cca3d070-58c6-11ea-8c0c-005056826c14",
        "description": "POST /api/cluster/metrocluster",
        "state": "success",
        "message": "There are not enough disks in Pool1.",
        "code": 2432836,
        "start_time": "2020-02-26T10:35:44-08:00",
        "end_time": "2020-02-26T10:47:38-08:00",
        "_links": {
            "self": {
                "href": "/api/cluster/jobs/cca3d070-58c6-11ea-8c0c-005056826c14"
            }
        }
    }, None)
}


class TestMyModule(unittest.TestCase):
    """ Unit tests for na_ontap_metrocluster """

    def setUp(self):
        self.mock_mcc_dr_pair = {
            'partner_cluster_name': 'rha2-b2b1_siteB',
            'node_name': 'rha17-a2',
            'partner_node_name': 'rha17-b2',
            'node_name2': 'rha17-b2',
            'partner_node_name2': 'rha17-b1'

        }

    def mock_args(self):
        return {
            'dr_pairs': [{
                'node_name': self.mock_mcc_dr_pair['node_name'],
                'partner_node_name': self.mock_mcc_dr_pair['partner_node_name'],
            }, {
                'node_name': self.mock_mcc_dr_pair['node_name2'],
                'partner_node_name': self.mock_mcc_dr_pair['partner_node_name2'],
            }],
            'partner_cluster_name': self.mock_mcc_dr_pair['partner_cluster_name'],
            'hostname': 'test_host',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_alias_mock_object(self):
        alias_obj = mcc_dr_pairs_module()
        return alias_obj

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create(self, mock_request):
        """Test successful rest create"""
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_mcc_dr_pair_with_no_results'],
            SRR['get_mcc_dr_pair_with_no_results'],
            SRR['mcc_dr_pair_post'],
            SRR['job'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_create_idempotency(self, mock_request):
        """Test rest create idempotency"""
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_mcc_dr_pair_with_results'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_delete(self, mock_request):
        """Test successful rest delete"""
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_mcc_dr_pair_with_results'],
            SRR['mcc_dr_pair_post'],
            SRR['job'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_delete_idempotency(self, mock_request):
        """Test rest delete idempotency"""
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_mcc_dr_pair_with_no_results'],
            SRR['get_mcc_dr_pair_with_no_results'],
            SRR['get_mcc_dr_node_none'],
            SRR['get_mcc_dr_node_none'],
            SRR['job'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert not exc.value.args[0]['changed']
