# (c) 2018, NTT Europe Ltd.
# (c) 2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit test for Ansible module: na_ontap_ipspace """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ipspace \
    import NetAppOntapIpspace as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


DEFAULT_ARGS = {
    "hostname": "10.10.10.10",
    "username": "admin",
    "password": "netapp1!",
    "validate_certs": "no",
    "https": "yes",
    "state": "present",
    "name": "test_ipspace"
}


ipspace_info = {
    'num-records': 1,
    'attributes-list': {
        'net-ipspaces-info': {
            'ipspace': 'test_ipspace'
        }
    }
}

ipspace_info_renamed = {
    'num-records': 1,
    'attributes-list': {
        'net-ipspaces-info': {
            'ipspace': 'test_ipspace_renamed'
        }
    }
}

ZRR = zapi_responses({
    'ipspace_info': build_zapi_response(ipspace_info),
    'ipspace_info_renamed': build_zapi_response(ipspace_info_renamed),
})

SRR = rest_responses({
    'ipspace_record': (200, {'records': [{
        "name": "test_ipspace",
        "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"}]}, None),
    'ipspace_record_renamed': (200, {'records': [{
        "name": "test_ipspace_renamed",
        "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"}]}, None)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_module()
    msg = 'missing required arguments:'
    assert msg in exc.value.args[0]['msg']


def test_get_ipspace_iscalled():
    ''' test if get_ipspace() is called '''
    register_responses([
        ('net-ipspaces-get-iter', ZRR['empty'])
    ])
    ipsace_obj = create_module(my_module, DEFAULT_ARGS, {'use_rest': 'never'})
    result = ipsace_obj.get_ipspace('dummy')
    assert result is None


def test_ipspace_apply_iscalled():
    ''' test if apply() is called - create and rename'''
    register_responses([
        # create
        ('net-ipspaces-get-iter', ZRR['empty']),
        ('net-ipspaces-create', ZRR['success']),
        # create idempotent check
        ('net-ipspaces-get-iter', ZRR['ipspace_info']),
        # rename
        ('net-ipspaces-get-iter', ZRR['empty']),
        ('net-ipspaces-get-iter', ZRR['ipspace_info']),
        ('net-ipspaces-rename', ZRR['success']),
        # rename idempotent check
        ('net-ipspaces-get-iter', ZRR['ipspace_info_renamed']),
        # delete
        ('net-ipspaces-get-iter', ZRR['ipspace_info']),
        ('net-ipspaces-destroy', ZRR['success'])
    ])
    args = {'use_rest': 'never'}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    args['from_name'] = 'test_ipspace'
    args['name'] = 'test_ipspace_renamed'
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    args = {'use_rest': 'never', 'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_successful_create_rest():
    ''' Test successful create and idempotent check'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'network/ipspaces', SRR['empty_records']),
        ('POST', 'network/ipspaces', SRR['success']),
        # idempotent
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'network/ipspaces', SRR['ipspace_record'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_successful_delete_rest():
    ''' Test successful delete and idempotent check'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'network/ipspaces', SRR['ipspace_record']),
        ('DELETE', 'network/ipspaces/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success']),
        # idempotent
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'network/ipspaces', SRR['empty_records'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_successful_rename_rest():
    ''' Test successful rename and idempotent check'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'network/ipspaces', SRR['empty_records']),
        ('GET', 'network/ipspaces', SRR['ipspace_record']),
        ('PATCH', 'network/ipspaces/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success']),
        # idempotent
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'network/ipspaces', SRR['ipspace_record_renamed'])
    ])
    args = {'from_name': 'test_ipspace', 'name': 'test_ipspace_renamed'}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_if_all_methods_catch_exception_zapi_rest():
    register_responses([
        # zapi
        ('net-ipspaces-get-iter', ZRR['error']),
        ('net-ipspaces-create', ZRR['error']),
        ('net-ipspaces-rename', ZRR['error']),
        ('net-ipspaces-destroy', ZRR['error']),
        # REST
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'network/ipspaces', SRR['generic_error']),
        ('POST', 'network/ipspaces', SRR['generic_error']),
        ('PATCH', 'network/ipspaces/abdcdef', SRR['generic_error']),
        ('DELETE', 'network/ipspaces/abdcdef', SRR['generic_error'])

    ])
    my_obj = create_module(my_module, DEFAULT_ARGS, {'from_name': 'test_ipspace_rename', 'use_rest': 'never'})
    assert 'Error getting ipspace' in expect_and_capture_ansible_exception(my_obj.get_ipspace, 'fail')['msg']
    assert 'Error provisioning ipspace' in expect_and_capture_ansible_exception(my_obj.create_ipspace, 'fail')['msg']
    assert 'Error renaming ipspace' in expect_and_capture_ansible_exception(my_obj.rename_ipspace, 'fail')['msg']
    assert 'Error removing ipspace' in expect_and_capture_ansible_exception(my_obj.delete_ipspace, 'fail')['msg']

    my_obj = create_module(my_module, DEFAULT_ARGS, {'from_name': 'test_ipspace_rename'})
    my_obj.uuid = 'abdcdef'
    assert 'Error getting ipspace' in expect_and_capture_ansible_exception(my_obj.get_ipspace, 'fail')['msg']
    assert 'Error provisioning ipspace' in expect_and_capture_ansible_exception(my_obj.create_ipspace, 'fail')['msg']
    assert 'Error renaming ipspace' in expect_and_capture_ansible_exception(my_obj.rename_ipspace, 'fail')['msg']
    assert 'Error removing ipspace' in expect_and_capture_ansible_exception(my_obj.delete_ipspace, 'fail')['msg']
