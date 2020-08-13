# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_dns'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_dns \
    import NetAppOntapDns as dns_module  # module under test

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
    'dns_record': (200, {"records": [{"domains": ['test.com'],
                                      "servers": ['0.0.0.0'],
                                      "svm": {"name": "svm1", "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"}}]}, None),
    'cluster_data': (200, {"dns_domains": ['test.com'],
                           "name_servers": ['0.0.0.0'],
                           "name": "cserver",
                           "uuid": "C2c9e252-41be-11e9-81d5-00a0986138f7"}, None),
    'cluster_name': (200, {"name": "cserver"}, None)
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
        if request.startswith("<ems-autosupport-log>"):
            xml = None  # or something that may the logger happy, and you don't need @patch anymore
            # or
            # xml = build_ems_log_response()
        elif request == "<net-dns-get/>":
            if self.kind == 'create':
                raise netapp_utils.zapi.NaApiError(code="15661")
            else:
                xml = self.build_dns_status_info()
        elif request.startswith("<net-dns-create>"):
            xml = self.build_dns_status_info()
        if self.kind == 'enable':
            xml = self.build_dns_status_info()
        self.xml_out = xml
        return xml

    @staticmethod
    def build_dns_status_info():
        xml = netapp_utils.zapi.NaElement('xml')
        nameservers = [{'ip-address': '0.0.0.0'}]
        domains = [{'string': 'test.com'}]
        attributes = {'num-records': 1,
                      'attributes': {'net-dns-info': {'name-servers': nameservers,
                                                      'domains': domains,
                                                      'skip-config-validation': 'false'}}}
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_job_schedule '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)

    def mock_args(self):
        return {
            'state': 'present',
            'vserver': 'vserver',
            'nameservers': ['0.0.0.0'],
            'domains': ['test.com'],
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_dns_mock_object(self, cx_type='zapi', kind=None, status=None):
        dns_obj = dns_module()
        if cx_type == 'zapi':
            if kind is None:
                dns_obj.server = MockONTAPConnection()
            else:
                dns_obj.server = MockONTAPConnection(kind=kind, data=status)
        return dns_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            dns_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_idempotent_modify_dns(self):
        data = self.mock_args()
        data['use_rest'] = 'never'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object('zapi', 'enable', 'false').apply()
        assert not exc.value.args[0]['changed']

    def test_successfully_modify_dns(self):
        data = self.mock_args()
        data['domains'] = ['new_test.com']
        data['use_rest'] = 'never'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object('zapi', 'enable', 'false').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event')
    def test_idempotent_create_dns(self, mock_ems_log_event):
        data = self.mock_args()
        data['use_rest'] = 'never'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object('zapi').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event')
    def test_successfully_create_dns(self, mock_ems_log_event):
        data = self.mock_args()
        print("create dns")
        data['domains'] = ['new_test.com']
        data['use_rest'] = 'never'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object('zapi', 'create').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_dns_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create(self, mock_request):
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],    # get
            SRR['cluster_data'],  # get cluster
            SRR['empty_good'],    # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_is_cluster_vserver(self, mock_request):
        data = self.mock_args()
        data['vserver'] = 'cvserver'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],    # get
            SRR['cluster_name'],  # get cluster name
            SRR['empty_good'],    # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_idempotent_create_dns(self, mock_request):
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['dns_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_destroy(self, mock_request):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['dns_record'],  # get
            SRR['empty_good'],  # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_idempotently_destroy(self, mock_request):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],    # get
            SRR['cluster_data'],  # get cluster
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_modify(self, mock_request):
        data = self.mock_args()
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],    # get
            SRR['cluster_data'],  # get cluster
            SRR['empty_good'],    # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_modify_is_cluster_vserver(self, mock_request):
        data = self.mock_args()
        data['vserver'] = 'cvserver'
        data['state'] = 'present'
        data['domains'] = 'new_test.com'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],    # get
            SRR['cluster_data'],  # get cluster data
            SRR['empty_good'],    # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_idempotently_modify(self, mock_request):
        data = self.mock_args()
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['dns_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_dns_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']
