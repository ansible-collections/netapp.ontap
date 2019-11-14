# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_volume_export_policy '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_name_service_switch \
    import NetAppONTAPNsswitch as nss_module  # module under test

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
        if self.kind == 'nss':
            xml = self.build_nss_info(self.params)
        if self.kind == 'error':
            error = netapp_utils.zapi.NaApiError('test', 'error')
            raise error
        self.xml_out = xml
        return xml

    @staticmethod
    def build_nss_info(nss_details):
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'namservice-nsswitch-config-info': {
                    'nameservice-database': nss_details['database_type'],
                    'nameservice-sources': {
                        'nss-source-type': nss_details['sources']
                    }
                }
            }
        }
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_name_service_switch '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_nss = {
            'state': 'present',
            'vserver': 'test_vserver',
            'database_type': 'namemap',
            'sources': 'files,ldap',
        }

    def mock_args(self):
        return {
            'state': self.mock_nss['state'],
            'vserver': self.mock_nss['vserver'],
            'database_type': self.mock_nss['database_type'],
            'sources': self.mock_nss['sources'],
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_nss_object(self, kind=None):
        nss_obj = nss_module()
        nss_obj.asup_log_for_cserver = Mock(return_value=None)
        if kind is None:
            nss_obj.server = MockONTAPConnection()
        else:
            nss_obj.server = MockONTAPConnection(kind=kind, data=self.mock_nss)
        return nss_obj

    def test_module_fail_when_required_args_missing(self):
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            nss_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_nonexistent_nss(self):
        set_module_args(self.mock_args())
        result = self.get_nss_object().get_name_service_switch()
        assert result is None

    def test_get_existing_nss(self):
        set_module_args(self.mock_args())
        result = self.get_nss_object('nss').get_name_service_switch()
        assert result

    def test_successfully_create(self):
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_nss_object().apply()
        assert exc.value.args[0]['changed']

    def test_successfully_modify(self):
        data = self.mock_args()
        data['sources'] = 'files'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_nss_object('nss').apply()
        assert exc.value.args[0]['changed']

    def test_successfully_delete(self):
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_nss_object('nss').apply()
        assert exc.value.args[0]['changed']

    def test_error(self):
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_nss_object('error').create_name_service_switch()
        print(exc)
        assert exc.value.args[0]['msg'] == 'Error on creating name service switch config on vserver test_vserver: NetApp API failed. Reason - test:error'
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_nss_object('error').modify_name_service_switch({})
        print(exc)
        assert exc.value.args[0]['msg'] == 'Error on modifying name service switch config on vserver test_vserver: NetApp API failed. Reason - test:error'
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_nss_object('error').delete_name_service_switch()
        print(exc)
        assert exc.value.args[0]['msg'] == 'Error on deleting name service switch config on vserver test_vserver: NetApp API failed. Reason - test:error'
