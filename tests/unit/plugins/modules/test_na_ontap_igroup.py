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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_igroup \
    import NetAppOntapIgroup as igroup  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_rest_9_9_0': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_9_1': (200, dict(version=dict(generation=9, major=9, minor=1, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'one_igroup_record': (200, dict(records=[
        dict(uuid='a1b2c3',
             name='test',
             svm=dict(name='vserver'),
             protocol='fcp',
             os_type='aix')
    ], num_records=1), None),
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
        self.kind = kind
        self.data = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.kind == 'igroup':
            xml = self.build_igroup()
        if self.kind == 'igroup_no_initiators':
            xml = self.build_igroup_no_initiators()
        self.xml_out = xml
        return xml

    @staticmethod
    def build_igroup():
        ''' build xml data for initiator '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'vserver': 'vserver',
                'initiator-group-os-type': 'linux',
                'initiator-group-info': {
                    'initiators': [
                        {
                            'initiator-info': {
                                'initiator-name': 'init1'
                            }},
                        {
                            'initiator-info': {
                                'initiator-name': 'init2'
                            }}
                    ]
                }
            }
        }
        xml.translate_struct(attributes)
        return xml

    @staticmethod
    def build_igroup_no_initiators():
        ''' build xml data for igroup with no initiators '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'initiator-group-info': {
                    'vserver': 'test'
                }
            }
        }
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.warnings = list()

        def log(other_self, msg, log_args=None):  # pylint: disable=unused-argument
            if msg.startswith('Invoked with'):
                return
            self.warnings.append(msg)

        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json,
                                                 log=log)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.server = MockONTAPConnection()

    def mock_args(self, use_rest='never'):
        return {
            'vserver': 'vserver',
            'name': 'test',
            'initiator_names': 'init1',
            'ostype': 'linux',
            'initiator_group_type': 'fcp',
            'bind_portset': 'true',
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'use_rest': use_rest
        }

    def get_igroup_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_igroup object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_igroup object
        """
        obj = igroup()
        obj.autosupport_log = Mock(return_value=None)
        if kind is None:
            obj.server = MockONTAPConnection()
        else:
            obj.server = MockONTAPConnection(kind=kind)
        return obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            igroup()
        msg = 'missing required arguments:'
        assert msg in exc.value.args[0]['msg']

    def test_get_nonexistent_igroup(self):
        ''' Test if get_igroup returns None for non-existent igroup '''
        data = self.mock_args()
        set_module_args(data)
        result = self.get_igroup_mock_object().get_igroup('dummy')
        assert result is None

    def test_get_existing_igroup_with_initiators(self):
        ''' Test if get_igroup returns list of existing initiators '''
        data = self.mock_args()
        set_module_args(data)
        result = self.get_igroup_mock_object('igroup').get_igroup(data['name'])
        assert data['initiator_names'] in result['initiator_names']
        assert result['initiator_names'] == ['init1', 'init2']

    def test_get_existing_igroup_without_initiators(self):
        ''' Test if get_igroup returns empty list() '''
        data = self.mock_args()
        set_module_args(data)
        result = self.get_igroup_mock_object('igroup_no_initiators').get_igroup(data['name'])
        assert result['initiator_names'] == []

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_igroup.NetAppOntapIgroup.add_initiators_or_igroups')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_igroup.NetAppOntapIgroup.remove_initiators_or_igroups')
    def test_modify_initiator_calls_add_and_remove(self, remove, add):
        '''Test remove_initiator() is called followed by add_initiator() on modify operation'''
        data = self.mock_args()
        data['initiator_names'] = 'replacewithme'
        set_module_args(data)
        obj = self.get_igroup_mock_object('igroup')
        with pytest.raises(AnsibleExitJson) as exc:
            current = obj.get_igroup(data['name'])
            obj.apply()
        remove.assert_called_with(None, 'initiator_names', current['initiator_names'], {})
        add.assert_called_with(None, 'initiator_names', current['initiator_names'])
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_igroup.NetAppOntapIgroup.modify_initiator')
    def test_modify_called_from_add(self, modify):
        '''Test remove_initiator() and add_initiator() calls modify'''
        data = self.mock_args()
        data['initiator_names'] = 'replacewithme'
        add = 'igroup-add'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_igroup_mock_object('igroup_no_initiators').apply()
        modify.assert_called_with('replacewithme', add)
        assert modify.call_count == 1      # remove nothing, add 1 new
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_igroup.NetAppOntapIgroup.modify_initiator')
    def test_modify_called_from_remove(self, modify):
        '''Test remove_initiator() and add_initiator() calls modify'''
        data = self.mock_args()
        data['initiator_names'] = ''
        remove = 'igroup-remove'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_igroup_mock_object('igroup').apply()
        modify.assert_called_with('init2', remove)
        assert modify.call_count == 2  # remove existing 2, add nothing
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_igroup.NetAppOntapIgroup.add_initiators_or_igroups')
    def test_successful_create(self, add):
        ''' Test successful create '''
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_igroup_mock_object().apply()
        assert exc.value.args[0]['changed']
        add.assert_called_with(None, 'initiator_names', [])

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_create_rest(self, mock_request):
        ''' Test successful create '''
        set_module_args(self.mock_args('always'))
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],     # get
            SRR['empty_good'],      # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            igroup().apply()
        assert exc.value.args[0]['changed']

    def test_successful_delete(self):
        ''' Test successful delete '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_igroup_mock_object('igroup').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_incomplete_record_rest(self, mock_request):
        ''' Test successful create '''
        set_module_args(self.mock_args('always'))
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['one_record_uuid'],     # get
            SRR['empty_good'],          # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            igroup().apply()
        msg = 'Error: unexpected igroup body:'
        assert msg in exc.value.args[0]['msg']
        msg = "KeyError on 'name'"
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_delete_rest(self, mock_request):
        ''' Test successful delete '''
        data = dict(self.mock_args('always'))
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['one_igroup_record'],   # get
            SRR['empty_good'],          # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            igroup().apply()
        assert exc.value.args[0]['changed']
        expected_call = call('DELETE', 'protocols/san/igroups/a1b2c3', None, json=None)
        assert expected_call in mock_request.mock_calls

    def test_successful_modify(self):
        ''' Test successful modify '''
        data = self.mock_args()
        data['initiators'] = 'new'
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_igroup_mock_object('igroup').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_rest(self, mock_request):
        ''' Test successful modify '''
        set_module_args(self.mock_args('always'))
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['one_igroup_record'],   # get
            SRR['empty_good'],          # post (add initiators)
            SRR['empty_good'],          # patch (modify os_type)
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            igroup().apply()
        assert exc.value.args[0]['changed']
        print(mock_request.mock_calls)
        expected_call = call('POST', 'protocols/san/igroups/a1b2c3/initiators', None, json={'records': [{'name': 'init1'}]})
        assert expected_call in mock_request.mock_calls
        expected_call = call('PATCH', 'protocols/san/igroups/a1b2c3', None, json={'os_type': 'linux'})
        assert expected_call in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_igroups_rest(self, mock_request):
        ''' Test successful modify '''
        data = dict(self.mock_args())
        data.pop('initiator_names')
        data['igroups'] = ['test_igroup']
        data['use_rest'] = 'auto'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_9_9_1'],
            SRR['one_igroup_record'],   # get
            SRR['empty_good'],          # post (add initiators)
            SRR['empty_good'],          # patch (modify os_type)
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            igroup().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_9_9_0_no_igroups_rest(self, mock_request):
        ''' Test failed to use igroups '''
        data = dict(self.mock_args())
        data.pop('initiator_names')
        data['igroups'] = ['test_igroup']
        data['use_rest'] = 'auto'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_9_9_0'],
            SRR['one_igroup_record'],   # get
            SRR['empty_good'],          # post (add initiators)
            SRR['empty_good'],          # patch (modify os_type)
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            igroup().apply()
        msg = 'Error: using igroups requires ONTAP 9.9.1 or later and REST must be enabled - ONTAP version: 9.9.0.'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_igroup.NetAppOntapIgroup.get_igroup')
    def test_successful_rename(self, get_vserver):
        '''Test successful rename'''
        data = self.mock_args()
        data['from_name'] = 'test'
        data['name'] = 'test_new'
        set_module_args(data)
        current = {
            'initiator_names': ['init1', 'init2'],
            'name_to_uuid': dict(initiator_names=dict())
        }
        get_vserver.side_effect = [
            None,
            current
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_igroup_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_rename_rest(self, mock_request):
        ''' Test successful rename '''
        data = dict(self.mock_args('always'))
        data['from_name'] = 'test'
        data['name'] = 'test_new'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],         # get
            SRR['one_igroup_record'],   # get
            SRR['empty_good'],          # post for add initiator
            SRR['empty_good'],          # patch for rename
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            igroup().apply()
        assert exc.value.args[0]['changed']
        # print(mock_request.mock_calls)
        expected_call = call('PATCH', 'protocols/san/igroups/a1b2c3', None, json={'name': 'test_new', 'os_type': 'linux'})
        assert expected_call in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_zapi_or_rest99_option(self, mock_request):
        ''' Test ZAPI option not currently supported in REST is rejected '''
        data = dict(self.mock_args('always'))
        data['bind_portset'] = 'my_portset'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_9_8'],
            SRR['end_of_sequence']
        ]
        obj = self.get_igroup_mock_object('igroup')
        with pytest.raises(AnsibleExitJson) as exc:
            obj.apply()
        assert exc.value.args[0]['changed']
        msg = "Warning: falling back to ZAPI: using bind_portset requires ONTAP 9.9 or later and REST must be enabled - ONTAP version: 9.8.0."
        assert msg in self.warnings[-1]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_positive_zapi_or_rest99_option(self, mock_request):
        ''' Test ZAPI option not currently supported in REST forces ZAPI calls '''
        data = dict(self.mock_args('auto'))
        data['bind_portset'] = 'my_portset'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_9_8'],
            SRR['end_of_sequence']
        ]
        obj = self.get_igroup_mock_object('igroup')
        with pytest.raises(AnsibleExitJson) as exc:
            obj.apply()
        assert exc.value.args[0]['changed']
        msg = "Warning: falling back to ZAPI: using bind_portset requires ONTAP 9.9 or later and REST must be enabled - ONTAP version: 9.8.0."
        print(self.warnings)
        assert msg in self.warnings[-1]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_create_rest_99(self, mock_request):
        ''' Test 9.9 option works with REST '''
        data = dict(self.mock_args('auto'))
        data['bind_portset'] = 'my_portset'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],         # get
            SRR['empty_good'],          # post
            SRR['end_of_sequence']
        ]
        obj = self.get_igroup_mock_object('igroup')
        with pytest.raises(AnsibleExitJson) as exc:
            obj.apply()
        assert exc.value.args[0]['changed']
        print(self.warnings)
        assert not self.warnings
        expected_json = {'name': 'test', 'os_type': 'linux', 'svm': {'name': 'vserver'}, 'protocol': 'fcp', 'portset': 'my_portset',
                         'initiators': [{'name': 'init1'}]}
        expected_call = call('POST', 'protocols/san/igroups', None, json=expected_json)
        assert expected_call in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_modify_anything_zapi(self, mock_request):
        ''' Test ZAPI option not currently supported in REST is rejected '''
        data = dict(self.mock_args('never'))
        data['vserver'] = 'my_vserver'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        obj = self.get_igroup_mock_object('igroup')
        with pytest.raises(AnsibleFailJson) as exc:
            obj.apply()
        print(mock_request.mock_calls)
        msg = "Error: modifying  {'vserver': 'my_vserver'} is not supported in ZAPI"
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_modify_vserver_rest(self, mock_request):
        ''' Test ZAPI option not currently supported in REST is rejected '''
        data = dict(self.mock_args('auto'))
        data['vserver'] = 'my_vserver'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['one_igroup_record'],   # get
            SRR['end_of_sequence']
        ]
        obj = self.get_igroup_mock_object('igroup')
        with pytest.raises(AnsibleFailJson) as exc:
            obj.apply()
        print(mock_request.mock_calls)
        msg = "Error: modifying  {'vserver': 'my_vserver'} is not supported in REST"
        assert msg in exc.value.args[0]['msg']

    def test_negative_mutually_exclusive(self):
        ''' Test ZAPI option not currently supported in REST is rejected '''
        data = dict(self.mock_args('auto'))
        data['igroups'] = ['my_igroup']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_igroup_mock_object('igroup')
        msg = "parameters are mutually exclusive: igroups|initiator_names"
        assert msg in exc.value.args[0]['msg']

    def test_negative_igroups_require_rest(self):
        ''' Test ZAPI option not currently supported in REST is rejected '''
        data = dict(self.mock_args())
        data.pop('initiator_names')
        data['igroups'] = ['test_igroup']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_igroup_mock_object('igroup')
        msg = "requires ONTAP 9.9.1 or later and REST must be enabled"
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_igroups_require_9_9(self, mock_request):
        ''' Test ZAPI option not currently supported in REST is rejected '''
        data = dict(self.mock_args())
        data.pop('initiator_names')
        data['igroups'] = ['test_igroup']
        data['use_rest'] = 'always'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_9_8'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_igroup_mock_object('igroup')
        msg = "requires ONTAP 9.9.1 or later and REST must be enabled"
        assert msg in exc.value.args[0]['msg']
