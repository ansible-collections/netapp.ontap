''' unit tests ONTAP Ansible module: na_ontap_quotas '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_quotas \
    import NetAppONTAPQuotas as my_module

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

    def __init__(self, kind=None, status=None):
        ''' save arguments '''
        self.type = kind
        self.status = status
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        print('IN:', xml.to_string())
        zapi = xml.get_name()
        if zapi == 'quota-status' and self.type != 'quota_fail':
            return self.build_quota_status(self.status)
        if self.type == 'quotas':
            xml = self.build_quota_info()
        elif self.type == 'quota_policy':
            xml = self.build_quota_policy_info_one()
            # expect a second request to get details
            self.type = 'quotas'
        elif self.type == 'quota_policies':
            xml = self.build_quota_policy_info_two()
        elif self.type == 'quota_fail_13001':
            # expect a retry
            self.type = 'quota_policy'
            raise netapp_utils.zapi.NaApiError(code='13001', message="success")
        elif self.type == 'quota_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_quota_info():
        ''' build xml data for quota-entry '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1,
                'attributes-list': {'quota-entry': {'volume': 'ansible',
                                                    'file-limit': '-', 'disk-limit': '-', 'quota-target': '/vol/ansible',
                                                    'soft-file-limit': '-', 'soft-disk-limit': '-', 'threshold': '-'}},
                'status': 'true'}
        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_quota_policy_info_one():
        ''' build xml data for quota-entry '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1,
                'attributes-list': [
                    {'quota-policy-info': {'policy-name': 'p1'}}],
                'status': 'true'}
        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_quota_policy_info_two():
        ''' build xml data for quota-entry '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 2,
                'attributes-list': [{'quota-policy-info': {'policy-name': 'p1'}},
                                    {'quota-policy-info': {'policy-name': 'p2'}}],
                'status': 'true'}
        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_quota_status(status):
        ''' build xml data for quota-status '''
        status = 'off' if status is None else status
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'status': status}
        xml.translate_struct(data)
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
        self.onbox = False

    def set_default_args(self):
        if self.onbox:
            hostname = '10.193.75.3'
            username = 'admin'
            password = 'netapp1!'
            volume = 'ansible'
            vserver = 'ansible'
            policy = 'ansible'
            quota_target = '/vol/ansible'
            type = 'user'
        else:
            hostname = 'hostname'
            username = 'username'
            password = 'password'
            volume = 'ansible'
            vserver = 'ansible'
            policy = 'ansible'
            quota_target = '/vol/ansible'
            type = 'user'
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'volume': volume,
            'vserver': vserver,
            'policy': policy,
            'quota_target': quota_target,
            'type': type
        })

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_quota for non-existent quota'''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = self.server
        assert my_obj.get_quotas is not None

    def test_ensure_get_called_existing(self):
        ''' test get_quota for existing quota'''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = MockONTAPConnection(kind='quotas')
        assert my_obj.get_quotas()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_quotas.NetAppONTAPQuotas.quota_entry_set')
    def test_successful_create(self, quota_entry_set):
        ''' creating quota and testing idempotency '''
        data = self.set_default_args()
        data.update({'file_limit': '3',
                     'disk_limit': '4',
                     'soft_file_limit': '3',
                     'soft_disk_limit': '4',
                     })
        # data['file_limit'] = '3'
        # data['disk_limit'] = '4'
        # data['threshold'] = '4'
        set_module_args(data)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        quota_entry_set.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(self.set_default_args())
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('quotas')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_quotas.NetAppONTAPQuotas.quota_entry_delete')
    def test_successful_delete(self, quota_entry_delete):
        ''' deleting quota and testing idempotency '''
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('quotas')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        quota_entry_delete.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_successful_modify(self):
        ''' modifying quota and testing idempotency '''
        data = self.set_default_args()
        data['file_limit'] = '3'
        set_module_args(data)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('quotas')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']

    def test_quota_on_off(self):
        ''' quota set on or off '''
        data = self.set_default_args()
        data['set_quota_status'] = 'false'
        set_module_args(data)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('quotas', 'off')
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
            my_obj.get_quota_status()
        assert 'Error fetching quotas status info' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.get_quotas()
        assert 'Error fetching quotas info' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.quota_entry_set()
        assert 'Error adding/modifying quota entry' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.quota_entry_delete()
        assert 'Error deleting quota entry' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.quota_entry_modify(module_args)
        assert 'Error modifying quota entry' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.on_or_off_quota('quota-on')
        assert 'Error setting quota-on for ansible' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.get_quota_policies()
        assert 'Error fetching quota policies: NetApp API failed. Reason - TEST:This exception is from the unit test' in exc.value.args[0]['msg']

    def test_get_quota_policies(self):
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('quota_policies')
        policies = my_obj.get_quota_policies()
        assert len(policies) == 2

    def test_debug_quota_get_error_fail(self):
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('quota_policies')
        error = 'dummy error'
        with pytest.raises(AnsibleFailJson) as exc:
            policies = my_obj.debug_quota_get_error(error)
        msg = 'Error fetching quotas info: dummy error - current vserver policies: '
        assert msg in exc.value.args[0]['msg']

    def test_debug_quota_get_error_success(self):
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('quota_policy')
        error = 'dummy error'
        quotas = my_obj.debug_quota_get_error(error)
        print('QUOTAS', quotas)
        assert quotas

    def test_get_quota_no_retry_on_13001(self):
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('quota_fail_13001')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.get_quotas()
        msg = 'Error fetching quotas info for policy ansible: NetApp API failed. Reason - 13001:success'
        assert msg in exc.value.args[0]['msg']

    def test_get_quota_retry_on_13001(self):
        module_args = {}
        module_args.update(self.set_default_args())
        module_args.pop('policy')
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('quota_fail_13001')
        quotas = my_obj.get_quotas()
        print('QUOTAS', quotas)
        assert quotas
