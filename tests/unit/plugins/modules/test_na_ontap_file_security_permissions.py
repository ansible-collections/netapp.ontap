# (c) 2022-2024, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import assert_warning_was_raised, print_warnings, \
    patch_ansible, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_file_security_permissions \
    import NetAppOntapFileSecurityPermissions as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


def build_acl(user, access='access_allow', access_control='file_directory', apply_to=None, inherited=None, advanced_rights='all', rights=None):
    if apply_to is None:
        apply_to = {'this_folder': True}
    if advanced_rights == 'all':
        advanced_rights = {
            'append_data': True,
            'delete': True,
            'delete_child': True,
            'execute_file': True,
            'full_control': True,
            'read_attr': True,
            'read_data': True,
            'read_ea': True,
            'read_perm': True,
            'synchronize': True,
            'write_attr': True,
            'write_data': True,
            'write_ea': True,
            'write_owner': True,
            'write_perm': True
        }

    acl = {
        'access': access,
        'access_control': access_control,
        'advanced_rights': advanced_rights,
        'apply_to': apply_to,
        'user': user
    }
    if inherited is not None:
        acl['inherited'] = inherited
    if rights is not None:
        acl['rights'] = rights
    return acl


SRR = rest_responses({
    'non_acl': (200, {
        'path': '/vol200/aNewFile.txt',
        'svm': {'name': 'ansible_ipspace_datasvm', 'uuid': '55bcb009'}
    }, None),
    'fd_acl_only_inherited_acl': (200, {
        'acls': [
            build_acl('Everyone', inherited=True)
        ],
        'control_flags': '0x8014',
        'group': 'BUILTIN\\Administrators',
        'owner': 'BUILTIN\\Administrators',
        'path': '/vol200/aNewFile.txt',
        'svm': {'name': 'ansible_ipspace_datasvm', 'uuid': '55bcb009'}
    }, None),
    'fd_acl_multiple_user': (200, {
        'acls': [
            build_acl('NETAPPAD\\mohan9'),
            build_acl('SERVER_CIFS_TE\\mohan11'),
            build_acl('Everyone', inherited=True)
        ],
        'control_flags': '0x8014',
        'group': 'BUILTIN\\Administrators',
        'owner': 'BUILTIN\\Administrators',
        'path': '/vol200/aNewFile.txt',
        'svm': {'name': 'ansible_ipspace_datasvm', 'uuid': '55bcb009'}
    }, None),
    'fd_acl_single_user_deny': (200, {
        'acls': [
            build_acl('NETAPPAD\\mohan9', access='access_deny')
        ],
        'control_flags': '0x8014',
        'group': 'BUILTIN\\Administrators',
        'owner': 'BUILTIN\\Administrators',
        'path': '/vol200/aNewFile.txt',
        'svm': {'name': 'ansible_ipspace_datasvm', 'uuid': '55bcb009'}
    }, None),
    'fd_acl_single_user_acl': (200, {
        'acls': [
            build_acl('NETAPPAD\\mohan9', access='access_deny', apply_to={'files': True, 'this_folder': True, 'sub_folders': True})
        ],
        'control_flags': '0x8014',
        'group': 'BUILTIN\\Administrators',
        'owner': 'BUILTIN\\Administrators',
        'path': '/vol200/aNewFile.txt',
        'svm': {'name': 'ansible_ipspace_datasvm', 'uuid': '55bcb009'}
    }, None),
    'fd_acl_single_user_deny_empty_advrights': (200, {
        'acls': [
            build_acl('NETAPPAD\\mohan9', access='access_deny', advanced_rights={})
        ],
        'control_flags': '0x8014',
        'group': 'BUILTIN\\Administrators',
        'owner': 'BUILTIN\\Administrators',
        'path': '/vol200/aNewFile.txt',
        'svm': {'name': 'ansible_ipspace_datasvm', 'uuid': '55bcb009'}
    }, None),
    'fd_acl_single_user_deny_empty_advrights_mohan11': (200, {
        'acls': [
            build_acl('NETAPPAD\\mohan9', access='access_deny', advanced_rights={})
        ],
        'control_flags': '0x8014',
        'group': 'BUILTIN\\Administrators',
        'owner': 'SERVER_CIFS_TE\\mohan11',
        'path': '/vol200/aNewFile.txt',
        'svm': {'name': 'ansible_ipspace_datasvm', 'uuid': '55bcb009'}
    }, None),
    'fd_acl_single_user_rights': (200, {
        'acls': [
            build_acl('NETAPPAD\\mohan9', access='access_deny', advanced_rights={}, rights='full_control')
        ],
        'control_flags': '0x8014',
        'group': 'BUILTIN\\Administrators',
        'owner': 'BUILTIN\\Administrators',
        'path': '/vol200/aNewFile.txt',
        'svm': {'name': 'ansible_ipspace_datasvm', 'uuid': '55bcb009'}
    }, None),
    'slag_acl_same_user': (200, {
        'acls': [
            build_acl('SERVER_CIFS_TE\\mohan11', access_control='slag', apply_to={'files': True}, advanced_rights={"append_data": True}, access='access_deny'),
            build_acl('SERVER_CIFS_TE\\mohan11', access_control='slag', apply_to={'files': True}, advanced_rights={"append_data": True})
        ],
        'control_flags': '0x8014',
        'group': 'BUILTIN\\Administrators',
        'owner': 'BUILTIN\\Administrators',
        'path': '/vol200/aNewFile.txt',
        'svm': {'name': 'ansible_ipspace_datasvm', 'uuid': '55bcb009'}
    }, None),
    'svm_id': (200, {
        'uuid': '55bcb009'
    }, None),
    'error_655865': (400, None, {'code': 655865, 'message': 'Expected error'}),
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'vserver',
    'path': '/vol200/aNewFile.txt',
    'acls': [
        {
            "access": "access_allow",
            "user": "SERVER_CIFS_TE\\mohan11",
            "advanced_rights": {"append_data": True},
            "apply_to": {"this_folder": True, "files": False, "sub_folders": False}
        },
        {
            "access": "access_allow",
            "user": "NETAPPAD\\mohan9",
            "advanced_rights": {"append_data": True},
            "apply_to": {"this_folder": True, "files": False, "sub_folders": False}
        },

    ]
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "vserver", "path"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_create_file_directory_acl():
    ''' create file_directory acl and idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['zero_records']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['non_acl']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl', SRR['success']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['zero_records']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['non_acl']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['non_acl']),
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS)['changed']
    # Add ACLs to an SD only record
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']
    # create SD only
    args = dict(DEFAULT_ARGS)
    args.pop('acls')
    assert create_and_apply(my_module, args)['changed']
    assert not create_and_apply(my_module, args)['changed']


def test_add_file_directory_acl():
    ''' add file_directory acl and idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user']),
        ('DELETE', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/NETAPPAD%5Cmohan9', SRR['success']),
        ('DELETE', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/SERVER_CIFS_TE%5Cmohan11', SRR['success']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny'])
    ])
    args = {
        'acls': [{
            "access": "access_deny",
            "user": "NETAPPAD\\mohan9",
            "advanced_rights": {"append_data": True},
            "apply_to": {"this_folder": True, "files": False, "sub_folders": False},
        }]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_add_file_directory_acl_without_apply_to():
    ''' add file_directory acl without apply_to and idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['non_acl']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_acl']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_acl'])
    ])
    args = {
        'acls': [{
            "access": "access_deny",
            "user": "NETAPPAD\\mohan9",
            "advanced_rights": {"append_data": True}
        }]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_delete_file_directory_acl():
    ''' add file_directory acl and idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user']),
        ('DELETE', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/NETAPPAD%5Cmohan9', SRR['success']),
        ('DELETE', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/SERVER_CIFS_TE%5Cmohan11', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_only_inherited_acl']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_only_inherited_acl']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['error_655865']),
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['generic_error']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['generic_error']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl', SRR['generic_error']),
        ('PATCH', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['generic_error']),
        ('PATCH', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/user1', SRR['generic_error']),
        ('DELETE', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/user1', SRR['generic_error'])
    ])

    acl_obj = create_module(my_module, DEFAULT_ARGS)
    acl_obj.svm_uuid = "55bcb009"
    assert 'Error fetching file security' in expect_and_capture_ansible_exception(acl_obj.get_file_security_permissions, 'fail')['msg']
    assert 'Error creating file security' in expect_and_capture_ansible_exception(acl_obj.create_file_security_permissions, 'fail')['msg']
    assert 'Error adding file security' in expect_and_capture_ansible_exception(acl_obj.add_file_security_permissions_acl, 'fail', {})['msg']
    assert 'Error modifying file security' in expect_and_capture_ansible_exception(acl_obj.modify_file_security_permissions, 'fail', {})['msg']
    acl = {'user': 'user1'}
    assert 'Error modifying file security' in expect_and_capture_ansible_exception(acl_obj.modify_file_security_permissions_acl, 'fail', acl)['msg']
    assert 'Error deleting file security permissions' in expect_and_capture_ansible_exception(acl_obj.delete_file_security_permissions_acl, 'fail', acl)['msg']
    # no network calls
    assert 'Error: mismatch on path values: desired:' in expect_and_capture_ansible_exception(
        acl_obj.get_modify_actions, 'fail', {'path': 'dummy'})['msg']


def test_create_file_directory_slag():
    ''' create slag acl and idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['zero_records']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['slag_acl_same_user']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['slag_acl_same_user'])
    ])
    args = {
        'access_control': 'slag',
        'acls': [
            {
                'access': 'access_deny',
                'access_control': 'slag',
                'advanced_rights': {'append_data': True},
                'apply_to': {'files': True, "this_folder": False, "sub_folders": False},
                'user': 'SERVER_CIFS_TE\\mohan11'
            },
            {
                'access': 'access_allow',
                'access_control': 'slag',
                'advanced_rights': {'append_data': True},
                'apply_to': {'files': True, "this_folder": False, "sub_folders": False},
                'user': 'SERVER_CIFS_TE\\mohan11'
            }
        ]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_modify_file_directory_owner():
    ''' modify file owner '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny_empty_advrights']),
        ('PATCH', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny_empty_advrights_mohan11']),
    ])
    args = {
        'acls': [{
            "access": "access_deny",
            "user": "NETAPPAD\\mohan9",
            "advanced_rights": {"append_data": False},
            "apply_to": {"this_folder": True, "files": False, "sub_folders": False},
        }],
        'owner': 'SERVER_CIFS_TE\\mohan11'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    # idempotency already tested in create and add


def test_modify_file_directory_acl_advrights():
    ''' add file_directory acl and idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny']),
        ('PATCH', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/NETAPPAD%5Cmohan9', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny_empty_advrights']),
    ])
    args = {
        'acls': [{
            "access": "access_deny",
            "user": "NETAPPAD\\mohan9",
            "advanced_rights": {"append_data": False},
            "apply_to": {"this_folder": True, "files": False, "sub_folders": False},
        }]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    # idempotency already tested in create and add


def test_modify_file_directory_acl_rights():
    ''' add file_directory acl using rights
        it always fails the validation check, as REST does not return rights
        it is not idempotent for the same reason
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny']),
        ('PATCH', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/NETAPPAD%5Cmohan9', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny_empty_advrights']),
        # 2nd run
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny']),
        ('PATCH', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/NETAPPAD%5Cmohan9', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny_empty_advrights']),
    ])
    args = {
        'acls': [{
            "access": "access_deny",
            "user": "NETAPPAD\\mohan9",
            "rights": 'modify',
            "apply_to": {"this_folder": True, "files": False, "sub_folders": False},
        }],
        'validate_changes': 'error'
    }
    error = "Error - patch-acls still required for [{"
    assert error in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']
    args['validate_changes'] = 'warn'
    assert call_main(my_main, DEFAULT_ARGS, args)['changed']
    print_warnings()
    assert_warning_was_raised('Error - patch-acls still required for [', partial_match=True)


def test_negative_acl_rights_and_advrights():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    args = {
        'access_control': 'file_directory',
        'acls': [{
            "access": "access_deny",
            "user": "NETAPPAD\\mohan9",
            "advanced_rights": {"append_data": False},
            "rights": 'modify',
            "apply_to": {"this_folder": True, "files": False, "sub_folders": False},
        }],
        'validate_changes': 'error'

    }
    error = "Error: suboptions 'rights' and 'advanced_rights' are mutually exclusive."
    assert error in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']
    del args['acls'][0]['rights']
    args['acls'][0]['access_control'] = "slag"
    error = "Error: mismatch between top level value and ACL value for"
    assert error in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']
    args['acls'][0]['apply_to'] = {"this_folder": False, "files": False, "sub_folders": False}
    error = "Error: at least one suboption must be true for apply_to.  Got: "
    assert error in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']


def test_get_acl_actions_on_create():
    """ given a set of ACLs in self.parameters, split them in four groups, or fewer """
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])

    apply_to = {'this_folder': True, 'files': False, 'sub_folders': False}

    fd_prop_acls = [
        # All these ACLs fall into a single category, as file_directory and propagate are the defaults
        {"access": "access_deny", "user": "user01", "apply_to": apply_to},
        {"access": "access_deny", "user": "user02", "apply_to": apply_to, 'access_control': 'file_directory'},
        {"access": "access_deny", "user": "user03", "apply_to": apply_to, 'access_control': 'file_directory', 'propagation_mode': 'propagate'},
        {"access": "access_deny", "user": "user04", "apply_to": apply_to, 'propagation_mode': 'propagate'}
    ]

    fd_replace_acls = [
        {"access": "access_deny", "user": "user11", "apply_to": apply_to, 'access_control': 'file_directory', 'propagation_mode': 'replace'},
        {"access": "access_deny", "user": "user12", "apply_to": apply_to, 'propagation_mode': 'replace'}
    ]

    slag_prop_acls = [
        {"access": "access_deny", "user": "user21", "apply_to": apply_to, 'access_control': 'slag'},
        {"access": "access_deny", "user": "user22", "apply_to": apply_to, 'access_control': 'slag', 'propagation_mode': 'propagate'},
    ]

    slag_replace_acls = [
        {"access": "access_deny", "user": "user31", "apply_to": apply_to, 'access_control': 'slag', 'propagation_mode': 'replace'},
    ]

    args = {
        'acls': fd_prop_acls,
        'validate_changes': 'error'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    acls = my_obj.get_acl_actions_on_create()
    assert not any(acls[x] for x in acls)
    assert my_obj.parameters['acls'] == fd_prop_acls

    args = {
        'acls': fd_prop_acls + fd_replace_acls + slag_prop_acls + slag_replace_acls,
        'validate_changes': 'error'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    acls = my_obj.get_acl_actions_on_create()
    print('P_ACLS', acls)
    print('C_ACLS', my_obj.parameters['acls'])
    assert len(acls['post-acls']) == 5
    assert my_obj.parameters['acls'] == fd_prop_acls

    args = {
        'acls': slag_replace_acls,
        'validate_changes': 'error'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    acls = my_obj.get_acl_actions_on_create()
    assert not any(acls[x] for x in acls)
    assert my_obj.parameters['acls'] == slag_replace_acls


def test_get_acl_actions_on_create_special():
    """ given a set of ACLs in self.parameters, split them in four groups, or fewer """
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])

    apply_to = {'this_folder': True, 'files': False, 'sub_folders': False}

    fd_prop_acls = [
        # All these ACLs fall into a single category, as file_directory and propagate are the defaults
        {"access": "access_deny", "user": "user01", "apply_to": apply_to},
        {"access": "access_deny", "user": "user02", "apply_to": apply_to, 'access_control': 'file_directory'},
        {"access": "access_deny", "user": "user03", "apply_to": apply_to, 'access_control': 'file_directory', 'propagation_mode': 'propagate'},
        {"access": "access_deny", "user": "user04", "apply_to": apply_to, 'propagation_mode': 'propagate'}
    ]

    fd_replace_acls = [
        {"access": "access_deny", "user": "user11", "apply_to": apply_to, 'access_control': 'file_directory', 'propagation_mode': 'replace'},
        {"access": "access_deny", "user": "user12", "apply_to": apply_to, 'propagation_mode': 'replace'}
    ]

    slag_prop_acls = [
        {"access": "access_allowed_callback", "user": "user21", "apply_to": apply_to, 'access_control': 'slag'},
        {"access": "access_denied_callback", "user": "user22", "apply_to": apply_to, 'access_control': 'slag', 'propagation_mode': 'propagate'},
    ]

    slag_replace_acls = [
        {"access": "access_deny", "user": "user31", "apply_to": apply_to, 'access_control': 'slag', 'propagation_mode': 'replace'},
    ]

    fd_replace_acls_conflict = [
        {"access": "access_denied_callback", "user": "user11", "apply_to": apply_to, 'access_control': 'file_directory', 'propagation_mode': 'replace'},
        {"access": "access_allowed_callback", "user": "user12", "apply_to": apply_to, 'propagation_mode': 'replace'}
    ]

    args = {
        'acls': fd_prop_acls + fd_replace_acls + slag_prop_acls + slag_replace_acls,
        'validate_changes': 'error'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    acls = my_obj.get_acl_actions_on_create()
    print('P_ACLS', acls)
    print('C_ACLS', my_obj.parameters['acls'])
    assert len(acls['post-acls']) == 7
    assert my_obj.parameters['acls'] == slag_prop_acls

    args = {
        'acls': fd_prop_acls + fd_replace_acls_conflict + slag_prop_acls + slag_replace_acls,
        'validate_changes': 'error'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    error = 'with access access_allowed_callback conflicts with other ACLs using accesses'
    assert error in expect_and_capture_ansible_exception(my_obj.get_acl_actions_on_create, 'fail')['msg']


def test_negative_unsupported_version():
    ''' create slag acl and idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        # ('GET', 'svm/svms', SRR['svm_id']),
        # ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['non_acl']),
        # ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['success']),
        # ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['slag_acl_same_user']),
        # ('GET', 'cluster', SRR['is_rest_9_10_1']),
        # ('GET', 'svm/svms', SRR['svm_id']),
        # ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['slag_acl_same_user'])
    ])
    args = {
        'access_control': 'slag',
        'acls': [
            {
                'access': 'access_deny',
                'access_control': 'slag',
                'advanced_rights': {'append_data': True},
                'apply_to': {'files': True, "this_folder": False, "sub_folders": False},
                'user': 'SERVER_CIFS_TE\\mohan11'
            },
            {
                'access': 'access_allow',
                'access_control': 'slag',
                'advanced_rights': {'append_data': True},
                'apply_to': {'files': True, "this_folder": False, "sub_folders": False},
                'user': 'SERVER_CIFS_TE\\mohan11'
            }
        ]
    }
    error = 'Error: na_ontap_file_security_permissions only supports REST, and requires ONTAP 9.9.1 or later.  Found: 9.8.0.'
    assert error in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']
    error = 'Minimum version of ONTAP for access_control is (9, 10, 1)'
    msg = call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']
    assert error in msg
    error = 'Minimum version of ONTAP for acls.access_control is (9, 10, 1)'
    assert error in msg


def test_match_acl_with_acls():
    """ given a set of ACLs in self.parameters, split them in four groups, or fewer """
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])

    apply_to = {'this_folder': True, 'files': False, 'sub_folders': False}

    fd_prop_acls = [
        # All these ACLs fall into a single category, as file_directory and propagate are the defaults
        {"access": "access_deny", "user": "user01", "apply_to": apply_to},
        {"access": "access_deny", "user": "user02", "apply_to": apply_to, 'access_control': 'file_directory'},
        {"access": "access_deny", "user": "user03", "apply_to": apply_to, 'access_control': 'file_directory', 'propagation_mode': 'propagate'},
        {"access": "access_deny", "user": "user04", "apply_to": apply_to, 'propagation_mode': 'propagate'}
    ]

    fd_replace_acls = [
        {"access": "access_deny", "user": "user11", "apply_to": apply_to, 'access_control': 'file_directory', 'propagation_mode': 'replace'},
        {"access": "access_deny", "user": "user12", "apply_to": apply_to, 'propagation_mode': 'replace'}
    ]

    acl = fd_prop_acls[3]
    my_obj = create_module(my_module, DEFAULT_ARGS)
    assert acl == my_obj.match_acl_with_acls(acl, fd_prop_acls)
    assert my_obj.match_acl_with_acls(acl, fd_replace_acls) is None
    error = 'Error: found more than one desired ACLs with same user, access, access_control and apply_to'
    assert error in expect_and_capture_ansible_exception(my_obj.match_acl_with_acls, 'fail', acl, fd_prop_acls + fd_prop_acls)['msg']


def test_validate_changes():
    """ verify nothing needs to be changed """
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/file-security/permissions/None/%2Fvol200%2FaNewFile.txt', SRR['zero_records']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/file-security/permissions/None/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_single_user_deny']),
    ])
    args = {
        'validate_changes': 'ignore'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    assert my_obj.validate_changes('create', {}) is None
    args = {
        'validate_changes': 'error'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    error = 'Error - create still required after create'
    assert error in expect_and_capture_ansible_exception(my_obj.validate_changes, 'fail', 'create', {})['msg']
    args = {
        'validate_changes': 'warn',
        'owner': 'new_owner'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    warning = "Error - modify: {'owner': 'new_owner'} still required after {'a': 'b'}"
    assert my_obj.validate_changes('create', {'a': 'b'}) is None
    assert_warning_was_raised(warning, partial_match=True)
    assert_warning_was_raised('post-acls still required for', partial_match=True)
    assert_warning_was_raised('delete-acls still required for', partial_match=True)
