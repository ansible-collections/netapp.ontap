''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_service_processor_network \
    import NetAppOntapServiceProcessorNetwork as sp_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def mock_args(enable=False, use_rest=False):
    data = {
        'node': 'test-vsim1',
        'is_enabled': enable,
        'address_type': 'ipv4',
        'hostname': 'host',
        'username': 'admin',
        'password': 'password',
        'use_rest': 'never'
    }
    if enable is True:
        data['is_enabled'] = enable
        data['ip_address'] = '1.1.1.1'
        data['gateway_ip_address'] = '2.2.2.2'
        data['netmask'] = '255.255.248.0'
        data['dhcp'] = 'none'
    if use_rest:
        data['use_rest'] = 'always'
    return data


sp_enabled_info = {
    'num-records': 1,
    'attributes-list': {
        'service-processor-network-info': {
            'node': 'test-vsim1',
            'is-enabled': 'true',
            'address-type': 'ipv4',
            'dhcp': 'v4',
            'gateway-ip-address': '2.2.2.2',
            'netmask': '255.255.248.0',
            'ip-address': '1.1.1.1',
            'setup-status': 'succeeded'
        }
    }
}

sp_disabled_info = {
    'num-records': 1,
    'attributes-list': {
        'service-processor-network-info': {
            'node-name': 'test-vsim1',
            'is-enabled': 'false',
            'address-type': 'ipv4',
            'setup-status': 'not_setup'
        }
    }
}

sp_status_info = {
    'num-records': 1,
    'attributes-list': {
        'service-processor-network-info': {
            'node-name': 'test-vsim1',
            'is-enabled': 'false',
            'address-type': 'ipv4',
            'setup-status': 'in_progress'
        }
    }
}

ZRR = zapi_responses({
    'sp_enabled_info': build_zapi_response(sp_enabled_info),
    'sp_disabled_info': build_zapi_response(sp_disabled_info),
    'sp_status_info': build_zapi_response(sp_status_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "node", "address_type"]
    error = create_module(sp_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_modify_error_on_disabled_sp():
    ''' a more interesting test '''
    register_responses([
        ('service-processor-network-get-iter', ZRR['sp_disabled_info'])
    ])
    error = 'Error: Cannot modify a service processor network if it is disabled in ZAPI'
    assert error in create_and_apply(sp_module, mock_args(), {'ip_address': '1.1.1.1'}, 'error')['msg']


def test_modify_error_on_disabe_dhcp_without_ip():
    ''' a more interesting test '''
    register_responses([
        ('service-processor-network-get-iter', ZRR['sp_enabled_info'])
    ])
    error = 'Error: To disable dhcp, configure ip-address, netmask and gateway details manually.'
    assert error in create_and_apply(sp_module, mock_args(enable=True), None, fail=True)['msg']


def test_modify_error_of_params_disabled_false():
    ''' a more interesting test '''
    register_responses([
        ('service-processor-network-get-iter', ZRR['sp_enabled_info'])
    ])
    error = 'Error: Cannot modify any other parameter for a service processor network if option "is_enabled" is set to false.'
    assert error in create_and_apply(sp_module, mock_args(), {'ip_address': '2.1.1.1'}, 'error')['msg']


def test_modify_sp():
    ''' a more interesting test '''
    register_responses([
        ('service-processor-network-get-iter', ZRR['sp_enabled_info']),
        ('service-processor-network-modify', ZRR['success'])
    ])
    assert create_and_apply(sp_module, mock_args(enable=True), {'ip_address': '3.3.3.3'})['changed']


@patch('time.sleep')
def test_modify_sp_wait(sleep):
    ''' a more interesting test '''
    register_responses([
        ('service-processor-network-get-iter', ZRR['sp_enabled_info']),
        ('service-processor-network-modify', ZRR['success']),
        ('service-processor-network-get-iter', ZRR['sp_enabled_info'])
    ])
    args = {'ip_address': '3.3.3.3', 'wait_for_completion': True}
    assert create_and_apply(sp_module, mock_args(enable=True), args)['changed']


def test_non_existing_sp():
    register_responses([
        ('service-processor-network-get-iter', ZRR['no_records'])
    ])
    error = 'Error No Service Processor for node: test-vsim1'
    assert create_and_apply(sp_module, mock_args(), fail=True)['msg']


@patch('time.sleep')
def test_wait_on_sp_status(sleep):
    register_responses([
        ('service-processor-network-get-iter', ZRR['sp_enabled_info']),
        ('service-processor-network-modify', ZRR['success']),
        ('service-processor-network-get-iter', ZRR['sp_status_info']),
        ('service-processor-network-get-iter', ZRR['sp_status_info']),
        ('service-processor-network-get-iter', ZRR['sp_status_info']),
        ('service-processor-network-get-iter', ZRR['sp_status_info']),
        ('service-processor-network-get-iter', ZRR['sp_enabled_info'])
    ])
    args = {'ip_address': '3.3.3.3', 'wait_for_completion': True}
    assert create_and_apply(sp_module, mock_args(enable=True), args)['changed']


def test_if_all_methods_catch_exception():
    ''' test error zapi - get/modify'''
    register_responses([
        ('service-processor-network-get-iter', ZRR['error']),
        ('service-processor-network-get-iter', ZRR['error']),
        ('service-processor-network-modify', ZRR['error'])
    ])
    sp_obj = create_module(sp_module, mock_args())

    assert 'Error fetching service processor network info' in expect_and_capture_ansible_exception(sp_obj.get_service_processor_network, 'fail')['msg']
    assert 'Error fetching service processor network status' in expect_and_capture_ansible_exception(sp_obj.get_sp_network_status, 'fail')['msg']
    assert 'Error modifying service processor network' in expect_and_capture_ansible_exception(sp_obj.modify_service_processor_network, 'fail', {})['msg']


SRR = rest_responses({
    'sp_enabled_info': (200, {"records": [{
        'name': 'ansdev-stor-1',
        'service_processor': {
            'dhcp_enabled': False,
            'firmware_version': '3.10',
            'ipv4_interface': {
                'address': '1.1.1.1',
                'gateway': '2.2.2.2',
                'netmask': '255.255.248.0'
            },
            'link_status': 'up',
            'state': 'online'
        },
        'uuid': '5dd7aed0'}
    ]}, None),
    'sp_disabled_info': (200, {"records": [{
        'name': 'ansdev-stor-1',
        'service_processor': {
            'firmware_version': '3.10',
            'link_status': 'up',
            'state': 'online'
        },
        'uuid': '5dd7aed0'}
    ]}, None)
})


def test_modify_sp_rest():
    ''' modify sp in rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'cluster/nodes', SRR['sp_enabled_info']),
        ('PATCH', 'cluster/nodes/5dd7aed0', SRR['success'])
    ])
    assert create_and_apply(sp_module, mock_args(enable=True, use_rest=True), {'ip_address': '3.3.3.3'})['changed']


def test_non_existing_sp_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'cluster/nodes', SRR['empty_records'])
    ])
    error = 'Error No Service Processor for node: test-vsim1'
    assert create_and_apply(sp_module, mock_args(enable=True, use_rest=True), fail=True)['msg']


def test_if_all_methods_catch_exception_rest():
    ''' test error zapi - get/modify'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'cluster/nodes', SRR['generic_error']),
        ('PATCH', 'cluster/nodes/5dd7aed0', SRR['generic_error'])
    ])
    sp_obj = create_module(sp_module, mock_args(use_rest=True))
    sp_obj.uuid = '5dd7aed0'
    assert 'Error fetching service processor network info' in expect_and_capture_ansible_exception(sp_obj.get_service_processor_network, 'fail')['msg']
    assert 'Error modifying service processor network' in expect_and_capture_ansible_exception(sp_obj.modify_service_processor_network, 'fail', {})['msg']


def test_disable_sp_rest():
    ''' disable not supported in REST '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'cluster/nodes', SRR['sp_enabled_info'])
    ])
    error = 'Error: disable service processor network status not allowed in REST'
    assert error in create_and_apply(sp_module, mock_args(enable=True, use_rest=True), {'is_enabled': False}, 'fail')['msg']


def test_enable_sp_rest_without_ip_or_dhcp():
    ''' enable requires ip or dhcp in REST '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'cluster/nodes', SRR['sp_disabled_info'])
    ])
    error = 'Error: enable service processor network requires dhcp or ip_address,netmask,gateway details in REST.'
    assert error in create_and_apply(sp_module, mock_args(use_rest=True), {'is_enabled': True}, 'fail')['msg']


@patch('time.sleep')
def test_wait_on_sp_status_rest(sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'cluster/nodes', SRR['sp_disabled_info']),
        ('PATCH', 'cluster/nodes/5dd7aed0', SRR['success']),
        ('GET', 'cluster/nodes', SRR['sp_disabled_info']),
        ('GET', 'cluster/nodes', SRR['sp_disabled_info']),
        ('GET', 'cluster/nodes', SRR['sp_enabled_info'])
    ])
    args = {'ip_address': '1.1.1.1', 'wait_for_completion': True}
    assert create_and_apply(sp_module, mock_args(enable=True, use_rest=True), args)['changed']


def test_error_dhcp_for_address_type_ipv6():
    ''' dhcp cannot be disabled if manual interface options not set'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1'])
    ])
    error = 'Error: dhcp cannot be set for address_type: ipv6'
    args = {'address_type': 'ipv6', 'dhcp': 'v4'}
    assert error in create_module(sp_module, mock_args(use_rest=True), args, fail=True)['msg']


def test_error_dhcp_enable_and_set_manual_options_rest():
    ''' dhcp enable and manual interface options set together'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1'])
    ])
    error = "Error: set dhcp v4 or all of 'ip_address, gateway_ip_address, netmask'."
    args = {'dhcp': 'v4'}
    assert error in create_module(sp_module, mock_args(use_rest=True, enable=True), args, fail=True)['msg']
