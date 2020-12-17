# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for ONTAP Ansible module na_ontap_info '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import sys
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_info import main as info_main
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_info import __finditem as info_finditem
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_info \
    import NetAppONTAPGatherInfo as info_module  # module under test
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_info \
    import convert_keys as info_convert_keys     # function under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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
        if self.type == 'vserver':
            xml = self.build_vserver_info()
        elif self.type == 'net_port':
            xml = self.build_net_port_info()
        elif self.type == 'net_port_no_ifgrp':
            xml = self.build_net_port_info('no_ifgrp')
        elif self.type == 'net_port_with_ifgrp':
            xml = self.build_net_port_info('with_ifgrp')
            # for the next calls
            self.type = 'net_ifgrp'
        elif self.type == 'net_ifgrp':
            xml = self.build_net_ifgrp_info()
        elif self.type == 'zapi_error':
            error = netapp_utils.zapi.NaApiError('test', 'error')
            raise error
        elif self.type == 'list_of_one':
            xml = self.list_of_one()
        elif self.type == 'list_of_two':
            xml = self.list_of_two()
        elif self.type == 'list_of_two_dups':
            xml = self.list_of_two_dups()
        else:
            raise KeyError(self.type)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_vserver_info():
        ''' build xml data for vserser-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = netapp_utils.zapi.NaElement('attributes-list')
        attributes.add_node_with_children('vserver-info',
                                          **{'vserver-name': 'test_vserver'})
        xml.add_child_elem(attributes)
        return xml

    @staticmethod
    def build_net_port_info(with_type=None):
        ''' build xml data for net-port-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes_list = netapp_utils.zapi.NaElement('attributes-list')
        num_net_port_info = 2
        for i in range(num_net_port_info):
            net_port_info = netapp_utils.zapi.NaElement('net-port-info')
            net_port_info.add_new_child('node', 'node_' + str(i))
            net_port_info.add_new_child('port', 'port_' + str(i))
            net_port_info.add_new_child('broadcast_domain', 'test_domain_' + str(i))
            net_port_info.add_new_child('ipspace', 'ipspace' + str(i))
            if with_type == 'with_ifgrp':
                net_port_info.add_new_child('port_type', 'if_group')
            elif with_type == 'no_ifgrp':
                net_port_info.add_new_child('port_type', 'whatever')
            attributes_list.add_child_elem(net_port_info)
        xml.add_child_elem(attributes_list)
        return xml

    @staticmethod
    def build_net_ifgrp_info():
        ''' build xml data for net-ifgrp-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes_list = netapp_utils.zapi.NaElement('attributes')
        num_net_ifgrp_info = 2
        for i in range(num_net_ifgrp_info):
            net_ifgrp_info = netapp_utils.zapi.NaElement('net-ifgrp-info')
            net_ifgrp_info.add_new_child('ifgrp-name', 'ifgrp_' + str(i))
            net_ifgrp_info.add_new_child('node', 'node_' + str(i))
            attributes_list.add_child_elem(net_ifgrp_info)
        xml.add_child_elem(attributes_list)
        return xml

    @staticmethod
    def list_of_one():
        ''' build xml data for list of one info element '''
        xml = netapp_utils.zapi.NaElement('xml')
        list_of_one = [{'k1': 'v1', 'k2': 'v2'}]
        xml.translate_struct(list_of_one)
        return xml

    @staticmethod
    def list_of_two():
        ''' build xml data for list of two info elements '''
        xml = netapp_utils.zapi.NaElement('xml')
        list_of_two = [{'k1': 'v1'}, {'k2': 'v2'}]
        xml.translate_struct(list_of_two)
        return xml

    @staticmethod
    def list_of_two_dups():
        ''' build xml data for list of two info elements with same key '''
        xml = netapp_utils.zapi.NaElement('xml')
        list_of_two = [{'k1': 'v1'}, {'k1': 'v2'}]
        xml.translate_struct(list_of_two)
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

    def mock_args(self):
        return {
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'vserver': None
        }

    def get_info_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_info object
        """
        argument_spec = netapp_utils.na_ontap_host_argument_spec()
        argument_spec.update(dict(
            state=dict(type='str', default='info', choices=['info']),
            gather_subset=dict(default=['all'], type='list'),
            vserver=dict(type='str', default=None, required=False),
            max_records=dict(type='int', default=1024, required=False),
            desired_attributes=dict(type='dict', required=False),
            use_native_zapi_tags=dict(type='bool', required=False, default=False),
            continue_on_error=dict(type='list', required=False, default=['never']),
            query=dict(type='dict', required=False),
        ))
        module = basic.AnsibleModule(
            argument_spec=argument_spec,
            supports_check_mode=True
        )
        max_records = module.params['max_records']
        obj = info_module(module, max_records)
        obj.netapp_info = dict()
        if kind is None:
            obj.server = MockONTAPConnection()
        else:
            obj.server = MockONTAPConnection(kind)
        return obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            self.get_info_mock_object()
        print('Info: %s' % exc.value.args[0]['msg'])

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event')
    def test_ensure_command_called(self, mock_ems_log):
        ''' calling get_all will raise a KeyError exception '''
        set_module_args(self.mock_args())
        my_obj = self.get_info_mock_object('vserver')
        with pytest.raises(KeyError) as exc:
            my_obj.get_all(['net_interface_info'])
        if sys.version_info >= (2, 7):
            msg = 'net-interface-info'
            print(exc.value.args[0])
            assert exc.value.args[0] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event')
    def test_get_generic_get_iter(self, mock_ems_log):
        '''calling get_generic_get_iter will return expected dict'''
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('net_port')
        result = obj.get_generic_get_iter(
            'net-port-get-iter',
            attribute='net-port-info',
            key_fields=('node', 'port'),
            query={'max-records': '1024'}
        )
        assert result.get('node_0:port_0')
        assert result.get('node_1:port_1')

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_info.NetAppONTAPGatherInfo.get_all')
    def test_main(self, get_all):
        '''test main method - default: no state.'''
        set_module_args(self.mock_args())
        get_all.side_effect = [
            {'test_get_all': {'vserver_login_banner_info': 'test_vserver_login_banner_info', 'vserver_info': 'test_vserver_info'}}
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            info_main()
        assert 'state' not in exc.value.args[0]

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_info.NetAppONTAPGatherInfo.get_all')
    def test_main_with_state(self, get_all):
        '''test main method with explicit state.'''
        args = self.mock_args()
        args['state'] = 'some_state'
        set_module_args(args)
        get_all.side_effect = [
            {'test_get_all': {'vserver_login_banner_info': 'test_vserver_login_banner_info', 'vserver_info': 'test_vserver_info'}}
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            info_main()
        assert exc.value.args[0]['state'] == 'some_state'

    def test_get_ifgrp_info_no_ifgrp(self):
        '''test get_ifgrp_info with empty ifgrp_info'''
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('net_port_no_ifgrp')
        result = obj.get_ifgrp_info()
        assert result == {}

    def test_get_ifgrp_info_with_ifgrp(self):
        '''test get_ifgrp_info with empty ifgrp_info'''
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('net_port_with_ifgrp')
        result = obj.get_ifgrp_info()
        assert result.get('node_0:ifgrp_0')
        assert result.get('node_1:ifgrp_1')

    def test_ontapi_error(self):
        '''test ontapi will raise zapi error'''
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('zapi_error')
        with pytest.raises(AnsibleFailJson) as exc:
            obj.ontapi()
        # The new version of nettap-lib adds a space after :
        # Keep both versions to keep the pipeline happy
        assert exc.value.args[0]['msg'] == 'Error calling API system-get-ontapi-version: NetApp API failed. Reason - test:error'

    def test_call_api_error(self):
        '''test call_api will raise zapi error'''
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('zapi_error')
        with pytest.raises(AnsibleFailJson) as exc:
            obj.call_api('nvme-get-iter')
        # The new version of nettap-lib adds a space after :
        # Keep both versions to keep the pipeline happy
        assert exc.value.args[0]['msg'] == 'Error calling API nvme-get-iter: NetApp API failed. Reason - test:error'

    def test_find_item(self):
        '''test __find_item return expected key value'''
        obj = {"A": 1, "B": {"C": {"D": 2}}}
        key = "D"
        result = info_finditem(obj, key)
        assert result == 2

    def test_subset_return_all_complete(self):
        ''' Check all returns all of the entries if version is high enough '''
        version = '170'         # change this if new ZAPIs are supported
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        subset = obj.get_subset(['all'], version)
        assert set(obj.info_subsets.keys()) == subset

    def test_subset_return_all_partial(self):
        ''' Check all returns a subset of the entries if version is low enough '''
        version = '120'         # low enough so that some ZAPIs are not supported
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        subset = obj.get_subset(['all'], version)
        all_keys = obj.info_subsets.keys()
        assert set(all_keys) > subset
        supported_keys = filter(lambda key: obj.info_subsets[key]['min_version'] <= version, all_keys)
        assert set(supported_keys) == subset

    def test_subset_return_one(self):
        ''' Check single entry returns one '''
        version = '120'         # low enough so that some ZAPIs are not supported
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        subset = obj.get_subset(['net_interface_info'], version)
        assert len(subset) == 1

    def test_subset_return_multiple(self):
        ''' Check that more than one entry returns the same number '''
        version = '120'         # low enough so that some ZAPIs are not supported
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        subset_entries = ['net_interface_info', 'net_port_info']
        subset = obj.get_subset(subset_entries, version)
        assert len(subset) == len(subset_entries)

    def test_subset_return_bad(self):
        ''' Check that a bad subset entry will error out '''
        version = '120'         # low enough so that some ZAPIs are not supported
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        with pytest.raises(AnsibleFailJson) as exc:
            obj.get_subset(['net_interface_info', 'my_invalid_subset'], version)
        print('Info: %s' % exc.value.args[0]['msg'])
        assert exc.value.args[0]['msg'] == 'Bad subset: my_invalid_subset'

    def test_subset_return_unsupported(self):
        ''' Check that a new subset entry will error out on an older system '''
        version = '120'         # low enough so that some ZAPIs are not supported
        key = 'nvme_info'       # only supported starting at 140
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        with pytest.raises(AnsibleFailJson) as exc:
            obj.get_subset(['net_interface_info', key], version)
        print('Info: %s' % exc.value.args[0]['msg'])
        msg = 'Remote system at version %s does not support %s' % (version, key)
        assert exc.value.args[0]['msg'] == msg

    def test_subset_return_none(self):
        ''' Check usable subset can be empty '''
        version = '!'   # lower then 0, so that no ZAPI is supported
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        subset = obj.get_subset(['all'], version)
        assert len(subset) == 0

    def test_subset_return_all_expect_one(self):
        ''' Check !x returns all of the entries except x if version is high enough '''
        version = '170'         # change this if new ZAPIs are supported
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        subset = obj.get_subset(['!net_interface_info'], version)
        assert len(obj.info_subsets.keys()) == len(subset) + 1
        subset.add('net_interface_info')
        assert set(obj.info_subsets.keys()) == subset

    def test_subset_return_all_expect_three(self):
        ''' Check !x,!y,!z returns all of the entries except x, y, z if version is high enough '''
        version = '170'         # change this if new ZAPIs are supported
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        subset = obj.get_subset(['!net_interface_info', '!nvme_info', '!ontap_version'], version)
        assert len(obj.info_subsets.keys()) == len(subset) + 3
        subset.update(['net_interface_info', 'nvme_info', 'ontap_version'])
        assert set(obj.info_subsets.keys()) == subset

    def test_subset_return_none_with_exclusion(self):
        ''' Check usable subset can be empty with !x '''
        version = '!'   # lower then 0, so that no ZAPI is supported
        key = 'net_interface_info'
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        with pytest.raises(AnsibleFailJson) as exc:
            obj.get_subset(['!' + key], version)
        print('Info: %s' % exc.value.args[0]['msg'])
        msg = 'Remote system at version %s does not support %s' % (version, key)
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event')
    def test_get_generic_get_iter_flatten_list_of_one(self, mock_ems_log):
        '''calling get_generic_get_iter will return expected dict'''
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('list_of_one')
        result = obj.get_generic_get_iter(
            'list_of_one',
            attributes_list_tag=None,
        )
        assert isinstance(result, dict)
        assert result.get('k1') == 'v1'
        assert result.get('k2') == 'v2'

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event')
    def test_get_generic_get_iter_flatten_list_of_two(self, mock_ems_log):
        '''calling get_generic_get_iter will return expected dict'''
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('list_of_two')
        result = obj.get_generic_get_iter(
            'list_of_two',
            attributes_list_tag=None,
        )
        assert isinstance(result, dict)
        assert result.get('k1') == 'v1'
        assert result.get('k2') == 'v2'

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event')
    def test_get_generic_get_iter_flatten_list_of_two_dups(self, mock_ems_log):
        '''calling get_generic_get_iter will return expected dict'''
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('list_of_two_dups')
        result = obj.get_generic_get_iter(
            'list_of_two_dups',
            attributes_list_tag=None,
        )
        assert isinstance(result, list)
        assert result[0].get('k1') == 'v1'
        assert result[1].get('k1') == 'v2'

    def test_check_underscore(self):
        ''' Check warning is recorded if '_' is found in key '''
        test_dict = dict(
            bad_key='something'
        )
        test_dict['good-key'] = [dict(
            other_bad_key=dict(
                yet_another_bad_key=1
            ),
            somekey=dict(
                more_bad_key=2
            )
        )]
        set_module_args(self.mock_args())
        obj = self.get_info_mock_object('vserver')
        obj.check_for___in_keys(test_dict)
        print('Info: %s' % repr(obj.warnings))
        for key in ['bad_key', 'other_bad_key', 'yet_another_bad_key', 'more_bad_key']:
            msg = "Underscore in ZAPI tag: %s, do you mean '-'?" % key
            assert msg in obj.warnings
            obj.warnings.remove(msg)
        # make sure there is no extra warnings (eg we found and removed all of them)
        assert obj.warnings == list()

    @staticmethod
    def d2us(astr):
        return str.replace(astr, '-', '_')

    def test_convert_keys_string(self):
        ''' no conversion '''
        key = 'a-b-c'
        assert info_convert_keys(key) == key

    def test_convert_keys_tuple(self):
        ''' no conversion '''
        key = 'a-b-c'
        anobject = (key, key)
        assert info_convert_keys(anobject) == anobject

    def test_convert_keys_list(self):
        ''' no conversion '''
        key = 'a-b-c'
        anobject = [key, key]
        assert info_convert_keys(anobject) == anobject

    def test_convert_keys_simple_dict(self):
        ''' conversion of keys '''
        key = 'a-b-c'
        anobject = {key: 1}
        assert list(info_convert_keys(anobject).keys())[0] == self.d2us(key)

    def test_convert_keys_list_of_dict(self):
        ''' conversion of keys '''
        key = 'a-b-c'
        anobject = [{key: 1}, {key: 2}]
        converted = info_convert_keys(anobject)
        for adict in converted:
            for akey in adict:
                assert akey == self.d2us(key)

    def test_set_error_flags_error_n(self):
        ''' Check set_error__flags return correct dict '''
        args = dict(self.mock_args())
        args['continue_on_error'] = ['never', 'whatever']
        set_module_args(args)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_info_mock_object('vserver')
        print('Info: %s' % exc.value.args[0]['msg'])
        msg = "never needs to be the only keyword in 'continue_on_error' option."
        assert exc.value.args[0]['msg'] == msg

    def test_set_error_flags_error_a(self):
        ''' Check set_error__flags return correct dict '''
        args = dict(self.mock_args())
        args['continue_on_error'] = ['whatever', 'always']
        set_module_args(args)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_info_mock_object('vserver')
        print('Info: %s' % exc.value.args[0]['msg'])
        msg = "always needs to be the only keyword in 'continue_on_error' option."
        assert exc.value.args[0]['msg'] == msg

    def test_set_error_flags_error_u(self):
        ''' Check set_error__flags return correct dict '''
        args = dict(self.mock_args())
        args['continue_on_error'] = ['whatever', 'else']
        set_module_args(args)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_info_mock_object('vserver')
        print('Info: %s' % exc.value.args[0]['msg'])
        msg = "whatever is not a valid keyword in 'continue_on_error' option."
        assert exc.value.args[0]['msg'] == msg

    def test_set_error_flags_1_flag(self):
        ''' Check set_error__flags return correct dict '''
        args = dict(self.mock_args())
        args['continue_on_error'] = ['missing_vserver_api_error']
        set_module_args(args)
        obj = self.get_info_mock_object('vserver')
        assert not obj.error_flags['missing_vserver_api_error']
        assert obj.error_flags['rpc_error']
        assert obj.error_flags['other_error']

    def test_set_error_flags_2_flags(self):
        ''' Check set_error__flags return correct dict '''
        args = dict(self.mock_args())
        args['continue_on_error'] = ['missing_vserver_api_error', 'rpc_error']
        set_module_args(args)
        obj = self.get_info_mock_object('vserver')
        assert not obj.error_flags['missing_vserver_api_error']
        assert not obj.error_flags['rpc_error']
        assert obj.error_flags['other_error']

    def test_set_error_flags_3_flags(self):
        ''' Check set_error__flags return correct dict '''
        args = dict(self.mock_args())
        args['continue_on_error'] = ['missing_vserver_api_error', 'rpc_error', 'other_error']
        set_module_args(args)
        obj = self.get_info_mock_object('vserver')
        assert not obj.error_flags['missing_vserver_api_error']
        assert not obj.error_flags['rpc_error']
        assert not obj.error_flags['other_error']
