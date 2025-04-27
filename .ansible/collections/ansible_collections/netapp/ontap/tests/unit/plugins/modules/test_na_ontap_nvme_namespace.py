# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_nvme_namespace'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_nvme_namespace \
    import NetAppONTAPNVMENamespace as my_module

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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
        if self.type == 'namespace':
            xml = self.build_namespace_info()
        elif self.type == 'quota_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_namespace_info():
        ''' build xml data for namespace-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 2,
                'attributes-list': [{'nvme-namespace-info': {'path': 'abcd/vol'}},
                                    {'nvme-namespace-info': {'path': 'xyz/vol'}}]}
        xml.translate_struct(data)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.server = MockONTAPConnection()
        self.onbox = False

    def set_default_args(self):
        if self.onbox:
            hostname = '10.193.75.3'
            username = 'admin'
            password = 'netapp1!'
            vserver = 'ansible'
            ostype = 'linux'
            path = 'abcd/vol'
            size = 20
            size_unit = 'mb'
        else:
            hostname = 'hostname'
            username = 'username'
            password = 'password'
            vserver = 'vserver'
            ostype = 'linux'
            path = 'abcd/vol'
            size = 20
            size_unit = 'mb'
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'ostype': ostype,
            'vserver': vserver,
            'path': path,
            'size': size,
            'size_unit': size_unit,
            'use_rest': 'never',
        })

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_namespace()  for non-existent namespace'''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = self.server
        assert my_obj.get_namespace() is None

    def test_ensure_get_called_existing(self):
        ''' test get_namespace()  for existing namespace'''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = MockONTAPConnection(kind='namespace')
        assert my_obj.get_namespace()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_nvme_namespace.NetAppONTAPNVMENamespace.create_namespace')
    def test_successful_create(self, create_namespace):
        ''' creating namespace and testing idempotency '''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        create_namespace.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('namespace')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_nvme_namespace.NetAppONTAPNVMENamespace.delete_namespace')
    def test_successful_delete(self, delete_namespace):
        ''' deleting namespace and testing idempotency '''
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('namespace')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        delete_namespace.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('quota_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.get_namespace()
        assert 'Error fetching namespace info:' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_namespace()
        assert 'Error creating namespace for path' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.delete_namespace()
        assert 'Error deleting namespace for path' in exc.value.args[0]['msg']
