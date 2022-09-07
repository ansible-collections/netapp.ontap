# (c) 2019-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_unix_group \
    import NetAppOntapUnixGroup as group_module  # module under test

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
                    "name": "user_group",
                    "id": 1,
                    "users": [{"name": "user1"}, {"name": "user2"}],
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

unix_group_info = {
    'num-records': 1,
    'attributes-list': {
        'unix-group-info': {
            'group-name': 'user_group',
            'group-id': '1',
            'users': [{'unix-user-name': {'user-name': 'user1'}}]
        }
    }
}


ZRR = zapi_responses({
    'unix_group_info': build_zapi_response(unix_group_info)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'vserver',
    'name': 'user_group',
    'id': '1',
    'use_rest': 'never',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        group_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_get_nonexistent_user_group():
    ''' Test if get_unix_group returns None for non-existent group '''
    register_responses([
        ('name-mapping-unix-group-get-iter', ZRR['empty'])
    ])
    user_obj = create_module(group_module, DEFAULT_ARGS)
    result = user_obj.get_unix_group()
    assert result is None


def test_get_user_group():
    ''' Test if get_unix_group returns unix group '''
    register_responses([
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info'])
    ])
    user_obj = create_module(group_module, DEFAULT_ARGS)
    result = user_obj.get_unix_group()
    assert result


def test_get_error_existent_user_group():
    ''' Test if get_unix_user returns existent user group '''
    register_responses([
        ('name-mapping-unix-group-get-iter', ZRR['error'])
    ])
    group_module_object = create_module(group_module, DEFAULT_ARGS)
    msg = "Error getting UNIX group"
    assert msg in expect_and_capture_ansible_exception(group_module_object.get_unix_group, 'fail')['msg']


def test_create_unix_group_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['empty']),
        ('name-mapping-unix-group-create', ZRR['success']),
    ])
    module_args = {
        'name': 'user_group',
        'id': '1'
    }
    assert create_and_apply(group_module, DEFAULT_ARGS, module_args)['changed']


def test_create_unix_group_with_user_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['empty']),
        ('name-mapping-unix-group-create', ZRR['success']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-add-user', ZRR['success'])
    ])
    module_args = {
        'name': 'user_group',
        'id': '1',
        'users': ['user1', 'user2']
    }
    assert create_and_apply(group_module, DEFAULT_ARGS, module_args)['changed']


def test_error_create_unix_user_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['empty']),
        ('name-mapping-unix-group-create', ZRR['error']),
    ])
    module_args = {
        'name': 'user_group',
        'id': '1',
        'users': ['user1', 'user2']
    }
    error = create_and_apply(group_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error creating UNIX group"
    assert msg in error


def test_delete_unix_group_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-destroy', ZRR['success']),
    ])
    module_args = {
        'name': 'user_group',
        'state': 'absent'
    }
    assert create_and_apply(group_module, DEFAULT_ARGS, module_args)['changed']


def test_error_remove_unix_group_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-destroy', ZRR['error']),
    ])
    module_args = {
        'name': 'user_group',
        'state': 'absent'
    }
    error = create_and_apply(group_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error removing UNIX group"
    assert msg in error


def test_create_idempotent():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info'])
    ])
    module_args = {
        'state': 'present',
        'name': 'user_group',
        'id': '1',
    }
    assert not create_and_apply(group_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_idempotent():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['empty'])
    ])
    module_args = {
        'state': 'absent',
        'name': 'user_group',
    }
    assert not create_and_apply(group_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_unix_group_id_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-modify', ZRR['success']),
    ])
    module_args = {
        'name': 'user_group',
        'id': '2'
    }
    assert create_and_apply(group_module, DEFAULT_ARGS, module_args)['changed']


def test_error_modify_unix_group_id_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-modify', ZRR['error']),
    ])
    module_args = {
        'name': 'user_group',
        'id': '2'
    }
    error = create_and_apply(group_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error modifying UNIX group"
    assert msg in error


def test_add_unix_group_user_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-add-user', ZRR['success'])
    ])
    module_args = {
        'name': 'user_group',
        'users': ['user1', 'user2']
    }
    assert create_and_apply(group_module, DEFAULT_ARGS, module_args)['changed']


def test_error_add_unix_group_user_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-add-user', ZRR['error'])
    ])
    module_args = {
        'name': 'user_group',
        'users': ['user1', 'user2']
    }
    error = create_and_apply(group_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error adding user"
    assert msg in error


def test_delete_unix_group_user_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-delete-user', ZRR['success'])
    ])
    module_args = {
        'name': 'user_group',
        'users': ''
    }
    assert create_and_apply(group_module, DEFAULT_ARGS, module_args)['changed']


def test_error_delete_unix_group_user_zapi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-get-iter', ZRR['unix_group_info']),
        ('name-mapping-unix-group-delete-user', ZRR['error'])
    ])
    module_args = {
        'name': 'user_group',
        'users': ''
    }
    error = create_and_apply(group_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error deleting user"
    assert msg in error


def test_if_all_methods_catch_exception():
    register_responses([
        ('name-mapping-unix-group-get-iter', ZRR['error']),
        ('name-mapping-unix-group-create', ZRR['error']),
        ('name-mapping-unix-group-destroy', ZRR['error']),
        ('name-mapping-unix-group-modify', ZRR['error']),
    ])
    module_args = {'use_rest': 'never', 'name': 'user_group'}
    my_obj = create_module(group_module, DEFAULT_ARGS, module_args)

    error = expect_and_capture_ansible_exception(my_obj.get_unix_group, 'fail')['msg']
    assert 'Error getting UNIX group user_group: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.create_unix_group, 'fail')['msg']
    assert 'Error creating UNIX group user_group: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.delete_unix_group, 'fail')['msg']
    assert 'Error removing UNIX group user_group: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.modify_unix_group, 'fail', 'name-mapping-unix-group-modify')['msg']
    assert 'Error modifying UNIX group user_group: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error


ARGS_REST = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
    'vserver': 'vserver',
    'name': 'user_group',
    'id': '1'
}


def test_get_nonexistent_user_group_rest():
    ''' Test if get_unix_user returns None for non-existent user '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['empty_records']),
    ])
    user_obj = create_module(group_module, ARGS_REST)
    result = user_obj.get_unix_group_rest()
    assert result is None


def test_get_existent_user_group_rest():
    ''' Test if get_unix_user returns existent user '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
    ])
    user_obj = create_module(group_module, ARGS_REST)
    result = user_obj.get_unix_group_rest()
    assert result


def test_get_error_existent_user_group_rest():
    ''' Test if get_unix_user returns existent user '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['generic_error']),
    ])
    error = create_and_apply(group_module, ARGS_REST, fail=True)['msg']
    msg = "Error getting UNIX group:"
    assert msg in error


def test_ontap_version_rest():
    ''' Test ONTAP version '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
    ])
    module_args = {'use_rest': 'always'}
    error = create_module(group_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error: REST requires ONTAP 9.9.1 or later for UNIX group APIs."
    assert msg in error


def test_create_unix_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['empty_records']),
        ('POST', 'name-services/unix-groups', SRR['empty_good']),
    ])
    module_args = {
        'name': 'user_group',
        'id': 1,
    }
    assert create_and_apply(group_module, ARGS_REST, module_args)['changed']


def test_create_unix_group_with_user_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['empty_records']),
        ('POST', 'name-services/unix-groups', SRR['empty_good']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
        ('POST', 'name-services/unix-groups/671aa46e-11ad-11ec-a267-005056b30cfa/user_group/users', SRR['empty_records'])
    ])
    module_args = {
        'name': 'user_group',
        'id': 1,
        'users': ['user1', 'user2', 'user3']
    }
    assert create_and_apply(group_module, ARGS_REST, module_args)['changed']


def test_error_create_unix_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['empty_records']),
        ('POST', 'name-services/unix-groups', SRR['generic_error']),
    ])
    module_args = {
        'name': 'user_group',
        'id': 1,
    }
    error = create_and_apply(group_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error creating UNIX group:"
    assert msg in error


def test_delete_unix_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
        ('DELETE', 'name-services/unix-groups/671aa46e-11ad-11ec-a267-005056b30cfa/user_group', SRR['empty_good']),
    ])
    module_args = {
        'name': 'user_group',
        'state': 'absent'
    }
    assert create_and_apply(group_module, ARGS_REST, module_args)['changed']


def test_error_remove_unix_user_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
        ('DELETE', 'name-services/unix-groups/671aa46e-11ad-11ec-a267-005056b30cfa/user_group', SRR['generic_error']),
    ])
    module_args = {
        'name': 'user_group',
        'state': 'absent'
    }
    error = create_and_apply(group_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error deleting UNIX group:"
    assert msg in error


def test_modify_unix_group_id_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
        ('PATCH', 'name-services/unix-groups/671aa46e-11ad-11ec-a267-005056b30cfa/user_group', SRR['empty_good'])
    ])
    module_args = {
        'name': 'user_group',
        'id': '2'
    }
    assert create_and_apply(group_module, ARGS_REST, module_args)['changed']


def test_error_modify_unix_group_id_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
        ('PATCH', 'name-services/unix-groups/671aa46e-11ad-11ec-a267-005056b30cfa/user_group', SRR['generic_error'])
    ])
    module_args = {
        'name': 'user_group',
        'id': '2'
    }
    error = create_and_apply(group_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on modifying UNIX group:"
    assert msg in error


def test_create_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
    ])
    module_args = {
        'state': 'present',
        'name': 'user_group',
        'id': '1',
    }
    assert not create_and_apply(group_module, ARGS_REST, module_args)['changed']


def test_delete_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['empty_records']),
    ])
    module_args = {
        'state': 'absent',
        'name': 'user_group'
    }
    assert not create_and_apply(group_module, ARGS_REST, module_args)['changed']


def test_add_unix_group_user_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
        ('POST', 'name-services/unix-groups/671aa46e-11ad-11ec-a267-005056b30cfa/user_group/users', SRR['empty_records'])
    ])
    module_args = {
        'name': 'user_group',
        'users': ['user1', 'user2', 'user3']
    }
    assert create_and_apply(group_module, ARGS_REST, module_args)['changed']


def test_error_add_unix_group_user_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
        ('POST', 'name-services/unix-groups/671aa46e-11ad-11ec-a267-005056b30cfa/user_group/users', SRR['generic_error'])
    ])
    module_args = {
        'name': 'user_group',
        'users': ['user1', 'user2', 'user3']
    }
    error = create_and_apply(group_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error Adding user to UNIX group:"
    assert msg in error


def test_delete_unix_group_user_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
        ('DELETE', 'name-services/unix-groups/671aa46e-11ad-11ec-a267-005056b30cfa/user_group/users/user2', SRR['empty_records'])
    ])
    module_args = {
        'users': ["user1"]
    }
    assert create_and_apply(group_module, ARGS_REST, module_args)['changed']


def test_error_delete_unix_group_user_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/unix-groups', SRR['user_record']),
        ('DELETE', 'name-services/unix-groups/671aa46e-11ad-11ec-a267-005056b30cfa/user_group/users/user2', SRR['generic_error'])
    ])
    module_args = {
        'users': ["user1"]
    }
    error = create_and_apply(group_module, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error removing user from UNIX group:"
    assert msg in error
