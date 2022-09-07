# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_nvme_subsystem '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    expect_and_capture_ansible_exception, call_main, create_module, patch_ansible
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_error_message, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_nvme_subsystem import NetAppONTAPNVMESubsystem as my_module, main as my_main

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

subsystem_info = {
    'attributes-list': [{'nvme-target-subsystem-map-info': {'path': 'abcd/vol'}},
                        {'nvme-target-subsystem-map-info': {'path': 'xyz/vol'}}]}

subsystem_info_one_path = {
    'attributes-list': [{'nvme-target-subsystem-map-info': {'path': 'abcd/vol'}}]}

subsystem_info_one_host = {
    'attributes-list': [{'nvme-target-subsystem-map-info': {'host-nqn': 'host-nqn'}}]}

ZRR = zapi_responses({
    'subsystem_info': build_zapi_response(subsystem_info, 2),
    'subsystem_info_one_path': build_zapi_response(subsystem_info_one_path, 1),
    'subsystem_info_one_host': build_zapi_response(subsystem_info_one_host, 1),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'never',
    'subsystem': 'subsystem',
    'vserver': 'vserver',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('subsystem')
    error = 'missing required arguments: subsystem'
    assert error in call_main(my_main, args, fail=True)['msg']


def test_ensure_get_called():
    ''' test get_subsystem()  for non-existent subsystem'''
    register_responses([
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_subsystem() is None


def test_ensure_get_called_existing():
    ''' test get_subsystem()  for existing subsystem'''
    register_responses([
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['subsystem_info']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_subsystem()


def test_successful_create():
    ''' creating subsystem and testing idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['no_records']),
        ('ZAPI', 'nvme-subsystem-create', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['subsystem_info']),
        # idempptency
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['subsystem_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'ostype': 'windows'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_delete():
    ''' deleting subsystem and testing idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['subsystem_info']),
        ('ZAPI', 'nvme-subsystem-delete', ZRR['success']),
        # idempptency
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
        'state': 'absent',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_ensure_get_host_map_called():
    ''' test get_subsystem_host_map()  for non-existent subsystem'''
    register_responses([
        ('ZAPI', 'nvme-subsystem-map-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_subsystem_host_map('paths') is None


def test_ensure_get_host_map_called_existing():
    ''' test get_subsystem_host_map()  for existing subsystem'''
    register_responses([
        ('ZAPI', 'nvme-subsystem-map-get-iter', ZRR['subsystem_info']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_subsystem_host_map('paths')


def test_successful_add():
    ''' adding subsystem host/map and testing idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['subsystem_info']),
        ('ZAPI', 'nvme-subsystem-host-get-iter', ZRR['no_records']),
        ('ZAPI', 'nvme-subsystem-map-get-iter', ZRR['no_records']),
        ('ZAPI', 'nvme-subsystem-host-add', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-map-add', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-map-add', ZRR['success']),
        # idempptency
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['subsystem_info']),
        ('ZAPI', 'nvme-subsystem-host-get-iter', ZRR['subsystem_info_one_host']),
        ('ZAPI', 'nvme-subsystem-map-get-iter', ZRR['subsystem_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'ostype': 'windows',
        'paths': ['abcd/vol', 'xyz/vol'],
        'hosts': 'host-nqn'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_remove():
    ''' removing subsystem host/map and testing idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['subsystem_info']),
        ('ZAPI', 'nvme-subsystem-map-get-iter', ZRR['subsystem_info']),
        ('ZAPI', 'nvme-subsystem-map-remove', ZRR['success']),
        # idempptency
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['subsystem_info_one_path']),
        ('ZAPI', 'nvme-subsystem-map-get-iter', ZRR['subsystem_info_one_path']),
    ])
    module_args = {
        'use_rest': 'never',
        'paths': ['abcd/vol'],
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_netapp_lib_error(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    module_args = {
        "use_rest": "never"
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_error_handling():
    ''' test error handling on ZAPI calls '''
    register_responses([
        ('ZAPI', 'nvme-subsystem-get-iter', ZRR['error']),
        ('ZAPI', 'nvme-subsystem-create', ZRR['error']),
        ('ZAPI', 'nvme-subsystem-delete', ZRR['error']),
        ('ZAPI', 'nvme-subsystem-map-get-iter', ZRR['error']),
        ('ZAPI', 'nvme-subsystem-host-add', ZRR['error']),
        ('ZAPI', 'nvme-subsystem-map-add', ZRR['error']),
        ('ZAPI', 'nvme-subsystem-host-remove', ZRR['error']),
        ('ZAPI', 'nvme-subsystem-map-remove', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
        'ostype': 'windows'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = zapi_error_message('Error fetching subsystem info')
    assert error in expect_and_capture_ansible_exception(my_obj.get_subsystem, 'fail')['msg']
    error = zapi_error_message('Error creating subsystem for subsystem')
    assert error in expect_and_capture_ansible_exception(my_obj.create_subsystem, 'fail')['msg']
    error = zapi_error_message('Error deleting subsystem for subsystem')
    assert error in expect_and_capture_ansible_exception(my_obj.delete_subsystem, 'fail')['msg']
    error = zapi_error_message('Error fetching subsystem path info')
    assert error in expect_and_capture_ansible_exception(my_obj.get_subsystem_host_map, 'fail', 'paths')['msg']
    error = zapi_error_message('Error adding hostname for subsystem subsystem')
    assert error in expect_and_capture_ansible_exception(my_obj.add_subsystem_host_map, 'fail', ['hostname'], 'hosts')['msg']
    error = zapi_error_message('Error adding pathname for subsystem subsystem')
    assert error in expect_and_capture_ansible_exception(my_obj.add_subsystem_host_map, 'fail', ['pathname'], 'paths')['msg']
    error = zapi_error_message('Error removing hostname for subsystem subsystem')
    assert error in expect_and_capture_ansible_exception(my_obj.remove_subsystem_host_map, 'fail', ['hostname'], 'hosts')['msg']
    error = zapi_error_message('Error removing pathname for subsystem subsystem')
    assert error in expect_and_capture_ansible_exception(my_obj.remove_subsystem_host_map, 'fail', ['pathname'], 'paths')['msg']
