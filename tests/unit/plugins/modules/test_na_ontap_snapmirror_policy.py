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
    'get_snapmirror_policy': {'vserver': 'ansible',
                              'policy_name': 'ansible',
                              'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
                              'comment': 'created by ansible',
                              'policy_type': 'async_mirror',
                              'snapmirror_label': [],
                              'keep': [],
                              'schedule': [],
                              'prefix': []},
    'get_snapmirror_policy_with_rules': {'vserver': 'ansible',
                                         'policy_name': 'ansible',
                                         'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
                                         'comment': 'created by ansible',
                                         'policy_type': 'async_mirror',
                                         'snapmirror_label': ['daily', 'weekly', 'monthly'],
                                         'keep': [7, 5, 12],
                                         'schedule': ['', 'weekly', 'monthly'],
                                         'prefix': ['', 'weekly', 'monthly']}
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

    def set_default_args(self, use_rest=None, with_rules=False):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'admin'
            password = 'password'
            vserver = 'ansible'
            policy_name = 'ansible'
            policy_type = 'async_mirror'
            comment = 'created by ansible'
            snapmirror_label = ['daily', 'weekly', 'monthly']
            keep = [7, 5, 12]
            schedule = ['', 'weekly', 'monthly']
            prefix = ['', 'weekly', 'monthly']
        else:
            hostname = '10.10.10.10'
            username = 'admin'
            password = 'password'
            vserver = 'ansible'
            policy_name = 'ansible'
            policy_type = 'async_mirror'
            comment = 'created by ansible'
            snapmirror_label = ['daily', 'weekly', 'monthly']
            keep = [7, 5, 12]
            schedule = ['', 'weekly', 'monthly']
            prefix = ['', 'weekly', 'monthly']

        args = dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'vserver': vserver,
            'policy_name': policy_name,
            'policy_type': policy_type,
            'comment': comment
        })

        if with_rules:
            args['snapmirror_label'] = snapmirror_label
            args['keep'] = keep
            args['schedule'] = schedule
            args['prefix'] = prefix

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
        ''' test get_snapmirror_policy for non-existent snapmirror policy'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = my_module()
        my_obj.server = self.server
        assert my_obj.get_snapmirror_policy is not None

    def test_ensure_get_called_existing(self):
        ''' test get_snapmirror_policy for existing snapmirror policy'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = my_module()
        my_obj.server = MockONTAPConnection(kind='snapmirror_policy')
        assert my_obj.get_snapmirror_policy()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.create_snapmirror_policy')
    def test_successful_create(self, snapmirror_create_policy):
        ''' creating snapmirror policy without rules and testing idempotency '''
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
        ''' creating snapmirror policy without rules via REST and testing idempotency '''
        data = self.set_default_args()
        data['use_rest'] = 'Always'
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock()
        my_obj.get_snapmirror_policy.side_effect = [None, SRR['get_snapmirror_policy']]
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

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.create_snapmirror_policy')
    def test_successful_create_with_rules(self, snapmirror_create_policy):
        ''' creating snapmirror policy with rules and testing idempotency '''
        data = self.set_default_args(use_rest='Never', with_rules=True)
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=None)
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        snapmirror_create_policy.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        data = self.set_default_args(use_rest='Never', with_rules=True)
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=SRR['get_snapmirror_policy_with_rules'])
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapmirror_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.modify_snapmirror_policy_rules')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.create_snapmirror_policy')
    def test_successful_create_with_rules_via_rest(self, snapmirror_create_policy, modify_snapmirror_policy_rules):
        ''' creating snapmirror policy with rules via rest and testing idempotency '''
        data = self.set_default_args(use_rest='Always', with_rules=True)
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock()
        my_obj.get_snapmirror_policy.side_effect = [None, SRR['get_snapmirror_policy']]
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        snapmirror_create_policy.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        data = self.set_default_args(use_rest='Always', with_rules=True)
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=SRR['get_snapmirror_policy_with_rules'])
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.delete_snapmirror_policy')
    def test_successful_delete(self, delete_snapmirror_policy):
        ''' deleting snapmirror policy and testing idempotency '''
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
        ''' deleting snapmirror policy via REST and testing idempotency '''
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
        delete_snapmirror_policy.assert_called_with('abcdef12-3456-7890-abcd-ef1234567890')
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=None)
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.modify_snapmirror_policy')
    def test_successful_modify(self, snapmirror_policy_modify):
        ''' modifying snapmirror policy without rules and testing idempotency '''
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
        ''' modifying snapmirror policy without rules via REST and testing idempotency '''
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
        snapmirror_policy_modify.assert_called_with('abcdef12-3456-7890-abcd-ef1234567890', 'async_mirror')
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

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.modify_snapmirror_policy')
    def test_successful_modify_with_rules(self, snapmirror_policy_modify):
        ''' modifying snapmirror policy with rules and testing idempotency '''
        data = self.set_default_args(use_rest='Never', with_rules=True)
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=SRR['get_snapmirror_policy'])
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapmirror_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        snapmirror_policy_modify.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        data = self.set_default_args(use_rest='Never', with_rules=True)
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=SRR['get_snapmirror_policy_with_rules'])
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapmirror_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.modify_snapmirror_policy_rules')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy.NetAppOntapSnapMirrorPolicy.modify_snapmirror_policy')
    def test_successful_modify_with_rules_via_rest(self, snapmirror_policy_modify, modify_snapmirror_policy_rules):
        ''' modifying snapmirror policy with rules via rest and testing idempotency '''
        data = self.set_default_args(use_rest='Always', with_rules=True)
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=SRR['get_snapmirror_policy'])
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        snapmirror_policy_modify.assert_called_with('abcdef12-3456-7890-abcd-ef1234567890', 'async_mirror')
        # to reset na_helper from remembering the previous 'changed' value
        data = self.set_default_args(use_rest='Always', with_rules=True)
        set_module_args(data)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        my_obj.get_snapmirror_policy = Mock(return_value=SRR['get_snapmirror_policy_with_rules'])
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

    def test_create_snapmirror_policy_retention_obj_for_rest(self):
        ''' test create_snapmirror_policy_retention_obj_for_rest '''
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = my_module()

        # Test no rules
        self.assertEqual(my_obj.create_snapmirror_policy_retention_obj_for_rest(), [])

        # Test one rule
        rules = [{'snapmirror_label': 'daily', 'keep': 7}]
        retention_obj = [{'label': 'daily', 'count': '7'}]
        self.assertEqual(my_obj.create_snapmirror_policy_retention_obj_for_rest(rules), retention_obj)

        # Test two rules, with a prefix
        rules = [{'snapmirror_label': 'daily', 'keep': 7},
                 {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly'}]
        retention_obj = [{'label': 'daily', 'count': '7'},
                         {'label': 'weekly', 'count': '5', 'prefix': 'weekly'}]
        self.assertEqual(my_obj.create_snapmirror_policy_retention_obj_for_rest(rules), retention_obj)

        # Test three rules, with a prefix & schedule
        rules = [{'snapmirror_label': 'daily', 'keep': 7},
                 {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly_sv'},
                 {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly_sv', 'schedule': 'monthly'}]
        retention_obj = [{'label': 'daily', 'count': '7'},
                         {'label': 'weekly', 'count': '5', 'prefix': 'weekly_sv'},
                         {'label': 'monthly', 'count': '12', 'prefix': 'monthly_sv', 'creation_schedule': {'name': 'monthly'}}]
        self.assertEqual(my_obj.create_snapmirror_policy_retention_obj_for_rest(rules), retention_obj)

    def test_identify_snapmirror_policy_rules_with_schedule(self):
        ''' test identify_snapmirror_policy_rules_with_schedule '''
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = my_module()

        # Test no rules
        self.assertEqual(my_obj.identify_snapmirror_policy_rules_with_schedule(), ([], []))

        # Test one non-schedule rule identified
        rules = [{'snapmirror_label': 'daily', 'keep': 7}]
        schedule_rules = []
        non_schedule_rules = [{'snapmirror_label': 'daily', 'keep': 7}]
        self.assertEqual(my_obj.identify_snapmirror_policy_rules_with_schedule(rules), (schedule_rules, non_schedule_rules))

        # Test one schedule and two non-schedule rules identified
        rules = [{'snapmirror_label': 'daily', 'keep': 7},
                 {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly_sv'},
                 {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly_sv', 'schedule': 'monthly'}]
        schedule_rules = [{'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly_sv', 'schedule': 'monthly'}]
        non_schedule_rules = [{'snapmirror_label': 'daily', 'keep': 7},
                              {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly_sv'}]
        self.assertEqual(my_obj.identify_snapmirror_policy_rules_with_schedule(rules), (schedule_rules, non_schedule_rules))

        # Test three schedule & zero non-schedule rules identified
        rules = [{'snapmirror_label': 'daily', 'keep': 7, 'schedule': 'daily'},
                 {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly_sv', 'schedule': 'weekly'},
                 {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly_sv', 'schedule': 'monthly'}]
        schedule_rules = [{'snapmirror_label': 'daily', 'keep': 7, 'schedule': 'daily'},
                          {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly_sv', 'schedule': 'weekly'},
                          {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly_sv', 'schedule': 'monthly'}]
        non_schedule_rules = []
        self.assertEqual(my_obj.identify_snapmirror_policy_rules_with_schedule(rules), (schedule_rules, non_schedule_rules))

    def test_identify_new_snapmirror_policy_rules(self):
        ''' test identify_new_snapmirror_policy_rules '''

        # Test with no rules in parameters. new_rules should always be [].
        data = self.set_default_args(use_rest='Never', with_rules=False)
        set_module_args(data)
        my_obj = my_module()

        current = None
        new_rules = []
        self.assertEqual(my_obj.identify_new_snapmirror_policy_rules(current), new_rules)

        current = {'snapmirror_label': ['daily'], 'keep': [7], 'prefix': [''], 'schedule': ['']}
        new_rules = []
        self.assertEqual(my_obj.identify_new_snapmirror_policy_rules(current), new_rules)

        # Test with rules in parameters.
        data = self.set_default_args(use_rest='Never', with_rules=True)
        set_module_args(data)
        my_obj = my_module()

        # Test three new rules identified when no rules currently exist
        current = None
        new_rules = [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''},
                     {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'},
                     {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'}]
        self.assertEqual(my_obj.identify_new_snapmirror_policy_rules(current), new_rules)

        # Test two new rules identified and one rule already exists
        current = {'snapmirror_label': ['daily'], 'keep': [7], 'prefix': [''], 'schedule': ['']}
        new_rules = [{'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'},
                     {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'}]
        self.assertEqual(my_obj.identify_new_snapmirror_policy_rules(current), new_rules)

        # Test one new rule identified and two rules already exist
        current = {'snapmirror_label': ['daily', 'monthly'],
                   'keep': [7, 12],
                   'prefix': ['', 'monthly'],
                   'schedule': ['', 'monthly']}
        new_rules = [{'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'}]
        self.assertEqual(my_obj.identify_new_snapmirror_policy_rules(current), new_rules)

        # Test no new rules identified as all rules already exist
        current = {'snapmirror_label': ['daily', 'monthly', 'weekly'],
                   'keep': [7, 12, 5],
                   'prefix': ['', 'monthly', 'weekly'],
                   'schedule': ['', 'monthly', 'weekly']}
        new_rules = []
        self.assertEqual(my_obj.identify_new_snapmirror_policy_rules(current), new_rules)

    def test_identify_obsolete_snapmirror_policy_rules(self):
        ''' test identify_obsolete_snapmirror_policy_rules '''

        # Test with no rules in parameters. obsolete_rules should always be [].
        data = self.set_default_args(use_rest='Never', with_rules=False)
        set_module_args(data)
        my_obj = my_module()

        current = None
        obsolete_rules = []
        self.assertEqual(my_obj.identify_obsolete_snapmirror_policy_rules(current), obsolete_rules)

        current = {'snapmirror_label': ['daily'], 'keep': [7], 'prefix': [''], 'schedule': ['']}
        obsolete_rules = []
        self.assertEqual(my_obj.identify_obsolete_snapmirror_policy_rules(current), obsolete_rules)

        # Test removing all rules. obsolete_rules should equal current.
        data = self.set_default_args(use_rest='Never', with_rules=False)
        data['snapmirror_label'] = []
        set_module_args(data)
        my_obj = my_module()

        current = {'snapmirror_label': ['monthly', 'weekly', 'hourly', 'daily', 'yearly'],
                   'keep': [12, 5, 24, 7, 7],
                   'prefix': ['monthly', 'weekly', '', '', 'yearly'],
                   'schedule': ['monthly', 'weekly', '', '', 'yearly']}
        obsolete_rules = [{'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'},
                          {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'},
                          {'snapmirror_label': 'hourly', 'keep': 24, 'prefix': '', 'schedule': ''},
                          {'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''},
                          {'snapmirror_label': 'yearly', 'keep': 7, 'prefix': 'yearly', 'schedule': 'yearly'}]
        self.assertEqual(my_obj.identify_obsolete_snapmirror_policy_rules(current), obsolete_rules)

        # Test with rules in parameters.
        data = self.set_default_args(use_rest='Never', with_rules=True)
        set_module_args(data)
        my_obj = my_module()

        # Test no rules exist, thus no obsolete rules
        current = None
        obsolete_rules = []
        self.assertEqual(my_obj.identify_obsolete_snapmirror_policy_rules(current), obsolete_rules)

        # Test new rules and one obsolete rule identified
        current = {'snapmirror_label': ['hourly'], 'keep': [24], 'prefix': [''], 'schedule': ['']}
        obsolete_rules = [{'snapmirror_label': 'hourly', 'keep': 24, 'prefix': '', 'schedule': ''}]
        self.assertEqual(my_obj.identify_obsolete_snapmirror_policy_rules(current), obsolete_rules)

        # Test new rules, with one retained and one obsolete rule identified
        current = {'snapmirror_label': ['hourly', 'daily'],
                   'keep': [24, 7],
                   'prefix': ['', ''],
                   'schedule': ['', '']}
        obsolete_rules = [{'snapmirror_label': 'hourly', 'keep': 24, 'prefix': '', 'schedule': ''}]
        self.assertEqual(my_obj.identify_obsolete_snapmirror_policy_rules(current), obsolete_rules)

        # Test new rules and two obsolete rules identified
        current = {'snapmirror_label': ['monthly', 'weekly', 'hourly', 'daily', 'yearly'],
                   'keep': [12, 5, 24, 7, 7],
                   'prefix': ['monthly', 'weekly', '', '', 'yearly'],
                   'schedule': ['monthly', 'weekly', '', '', 'yearly']}
        obsolete_rules = [{'snapmirror_label': 'hourly', 'keep': 24, 'prefix': '', 'schedule': ''},
                          {'snapmirror_label': 'yearly', 'keep': 7, 'prefix': 'yearly', 'schedule': 'yearly'}]
        self.assertEqual(my_obj.identify_obsolete_snapmirror_policy_rules(current), obsolete_rules)

    def test_identify_modified_snapmirror_policy_rules(self):
        ''' test identify_modified_snapmirror_policy_rules '''

        # Test with no rules in parameters. modified_rules & unmodified_rules should always be [].
        data = self.set_default_args(use_rest='Never', with_rules=False)
        data.pop('snapmirror_label', None)
        set_module_args(data)
        my_obj = my_module()

        current = None
        modified_rules, unmodified_rules = [], []
        self.assertEqual(my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules, unmodified_rules))

        current = {'snapmirror_label': ['daily'], 'keep': [14], 'prefix': ['daily'], 'schedule': ['daily']}
        modified_rules, unmodified_rules = [], []
        self.assertEqual(my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules, unmodified_rules))

        # Test removing all rules. modified_rules & unmodified_rules should be [].
        data = self.set_default_args(use_rest='Never', with_rules=False)
        data['snapmirror_label'] = []
        set_module_args(data)
        my_obj = my_module()
        current = {'snapmirror_label': ['monthly', 'weekly', 'hourly', 'daily', 'yearly'],
                   'keep': [12, 5, 24, 7, 7],
                   'prefix': ['monthly', 'weekly', '', '', 'yearly'],
                   'schedule': ['monthly', 'weekly', '', '', 'yearly']}
        modified_rules, unmodified_rules = [], []
        self.assertEqual(my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules, unmodified_rules))

        # Test with rules in parameters.
        data = self.set_default_args(use_rest='Never', with_rules=True)
        set_module_args(data)
        my_obj = my_module()

        # Test no rules exist, thus no modified & unmodified rules
        current = None
        modified_rules, unmodified_rules = [], []
        self.assertEqual(my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules, unmodified_rules))

        # Test new rules don't exist, thus no modified & unmodified rules
        current = {'snapmirror_label': ['hourly'], 'keep': [24], 'prefix': [''], 'schedule': ['']}
        modified_rules, unmodified_rules = [], []
        self.assertEqual(my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules, unmodified_rules))

        # Test daily & monthly modified, weekly unmodified
        current = {'snapmirror_label': ['hourly', 'daily', 'weekly', 'monthly'],
                   'keep': [24, 14, 5, 6],
                   'prefix': ['', 'daily', 'weekly', 'monthly'],
                   'schedule': ['', 'daily', 'weekly', 'monthly']}
        modified_rules = [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''},
                          {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'}]
        unmodified_rules = [{'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'}]
        self.assertEqual(my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules, unmodified_rules))

        # Test all rules modified
        current = {'snapmirror_label': ['daily', 'weekly', 'monthly'],
                   'keep': [14, 10, 6],
                   'prefix': ['', '', ''],
                   'schedule': ['daily', 'weekly', 'monthly']}
        modified_rules = [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''},
                          {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'},
                          {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'}]
        unmodified_rules = []
        self.assertEqual(my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules, unmodified_rules))

        # Test all rules unmodified
        current = {'snapmirror_label': ['daily', 'weekly', 'monthly'],
                   'keep': [7, 5, 12],
                   'prefix': ['', 'weekly', 'monthly'],
                   'schedule': ['', 'weekly', 'monthly']}
        modified_rules = []
        unmodified_rules = [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''},
                            {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'},
                            {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'}]
        self.assertEqual(my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules, unmodified_rules))
