# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_volume_clone'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    call_main, create_and_apply, create_module, expect_and_capture_ansible_exception, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import zapi_responses, build_zapi_response, build_zapi_error

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_clone \
    import NetAppONTAPVolumeClone as my_module, main as my_main

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

clone_info = {
    'attributes': {
        'volume-clone-info': {
            'volume': 'ansible',
            'parent-volume': 'ansible'}}}

clone_info_split_in_progress = {
    'attributes': {
        'volume-clone-info': {
            'volume': 'ansible',
            'parent-volume': 'ansible',
            'block-percentage-complete': 20,
            'blocks-scanned': 56676,
            'blocks-updated': 54588}}}

ZRR = zapi_responses({
    'clone_info': build_zapi_response(clone_info, 1),
    'clone_info_split_in_progress': build_zapi_response(clone_info_split_in_progress, 1),
    'error_no_clone': build_zapi_error(15661, 'flexclone not found.')
})

DEFAULT_ARGS = {
    'hostname': '10.10.10.10',
    'username': 'username',
    'password': 'password',
    'vserver': 'ansible',
    'volume': 'ansible',
    'parent_volume': 'ansible',
    'split': None,
    'use_rest': 'never'
}


def test_module_fail_when_required_args_missing():
    ''' test required arguments are reported as errors '''
    msg = create_module(my_module, fail=True)['msg']
    print('Info: %s' % msg)


def test_ensure_get_called():
    ''' test get_volume_clone() for non-existent volume clone'''
    register_responses([
        ('volume-clone-get', ZRR['empty'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    assert my_obj.get_volume_clone() is None


def test_ensure_get_called_existing():
    ''' test get_volume_clone() for existing volume clone'''
    register_responses([
        ('volume-clone-get', ZRR['clone_info'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    current = {'split': False}
    assert my_obj.get_volume_clone() == current


def test_ensure_get_called_no_clone_error():
    ''' test get_volume_clone() for existing volume clone'''
    register_responses([
        ('volume-clone-get', ZRR['error_no_clone'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    current = {'split': False}
    assert my_obj.get_volume_clone() is None


def test_successful_create():
    ''' test creating volume_clone without split and testing idempotency '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('volume-clone-get', ZRR['empty']),
        ('volume-clone-create', ZRR['success']),
        ('ems-autosupport-log', ZRR['empty']),
        ('volume-clone-get', ZRR['clone_info']),
    ])
    module_args = {
        'parent_snapshot': 'abc',
        'volume_type': 'dp',
        'qos_policy_group_name': 'abc',
        'junction_path': 'abc',
        'uid': '1',
        'gid': '1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_create_with_split():
    ''' test creating volume_clone with split and testing idempotency '''
    register_responses([
        # first test, create and split
        ('ems-autosupport-log', ZRR['empty']),
        ('volume-clone-get', ZRR['empty']),
        ('volume-clone-create', ZRR['success']),
        ('volume-clone-split-start', ZRR['success']),
        # second test, clone already exists but is not split
        ('ems-autosupport-log', ZRR['empty']),
        ('volume-clone-get', ZRR['clone_info']),
        ('volume-clone-split-start', ZRR['success']),
        # third test, clone already exists, split already in progress
        ('ems-autosupport-log', ZRR['empty']),
        ('volume-clone-get', ZRR['clone_info_split_in_progress']),
    ])
    module_args = {
        'parent_snapshot': 'abc',
        'volume_type': 'dp',
        'qos_policy_group_name': 'abc',
        'junction_path': 'abc',
        'uid': '1',
        'gid': '1',
        'split': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_create_with_parent_vserver():
    ''' test creating volume_clone with split and testing idempotency '''
    register_responses([
        # first test, create and split
        ('ems-autosupport-log', ZRR['empty']),
        ('volume-clone-get', ZRR['empty']),
        ('volume-clone-create', ZRR['success']),
        ('volume-clone-split-start', ZRR['success']),
        # second test, clone already exists but is not split
        ('ems-autosupport-log', ZRR['empty']),
        ('volume-clone-get', ZRR['clone_info']),
        ('volume-clone-split-start', ZRR['success']),
        # third test, clone already exists, split already in progress
        ('ems-autosupport-log', ZRR['empty']),
        ('volume-clone-get', ZRR['clone_info_split_in_progress']),
    ])
    module_args = {
        'parent_snapshot': 'abc',
        'parent_vserver': 'abc',
        'volume_type': 'dp',
        'qos_policy_group_name': 'abc',
        'space_reserve': 'volume',
        'split': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_vserver_cluster_options_give_error():
    module_args = {
        'parent_snapshot': 'abc',
        'parent_vserver': 'abc',
        'volume_type': 'dp',
        'qos_policy_group_name': 'abc',
        'junction_path': 'abc',
        'uid': '1',
        'gid': '1'
    }
    msg = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert "parameters are mutually exclusive: " in msg
    print('Info: %s' % msg)


def test_if_all_methods_catch_exception():
    ''' test if all methods catch exception '''
    register_responses([
        ('volume-clone-get', ZRR['error']),
        ('volume-clone-create', ZRR['error']),
        ('volume-clone-split-start', ZRR['error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = expect_and_capture_ansible_exception(my_obj.get_volume_clone, 'fail')['msg']
    assert 'Error fetching volume clone information ' in msg
    msg = expect_and_capture_ansible_exception(my_obj.create_volume_clone, 'fail')['msg']
    assert 'Error creating volume clone: ' in msg
    msg = expect_and_capture_ansible_exception(my_obj.start_volume_clone_split, 'fail')['msg']
    assert 'Error starting volume clone split: ' in msg


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_missing_netapp_lib(mock_has_netapp_lib):
    ''' test error when netapp_lib is missing '''
    mock_has_netapp_lib.return_value = False
    msg = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' == msg


def test_main():
    ''' validate call to main() '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('volume-clone-get', ZRR['empty']),
        ('volume-clone-create', ZRR['success']),
    ])
    assert call_main(my_main, DEFAULT_ARGS)['changed']
