# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_unix_user \
    import NetAppOntapUnixUser as user_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'user_record': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "vserver"
                    },
                    "name": "user",
                    "primary_gid": 2,
                    "id": 1,
                    "full_name": "test_user",
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    }
                }
            ],
            "num_records": 1
        }, None
    ),
    "no_record": (
        200,
        {"num_records": 0},
        None)
})

unix_user_info = {
    'num-records': 1,
    'attributes-list': {
        'unix-user-info': {
            'name': 'user',
            'user-id': '1',
            'group-id': 2,
            'full-name': 'test_user'}
    }
}

ZRR = zapi_responses({
    'unix_user_info': build_zapi_response(unix_user_info)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'vserver',
    'name': 'user',
    'group_id': 2,
    'id': '1',
    'full_name': 'test_user',
    'use_rest': 'never',
}


DEFAULT_NO_USER = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'vserver',
    'name': 'no_user',
    'group_id': '2',
    'id': '1',
    'full_name': 'test_user',
    'use_rest': 'never',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        user_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_get_nonexistent_user():
    ''' Test if get_unix_user returns None for non-existent user '''
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['empty'])
    ])
    user_obj = create_module(user_module, DEFAULT_NO_USER)
    result = user_obj.get_unix_user()
    assert result is None


def test_get_existent_user():
    ''' Test if get_unix_user returns existent user '''
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['unix_user_info'])
    ])
    user_obj = create_module(user_module, DEFAULT_ARGS)
    result = user_obj.get_unix_user()
    assert result


def test_get_error_existent_user():
    ''' Test if get_unix_user returns existent user '''
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['error'])
    ])
    user_module_object = create_module(user_module, DEFAULT_ARGS)
    msg = "Error getting UNIX user"
    assert msg in expect_and_capture_ansible_exception(user_module_object.get_unix_user, 'fail')['msg']


def test_create_unix_user_zapi():
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['empty']),
        ('name-mapping-unix-user-create', ZRR['success']),
    ])
    module_args = {
        'name': 'user',
        'group_id': '2',
        'id': '1',
        'full_name': 'test_user',
    }
    assert create_and_apply(user_module, DEFAULT_ARGS, module_args)['changed']


def test_error_create_unix_user_zapi():
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['empty']),
        ('name-mapping-unix-user-create', ZRR['error']),
    ])
    module_args = {
        'name': 'user4',
        'group_id': '4',
        'id': '4',
        'full_name': 'test_user4',
    }
    error = create_and_apply(user_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error creating UNIX user"
    assert msg in error


def test_delete_unix_user_zapi():
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['unix_user_info']),
        ('name-mapping-unix-user-destroy', ZRR['success']),
    ])
    module_args = {
        'name': 'user',
        'group_id': '2',
        'id': '1',
        'full_name': 'test_user',
        'state': 'absent'
    }
    assert create_and_apply(user_module, DEFAULT_ARGS, module_args)['changed']


def test_error_remove_unix_user_zapi():
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['unix_user_info']),
        ('name-mapping-unix-user-destroy', ZRR['error']),
    ])
    module_args = {
        'name': 'user',
        'group_id': '2',
        'id': '1',
        'full_name': 'test_user',
        'state': 'absent'
    }
    error = create_and_apply(user_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error removing UNIX user"
    assert msg in error


def test_modify_unix_user_id_zapi():
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['unix_user_info']),
        ('name-mapping-unix-user-modify', ZRR['success']),
    ])
    module_args = {
        'group_id': '3',
        'id': '2'
    }
    assert create_and_apply(user_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_unix_user_full_name_zapi():
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['unix_user_info']),
        ('name-mapping-unix-user-modify', ZRR['success']),
    ])
    module_args = {
        'full_name': 'test_user1'
    }
    assert create_and_apply(user_module, DEFAULT_ARGS, module_args)['changed']


def test_error_modify_unix_user_full_name_zapi():
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['unix_user_info']),
        ('name-mapping-unix-user-modify', ZRR['error']),
    ])
    module_args = {
        'full_name': 'test_user1'
    }
    error = create_and_apply(user_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error modifying UNIX user"
    assert msg in error


def test_create_idempotent():
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['unix_user_info'])
    ])
    module_args = {
        'state': 'present',
        'name': 'user',
        'group_id': 2,
        'id': '1',
        'full_name': 'test_user',
    }
    assert not create_and_apply(user_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_idempotent():
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['empty'])
    ])
    module_args = {
        'state': 'absent'
    }
    assert not create_and_apply(user_module, DEFAULT_ARGS, module_args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('name-mapping-unix-user-get-iter', ZRR['error']),
        ('name-mapping-unix-user-create', ZRR['error']),
        ('name-mapping-unix-user-destroy', ZRR['error']),
        ('name-mapping-unix-user-modify', ZRR['error'])
    ])
    module_args = {'id': 5}
    my_obj = create_module(user_module, DEFAULT_ARGS, module_args)

    error = expect_and_capture_ansible_exception(my_obj.get_unix_user, 'fail')['msg']
    assert 'Error getting UNIX user user: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.create_unix_user, 'fail')['msg']
    assert 'Error creating UNIX user user: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.delete_unix_user, 'fail')['msg']
    assert 'Error removing UNIX user user: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.modify_unix_user, 'fail', 'name-mapping-unix-user-modify')['msg']
    assert 'Error modifying UNIX user user: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error


ARGS_REST = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
    'vserver': 'vserver',
    'name': 'user',
    'primary_gid': 2,
    'id': 1,
    'full_name': 'test_user'
}

REST_NO_USER = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
    'vserver': 'vserver',
    'name': 'user5',
    'primary_gid': 2,
    'id': 1,
    'full_name': 'test_user'
}


def test_get_nonexistent_user_rest_rest():
    ''' Test if get_unix_user returns None for non-existent user '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['empty_records']),
    ])
    user_obj = create_module(user_module, REST_NO_USER)
    result = user_obj.get_unix_user_rest()
    assert result is None


def test_get_existent_user_rest():
    ''' Test if get_unix_user returns existent user '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['user_record']),
    ])
    user_obj = create_module(user_module, ARGS_REST)
    result = user_obj.get_unix_user_rest()
    assert result


def test_get_error_existent_user_rest():
    ''' Test if get_unix_user returns existent user '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['generic_error']),
    ])
    error = create_and_apply(user_module, ARGS_REST, fail=True)['msg']
    msg = "Error on getting unix-user info:"
    assert msg in error


def test_create_unix_user_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['empty_records']),
        ('POST', 'name-services/unix-users', SRR['empty_good']),
    ])
    module_args = {
        'name': 'user',
        'primary_gid': 2,
        'id': 1,
        'full_name': 'test_user',
    }
    assert create_and_apply(user_module, ARGS_REST, module_args)['changed']


def test_error_create_unix_user_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['empty_records']),
        ('POST', 'name-services/unix-users', SRR['generic_error']),
    ])
    module_args = {
        'name': 'user4',
        'primary_gid': 4,
        'id': 4,
        'full_name': 'test_user4',
    }
    error = create_and_apply(user_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on creating unix-user:"
    assert msg in error


def test_delete_unix_user_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['user_record']),
        ('DELETE', 'name-services/unix-users/671aa46e-11ad-11ec-a267-005056b30cfa/user', SRR['empty_good']),
    ])
    module_args = {
        'name': 'user',
        'group_id': '2',
        'id': '1',
        'full_name': 'test_user',
        'state': 'absent'
    }
    assert create_and_apply(user_module, ARGS_REST, module_args)['changed']


def test_error_remove_unix_user_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['user_record']),
        ('DELETE', 'name-services/unix-users/671aa46e-11ad-11ec-a267-005056b30cfa/user', SRR['generic_error'])
    ])
    module_args = {
        'name': 'user',
        'id': '1',
        'state': 'absent'
    }
    error = create_and_apply(user_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on deleting unix-user"
    assert msg in error


def test_modify_unix_user_id_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['user_record']),
        ('PATCH', 'name-services/unix-users/671aa46e-11ad-11ec-a267-005056b30cfa/user', SRR['empty_good'])
    ])
    module_args = {
        'name': 'user',
        'group_id': '3',
        'id': '2'
    }
    assert create_and_apply(user_module, ARGS_REST, module_args)['changed']


def test_modify_unix_user_full_name_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['user_record']),
        ('PATCH', 'name-services/unix-users/671aa46e-11ad-11ec-a267-005056b30cfa/user', SRR['empty_good'])
    ])
    module_args = {
        'name': 'user',
        'full_name': 'test_user1'
    }
    assert create_and_apply(user_module, ARGS_REST, module_args)['changed']


def test_error_modify_unix_user_full_name_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['user_record']),
        ('PATCH', 'name-services/unix-users/671aa46e-11ad-11ec-a267-005056b30cfa/user', SRR['generic_error'])
    ])
    module_args = {
        'name': 'user',
        'full_name': 'test_user1'
    }
    error = create_and_apply(user_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on modifying unix-user:"
    assert msg in error


def test_create_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['user_record']),
    ])
    module_args = {
        'state': 'present',
        'name': 'user',
        'group_id': 2,
        'id': '1',
        'full_name': 'test_user',
    }
    assert not create_and_apply(user_module, ARGS_REST, module_args)['changed']


def test_delete_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/unix-users', SRR['empty_records']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert not create_and_apply(user_module, ARGS_REST, module_args)['changed']
