# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer \
    import NetAppONTAPVserverPeer as vserver_peer, main as uut_main  # module under test

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
        self.kind = kind
        self.data = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.kind == 'vserver_peer':
            xml = self.build_vserver_peer_info(self.data)
        if self.kind == 'cluster':
            xml = self.build_cluster_info(self.data)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_vserver_peer_info(vserver):
        ''' build xml data for vserser-peer-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'vserver-peer-info': {
                    'remote-vserver-name': vserver['peer_vserver'],
                    'vserver': vserver['vserver'],
                    'peer-vserver': vserver['peer_vserver'],
                    'peer-state': 'peered'
                }
            }
        }
        xml.translate_struct(attributes)
        print(xml.to_string())
        return xml

    @staticmethod
    def build_cluster_info(vserver):
        ''' build xml data for cluster-identity-get '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'attributes': {
                'cluster-identity-info': {
                    'cluster-name': vserver['peer_cluster']
                }
            }
        }
        xml.translate_struct(attributes)
        print(xml.to_string())
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_vserver_peer = {
            'vserver': 'test',
            'peer_vserver': 'test_peer',
            'peer_cluster': 'test_cluster_peer',
            'local_name_for_peer': 'peer_name',
            'local_name_for_source': 'source_name',
            'applications': ['snapmirror'],
            'hostname': 'hostname',
            'dest_hostname': 'hostname',
            'username': 'username',
            'password': 'password',

        }

    def get_vserver_peer_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_vserver_peer object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_vserver_peer object
        """
        vserver_peer_obj = vserver_peer()
        vserver_peer_obj.asup_log_for_cserver = Mock(return_value=None)
        if kind is None:
            vserver_peer_obj.server = MockONTAPConnection()
            vserver_peer_obj.dest_server = MockONTAPConnection()
        else:
            vserver_peer_obj.server = MockONTAPConnection(kind=kind, data=self.mock_vserver_peer)
            vserver_peer_obj.dest_server = MockONTAPConnection(kind=kind, data=self.mock_vserver_peer)
        return vserver_peer_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_obj = vserver_peer()
        print('Info: %s' % exc.value.args[0]['msg'])

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer.NetAppONTAPVserverPeer.vserver_peer_get')
    def test_successful_create(self, vserver_peer_get):
        ''' Test successful create '''
        data = self.mock_vserver_peer
        data['dest_hostname'] = 'test_destination'
        set_module_args(self.mock_vserver_peer)
        vserver_peer_get.return_value = None

        self.get_vserver_peer_mock_object().vserver_peer_create()
        current = {
            'vserver': 'test',
            'peer_vserver': self.mock_vserver_peer['peer_vserver'],
            'local_peer_vserver': self.mock_vserver_peer['peer_vserver'],
            'peer_cluster': self.mock_vserver_peer['peer_cluster']
        }
        vserver_peer_get.return_value = current
        self.get_vserver_peer_mock_object().vserver_peer_accept()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer.NetAppONTAPVserverPeer.vserver_peer_get')
    def test_successful_create_new_style(self, vserver_peer_get):
        ''' Test successful create '''
        data = dict(self.mock_vserver_peer)
        data.pop('dest_hostname')
        data['peer_options'] = dict(hostname='test_destination')
        set_module_args(data)

        current = {
            'vserver': 'test',
            'peer_vserver': self.mock_vserver_peer['peer_vserver'],
            'local_peer_vserver': self.mock_vserver_peer['peer_vserver'],
            'peer_cluster': self.mock_vserver_peer['peer_cluster']
        }
        vserver_peer_get.side_effect = [None, current]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_peer_mock_object('vserver_peer').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer.NetAppONTAPVserverPeer.vserver_peer_get')
    def test_create_idempotency(self, vserver_peer_get):
        ''' Test create idempotency '''
        data = self.mock_vserver_peer
        data['dest_hostname'] = 'test_destination'
        set_module_args(self.mock_vserver_peer)
        current = {
            'vserver': 'test',
            'peer_vserver': self.mock_vserver_peer['peer_vserver'],
            'peer_cluster': self.mock_vserver_peer['peer_cluster']
        }
        vserver_peer_get.return_value = current
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_peer_mock_object('vserver_peer').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer.NetAppONTAPVserverPeer.vserver_peer_get')
    def test_successful_delete(self, vserver_peer_get):
        ''' Test successful delete peer '''
        data = self.mock_vserver_peer
        data['state'] = 'absent'
        set_module_args(data)
        current = {
            'vserver': 'test',
            'peer_vserver': self.mock_vserver_peer['peer_vserver'],
            'peer_cluster': self.mock_vserver_peer['peer_cluster'],
            'local_peer_vserver': self.mock_vserver_peer['local_name_for_peer']
        }
        vserver_peer_get.return_value = current
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_peer_mock_object('vserver_peer').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer.NetAppONTAPVserverPeer.vserver_peer_get')
    def test_delete_idempotency(self, vserver_peer_get):
        ''' Test delete idempotency '''
        data = self.mock_vserver_peer
        data['state'] = 'absent'
        set_module_args(data)
        vserver_peer_get.return_value = None
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_peer_mock_object().apply()
        assert not exc.value.args[0]['changed']

    def test_helper_vserver_peer_get_iter(self):
        ''' Test vserver_peer_get_iter method '''
        set_module_args(self.mock_vserver_peer)
        obj = self.get_vserver_peer_mock_object('vserver_peer')
        result = obj.vserver_peer_get_iter('source')
        print(result.to_string(pretty=True))
        assert result['query'] is not None
        assert result['query']['vserver-peer-info'] is not None
        info = result['query']['vserver-peer-info']
        assert info['vserver'] == self.mock_vserver_peer['vserver']
        assert info['remote-vserver-name'] == self.mock_vserver_peer['peer_vserver']

    def test_get_packet(self):
        ''' Test vserver_peer_get method '''
        set_module_args(self.mock_vserver_peer)
        obj = self.get_vserver_peer_mock_object('vserver_peer')
        result = obj.vserver_peer_get()
        assert 'vserver' in result.keys()
        assert 'peer_vserver' in result.keys()
        assert 'peer_state' in result.keys()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer.NetAppONTAPVserverPeer.vserver_peer_get')
    def test_error_on_missing_params_create(self, vserver_peer_get):
        ''' Test error thrown from vserver_peer_create '''
        data = self.mock_vserver_peer
        del data['applications']
        set_module_args(data)
        vserver_peer_get.return_value = None
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_vserver_peer_mock_object().apply()
        assert exc.value.args[0]['msg'] == "applications parameter is missing"

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer.NetAppONTAPVserverPeer.get_peer_cluster_name')
    def test_get_peer_cluster_called(self, cluster_peer_get):
        ''' Test get_peer_cluster_name called if peer_cluster is missing '''
        data = self.mock_vserver_peer
        del data['peer_cluster']
        set_module_args(data)
        cluster_peer_get.return_value = 'something'
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_peer_mock_object().apply()
        assert cluster_peer_get.call_count == 1

    def test_get_peer_cluster_packet(self):
        ''' Test get_peer_cluster_name xml packet '''
        data = self.mock_vserver_peer
        set_module_args(data)
        obj = self.get_vserver_peer_mock_object('cluster')
        result = obj.get_peer_cluster_name()
        assert result == data['peer_cluster']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer.NetAppONTAPVserverPeer.vserver_peer_get')
    def test_error_on_missing_params_create(self, vserver_peer_get):
        ''' Test error thrown from vserver_peer_create '''
        data = dict(self.mock_vserver_peer)
        data.pop('dest_hostname')
        set_module_args(data)
        current = {
            'vserver': 'test',
            'peer_vserver': self.mock_vserver_peer['peer_vserver'],
            'local_peer_vserver': self.mock_vserver_peer['peer_vserver'],
            'peer_cluster': self.mock_vserver_peer['peer_cluster']
        }
        vserver_peer_get.side_effect = [None, current]

        with pytest.raises(AnsibleFailJson) as exc:
            self.get_vserver_peer_mock_object().apply()
        msg = "dest_hostname is required for peering a vserver in remote cluster"
        assert exc.value.args[0]['msg'] == msg

    def test_error_on_first_ZAPI_call(self):
        ''' Test error thrown from vserver_peer_get '''
        data = dict(self.mock_vserver_peer)
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            uut_main()
        msg = "Error fetching vserver peer"
        assert msg in exc.value.args[0]['msg']

    def test_error_create_new_style(self):
        ''' Test error in create - peer not visible '''
        data = dict(self.mock_vserver_peer)
        data.pop('dest_hostname')
        data['peer_options'] = dict(hostname='test_destination')
        set_module_args(data)

        current = {
            'vserver': 'test',
            'peer_vserver': self.mock_vserver_peer['peer_vserver'],
            'local_peer_vserver': self.mock_vserver_peer['peer_vserver'],
            'peer_cluster': self.mock_vserver_peer['peer_cluster']
        }
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_vserver_peer_mock_object().apply()
        msg = 'Error retrieving vserver peer information while accepting'
        assert msg in exc.value.args[0]['msg']


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


WARNINGS = []


def warn(dummy, msg):
    WARNINGS.append(msg)


def default_args():
    return {
        "hostname": "10.193.177.97",
        "username": "admin",
        "password": "netapp123",
        "https": "yes",
        "validate_certs": "no",
        "use_rest": "always",
        "state": "present",
        "dest_hostname": "0.0.0.0"
    }


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'src_use_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'dst_use_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_6': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, {
        "records": [{
            "vserver": "svmsrc1",
            "peer_vserver": "svmdst1",
            "peer_state": "peered",
            "local_peer_vserver_uuid": "545d2562-2fca-11ec-8016-005056b3f5d5"
        }],
        "num_records": 1,
    }, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'server_record': (200, {
        "records": [{
            "vserver": "svmsrc1",
            "peer_vserver": "svmdst1",
            "state": "peered",
            "local_peer_vserver_uuid": "545d2562-2fca-11ec-8016-005056b3f5d5"
        }],
        'num_records': 1
    }, None),

    'create_server': (200, {
        'job': {
            'uuid': 'fde79888-692a-11ea-80c2-005056b39fe7',
            '_links': {
                'self': {
                    'href': '/api/cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7'}}}
    }, None),
    'job': (200, {
        "uuid": "fde79888-692a-11ea-80c2-005056b39fe7",
        "state": "success",
        "start_time": "2020-02-26T10:35:44-08:00",
        "end_time": "2020-02-26T10:47:38-08:00",
        "_links": {
            "self": {
                "href": "/api/cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7"
            }
        }
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
    args = dict(default_args())
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args(args)
        my_obj = vserver_peer()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'missing required arguments:'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_when_required_applications_args_missing(mock_request, patch_ansible):
    args = dict(default_args())
    args['vserver'] = 'svmsrc3'
    args['peer_vserver'] = 'svmdst3'
    args['state'] = 'present'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['src_use_rest'],
        SRR['dst_use_rest'],
        SRR['zero_record'],
        SRR['create_server'],       # create
        SRR['job'],
        SRR['end_of_sequence']
    ]
    my_obj = vserver_peer()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'applications parameter is missing'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_get_server_called(mock_request, patch_ansible):
    args = dict(default_args())
    args['vserver'] = 'svmsrc3'
    args['peer_vserver'] = 'svmdst3'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['src_use_rest'],
        SRR['dst_use_rest'],
        SRR['one_record_uuid'],       # get
        SRR['end_of_sequence']
    ]
    my_obj = vserver_peer()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_create_server_called(mock_request, patch_ansible):
    args = dict(default_args())
    args['vserver'] = 'svmsrc3'
    args['peer_vserver'] = 'svmdst3'
    args['applications'] = ['snapmirror']
    args['state'] = 'present'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['src_use_rest'],
        SRR['dst_use_rest'],
        SRR['zero_record'],
        SRR['create_server'],       # create
        SRR['job'],
        SRR['end_of_sequence']
    ]
    my_obj = vserver_peer()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_server_called(mock_request, patch_ansible):
    args = dict(default_args())
    args['vserver'] = 'svmsrc3'
    args['peer_vserver'] = 'svmdst3'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['src_use_rest'],
        SRR['dst_use_rest'],
        SRR['server_record'],
        SRR['empty_good'],       # delete
        SRR['end_of_sequence']
    ]
    my_obj = vserver_peer()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS
