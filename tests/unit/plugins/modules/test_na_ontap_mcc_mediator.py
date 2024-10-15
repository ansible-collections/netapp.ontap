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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_mcc_mediator \
    import NetAppOntapMccipMediator as mediator_module  # module under test

SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'get_mediator_with_no_results': (200, {'num_records': 0}, None),
    'get_mediator_with_results': (200, {
        'num_records': 1,
        'records': [{
            'ip_address': '10.10.10.10',
            'uuid': 'ebe27c49-1adf-4496-8335-ab862aebebf2'
        }]
    }, None)
}


class TestMyModule(unittest.TestCase):
    """ Unit tests for na_ontap_metrocluster """

    def setUp(self):
        self.mock_mediator = {
            'mediator_address': '10.10.10.10',
            'mediator_user': 'carchi',
            'mediator_password': 'netapp1!'
        }

    def mock_args(self):
        return {
            'mediator_address': self.mock_mediator['mediator_address'],
            'mediator_user': self.mock_mediator['mediator_user'],
            'mediator_password': self.mock_mediator['mediator_password'],
            'hostname': 'test_host',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_alias_mock_object(self):
        alias_obj = mediator_module()
        return alias_obj

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create(self, mock_request):
        """Test successful rest create"""
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_mediator_with_no_results'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create_idempotency(self, mock_request):
        """Test successful rest create"""
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_mediator_with_results'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_delete(self, mock_request):
        """Test successful rest create"""
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_mediator_with_results'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_delete(self, mock_request):
        """Test successful rest create"""
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_mediator_with_no_results'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_alias_mock_object().apply()
        assert not exc.value.args[0]['changed']
