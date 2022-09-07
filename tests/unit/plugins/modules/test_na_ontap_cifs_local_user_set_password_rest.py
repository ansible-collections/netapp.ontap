# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    patch_ansible, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_user_set_password \
    import NetAppONTAPCifsSetPassword as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'svm_uuid': (200, {"records": [
        {
            'uuid': 'e3cb5c7f-cd20'
        }], "num_records": 1}, None),
    'local_user_sid': (200, {"records": [{'sid': '1234-sd'}]}, None)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'user_name': 'carchi8py',
    'user_password': 'p@SSWord',
    'vserver': 'vserver'
}


def test_change_password():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/local-users', SRR['local_user_sid']),
        ('PATCH', 'protocols/cifs/local-users/e3cb5c7f-cd20/1234-sd', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {})['changed']


def test_get_svm_uuid_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.get_svm_uuid, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error fetching vserver vserver: calling: svm/svms: got Expected error.' == error


def test_get_cifs_local_users_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-users', SRR['generic_error']),
        # 2nd call
        ('GET', 'protocols/cifs/local-users', SRR['zero_records']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.get_user_sid, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error fetching cifs/local-user carchi8py: calling: protocols/cifs/local-users: got Expected error.' == error
    # no user
    error = 'Error no cifs/local-user with name carchi8py'
    assert error in expect_and_capture_ansible_exception(my_obj.get_user_sid, 'fail')['msg']


def test_patch_cifs_local_users_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/local-users', SRR['local_user_sid']),
        ('PATCH', 'protocols/cifs/local-users/e3cb5c7f-cd20/1234-sd', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.cifs_local_set_passwd_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error change password for user carchi8py: calling: protocols/cifs/local-users/e3cb5c7f-cd20/1234-sd: got Expected error.' == error


def test_fail_old_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'use_rest': 'always'
    }
    error = 'Error: REST requires ONTAP 9.10.1 or later for protocols/cifs/local-users APIs.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
