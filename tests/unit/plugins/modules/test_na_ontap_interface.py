# (c) 2018-2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import json
import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_interface \
    import NetAppOntapInterface as interface_module, netmask_length_to_netmask, netmask_to_netmask_length


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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
        self.type = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        print(xml.to_string())
        if self.type == 'interface':
            xml = self.build_interface_info(self.params)
        elif self.type == 'interface_rename':
            self.type = 'interface'
        elif self.type == 'zapi_error':
            error = netapp_utils.zapi.NaApiError('test', 'error')
            raise error
        self.xml_out = xml
        return xml

    @staticmethod
    def build_interface_info(data):
        ''' build xml data for vserser-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'net-interface-info': {
                    'interface-name': data['name'],
                    'administrative-status': data['administrative-status'],
                    'failover-policy': data['failover-policy'],
                    'firewall-policy': data['firewall-policy'],
                    'is-auto-revert': data['is-auto-revert'],
                    'home-node': data['home_node'],
                    'home-port': data['home_port'],
                    'address': data['address'],
                    'netmask': data['netmask'],
                    'role': data['role'],
                    'protocols': data['protocols'] if data.get('protocols') else None,
                    'dns-domain-name': data['dns_domain_name'],
                    'listen-for-dns_query': data['listen_for_dns_query'],
                    'is-dns-update-enabled': data['is_dns_update_enabled']
                }
            }
        }
        xml.translate_struct(attributes)
        return xml


# @pytest.mark.skip()
class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_interface = {
            'name': 'test_lif',
            'administrative-status': 'up',
            'failover-policy': 'up',
            'firewall-policy': 'up',
            'is-auto-revert': 'true',
            'home_node': 'node',
            'role': 'data',
            'home_port': 'e0c',
            'address': '2.2.2.2',
            'netmask': '1.1.1.1',
            'dns_domain_name': 'test.com',
            'listen_for_dns_query': True,
            'is_dns_update_enabled': True,
            'admin_status': 'up'
        }

    def mock_args(self, use_rest='never'):
        return {
            'vserver': 'vserver',
            'interface_name': self.mock_interface['name'],
            'home_node': self.mock_interface['home_node'],
            'role': self.mock_interface['role'],
            'home_port': self.mock_interface['home_port'],
            'address': self.mock_interface['address'],
            'netmask': self.mock_interface['netmask'],
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'use_rest': use_rest
        }

    def get_interface_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_interface object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_interface object
        """
        interface_obj = interface_module()
        interface_obj.autosupport_log = Mock(return_value=None)
        if kind is None:
            interface_obj.server = MockONTAPConnection()
        else:
            interface_obj.server = MockONTAPConnection(kind=kind, data=self.mock_interface)
        return interface_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            interface_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_create_error_missing_param(self):
        # sourcery skip: class-extract-method
        ''' Test if create throws an error if required param 'role' is not specified'''
        data = self.mock_args()
        del data['role']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_interface_mock_object('interface').create_interface(None)
        msg = 'Error: Missing one or more required parameters for creating interface: ' \
              'home_port, netmask, role, home_node, address'
        expected = sorted(','.split(msg))
        received = sorted(','.split(exc.value.args[0]['msg']))
        assert expected == received

    def test_get_nonexistent_interface(self):
        ''' Test if get_interface returns None for non-existent interface '''
        set_module_args(self.mock_args())
        result = self.get_interface_mock_object().get_interface()
        assert result is None

    def test_get_existing_interface(self):
        ''' Test if get_interface returns None for existing interface '''
        set_module_args(self.mock_args())
        result = self.get_interface_mock_object(kind='interface').get_interface()
        assert result['interface_name'] == self.mock_interface['name']

    def test_successful_create(self):
        ''' Test successful create '''
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_interface_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_successful_create_for_NVMe(self):
        ''' Test successful create for NVMe protocol'''
        data = self.mock_args()
        data['protocols'] = 'fc-nvme'
        del data['address']
        del data['netmask']
        del data['home_port']
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_interface_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_create_idempotency_for_NVMe(self):
        ''' Test create idempotency for NVMe protocol '''
        data = self.mock_args()
        data['protocols'] = 'fc-nvme'
        del data['address']
        del data['netmask']
        del data['home_port']
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_interface_mock_object('interface').apply()
        assert not exc.value.args[0]['changed']

    def test_create_error_for_NVMe(self):
        ''' Test if create throws an error if required param 'protocols' uses NVMe'''
        data = self.mock_args()
        data['protocols'] = 'fc-nvme'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_interface_mock_object('interface').create_interface(None)
        msg = 'Error: Following parameters for creating interface are not supported for data-protocol fc-nvme: ' \
              'netmask, firewall_policy, address'
        expected = sorted(','.split(msg))
        received = sorted(','.split(exc.value.args[0]['msg']))
        assert expected == received

    def test_create_idempotency(self):
        ''' Test create idempotency '''
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_interface_mock_object('interface').apply()
        assert not exc.value.args[0]['changed']

    def test_successful_delete(self):
        ''' Test delete existing interface '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_interface_mock_object('interface').apply()
        assert exc.value.args[0]['changed']

    def test_delete_idempotency(self):
        ''' Test delete idempotency '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_interface_mock_object().apply()
        assert not exc.value.args[0]['changed']

    def test_successful_modify(self):
        ''' Test successful modify interface_minutes '''
        data = self.mock_args()
        data['home_port'] = 'new_port'
        data['dns_domain_name'] = 'test2.com'
        data['listen_for_dns_query'] = False
        data['is_dns_update_enabled'] = False
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            interface_obj = self.get_interface_mock_object('interface')
            interface_obj.apply()
        assert exc.value.args[0]['changed']

    def test_modify_idempotency(self):
        ''' Test modify idempotency '''
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_interface_mock_object('interface').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_interface.NetAppOntapInterface.get_interface')
    def test_error_message(self, get_interface):
        ''' Test modify idempotency '''
        data = self.mock_args()
        set_module_args(data)
        get_interface.side_effect = [None]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_interface_mock_object('zapi_error').apply()
        assert exc.value.args[0]['msg'] == 'Error Creating interface test_lif: NetApp API failed. Reason - test:error'

        data = self.mock_args()
        data['home_port'] = 'new_port'
        data['dns_domain_name'] = 'test2.com'
        data['listen_for_dns_query'] = False
        data['is_dns_update_enabled'] = False
        set_module_args(data)
        get_interface.side_effect = [
            self.mock_interface
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_interface_mock_object('zapi_error').apply()
        assert exc.value.args[0]['msg'] == 'Error modifying interface test_lif: NetApp API failed. Reason - test:error'

        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        current = self.mock_interface
        current['admin_status'] = 'down'
        get_interface.side_effect = [
            current
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_interface_mock_object('zapi_error').apply()
        assert exc.value.args[0]['msg'] == 'Error deleting interface test_lif: NetApp API failed. Reason - test:error'

    def test_successful_rename(self):
        ''' Test successful modify interface_minutes '''
        data = self.mock_args()
        data['home_port'] = 'new_port'
        data['dns_domain_name'] = 'test2.com'
        data['listen_for_dns_query'] = False
        data['is_dns_update_enabled'] = False
        data['from_name'] = 'from_interface_name'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            interface_obj = self.get_interface_mock_object('interface_rename')
            interface_obj.apply()
        assert exc.value.args[0]['changed']

    def test_negative_rename_not_found(self):
        ''' Test successful modify interface_minutes '''
        data = self.mock_args()
        data['home_port'] = 'new_port'
        data['dns_domain_name'] = 'test2.com'
        data['listen_for_dns_query'] = False
        data['is_dns_update_enabled'] = False
        data['from_name'] = 'from_interface_name'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            interface_obj = self.get_interface_mock_object()
            interface_obj.apply()
        msg = 'Error renaming interface test_lif: no interface with from_name from_interface_name.'
        assert msg in exc.value.args[0]['msg']


SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy_9_6_0')), None),
    'is_rest_95': (200, dict(version=dict(generation=9, major=5, minor=0, full='dummy_9_5_0')), None),
    'is_rest_96': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy_9_6_0')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': ({}, None, None),
    'zero_record': (200, {'records': []}, None),
    'one_record_home_node': (200, {'records': [
        {'name': 'node2_abc_if',
         'uuid': '54321',
         'enabled': True,
         'location': {'home_port': {'name': 'e0k'}, 'home_node': {'name': 'node2'}, 'node': {'name': 'node2'}}
         }]}, None),
    'one_record_vserver': (200, {'records': [
        {'name': 'abc_if',
         'uuid': '54321',
         'enabled': True,
         'location': {'home_port': {'name': 'e0k'}, 'home_node': {'name': 'node2'}, 'node': {'name': 'node2'}}
         }]}, None),
    'two_records': (200, {'records': [{'name': 'node2_abc_if'}, {'name': 'node2_abc_if'}]}, None),
    'precluster': (500, None, {'message': 'are available in precluster.'}),
    'cluster_identity': (200, {'location': 'Oz', 'name': 'abc'}, None),
    'nodes': (200, {'records': [
        {'name': 'node2', 'uuid': 'uuid2', 'cluster_interfaces': [{'ip': {'address': '10.10.10.2'}}]}
    ]}, None),
    'end_of_sequence': (None, None, "Unexpected call to send_request"),
    'generic_error': (None, "Expected error"),
}


# using pytest natively, without unittest.TestCase
@pytest.fixture
def patch_ansible():
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json) as mocks:
        yield mocks


def set_default_args(use_rest='always', **kwargs):
    hostname = '10.10.10.10'
    username = 'admin'
    password = 'password'
    if_name = 'abc_if'
    args = dict({
        'hostname': hostname,
        'username': username,
        'password': password,
        'home_port': 'e0k',
        'interface_name': if_name,
        'use_rest': use_rest
    })
    args.update(kwargs)
    if 'ip' in args and args.pop('ip'):
        args.update({
            'address': '10.12.12.13',
            'netmask': '255.255.192.0',
        })
    return args


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create_ip_no_svm(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', ip=True))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],     # get IP
        # SRR['zero_record'],     # get FC
        SRR['nodes'],           # get nodes
        SRR['empty_good'],      # post
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create_ip_no_svm_idempotent(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', ip=True))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record_home_node'],     # get IP
        # SRR['zero_record'],            # get FC
        SRR['nodes'],                    # get nodes
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is False
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create_ip_no_svm_idempotent_localhost(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', ip=True, home_node='localhost'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record_home_node'],     # get IP
        # SRR['zero_record'],            # get FC
        SRR['nodes'],                    # get nodes
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is False
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create_ip_with_svm(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', vserver='vserver', ip=True))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],     # get IP
        # SRR['zero_record'],     # get FC
        SRR['nodes'],           # get nodes
        SRR['empty_good'],      # post
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_create_ip(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', ip=True))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],     # get IP
        # SRR['zero_record'],     # get FC
        SRR['zero_record'],     # get nodes
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    msg = 'Error: Cannot guess home_node, home_node is required when home_port is present with REST.'
    assert msg in exc.value.args[0]['msg']
    # print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_create_no_ip_address(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],     # get IP
        SRR['zero_record'],     # get FC
        SRR['nodes'],           # get nodes
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    msg = 'Error: Missing one or more required parameters for creating interface: interface_type.'
    assert msg in exc.value.args[0]['msg']
    # print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_get_multiple_ip_if(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['two_records'],     # get IP
        SRR['zero_record'],     # get FC
        SRR['nodes'],           # get nodes
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    msg = 'Error: multiple records for: node2_abc_if'
    assert msg in exc.value.args[0]['msg']
    # print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_get_multiple_fc_if(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],     # get IP
        SRR['two_records'],     # get FC
        SRR['nodes'],           # get nodes
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    msg = 'Error: multiple records for: node2_abc_if'
    assert msg in exc.value.args[0]['msg']
    # print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_modify_idempotent_ip_no_svm(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', ip=True))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record_home_node'],      # get IP
        # SRR['zero_record'],     # get FC
        SRR['nodes'],           # get nodes
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is False
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_modify_ip_no_svm(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', ip=True, home_node='node1'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record_home_node'],      # get IP
        # SRR['zero_record'],     # get FC
        # SRR['nodes'],           # get nodes (for get) when home_node is missing
        SRR['empty_good'],      # patch
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_modify_ip_svm(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', ip=True, vserver='vserver', home_node='node1'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record_vserver'],      # get IP
        # SRR['zero_record'],           # get FC
        # SRR['nodes'],                   # get nodes (for get)
        SRR['empty_good'],              # patch
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert len(mock_request.mock_calls) == 3


@patch('time.sleep')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_migrate_ip_no_svm(mock_request, sleep_mock, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', ip=True, current_node='node1'))
    set_module_args(args)
    modified = copy.deepcopy(SRR['one_record_home_node'])
    modified[1]['records'][0]['location']['node']['name'] = 'node1'
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record_home_node'],      # get IP
        # SRR['zero_record'],     # get FC
        SRR['nodes'],           # get nodes (for get)
        SRR['empty_good'],      # patch
        SRR['one_record_home_node'],      # get - no change
        SRR['empty_good'],      # patch again
        modified,               # get
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert len(mock_request.mock_calls) == 7


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_delete_ip_no_svm(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', ip=True, state='absent'))
    set_module_args(args)
    modified = copy.deepcopy(SRR['one_record_home_node'])
    modified[1]['records'][0]['location']['node']['name'] = 'node1'
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record_home_node'],      # get IP
        # SRR['zero_record'],     # get FC
        SRR['nodes'],           # get nodes (for get)
        SRR['empty_good'],      # delete
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_delete_idempotent_ip_no_svm(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', ip=True, state='absent'))
    set_module_args(args)
    modified = copy.deepcopy(SRR['one_record_home_node'])
    modified[1]['records'][0]['location']['node']['name'] = 'node1'
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],         # get IP
        # SRR['zero_record'],       # get FC
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is False
    assert len(mock_request.mock_calls) == 2


def test_netmask_to_len():
    # note the address has host bits set
    assert netmask_to_netmask_length('10.10.10.10', '255.255.0.0') == '16'


def test_len_to_netmask():
    # note the address has host bits set
    assert netmask_length_to_netmask('10.10.10.10', '16') == '255.255.0.0'


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_derive_fc_protocol_fcp(mock_request):
    args = dict(set_default_args(protocols=['fcp']))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    my_obj.derive_fc_data_protocol()
    assert my_obj.parameters['data_protocol'] == 'fcp'


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_derive_fc_protocol_nvme(mock_request):
    args = dict(set_default_args(protocols=['fc-nvme']))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    my_obj.derive_fc_data_protocol()
    assert my_obj.parameters['data_protocol'] == 'fc_nvme'


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_derive_fc_protocol_nvme_empty(mock_request):
    args = dict(set_default_args(protocols=[]))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_derive_fc_protocol_nvme(mock_request, patch_ansible):
    args = dict(set_default_args(protocols=['fc-nvme', 'fcp']))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.derive_fc_data_protocol()
    print(mock_request.mock_calls)
    msg = "A single protocol entry is expected for FC interface, got ['fc-nvme', 'fcp']."
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_derive_fc_protocol_nvme_mismatch(mock_request, patch_ansible):
    args = dict(set_default_args(protocols=['fc-nvme'], data_protocol='fcp'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.derive_fc_data_protocol()
    print(mock_request.mock_calls)
    msg = "Error: mismatch between configured data_protocol: fcp and data_protocols: ['fc-nvme']"
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_derive_interface_type_nvme(mock_request):
    args = dict(set_default_args(protocols=['fc-nvme']))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    my_obj.derive_interface_type()
    assert my_obj.parameters['interface_type'] == 'fc'


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_derive_interface_type_iscsi(mock_request):
    args = dict(set_default_args(protocols=['iscsi']))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    my_obj.derive_interface_type()
    assert my_obj.parameters['interface_type'] == 'ip'


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_derive_interface_type_cluster(mock_request):
    args = dict(set_default_args(role='cluster'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    my_obj.derive_interface_type()
    assert my_obj.parameters['interface_type'] == 'ip'


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_derive_interface_type_nvme_mismatch(mock_request, patch_ansible):
    args = dict(set_default_args(protocols=['fc-nvme'], interface_type='ip'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.derive_interface_type()
    print(mock_request.mock_calls)
    msg = "Error: mismatch between configured interface_type: ip and derived interface_type: fc."
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_derive_interface_type_unknown(mock_request, patch_ansible):
    args = dict(set_default_args(protocols=['unexpected']))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.derive_interface_type()
    print(mock_request.mock_calls)
    msg = "Error: Unexpected value(s) for protocols: ['unexpected']"
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_derive_interface_type_multiple(mock_request, patch_ansible):
    args = dict(set_default_args(protocols=['fc-nvme', 'cifs']))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.derive_interface_type()
    print(mock_request.mock_calls)
    msg = "Error: Incompatible value(s) for protocols: ['fc-nvme', 'cifs']"
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_derive_block_file_type_fcp(mock_request):
    args = dict(set_default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    block_p, file_p = my_obj.derive_block_file_type(['fcp'])
    assert block_p, not file_p


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_derive_block_file_type_cifs(mock_request):
    args = dict(set_default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    block_p, file_p = my_obj.derive_block_file_type(['cifs'])
    assert not block_p, file_p


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_map_failover_policy(mock_request):
    args = dict(set_default_args(failover_policy='local-only'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    my_obj = interface_module()
    my_obj.map_failover_policy()
    assert my_obj.parameters['failover_scope'] == 'home_node_only'


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_unsupported_zapi_option_fail(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', is_ipv4_link_local=True))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['end_of_sequence']
    ]
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = interface_module()
    print(mock_request.mock_calls)
    msg = "REST API currently does not support 'is_ipv4_link_local'"
    assert msg in exc.value.args[0]['msg']
    # print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 0


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_unsupported_zapi_option_force_zapi(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', is_ipv4_link_local=True, use_rest='auto'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = interface_module()
    print(mock_request.mock_calls)
    msg = "missing required arguments: vserver"
    assert msg in exc.value.args[0]['msg']
    # print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 1


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_unsupported_zapi_option_force_zapi(mock_request, mock_netapp_lib, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(ipspace='cluster', is_ipv4_link_local=True, use_rest='auto'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    mock_netapp_lib.return_value = False
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = interface_module()
    print(mock_request.mock_calls)
    msg = "the python NetApp-Lib module is required"
    assert msg in exc.value.args[0]['msg']
    # print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 1


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_unsupported_rest_version(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(use_rest='always'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_96'],
        SRR['end_of_sequence']
    ]
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = interface_module()
    print(mock_request.mock_calls)
    msg = "Error: REST requires ONTAP 9.7 or later for interface APIs."
    assert msg in exc.value.args[0]['msg']
    # print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 1


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_auto_falls_back_to_zapi(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args(use_rest='auto'))
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    # with pytest.raises((AnsibleExitJson, AnsibleFailJson)) as exc:
    with pytest.raises(AnsibleFailJson) as exc:
        interface_module()
    # vserver is a required parameter with ZAPI
    msg = "missing required argument with ZAPI: vserver"
    assert msg in exc.value.args[0]['msg']
    assert len(mock_request.mock_calls) == 1
