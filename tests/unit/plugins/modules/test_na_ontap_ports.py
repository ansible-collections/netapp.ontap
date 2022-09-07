# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for ONTAP Ansible module: na_ontap_port'''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import assert_no_warnings, set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports \
    import NetAppOntapPorts as port_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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
        self.xml_out = xml
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def mock_args(self, choice):
        if choice == 'broadcast_domain':
            return {
                'names': ['test_port_1', 'test_port_2'],
                'resource_name': 'test_domain',
                'resource_type': 'broadcast_domain',
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'use_rest': 'never'
            }
        elif choice == 'portset':
            return {
                'names': ['test_lif'],
                'resource_name': 'test_portset',
                'resource_type': 'portset',
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'vserver': 'test_vserver',
                'use_rest': 'never'
            }

    def get_port_mock_object(self):
        """
        Helper method to return an na_ontap_port object
        """
        port_obj = port_module()
        port_obj.server = MockONTAPConnection()
        return port_obj

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.add_broadcast_domain_ports')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.get_broadcast_domain_ports')
    def test_successfully_add_broadcast_domain_ports(self, get_broadcast_domain_ports, add_broadcast_domain_ports, ignored):
        ''' Test successful add broadcast domain ports '''
        data = self.mock_args('broadcast_domain')
        set_module_args(data)
        get_broadcast_domain_ports.side_effect = [
            []
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.add_broadcast_domain_ports')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.get_broadcast_domain_ports')
    def test_add_broadcast_domain_ports_idempotency(self, get_broadcast_domain_ports, add_broadcast_domain_ports, ignored):
        ''' Test add broadcast domain ports idempotency '''
        data = self.mock_args('broadcast_domain')
        set_module_args(data)
        get_broadcast_domain_ports.side_effect = [
            ['test_port_1', 'test_port_2']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object().apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.add_portset_ports')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.portset_get')
    def test_successfully_add_portset_ports(self, portset_get, add_portset_ports, ignored):
        ''' Test successful add portset ports '''
        data = self.mock_args('portset')
        set_module_args(data)
        portset_get.side_effect = [
            []
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.add_portset_ports')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.portset_get')
    def test_add_portset_ports_idempotency(self, portset_get, add_portset_ports, ignored):
        ''' Test add portset ports idempotency '''
        data = self.mock_args('portset')
        set_module_args(data)
        portset_get.side_effect = [
            ['test_lif']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object().apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.add_broadcast_domain_ports')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.get_broadcast_domain_ports')
    def test_successfully_remove_broadcast_domain_ports(self, get_broadcast_domain_ports, add_broadcast_domain_ports, ignored):
        ''' Test successful remove broadcast domain ports '''
        data = self.mock_args('broadcast_domain')
        data['state'] = 'absent'
        set_module_args(data)
        get_broadcast_domain_ports.side_effect = [
            ['test_port_1', 'test_port_2']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.add_portset_ports')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ports.NetAppOntapPorts.portset_get')
    def test_remove_add_portset_ports(self, portset_get, add_portset_ports, ignored):
        ''' Test successful remove portset ports '''
        data = self.mock_args('portset')
        data['state'] = 'absent'
        set_module_args(data)
        portset_get.side_effect = [
            ['test_lif']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object().apply()
        assert exc.value.args[0]['changed']


def default_args(choice=None, resource_name=None, portset_type=None):
    args = {
        'state': 'present',
        'hostname': '10.10.10.10',
        'username': 'admin',
        'https': 'true',
        'validate_certs': 'false',
        'password': 'password',
        'use_rest': 'always'
    }
    if choice == 'broadcast_domain':
        args['resource_type'] = "broadcast_domain"
        args['resource_name'] = "domain2"
        args['ipspace'] = "ip1"
        args['names'] = ["mohan9cluster2-01:e0b", "mohan9cluster2-01:e0d"]
        return args
    if choice == 'portset':
        args['portset_type'] = portset_type
        args['resource_name'] = resource_name
        args['resource_type'] = 'portset'
        args['vserver'] = 'svm3'
        return args
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
    'broadcast_domain_record1': (200, {
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
    }, None),
    'iscsips': (200, {
        "num_records": 1,
        "records": [
            {
                "uuid": "52e31a9d-72e2-11ec-95ea-005056b3b297",
                "svm": {"name": "svm3"},
                "name": "iscsips"
            }]
    }, None),
    'iscsips_updated': (200, {
        "num_records": 1,
        "records": [
            {
                "uuid": "52e31a9d-72e2-ec11-95ea-005056b3b298",
                "svm": {"name": "svm3"},
                "name": "iscsips_updated",
                "interfaces": [
                    {
                        "uuid": "6a82e94a-72da-11ec-95ea-005056b3b297",
                        "ip": {"name": "lif_svm3_856"}
                    }]
            }]
    }, None),
    'mixedps': (200, {
        "num_records": 1,
        "records": [
            {
                "uuid": "ba02916a-72da-11ec-95ea-005056b3b297",
                "svm": {
                    "name": "svm3"
                },
                "name": "mixedps",
                "interfaces": [
                    {
                        "uuid": "2c373289-728f-11ec-95ea-005056b3b297",
                        "fc": {"name": "lif_svm3_681_2"}
                    },
                    {
                        "uuid": "d229cc03-7797-11ec-95ea-005056b3b297",
                        "fc": {"name": "lif_svm3_681_1_1"}
                    },
                    {
                        "uuid": "d24e03c6-7797-11ec-95ea-005056b3b297",
                        "fc": {"name": "lif_svm3_681_1_2"}
                    }]
            }]
    }, None),
    'mixedps_updated': (200, {
        "num_records": 1,
        "records": [
            {
                "uuid": "ba02916a-72da-11ec-95ea-005056b3b297",
                "svm": {
                    "name": "svm3"
                },
                "name": "mixedps_updated",
                "interfaces": [
                    {
                        "uuid": "6a82e94a-72da-11ec-95ea-005056b3b297",
                        "ip": {"name": "lif_svm3_856"}
                    },
                    {
                        "uuid": "2bf30606-728f-11ec-95ea-005056b3b297",
                        "fc": {"name": "lif_svm3_681_1"}
                    },
                    {
                        "uuid": "2c373289-728f-11ec-95ea-005056b3b297",
                        "fc": {"name": "lif_svm3_681_2"}
                    },
                    {
                        "uuid": "d229cc03-7797-11ec-95ea-005056b3b297",
                        "fc": {"name": "lif_svm3_681_1_1"}
                    },
                    {
                        "uuid": "d24e03c6-7797-11ec-95ea-005056b3b297",
                        "fc": {"name": "lif_svm3_681_1_2"}
                    }]
            }]
    }, None),
    'lif_svm3_681_1_1': (200, {
        "num_records": 1,
        "records": [{"uuid": "d229cc03-7797-11ec-95ea-005056b3b297"}]
    }, None),
    'lif_svm3_681_1_2': (200, {
        "num_records": 1,
        "records": [{"uuid": "d24e03c6-7797-11ec-95ea-005056b3b297"}]
    }, None),
    'lif_svm3_681_1': (200, {
        "num_records": 1,
        "records": [{"uuid": "2bf30606-728f-11ec-95ea-005056b3b297"}]
    }, None),
    'lif_svm3_681_2': (200, {
        "num_records": 1,
        "records": [{"uuid": "2c373289-728f-11ec-95ea-005056b3b297"}]
    }, None),
    'lif_svm3_856': (200, {
        "num_records": 1,
        "records": [{"uuid": "6a82e94a-72da-11ec-95ea-005056b3b297"}]
    }, None)
}


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args(dict(hostname=''))
        port_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'missing required arguments:'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_add_broadcast_domain_port_rest(mock_request, patch_ansible):
    ''' test add broadcast domain port'''
    args = dict(default_args('broadcast_domain'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['port_detail_e0b'],
        SRR['port_detail_e0d'],
        SRR['broadcast_domain_record1'],   # get
        SRR['empty_good'],                 # add e0b
        SRR['empty_good'],                 # add e0d
        SRR['end_of_sequence']
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_add_broadcast_domain_port_rest_idempotent(mock_request, patch_ansible):
    ''' test add broadcast domain port'''
    args = dict(default_args('broadcast_domain'))
    args['resource_name'] = "domain2"
    args['names'] = ["mohan9cluster2-01:e0a"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['port_detail_e0a'],
        SRR['broadcast_domain_record1'],   # get
        SRR['end_of_sequence']
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_remove_broadcast_domain_port_rest(mock_request, patch_ansible):
    ''' test remove broadcast domain port'''
    args = dict(default_args('broadcast_domain'))
    args['resource_name'] = "domain1"
    args['names'] = ["mohan9cluster2-01:e0b", "mohan9cluster2-01:e0d"]
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['port_detail_e0b'],
        SRR['port_detail_e0d'],
        SRR['broadcast_domain_record'],    # get
        SRR['empty_good'],                 # remove e0b and e0d
        SRR['end_of_sequence']
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_remove_broadcast_domain_port_rest_idempotent(mock_request, patch_ansible):
    ''' test remove broadcast domain port'''
    args = dict(default_args('broadcast_domain'))
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['port_detail_e0b'],
        SRR['port_detail_e0d'],
        SRR['broadcast_domain_record1'],   # get
        SRR['end_of_sequence']
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_get_ports_rest(mock_request, patch_ansible):
    ''' test get port '''
    args = dict(default_args('broadcast_domain'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],            # get version
        SRR['generic_error'],          # Error in getting ports
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = port_module()
    print('Info: %s' % exc.value.args[0])
    msg = 'calling: network/ethernet/ports: got Expected error.'
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_get_broadcast_domain_ports_rest(mock_request, patch_ansible):
    ''' test get broadcast domain '''
    args = dict(default_args('broadcast_domain'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],            # get version
        SRR['port_detail_e0b'],
        SRR['port_detail_e0d'],
        SRR['generic_error'],          # Error in getting broadcast domain ports
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'calling: network/ethernet/broadcast-domains: got Expected error.'
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_add_broadcast_domain_ports_rest(mock_request, patch_ansible):
    ''' test add broadcast domain ports '''
    args = dict(default_args('broadcast_domain'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['port_detail_e0b'],
        SRR['port_detail_e0d'],
        SRR['broadcast_domain_record1'],   # get
        SRR['generic_error'],              # Error in adding ports
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'got Expected error.'
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_remove_broadcast_domain_ports_rest(mock_request, patch_ansible):
    ''' test remove broadcast domain ports '''
    args = dict(default_args('broadcast_domain'))
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['port_detail_e0b'],
        SRR['port_detail_e0d'],
        SRR['broadcast_domain_record'],    # get
        SRR['generic_error'],              # Error in removing ports
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error removing ports: calling: private/cli/network/port/broadcast-domain/remove-ports: got Expected error.'
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_invalid_ports_rest(mock_request, patch_ansible):
    ''' test remove broadcast domain ports '''
    args = dict(default_args('broadcast_domain'))
    args['names'] = ["mohan9cluster2-01e0b"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['generic_error']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = port_module()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error: Invalid value specified for port: mohan9cluster2-01e0b, provide port name as node_name:port_name'
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_broadcast_domain_missing_ports_rest(mock_request, patch_ansible):
    ''' test get ports '''
    args = dict(default_args('broadcast_domain'))
    args['names'] = ["mohan9cluster2-01:e0l"]
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['zero_record']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = port_module()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error: ports: mohan9cluster2-01:e0l not found'
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_add_portset_port_iscsi_rest(mock_request, patch_ansible):
    ''' test add portset port'''
    args = dict(default_args('portset', 'iscsips', 'iscsi'))
    args['names'] = ['lif_svm3_856']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],                    # get version
        SRR['lif_svm3_856'],
        SRR['iscsips'],                    # get portset
        SRR['empty_good'],                 # add lif_svm3_856
        SRR['end_of_sequence']
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_add_portset_port_iscsi_rest_idempotent(mock_request, patch_ansible):
    ''' test add portset port'''
    args = dict(default_args('portset', 'iscsips_updated', 'iscsi'))
    args['names'] = ['lif_svm3_856']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],                       # get version
        SRR['lif_svm3_856'],
        SRR['iscsips_updated'],               # get
        SRR['end_of_sequence']
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_remove_portset_port_iscsi_rest(mock_request, patch_ansible):
    ''' test remove portset port'''
    args = dict(default_args('portset', 'iscsips_updated', 'iscsi'))
    args['names'] = ['lif_svm3_856']
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],                    # get version
        SRR['lif_svm3_856'],
        SRR['iscsips_updated'],
        SRR['empty_good'],                 # remove lif_svm3_856
        SRR['end_of_sequence']
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_add_portset_port_mixed_rest(mock_request, patch_ansible):
    ''' test add portset port'''
    args = dict(default_args('portset', 'mixedps', 'mixed'))
    args['names'] = ['lif_svm3_856', 'lif_svm3_681_1']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],                    # get version
        SRR['lif_svm3_856'],               # get lif_svm3_856 in ip
        SRR['zero_record'],                # lif_svm3_856 not found in fc
        SRR['zero_record'],                # lif_svm3_681_1 not found in ip
        SRR['lif_svm3_681_1'],             # get lif_svm3_681_1 in fc
        SRR['mixedps'],                    # get portset
        SRR['empty_good'],                 # Add both ip and fc to mixed portset
        SRR['end_of_sequence']
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_get_portset_fetching_rest(mock_request, patch_ansible):
    ''' test get port '''
    args = dict(default_args('portset', 'iscsips_updated', 'mixed'))
    args['names'] = ['lif_svm3_856']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],            # get version
        SRR['generic_error'],      # Error in getting portset
        SRR['generic_error']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = port_module()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error fetching lifs details for lif_svm3_856: calling: network/ip/interfaces: got Expected error.'
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_get_portset_fetching_portset_ip_rest(mock_request, patch_ansible):
    ''' test get port ip'''
    args = dict(default_args('portset', 'iscsips_updated', 'ip'))
    args['names'] = ['lif_svm3_856']
    del args['portset_type']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],            # get version
        SRR['lif_svm3_856'],
        SRR['generic_error'],
        SRR['iscsips_updated'],
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj = port_module()
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_get_portset_fetching_portset_fcp_rest(mock_request, patch_ansible):
    ''' test get port fcp'''
    args = dict(default_args('portset', 'mixedps_updated', 'fcp'))
    args['names'] = ['lif_svm3_681_1']
    del args['portset_type']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],            # get version
        SRR['generic_error'],
        SRR['lif_svm3_681_1'],
        SRR['mixedps_updated'],
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj = port_module()
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_get_portset_rest(mock_request, patch_ansible):
    ''' test get portset '''
    args = dict(default_args('portset', 'iscsips_updated', 'iscsi'))
    args['names'] = ['lif_svm3_856']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],               # get version
        SRR['lif_svm3_856'],
        SRR['generic_error'],          # Error in getting portset
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'calling: protocols/san/portsets: got Expected error'
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_get_portset_error_rest(mock_request, patch_ansible):
    ''' test get portset '''
    args = dict(default_args('portset', 'iscsips_updated', 'iscsi'))
    args['names'] = ['lif_svm3_856']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],               # get version
        SRR['lif_svm3_856'],
        SRR['zero_record'],
        SRR['generic_error'],          # Error in getting portset
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: Portset 'iscsips_updated' does not exist"
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_get_portset_missing_rest(mock_request, patch_ansible):
    ''' test get portset '''
    args = dict(default_args('portset', 'iscsips_updated', 'iscsi'))
    args['names'] = ['lif_svm3_856']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],               # get version
        SRR['zero_record'],
        SRR['generic_error'],          # Error in getting portset
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = port_module()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: lifs: lif_svm3_856 of type iscsi not found in vserver svm3"
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_get_portset_missing_state_absent_rest(mock_request, patch_ansible):
    ''' test get portset '''
    args = dict(default_args('portset', 'iscsips_updated', 'iscsi'))
    args['names'] = ['lif_svm3_856']
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],               # get version
        SRR['lif_svm3_856'],
        SRR['zero_record'],
        SRR['end_of_sequence']
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_add_portset_ports_rest(mock_request, patch_ansible):
    ''' test add portset ports '''
    args = dict(default_args('portset', 'iscsips', 'iscsi'))
    args['names'] = ['lif_svm3_856']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],                   # get version
        SRR['lif_svm3_856'],
        SRR['iscsips'],
        SRR['generic_error'],              # Error in adding ports
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'calling: protocols/san/portsets/52e31a9d-72e2-11ec-95ea-005056b3b297/interfaces: got Expected error.'
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_remove_portset_ports_rest(mock_request, patch_ansible):
    ''' test remove broadcast domain ports '''
    args = dict(default_args('portset', 'iscsips_updated', 'iscsi'))
    args['names'] = ['lif_svm3_856']
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],                # get version
        SRR['lif_svm3_856'],
        SRR['iscsips_updated'],
        SRR['generic_error'],           # Error in removing ports
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'calling: protocols/san/portsets/52e31a9d-72e2-ec11-95ea-005056b3b298/interfaces/6a82e94a-72da-11ec-95ea-005056b3b297: got Expected error.'
    assert msg in exc.value.args[0]['msg']
    assert_no_warnings()
