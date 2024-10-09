# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for ONTAP Ansible module na_ontap_info '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_error_message, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_warning_was_raised, expect_and_capture_ansible_exception, call_main, create_module, patch_ansible, print_warnings
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_info import NetAppONTAPGatherInfo as my_module, main as my_main
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_info import convert_keys as info_convert_keys, __finditem as info_finditem

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if sys.version_info < (3, 11):
    pytestmark = pytest.mark.skip("Skipping Unit Tests on 3.11")


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'use_rest',
}


def net_port_info(port_type):
    return {
        'attributes-list': [{
            'net-port-info': {
                'node': 'node_0',
                'port': 'port_0',
                'broadcast_domain': 'broadcast_domain_0',
                'ipspace': 'ipspace_0',
                'port_type': port_type
            }}, {
            'net-port-info': {
                'node': 'node_1',
                'port': 'port_1',
                'broadcast_domain': 'broadcast_domain_1',
                'ipspace': 'ipspace_1',
                'port_type': port_type
            }}
        ]
    }


def net_ifgrp_info(id):
    return {
        'attributes': {
            'net-ifgrp-info': {
                'ifgrp-name': 'ifgrp_%d' % id,
                'node': 'node_%d' % id,
            }
        }
    }


def aggr_efficiency_info(node):
    attributes = {
        'aggregate': 'v2',
    }
    if node:
        attributes['node'] = node
    return {
        'attributes-list': [{
            'aggr-efficiency-info': attributes
        }]
    }


def lun_info(path, next=False):
    info = {
        'attributes-list': [{
            'lun-info': {
                'serial-number': 'z6CcD+SK5mPb',
                'vserver': 'svm1',
                'path': path}
        }]
    }
    if next:
        info['next-tag'] = 'next_tag'
    return info


list_of_one = [{'k1': 'v1'}]
list_of_two = [{'k1': 'v1'}, {'k2': 'v2'}]
list_of_two_dups = [{'k1': 'v1'}, {'k1': 'v2'}]


ZRR = zapi_responses({
    'net_port_info': build_zapi_response(net_port_info('whatever'), 2),
    'net_port_info_with_ifgroup': build_zapi_response(net_port_info('if_group'), 2),
    'net_ifgrp_info_0': build_zapi_response(net_ifgrp_info(0), 1),
    'net_ifgrp_info_1': build_zapi_response(net_ifgrp_info(1), 1),
    'list_of_one': build_zapi_response(list_of_one),
    'list_of_two': build_zapi_response(list_of_two),
    'list_of_two_dups': build_zapi_response(list_of_two_dups),
    'aggr_efficiency_info': build_zapi_response(aggr_efficiency_info('v1')),
    'aggr_efficiency_info_no_node': build_zapi_response(aggr_efficiency_info(None)),
    'lun_info': build_zapi_response(lun_info('p1')),
    'lun_info_next_2': build_zapi_response(lun_info('p2', True)),
    'lun_info_next_3': build_zapi_response(lun_info('p3', True)),
    'lun_info_next_4': build_zapi_response(lun_info('p4', True)),
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    assert 'missing required arguments: hostname' in call_main(my_main, {}, fail=True)['msg']


def test_ensure_command_called():
    ''' calling get_all will raise a KeyError exception '''
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['version']),
        ('ZAPI', 'net-interface-get-iter', ZRR['success']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    results = my_obj.get_all(['net_interface_info'])
    assert 'net_interface_info' in results


def test_get_generic_get_iter():
    '''calling get_generic_get_iter will return expected dict'''
    register_responses([
        ('ZAPI', 'net-port-get-iter', ZRR['net_port_info']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    result = obj.get_generic_get_iter(
        'net-port-get-iter',
        attribute='net-port-info',
        key_fields=('node', 'port'),
        query={'max-records': '1024'}
    )
    assert result.get('node_0:port_0')
    assert result.get('node_1:port_1')


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_info.NetAppONTAPGatherInfo.get_all')
def test_main(get_all):
    '''test main method - default: no state.'''
    register_responses([
    ])
    get_all.side_effect = [
        {'test_get_all': {'vserver_login_banner_info': 'test_vserver_login_banner_info', 'vserver_info': 'test_vserver_info'}}
    ]
    results = call_main(my_main, DEFAULT_ARGS)
    assert 'ontap_info' in results
    assert 'test_get_all' in results['ontap_info']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_info.NetAppONTAPGatherInfo.get_all')
def test_main_with_state(get_all):
    '''test main method with explicit state.'''
    register_responses([
    ])
    module_args = {'state': 'some_state'}
    get_all.side_effect = [
        {'test_get_all': {'vserver_login_banner_info': 'test_vserver_login_banner_info', 'vserver_info': 'test_vserver_info'}}
    ]
    results = call_main(my_main, DEFAULT_ARGS, module_args)
    assert 'ontap_info' in results
    assert 'test_get_all' in results['ontap_info']
    print_warnings()
    assert_warning_was_raised("option 'state' is deprecated.")


def test_get_ifgrp_info_no_ifgrp():
    '''test get_ifgrp_info with empty ifgrp_info'''
    register_responses([
        ('ZAPI', 'net-port-get-iter', ZRR['net_port_info']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    result = obj.get_ifgrp_info()
    assert result == {}


def test_get_ifgrp_info_with_ifgrp():
    '''test get_ifgrp_info with empty ifgrp_info'''
    register_responses([
        ('ZAPI', 'net-port-get-iter', ZRR['net_port_info_with_ifgroup']),
        ('ZAPI', 'net-port-ifgrp-get', ZRR['net_ifgrp_info_0']),
        ('ZAPI', 'net-port-ifgrp-get', ZRR['net_ifgrp_info_1']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    results = obj.get_ifgrp_info()
    assert results.get('node_0:ifgrp_0')
    assert results.get('node_1:ifgrp_1')


def test_ontapi_error():
    '''test ontapi will raise zapi error'''
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['error']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    error = zapi_error_message('Error calling API system-get-ontapi-version')
    assert error in expect_and_capture_ansible_exception(obj.ontapi, 'fail')['msg']


def test_call_api_error():
    '''test call_api will raise zapi error'''
    register_responses([
        ('ZAPI', 'security-key-manager-key-get-iter', ZRR['error']),
        ('ZAPI', 'lun-get-iter', ZRR['error_missing_api']),
        ('ZAPI', 'nvme-get-iter', ZRR['error']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    # 1 error is ignored
    assert obj.call_api('security-key-manager-key-get-iter') == (None, None)
    # 2 missing API (cluster admin API not visible at vserver level)
    error = zapi_error_message('Error invalid API.  Most likely running a cluster level API as vserver', 13005)
    assert error in expect_and_capture_ansible_exception(obj.call_api, 'fail', 'lun-get-iter')['msg']
    # 3 API error
    error = zapi_error_message('Error calling API nvme-get-iter')
    assert error in expect_and_capture_ansible_exception(obj.call_api, 'fail', 'nvme-get-iter')['msg']


def test_get_generic_get_iter_key_error():
    register_responses([
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    keys = 'single_key'
    error = "Error: key 'single_key' not found for lun-get-iter, got:"
    assert error in expect_and_capture_ansible_exception(obj.get_generic_get_iter, 'fail', 'lun-get-iter', None, keys)['msg']
    keys = ('key1', 'path')
    error = "Error: key 'key1' not found for lun-get-iter, got:"
    assert error in expect_and_capture_ansible_exception(obj.get_generic_get_iter, 'fail', 'lun-get-iter', None, keys)['msg']
    # ignoring key_errors
    module_args = {'continue_on_error': 'key_error'}
    obj = create_module(my_module, DEFAULT_ARGS, module_args)
    keys = 'single_key'
    missing_key = 'Error_1_key_not_found_%s' % keys
    results = obj.get_generic_get_iter('lun-get-iter', None, keys)
    assert missing_key in results
    keys = ('key1', 'path')
    missing_key = 'Error_1_key_not_found_%s' % keys[0]
    results = obj.get_generic_get_iter('lun-get-iter', None, keys)
    assert missing_key in results


def test_find_item():
    '''test __find_item return expected key value'''
    register_responses([
    ])
    obj = {"A": 1, "B": {"C": {"D": 2}}}
    key = "D"
    result = info_finditem(obj, key)
    assert result == 2
    obj = {"A": 1, "B": {"C": {"D": None}}}
    result = info_finditem(obj, key)
    assert result == "None"


def test_subset_return_all_complete():
    ''' Check all returns all of the entries if version is high enough '''
    register_responses([
    ])
    version = '170'         # change this if new ZAPIs are supported
    obj = create_module(my_module, DEFAULT_ARGS)
    subset = obj.get_subset(['all'], version)
    assert set(obj.info_subsets.keys()) == subset


def test_subset_return_all_partial():
    ''' Check all returns a subset of the entries if version is low enough '''
    register_responses([
    ])
    version = '120'         # low enough so that some ZAPIs are not supported
    obj = create_module(my_module, DEFAULT_ARGS)
    subset = obj.get_subset(['all'], version)
    all_keys = obj.info_subsets.keys()
    assert set(all_keys) > subset
    supported_keys = filter(lambda key: obj.info_subsets[key]['min_version'] <= version, all_keys)
    assert set(supported_keys) == subset


def test_subset_return_one():
    ''' Check single entry returns one '''
    register_responses([
    ])
    version = '120'         # low enough so that some ZAPIs are not supported
    obj = create_module(my_module, DEFAULT_ARGS)
    subset = obj.get_subset(['net_interface_info'], version)
    assert len(subset) == 1


def test_subset_return_multiple():
    ''' Check that more than one entry returns the same number '''
    register_responses([
    ])
    version = '120'         # low enough so that some ZAPIs are not supported
    obj = create_module(my_module, DEFAULT_ARGS)
    subset_entries = ['net_interface_info', 'net_port_info']
    subset = obj.get_subset(subset_entries, version)
    assert len(subset) == len(subset_entries)


def test_subset_return_bad():
    ''' Check that a bad subset entry will error out '''
    register_responses([
    ])
    version = '120'         # low enough so that some ZAPIs are not supported
    obj = create_module(my_module, DEFAULT_ARGS)
    error = 'Bad subset: my_invalid_subset'
    assert error in expect_and_capture_ansible_exception(obj.get_subset, 'fail', ['net_interface_info', 'my_invalid_subset'], version)['msg']


def test_subset_return_unsupported():
    ''' Check that a new subset entry will error out on an older system '''
    register_responses([
    ])
    version = '120'         # low enough so that some ZAPIs are not supported
    key = 'nvme_info'       # only supported starting at 140
    obj = create_module(my_module, DEFAULT_ARGS)
    error = 'Remote system at version %s does not support %s' % (version, key)
    assert error in expect_and_capture_ansible_exception(obj.get_subset, 'fail', ['net_interface_info', key], version)['msg']


def test_subset_return_none():
    ''' Check usable subset can be empty '''
    register_responses([
    ])
    version = '!'   # lower then 0, so that no ZAPI is supported
    obj = create_module(my_module, DEFAULT_ARGS)
    subset = obj.get_subset(['all'], version)
    assert len(subset) == 0


def test_subset_return_all_expect_one():
    ''' Check !x returns all of the entries except x if version is high enough '''
    register_responses([
    ])
    version = '170'         # change this if new ZAPIs are supported
    obj = create_module(my_module, DEFAULT_ARGS)
    subset = obj.get_subset(['!net_interface_info'], version)
    assert len(obj.info_subsets.keys()) == len(subset) + 1
    subset.add('net_interface_info')
    assert set(obj.info_subsets.keys()) == subset


def test_subset_return_all_expect_three():
    ''' Check !x,!y,!z returns all of the entries except x, y, z if version is high enough '''
    register_responses([
    ])
    version = '170'         # change this if new ZAPIs are supported
    obj = create_module(my_module, DEFAULT_ARGS)
    subset = obj.get_subset(['!net_interface_info', '!nvme_info', '!ontap_version'], version)
    assert len(obj.info_subsets.keys()) == len(subset) + 3
    subset.update(['net_interface_info', 'nvme_info', 'ontap_version'])
    assert set(obj.info_subsets.keys()) == subset


def test_subset_return_none_with_exclusion():
    ''' Check usable subset can be empty with !x '''
    register_responses([
    ])
    version = '!'   # lower then 0, so that no ZAPI is supported
    key = 'net_interface_info'
    obj = create_module(my_module, DEFAULT_ARGS)
    error = 'Remote system at version %s does not support %s' % (version, key)
    assert error in expect_and_capture_ansible_exception(obj.get_subset, 'fail', ['!' + key], version)['msg']


def test_get_generic_get_iter_flatten_list_of_one():
    '''calling get_generic_get_iter will return expected dict'''
    register_responses([
        ('ZAPI', 'list_of_one', ZRR['list_of_one']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    result = obj.get_generic_get_iter(
        'list_of_one',
        attributes_list_tag=None,
    )
    print(ZRR['list_of_one'][0].to_string())
    print(result)
    assert isinstance(result, dict)
    assert result.get('k1') == 'v1'


def test_get_generic_get_iter_flatten_list_of_two():
    '''calling get_generic_get_iter will return expected dict'''
    register_responses([
        ('ZAPI', 'list_of_two', ZRR['list_of_two']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    result = obj.get_generic_get_iter(
        'list_of_two',
        attributes_list_tag=None,
    )
    print(result)
    assert isinstance(result, dict)
    assert result.get('k1') == 'v1'
    assert result.get('k2') == 'v2'


def test_get_generic_get_iter_flatten_list_of_two_dups():
    '''calling get_generic_get_iter will return expected dict'''
    register_responses([
        ('ZAPI', 'list_of_two_dups', ZRR['list_of_two_dups']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    result = obj.get_generic_get_iter(
        'list_of_two_dups',
        attributes_list_tag=None,
    )
    assert isinstance(result, list)
    assert result[0].get('k1') == 'v1'
    assert result[1].get('k1') == 'v2'


def test_check_underscore():
    ''' Check warning is recorded if '_' is found in key '''
    register_responses([
    ])
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
    obj = create_module(my_module, DEFAULT_ARGS)
    obj.check_for___in_keys(test_dict)
    print('Info: %s' % repr(obj.warnings))
    for key in ['bad_key', 'other_bad_key', 'yet_another_bad_key', 'more_bad_key']:
        msg = "Underscore in ZAPI tag: %s, do you mean '-'?" % key
        assert msg in obj.warnings
        obj.warnings.remove(msg)
    # make sure there is no extra warnings (eg we found and removed all of them)
    assert obj.warnings == list()


def d2us(astr):
    return str.replace(astr, '-', '_')


def test_convert_keys_string():
    ''' no conversion '''
    register_responses([
    ])
    key = 'a-b-c'
    assert info_convert_keys(key) == key


def test_convert_keys_tuple():
    ''' no conversion '''
    register_responses([
    ])
    key = 'a-b-c'
    anobject = (key, key)
    assert info_convert_keys(anobject) == anobject


def test_convert_keys_list():
    ''' no conversion '''
    register_responses([
    ])
    key = 'a-b-c'
    anobject = [key, key]
    assert info_convert_keys(anobject) == anobject


def test_convert_keys_simple_dict():
    ''' conversion of keys '''
    register_responses([
    ])
    key = 'a-b-c'
    anobject = {key: 1}
    assert list(info_convert_keys(anobject).keys())[0] == d2us(key)


def test_convert_keys_list_of_dict():
    ''' conversion of keys '''
    register_responses([
    ])
    key = 'a-b-c'
    anobject = [{key: 1}, {key: 2}]
    converted = info_convert_keys(anobject)
    for adict in converted:
        for akey in adict:
            assert akey == d2us(key)


def test_set_error_flags_error_n():
    ''' Check set_error__flags return correct dict '''
    register_responses([
    ])
    module_args = {'continue_on_error': ['never', 'whatever']}
    msg = "never needs to be the only keyword in 'continue_on_error' option."
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_set_error_flags_error_a():
    ''' Check set_error__flags return correct dict '''
    register_responses([
    ])
    module_args = {'continue_on_error': ['whatever', 'always']}
    print('Info: %s' % call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'])
    msg = "always needs to be the only keyword in 'continue_on_error' option."
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_set_error_flags_error_u():
    ''' Check set_error__flags return correct dict '''
    register_responses([
    ])
    module_args = {'continue_on_error': ['whatever', 'else']}

    print('Info: %s' % call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'])
    msg = "whatever is not a valid keyword in 'continue_on_error' option."
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_set_error_flags_1_flag():
    ''' Check set_error__flags return correct dict '''
    register_responses([
    ])
    module_args = {'continue_on_error': ['missing_vserver_api_error']}
    obj = create_module(my_module, DEFAULT_ARGS, module_args, 'vserver')
    assert not obj.error_flags['missing_vserver_api_error']
    assert obj.error_flags['rpc_error']
    assert obj.error_flags['other_error']


def test_set_error_flags_2_flags():
    ''' Check set_error__flags return correct dict '''
    register_responses([
    ])
    module_args = {'continue_on_error': ['missing_vserver_api_error', 'rpc_error']}
    obj = create_module(my_module, DEFAULT_ARGS, module_args, 'vserver')
    assert not obj.error_flags['missing_vserver_api_error']
    assert not obj.error_flags['rpc_error']
    assert obj.error_flags['other_error']


def test_set_error_flags_3_flags():
    ''' Check set_error__flags return correct dict '''
    register_responses([
    ])
    module_args = {'continue_on_error': ['missing_vserver_api_error', 'rpc_error', 'other_error']}
    obj = create_module(my_module, DEFAULT_ARGS, module_args, 'vserver')
    assert not obj.error_flags['missing_vserver_api_error']
    assert not obj.error_flags['rpc_error']
    assert not obj.error_flags['other_error']


def test_get_subset_missing_key():
    '''calling aggr_efficiency_info with missing key'''
    register_responses([
        ('ZAPI', 'aggr-efficiency-get-iter', ZRR['aggr_efficiency_info']),
        ('ZAPI', 'aggr-efficiency-get-iter', ZRR['aggr_efficiency_info_no_node']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    call = obj.info_subsets['aggr_efficiency_info']
    info = call['method'](**call['kwargs'])
    print(info)
    assert 'v1:v2' in info
    call = obj.info_subsets['aggr_efficiency_info']
    info = call['method'](**call['kwargs'])
    print(info)
    assert 'key_not_present:v2' in info


def test_get_lun_with_serial():
    '''calling lun_info with serial-number key'''
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
        # no records
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['no_records']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    info = obj.get_all(['lun_info'])
    print(info)
    assert 'lun_info' in info
    lun_info = info['lun_info']['svm1:p1']
    assert lun_info['serial_number'] == 'z6CcD+SK5mPb'
    assert lun_info['serial_hex'] == '7a364363442b534b356d5062'
    assert lun_info['naa_id'] == 'naa.600a0980' + '7a364363442b534b356d5062'
    # no records
    info = obj.get_all(['lun_info'])
    assert 'lun_info' in info
    assert info['lun_info'] is None
    # error


def test_get_nothing():
    '''calling with !all'''
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    info = obj.get_all(['!all'])
    print(info)
    assert info == {'ontap_version': '0', 'ontapi_version': '0'}


def test_deprecation_ontap_version():
    '''calling ontap_version'''
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    info = obj.get_all(['ontap_version'])
    assert info
    assert 'deprecation_warning' in info
    assert info['deprecation_warning'] == 'ontap_version is deprecated, please use ontapi_version'


def test_help():
    '''calling help'''
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
    ])
    obj = create_module(my_module, DEFAULT_ARGS)
    info = obj.get_all(['help'])
    assert info
    assert 'help' in info


def test_desired_attributes():
    '''desired_attributes option'''
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['success']),
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
    ])
    module_args = {'desired_attributes': {'attr': 'value'}}
    obj = create_module(my_module, DEFAULT_ARGS, module_args)
    info = obj.get_all(['lun_info'])
    assert 'lun_info' in info
    assert info['lun_info'] is None
    error = 'desired_attributes option is only supported with a single subset'
    assert error in expect_and_capture_ansible_exception(obj.get_all, 'fail', ['ontapi_version', 'ontap_system_version'])['msg']


def test_query():
    '''query option'''
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
    ])
    module_args = {'query': {'attr': 'value', 'a_b': 'val'}}
    obj = create_module(my_module, DEFAULT_ARGS, module_args)
    info = obj.get_all(['ontapi_version'])
    assert info == {'ontap_version': '0', 'ontapi_version': '0', 'module_warnings': ["Underscore in ZAPI tag: a_b, do you mean '-'?"]}
    error = 'query option is only supported with a single subset'
    assert error in expect_and_capture_ansible_exception(obj.get_all, 'fail', ['ontapi_version', 'ontap_system_version'])['msg']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_info.NetAppONTAPGatherInfo.get_all')
def test_get_all_with_summary(mock_get_all):
    '''all and summary'''
    register_responses([
    ])
    module_args = {'summary': True, 'gather_subset': []}
    mock_get_all.return_value = {'a_info': {'1': '1.1'}, 'b_info': {'2': '2.2'}}
    info = call_main(my_main, DEFAULT_ARGS, module_args)
    assert info
    assert 'ontap_info' in info
    assert info['ontap_info'] == {'a_info': {'1': None}.keys(), 'b_info': {'2': None}.keys()}


def test_repeated_get():
    '''query option'''
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info_next_2']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info_next_3']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info_next_4']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
    ])
    module_args = {'query': {}}
    obj = create_module(my_module, DEFAULT_ARGS, module_args)
    info = obj.get_all(['lun_info'])
    assert info
    assert 'lun_info' in info
    assert len(info['lun_info']) == 4


def test_repeated_get_error():
    '''query option'''
    register_responses([
        ('ZAPI', 'lun-get-iter', ZRR['lun_info_next_2']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
    ])
    module_args = {'query': {}}
    obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = "'next-tag' is not expected for this API"
    assert error in expect_and_capture_ansible_exception(obj.call_api, 'fail', 'lun-get-iter', attributes_list_tag=None)['msg']


def test_attribute_error():
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
        ('ZAPI', 'license-v2-list-info', ZRR['no_records']),
    ])
    module_args = {'gather_subset': ['license_info'], 'vserver': 'svm'}
    error = "Error: attribute 'licenses' not found for license-v2-list-info, got:"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_continue_on_error():
    register_responses([
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
        ('ZAPI', 'license-v2-list-info', ZRR['error']),
        ('ZAPI', 'system-get-ontapi-version', ZRR['success']),
        ('ZAPI', 'license-v2-list-info', ZRR['error']),
    ])
    module_args = {'gather_subset': ['license_info'], 'vserver': 'svm'}
    error = zapi_error_message('Error calling API license-v2-list-info')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args = {'gather_subset': ['license_info'], 'vserver': 'svm', 'continue_on_error': 'always'}
    info = call_main(my_main, DEFAULT_ARGS, module_args)
    error = {'error': zapi_error_message('Error calling API license-v2-list-info')}
    assert info is not None
    assert info['ontap_info']['license_info'] == error
