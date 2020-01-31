# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_volume_clone'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_clone \
    import NetAppONTAPVolumeClone as my_module

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

    def __init__(self, kind=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'volume_clone':
            xml = self.build_volume_clone_info()
        elif self.type == 'volume_clone_split_in_progress':
            xml = self.build_volume_clone_info_split_in_progress()
        elif self.type == 'volume_clone_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_volume_clone_info():
        ''' build xml data for volume-clone-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'attributes': {'volume-clone-info': {'volume': 'ansible',
                                                     'parent-volume': 'ansible'}}}
        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_volume_clone_info_split_in_progress():
        ''' build xml data for volume-clone-info whilst split in progress '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'attributes': {'volume-clone-info': {'volume': 'ansible',
                                                     'parent-volume': 'ansible',
                                                     'block-percentage-complete': 20,
                                                     'blocks-scanned': 56676,
                                                     'blocks-updated': 54588}}}
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
        self.vserver = MockONTAPConnection()
        self.onbox = False

    def set_default_args(self):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'ansible'
            volume = 'ansible'
            parent_volume = 'ansible'
            split = None
        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'ansible'
            volume = 'ansible'
            parent_volume = 'ansible'
            split = None
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'vserver': vserver,
            'volume': volume,
            'parent_volume': parent_volume,
            'split': split
        })

    def set_default_current(self):
        return dict({
            'split': False
        })

    def test_module_fail_when_required_args_missing(self):
        ''' test required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_volume_clone() for non-existent volume clone'''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.vserver = self.vserver
        assert my_obj.get_volume_clone() is None

    def test_ensure_get_called_existing(self):
        ''' test get_volume_clone() for existing volume clone'''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.vserver = MockONTAPConnection(kind='volume_clone')
        current = self.set_default_current()
        assert my_obj.get_volume_clone() == current

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_clone.NetAppONTAPVolumeClone.create_volume_clone')
    def test_successful_create(self, create_volume_clone):
        ''' test creating volume_clone without split and testing idempotency '''
        module_args = {
            'parent_vserver': 'abc',
            'parent_snapshot': 'abc',
            'volume_type': 'dp',
            'qos_policy_group_name': 'abc',
            'junction_path': 'abc',
            'uid': '1',
            'gid': '1'
        }
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.vserver = self.vserver
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        create_volume_clone.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = my_module()
        if not self.onbox:
            my_obj.vserver = MockONTAPConnection('volume_clone')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_clone.NetAppONTAPVolumeClone.create_volume_clone')
    def test_successful_create_with_split(self, create_volume_clone):
        ''' test creating volume_clone with split and testing idempotency '''
        module_args = {
            'parent_snapshot': 'abc',
            'parent_vserver': 'abc',
            'volume_type': 'dp',
            'qos_policy_group_name': 'abc',
            'junction_path': 'abc',
            'uid': '1',
            'gid': '1'
        }
        module_args.update(self.set_default_args())
        module_args['split'] = True
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.vserver = self.vserver
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        create_volume_clone.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = my_module()
        if not self.onbox:
            my_obj.vserver = MockONTAPConnection('volume_clone_split_in_progress')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_clone.NetAppONTAPVolumeClone.create_volume_clone')
    def test_successful_create_with_split_in_progress(self, create_volume_clone):
        ''' test creating volume_clone with split and split already in progress '''
        module_args = {
            'parent_snapshot': 'abc',
            'parent_vserver': 'abc',
            'volume_type': 'dp',
            'qos_policy_group_name': 'abc',
            'junction_path': 'abc',
            'uid': '1',
            'gid': '1'
        }
        module_args.update(self.set_default_args())
        module_args['split'] = True
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.vserver = MockONTAPConnection('volume_clone_split_in_progress')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        ''' test if all methods catch exception '''
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.vserver = MockONTAPConnection('volume_clone_fail')
            my_obj.create_server = my_obj.vserver
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.get_volume_clone()
        assert 'Error fetching volume clone information ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_volume_clone()
        assert 'Error creating volume clone: ' in exc.value.args[0]['msg']
