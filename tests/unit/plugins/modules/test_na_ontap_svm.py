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
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_svm \
    import NetAppOntapSVM as svm_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=1, full='dummy_9_9_1')), None),
    'is_rest_96': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy_9_6_0')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {'num_records': 0}, None),
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
                                 "nfs": {"enabled": True, "allowed": True},
                                 "cifs": {"enabled": False},
                                 "iscsi": {"enabled": False},
                                 "fcp": {"enabled": False},
                                 "nvme": {"enabled": False}}]}, None),
    'svm_record_ap': (200,
                      {'records': [{"name": "test_svm",
                                    "aggregates": [{"name": "aggr_1",
                                                    "uuid": "850dd65b-8811-4611-ac8c-6f6240475ff9"},
                                                   {"name": "aggr_2",
                                                    "uuid": "850dd65b-8811-4611-ac8c-6f6240475ff9"}],
                                    "ipspace": {"name": "ansible_ipspace",
                                                "uuid": "2b760d31-8dfd-11e9-b162-005056b39fe7"},
                                    "snapshot_policy": {"uuid": "3b611707-8dfd-11e9-b162-005056b39fe7",
                                                        "name": "old_snapshot_policy"},
                                    "nfs": {"enabled": False},
                                    "cifs": {"enabled": True, "allowed": True},
                                    "iscsi": {"enabled": True, "allowed": True},
                                    "fcp": {"enabled": False},
                                    "nvme": {"enabled": False}}]}, None),
    'cli_record': (200,
                   {'records': [{"max_volumes": 100, "allowed_protocols": ['nfs', 'iscsi']}]}, None)
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
                'password': 'test_pass!',
                'use_rest': 'never'
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
            elif data is None:
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

    def test_successful_create_zapi(self):
        '''Test successful create'''
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_vserver_mock_object().apply()
        assert exc.value.args[0]['changed']

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
        self._modify_options_with_expected_change('state', 'absent')

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
        self._modify_options_with_expected_change('language', 'c')

    def test_successful_modify_snapshot_policy(self):
        '''Test successful modify language'''
        self._modify_options_with_expected_change(
            'snapshot_policy', 'new_snapshot_policy'
        )

    def test_successful_modify_allowed_protocols(self):
        '''Test successful modify allowed protocols'''
        self._modify_options_with_expected_change(
            'allowed_protocols', 'nvme,fcp'
        )

    def test_successful_modify_aggr_list(self):
        '''Test successful modify aggr-list'''
        self._modify_options_with_expected_change(
            'aggr_list', 'aggr_3,aggr_4'
        )

    def _modify_options_with_expected_change(self, arg0, arg1):
        data = self.mock_args()
        data[arg0] = arg1
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
        assert exc.value.args[0]['msg'] == 'calling: svm/svms: got %s.' % SRR['generic_error'][2]

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

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_get(self, mock_request):
        '''Test successful get'''
        data = self.mock_args(rest=True)
        data['language'] = 'c'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['svm_record'],      # get
            SRR['svm_record_ap'],   # get AP
            SRR['end_of_sequence']
        ]
        na_ontap_svm_object = self.get_vserver_mock_object(cx_type='rest')
        current = na_ontap_svm_object.get_vserver()
        print(current)
        assert current['services']['nfs']['allowed']
        assert not current['services']['cifs']['enabled']
        current = na_ontap_svm_object.get_vserver()
        print(current)
        assert not current['services']['nfs']['enabled']
        assert current['services']['cifs']['allowed']
        assert current['services']['iscsi']['allowed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_ignore_zapi_option(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['root_volume'] = 'whatever'
        data['aggr_list'] = '*'
        data['ignore_rest_unsupported_options'] = 'true'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # get
            SRR['empty_good'],  # post
            SRR['end_of_sequence']
        ]
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleExitJson) as exc:
            module.apply()
        assert exc.value.args[0]['changed']
        assert module.use_rest

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_with_service(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # get
            SRR['empty_good'],  # post
            SRR['end_of_sequence']
        ]
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleExitJson) as exc:
            module.apply()
        assert exc.value.args[0]['changed']
        assert module.use_rest

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_modify_with_service(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}, 'fcp': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['svm_record'],  # get
            SRR['empty_good'],  # patch svm for allowed
            SRR['empty_good'],  # post to enable fcp service
            SRR['end_of_sequence']
        ]
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleExitJson) as exc:
            module.apply()
        assert exc.value.args[0]['changed']
        assert module.use_rest
        expected = call('POST', 'protocols/san/fcp/services', {'return_timeout': 30}, json={'enabled': True, 'svm.name': 'test_svm'})
        print(mock_request.mock_calls)
        assert expected in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_enable_service(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # post to enable FCP
            SRR['end_of_sequence']
        ]
        # modify = {'enabled_protocols': ['nfs', 'fcp']}
        # current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
        modify = {'services': {'nfs': {'allowed': True}, 'fcp': {'enabled': True}}}
        current = {'services': {'nfs': {'allowed': True}}, 'uuid': 'uuid'}
        module = self.get_vserver_mock_object(cx_type='rest')
        module.modify_services(modify, current)
        expected = call('POST', 'protocols/san/fcp/services', {'return_timeout': 30}, json={'enabled': True, 'svm.name': 'test_svm'})
        print(mock_request.mock_calls)
        assert expected in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_reenable_service(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # patch to reenable FCP
            SRR['end_of_sequence']
        ]
        # modify = {'enabled_protocols': ['nfs', 'fcp']}
        fcp_dict = {'_links': {'self': {'href': 'fcp_link'}}}
        # current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid', 'fcp': fcp_dict}
        modify = {'services': {'nfs': {'allowed': True}, 'fcp': {'enabled': True}}}
        current = {'services': {'nfs': {'allowed': True}}, 'uuid': 'uuid', 'fcp': fcp_dict}
        module = self.get_vserver_mock_object(cx_type='rest')
        module.modify_services(modify, current)
        expected = call('PATCH', 'protocols/san/fcp/services/uuid', {'return_timeout': 30}, json={'enabled': True})
        print(mock_request.mock_calls)
        assert expected in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_enable_service(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # patch to reenable FCP
            SRR['end_of_sequence']
        ]
        # modify = {'enabled_protocols': ['nfs', 'bad_value']}
        # current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme']}
        modify = {'services': {'nfs': {'allowed': True}, 'bad_value': {'enabled': True}}, 'name': 'new_name'}
        current = {'services': {'nfs': {'allowed': True}}, 'uuid': 'uuid'}
        module = self.get_vserver_mock_object(cx_type='rest')
        module.enablable_protocols = ['nfs', 'bad_value']
        with pytest.raises(AnsibleFailJson) as exc:
            module.modify_services(modify, current)
        msg = 'Internal error, unexpecting service: bad_value.'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_modify_services(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],   # patch to reenable FCP
            SRR['end_of_sequence']
        ]
        # modify = {'enabled_protocols': ['nfs', 'fcp']}
        # current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
        modify = {'services': {'nfs': {'allowed': True}, 'fcp': {'enabled': True}}, 'name': 'new_name'}
        current = {'services': {'nfs': {'allowed': True}}, 'uuid': 'uuid'}
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleFailJson) as exc:
            module.modify_services(modify, current)
        msg = 'Error in modify service for fcp: calling: protocols/san/fcp/services: got Expected error.'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_modify_current_none(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        modify = {'enabled_protocols': ['nfs', 'fcp']}
        current = None
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleFailJson) as exc:
            module.modify_vserver(modify, current)
        msg = 'Internal error, expecting SVM object in modify.'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_modify_modify_none(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        modify = {}
        current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleFailJson) as exc:
            module.modify_vserver(modify, current)
        msg = 'Internal error, expecting something to modify in modify.'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_modify_error_1(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],   # patch to rename
            SRR['end_of_sequence']
        ]
        # modify = {'enabled_protocols': ['nfs', 'fcp'], 'name': 'new_name'}
        # current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
        modify = {'services': {'nfs': {'allowed': True}, 'fcp': {'allowed': True}}, 'name': 'new_name'}
        current = {'services': {'nfs': {'allowed': True}}, 'uuid': 'uuid'}
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleFailJson) as exc:
            module.modify_vserver(modify, current)
        msg = 'Error in rename: calling: svm/svms/uuid: got Expected error.'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_modify_error_2(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        data['language'] = 'klingon'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],      # patch to rename
            SRR['generic_error'],   # patch for other options
            SRR['end_of_sequence']
        ]
        modify = {'enabled_protocols': ['nfs', 'fcp'], 'name': 'new_name', 'language': 'klingon'}
        current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleFailJson) as exc:
            module.modify_vserver(modify, current)
        msg = 'Error in modify: calling: svm/svms/uuid: got Expected error.'
        assert exc.value.args[0]['msg'] == msg
        # print(mock_request.mock_calls)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_get_older_rest(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_96'],
            SRR['svm_record'],          # get
            SRR['empty_good'],          # get using REST CLI
            SRR['end_of_sequence']
        ]
        module = self.get_vserver_mock_object(cx_type='rest')
        details = module.get_vserver()
        expected = call('GET', 'private/cli/vserver', {'fields': 'allowed_protocols', 'vserver': 'test_svm'})
        print(mock_request.mock_calls)
        print(details)
        assert expected in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_add_protocols_on_create(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_96'],
            SRR['empty_good'],          # get
            SRR['empty_good'],          # POST for create
            SRR['empty_good'],          # PATCH for add-protocols
            SRR['end_of_sequence']
        ]
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleExitJson) as exc:
            module.apply()
        expected = call('PATCH', 'private/cli/vserver/add-protocols', {'return_timeout': 30, 'vserver': 'test_svm'}, json={'protocols': ['nfs']})
        print(mock_request.mock_calls)
        assert expected in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_add_remove_protocols_on_modify(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}, 'iscsi': {'allowed': False}, 'fcp': {'allowed': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_96'],
            SRR['svm_record'],          # get
            SRR['cli_record'],          # get for protocols
            SRR['empty_good'],          # PATCH for add-protocols
            SRR['empty_good'],          # PATCH for remove-protocols
            SRR['end_of_sequence']
        ]
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleExitJson) as exc:
            module.apply()
        print(mock_request.mock_calls)
        expected = call('PATCH', 'private/cli/vserver/add-protocols', {'return_timeout': 30, 'vserver': 'test_svm'}, json={'protocols': ['fcp']})
        assert expected in mock_request.mock_calls
        expected = call('PATCH', 'private/cli/vserver/remove-protocols', {'return_timeout': 30, 'vserver': 'test_svm'}, json={'protocols': ['iscsi']})
        assert expected in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_add_remove_protocols_on_modify_old_style(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['allowed_protocols'] = ['nfs', 'fcp']
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_96'],
            SRR['svm_record'],          # get
            SRR['cli_record'],          # get for protocols
            SRR['empty_good'],          # PATCH for add-protocols
            SRR['empty_good'],          # PATCH for remove-protocols
            SRR['end_of_sequence']
        ]
        module = self.get_vserver_mock_object(cx_type='rest')
        with pytest.raises(AnsibleExitJson) as exc:
            module.apply()
        print(mock_request.mock_calls)
        expected = call('PATCH', 'private/cli/vserver/add-protocols', {'return_timeout': 30, 'vserver': 'test_svm'}, json={'protocols': ['fcp']})
        assert expected in mock_request.mock_calls
        expected = call('PATCH', 'private/cli/vserver/remove-protocols', {'return_timeout': 30, 'vserver': 'test_svm'}, json={'protocols': ['iscsi']})
        assert expected in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_validate_int_or_string_as_int(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        modify = {}
        current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
        module = self.get_vserver_mock_object(cx_type='rest')
        module.validate_int_or_string('10', 'whatever')

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_validate_int_or_string_as_str(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        modify = {}
        current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
        module = self.get_vserver_mock_object(cx_type='rest')
        module.validate_int_or_string('whatever', 'whatever')

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_validate_int_or_string(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['services'] = {'nfs': {'allowed': True, 'enabled': True}}
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        modify = {}
        current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
        module = self.get_vserver_mock_object(cx_type='rest')
        astring = 'testme'
        with pytest.raises(AnsibleFailJson) as exc:
            module.validate_int_or_string('10a', astring)
        msg = "expecting int value or '%s'" % astring
        assert msg in exc.value.args[0]['msg']
