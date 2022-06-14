# (c) 2019-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_motd """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_error_message, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_warning_was_raised, expect_and_capture_ansible_exception, call_main, create_module, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_motd import NetAppONTAPMotd as my_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def motd_info(msg):
    return {
        'num-records': 1,
        'attributes-list': {
            'vserver-motd-info': {
                'message': msg,
                'vserver': 'ansible',
                'is-cluster-message-enabled': 'true'}}
    }


ZRR = zapi_responses({
    'motd_info': build_zapi_response(motd_info('motd_message')),
    'motd_none': build_zapi_response(motd_info('None')),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'use_rest',
    'motd_message': 'motd_message',
    'vserver': 'ansible',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    module_args = {
    }
    print('Info: %s' % call_main(my_main, module_args, fail=True)['msg'])


def test_ensure_motd_get_called():
    ''' fetching details of motd '''
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.motd_get() is None


def test_ensure_get_called_existing():
    ''' test for existing motd'''
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_info']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.motd_get()


def test_motd_create():
    ''' test for creating motd'''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-motd-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-motd-modify-iter', ZRR['success']),
        # idempotency
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_info']),
        # modify
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-motd-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-motd-modify-iter', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['message'] = 'new_message'
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_motd_delete():
    ''' test for deleting motd'''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_info']),
        ('ZAPI', 'vserver-motd-modify-iter', ZRR['motd_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-motd-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_none']),
    ])
    module_args = {
        'state': 'absent',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['error']),
        ('ZAPI', 'vserver-motd-modify-iter', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert expect_and_capture_ansible_exception(my_obj.motd_get, 'fail')['msg'] == zapi_error_message('Error fetching motd info')
    assert expect_and_capture_ansible_exception(my_obj.modify_motd, 'fail')['msg'] == zapi_error_message('Error creating motd')


def test_rest_required():
    module_args = {
        'use_rest': 'always',
    }
    error_msg = 'netapp.ontap.na_ontap_motd is deprecated and only supports ZAPI.  Please use netapp.ontap.na_ontap_login_messages.'
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == 'Error: %s' % error_msg
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-motd-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-motd-modify-iter', ZRR['success']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-motd-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-motd-modify-iter', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'auto',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert_warning_was_raised('Falling back to ZAPI: %s' % error_msg)
    module_args = {
        'use_rest': 'NevEr',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert_warning_was_raised(error_msg)


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_NETAPP_LIB', False)
def test_module_fail_when_netapp_lib_missing():
    ''' required lib missing '''
    module_args = {
        'use_rest': 'never',
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
