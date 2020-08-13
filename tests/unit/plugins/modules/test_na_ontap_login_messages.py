# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_login_messages'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_login_messages \
    import NetAppOntapLoginMessages as messages_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')
HAS_NETAPP_ZAPI_MSG = "pip install netapp_lib is required"


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # 'dns_record': ({"records": [{"message": "test message",
    #                              "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"}]}, None),
    'svm_uuid': (200, {"records": [{"uuid": "test_uuid"}], "num_records": 1}, None)
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
        self.kind = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        request = xml.to_string().decode('utf-8')
        print(request)
        if self.kind == 'error':
            raise netapp_utils.zapi.NaApiError('test', 'expect error')
        elif request.startswith("<ems-autosupport-log>"):
            xml = None  # or something that may the logger happy, and you don't need @patch anymore
            # or
            # xml = build_ems_log_response()
        elif request.startswith("<vserver-login-banner-get-iter>"):
            if self.kind == 'create':
                xml = self.build_banner_info()
            # elif self.kind == 'create_idempotency':
            #     xml = self.build_banner_info(self.params)
            else:
                xml = self.build_banner_info(self.params)
        elif request.startswith("<vserver-login-banner-modify-iter>"):
            xml = self.build_banner_info(self.params)
        elif request.startswith("<vserver-motd-modify-iter>"):
            xml = self.build_motd_info(self.params)
        elif request.startswith("<vserver-motd-get-iter>"):
            if self.kind == 'create':
                xml = self.build_motd_info()
            # elif self.kind == 'create_idempotency':
            #     xml = self.build_banner_info(self.params)
            else:
                xml = self.build_motd_info(self.params)

        self.xml_out = xml
        return xml

    @staticmethod
    def build_banner_info(data=None):
        xml = netapp_utils.zapi.NaElement('xml')
        vserver = 'vserver'
        attributes = {'num-records': 1,
                      'attributes-list': {'vserver-login-banner-info': {'vserver': vserver}}}
        if data is not None and data.get('banner'):
            attributes['attributes-list']['vserver-login-banner-info']['message'] = data['banner']
        xml.translate_struct(attributes)
        return xml

    @staticmethod
    def build_motd_info(data=None):
        xml = netapp_utils.zapi.NaElement('xml')
        vserver = 'vserver'
        attributes = {'num-records': 1,
                      'attributes-list': {'vserver-motd-info': {'vserver': vserver}}}
        if data is not None and data.get('motd_message'):
            attributes['attributes-list']['vserver-motd-info']['message'] = data['motd_message']
        if data is not None and data.get('show_cluster_motd') is False:
            attributes['attributes-list']['vserver-motd-info']['is-cluster-message-enabled'] = 'false'
        else:
            attributes['attributes-list']['vserver-motd-info']['is-cluster-message-enabled'] = 'true'
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_login_banner '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)

    def mock_args(self):
        return {
            'vserver': 'vserver',
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_login_mock_object(self, cx_type='zapi', kind=None, status=None):
        banner_obj = messages_module()
        netapp_utils.ems_log_event = Mock(return_value=None)
        if cx_type == 'zapi':
            if kind is None:
                banner_obj.server = MockONTAPConnection()
            else:
                banner_obj.server = MockONTAPConnection(kind=kind, data=status)
        return banner_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            messages_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_successfully_create_banner(self):
        data = self.mock_args()
        data['banner'] = 'test banner'
        data['use_rest'] = 'never'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_login_mock_object('zapi', 'create', data).apply()
        assert exc.value.args[0]['changed']

    def test_create_banner_idempotency(self):
        data = self.mock_args()
        data['banner'] = 'test banner'
        data['use_rest'] = 'never'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_login_mock_object('zapi', 'create_idempotency', data).apply()
        assert not exc.value.args[0]['changed']

    def test_successfully_create_motd(self):
        data = self.mock_args()
        data['motd_message'] = 'test message'
        data['use_rest'] = 'never'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_login_mock_object('zapi', 'create', data).apply()
        assert exc.value.args[0]['changed']

    def test_create_motd_idempotency(self):
        data = self.mock_args()
        data['motd_message'] = 'test message'
        data['use_rest'] = 'never'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_login_mock_object('zapi', 'create_idempotency', data).apply()
        assert not exc.value.args[0]['changed']

    def test_get_banner_error(self):
        data = self.mock_args()
        data['use_rest'] = 'never'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_login_mock_object('zapi', 'error', data).apply()
        assert exc.value.args[0]['msg'] == 'Error fetching login_banner info: NetApp API failed. Reason - test:expect error'

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_login_messages.NetAppOntapLoginMessages.get_banner_motd')
    def test_modify_banner_error(self, get_info):
        data = self.mock_args()
        data['banner'] = 'modify to new banner'
        data['use_rest'] = 'never'
        set_module_args(data)
        get_info.side_effect = [
            {
                'banner': 'old banner',
                'motd': ''
            }
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_login_mock_object('zapi', 'error', data).apply()
        assert exc.value.args[0]['msg'] == 'Error modifying login_banner: NetApp API failed. Reason - test:expect error'

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_login_messages.NetAppOntapLoginMessages.get_banner_motd')
    def test_modify_motd_error(self, get_info):
        data = self.mock_args()
        data['motd_message'] = 'modify to new motd'
        data['use_rest'] = 'never'
        set_module_args(data)
        get_info.side_effect = [
            {
                'motd': 'old motd',
                'show_cluster_motd': False
            }
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_login_mock_object('zapi', 'error', data).apply()
        assert exc.value.args[0]['msg'] == 'Error modifying motd: NetApp API failed. Reason - test:expect error'

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successfully_create_banner_rest(self, mock_request):
        data = self.mock_args()
        data['banner'] = 'test banner'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['svm_uuid'],
            SRR['empty_good'],    # get
            SRR['empty_good'],    # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_login_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_banner_error_rest(self, mock_request):
        data = self.mock_args()
        data['banner'] = 'test banner'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['svm_uuid'],
            SRR['generic_error'],    # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_login_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == 'Error when fetching login_banner info: Expected error'

        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['svm_uuid'],
            SRR['empty_good'],       # get
            SRR['generic_error'],    # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_login_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == 'Error when modifying banner: Expected error'
