# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_cluster '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster \
    import NetAppONTAPCluster as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


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

    def __init__(self, kind=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'cluster':
            xml = self.build_cluster_info()
        if self.type == 'cluster_success':
            xml = self.build_cluster_info_success()
        elif self.type == 'cluster_add':
            xml = self.build_add_node_info()
        elif self.type == 'cluster_extra_input':
            self.type = 'cluster'   # success on second call
            raise netapp_utils.zapi.NaApiError(code='TEST1', message="Extra input: single-node-cluster")
        elif self.type == 'cluster_extra_input_loop':
            raise netapp_utils.zapi.NaApiError(code='TEST2', message="Extra input: single-node-cluster")
        elif self.type == 'cluster_extra_input_other':
            raise netapp_utils.zapi.NaApiError(code='TEST3', message="Extra input: other-unexpected-element")
        elif self.type == 'cluster_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST4', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    def autosupport_log(self):
        ''' mock autosupport log'''
        return None

    @staticmethod
    def build_cluster_info():
        ''' build xml data for cluster-create-join-progress-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'attributes': {
                'cluster-create-join-progress-info': {
                    'is-complete': 'true',
                    'status': 'whatever'
                }
            }
        }
        xml.translate_struct(attributes)
        return xml

    @staticmethod
    def build_cluster_info_success():
        ''' build xml data for cluster-create-join-progress-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'attributes': {
                'cluster-create-join-progress-info': {
                    'is-complete': 'false',
                    'status': 'success'
                }
            }
        }
        xml.translate_struct(attributes)
        return xml

    @staticmethod
    def build_add_node_info():
        ''' build xml data for cluster-create-add-node-status-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'attributes-list': {
                'cluster-create-add-node-status-info': {
                    'failure-msg': '',
                    'status': 'success'
                }
            }
        }
        xml.translate_struct(attributes)
        return xml


# using pytest natively, without unittest.TestCase
@pytest.fixture
def patch_ansible():
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json) as mocks:
        yield mocks


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.server = MockONTAPConnection()
        self.use_vsim = False

    def set_default_args(self, use_rest='never'):
        hostname = '10.10.10.10'
        username = 'admin'
        password = 'password'
        cluster_name = 'abc'
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'cluster_name': cluster_name,
            'use_rest': use_rest
        })

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    @patch('time.sleep')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    def test_ensure_apply_for_cluster_called(self, get_cl_id, sleep_mock):
        ''' creating cluster and checking idempotency '''
        get_cl_id.return_value = None
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    @patch('time.sleep')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.create_cluster')
    def test_cluster_create_called(self, cluster_create, get_cl_id, sleep_mock):
        ''' creating cluster'''
        get_cl_id.return_value = None
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_success')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        cluster_create.assert_called_with()

    @patch('time.sleep')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    def test_cluster_create_old_api(self, get_cl_id, sleep_mock):
        ''' creating cluster'''
        get_cl_id.return_value = None
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_extra_input')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    def test_cluster_create_old_api_loop(self, get_cl_id):
        ''' creating cluster'''
        get_cl_id.return_value = None
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_extra_input_loop')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = 'TEST2:Extra input: single-node-cluster'
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    def test_cluster_create_old_api_other_extra(self, get_cl_id):
        ''' creating cluster'''
        get_cl_id.return_value = None
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_extra_input_other')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = 'TEST3:Extra input: other-unexpected-element'
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        assert msg in exc.value.args[0]['msg']

    @patch('time.sleep')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_ip_addresses')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.add_node')
    def test_add_node_called(self, add_node, get_cl_id, get_cl_ips, sleep_mock):
        ''' creating add_node'''
        get_cl_ips.return_value = []
        get_cl_id.return_value = None
        data = self.set_default_args()
        del data['cluster_name']
        data['cluster_ip_address'] = '10.10.10.10'
        set_module_args(data)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_add')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        add_node.assert_called_with()
        assert exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_cluster()
        assert 'Error creating cluster' in exc.value.args[0]['msg']
        data = self.set_default_args()
        data['cluster_ip_address'] = '10.10.10.10'
        set_module_args(data)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.add_node()
        assert 'Error adding node with ip' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_ip_addresses')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.add_node')
    def test_add_node_idempotent(self, add_node, get_cl_id, get_cl_ips):
        ''' creating add_node'''
        get_cl_ips.return_value = ['10.10.10.10']
        get_cl_id.return_value = None
        data = self.set_default_args()
        del data['cluster_name']
        data['cluster_ip_address'] = '10.10.10.10'
        set_module_args(data)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_add')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        try:
            add_node.assert_not_called()
        except AttributeError:
            # not supported with python <= 3.4
            pass
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_ip_addresses')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.remove_node')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.node_remove_wait')
    def test_remove_node_ip(self, wait, remove_node, get_cl_id, get_cl_ips):
        ''' creating add_node'''
        get_cl_ips.return_value = ['10.10.10.10']
        get_cl_id.return_value = None
        wait.return_value = None
        data = self.set_default_args()
        # del data['cluster_name']
        data['cluster_ip_address'] = '10.10.10.10'
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_add')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        remove_node.assert_called_with()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_ip_addresses')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.remove_node')
    def test_remove_node_ip_idempotent(self, remove_node, get_cl_id, get_cl_ips):
        ''' creating add_node'''
        get_cl_ips.return_value = []
        get_cl_id.return_value = None
        data = self.set_default_args()
        # del data['cluster_name']
        data['cluster_ip_address'] = '10.10.10.10'
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_add')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        try:
            remove_node.assert_not_called()
        except AttributeError:
            # not supported with python <= 3.4
            pass
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_nodes')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.remove_node')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.node_remove_wait')
    def test_remove_node_name(self, wait, remove_node, get_cl_id, get_cl_nodes):
        ''' creating add_node'''
        get_cl_nodes.return_value = ['node1', 'node2']
        get_cl_id.return_value = None
        wait.return_value = None
        data = self.set_default_args()
        # del data['cluster_name']
        data['node_name'] = 'node2'
        data['state'] = 'absent'
        data['force'] = True
        set_module_args(data)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_add')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        remove_node.assert_called_with()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_nodes')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.get_cluster_identity')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster.NetAppONTAPCluster.remove_node')
    def test_remove_node_name_idempotent(self, remove_node, get_cl_id, get_cl_nodes):
        ''' creating add_node'''
        get_cl_nodes.return_value = ['node1', 'node2']
        get_cl_id.return_value = None
        data = self.set_default_args()
        # del data['cluster_name']
        data['node_name'] = 'node3'
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = my_module()
        my_obj.autosupport_log = Mock(return_value=None)
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cluster_add')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cluster_apply: %s' % repr(exc.value))
        try:
            remove_node.assert_not_called()
        except AttributeError:
            # not supported with python <= 3.4
            pass
        assert not exc.value.args[0]['changed']

    def test_remove_node_name_and_id(self):
        ''' creating add_node'''
        data = self.set_default_args()
        # del data['cluster_name']
        data['cluster_ip_address'] = '10.10.10.10'
        data['node_name'] = 'node3'
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            my_module()
        print('Info: test_remove_node_name_and_id: %s' % repr(exc.value))
        msg = 'when state is "absent", parameters are mutually exclusive: cluster_ip_address|node_name'
        assert msg in exc.value.args[0]['msg']


SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy_9_7_0')), None),
    'is_rest_95': (200, dict(version=dict(generation=9, major=5, minor=0, full='dummy_9_5_0')), None),
    'is_rest_96': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy_9_6_0')), None),
    'is_rest_97': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy_9_7_0')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': ({}, None, None),
    'zero_record': (200, {'records': []}, None),
    'precluster': (500, None, {'message': 'are available in precluster.'}),
    'cluster_identity': (200, {'location': 'Oz', 'name': 'abc'}, None),
    'nodes': (200, {'records': [
        {'name': 'node2', 'uuid': 'uuid2', 'cluster_interfaces': [{'ip': {'address': '10.10.10.2'}}]}
    ]}, None),
    'end_of_sequence': (None, None, "Unexpected call to send_request"),
    'generic_error': (None, "Expected error"),
}


def set_default_args(use_rest='auto'):
    hostname = '10.10.10.10'
    username = 'admin'
    password = 'password'
    cluster_name = 'abc'
    return dict({
        'hostname': hostname,
        'username': username,
        'password': password,
        'cluster_name': cluster_name,
        'use_rest': use_rest
    })


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['precluster'],      # get
        SRR['empty_good'],      # post
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create_single(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args())
    args['single_node_cluster'] = True
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['precluster'],      # get
        SRR['empty_good'],      # post
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3
    post_call = call('POST', 'cluster', {'return_timeout': 30, 'single_node_cluster': True}, json={'name': 'abc'}, headers=None)
    assert post_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_modify(mock_request, patch_ansible):
    ''' modify cluster location '''
    args = dict(set_default_args())
    args['cluster_location'] = 'Mars'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['cluster_identity'],        # get
        SRR['empty_good'],              # post
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_modify_idempotent(mock_request, patch_ansible):
    ''' modify cluster location '''
    args = dict(set_default_args())
    args['cluster_location'] = 'Oz'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['cluster_identity'],        # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is False
    assert len(mock_request.mock_calls) == 2


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_add_node(mock_request, patch_ansible):
    ''' modify cluster location '''
    args = dict(set_default_args())
    args['node_name'] = 'node2'
    args['cluster_ip_address'] = '10.10.10.2'

    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['cluster_identity'],        # get
        SRR['zero_record'],             # get nodes
        SRR['empty_good'],              # post
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_remove_node_by_ip(mock_request, patch_ansible):
    ''' modify cluster location '''
    args = dict(set_default_args())
    # args['node_name'] = 'node2'
    args['cluster_ip_address'] = '10.10.10.2'
    args['state'] = 'absent'

    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['cluster_identity'],        # get
        SRR['nodes'],                   # get nodes
        SRR['empty_good'],              # post
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_remove_node_by_ip_idem(mock_request, patch_ansible):
    ''' modify cluster location '''
    args = dict(set_default_args())
    # args['node_name'] = 'node2'
    args['cluster_ip_address'] = '10.10.10.3'
    args['state'] = 'absent'

    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['cluster_identity'],        # get
        SRR['nodes'],                   # get nodes
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is False
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_remove_node_by_name(mock_request, patch_ansible):
    ''' modify cluster location '''
    args = dict(set_default_args())
    args['node_name'] = 'node2'
    # args['cluster_ip_address'] = '10.10.10.2'
    args['state'] = 'absent'
    args['force'] = True

    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['cluster_identity'],        # get
        SRR['nodes'],                   # get nodes
        SRR['empty_good'],              # post
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_remove_node_by_name_idem(mock_request, patch_ansible):
    ''' modify cluster location '''
    args = dict(set_default_args())
    args['node_name'] = 'node3'
    # args['cluster_ip_address'] = '10.10.10.2'
    args['state'] = 'absent'

    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['cluster_identity'],        # get
        SRR['nodes'],                   # get nodes
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is False
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_remove_node_by_name_rest_96(mock_request, patch_ansible):
    ''' revert to ZAPI for 9.6 '''
    args = dict(set_default_args())
    args['node_name'] = 'node3'
    # args['cluster_ip_address'] = '10.10.10.2'
    args['state'] = 'absent'

    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_96'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    # revert to ZAPI for 9.6
    assert not my_obj.use_rest
