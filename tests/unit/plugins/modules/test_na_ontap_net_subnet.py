# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    call_main, create_module, expect_and_capture_ansible_exception, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_error_message, zapi_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_subnet \
    import NetAppOntapSubnet as my_module, main as my_main      # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


DEFAULT_ARGS = {
    'name': 'test_subnet',
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'broadcast_domain': 'Default',
    'gateway': '10.0.0.1',
    'ipspace': 'Default',
    'subnet': '10.0.0.0/24',
    'ip_ranges': ['10.0.0.10-10.0.0.20', '10.0.0.30']
}


def subnet_info(name):
    return {
        'num-records': 1,
        'attributes-list': {
            'net-subnet-info': {
                'broadcast-domain': DEFAULT_ARGS['broadcast_domain'],
                'gateway': DEFAULT_ARGS['gateway'],
                'ip-ranges': [{'ip-range': elem} for elem in DEFAULT_ARGS['ip_ranges']],
                'ipspace': DEFAULT_ARGS['ipspace'],
                'subnet': DEFAULT_ARGS['subnet'],
                'subnet-name': name,
            }
        }
    }


ZRR = zapi_responses({
    'subnet_info': build_zapi_response(subnet_info(DEFAULT_ARGS['name'])),
    'subnet_info_renamed': build_zapi_response(subnet_info('new_test_subnet')),
})


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_NETAPP_LIB', False)
def test_module_fail_when_netapp_lib_missing():
    ''' required lib missing '''
    module_args = {
        'use_rest': 'never',
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_successful_create():
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['no_records']),
        ('ZAPI', 'net-subnet-create', ZRR['success']),
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['subnet_info']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # idempotency
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_delete():
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['subnet_info']),
        ('ZAPI', 'net-subnet-destroy', ZRR['success']),
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
        'state': 'absent',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # idempotency
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify():
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['subnet_info']),
        ('ZAPI', 'net-subnet-modify', ZRR['success']),
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['subnet_info']),
    ])
    module_args = {
        'use_rest': 'always',
        'ip_ranges': ['10.0.0.10-10.0.0.25', '10.0.0.30'],
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # idempotency
    module_args.pop('ip_ranges')
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_rename():
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['no_records']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['subnet_info']),
        ('ZAPI', 'net-subnet-rename', ZRR['success']),
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['subnet_info']),
    ])
    module_args = {
        'use_rest': 'always',
        'from_name': DEFAULT_ARGS['name'],
        'name': 'new_test_subnet'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # idempotency
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_negative_modify_broadcast_domain():
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['subnet_info']),
    ])
    module_args = {
        'use_rest': 'always',
        'broadcast_domain': 'cannot change',
    }
    error = 'Error modifying subnet test_subnet: cannot modify broadcast_domain parameter, desired "cannot change", currrent "Default"'
    assert error == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_rename():
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['no_records']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'always',
        'from_name': DEFAULT_ARGS['name'],
        'name': 'new_test_subnet'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == 'Error renaming: subnet test_subnet does not exist'


def test_negative_create():
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['no_records']),
        # second test
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['no_records']),
        # third test
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-subnet-get-iter', ZRR['no_records']),
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('subnet')
    module_args = {
        'use_rest': 'always',
    }
    assert call_main(my_main, args, module_args, fail=True)['msg'] == 'Error - missing required arguments: subnet.'
    args = dict(DEFAULT_ARGS)
    args.pop('broadcast_domain')
    assert call_main(my_main, args, module_args, fail=True)['msg'] == 'Error - missing required arguments: broadcast_domain.'
    args.pop('subnet')
    assert call_main(my_main, args, module_args, fail=True)['msg'] == 'Error - missing required arguments: subnet.'


def test_if_all_methods_catch_exception():
    register_responses([
        ('ZAPI', 'net-subnet-create', ZRR['error']),
        ('ZAPI', 'net-subnet-destroy', ZRR['error']),
        ('ZAPI', 'net-subnet-modify', ZRR['error']),
        ('ZAPI', 'net-subnet-rename', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert zapi_error_message('Error creating subnet test_subnet') == expect_and_capture_ansible_exception(my_obj.create_subnet, 'fail')['msg']
    assert zapi_error_message('Error deleting subnet test_subnet') == expect_and_capture_ansible_exception(my_obj.delete_subnet, 'fail')['msg']
    assert zapi_error_message('Error modifying subnet test_subnet') == expect_and_capture_ansible_exception(my_obj.modify_subnet, 'fail')['msg']
    assert zapi_error_message('Error renaming subnet test_subnet') == expect_and_capture_ansible_exception(my_obj.rename_subnet, 'fail')['msg']
