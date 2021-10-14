# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_object_store """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_object_store \
    import NetAppOntapObjectStoreConfig as my_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'get_uuid': (200, {'records': [{'uuid': 'ansible'}]}, None),
    'get_object_store': (200,
                         {'uuid': 'ansible',
                          'name': 'ansible',
                          'provider_type': 'abc',
                          'access_key': 'abc',
                          'owner': 'fabricpool'
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
        print('IN:', xml.to_string())
        if self.type == 'object_store':
            xml = self.build_object_store_info()
        elif self.type == 'object_store_not_found':
            self.type = 'object_store'
            raise netapp_utils.zapi.NaApiError(code='15661', message="This exception is from the unit test - 15661")
        elif self.type == 'object_store_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        print('OUT:', xml.to_string())
        return xml

    @staticmethod
    def build_object_store_info():
        ''' build xml data for object store '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'attributes':
                {'aggr-object-store-config-info':
                 {'object-store-name': 'ansible',
                  'provider-type': 'abc',
                  'access-key': 'abc',
                  'server': 'abc',
                  's3-name': 'abc',
                  'ssl-enabled': 'true',
                  'port': '1234',
                  'is-certificate-validation-enabled': 'true'}
                 }
                }
        xml.translate_struct(data)
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
        self.server = MockONTAPConnection()
        # whether to use a mock or a simulator
        self.onbox = False

    def set_default_args(self):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'admin'
            password = 'password'
            name = 'ansible'
        else:
            hostname = 'hostname'
            username = 'username'
            password = 'password'
            name = 'ansible'
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'name': name
        })

    def call_command(self, module_args, cx_type='zapi'):
        ''' utility function to call apply '''
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        if cx_type == 'zapi':
            if not self.onbox:
                # mock the connection
                my_obj.server = MockONTAPConnection('object_store')
            with pytest.raises(AnsibleExitJson) as exc:
                my_obj.apply()
        return exc.value.args[0]['changed']

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_netapp_lib(self, mock_request, mock_has_netapp_lib):
        ''' fetching details of object store '''
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        mock_has_netapp_lib.return_value = False
        set_module_args(self.set_default_args())
        with pytest.raises(AnsibleFailJson) as exc:
            my_main()
        msg = 'Error: the python NetApp-Lib module is required.  Import error: None'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_ensure_object_store_get_called(self, mock_request):
        ''' fetching details of object store '''
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = self.server
        assert my_obj.get_aggr_object_store() is None

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_ensure_get_called_existing(self, mock_request):
        ''' test for existing object store'''
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = MockONTAPConnection(kind='object_store')
        object_store = my_obj.get_aggr_object_store()
        assert object_store
        assert 'name' in object_store
        assert object_store['name'] == 'ansible'

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_object_store_create(self, mock_request, mock_ems):
        ''' test for creating object store'''
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        module_args = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc',
            'access_key': 'abc',
            'secret_password': 'abc',
            'port': 1234,
            'certificate_validation_enabled': True,
            'ssl_enabled': True
        }
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            # mock the connection
            my_obj.server = MockONTAPConnection(kind='object_store_not_found')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_object_store_negative_create_bad_owner(self, mock_request, mock_ems):
        ''' test for creating object store'''
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        module_args = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc',
            'access_key': 'abc',
            'secret_password': 'abc',
            'port': 1234,
            'certificate_validation_enabled': True,
            'ssl_enabled': True,
            'owner': 'snapmirror'
        }
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        with pytest.raises(AnsibleFailJson) as exc:
            my_module()
        print(exc.value.args[0])
        assert exc.value.args[0]['msg'] == 'Error: unsupported value for owner: snapmirror when using ZAPI.'

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_object_store_delete(self, mock_request):
        ''' test for deleting object store'''
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        module_args = {
            'state': 'absent',
        }
        changed = self.call_command(module_args)
        assert changed

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_object_store_modify(self, mock_request, mock_ems):
        ''' test for modifying object store'''
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        module_args = {
            'provider_type': 'abc',
            'server': 'abc2',
            'container': 'abc',
            'access_key': 'abc2',
            'secret_password': 'abc'
        }
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.server = MockONTAPConnection(kind='object_store')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = 'Error - modify is not supported with ZAPI'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        set_module_args(self.set_default_args())
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['msg'] == 'Error calling: cloud/targets: got %s.' % SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create(self, mock_request):
        data = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc',
            'access_key': 'abc',
            'secret_password': 'abc',
            'port': 1234,
            'certificate_validation_enabled': True,
            'ssl_enabled': True
        }
        data.update(self.set_default_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_create_missing_parameter(self, mock_request):
        data = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc',
            'secret_password': 'abc',
            'port': 1234,
            'certificate_validation_enabled': True,
            'ssl_enabled': True
        }
        data.update(self.set_default_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = 'Error provisioning object store ansible: one of the following parameters are missing'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_create_api_error(self, mock_request):
        data = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc',
            'access_key': 'abc',
            'secret_password': 'abc',
            'port': 1234,
            'certificate_validation_enabled': True,
            'ssl_enabled': True
        }
        data.update(self.set_default_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            my_main()
        assert exc.value.args[0]['msg'] == 'Error calling: cloud/targets: got %s.' % SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_modify(self, mock_request):
        data = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc2',
            'access_key': 'abc2',
            'secret_password': 'abc'
        }
        data.update(self.set_default_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_object_store'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print(mock_request.mock_calls)
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_modify_rest_error(self, mock_request):
        data = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc2',
            'access_key': 'abc2',
            'secret_password': 'abc'
        }
        data.update(self.set_default_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_object_store'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['msg'] == 'Error calling: cloud/targets/ansible: got %s.' % SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_modify_owner(self, mock_request):
        data = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc2',
            'access_key': 'abc2',
            'secret_password': 'abc',
            'owner': 'snapmirror'
        }
        data.update(self.set_default_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_object_store'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['msg'] == 'Error modifying object store, owner cannot be changed.  Found: snapmirror.'

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_modify_password(self, mock_request):
        data = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc',
            'access_key': 'abc',
            'secret_password': 'abc2',
            'change_password': True

        }
        data.update(self.set_default_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_object_store'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print(mock_request.mock_calls)
        assert exc.value.args[0]['changed']
        assert 'secret_password' in exc.value.args[0]['modify']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_idempotent(self, mock_request):
        data = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc',
            'access_key': 'abc',
            'secret_password': 'abc2'
        }
        data.update(self.set_default_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_object_store'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print(mock_request.mock_calls)
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_delete(self, mock_request):
        data = {
            'state': 'absent',
        }
        data.update(self.set_default_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_uuid'],
            SRR['get_object_store'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_delete(self, mock_request):
        data = {
            'state': 'absent',
        }
        data.update(self.set_default_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_object_store'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        my_obj = my_module()
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['msg'] == 'Error calling: cloud/targets/ansible: got %s.' % SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_if_all_methods_catch_exception(self, mock_request):
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        module_args = {
            'provider_type': 'abc',
            'server': 'abc',
            'container': 'abc',
            'access_key': 'abc',
            'secret_password': 'abc'
        }
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('object_store_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.get_aggr_object_store()
        assert '' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_aggr_object_store(None)
        assert 'Error provisioning object store config ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.delete_aggr_object_store()
        assert 'Error removing object store config ' in exc.value.args[0]['msg']
