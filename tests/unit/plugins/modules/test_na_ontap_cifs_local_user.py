# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_user \
    import NetAppOntapCifsLocalUser as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'local_user_sid': (200, {
        "records": [{
            "sid": "S-1-5-21-256008430-3394229847-3930036330-1001",
            "members": [{
                "name": "string"
            }],
            "name": "SMB_SERVER01\\username",
            "svm": {
                "name": "svm1",
                "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
            },
            "description": "This is a local group",
            "full_name": "User Name",
            "account_disabled": False
        }]
    }, None),
    'svm_uuid': (200, {"records": [
        {
            'uuid': 'e3cb5c7f-cd20'
        }], "num_records": 1}, None),
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'vserver',
    'name': "username"
}


def test_low_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error: na_ontap_cifs_local_user only supports REST, and requires ONTAP 9.10.1 or later.'
    assert msg in error


def test_get_svm_uuid_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.get_svm_uuid, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error fetching vserver vserver: calling: svm/svms: got Expected error.' == error


def test_get_cifs_local_user_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/local-users', SRR['zero_records']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_cifs_local_user() is None


def test_get_cifs_local_user_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/local-users', SRR['generic_error']),
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching cifs/local-user username: calling: protocols/cifs/local-users: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_cifs_local_user, 'fail')['msg']


def test_get_cifs_local_user():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/local-users', SRR['local_user_sid']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_cifs_local_user() is not None


def test_create_cifs_local_user():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/local-users', SRR['empty_records']),
        ('POST', 'protocols/cifs/local-users', SRR['empty_good'])
    ])
    module_args = {'name': 'username',
                   'user_password': 'password',
                   'account_disabled': 'False',
                   'full_name': 'User Name',
                   'description': 'Test user'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_cifs_local_user_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('POST', 'protocols/cifs/local-users', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['name'] = 'username'
    my_obj.parameters['user_password'] = 'password'
    my_obj.parameters['account_disabled'] = False
    my_obj.parameters['full_name'] = 'User Name'
    my_obj.parameters['description'] = 'This is a local group'
    error = expect_and_capture_ansible_exception(my_obj.create_cifs_local_user, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error creating CIFS local users with name username: calling: protocols/cifs/local-users: got Expected error.' == error


def test_delete_cifs_local_user():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/local-users', SRR['local_user_sid']),
        ('DELETE', 'protocols/cifs/local-users/e3cb5c7f-cd20/S-1-5-21-256008430-3394229847-3930036330-1001', SRR['empty_good'])
    ])
    module_args = {'name': 'username',
                   'state': 'absent',
                   'user_password': 'password',
                   'description': 'This is a local group'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_cifs_local_user_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('DELETE', 'protocols/cifs/local-users/e3cb5c7f-cd20/S-1-5-21-256008430-3394229847-3930036330-1001', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    my_obj.sid = 'S-1-5-21-256008430-3394229847-3930036330-1001'
    my_obj.parameters['name'] = 'username'
    my_obj.parameters['state'] = 'absent'
    my_obj.parameters['user_password'] = 'password'
    my_obj.parameters['description'] = 'This is a local group'
    error = expect_and_capture_ansible_exception(my_obj.delete_cifs_local_user, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error while deleting CIFS local user: calling: '\
           'protocols/cifs/local-users/e3cb5c7f-cd20/S-1-5-21-256008430-3394229847-3930036330-1001: got Expected error.' == error


def test_modify_cifs_local_user():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/local-users', SRR['local_user_sid']),
        ('PATCH', 'protocols/cifs/local-users/e3cb5c7f-cd20/S-1-5-21-256008430-3394229847-3930036330-1001', SRR['empty_good'])
    ])
    module_args = {'name': 'username',
                   'user_password': 'mypassword',
                   'description': 'This is a local group2',
                   'account_disabled': True,
                   'full_name': 'Full Name'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_cifs_local_user_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('PATCH', 'protocols/cifs/local-users/e3cb5c7f-cd20/S-1-5-21-256008430-3394229847-3930036330-1001', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    my_obj.sid = 'S-1-5-21-256008430-3394229847-3930036330-1001'
    my_obj.parameters['name'] = 'username'
    my_obj.parameters['user_password'] = 'mypassword'
    my_obj.parameters['description'] = 'This is a local group2'
    current = {'description': 'This is a local group'}
    error = expect_and_capture_ansible_exception(my_obj.modify_cifs_local_user, 'fail', current)['msg']
    print('Info: %s' % error)
    assert 'Error while modifying CIFS local user: calling: '\
           'protocols/cifs/local-users/e3cb5c7f-cd20/S-1-5-21-256008430-3394229847-3930036330-1001: got Expected error.' == error
