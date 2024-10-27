''' unit tests ONTAP Ansible module: na_ontap_log_forward '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_log_forward \
    import NetAppOntapLogForward as log_forward_module  # module under test


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Ooops, the UT needs one more SRR response"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'log_forward_record': (200, {
        "records": [{
            "address": "10.11.12.13",
            "facility": "user",
            "port": 514,
            "protocol": "udp_unencrypted",
            "verify_server": False
        }]
    }, None)
}


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
        if self.type == 'log_forward':
            xml = self.build_log_forward_info()
        elif self.type == 'log_forward_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_log_forward_info():
        ''' build xml data for cluster-log-forward-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes': {
                'cluster-log-forward-info': {
                    'destination': '10.11.12.13',
                    'facility': 'user',
                    'port': '514',
                    'protocol': 'udp_unencrypted',
                    'verify-server': 'false'
                }
            }
        }

        xml.translate_struct(data)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.server = MockONTAPConnection()
        self.onbox = False

    def set_default_args(self, use_rest=None):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            destination = '10.11.12.13'
            port = 514
            facility = 'user'
            force = True
            protocol = 'udp_unencrypted'
            verify_server = False
        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            destination = '10.11.12.13'
            port = 514
            facility = 'user'
            force = True
            protocol = 'udp_unencrypted'
            verify_server = False

        args = dict({
            'state': 'present',
            'hostname': hostname,
            'username': username,
            'password': password,
            'destination': destination,
            'port': port,
            'facility': facility,
            'force': force,
            'protocol': protocol,
            'verify_server': verify_server
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_log_forward_mock_object(cx_type='zapi', kind=None):
        log_forward_obj = log_forward_module()
        if cx_type == 'zapi':
            if kind is None:
                log_forward_obj.server = MockONTAPConnection()
            else:
                log_forward_obj.server = MockONTAPConnection(kind=kind)
        return log_forward_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            log_forward_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_log_forward_config for non-existent config'''
        set_module_args(self.set_default_args(use_rest='Never'))
        print('starting')
        my_obj = log_forward_module()
        print('use_rest:', my_obj.use_rest)
        my_obj.server = self.server
        assert my_obj.get_log_forward_config is not None

    def test_ensure_get_called_existing(self):
        ''' test get_log_forward_config for existing config'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = log_forward_module()
        my_obj.server = MockONTAPConnection(kind='log_forward')
        assert my_obj.get_log_forward_config()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_log_forward.NetAppOntapLogForward.create_log_forward_config')
    def test_successful_create(self, create_log_forward_config):
        ''' creating log_forward config and testing idempotency '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = log_forward_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        create_log_forward_config.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = log_forward_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('log_forward')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_log_forward.NetAppOntapLogForward.destroy_log_forward_config')
    def test_successful_delete(self, destroy_log_forward):
        ''' deleting log_forward config and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = log_forward_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('log_forward')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # destroy_log_forward_config.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = log_forward_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_log_forward.NetAppOntapLogForward.modify_log_forward_config')
    def test_successful_modify(self, modify_log_forward_config):
        ''' modifying log_forward config and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['facility'] = 'kern'
        set_module_args(data)
        my_obj = log_forward_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('log_forward')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']

        # modify_log_forward_config.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        data['facility'] = 'user'
        set_module_args(data)
        my_obj = log_forward_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('log_forward')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = log_forward_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('log_forward_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_log_forward_config()
        assert 'Error creating log forward config with destination ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.destroy_log_forward_config()
        assert 'Error destroying log forward destination ' in exc.value.args[0]['msg']

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
            self.get_log_forward_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_create_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # get
            SRR['empty_good'],  # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_log_forward_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_create_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['log_forward_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_log_forward_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_delete_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['log_forward_record'],  # get
            SRR['empty_good'],  # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_log_forward_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_delete_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_log_forward_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['facility'] = 'kern'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['log_forward_record'],  # get
            SRR['empty_good'],  # delete
            SRR['empty_good'],  # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_log_forward_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['log_forward_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_log_forward_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']
