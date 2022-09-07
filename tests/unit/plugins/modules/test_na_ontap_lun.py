# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    call_main, create_module, expect_and_capture_ansible_exception, patch_ansible
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_error, build_zapi_response, zapi_error_message, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_lun import NetAppOntapLUN as my_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def lun_info(name, next_tag=None):
    info = {
        'num-records': 1,
        'attributes-list': [{
            'lun_info': {
                'path': "/what/ever/%s" % name,
                'size': 5368709120,
                'is-space-alloc-enabled': "false",
                'is-space-reservation-enabled': "true",
                'multiprotocol-type': 'linux',
                'qos-policy-group': 'qospol',
                'qos-adaptive-policy-group': 'qosadppol',
            }
        }]
    }
    if next_tag:
        info['next-tag'] = next_tag
    return info


ZRR = zapi_responses({
    'lun_info': build_zapi_response(lun_info('lun_name')),
    'lun_info_from': build_zapi_response(lun_info('lun_from_name')),
    'lun_info_with_tag': build_zapi_response(lun_info('lun_name', 'more to come')),
    'error_9042': build_zapi_error(9042, 'new size == old size, more or less'),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'use_rest',
    'name': 'lun_name',
    'vserver': 'lunsvm_name',
}


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_NETAPP_LIB', False)
def test_module_fail_when_netapp_lib_missing():
    ''' required lib missing '''
    module_args = {
        'use_rest': 'never',
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never'
    }
    print('Info: %s' % call_main(my_main, {}, module_args, fail=True)['msg'])


def test_create_error_missing_param():
    ''' Test if create throws an error if required param 'destination_vserver' is not specified'''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    msg = "Error: 'flexvol_name' option is required when using ZAPI."
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['flexvol_name'] = 'xxx'
    msg = 'size is a required parameter for create.'
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_successful_create():
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['no_records']),
        ('ZAPI', 'lun-create-by-size', ZRR['success']),
        # second create
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['no_records']),
        ('ZAPI', 'lun-create-by-size', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'comment': 'some comment',
        'flexvol_name': 'vol_name',
        'qos_adaptive_policy_group': 'new_adaptive_pol',
        'size': 5,
        'space_allocation': False,
        'space_reserve': False,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        'use_rest': 'never',
        'comment': 'some comment',
        'flexvol_name': 'vol_name',
        'os_type': 'windows',
        'qos_policy_group': 'new_pol',
        'size': 5,
        'space_allocation': False,
        'space_reserve': False,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_rename_idempotency():
    ''' Test create idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'flexvol_name': 'vol_name',
        'size': 5,
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete_lun():
    ''' Test delete and idempotency '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
        ('ZAPI', 'lun-destroy', ZRR['success']),
        # idempotency
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
        'flexvol_name': 'vol_name',
        'state': 'absent',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete_lun_no_input():
    ''' Nothing to delete! '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never',
        'state': 'absent',
    }
    msg = "Error: 'flexvol_name' option is required when using ZAPI."
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_successful_resize():
    ''' Test successful resize '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
        ('ZAPI', 'lun-resize', ZRR['success']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
        ('ZAPI', 'lun-resize', ZRR['error_9042']),
    ])
    module_args = {
        'use_rest': 'never',
        'flexvol_name': 'vol_name',
        'size': 7
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify():
    ''' Test successful modify '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
        ('ZAPI', 'lun-set-comment', ZRR['success']),
        ('ZAPI', 'lun-set-qos-policy-group', ZRR['success']),
        ('ZAPI', 'lun-set-space-alloc', ZRR['success']),
        # second call
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
        ('ZAPI', 'lun-set-comment', ZRR['success']),
        ('ZAPI', 'lun-set-qos-policy-group', ZRR['success']),
        ('ZAPI', 'lun-set-space-reservation-info', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'comment': 'some comment',
        'flexvol_name': 'vol_name',
        'qos_policy_group': 'new_pol',
        'space_allocation': True,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        'use_rest': 'never',
        'comment': 'some comment',
        'flexvol_name': 'vol_name',
        'qos_adaptive_policy_group': 'new_adaptive_pol',
        'space_allocation': False,
        'space_reserve': False,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_negative_modify():
    ''' Test successful modify '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'flexvol_name': 'vol_name',
        'comment': 'some comment',
        'os_type': 'windows',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == 'os_type cannot be modified: current: linux, desired: windows'


def test_successful_rename():
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['no_records']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info_from']),
        ('ZAPI', 'lun-move', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'flexvol_name': 'vol_name',
        'from_name': 'lun_from_name'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_failed_rename():
    ''' Test failed rename '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'lun-get-iter', ZRR['no_records']),
        ('ZAPI', 'lun-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
        'flexvol_name': 'vol_name',
        'from_name': 'lun_from_name'
    }
    msg = 'Error renaming lun: lun_from_name does not exist'
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_zapi_errors():
    register_responses([
        # get error
        ('ZAPI', 'lun-get-iter', ZRR['error']),
        # error on next tag
        ('ZAPI', 'lun-get-iter', ZRR['lun_info_with_tag']),
        ('ZAPI', 'lun-get-iter', ZRR['lun_info_with_tag']),
        ('ZAPI', 'lun-get-iter', ZRR['error']),
        # create error
        ('ZAPI', 'lun-create-by-size', ZRR['error']),
        # resize error
        ('ZAPI', 'lun-resize', ZRR['error']),
        # rename error
        ('ZAPI', 'lun-move', ZRR['error']),
        # modify error
        ('ZAPI', 'lun-set-space-reservation-info', ZRR['error']),
        # delete error
        ('ZAPI', 'lun-destroy', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
        'flexvol_name': 'vol_name',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    msg = 'Error fetching luns for vol_name'
    assert zapi_error_message(msg) == expect_and_capture_ansible_exception(my_obj.get_luns, 'fail')['msg']
    assert zapi_error_message(msg) == expect_and_capture_ansible_exception(my_obj.get_luns, 'fail')['msg']

    my_obj.parameters['size'] = 123456
    msg = 'Error provisioning lun lun_name of size 123456'
    assert zapi_error_message(msg) == expect_and_capture_ansible_exception(my_obj.create_lun, 'fail')['msg']

    msg = 'Error resizing lun path'
    assert zapi_error_message(msg) == expect_and_capture_ansible_exception(my_obj.resize_lun, 'fail', 'path')['msg']

    my_obj.parameters.pop('size')
    msg = 'Error moving lun old_path'
    assert zapi_error_message(msg) == expect_and_capture_ansible_exception(my_obj.rename_lun, 'fail', 'old_path', 'new_path')['msg']

    msg = 'Error setting lun option space_reserve'
    assert zapi_error_message(msg) == expect_and_capture_ansible_exception(my_obj.modify_lun, 'fail', 'path', {'space_reserve': True})['msg']

    msg = 'Error deleting lun path'
    assert zapi_error_message(msg) == expect_and_capture_ansible_exception(my_obj.delete_lun, 'fail', 'path')['msg']
