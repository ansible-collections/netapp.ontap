''' unit tests ONTAP Ansible module: na_ontap_fpolicy_policy '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_policy \
    import NetAppOntapFpolicyPolicy as fpolicy_policy_module  # module under test


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Ooops, the UT needs one more SRR response"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'fpolicy_policy_record': (200, {
        "records": [{
            "vserver": "svm1",
            "policy_name": "policy1",
            "events": ['my_event'],
            "engine": "native",
            "is_mandatory": False,
            "allow_privileged_access": False,
            "is_passthrough_read_enabled": False
        }]
    }, None)
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

    def __init__(self, kind=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'fpolicy_policy':
            xml = self.build_fpolicy_policy_info()
        elif self.type == 'fpolicy_policy_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_fpolicy_policy_info():
        ''' build xml data for fpolicy-policy-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes-list': {
                'fpolicy-policy-info': {
                    "vserver": "svm1",
                    "policy-name": "policy1",
                    "events": [
                        {'event-name': 'my_event'}
                    ],
                    "engine-name": "native",
                    "is-mandatory": "False",
                    "allow-privileged-access": "False",
                    "is-passthrough-read-enabled": "False"
                }
            }
        }
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

    def set_default_args(self, use_rest=None):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'svm1'
            name = 'policy1'
            events = 'my_event'
            is_mandatory = False

        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'svm1'
            name = 'policy1'
            events = 'my_event'
            is_mandatory = False

        args = dict({
            'state': 'present',
            'hostname': hostname,
            'username': username,
            'password': password,
            'vserver': vserver,
            'name': name,
            'events': events,
            'is_mandatory': is_mandatory
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_fpolicy_policy_mock_object(cx_type='zapi', kind=None):
        fpolicy_policy_obj = fpolicy_policy_module()
        if cx_type == 'zapi':
            if kind is None:
                fpolicy_policy_obj.server = MockONTAPConnection()
            else:
                fpolicy_policy_obj.server = MockONTAPConnection(kind=kind)
        return fpolicy_policy_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            fpolicy_policy_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_fpolicy_policy for non-existent config'''
        set_module_args(self.set_default_args(use_rest='Never'))
        print('starting')
        my_obj = fpolicy_policy_module()
        print('use_rest:', my_obj.use_rest)
        my_obj.server = self.server
        assert my_obj.get_fpolicy_policy is not None

    def test_ensure_get_called_existing(self):
        ''' test get_fpolicy_policy_config for existing config'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = fpolicy_policy_module()
        my_obj.server = MockONTAPConnection(kind='fpolicy_policy')
        assert my_obj.get_fpolicy_policy()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_policy.NetAppOntapFpolicyPolicy.create_fpolicy_policy')
    def test_successful_create(self, create_fpolicy_policy):
        ''' creating fpolicy_policy and test idempotency '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = fpolicy_policy_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        create_fpolicy_policy.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = fpolicy_policy_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('fpolicy_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_policy.NetAppOntapFpolicyPolicy.delete_fpolicy_policy')
    def test_successful_delete(self, delete_fpolicy_policy):
        ''' delete fpolicy_policy and test idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = fpolicy_policy_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('fpolicy_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = fpolicy_policy_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_policy.NetAppOntapFpolicyPolicy.modify_fpolicy_policy')
    def test_successful_modify(self, modify_fpolicy_policy):
        ''' modifying fpolicy_policy config and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['is_mandatory'] = True
        set_module_args(data)
        my_obj = fpolicy_policy_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('fpolicy_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # to reset na_helper from remembering the previous 'changed' value
        data['is_mandatory'] = False
        set_module_args(data)
        my_obj = fpolicy_policy_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('fpolicy_policy')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = fpolicy_policy_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('fpolicy_policy_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_fpolicy_policy()
        assert 'Error creating fPolicy policy ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.delete_fpolicy_policy()
        assert 'Error deleting fPolicy policy ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_fpolicy_policy(modify={})
        assert 'Error modifying fPolicy policy ' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_fpolicy_policy_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_create_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_policy_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_create_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['fpolicy_policy_record'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_policy_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_delete_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['fpolicy_policy_record'],  # get
            SRR['empty_good'],  # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_policy_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_delete_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_policy_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['is_mandatory'] = 'True'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['fpolicy_policy_record'],  # get
            SRR['empty_good'],  # no response for modify
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_policy_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['is_mandatory'] = False
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['fpolicy_policy_record'],  # get
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_fpolicy_policy_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']
