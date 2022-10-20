# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import create_module,\
    patch_ansible, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, build_zapi_error, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_routes \
    import NetAppOntapNetRoutes as net_route_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


DEFAULT_ARGS = {
    'https': 'True',
    'use_rest': 'never',
    'state': 'present',
    'destination': '176.0.0.0/24',
    'gateway': '10.193.72.1',
    'vserver': 'test_vserver',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'metric': 70
}


def route_info_zapi(destination='176.0.0.0/24', gateway='10.193.72.1', metric=70):
    return {
        'attributes': {
            'net-vs-routes-info': {
                'address-family': 'ipv4',
                'destination': destination,
                'gateway': gateway,
                'metric': metric,
                'vserver': 'test_vserver'
            }
        }
    }


ZRR = zapi_responses({
    'net_route_info': build_zapi_response(route_info_zapi()),
    'net_route_info_gateway': build_zapi_response(route_info_zapi(gateway='10.193.0.1', metric=40)),
    'net_route_info_destination': build_zapi_response(route_info_zapi(destination='178.0.0.1/24', metric=40)),
    'error_15661': build_zapi_error(15661, 'not_exists_error'),
    'error_13001': build_zapi_error(13001, 'already exists')
})


SRR = rest_responses({
    'net_routes_record': (200, {
        'records': [
            {
                "destination": {"address": "176.0.0.0", "netmask": "24", "family": "ipv4"},
                "gateway": '10.193.72.1',
                "uuid": '1cd8a442-86d1-11e0-ae1c-123478563412',
                "metric": 70,
                "svm": {"name": "test_vserver"}
            }
        ]
    }, None),
    'net_routes_cluster': (200, {
        'records': [
            {
                "destination": {"address": "176.0.0.0", "netmask": "24", "family": "ipv4"},
                "gateway": '10.193.72.1',
                "uuid": '1cd8a442-86d1-11e0-ae1c-123478563412',
                "metric": 70,
                "scope": "cluster"
            }
        ]
    }, None),
    'modified_record': (200, {
        'records': [
            {
                "destination": {"address": "0.0.0.0", "netmask": "0", "family": "ipv4"},
                "gateway": '10.193.72.1',
                "uuid": '1cd8a442-86d1-11e0-ae1c-123478563412',
                "scope": "cluster",
                "metric": 90
            }
        ]
    }, None)
})


def test_module_fail_when_required_args_missing():
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "destination", "gateway"]
    error = create_module(net_route_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_get_nonexistent_net_route():
    ''' Test if get_net_route returns None for non-existent net_route '''
    register_responses([
        ('net-routes-get', ZRR['no_records'])
    ])
    assert create_module(net_route_module, DEFAULT_ARGS).get_net_route() is None


def test_get_nonexistent_net_route_15661():
    ''' Test if get_net_route returns None for non-existent net_route
        when ZAPI returns an exception for a route not found
    '''
    register_responses([
        ('net-routes-get', ZRR['error_15661'])
    ])
    assert create_module(net_route_module, DEFAULT_ARGS).get_net_route() is None


def test_get_existing_route():
    ''' Test if get_net_route returns details for existing net_route '''
    register_responses([
        ('net-routes-get', ZRR['net_route_info'])
    ])
    result = create_module(net_route_module, DEFAULT_ARGS).get_net_route()
    assert result['destination'] == DEFAULT_ARGS['destination']
    assert result['gateway'] == DEFAULT_ARGS['gateway']


def test_create_error_missing_param():
    ''' Test if create throws an error if destination is not specified'''
    error = 'missing required arguments: destination'
    assert error in create_module(net_route_module, {'hostname': 'host', 'gateway': 'gate'}, fail=True)['msg']


def test_successful_create():
    ''' Test successful create '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['empty']),
        ('net-routes-create', ZRR['success']),
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['net_route_info']),
    ])
    assert create_and_apply(net_route_module, DEFAULT_ARGS)['changed']
    assert not create_and_apply(net_route_module, DEFAULT_ARGS)['changed']


def test_create_zapi_ignore_route_exist():
    ''' Test NaApiError on create '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['empty']),
        ('net-routes-create', ZRR['error_13001'])
    ])
    assert create_and_apply(net_route_module, DEFAULT_ARGS)['changed']


def test_successful_create_zapi_no_metric():
    ''' Test successful create '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['empty']),
        ('net-routes-create', ZRR['success'])
    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['metric']
    assert create_and_apply(net_route_module, DEFAULT_ARGS)['changed']


def test_successful_delete():
    ''' Test successful delete '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['net_route_info']),
        ('net-routes-destroy', ZRR['success']),
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['empty']),
    ])
    assert create_and_apply(net_route_module, DEFAULT_ARGS, {'state': 'absent'})['changed']
    assert not create_and_apply(net_route_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_successful_modify_metric():
    ''' Test successful modify metric '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['net_route_info']),
        ('net-routes-destroy', ZRR['success']),
        ('net-routes-create', ZRR['success'])
    ])
    assert create_and_apply(net_route_module, DEFAULT_ARGS, {'metric': '40'})['changed']


def test_successful_modify_gateway():
    ''' Test successful modify gateway '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['empty']),
        ('net-routes-get', ZRR['net_route_info']),
        ('net-routes-destroy', ZRR['success']),
        ('net-routes-create', ZRR['success']),
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['net_route_info_gateway'])
    ])
    args = {'from_gateway': '10.193.72.1', 'gateway': '10.193.0.1', 'metric': 40}
    assert create_and_apply(net_route_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(net_route_module, DEFAULT_ARGS, args)['changed']


def test_successful_modify_destination():
    ''' Test successful modify destination '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['empty']),
        ('net-routes-get', ZRR['net_route_info']),
        ('net-routes-destroy', ZRR['success']),
        ('net-routes-create', ZRR['success']),
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['net_route_info_gateway'])
    ])
    args = {'from_destination': '176.0.0.0/24', 'destination': '178.0.0.1/24', 'metric': 40}
    assert create_and_apply(net_route_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(net_route_module, DEFAULT_ARGS, args)['changed']


def test_if_all_methods_catch_exception_zapi():
    ''' test error zapi - get/create/modify/delete'''
    register_responses([
        # ZAPI get/create/delete error.
        ('net-routes-get', ZRR['error']),
        ('net-routes-create', ZRR['error']),
        ('net-routes-destroy', ZRR['error']),
        # ZAPI modify error.
        ('ems-autosupport-log', ZRR['empty']),
        ('net-routes-get', ZRR['net_route_info']),
        ('net-routes-destroy', ZRR['success']),
        ('net-routes-create', ZRR['error']),
        ('net-routes-create', ZRR['success']),
        # REST get/create/delete error.
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['generic_error']),
        ('POST', 'network/ip/routes', SRR['generic_error']),
        ('DELETE', 'network/ip/routes/12345', SRR['generic_error']),
        # REST modify error.
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['net_routes_record']),
        ('DELETE', 'network/ip/routes/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success']),
        ('POST', 'network/ip/routes', SRR['generic_error']),
        ('POST', 'network/ip/routes', SRR['success']),
    ])
    net_route_obj = create_module(net_route_module, DEFAULT_ARGS)
    assert 'Error fetching net route' in expect_and_capture_ansible_exception(net_route_obj.get_net_route, 'fail')['msg']
    assert 'Error creating net route' in expect_and_capture_ansible_exception(net_route_obj.create_net_route, 'fail')['msg']
    current = {'destination': '', 'gateway': ''}
    assert 'Error deleting net route' in expect_and_capture_ansible_exception(net_route_obj.delete_net_route, 'fail', current)['msg']
    error = 'Error modifying net route'
    assert error in create_and_apply(net_route_module, DEFAULT_ARGS, {'metric': 80}, fail=True)['msg']

    net_route_obj = create_module(net_route_module, DEFAULT_ARGS, {'use_rest': 'always'})
    assert 'Error fetching net route' in expect_and_capture_ansible_exception(net_route_obj.get_net_route, 'fail')['msg']
    assert 'Error creating net route' in expect_and_capture_ansible_exception(net_route_obj.create_net_route, 'fail')['msg']
    current = {'uuid': '12345'}
    assert 'Error deleting net route' in expect_and_capture_ansible_exception(net_route_obj.delete_net_route, 'fail', current)['msg']
    assert error in create_and_apply(net_route_module, DEFAULT_ARGS, {'metric': 80, 'use_rest': 'always'}, fail=True)['msg']


def test_rest_successfully_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['empty_records']),
        ('POST', 'network/ip/routes', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['net_routes_record'])
    ])
    assert create_and_apply(net_route_module, DEFAULT_ARGS, {'use_rest': 'always'})['changed']
    assert not create_and_apply(net_route_module, DEFAULT_ARGS, {'use_rest': 'always'})['changed']


def test_rest_successfully_create_cluster_scope():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['empty_records']),
        ('POST', 'network/ip/routes', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['net_routes_cluster']),
    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['vserver']
    assert create_and_apply(net_route_module, DEFAULT_ARGS_COPY, {'use_rest': 'always'})['changed']
    assert not create_and_apply(net_route_module, DEFAULT_ARGS_COPY, {'use_rest': 'always'})['changed']


def test_rest_successfully_destroy():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['net_routes_record']),
        ('DELETE', 'network/ip/routes/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['empty_records']),
    ])
    args = {'use_rest': 'always', 'state': 'absent'}
    assert create_and_apply(net_route_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(net_route_module, DEFAULT_ARGS, args)['changed']


def test_rest_successfully_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['empty_records']),
        ('GET', 'network/ip/routes', SRR['net_routes_record']),
        ('DELETE', 'network/ip/routes/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success']),
        ('POST', 'network/ip/routes', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['modified_record'])
    ])
    args = {'use_rest': 'always', 'metric': '90', 'from_destination': '176.0.0.0/24', 'destination': '0.0.0.0/24'}
    assert create_and_apply(net_route_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(net_route_module, DEFAULT_ARGS, args)['changed']


def test_rest_negative_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'network/ip/routes', SRR['empty_records']),
        ('GET', 'network/ip/routes', SRR['empty_records'])
    ])
    error = 'Error modifying: route 176.0.0.0/24 does not exist'
    args = {'use_rest': 'auto', 'from_destination': '176.0.0.0/24'}
    assert error in create_and_apply(net_route_module, DEFAULT_ARGS, args, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_negative_zapi_no_netapp_lib(mock_has_lib):
    mock_has_lib.return_value = False
    msg = 'Error: the python NetApp-Lib module is required.'
    assert msg in create_module(net_route_module, DEFAULT_ARGS, fail=True)['msg']


def test_negative_non_supported_option():
    error = "REST API currently does not support 'from_metric'"
    args = {'use_rest': 'always', 'from_metric': 23}
    assert error in create_module(net_route_module, DEFAULT_ARGS, args, fail=True)['msg']


def test_negative_zapi_requires_vserver():
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['vserver']
    error = "Error: vserver is a required parameter when using ZAPI"
    assert error in create_module(net_route_module, DEFAULT_ARGS_COPY, fail=True)['msg']


def test_negative_dest_format():
    error = "Error: Expecting '/' in '1.2.3.4'."
    assert error in create_module(net_route_module, DEFAULT_ARGS, {'destination': '1.2.3.4'}, fail=True)['msg']


def test_negative_from_dest_format():
    args = {'destination': '1.2.3.4', 'from_destination': '5.6.7.8'}
    error_msg = create_module(net_route_module, DEFAULT_ARGS, args, fail=True)['msg']
    msg = "Error: Expecting '/' in '1.2.3.4'."
    assert msg in error_msg
    msg = "Expecting '/' in '5.6.7.8'."
    assert msg in error_msg
