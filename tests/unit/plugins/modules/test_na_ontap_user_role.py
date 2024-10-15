# (c) 2018-2024, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_user_role \
    import NetAppOntapUserRole as role_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def build_role_info(access_level='all'):
    return {
        'num-records': 1,
        'attributes-list': {
            'security-login-role-info': {
                'access-level': access_level,
                'command-directory-name': 'volume',
                'role-name': 'testrole',
                'role-query': 'show',
                'vserver': 'ansible'
            }
        }
    }


ZRR = zapi_responses({
    'build_role_info': build_zapi_response(build_role_info()),
    'build_role_modified': build_zapi_response(build_role_info('none'))
})

DEFAULT_ARGS = {
    'name': 'testrole',
    'vserver': 'ansible',
    'command_directory_name': 'volume',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'https': 'False',
    'use_rest': 'never'
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "name"]
    error = create_module(role_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_get_nonexistent_policy():
    ''' Test if get_role returns None for non-existent role '''
    register_responses([
        ('ZAPI', 'security-login-role-get-iter', ZRR['empty']),
    ])
    my_obj = create_module(role_module, DEFAULT_ARGS)
    assert my_obj.get_role() is None


def test_get_existing_role():
    ''' Test if get_role returns details for existing role '''
    register_responses([
        ('ZAPI', 'security-login-role-get-iter', ZRR['build_role_info']),
    ])
    my_obj = create_module(role_module, DEFAULT_ARGS)
    current = my_obj.get_role()
    assert current['name'] == DEFAULT_ARGS['name']


def test_successful_create():
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'security-login-role-get-iter', ZRR['empty']),
        ('ZAPI', 'security-login-role-create', ZRR['success']),
        # idempotency check
        ('ZAPI', 'security-login-role-get-iter', ZRR['build_role_info']),
    ])
    assert create_and_apply(role_module, DEFAULT_ARGS)['changed']
    assert not create_and_apply(role_module, DEFAULT_ARGS)['changed']


def test_successful_modify():
    ''' Test successful modify '''
    register_responses([
        ('ZAPI', 'security-login-role-get-iter', ZRR['build_role_info']),
        ('ZAPI', 'security-login-role-modify', ZRR['success']),
        # idempotency check
        ('ZAPI', 'security-login-role-get-iter', ZRR['build_role_modified']),
    ])
    assert create_and_apply(role_module, DEFAULT_ARGS, {'access_level': 'none'})['changed']
    assert not create_and_apply(role_module, DEFAULT_ARGS, {'access_level': 'none'})['changed']


def test_successful_delete():
    ''' Test delete existing role '''
    register_responses([
        ('ZAPI', 'security-login-role-get-iter', ZRR['build_role_info']),
        ('ZAPI', 'security-login-role-delete', ZRR['success']),
        # idempotency check
        ('ZAPI', 'security-login-role-get-iter', ZRR['empty']),
    ])
    assert create_and_apply(role_module, DEFAULT_ARGS, {'state': 'absent'})['changed']
    assert not create_and_apply(role_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('ZAPI', 'security-login-role-get-iter', ZRR['error']),
        ('ZAPI', 'security-login-role-create', ZRR['error']),
        ('ZAPI', 'security-login-role-modify', ZRR['error']),
        ('ZAPI', 'security-login-role-delete', ZRR['error'])
    ])
    my_obj = create_module(role_module, DEFAULT_ARGS)
    assert 'Error getting role' in expect_and_capture_ansible_exception(my_obj.get_role, 'fail')['msg']
    assert 'Error creating role' in expect_and_capture_ansible_exception(my_obj.create_role, 'fail')['msg']
    assert 'Error modifying role' in expect_and_capture_ansible_exception(my_obj.modify_role, 'fail', {})['msg']
    assert 'Error removing role' in expect_and_capture_ansible_exception(my_obj.delete_role, 'fail')['msg']

    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['command_directory_name']
    assert 'Error: command_directory_name is a required field' in create_module(role_module, DEFAULT_ARGS_COPY, fail=True)['msg']

    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['vserver']
    assert 'Error: vserver is a required field' in create_module(role_module, DEFAULT_ARGS_COPY, fail=True)['msg']
