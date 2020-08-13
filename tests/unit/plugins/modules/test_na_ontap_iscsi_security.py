# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_iscsi_security '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_iscsi_security \
    import NetAppONTAPIscsiSecurity as iscsi_module  # module under test

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'get_uuid': (
        200,
        {
            "records": [
                {
                    "uuid": "e2e89ccc-db35-11e9-0000-000000000000"
                }
            ],
            "num_records": 1
        }, None),
    'get_initiator': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "e2e89ccc-db35-11e9-0000-000000000000",
                        "name": "test_ansible"
                    },
                    "initiator": "eui.0123456789abcdef",
                    "authentication_type": "chap",
                    "chap": {
                        "inbound": {
                            "user": "test_user_1"
                        },
                        "outbound": {
                            "user": "test_user_2"
                        }
                    },
                    "initiator_address": {
                        "ranges": [
                            {
                                "start": "10.125.10.0",
                                "end": "10.125.10.10",
                                "family": "ipv4"
                            },
                            {
                                "start": "10.10.10.7",
                                "end": "10.10.10.7",
                                "family": "ipv4"
                            }
                        ]
                    }
                }
            ],
            "num_records": 1
        }, None),
    "no_record": (
        200,
        {
            "num_records": 0
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


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_iscsi_security '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_iscsi = {
            "initiator": "eui.0123456789abcdef",
            "inbound_username": "test_user_1",
            "inbound_password": "123",
            "outbound_username": "test_user_2",
            "outbound_password": "321",
            "auth_type": "chap",
            "address_ranges": ["10.125.10.0-10.125.10.10", "10.10.10.7"]
        }

    def mock_args(self):
        return {
            'initiator': self.mock_iscsi['initiator'],
            'inbound_username': self.mock_iscsi['inbound_username'],
            'inbound_password': self.mock_iscsi['inbound_password'],
            'outbound_username': self.mock_iscsi['outbound_username'],
            'outbound_password': self.mock_iscsi['outbound_password'],
            'auth_type': self.mock_iscsi['auth_type'],
            'address_ranges': self.mock_iscsi['address_ranges'],
            'hostname': 'test',
            'vserver': 'test_vserver',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_iscsi_mock_object(self):
        """
        Helper method to return an na_ontap_iscsi_security object
        :return: na_ontap_iscsi_security object
        """
        iscsi_obj = iscsi_module()
        return iscsi_obj

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['get_uuid'],
            SRR['no_record'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_iscsi_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_create_idempotency(self, mock_request):
        '''Test rest create idempotency'''
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['get_uuid'],
            SRR['get_initiator'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_iscsi_mock_object().apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_modify_address(self, mock_request):
        '''Test successful rest modify'''
        data = self.mock_args()
        data['address_ranges'] = ['10.10.10.8']
        set_module_args(data)
        mock_request.side_effect = [
            SRR['get_uuid'],
            SRR['get_initiator'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_iscsi_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_modify_user(self, mock_request):
        '''Test successful rest modify'''
        data = self.mock_args()
        data['inbound_username'] = 'test_user_3'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['get_uuid'],
            SRR['get_initiator'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_iscsi_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        '''Test rest error'''
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['get_uuid'],
            SRR['no_record'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_iscsi_mock_object().apply()
        assert 'Error on creating initiator: Expected error' in exc.value.args[0]['msg']

        data = self.mock_args()
        data['inbound_username'] = 'test_user_3'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['get_uuid'],
            SRR['get_initiator'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_iscsi_mock_object().apply()
        assert 'Error on modifying initiator: Expected error' in exc.value.args[0]['msg']

        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['get_uuid'],
            SRR['get_initiator'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_iscsi_mock_object().apply()
        assert 'Error on deleting initiator: Expected error' in exc.value.args[0]['msg']
