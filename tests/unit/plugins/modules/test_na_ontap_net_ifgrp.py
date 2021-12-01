# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_ifgrp \
    import NetAppOntapIfGrp as ifgrp_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


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
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.kind == 'ifgrp':
            xml = self.build_ifgrp_info(self.params)
        elif self.kind == 'ifgrp-ports':
            xml = self.build_ifgrp_ports_info(self.params)
        elif self.kind == 'ifgrp-fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_ifgrp_info(ifgrp_details):
        ''' build xml data for ifgrp-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'net-port-info': {
                    'port': ifgrp_details['name'],
                    'ifgrp-distribution-function': 'mac',
                    'ifgrp-mode': ifgrp_details['mode'],
                    'node': ifgrp_details['node']
                }
            }
        }
        xml.translate_struct(attributes)
        return xml

    @staticmethod
    def build_ifgrp_ports_info(data):
        ''' build xml data for ifgrp-ports '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'attributes': {
                'net-ifgrp-info': {
                    'ports': [
                        {'lif-bindable': data['ports'][0]},
                        {'lif-bindable': data['ports'][1]},
                        {'lif-bindable': data['ports'][2]}
                    ]
                }
            }
        }
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_ifgrp = {
            'name': 'test',
            'port': 'a1',
            'node': 'test_vserver',
            'mode': 'something'
        }

    def mock_args(self):
        return {
            'name': self.mock_ifgrp['name'],
            'distribution_function': 'mac',
            'ports': [self.mock_ifgrp['port']],
            'node': self.mock_ifgrp['node'],
            'mode': self.mock_ifgrp['mode'],
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_ifgrp_mock_object(self, kind=None, data=None):
        """
        Helper method to return an na_ontap_net_ifgrp object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_net_ifgrp object
        """
        obj = ifgrp_module()
        obj.autosupport_log = Mock(return_value=None)
        if data is None:
            data = self.mock_ifgrp
        obj.server = MockONTAPConnection(kind=kind, data=data)
        return obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            ifgrp_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_nonexistent_ifgrp(self):
        ''' Test if get_ifgrp returns None for non-existent ifgrp '''
        set_module_args(self.mock_args())
        result = self.get_ifgrp_mock_object().get_if_grp()
        assert result is None

    def test_get_existing_ifgrp(self):
        ''' Test if get_ifgrp returns details for existing ifgrp '''
        set_module_args(self.mock_args())
        result = self.get_ifgrp_mock_object('ifgrp').get_if_grp()
        assert result['name'] == self.mock_ifgrp['name']

    def test_successful_create(self):
        ''' Test successful create '''
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ifgrp_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_successful_delete(self):
        ''' Test delete existing volume '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ifgrp_mock_object('ifgrp').apply()
        assert exc.value.args[0]['changed']

    def test_successful_modify(self):
        ''' Test delete existing volume '''
        data = self.mock_args()
        data['ports'] = ['1', '2', '3']
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ifgrp_mock_object('ifgrp').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_ifgrp.NetAppOntapIfGrp.get_if_grp')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_ifgrp.NetAppOntapIfGrp.create_if_grp')
    def test_create_called(self, create_ifgrp, get_ifgrp):
        data = self.mock_args()
        set_module_args(data)
        get_ifgrp.return_value = None
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ifgrp_mock_object().apply()
        get_ifgrp.assert_called_with()
        create_ifgrp.assert_called_with()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_ifgrp.NetAppOntapIfGrp.add_port_to_if_grp')
    def test_if_ports_are_added_after_create(self, add_ports):
        ''' Test successful create '''
        data = self.mock_args()
        set_module_args(data)
        self.get_ifgrp_mock_object().create_if_grp()
        add_ports.assert_called_with('a1')

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_ifgrp.NetAppOntapIfGrp.get_if_grp')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_ifgrp.NetAppOntapIfGrp.delete_if_grp')
    def test_delete_called(self, delete_ifgrp, get_ifgrp):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        get_ifgrp.return_value = Mock()
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ifgrp_mock_object().apply()
        get_ifgrp.assert_called_with()
        delete_ifgrp.assert_called_with(None)

    def test_get_return_value(self):
        data = self.mock_args()
        set_module_args(data)
        result = self.get_ifgrp_mock_object('ifgrp').get_if_grp()
        assert result['name'] == data['name']
        assert result['mode'] == data['mode']
        assert result['node'] == data['node']

    def test_get_ports_list(self):
        data = self.mock_args()
        data['ports'] = ['e0a', 'e0b', 'e0c']
        set_module_args(data)
        result = self.get_ifgrp_mock_object('ifgrp-ports', data).get_if_grp_ports()
        assert result['ports'] == data['ports']

    def test_add_port_packet(self):
        data = self.mock_args()
        set_module_args(data)
        obj = self.get_ifgrp_mock_object('ifgrp')
        obj.add_port_to_if_grp('addme')
        assert obj.server.xml_in['port'] == 'addme'

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_ifgrp.NetAppOntapIfGrp.remove_port_to_if_grp')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_ifgrp.NetAppOntapIfGrp.add_port_to_if_grp')
    def test_modify_ports_calls_remove_existing_ports(self, add_port, remove_port):
        ''' Test if already existing ports are not being added again '''
        data = self.mock_args()
        data['ports'] = ['1', '2']
        set_module_args(data)
        self.get_ifgrp_mock_object('ifgrp').modify_ports(current_ports=['1', '2', '3'])
        assert remove_port.call_count == 1
        assert add_port.call_count == 0

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_ifgrp.NetAppOntapIfGrp.remove_port_to_if_grp')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_ifgrp.NetAppOntapIfGrp.add_port_to_if_grp')
    def test_modify_ports_calls_add_new_ports(self, add_port, remove_port):
        ''' Test new ports are added '''
        data = self.mock_args()
        data['ports'] = ['1', '2', '3', '4']
        set_module_args(data)
        self.get_ifgrp_mock_object('ifgrp').modify_ports(current_ports=['1', '2'])
        assert remove_port.call_count == 0
        assert add_port.call_count == 2

    def test_get_ports_returns_none(self):
        set_module_args(self.mock_args())
        result = self.get_ifgrp_mock_object().get_if_grp_ports()
        assert result['ports'] == []
        result = self.get_ifgrp_mock_object().get_if_grp()
        assert result is None

    def test_if_all_methods_catch_exception(self):
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_ifgrp_mock_object('ifgrp-fail').get_if_grp()
        assert 'Error getting if_group test' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_ifgrp_mock_object('ifgrp-fail').create_if_grp()
        assert 'Error creating if_group test' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_ifgrp_mock_object('ifgrp-fail').get_if_grp_ports()
        assert 'Error getting if_group ports test' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_ifgrp_mock_object('ifgrp-fail').add_port_to_if_grp('test-port')
        assert 'Error adding port test-port to if_group test' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_ifgrp_mock_object('ifgrp-fail').remove_port_to_if_grp('test-port')
        assert 'Error removing port test-port to if_group test' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_ifgrp_mock_object('ifgrp-fail').delete_if_grp()
        assert 'Error deleting if_group test' in exc.value.args[0]['msg']


WARNINGS = list()


def warn(dummy, msg):
    WARNINGS.append(msg)


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
    'ifgrp_record': (200, {
        "num_records": 2,
        "records": [
            {
                'lag': {
                    'distribution_policy': 'ip',
                    'mode': 'multimode_lacp'
                },
                'name': 'a0b',
                'node': {'name': 'mohan9cluster2-01'},
                'type': 'lag',
                'uuid': '1b830a46-47cd-11ec-90df-005056b3dfc8'
            },
            {
                'broadcast_domain': {
                    'ipspace': {'name': 'ip1'},
                    'name': 'test1'
                },
                'lag': {
                    'distribution_policy': 'ip',
                    'member_ports': [
                        {
                            'name': 'e0d',
                            'node': {'name': 'mohan9cluster2-01'},
                        }],
                    'mode': 'multimode_lacp'},
                'name': 'a0d',
                'node': {'name': 'mohan9cluster2-01'},
                'type': 'lag',
                'uuid': '5aeebc96-47d7-11ec-90df-005056b3dfc8'
            },
            {
                'broadcast_domain': {
                    'ipspace': {'name': 'ip1'},
                    'name': 'test1'
                },
                'lag': {
                    'distribution_policy': 'ip',
                    'member_ports': [
                        {
                            'name': 'e0c',
                            'node': {'name': 'mohan9cluster2-01'},
                        },
                        {
                            'name': 'e0a',
                            'node': {'name': 'mohan9cluster2-01'},
                        }],
                    'mode': 'multimode_lacp'
                },
                'name': 'a0d',
                'node': {'name': 'mohan9cluster2-01'},
                'type': 'lag',
                'uuid': '5aeebc96-47d7-11ec-90df-005056b3dsd4'
            }]
    }, None),
    'ifgrp_record_create': (200, {
        "num_records": 1,
        "records": [
            {
                'lag': {
                    'distribution_policy': 'ip',
                    'mode': 'multimode_lacp'
                },
                'name': 'a0b',
                'node': {'name': 'mohan9cluster2-01'},
                'type': 'lag',
                'uuid': '1b830a46-47cd-11ec-90df-005056b3dfc8'
            }]
    }, None),
    'ifgrp_record_modify': (200, {
        "num_records": 1,
        "records": [
            {
                'broadcast_domain': {
                    'ipspace': {'name': 'ip1'},
                    'name': 'test1'
                },
                'lag': {
                    'distribution_policy': 'ip',
                    'member_ports': [
                        {
                            'name': 'e0c',
                            'node': {'name': 'mohan9cluster2-01'},
                        },
                        {
                            'name': 'e0d',
                            'node': {'name': 'mohan9cluster2-01'},
                        }],
                    'mode': 'multimode_lacp'
                },
                'name': 'a0d',
                'node': {'name': 'mohan9cluster2-01'},
                'type': 'lag',
                'uuid': '5aeebc96-47d7-11ec-90df-005056b3dsd4'
            }]
    }, None)
}


# using pytest natively, without unittest.TestCase
@pytest.fixture
def patch_ansible():
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json,
                        warn=warn) as mocks:
        global WARNINGS
        WARNINGS = []
        yield mocks


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args(dict(hostname=''))
        ifgrp_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'missing required arguments:'
    assert msg in exc.value.args[0]['msg']


def test_module_fail_when_broadcast_domain_ipspace(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args(dict(hostname=''))
        ifgrp_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'missing required arguments:'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_broadcast_domain_ipspace_rest_ontap96(mock_request, patch_ansible):
    '''throw error if broadcast_domain and ipspace are not set'''
    args = dict(default_args())
    args['ports'] = "e0c"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    args['node'] = "mohan9cluster2-01"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_6'],         # get version
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        ifgrp_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'are mandatory fields with ONTAP 9.6 and 9.7'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_broadcast_domain_ipspace_rest_required_together(mock_request, patch_ansible):
    '''throw error if one of broadcast_domain or ipspace only set'''
    args = dict(default_args())
    args['ports'] = "e0c"
    args['distribution_function'] = "ip"
    args['ipspace'] = "Default"
    args['mode'] = "multimode_lacp"
    args['node'] = "mohan9cluster2-01"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_6'],         # get version
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        ifgrp_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'parameters are required together: broadcast_domain, ipspace'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_ifgrp_not_found_from_lag_ports(mock_request, patch_ansible):
    ''' throw error if lag not found with both ports and from_lag_ports '''
    args = dict(default_args())
    args['node'] = "mohan9-vsim1"
    args['ports'] = "e0f"
    args['from_lag_ports'] = "e0l"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],          # get version
        SRR['ifgrp_record']         # get for ports
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: cannot find LAG matching from_lag_ports: '['e0l']'."
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_from_lag_ports_1_or_more_ports_not_in_current(mock_request, patch_ansible):
    ''' throw error if 1 or more from_lag_ports not found in current '''
    args = dict(default_args())
    args['node'] = "mohan9-vsim1"
    args['ports'] = "e0f"
    args['from_lag_ports'] = "e0d,e0h"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],        # get version
    ]
    my_obj = ifgrp_module()
    my_obj.current_records = SRR['ifgrp_record'][1]['records']
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: cannot find LAG matching from_lag_ports: '['e0d', 'e0h']'."
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_from_lag_ports_are_in_different_LAG(mock_request, patch_ansible):
    ''' throw error if ports in from_lag_ports are in different LAG '''
    args = dict(default_args())
    args['node'] = "mohan9-vsim1"
    args['ports'] = "e0f"
    args['from_lag_ports'] = "e0d,e0c"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],        # get version
        SRR['ifgrp_record']        # get
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = "'e0d, e0c' are in different LAG"
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_try_to_delete_only_partial_match_found(mock_request, patch_ansible):
    ''' delete only with exact match of ports'''
    args = dict(default_args())
    args['node'] = "mohan9cluster2-01"
    args['ports'] = "e0c"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    args['broadcast_domain'] = "test1"
    args['ipspace'] = "ip1"
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['ifgrp_record'],        # get
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_try_to_delete_ports_in_different_LAG(mock_request, patch_ansible):
    ''' if ports are in different LAG, not to delete and returk ok'''
    args = dict(default_args())
    args['node'] = "mohan9cluster2-01"
    args['ports'] = "e0c,e0d"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    args['broadcast_domain'] = "test1"
    args['ipspace'] = "ip1"
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['ifgrp_record'],        # get
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_partial_match(mock_request, patch_ansible):
    '''fail if partial match only found in from_lag_ports'''
    args = dict(default_args())
    args['node'] = "mohan9cluster2-01"
    args['from_lag_ports'] = "e0c,e0a,e0v"
    args['ports'] = "e0n"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    args['state'] = 'present'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['ifgrp_record'],        # get
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: cannot find LAG matching from_lag_ports: '['e0c', 'e0a', 'e0v']'."
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_partial_match_ports_empty_record_from_lag_ports(mock_request, patch_ansible):
    ''' remove port e0a from ifgrp a0d with ports e0d,e0c'''
    args = dict(default_args())
    args['node'] = "mohan9cluster2-01"
    args['ports'] = "e0c"
    args['from_lag_ports'] = "e0k"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['ifgrp_record_modify']         # get
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: cannot find LAG matching from_lag_ports: '['e0k']'."
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_create_ifgrp_port(mock_request, patch_ansible):
    ''' test create ifgrp '''
    args = dict(default_args())
    args['node'] = "mohan9-vsim1"
    args['ports'] = "e0c,e0a"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['ifgrp_record_create'],        # get
        SRR['empty_good'],                 # create
        SRR['end_of_sequence']
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_create_ifgrp_port_idempotent(mock_request, patch_ansible):
    ''' test create ifgrp idempotent '''
    args = dict(default_args())
    args['node'] = "mohan9cluster2-01"
    args['ports'] = "e0c,e0a"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['ifgrp_record'],               # get
        SRR['end_of_sequence']
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_modify_ifgrp_port(mock_request, patch_ansible):
    ''' remove port e0a from ifgrp a0d with ports e0d,e0c'''
    args = dict(default_args())
    args['node'] = "mohan9cluster2-01"
    args['ports'] = "e0c"
    args['from_lag_ports'] = "e0c,e0d"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],                # get version
        SRR['ifgrp_record_modify'],        # get
        SRR['empty_good'],                 # modify
        SRR['end_of_sequence']
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_modify_ifgrp_broadcast_domain(mock_request, patch_ansible):
    ''' modify broadcast domain and ipspace'''
    args = dict(default_args())
    args['node'] = "mohan9cluster2-01"
    args['ports'] = "e0c,e0a"
    args['from_lag_ports'] = 'e0c'
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    args['broadcast_domain'] = "test1"
    args['ipspace'] = "Default"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['ifgrp_record'],        # get
        SRR['empty_good'],          # modify
        SRR['end_of_sequence']
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_delete_ifgrp(mock_request, patch_ansible):
    ''' test delete LAG'''
    args = dict(default_args())
    args['node'] = "mohan9cluster2-01"
    args['ports'] = "e0c,e0a"
    args['distribution_function'] = "ip"
    args['mode'] = "multimode_lacp"
    args['broadcast_domain'] = "test1"
    args['ipspace'] = "ip1"
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['ifgrp_record'],        # get
        SRR['empty_good'],          # delete
        SRR['end_of_sequence']
    ]
    my_obj = ifgrp_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS
