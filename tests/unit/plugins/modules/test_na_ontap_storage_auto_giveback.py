''' unit tests ONTAP Ansible module: na_ontap_storage_auto_giveback '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_storage_auto_giveback \
    import NetAppOntapStorageAutoGiveback as storage_auto_giveback_module  # module under test


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
    'storage_auto_giveback_enabled_record': (200, {
        'num_records': 1,
        'records': [{
            'node': 'node1',
            'auto_giveback': True,
            'auto_giveback_after_panic': True
        }]
    }, None),
    'storage_auto_giveback_disabled_record': (200, {
        'num_records': 1,
        "records": [{
            'node': 'node1',
            'auto_giveback': False,
            'auto_giveback_after_panic': False
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
        if self.type == 'auto_giveback_enabled':
            xml = self.build_storage_auto_giveback_enabled_info()
        elif self.type == 'auto_giveback_disabled':
            xml = self.build_storage_auto_giveback_disabled_info()
        elif self.type == 'auto_giveback_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_storage_auto_giveback_enabled_info():
        ''' build xml data for cf-get-iter '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'num-records': 1,
            'attributes-list': {
                'storage-failover-info': {
                    'sfo-node-info': {
                        'node-related-info': {
                            'node': 'node1'
                        }
                    },
                    'sfo-options-info': {
                        'options-related-info': {
                            'auto-giveback-enabled': 'true',
                            'sfo-giveback-options-info': {
                                'giveback-options': {
                                    'auto-giveback-after-panic-enabled': 'true'
                                }
                            }
                        }
                    }
                }
            }
        }

        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_storage_auto_giveback_disabled_info():
        ''' build xml data for cf-get-iter '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'num-records': 1,
            'attributes-list': {
                'storage-failover-info': {
                    'sfo-node-info': {
                        'node-related-info': {
                            'node': 'node1'
                        }
                    },
                    'sfo-options-info': {
                        'options-related-info': {
                            'auto-giveback-enabled': 'false',
                            'sfo-giveback-options-info': {
                                'giveback-options': {
                                    'auto-giveback-after-panic-enabled': 'false'
                                }
                            }
                        }
                    }
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
            name = 'node1'
            auto_giveback_enabled = True
            auto_giveback_after_panic_enabled = True
        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            name = 'node1'
            auto_giveback_enabled = True
            auto_giveback_after_panic_enabled = True

        args = dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'name': name,
            'auto_giveback_enabled': auto_giveback_enabled,
            'auto_giveback_after_panic_enabled': auto_giveback_after_panic_enabled
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_storage_auto_giveback_mock_object(cx_type='zapi', kind=None):
        storage_auto_giveback_obj = storage_auto_giveback_module()
        if cx_type == 'zapi':
            if kind is None:
                storage_auto_giveback_obj.server = MockONTAPConnection()
            else:
                storage_auto_giveback_obj.server = MockONTAPConnection(kind=kind)
        return storage_auto_giveback_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            storage_auto_giveback_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called_existing(self):
        ''' test get_storage_auto_giveback for existing config '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = storage_auto_giveback_module()
        my_obj.server = MockONTAPConnection(kind='auto_giveback_enabled')
        assert my_obj.get_storage_auto_giveback()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_storage_auto_giveback.NetAppOntapStorageAutoGiveback.modify_storage_auto_giveback')
    def test_successful_enable(self, modify_storage_auto_giveback):
        ''' enable storage_auto_giveback and testing idempotency '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = storage_auto_giveback_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('auto_giveback_disabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        modify_storage_auto_giveback.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = storage_auto_giveback_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('auto_giveback_enabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_storage_auto_giveback.NetAppOntapStorageAutoGiveback.modify_storage_auto_giveback')
    def test_successful_disable(self, modify_storage_auto_giveback):
        ''' disable storage_auto_giveback and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['auto_giveback_enabled'] = False
        data['auto_giveback_after_panic_enabled'] = False
        set_module_args(data)
        my_obj = storage_auto_giveback_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('auto_giveback_enabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # modify_storage_auto_giveback.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        data = self.set_default_args(use_rest='Never')
        data['auto_giveback_enabled'] = False
        data['auto_giveback_after_panic_enabled'] = False
        set_module_args(data)
        my_obj = storage_auto_giveback_module()
        my_obj.ems_log_event = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('auto_giveback_disabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = storage_auto_giveback_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('auto_giveback_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_storage_auto_giveback()
        assert 'Error modifying auto giveback' in exc.value.args[0]['msg']

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
            self.get_storage_auto_giveback_mock_object(cx_type='rest').apply()
        assert SRR['generic_error'][2] in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_enabled_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['storage_auto_giveback_disabled_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_storage_auto_giveback_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_enabled_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['storage_auto_giveback_enabled_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_storage_auto_giveback_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_disabled_rest(self, mock_request):
        data = self.set_default_args()
        data['auto_giveback_enabled'] = False
        data['auto_giveback_after_panic_enabled'] = False
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['storage_auto_giveback_enabled_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_storage_auto_giveback_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_disabled_rest(self, mock_request):
        data = self.set_default_args()
        data['auto_giveback_enabled'] = False
        data['auto_giveback_after_panic_enabled'] = False
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['storage_auto_giveback_disabled_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_storage_auto_giveback_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']
