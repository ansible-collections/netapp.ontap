# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_ldap_client '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ldap_client \
    import NetAppOntapLDAPClient as client_module  # module under test

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
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.kind == 'client':
            xml = self.build_ldap_client_info(self.params)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_ldap_client_info(client_details):
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'ldap-client': {
                    'ldap-client-config': client_details['name'],
                    'schema': client_details['schema'],
                    'ldap-servers': [
                        {"ldap-server": client_details['ldap_servers'][0]},
                        {"ldap-server": client_details['ldap_servers'][1]}
                    ]
                }
            }
        }
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
        self.mock_client = {
            'state': 'present',
            'name': 'test_ldap',
            'ldap_servers': ['ldap1.example.company.com', 'ldap2.example.company.com'],
            'schema': 'RFC-2307',
            'vserver': 'test_vserver',
        }

    def mock_args(self):
        return {
            'state': self.mock_client['state'],
            'name': self.mock_client['name'],
            'ldap_servers': self.mock_client['ldap_servers'],
            'schema': self.mock_client['schema'],
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!',
            'vserver': 'test_vserver',
        }

    def get_client_mock_object(self, kind=None):
        client_obj = client_module()
        client_obj.asup_log_for_cserver = Mock(return_value=None)
        if kind is None:
            client_obj.server = MockONTAPConnection()
        else:
            client_obj.server = MockONTAPConnection(kind='client', data=self.mock_client)
        return client_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            client_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_nonexistent_client(self):
        ''' Test if get ldap client returns None for non-existent job '''
        set_module_args(self.mock_args())
        result = self.get_client_mock_object().get_ldap_client()
        assert not result

    def test_get_existing_client(self):
        ''' Test if get ldap client returns None for non-existent job '''
        set_module_args(self.mock_args())
        result = self.get_client_mock_object('client').get_ldap_client()
        assert result

    def test_successfully_create(self):
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_client_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_successfully_create_ad_servers(self):
        self.set_args_for_ad()
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_client_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_create_idempotency(self):
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_client_mock_object('client').apply()
        assert not exc.value.args[0]['changed']

    def test_successfully_delete(self):
        self.set_args_for_delete()
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_client_mock_object('client').apply()
        assert exc.value.args[0]['changed']

    def test_delete_idempotency(self):
        self.set_args_for_delete()
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_client_mock_object().apply()
        assert not exc.value.args[0]['changed']

    def set_args_for_delete(self):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)

    def test_successfully_modify(self):
        data = self.mock_args()
        data['ldap_servers'] = ["ldap1.example.company.com"]
        set_module_args(data)
        print(self.get_client_mock_object('client').get_ldap_client())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_client_mock_object('client').apply()
        assert exc.value.args[0]['changed']

    def test_successfully_modify_ad_servers(self):
        self.set_args_for_ad()
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_client_mock_object('client').apply()
        assert exc.value.args[0]['changed']

    def set_args_for_ad(self):
        data = self.mock_args()
        data.pop('ldap_servers')
        data['ad_domain'] = 'example.com'
        data['preferred_ad_servers'] = ['10.10.10.1', '10.10.10.2']
        set_module_args(data)
