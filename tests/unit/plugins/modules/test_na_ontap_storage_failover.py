''' unit tests ONTAP Ansible module: na_ontap_storage_failover '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_storage_failover \
    import NetAppOntapStorageFailover as storage_failover_module  # module under test


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'no_records': (200, {'records': []}, None),
    'end_of_sequence': (500, None, "Ooops, the UT needs one more SRR response"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'storage_failover_enabled_record': (200, {
        'num_records': 1,
        'records': [{
            'name': 'node1',
            'uuid': '56ab5d21-312a-11e8-9166-9d4fc452db4e',
            'ha': {
                'enabled': True
            }
        }]
    }, None),
    'storage_failover_disabled_record': (200, {
        'num_records': 1,
        "records": [{
            'name': 'node1',
            'uuid': '56ab5d21-312a-11e8-9166-9d4fc452db4e',
            'ha': {
                'enabled': False
            }
        }]
    }, None),
    'no_ha_record': (200, {
        'num_records': 1,
        "records": [{
            'name': 'node1',
            'uuid': '56ab5d21-312a-11e8-9166-9d4fc452db4e',
        }]
    }, None)
}


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
        if self.type == 'storage_failover_enabled':
            xml = self.build_storage_failover_enabled_info()
        elif self.type == 'storage_failover_disabled':
            xml = self.build_storage_failover_disabled_info()
        elif self.type == 'storage_failover_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_storage_failover_enabled_info():
        ''' build xml data for cf-status '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'is-enabled': 'true'
        }

        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_storage_failover_disabled_info():
        ''' build xml data for cf-status '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'is-enabled': 'false'
        }

        xml.translate_struct(data)
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
        self.onbox = False

    def set_default_args(self, use_rest=None):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            node_name = 'node1'
        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            node_name = 'node1'

        args = dict({
            'state': 'present',
            'hostname': hostname,
            'username': username,
            'password': password,
            'node_name': node_name
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_storage_failover_mock_object(cx_type='zapi', kind=None):
        storage_failover_obj = storage_failover_module()
        if cx_type == 'zapi':
            if kind is None:
                storage_failover_obj.server = MockONTAPConnection()
            else:
                storage_failover_obj.server = MockONTAPConnection(kind=kind)
        return storage_failover_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            storage_failover_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called_existing(self):
        ''' test get_storage_failover for existing config '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = storage_failover_module()
        my_obj.server = MockONTAPConnection(kind='storage_failover_enabled')
        assert my_obj.get_storage_failover()

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_storage_failover.NetAppOntapStorageFailover.modify_storage_failover')
    def test_successful_enable(self, modify_storage_failover, mock_ems):
        ''' enable storage_failover and testing idempotency '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = storage_failover_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('storage_failover_disabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        modify_storage_failover.assert_called_with({'is_enabled': False})
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = storage_failover_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('storage_failover_enabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_storage_failover.NetAppOntapStorageFailover.modify_storage_failover')
    def test_successful_disable(self, modify_storage_failover, mock_ems):
        ''' disable storage_failover and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = storage_failover_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('storage_failover_enabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        modify_storage_failover.assert_called_with({'is_enabled': True})
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = storage_failover_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('storage_failover_disabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = storage_failover_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('storage_failover_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_storage_failover(self.get_storage_failover_mock_object())
        assert 'Error modifying storage failover' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
    def test_negative_no_netapp_lib(self, mock_request):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        mock_request.return_value = False
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_storage_failover_mock_object(cx_type='rest').apply()
        assert 'Error: the python NetApp-Lib module is required.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_storage_failover_mock_object(cx_type='rest').apply()
        assert SRR['generic_error'][2] in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_enabled_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['storage_failover_disabled_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_storage_failover_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_enabled_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['storage_failover_enabled_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_storage_failover_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_disabled_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['storage_failover_enabled_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_storage_failover_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_disabled_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['storage_failover_disabled_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_storage_failover_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_no_ha_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_ha_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_storage_failover_mock_object(cx_type='rest').apply()
        assert 'HA is not available on node: node1' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_node_not_found_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_records'],
            SRR['storage_failover_disabled_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_storage_failover_mock_object(cx_type='rest').apply()
        assert 'REST API did not return failover details for node' in exc.value.args[0]['msg']
        assert 'current nodes: node1' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_node_not_found_rest_no_names(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_records'],
            SRR['no_records'],  # get  all nodes
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_storage_failover_mock_object(cx_type='rest').apply()
        assert 'REST API did not return failover details for node' in exc.value.args[0]['msg']
        assert 'current nodes: node1' not in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_node_not_found_rest_error_on_get_nodes(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_records'],
            SRR['generic_error'],  # get all nodes
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_storage_failover_mock_object(cx_type='rest').apply()
        assert 'REST API did not return failover details for node' in exc.value.args[0]['msg']
        assert 'current nodes: node1' not in exc.value.args[0]['msg']
        assert 'failed to get list of nodes' in exc.value.args[0]['msg']
