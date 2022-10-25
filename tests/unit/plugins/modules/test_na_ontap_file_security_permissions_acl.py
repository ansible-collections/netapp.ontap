# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    patch_ansible, assert_warning_was_raised, call_main, print_warnings, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    get_mock_record, patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_file_security_permissions_acl\
    import NetAppOntapFileSecurityPermissionsACL as my_module, main as my_main  # module under test

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
    'fd_acl_multiple_user_adv_rights': (200, {
        'acls': [
            build_acl('NETAPPAD\\mohan9'),
            build_acl('SERVER_CIFS_TE\\mohan11', advanced_rights={"append_data": True}),
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
            build_acl('SERVER_CIFS_TE\\mohan11', access='access_deny')
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
    'access_control': 'file_directory',
    "access": "access_allow",
    "acl_user": "SERVER_CIFS_TE\\mohan11",
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
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['non_acl']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user'])
    ])
    module_args = {
        "advanced_rights": {"append_data": True},
        "apply_to": {"this_folder": True, "files": False, "sub_folders": False},
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_modify_file_directory_acl():
    ''' modify file_directory acl and idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user']),
        ('PATCH', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/SERVER_CIFS_TE%5Cmohan11', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user_adv_rights']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user_adv_rights']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user_adv_rights']),
        ('PATCH', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/SERVER_CIFS_TE%5Cmohan11', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user_adv_rights']),
    ])
    module_args = {
        'advanced_rights': {'append_data': True, 'delete': False},
        "apply_to": {"this_folder": True, "files": False, "sub_folders": False},
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        "apply_to": {"this_folder": True, "files": False, "sub_folders": False},
        'rights': 'full_control',
    }
    error = "Error - modify: {'rights': 'full_control'} still required after {'rights': 'full_control'}"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_delete_file_directory_acl():
    ''' add file_directory acl and idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_multiple_user']),
        ('DELETE', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/SERVER_CIFS_TE%5Cmohan11', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['non_acl']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['fd_acl_only_inherited_acl']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['error_655865'])
    ])
    module_args = {
        "advanced_rights": {"append_data": True},
        "apply_to": {"this_folder": True, "files": False, "sub_folders": False},
        "state": "absent"
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_negative_acl_rights_and_advrights():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    args = {
        'access_control': 'file_directory',
        "access": "access_deny",
        "acl_user": "NETAPPAD\\mohan9",
        "advanced_rights": {"append_data": False},
        "rights": 'modify',
        "apply_to": {"this_folder": True, "files": False, "sub_folders": False},
        'validate_changes': 'error'

    }
    error = "Error: suboptions 'rights' and 'advanced_rights' are mutually exclusive."
    assert error in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']

    del args['rights']
    args['apply_to'] = {"this_folder": False, "files": False, "sub_folders": False}
    error = "Error: at least one suboption must be true for apply_to.  Got: "
    assert error in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']


def test_if_all_methods_catch_exception():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['generic_error']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl', SRR['generic_error']),
        ('PATCH', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/SERVER_CIFS_TE%5Cmohan11', SRR['generic_error']),
        ('DELETE', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl/SERVER_CIFS_TE%5Cmohan11', SRR['generic_error'])
    ])
    module_args = {
        "advanced_rights": {"append_data": True},
        "apply_to": {"this_folder": True, "files": False, "sub_folders": False}
    }

    acl_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    acl_obj.svm_uuid = "55bcb009"
    assert 'Error fetching file security' in expect_and_capture_ansible_exception(acl_obj.get_file_security_permissions_acl, 'fail')['msg']
    assert 'Error creating file security' in expect_and_capture_ansible_exception(acl_obj.create_file_security_permissions_acl, 'fail')['msg']
    assert 'Error modifying file security' in expect_and_capture_ansible_exception(acl_obj.modify_file_security_permissions_acl, 'fail')['msg']
    assert 'Error deleting file security permissions' in expect_and_capture_ansible_exception(acl_obj.delete_file_security_permissions_acl, 'fail')['msg']
    assert 'Internal error - unexpected action bad_action' in expect_and_capture_ansible_exception(acl_obj.build_body, 'fail', 'bad_action')['msg']
    acl = build_acl('user')
    acls = [acl, acl]
    assert 'Error matching ACLs, found more than one match.  Found' in expect_and_capture_ansible_exception(acl_obj.match_acl_with_acls, 'fail',
                                                                                                            acl, acls)['msg']


def test_create_file_directory_slag():
    ''' create slag acl and idempotent '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['non_acl']),
        ('POST', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt/acl', SRR['success']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['slag_acl_same_user']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_id']),
        ('GET', 'protocols/file-security/permissions/55bcb009/%2Fvol200%2FaNewFile.txt', SRR['slag_acl_same_user'])
    ])
    module_args = {
        'access_control': 'slag',
        'access': 'access_deny',
        'advanced_rights': {'append_data': True},
        'apply_to': {'files': True},
        'acl_user': 'SERVER_CIFS_TE\\mohan11'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


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
        "advanced_rights": {"append_data": True},
        'apply_to': {'files': True},
        'validate_changes': 'ignore',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    assert my_obj.validate_changes('create', {}) is None
    args = {
        "advanced_rights": {"append_data": True},
        'apply_to': {'files': True},
        'validate_changes': 'error',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    error = 'Error - create still required after create'
    assert error in expect_and_capture_ansible_exception(my_obj.validate_changes, 'fail', 'create', {})['msg']
    args = {
        'access': 'access_deny',
        'advanced_rights': {
            'append_data': False,
        },
        'apply_to': {'this_folder': True},
        'validate_changes': 'warn',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, args)
    warning = "Error - modify: {'advanced_rights': {'append_data': False}} still required after {'a': 'b'}"
    assert my_obj.validate_changes('create', {'a': 'b'}) is None
    print_warnings()
    assert_warning_was_raised(warning, partial_match=True)
