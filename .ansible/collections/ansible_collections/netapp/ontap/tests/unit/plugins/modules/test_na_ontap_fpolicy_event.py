''' unit tests ONTAP Ansible module: na_ontap_fpolicy_event '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_event \
    import NetAppOntapFpolicyEvent as fpolicy_event_module  # module under test


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {"num_records": 0}, None),
    'end_of_sequence': (500, None, "Ooops, the UT needs one more SRR response"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'fpolicy_event_record': (200, {
        "num_records": 1,
        "records": [{
            'svm': {'uuid': '3b21372b-64ae-11eb-8c0e-0050568176ec'},
            'name': 'my_event2',
            'volume_monitoring': False
        }]
    }, None),
    'vserver_uuid_record': (200, {
        'records': [{
            'uuid': '3b21372b-64ae-11eb-8c0e-0050568176ec'
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
        if self.type == 'fpolicy_event':
            xml = self.build_fpolicy_event_info()
        elif self.type == 'fpolicy_event_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_fpolicy_event_info():
        ''' build xml data for fpolicy-policy-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes-list': {
                'fpolicy-event-options-config': {
                    "event-name": "my_event2",
                    "vserver": "svm1",
                    'volume-operation': "false"
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
            vserver = 'svm1'
            name = 'my_event2'
            volume_monitoring = False

        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'svm1'
            name = 'my_event2'
            volume_monitoring = False

        args = dict({
            'state': 'present',
            'hostname': hostname,
            'username': username,
            'password': password,
            'vserver': vserver,
            'name': name,
            'volume_monitoring': volume_monitoring
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_fpolicy_event_mock_object(cx_type='zapi', kind=None):
        fpolicy_event_obj = fpolicy_event_module()
        if cx_type == 'zapi':
            if kind is None:
                fpolicy_event_obj.server = MockONTAPConnection()
            else:
                fpolicy_event_obj.server = MockONTAPConnection(kind=kind)
        return fpolicy_event_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            fpolicy_event_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_fpolicy_event for non-existent config'''
        set_module_args(self.set_default_args(use_rest='Never'))
        print('starting')
        my_obj = fpolicy_event_module()
        print('use_rest:', my_obj.use_rest)
        my_obj.server = self.server
        assert my_obj.get_fpolicy_event is not None

    def test_ensure_get_called_existing(self):
        ''' test get_fpolicy_event_config for existing config'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = fpolicy_event_module()
        my_obj.server = MockONTAPConnection(kind='fpolicy_event')
        assert my_obj.get_fpolicy_event()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_event.NetAppOntapFpolicyEvent.create_fpolicy_event')
    def test_successful_create(self, create_fpolicy_event):
        ''' creating fpolicy_event and test idempotency '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = fpolicy_event_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        create_fpolicy_event.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = fpolicy_event_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('fpolicy_event')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_event.NetAppOntapFpolicyEvent.delete_fpolicy_event')
    def test_successful_delete(self, delete_fpolicy_event):
        ''' delete fpolicy_event and test idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = fpolicy_event_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('fpolicy_event')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = fpolicy_event_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_event.NetAppOntapFpolicyEvent.modify_fpolicy_event')
    def test_successful_modify(self, modify_fpolicy_event):
        ''' modifying fpolicy_event config and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['volume_monitoring'] = True
        set_module_args(data)
        my_obj = fpolicy_event_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('fpolicy_event')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # to reset na_helper from remembering the previous 'changed' value
        data['volume_monitoring'] = False
        set_module_args(data)
        my_obj = fpolicy_event_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('fpolicy_event')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = fpolicy_event_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('fpolicy_event_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_fpolicy_event()
        assert 'Error creating fPolicy policy event ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.delete_fpolicy_event()
        assert 'Error deleting fPolicy policy event ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_fpolicy_event(modify={})
        assert 'Error modifying fPolicy policy event ' in exc.value.args[0]['msg']

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
            self.get_fpolicy_event_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_create_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['vserver_uuid_record'],
            SRR['empty_good'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_event_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_create_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['vserver_uuid_record'],
            SRR['fpolicy_event_record'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_event_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_delete_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['vserver_uuid_record'],
            SRR['fpolicy_event_record'],  # get
            SRR['empty_good'],  # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_event_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_delete_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['vserver_uuid_record'],
            SRR['empty_good'],  # get
            SRR['empty_good'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_event_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['volume_monitoring'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['vserver_uuid_record'],
            SRR['fpolicy_event_record'],  # get
            SRR['empty_good'],  # no response for modify
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_event_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['volume_monitoring'] = False
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['vserver_uuid_record'],
            SRR['fpolicy_event_record'],  # get
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_event_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']
