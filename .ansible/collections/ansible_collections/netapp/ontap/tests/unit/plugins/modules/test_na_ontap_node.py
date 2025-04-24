# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_node \
    import NetAppOntapNode as node_module  # module under test


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
    'node_record': (200, {"num_records": 1, "records": [
        {
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7",
            "name": 'node1',
            "location": 'myloc'}
    ]}, None)
}


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
        if self.type == 'node':
            xml = self.build_node_info()
        elif self.type == 'node_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_node_info():
        ''' build xml data for node-details-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes': {
                'node-details-info': {
                    "node": "node1",
                    "node-location": "myloc",
                    "node-asset-tag": "mytag"
                }
            }
        }
        xml.translate_struct(data)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def set_default_args(self, use_rest=None):
        hostname = '10.10.10.10'
        username = 'username'
        password = 'password'
        name = 'node1'

        args = dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'name': name,
            'location': 'myloc'
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_node_mock_object(cx_type='zapi', kind=None):
        node_obj = node_module()
        if cx_type == 'zapi':
            if kind is None:
                node_obj.server = MockONTAPConnection()
            else:
                node_obj.server = MockONTAPConnection(kind=kind)
        return node_obj

    def test_ensure_get_called(self):
        ''' test get_node for non-existent entry'''
        set_module_args(self.set_default_args(use_rest='Never'))
        print('starting')
        my_obj = node_module()
        print('use_rest:', my_obj.use_rest)
        my_obj.cluster = MockONTAPConnection('node')
        assert my_obj.get_node is not None

    def test_successful_rename(self):
        ''' renaming node and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['from_name'] = 'node1'
        data['name'] = 'node2'
        set_module_args(data)
        my_obj = node_module()
        my_obj.cluster = MockONTAPConnection('node')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # to reset na_helper from remembering the previous 'changed' value
        data['name'] = 'node1'
        set_module_args(data)
        my_obj = node_module()
        my_obj.cluster = MockONTAPConnection('node')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_successful_modify(self):
        ''' modifying node and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['location'] = 'myloc1'
        set_module_args(data)
        my_obj = node_module()
        my_obj.cluster = MockONTAPConnection('node')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # to reset na_helper from remembering the previous 'changed' value
        data['location'] = 'myloc'
        set_module_args(data)
        my_obj = node_module()
        my_obj.cluster = MockONTAPConnection('node')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        data['from_name'] = 'node1'
        data['name'] = 'node2'
        set_module_args(data)
        my_obj = node_module()
        my_obj.cluster = MockONTAPConnection('node_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.rename_node()
        assert 'Error renaming node: ' in exc.value.args[0]['msg']
        data = self.set_default_args(use_rest='Never')
        data['location'] = 'myloc1'
        set_module_args(data)
        my_obj1 = node_module()
        my_obj1.cluster = MockONTAPConnection('node_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj1.modify_node()
        assert 'Error modifying node: ' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['from_name'] = 'node2'
        data['location'] = 'mylocnew'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['node_record'],  # get
            SRR['empty_good'],  # no response for modify
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_node_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_rename_rest(self, mock_request):
        data = self.set_default_args()
        data['from_name'] = 'node'
        data['name'] = 'node2'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['node_record'],  # get
            SRR['empty_good'],  # no response for modify
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_node_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_location_rest(self, mock_request):
        data = self.set_default_args()
        data['location'] = 'mylocnew'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['node_record'],  # get
            SRR['empty_good'],  # no response for modify
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_node_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']
