# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_clone \
    import NetAppONTAPVolumeClone as volume_clone_module  # module under test

# needed for get and modify/delete as they still use ZAPI
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request

SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_rest_96': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy_9_6_0')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'no_record': (200, {'num_records': 0, 'records': []}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'volume_clone': (
        200,
        {'records': [{
            "clone": {
                "is_flexclone": True,
                "parent_snapshot": {
                    "name": "clone_ansibleVolume12_.2022-01-25_211704.0"
                },
                "parent_svm": {
                    "name": "ansibleSVM"
                },
                "parent_volume": {
                    "name": "ansibleVolume12"
                }
            },
            "name": "ansibleVolume12_clone",
            "nas": {
                "gid": 0,
                "uid": 0
            },
            "svm": {
                "name": "ansibleSVM"
            },
            "uuid": "2458688d-7e24-11ec-a267-005056b30cfa"
        }
        ]}, None
    )
}


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        # self.server = MockONTAPConnection()
        self.mock_vserver = {
            'name': 'test_svm',
            'use_rest': 'always'
        }
        global WARNINGS
        WARNINGS = []

    @staticmethod
    def mock_args_volume():
        return {
            'vserver': 'ansibleSVM',
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!',
            'use_rest': 'always',
            'name': 'clone_of_parent_volume',
            'parent_volume': 'parent_volume'
        }

    def get_volume_mock_object(self):
        return volume_clone_module()

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            volume_clone_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successfully_create_clone(self, mock_request):
        data = dict(self.mock_args_volume())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_error_getting_volume_clone(self, mock_request):
        data = dict(self.mock_args_volume())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],  # Error Get Volume
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error getting volume clone clone_of_parent_volume: calling: storage/volumes: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_error_creating_volume_clone(self, mock_request):
        data = dict(self.mock_args_volume())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['generic_error']  # Error creating volume
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error creating volume clone clone_of_parent_volume: calling: storage/volumes: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_error_space_reserve_volume_clone(self, mock_request):
        data = dict(self.mock_args_volume())
        data['space_reserve'] = 'volume'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['generic_error'],  # Non rest option used
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "REST API currently does not support 'space_reserve'"
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successfully_create_with_optional_clone(self, mock_request):
        data = dict(self.mock_args_volume())
        data['qos_policy_group_name'] = 'test_policy_name'
        data['parent_snapshot'] = 'test_snapshot'
        data['volume_type'] = 'rw'
        data['junction_path'] = '/test_junction_path'
        data['uid'] = 10
        data['gid'] = 20
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successfully_create_with_parent_vserver_clone(self, mock_request):
        data = dict(self.mock_args_volume())
        data['qos_policy_group_name'] = 'test_policy_name'
        data['parent_snapshot'] = 'test_snapshot'
        data['volume_type'] = 'rw'
        data['parent_vserver'] = 'test_vserver'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successfully_split_clone(self, mock_request):
        data = dict(self.mock_args_volume())
        data['split'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_clone'],  # Get Volume
            SRR['no_record'],  # Split Volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_error_split_volume_clone(self, mock_request):
        data = dict(self.mock_args_volume())
        data['split'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_clone'],  # Get Volume
            SRR['generic_error'],  # Split Volume
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error starting volume clone split clone_of_parent_volume: calling: storage/volumes/2458688d-7e24-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg
