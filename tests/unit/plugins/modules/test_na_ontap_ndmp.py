# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ndmp \
    import NetAppONTAPNdmp as ndmp_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'get_uuid': (200, {'records': [{'uuid': 'testuuid'}]}, None),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, 'Error fetching ndmp from ansible: NetApp API failed. Reason - Unexpected error:',
                      "REST API currently does not support 'backup_log_enable, ignore_ctime_enabled'"),
    'get_ndmp_uuid': (200, {"records": [{"svm": {"name": "svm1", "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"}}]}, None),
    'get_ndmp': (200, {"enabled": True, "authentication_types": ["test"],
                       "records": [{"svm": {"name": "svm1", "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"}}]}, None)
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

    def __init__(self, kind=None, data=None):
        ''' save arguments '''
        self.type = kind
        self.data = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'ndmp':
            xml = self.build_ndmp_info(self.data)
        if self.type == 'error':
            error = netapp_utils.zapi.NaApiError('test', 'error')
            raise error
        self.xml_out = xml
        return xml

    @staticmethod
    def build_ndmp_info(ndmp_details):
        ''' build xml data for ndmp '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'ndmp-vserver-attributes-info': {
                    'ignore_ctime_enabled': ndmp_details['ignore_ctime_enabled'],
                    'backup_log_enable': ndmp_details['backup_log_enable'],

                    'authtype': [
                        {'ndmpd-authtypes': 'plaintext'},
                        {'ndmpd-authtypes': 'challenge'}
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
        self.mock_ndmp = {
            'ignore_ctime_enabled': True,
            'backup_log_enable': 'false',
            'authtype': 'plaintext',
            'enable': True
        }

    def mock_args(self, rest=False):
        if rest:
            return {
                'authtype': self.mock_ndmp['authtype'],
                'enable': True,
                'vserver': 'ansible',
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'https': 'False'
            }
        else:
            return {
                'vserver': 'ansible',
                'authtype': self.mock_ndmp['authtype'],
                'ignore_ctime_enabled': self.mock_ndmp['ignore_ctime_enabled'],
                'backup_log_enable': self.mock_ndmp['backup_log_enable'],
                'enable': self.mock_ndmp['enable'],
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!'
            }

    def get_ndmp_mock_object(self, kind=None, cx_type='zapi'):
        """
        Helper method to return an na_ontap_ndmp object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_ndmp object
        """
        obj = ndmp_module()
        if cx_type == 'zapi':
            obj.asup_log_for_cserver = Mock(return_value=None)
            obj.server = Mock()
            obj.server.invoke_successfully = Mock()
            if kind is None:
                obj.server = MockONTAPConnection()
            else:
                obj.server = MockONTAPConnection(kind=kind, data=self.mock_ndmp)
        return obj

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ndmp.NetAppONTAPNdmp.ndmp_get_iter')
    def test_successful_modify(self, ger_ndmp):
        ''' Test successful modify ndmp'''
        data = self.mock_args()
        set_module_args(data)
        current = {
            'ignore_ctime_enabled': False,
            'backup_log_enable': True
        }
        ger_ndmp.side_effect = [
            current
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ndmp_mock_object('ndmp').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_ndmp.NetAppONTAPNdmp.ndmp_get_iter')
    def test_modify_error(self, ger_ndmp):
        ''' Test modify error '''
        data = self.mock_args()
        set_module_args(data)
        current = {
            'ignore_ctime_enabled': False,
            'backup_log_enable': True
        }
        ger_ndmp.side_effect = [
            current
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_ndmp_mock_object('error').apply()
        assert exc.value.args[0]['msg'] == 'Error modifying ndmp on ansible: NetApp API failed. Reason - test:error'

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        data = self.mock_args()
        data['use_rest'] = 'Always'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_ndmp_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == SRR['generic_error'][3]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_modify(self, mock_request):
        data = self.mock_args(rest=True)
        data['use_rest'] = 'Always'
        set_module_args(data)
        mock_request.side_effect = [
            # SRR['is_rest'],           # WHY IS IT NOT CALLED HERE?
            SRR['get_ndmp_uuid'],       # for get svm uuid: protocols/ndmp/svms
            SRR['get_ndmp'],            # for get ndmp details: '/protocols/ndmp/svms/' + uuid
            SRR['get_ndmp_uuid'],       # for get svm uuid: protocols/ndmp/svms   (before modify)
            SRR['empty_good'],          # modify (patch)
            SRR['end_of_sequence'],
        ]
        my_obj = ndmp_module()
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
