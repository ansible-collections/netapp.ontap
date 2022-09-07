# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import assert_no_warnings, set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain \
    import NetAppOntapBroadcastDomain as broadcast_domain_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


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
        if self.type == 'broadcast_domain':
            xml = self.build_broadcast_domain_info(self.params)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_broadcast_domain_info(broadcast_domain_details):
        ''' build xml data for broadcast_domain info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'net-port-broadcast-domain-info': {
                    'broadcast-domain': broadcast_domain_details['name'],
                    'ipspace': broadcast_domain_details['ipspace'],
                    'mtu': broadcast_domain_details['mtu'],
                    'ports': {
                        'port-info': {
                            'port': 'test_port_1'
                        }
                    }
                }

            }
        }
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.server = MockONTAPConnection()
        self.mock_broadcast_domain = {
            'name': 'test_broadcast_domain',
            'mtu': 1000,
            'ipspace': 'Default',
            'ports': 'test_port_1'
        }

    def mock_args(self):
        return {
            'name': self.mock_broadcast_domain['name'],
            'ipspace': self.mock_broadcast_domain['ipspace'],
            'mtu': self.mock_broadcast_domain['mtu'],
            'ports': self.mock_broadcast_domain['ports'],
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!',
            'use_rest': 'never',
            'feature_flags': {'no_cserver_ems': True}
        }

    def get_broadcast_domain_mock_object(self, kind=None, data=None):
        """
        Helper method to return an na_ontap_volume object
        :param kind: passes this param to MockONTAPConnection()
        :param data: passes this param to MockONTAPConnection()
        :return: na_ontap_volume object
        """
        broadcast_domain_obj = broadcast_domain_module()
        broadcast_domain_obj.asup_log_for_cserver = Mock(return_value=None)
        broadcast_domain_obj.cluster = Mock()
        broadcast_domain_obj.cluster.invoke_successfully = Mock()
        if kind is None:
            broadcast_domain_obj.server = MockONTAPConnection()
        else:
            if data is None:
                broadcast_domain_obj.server = MockONTAPConnection(kind='broadcast_domain', data=self.mock_broadcast_domain)
            else:
                broadcast_domain_obj.server = MockONTAPConnection(kind='broadcast_domain', data=data)
        return broadcast_domain_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            broadcast_domain_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_nonexistent_net_route(self):
        ''' Test if get_broadcast_domain returns None for non-existent broadcast_domain '''
        set_module_args(self.mock_args())
        result = self.get_broadcast_domain_mock_object().get_broadcast_domain()
        assert result is None

    def test_create_error_missing_broadcast_domain(self):
        ''' Test if create throws an error if broadcast_domain is not specified'''
        data = self.mock_args()
        del data['name']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_broadcast_domain_mock_object('broadcast_domain').create_broadcast_domain()
        msg = 'missing required arguments: name'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.create_broadcast_domain')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.get_broadcast_domain')
    def test_successful_create(self, get_broadcast_domain, create_broadcast_domain):
        ''' Test successful create '''
        data = self.mock_args()
        set_module_args(data)
        get_broadcast_domain.side_effect = [None]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object().apply()
        assert exc.value.args[0]['changed']
        create_broadcast_domain.assert_called_with(None)

    def test_create_idempotency(self):
        ''' Test create idempotency '''
        set_module_args(self.mock_args())
        obj = self.get_broadcast_domain_mock_object('broadcast_domain')
        with pytest.raises(AnsibleExitJson) as exc:
            obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.create_broadcast_domain')
    def test_create_idempotency_identical_ports(self, create_broadcast_domain):
        ''' Test create idemptency identical ports '''
        data = self.mock_args()
        data['ports'] = ['test_port_1', 'test_port_1']
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object('broadcast_domain').apply()
        assert not exc.value.args[0]['changed']

    def test_modify_mtu(self):
        ''' Test successful modify mtu '''
        data = self.mock_args()
        data['mtu'] = 1200
        data['from_ipspace'] = 'test'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object('broadcast_domain').apply()
        assert exc.value.args[0]['changed']

    def test_modify_ipspace_idempotency(self):
        ''' Test modify ipsapce idempotency'''
        data = self.mock_args()
        data['ipspace'] = 'Default'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object('broadcast_domain').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.add_broadcast_domain_ports')
    def test_add_ports(self, add_broadcast_domain_ports):
        ''' Test successful modify ports '''
        data = self.mock_args()
        data['ports'] = 'test_port_1,test_port_2'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object('broadcast_domain').apply()
        assert exc.value.args[0]['changed']
        add_broadcast_domain_ports.assert_called_with(['test_port_2'])

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.delete_broadcast_domain_ports')
    def test_delete_ports(self, delete_broadcast_domain_ports):
        ''' Test successful modify ports '''
        data = self.mock_args()
        data['ports'] = ''
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object('broadcast_domain').apply()
        assert exc.value.args[0]['changed']
        delete_broadcast_domain_ports.assert_called_with(['test_port_1'])

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.modify_broadcast_domain')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.split_broadcast_domain')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.get_broadcast_domain')
    def test_split_broadcast_domain(self, get_broadcast_domain, split_broadcast_domain, modify_broadcast_domain):
        ''' Test successful split broadcast domain '''
        data = self.mock_args()
        data['from_name'] = 'test_broadcast_domain'
        data['name'] = 'test_broadcast_domain_2'
        data['ports'] = 'test_port_2'
        set_module_args(data)
        current = {
            'domain-name': 'test_broadcast_domain',
            'mtu': 1000,
            'ipspace': 'Default',
            'ports': ['test_port_1,test_port2']
        }
        get_broadcast_domain.side_effect = [
            None,
            current
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object().apply()
        assert exc.value.args[0]['changed']
        modify_broadcast_domain.assert_not_called()
        split_broadcast_domain.assert_called_with()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.delete_broadcast_domain')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.modify_broadcast_domain')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.get_broadcast_domain')
    def test_split_broadcast_domain_modify_delete(self, get_broadcast_domain, modify_broadcast_domain, delete_broadcast_domain):
        ''' Test successful split broadcast domain '''
        data = self.mock_args()
        data['from_name'] = 'test_broadcast_domain'
        data['name'] = 'test_broadcast_domain_2'
        data['ports'] = ['test_port_1', 'test_port_2']
        data['mtu'] = 1200
        set_module_args(data)
        current = {
            'name': 'test_broadcast_domain',
            'mtu': 1000,
            'ipspace': 'Default',
            'ports': ['test_port_1', 'test_port2']
        }
        get_broadcast_domain.side_effect = [
            None,
            current
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object().apply()
        assert exc.value.args[0]['changed']
        delete_broadcast_domain.assert_called_with('test_broadcast_domain')
        modify_broadcast_domain.assert_called_with()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.get_broadcast_domain')
    def test_split_broadcast_domain_not_exist(self, get_broadcast_domain):
        ''' Test split broadcast domain does not exist '''
        data = self.mock_args()
        data['from_name'] = 'test_broadcast_domain'
        data['name'] = 'test_broadcast_domain_2'
        data['ports'] = 'test_port_2'
        set_module_args(data)

        get_broadcast_domain.side_effect = [
            None,
            None,
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_broadcast_domain_mock_object().apply()
        msg = 'A domain cannot be split if it does not exist.'
        assert exc.value.args[0]['msg'], msg

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.split_broadcast_domain')
    def test_split_broadcast_domain_idempotency(self, split_broadcast_domain):
        ''' Test successful split broadcast domain '''
        data = self.mock_args()
        data['from_name'] = 'test_broadcast_domain'
        data['ports'] = 'test_port_1'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object('broadcast_domain').apply()
        assert not exc.value.args[0]['changed']
        split_broadcast_domain.assert_not_called()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.delete_broadcast_domain')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.get_broadcast_domain')
    def test_delete_broadcast_domain(self, get_broadcast_domain, delete_broadcast_domain):
        ''' test delete broadcast domain '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        current = {
            'name': 'test_broadcast_domain',
            'mtu': 1000,
            'ipspace': 'Default',
            'ports': ['test_port_1', 'test_port2']
        }
        get_broadcast_domain.side_effect = [current]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object().apply()
        assert exc.value.args[0]['changed']
        delete_broadcast_domain.assert_called_with(current=current)

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.delete_broadcast_domain')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.get_broadcast_domain')
    def test_delete_broadcast_domain_idempotent(self, get_broadcast_domain, delete_broadcast_domain):
        ''' test delete broadcast domain '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        get_broadcast_domain.side_effect = [None]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object().apply()
        assert not exc.value.args[0]['changed']
        delete_broadcast_domain.assert_not_called()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.delete_broadcast_domain')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_broadcast_domain.NetAppOntapBroadcastDomain.get_broadcast_domain')
    def test_delete_broadcast_domain_if_all_ports_are_removed(self, get_broadcast_domain, delete_broadcast_domain):
        ''' test delete broadcast domain if all the ports are deleted '''
        data = self.mock_args()
        data['ports'] = []
        data['state'] = 'present'
        set_module_args(data)
        current = {
            'name': 'test_broadcast_domain',
            'mtu': 1000,
            'ipspace': 'Default',
            'ports': ['test_port_1', 'test_port2']
        }
        get_broadcast_domain.side_effect = [current]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_broadcast_domain_mock_object().apply()
        assert exc.value.args[0]['changed']
        delete_broadcast_domain.assert_called_with(current=current)


def default_args():
    args = {
        'state': 'present',
        'hostname': '10.10.10.10',
        'username': 'admin',
        'https': 'true',
        'validate_certs': 'false',
        'password': 'password',
        'use_rest': 'always'
    }
    return args


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_6': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy')), None),
    'is_rest_9_7': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'port_detail_e0d': (200, {
        "num_records": 1,
        "records": [
            {
                'name': 'e0d',
                'node': {'name': 'mohan9cluster2-01'},
                'uuid': 'ea670505-2ab3-11ec-aa30-005056b3dfc8'
            }]
    }, None),
    'port_detail_e0a': (200, {
        "num_records": 1,
        "records": [
            {
                'name': 'e0a',
                'node': {'name': 'mohan9cluster2-01'},
                'uuid': 'ea63420b-2ab3-11ec-aa30-005056b3dfc8'
            }]
    }, None),
    'port_detail_e0b': (200, {
        "num_records": 1,
        "records": [
            {
                'name': 'e0b',
                'node': {'name': 'mohan9cluster2-01'},
                'uuid': 'ea64c0f2-2ab3-11ec-aa30-005056b3dfc8'
            }]
    }, None),
    'broadcast_domain_record': (200, {
        "num_records": 1,
        "records": [
            {
                "uuid": "4475a2c8-f8a0-11e8-8d33-005056bb986f",
                "name": "domain1",
                "ipspace": {"name": "ip1"},
                "ports": [
                    {
                        "uuid": "ea63420b-2ab3-11ec-aa30-005056b3dfc8",
                        "name": "e0a",
                        "node": {
                            "name": "mohan9cluster2-01"
                        }
                    },
                    {
                        "uuid": "ea64c0f2-2ab3-11ec-aa30-005056b3dfc8",
                        "name": "e0b",
                        "node": {
                            "name": "mohan9cluster2-01"
                        }
                    },
                    {
                        "uuid": "ea670505-2ab3-11ec-aa30-005056b3dfc8",
                        "name": "e0d",
                        "node": {
                            "name": "mohan9cluster2-01"
                        }
                    }
                ],
                "mtu": 9000
            }]
    }, None),
    'broadcast_domain_record_split': (200, {
        "num_records": 1,
        "records": [
            {
                "uuid": "4475a2c8-f8a0-11e8-8d33-005056bb986f",
                "name": "domain2",
                "ipspace": {"name": "ip1"},
                "ports": [
                    {
                        "uuid": "ea63420b-2ab3-11ec-aa30-005056b3dfc8",
                        "name": "e0a",
                        "node": {
                            "name": "mohan9cluster2-01"
                        }
                    }
                ],
                "mtu": 9000
            }]
    }, None)
}


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args(dict(hostname=''))
        broadcast_domain_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'missing required arguments:'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_create_broadcast_domain(mock_request, patch_ansible):
    ''' test create broadcast domain '''
    args = dict(default_args())
    args['name'] = "domain1"
    args['ipspace'] = "ip1"
    args['mtu'] = "9000"
    args['ports'] = ["mohan9cluster2-01:e0a", "mohan9cluster2-01:e0b", "mohan9cluster2-01:e0d"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['port_detail_e0a'],
        SRR['port_detail_e0b'],
        SRR['port_detail_e0d'],
        SRR['zero_record'],                # get
        SRR['empty_good'],                 # create
        SRR['empty_good'],                 # add e0a
        SRR['empty_good'],                 # add e0b
        SRR['empty_good'],                 # add e0c
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_create_broadcast_domain_idempotency(mock_request, patch_ansible):
    ''' test create broadcast domain '''
    args = dict(default_args())
    args['name'] = "domain1"
    args['ipspace'] = "ip1"
    args['mtu'] = 9000
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['broadcast_domain_record'],    # get
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_create_broadcast_domain_idempotency_identical_ports(mock_request, patch_ansible):
    ''' test create broadcast domain '''
    args = dict(default_args())
    args['name'] = "domain2"
    args['ipspace'] = "ip1"
    args['mtu'] = 9000
    args['ports'] = ['mohan9cluster2-01:e0a', 'mohan9cluster2-01:e0a']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['port_detail_e0a'],
        SRR['broadcast_domain_record_split'],    # get
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_modify_broadcast_domain(mock_request, patch_ansible):
    ''' test modify broadcast domain mtu '''
    args = dict(default_args())
    args['name'] = "domain1"
    args['ipspace'] = "ip1"
    args['mtu'] = 1500
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['broadcast_domain_record'],    # get
        SRR['empty_good'],                 # modify
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rename_broadcast_domain(mock_request, patch_ansible):
    ''' test modify broadcast domain mtu '''
    args = dict(default_args())
    args['from_name'] = "domain1"
    args['name'] = "domain2"
    args['ipspace'] = "ip1"
    args['mtu'] = 1500
    args['ports'] = ["mohan9cluster2-01:e0a", "mohan9cluster2-01:e0b", "mohan9cluster2-01:e0d"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['port_detail_e0a'],
        SRR['port_detail_e0b'],
        SRR['port_detail_e0d'],
        SRR['zero_record'],                # get
        SRR['broadcast_domain_record'],    # get
        SRR['empty_good'],                 # rename broadcast domain
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_split_broadcast_domain_create_domain2_with_e0a(mock_request, patch_ansible):
    ''' test modify broadcast domain mtu '''
    args = dict(default_args())
    args['from_name'] = "domain1"
    args['name'] = "domain2"
    args['ipspace'] = "ip1"
    args['mtu'] = 1500
    args['ports'] = ["mohan9cluster2-01:e0a"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                 # get version
        SRR['port_detail_e0a'],
        SRR['zero_record'],                 # get
        SRR['broadcast_domain_record'],     # get
        SRR['empty_good'],                  # create broadcast domain
        SRR['empty_good'],                  # add e0a to domain2
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_split_broadcast_domain_create_domain2_with_e0a_idempotent(mock_request, patch_ansible):
    ''' test modify broadcast domain mtu '''
    args = dict(default_args())
    args['from_name'] = "domain1"
    args['name'] = "domain2"
    args['ipspace'] = "ip1"
    args['mtu'] = 1500
    args['ports'] = ["mohan9cluster2-01:e0a"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                     # get version
        SRR['port_detail_e0a'],
        SRR['broadcast_domain_record_split'],    # get domain2 details
        SRR['zero_record'],                      # empty record for domain1
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_create_new_broadcast_domain_with_partial_match(mock_request, patch_ansible):
    ''' test modify broadcast domain mtu '''
    args = dict(default_args())
    args['from_name'] = "domain2"
    args['name'] = "domain1"
    args['ipspace'] = "ip1"
    args['mtu'] = 1500
    args['ports'] = ["mohan9cluster2-01:e0b"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                     # get version
        SRR['port_detail_e0b'],
        SRR['zero_record'],                      # empty record for domain1
        SRR['broadcast_domain_record_split'],    # get domain2 details
        SRR['empty_good'],                       # create broadcast domain domain1
        SRR['empty_good'],                       # add e0b to domain1
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_delete_broadcast_domain(mock_request, patch_ansible):
    ''' test delete broadcast domain mtu '''
    args = dict(default_args())
    args['name'] = "domain1"
    args['ipspace'] = "ip1"
    args['mtu'] = 1500
    args['state'] = "absent"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['broadcast_domain_record'],    # get
        SRR['empty_good'],                 # remove all the ports in broadcast domain
        SRR['empty_good'],                 # delete broadcast domain
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_try_to_bad_format_port(mock_request, patch_ansible):
    ''' test delete broadcast domain mtu '''
    args = dict(default_args())
    args['name'] = "domain1"
    args['ipspace'] = "ip1"
    args['mtu'] = 1500
    args['state'] = "present"
    args['ports'] = ["mohan9cluster2-01e0a"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = broadcast_domain_module()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: Invalid value specified for port: mohan9cluster2-01e0a, provide port name as node_name:port_name"
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_try_to_create_domain_without_ipspace(mock_request, patch_ansible):
    ''' test delete broadcast domain mtu '''
    args = dict(default_args())
    args['name'] = "domain1"
    args['mtu'] = 1500
    args['state'] = "present"
    args['ports'] = ["mohan9cluster2-01:e0a"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = broadcast_domain_module()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: ipspace space is a required option with REST"
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_modify_ipspace(mock_request, patch_ansible):
    ''' test modify ipspace '''
    args = dict(default_args())
    args['name'] = "domain2"
    args['from_ipspace'] = "ip1"
    args['ipspace'] = "Default"
    args['mtu'] = 1500
    args['ports'] = ["mohan9cluster2-01:e0b"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                     # get version
        SRR['port_detail_e0b'],
        SRR['zero_record'],                      # empty record for domain2 in ipspace Default
        SRR['broadcast_domain_record_split'],    # get domain2 details in ipspace ip1
        SRR['empty_good'],                       # modify ipspace
        SRR['empty_good'],                       # add e0b to domain2
        SRR['empty_good'],                       # remove e0a
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_modify_name_and_ipspace(mock_request, patch_ansible):
    ''' test modify ipspace '''
    args = dict(default_args())
    args['from_name'] = "domain2"
    args['name'] = "domain1"
    args['from_ipspace'] = "ip1"
    args['ipspace'] = "Default"
    args['mtu'] = 1500
    args['ports'] = ["mohan9cluster2-01:e0a"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                     # get version
        SRR['port_detail_e0a'],
        SRR['zero_record'],                      # empty record for domain2 in ipspace Default
        SRR['broadcast_domain_record_split'],    # get domain2 details in ipspace ip1
        SRR['empty_good'],                       # modify name, ipspace and mtu
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_split_name_ipspace_if_not_exact_match_of_ports(mock_request, patch_ansible):
    ''' test create new domain as exact match not found '''
    args = dict(default_args())
    args['from_name'] = "domain2"
    args['name'] = "domain1"
    args['from_ipspace'] = "ip1"
    args['ipspace'] = "Default"
    args['mtu'] = 1500
    args['ports'] = ["mohan9cluster2-01:e0b"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                     # get version
        SRR['port_detail_e0b'],
        SRR['zero_record'],                      # empty record for domain1 in ipspace Default
        SRR['broadcast_domain_record_split'],    # get domain2 details in ipspace ip1
        SRR['empty_good'],                       # create new broadcast domain domain1 in ipspace Default
        SRR['empty_good'],                       # Add e0b to domain1
        SRR['end_of_sequence']
    ]
    my_obj = broadcast_domain_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()
