# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_autosupport_invoke '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_autosupport_invoke \
    import NetAppONTAPasupInvoke as invoke_module  # module under test

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error")
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

    def invoke_successfully(self, xml, enable_tunneling):
        raise netapp_utils.zapi.NaApiError('test', 'Expected error')


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_wwpn_alias '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_invoke = {
            'name': 'test_node',
            'message': 'test_message',
            'type': 'all'
        }

    def mock_args(self):
        return {
            'message': self.mock_invoke['message'],
            'name': self.mock_invoke['name'],
            'type': self.mock_invoke['type'],
            'hostname': 'test_host',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_invoke_mock_object(self, use_rest=True):
        invoke_obj = invoke_module()
        if not use_rest:
            invoke_obj.ems_log_event = Mock()
            invoke_obj.server = MockONTAPConnection()
        return invoke_obj

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_send(self, mock_request):
        '''Test successful send message'''
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_invoke_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_send_error(self, mock_request):
        '''Test rest send error'''
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_invoke_mock_object().apply()
        msg = "Error on sending autosupport message to node %s: Expected error." % data['name']
        assert exc.value.args[0]['msg'] == msg

    def test_zapi_send_error(self):
        '''Test rest send error'''
        data = self.mock_args()
        data['use_rest'] = 'Never'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_invoke_mock_object(use_rest=False).apply()
        msg = "Error on sending autosupport message to node %s: NetApp API failed. Reason - test:Expected error." % data['name']
        assert exc.value.args[0]['msg'] == msg
