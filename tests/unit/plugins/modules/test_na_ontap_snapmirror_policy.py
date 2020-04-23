''' unit tests ONTAP Ansible module: na_ontap_snapmirror_policy '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy \
    import NetAppOntapSnapMirrorPolicy as my_module

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': ({}, None),
    'end_of_sequence': (None, "Unexpected call to send_request"),
    'generic_error': (None, "Expected error"),
    # module specific responses
    'get_snapmirror_policy': {'svm.name': 'ansible',
                              'name': 'ansible',
                              'uuid': 1234,
                              'comment': 'created by ansible',
                              'type': 'ansible'}
}


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

    def __init__(self, kind=None, parm=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None
        self.parm = parm

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'snapmirror_policy':
            xml = self.build_snapmirror_policy_info(self.parm)
        elif self.type == 'snapmirror_policy_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_snapmirror_policy_info(mirror_state):
        ''' build xml data for snapmirror_policy-entry '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1,
                'attributes-list': {'snapmirror-policy-info': {'comment': 'created by ansible',
                                                               'policy-name': 'ansible',
                                                               'type': 'async_mirror',
                                                               'tries': '8',
                                                               'transfer-priority': 'normal',
                                                               'restart': 'always',
                                                               'is-network-compression-enabled': False,
                                                               'ignore-atime': False,
                                                               'vserver-name': 'ansible'}}}
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
        self.source_server = MockONTAPConnection()
        self.onbox = False

    def set_default_args(self, use_rest=None):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'admin'
            password = 'password'
            vserver = 'ansible'
            policy_name = 'ansible'
            policy_type = 'async_mirror'
            comment = 'created by ansible'
        else:
            hostname = '10.10.10.10'
            username = 'admin'
            password = 'password'
            vserver = 'ansible'
            policy_name = 'ansible'
            policy_type = 'async_mirror'
            comment = 'created by ansible'

        args = dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'vserver': vserver,
            'policy_name': policy_name,
            'policy_type': policy_type,
            'comment': comment
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test snapmirror_policy_get for non-existent snapmirror policy'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = my_module()
        my_obj.server = self.server
        assert my_obj.get_snapmirror_policy is not None

    def test_ensure_get_called_existing(self):
        ''' test snapmirror_policy_get for existing snapmirror policy'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = my_module()
        my_obj.server = MockONTAPConnection(kind='snapmirror_policy')
        assert my_obj.get_snapmirror_policy()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.create_snapmirror_policy')
    def test_successful_create(self, snapmirror_create_policy):
        ''' creating snapmirror_policy and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        snapmirror_create_policy.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapmirror_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.create_snapmirror_policy')
    def test_successful_create_with_rest(self, snapmirror_create_policy):
        ''' creating snapmirror_policy and testing idempotency '''
        data = self.set_default_args()
        data['use_rest'] = 'Always'
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=None)
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        snapmirror_create_policy.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        data = self.set_default_args(use_rest='Never')
        data['use_rest'] = 'Always'
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=SRR['get_snapmirror_policy'])
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.delete_snapmirror_policy')
    def test_successful_delete(self, delete_snapmirror_policy):
        ''' deleting snapmirror_policy and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapmirror_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        delete_snapmirror_policy.assert_called_with(None)
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.delete_snapmirror_policy')
    def test_successful_delete_with_rest(self, delete_snapmirror_policy):
        ''' deleting snapmirror_policy and testing idempotency '''
        data = self.set_default_args()
        data['state'] = 'absent'
        data['use_rest'] = 'Always'
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=SRR['get_snapmirror_policy'])
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        delete_snapmirror_policy.assert_called_with(1234)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=None)
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.modify_snapmirror_policy')
    def test_successful_modify(self, snapmirror_policy_modify):
        ''' modifying snapmirror_policy and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['comment'] = 'old comment'
        data['ignore_atime'] = True
        data['is_network_compression_enabled'] = True
        data['owner'] = 'cluster_admin'
        data['restart'] = 'default'
        data['tries'] = '7'
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapmirror_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        snapmirror_policy_modify.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapmirror_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.modify_snapmirror_policy')
    def test_successful_modify_with_rest(self, snapmirror_policy_modify):
        ''' modifying snapmirror_policy and testing idempotency '''
        data = self.set_default_args()
        data['comment'] = 'old comment'
        data['use_rest'] = 'Always'
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=SRR['get_snapmirror_policy'])
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        snapmirror_policy_modify.assert_called_with(1234, 'ansible')
        # to reset na_helper from remembering the previous 'changed' value
        data = self.set_default_args()
        data['use_rest'] = 'Always'
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=SRR['get_snapmirror_policy'])
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapmirror_policy_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.get_snapmirror_policy()
        assert 'Error getting snapmirror policy ansible:' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_snapmirror_policy()
        assert 'Error creating snapmirror policy ansible:' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.delete_snapmirror_policy()
        assert 'Error deleting snapmirror policy ansible:' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_snapmirror_policy()
        assert 'Error modifying snapmirror policy ansible:' in exc.value.args[0]['msg']
