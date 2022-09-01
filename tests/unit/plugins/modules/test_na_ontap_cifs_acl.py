# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_cifs_acl """

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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_acl \
    import NetAppONTAPCifsAcl as my_module, main as my_main     # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


SHARE_NAME = 'share_name'

acl_info = {'num-records': 1,
            'attributes-list':
                {'cifs-share-access-control':
                    {'share': SHARE_NAME,
                     'user-or-group': 'user123',
                     'permission': 'full_control',
                     'user-group-type': 'windows'
                     }
                 },
            }

ZRR = zapi_responses({
    'acl_info': build_zapi_response(acl_info),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'permission': 'full_control',
    'share_name': 'share_name',
    'user_or_group': 'user_or_group',
    'vserver': 'vserver',
    'use_rest': 'never',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    error_msg = create_module(my_module, fail=True)['msg']
    for fragment in 'missing required arguments:', 'hostname', 'share_name', 'user_or_group', 'vserver':
        assert fragment in error_msg
    assert 'permission' not in error_msg

    args = dict(DEFAULT_ARGS)
    args.pop('permission')
    msg = 'state is present but all of the following are missing: permission'
    assert create_module(my_module, args, fail=True)['msg'] == msg


def test_create():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['empty']),
        ('cifs-share-access-control-create', ZRR['success']),
    ])
    module_args = {
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_with_type():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['empty']),
        ('cifs-share-access-control-create', ZRR['success']),
    ])
    module_args = {
        'type': 'unix_group'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['acl_info']),
        ('cifs-share-access-control-delete', ZRR['success']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_idempotent():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['empty']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['acl_info']),
        ('cifs-share-access-control-modify', ZRR['success']),
    ])
    module_args = {
        'permission': 'no_access',
        'type': 'windows'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_modify_idempotent():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['acl_info']),
    ])
    module_args = {
        'permission': 'full_control',
        'type': 'windows'
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_negative_modify_with_type():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['acl_info']),
    ])
    module_args = {
        'type': 'unix_group'
    }
    msg = 'Error: changing the type is not supported by ONTAP - current: windows, desired: unix_group'
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_negative_modify_with_extra_stuff():
    register_responses([
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    current = {'share_name': 'extra'}
    msg = "Error: only permission can be changed - modify: {'share_name': 'share_name'}"
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_modify, 'fail', current)['msg']

    current = {'share_name': 'extra', 'permission': 'permission'}
    # don't check dict contents as order may differ
    msg = "Error: only permission can be changed - modify:"
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_modify, 'fail', current)['msg']


def test_if_all_methods_catch_exception():
    register_responses([
        ('cifs-share-access-control-get-iter', ZRR['error']),
        ('cifs-share-access-control-create', ZRR['error']),
        ('cifs-share-access-control-modify', ZRR['error']),
        ('cifs-share-access-control-delete', ZRR['error']),
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)

    msg = 'Error getting cifs-share-access-control share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_cifs_acl, 'fail')['msg']

    msg = 'Error creating cifs-share-access-control share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg in expect_and_capture_ansible_exception(my_module_object.create_cifs_acl, 'fail')['msg']

    msg = 'Error modifying cifs-share-access-control permission share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg in expect_and_capture_ansible_exception(my_module_object.modify_cifs_acl_permission, 'fail')['msg']

    msg = 'Error deleting cifs-share-access-control share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg in expect_and_capture_ansible_exception(my_module_object.delete_cifs_acl, 'fail')['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_missing_netapp_lib(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    msg = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert msg in create_module(my_module, DEFAULT_ARGS, fail=True)['msg']


def test_main():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['empty']),
        ('cifs-share-access-control-create', ZRR['success']),
    ])
    set_module_args(DEFAULT_ARGS)
    assert expect_and_capture_ansible_exception(my_main, 'exit')['changed']


SRR = rest_responses({
    'acl_record': (200, {"records": [
        {
            "svm": {
                "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                "name": "ansibleSVM"
            },
            "share": "share_name",
            "user_or_group": "Everyone",
            "permission": "full_control",
            "type": "windows"
        }
    ], "num_records": 1}, None),
    'cifs_record': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansibleSVM"
                    },
                    "name": 'share_name',
                    "path": '/',
                    "comment": 'CIFS share comment',
                    "unix_symlink": 'widelink',
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    }
                }
            ],
            "num_records": 1
        }, None
    )
})

ARGS_REST = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'permission': 'full_control',
    'share_name': 'share_name',
    'user_or_group': 'Everyone',
    'vserver': 'vserver',
    'type': 'windows',
    'use_rest': 'always',
}


def test_error_get_acl_rest():
    ''' Test get error with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('GET', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on fetching cifs shares acl:' in error


def test_error_get_share_rest():
    ''' Test get share not exists with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on fetching cifs shares:' in error


def test_error_get_no_share_rest():
    ''' Test get share not exists with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['empty_records']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error: the cifs share does not exist:' in error


def test_create_rest():
    ''' Test create with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('GET', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['empty_records']),
        ('POST', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['empty_good']),
    ])
    assert create_and_apply(my_module, ARGS_REST)


def test_delete_rest():
    ''' Test delete with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('GET', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['acl_record']),
        ('DELETE', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls/Everyone/windows', SRR['empty_good']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_create_error_rest():
    ''' Test create error with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('GET', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['empty_records']),
        ('POST', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on creating cifs share acl:' in error


def test_error_delete_rest():
    ''' Test delete error with rest API '''
    module_args = {
        'state': 'absent'
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('GET', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['acl_record']),
        ('DELETE', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls/Everyone/windows', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on deleting cifs share acl:' in error


def test_modify_rest():
    ''' Test modify with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('GET', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['acl_record']),
        ('PATCH', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls/Everyone/windows', SRR['empty_good']),
    ])
    module_args = {
        'permission': 'no_access'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_error_modify_rest():
    ''' Test modify error with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('GET', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['acl_record']),
        ('PATCH', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls/Everyone/windows', SRR['generic_error'])
    ])
    module_args = {'permission': 'no_access'}
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    msg = 'Error modifying cifs share ACL permission: '\
          'calling: protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls/Everyone/windows: got Expected error.'
    assert msg == error


def test_error_get_modify_rest():
    ''' Test modify error with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('GET', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['acl_record']),
    ])
    module_args = {
        'type': 'unix_group'
    }
    msg = 'Error: changing the type is not supported by ONTAP - current: windows, desired: unix_group'
    assert create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg'] == msg


def test_negative_modify_with_extra_stuff_rest():
    ''' Test modify error with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    my_module_object = create_module(my_module, ARGS_REST)
    current = {'share_name': 'extra'}
    msg = "Error: only permission can be changed - modify: {'share_name': 'share_name'}"
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_modify, 'fail', current)['msg']

    current = {'share_name': 'extra', 'permission': 'permission'}
    # don't check dict contents as order may differ
    msg = "Error: only permission can be changed - modify:"
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_modify, 'fail', current)['msg']


def test_delete_idempotent_rest():
    ''' Test delete idempotency with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('GET', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['empty_records']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert not create_and_apply(my_module, ARGS_REST, module_args)['changed']


def test_create_modify_idempotent_rest():
    ''' Test create and modify idempotency with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('GET', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/share_name/acls', SRR['acl_record']),
    ])
    module_args = {
        'permission': 'full_control',
        'type': 'windows'
    }
    assert not create_and_apply(my_module, ARGS_REST, module_args)['changed']
