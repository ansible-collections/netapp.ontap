# (c) 2018-2021, NetApp, Inc
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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_port \
    import NetAppOntapNetPort as port_module  # module under test

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
        self.type = kind
        self.data = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        if self.type == 'raise':
            raise netapp_utils.zapi.NaApiError(code='1111', message='forcing an error')
        self.xml_in = xml
        if self.type == 'port':
            xml = self.build_port_info(self.data)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_port_info(port_details):
        ''' build xml data for net-port-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'net-port-info': {
                    # 'port': port_details['port'],
                    'mtu': str(port_details['mtu']),
                    'is-administrative-auto-negotiate': 'true',
                    'is-administrative-up': str(port_details['up_admin']).lower(),      # ZAPI uses 'true', 'false'
                    'ipspace': 'default',
                    'administrative-flowcontrol': port_details['flowcontrol_admin'],
                    'node': port_details['node']
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
        self.server = MockONTAPConnection()
        self.mock_port = {
            'node': 'test',
            'ports': 'a1',
            'up_admin': True,
            'flowcontrol_admin': 'something',
            'mtu': 1000
        }

    def mock_args(self):
        return {
            'node': self.mock_port['node'],
            'flowcontrol_admin': self.mock_port['flowcontrol_admin'],
            'ports': [self.mock_port['ports']],
            'mtu': self.mock_port['mtu'],
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_port_mock_object(self, kind=None, data=None):
        """
        Helper method to return an na_ontap_net_port object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_net_port object
        """
        obj = port_module()
        obj.autosupport_log = Mock(return_value=None)
        if data is None:
            data = self.mock_port
        obj.server = MockONTAPConnection(kind=kind, data=data)
        return obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            port_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_nonexistent_port(self):
        ''' Test if get_net_port returns None for non-existent port '''
        set_module_args(self.mock_args())
        result = self.get_port_mock_object().get_net_port('test')
        assert result is None

    def test_get_existing_port(self):
        ''' Test if get_net_port returns details for existing port '''
        set_module_args(self.mock_args())
        result = self.get_port_mock_object('port').get_net_port('test')
        assert result['mtu'] == self.mock_port['mtu']
        assert result['flowcontrol_admin'] == self.mock_port['flowcontrol_admin']
        assert result['up_admin'] == self.mock_port['up_admin']

    def test_successful_modify(self):
        ''' Test modify_net_port '''
        data = self.mock_args()
        data['mtu'] = '2000'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object('port').apply()
        assert exc.value.args[0]['changed']

    def test_successful_modify_int(self):
        ''' Test modify_net_port '''
        data = self.mock_args()
        data['mtu'] = 2000
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object('port').apply()
        assert exc.value.args[0]['changed']
        print(exc.value.args[0]['modify'])

    def test_successful_modify_bool(self):
        ''' Test modify_net_port '''
        data = self.mock_args()
        data['up_admin'] = False
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object('port').apply()
        assert exc.value.args[0]['changed']
        print(exc.value.args[0]['modify'])

    def test_successful_modify_str(self):
        ''' Test modify_net_port '''
        data = self.mock_args()
        data['flowcontrol_admin'] = 'anything'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object('port').apply()
        assert exc.value.args[0]['changed']
        print(exc.value.args[0]['modify'])

    def test_successful_modify_multiple_ports(self):
        ''' Test modify_net_port '''
        data = self.mock_args()
        data['ports'] = ['a1', 'a2']
        data['mtu'] = '2000'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object('port').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_port.NetAppOntapNetPort.get_net_port')
    def test_get_called(self, get_port):
        ''' Test get_net_port '''
        data = self.mock_args()
        data['ports'] = ['a1', 'a2']
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_port_mock_object('port').apply()
        assert get_port.call_count == 2

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_port.NetAppOntapNetPort.get_net_port')
    def test_negative_not_found_1(self, get_port):
        ''' Test get_net_port '''
        data = self.mock_args()
        data['ports'] = ['a1']
        set_module_args(data)
        get_port.return_value = None
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_port_mock_object('port').apply()
        msg = 'Error: port: a1 not found on node: test - check node name.'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_port.NetAppOntapNetPort.get_net_port')
    def test_negative_not_found_2(self, get_port):
        ''' Test get_net_port '''
        data = self.mock_args()
        data['ports'] = ['a1', 'a2']
        set_module_args(data)
        get_port.return_value = None
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_port_mock_object('port').apply()
        msg = 'Error: ports: a1, a2 not found on node: test - check node name.'
        assert msg in exc.value.args[0]['msg']

    def test_negative_zapi_exception_in_get(self):
        ''' Test get_net_port '''
        data = self.mock_args()
        data['ports'] = ['a1', 'a2']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_port_mock_object('raise').get_net_port('a1')
        msg = 'Error getting net ports for test: NetApp API failed. Reason - 1111:forcing an error'
        assert msg in exc.value.args[0]['msg']

    def test_negative_zapi_exception_in_modify(self):
        ''' Test get_net_port '''
        data = self.mock_args()
        data['ports'] = ['a1', 'a2']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_port_mock_object('raise').modify_net_port('a1', dict())
        msg = 'Error modifying net ports for test: NetApp API failed. Reason - 1111:forcing an error'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
    def test_negative_no_netapp_lib(self, get_port):
        ''' Test get_net_port '''
        data = self.mock_args()
        set_module_args(data)
        get_port.return_value = False
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_port_mock_object('port').apply()
        msg = 'the python NetApp-Lib module is required'
        assert msg in exc.value.args[0]['msg']


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
    'vlan_record': (200, {
        "num_records": 1,
        "records": [{
            'broadcast_domain': {
                'ipspace': {'name': 'Default'},
                'name': 'test1'
            },
            'enabled': False,
            'name': 'e0c-15',
            'node': {'name': 'mohan9-vsim1'},
            'uuid': '97936a14-30de-11ec-ac4d-005056b3d8c8'
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
        port_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'missing required arguments:'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_unsupported_rest_properties(mock_request, patch_ansible):
    '''throw error if unsupported rest properties are set'''
    args = dict(default_args())
    args['node'] = "mohan9-vsim1"
    args['ports'] = "e0d,e0d-15"
    args['mtu'] = 1500
    args['duplex_admin'] = 'admin'
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args(args)
        port_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'REST API currently does not support'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_enable_port(mock_request, patch_ansible):
    ''' test enable vlan'''
    args = dict(default_args())
    args['node'] = "mohan9-vsim1"
    args['ports'] = "e0c-15"
    args['up_admin'] = True
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['vlan_record'],         # get
        SRR['empty_good'],          # delete
        SRR['end_of_sequence']
    ]
    my_obj = port_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS
