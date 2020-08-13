# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_svm \
    import NetAppOntapSVM as svm_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'svm_record': (200,
                   {'records': [{"uuid": "09e9fd5e-8ebd-11e9-b162-005056b39fe7",
                                 "name": "test_svm",
                                 "subtype": "default",
                                 "language": "c.utf_8",
                                 "aggregates": [{"name": "aggr_1",
                                                 "uuid": "850dd65b-8811-4611-ac8c-6f6240475ff9"},
                                                {"name": "aggr_2",
                                                 "uuid": "850dd65b-8811-4611-ac8c-6f6240475ff9"}],
                                 "comment": "new comment",
                                 "ipspace": {"name": "ansible_ipspace",
                                             "uuid": "2b760d31-8dfd-11e9-b162-005056b39fe7"},
                                 "snapshot_policy": {"uuid": "3b611707-8dfd-11e9-b162-005056b39fe7",
                                                     "name": "old_snapshot_policy"},
                                 "nfs": {"enabled": True},
                                 "cifs": {"enabled": False},
                                 "iscsi": {"enabled": False},
                                 "fcp": {"enabled": False},
                                 "nvme": {"enabled": False}}]}, None)
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

    def __init__(self, kind=None, data=None):
        ''' save arguments '''
        self.type = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'vserver':
            xml = self.build_vserver_info(self.params)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_vserver_info(vserver):
        ''' build xml data for vserser-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1, 'attributes-list': {'vserver-info': {
            'vserver-name': vserver['name'],
            'ipspace': vserver['ipspace'],
            'root-volume': vserver['root_volume'],
            'root-volume-aggregate': vserver['root_volume_aggregate'],
            'language': vserver['language'],
            'comment': vserver['comment'],
            'snapshot-policy': vserver['snapshot_policy'],
            'vserver-subtype': vserver['subtype'],
            'allowed-protocols': [{'protocol': 'nfs'}, {'protocol': 'cifs'}],
            'aggr-list': [{'aggr-name': 'aggr_1'}, {'aggr-name': 'aggr_2'}],
        }}}
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
        self.mock_vserver = {
            'name': 'test_svm',
            'root_volume': 'ansible_vol',
            'root_volume_aggregate': 'ansible_aggr',
            'aggr_list': 'aggr_1,aggr_2',
            'ipspace': 'ansible_ipspace',
            'subtype': 'default',
            'language': 'c.utf_8',
            'snapshot_policy': 'old_snapshot_policy',
            'comment': 'new comment'
        }

    def mock_args(self, rest=False):
        if rest:
            return {'name': self.mock_vserver['name'],
                    'aggr_list': self.mock_vserver['aggr_list'],
                    'ipspace': self.mock_vserver['ipspace'],
                    'comment': self.mock_vserver['comment'],
                    'subtype': 'default',
                    'hostname': 'test',
                    'username': 'test_user',
                    'password': 'test_pass!'}
        else:
            return {
                'name': self.mock_vserver['name'],
                'root_volume': self.mock_vserver['root_volume'],
                'root_volume_aggregate': self.mock_vserver['root_volume_aggregate'],
                'aggr_list': self.mock_vserver['aggr_list'],
                'ipspace': self.mock_vserver['ipspace'],
                'comment': self.mock_vserver['comment'],
                'subtype': 'default',
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!'
            }

    def get_vserver_mock_object(self, kind=None, data=None, cx_type='zapi'):
        """
        Helper method to return an na_ontap_volume object
        :param kind: passes this param to MockONTAPConnection()
        :param data: passes this param to MockONTAPConnection()
        :return: na_ontap_volume object
        """
        vserver_obj = svm_module()
        if cx_type == 'zapi':
            vserver_obj.asup_log_for_cserver = Mock(return_value=None)
            vserver_obj.cluster = Mock()
            vserver_obj.cluster.invoke_successfully = Mock()
            if kind is None:
                vserver_obj.server = MockONTAPConnection()
            else:
                if data is None:
                    vserver_obj.server = MockONTAPConnection(kind='vserver', data=self.mock_vserver)
                else:
                    vserver_obj.server = MockONTAPConnection(kind='vserver', data=data)
        return vserver_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            svm_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_nonexistent_vserver(self):
        ''' test if get_vserver() throws an error if vserver is not specified '''
        data = self.mock_args()
        set_module_args(data)
        result = self.get_vserver_mock_object().get_vserver()
        assert result is None

    def test_create_error_missing_name(self):
        ''' Test if create throws an error if name is not specified'''
        data = self.mock_args()
        del data['name']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_vserver_mock_object('vserver').create_vserver()
        msg = 'missing required arguments: name'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_svm.NetAppOntapSVM.create_vserver')
    def test_successful_create(self, create_vserver):
        '''Test successful create'''
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object().apply()
        assert exc.value.args[0]['changed']
        create_vserver.assert_called_with()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_svm.NetAppOntapSVM.create_vserver')
    def test_create_idempotency(self, create_vserver):
        '''Test successful create'''
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object('vserver').apply()
        assert not exc.value.args[0]['changed']
        create_vserver.assert_not_called()

    def test_successful_delete(self):
        '''Test successful delete'''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object('vserver').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_svm.NetAppOntapSVM.delete_vserver')
    def test_delete_idempotency(self, delete_vserver):
        '''Test delete idempotency'''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object().apply()
        assert not exc.value.args[0]['changed']
        delete_vserver.assert_not_called()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_svm.NetAppOntapSVM.get_vserver')
    def test_successful_rename(self, get_vserver):
        '''Test successful rename'''
        data = self.mock_args()
        data['from_name'] = 'test_svm'
        data['name'] = 'test_new_svm'
        set_module_args(data)
        current = {
            'name': 'test_svm',
            'root_volume': 'ansible_vol',
            'root_volume_aggregate': 'ansible_aggr',
            'ipspace': 'ansible_ipspace',
            'subtype': 'default',
            'language': 'c.utf_8'
        }
        get_vserver.side_effect = [
            None,
            current
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_successful_modify_language(self):
        '''Test successful modify language'''
        data = self.mock_args()
        data['language'] = 'c'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object('vserver').apply()
        assert exc.value.args[0]['changed']

    def test_successful_modify_snapshot_policy(self):
        '''Test successful modify language'''
        data = self.mock_args()
        data['snapshot_policy'] = 'new_snapshot_policy'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object('vserver').apply()
        assert exc.value.args[0]['changed']

    def test_successful_modify_allowed_protocols(self):
        '''Test successful modify allowed protocols'''
        data = self.mock_args()
        data['allowed_protocols'] = 'protocol_1,protocol_2'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object('vserver').apply()
        assert exc.value.args[0]['changed']

    def test_successful_modify_aggr_list(self):
        '''Test successful modify aggr-list'''
        data = self.mock_args()
        data['aggr_list'] = 'aggr_3,aggr_4'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object('vserver').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_vserver_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_unsupported_parm(self, mock_request):
        data = self.mock_args(rest=True)
        data['use_rest'] = 'Always'
        data['root_volume'] = 'not_supported_by_rest'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_vserver_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == "REST API currently does not support 'root_volume'"

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # get
            SRR['empty_good'],  # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_create_idempotency(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['svm_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_delete(self, mock_request):
        '''Test successful delete'''
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['svm_record'],  # get
            SRR['empty_good'],  # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_delete_idempotency(self, mock_request):
        '''Test delete idempotency'''
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_rename(self, mock_request):
        '''Test successful rename'''
        data = self.mock_args(rest=True)
        data['from_name'] = 'test_svm'
        data['name'] = 'test_new_svm'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['svm_record'],  # get
            SRR['svm_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_modify_language(self, mock_request):
        '''Test successful modify language'''
        data = self.mock_args(rest=True)
        data['language'] = 'c'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['svm_record'],  # get
            SRR['svm_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']
