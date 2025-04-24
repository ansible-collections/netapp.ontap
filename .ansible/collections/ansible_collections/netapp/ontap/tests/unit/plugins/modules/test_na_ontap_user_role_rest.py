# (c) 2022-2024, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception, assert_warning_was_raised, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_user_role \
    import NetAppOntapUserRole as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'user_role_9_10': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [
            {
                "access": "readonly",
                "path": "/api/storage/volumes"
            }
        ],
        "name": "admin",
        "scope": "cluster"
    }, None),
    'user_role_9_11_command': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [
            {
                "path": "job schedule interval",
                'query': "-days <1 -hours >12"
            }, {
                'path': 'DEFAULT',
                'access': 'none',
                "_links": {
                    "self": {
                        "href": "/api/resourcelink"
                    }}
            }
        ],
        "name": "admin",
        "scope": "cluster"
    }, None),
    'user_role_9_10_two_paths': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [
            {
                "access": "readonly",
                "path": "/api/storage/volumes"
            },
            {
                "access": "readonly",
                "path": "/api/cluster/jobs",
            }
        ],
        "name": "admin",
        "scope": "cluster"
    }, None),
    'user_role_9_10_two_paths_modified': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [
            {"access": "readonly", "path": "/api/storage/volumes"},
            {"access": "readonly", "path": "/api/cluster/jobs"}
        ],
        "name": "admin",
        "scope": "cluster"
    }, None),
    'user_role_9_11': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [
            {
                "access": "readonly",
                "path": "/api/cluster/jobs",
            }
        ],
        "name": "admin",
        "scope": "cluster"
    }, None),
    'user_role_cluster_jobs_all': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [{"access": "all", "path": "/api/cluster/jobs"}],
        "name": "admin",
        "scope": "cluster"
    }, None),
    'user_role_privileges': (200, {
        "records": [
            {
                "access": "readonly",
                "_links": {
                    "self": {
                        "href": "/api/resourcelink"
                    }
                },
                "path": "/api/cluster/jobs",
            }
        ],
    }, None),
    'user_role_privileges_command': (200, {
        "records": [
            {
                "access": "all",
                'query': "-days <1 -hours >12",
                "_links": {
                    "self": {
                        "href": "/api/resourcelink"
                    }
                },
                "path": "job schedule interval",
            }
        ],
    }, None),
    'user_role_privileges_two_paths': (200, {
        "records": [
            {
                "access": "readonly",
                "_links": {
                    "self": {
                        "href": "/api/resourcelink"
                    }
                },
                "path": "/api/cluster/jobs",
            }, {
                "access": "readonly",
                "_links": {
                    "self": {
                        "href": "/api/resourcelink"
                    }
                },
                "path": "/api/storage/volumes",
            }
        ],
    }, None),
    'user_role_volume': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [
            {
                "access": "readonly",
                "path": "volume create"
            },
            {
                "access": "readonly",
                "path": "volume modify",
            },
            {
                "access": "readonly",
                "path": "volume show",
            }
        ],
        "name": "admin",
    }, None),
    'user_role_vserver': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [{"access": "readonly", "path": "vserver show"}],
        "name": "admin",
    }, None),
    'user_role_volume_privileges': (200, {
        "records": [
            {"access": "readonly", "path": "volume create"},
            {"access": "readonly", "path": "volume modify"}
        ],
    }, None),
    'user_role_privileges_schedule': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [{"access": "all", "path": "job schedule interval", "query": "-days <1 -hours >12"}],
        "name": "admin",
    }, None),
    'user_role_privileges_schedule_modify': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [{"access": "all", "path": "job schedule interval", "query": "-days <1 -hours >8"}],
        "name": "admin",
    }, None),
    'user_role_volume_with_query': (200, {
        "owner": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "privileges": [{"access": "readonly", "path": "/api/storage/volumes", "query": "-vserver vs1|vs2|vs3 -destination-aggregate aggr1|aggr2"}],
        "name": "admin",
        "scope": "cluster"
    }, None),
    "error_4": (409, None, {'code': 4, 'message': "entry doesn't exist, 'target': 'path'"}),
})

PRIVILEGES_SINGLE_WITH_QUERY = [{
    "path": "job schedule interval",
    'query': "-days <1 -hours >12"
}]

PRIVILEGES_PATH_ONLY = [{
    "path": "/api/cluster/jobs"
}]

PRIVILEGES_2_PATH_ONLY = [{
    "path": "/api/cluster/jobs"
}, {
    "path": "/api/storage/volumes"
}]

PRIVILEGES = [{
    'path': '/api/storage/volumes',
    'access': 'readonly'
}]

PRIVILEGES_911 = [{
    'path': '/api/storage/volumes',
    'access': 'readonly',
}]

PRIVILEGES_MODIFY = [{
    'path': '/api/cluster/jobs',
    'access': 'all'
}]

PRIVILEGES_COMMAND_MODIFY = [{
    'path': 'job schedule interval',
    'query': "-days <1 -hours >8"
}]

PRIVILEGES_MODIFY_911 = [{
    'path': '/api/cluster/jobs',
    'access': 'all',
}]

PRIVILEGES_MODIFY_NEW_PATH = [{
    'path': '/api/cluster/jobs',
    'access': 'all'
}, {
    "path": "/api/storage/volumes",
    "access": 'all'
}]

PRIVILEGES_MODIFY_NEW_PATH_9_11 = [{
    'path': '/api/cluster/jobs',
    'access': 'all',
}, {
    "path": "/api/storage/volumes",
    "access": 'all',
}]

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'admin',
    'vserver': 'svm1'
}


def test_privileges_query_in_9_10():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    module_args = {'privileges': PRIVILEGES_SINGLE_WITH_QUERY,
                   'use_rest': 'always'}
    my_module_object = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)
    msg = 'Minimum version of ONTAP for privileges.query is (9, 11, 1)'
    assert msg in my_module_object['msg']


def test_get_user_role_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_role() is None


def test_get_user_role_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error getting role admin: calling: security/roles: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_role, 'fail')['msg']


def test_get_user_role():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles', SRR['user_role_9_10'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_role() is not None


def test_get_user_role_9_11():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/roles', SRR['user_role_9_11'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_role() is not None


def test_create_user_role_9_10_new_format():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles', SRR['empty_records']),
        ('POST', 'security/roles', SRR['empty_good']),
        ('GET', 'security/roles', SRR['user_role_9_10'])
    ])
    module_args = {'privileges': PRIVILEGES}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_user_role_9_11_new_format():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/roles', SRR['empty_records']),
        ('POST', 'security/roles', SRR['empty_good']),
        ('GET', 'security/roles', SRR['user_role_9_10'])
    ])
    module_args = {'privileges': PRIVILEGES_911}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_user_role_9_11_new_format_query():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/roles', SRR['empty_records']),
        ('POST', 'security/roles', SRR['empty_good']),
        ('GET', 'security/roles', SRR['user_role_privileges_schedule'])
    ])
    module_args = {'privileges': PRIVILEGES_SINGLE_WITH_QUERY}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_user_role_9_10_new_format_path_only():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles', SRR['empty_records']),
        ('POST', 'security/roles', SRR['empty_good']),
        ('GET', 'security/roles', SRR['user_role_9_11'])
    ])
    module_args = {'privileges': PRIVILEGES_PATH_ONLY}
    print(module_args)
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_user_role_9_10_new_format_2_path_only():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles', SRR['empty_records']),
        ('POST', 'security/roles', SRR['empty_good']),
        ('GET', 'security/roles', SRR['user_role_9_10_two_paths'])
    ])
    module_args = {'privileges': PRIVILEGES_2_PATH_ONLY}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_user_role_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('POST', 'security/roles', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['privileges'] = PRIVILEGES
    error = expect_and_capture_ansible_exception(my_obj.create_role, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error creating role admin: calling: security/roles: got Expected error.' == error


def test_delete_user_role():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/roles', SRR['user_role_9_10']),
        ('DELETE', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin', SRR['empty_good']),
        ('GET', 'security/roles', SRR['empty_records'])
    ])
    module_args = {'state': 'absent',
                   'privileges': [{'path': "/api/storage/volumes",
                                   'access': 'readonly'}]}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_user_role_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('DELETE', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['privileges'] = PRIVILEGES
    my_obj.parameters['state'] = 'absent'
    my_obj.owner_uuid = '02c9e252-41be-11e9-81d5-00a0986138f7'
    error = expect_and_capture_ansible_exception(my_obj.delete_role, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error deleting role admin: calling: security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin: got Expected error.' == error


def test_modify_user_role_9_10():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles', SRR['user_role_9_10']),
        ('GET', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['user_role_privileges']),
        ('PATCH', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/%2Fapi%2Fcluster%2Fjobs', SRR['empty_good']),
        ('GET', 'security/roles', SRR['user_role_cluster_jobs_all'])
    ])
    module_args = {'privileges': PRIVILEGES_MODIFY}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_user_role_command_9_10():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/roles', SRR['user_role_9_11_command']),
        ('GET', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['user_role_privileges_command']),
        ('PATCH', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/job schedule interval', SRR['empty_good']),
        ('GET', 'security/roles', SRR['user_role_privileges_schedule_modify'])
    ])
    module_args = {'privileges': PRIVILEGES_COMMAND_MODIFY}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_remove_user_role_9_10():
    # This test will modify cluster/job, and delete storage/volumes
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles', SRR['user_role_9_10_two_paths']),
        ('GET', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['user_role_privileges_two_paths']),
        ('PATCH', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/%2Fapi%2Fcluster%2Fjobs', SRR['empty_good']),
        ('DELETE', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/%2Fapi%2Fstorage%2Fvolumes', SRR['empty_good']),
        ('GET', 'security/roles', SRR['user_role_cluster_jobs_all'])
    ])
    module_args = {'privileges': PRIVILEGES_MODIFY}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_user_role_9_11():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/roles', SRR['user_role_9_11']),
        ('GET', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['user_role_privileges']),
        ('PATCH', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/%2Fapi%2Fcluster%2Fjobs', SRR['empty_good']),
        ('GET', 'security/roles', SRR['user_role_cluster_jobs_all'])
    ])
    module_args = {'privileges': PRIVILEGES_MODIFY_911}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_user_role_create_new_privilege():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles', SRR['user_role_9_10']),
        ('GET', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['user_role_privileges']),
        ('PATCH', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/%2Fapi%2Fcluster%2Fjobs', SRR['empty_good']),  # First path
        ('POST', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['empty_good']),  # Second path
        ('GET', 'security/roles', SRR['user_role_9_10_two_paths_modified'])
    ])
    module_args = {'privileges': PRIVILEGES_MODIFY_NEW_PATH}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_user_role_create_new_privilege_9_11():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/roles', SRR['user_role_9_11']),
        ('GET', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['user_role_privileges']),
        ('PATCH', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/%2Fapi%2Fcluster%2Fjobs', SRR['empty_good']),  # First path
        ('POST', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['empty_good']),  # Second path
        ('GET', 'security/roles', SRR['empty_records'])
    ])
    module_args = {'privileges': PRIVILEGES_MODIFY_NEW_PATH_9_11}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_remove_user_role_error():
    # This test will modify cluster/job, and delete storage/volumes
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('DELETE', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/%2Fapi%2Fstorage%2Fvolumes', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['name'] = 'admin'
    my_obj.owner_uuid = '02c9e252-41be-11e9-81d5-00a0986138f7'
    error = expect_and_capture_ansible_exception(my_obj.delete_role_privilege, 'fail', '/api/storage/volumes')['msg']
    print('Info: %s' % error)
    assert 'Error deleting role privileges admin: calling: security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/%2Fapi%2Fstorage%2Fvolumes: '\
           'got Expected error.' == error


def test_get_user_role_privileges_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['name'] = 'admin'
    my_obj.owner_uuid = '02c9e252-41be-11e9-81d5-00a0986138f7'
    error = expect_and_capture_ansible_exception(my_obj.get_role_privileges_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error getting role privileges for role admin: calling: security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges: '\
           'got Expected error.' == error


def test_create_user_role_privileges_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('POST', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['name'] = 'admin'
    my_obj.owner_uuid = '02c9e252-41be-11e9-81d5-00a0986138f7'
    error = expect_and_capture_ansible_exception(my_obj.create_role_privilege, 'fail', PRIVILEGES[0])['msg']
    print('Info: %s' % error)
    assert 'Error creating role privilege /api/storage/volumes: calling: security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges: '\
           'got Expected error.' == error


def test_modify_user_role_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['user_role_privileges']),
        ('PATCH', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/%2Fapi%2Fcluster%2Fjobs', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['privileges'] = PRIVILEGES_MODIFY
    my_obj.owner_uuid = '02c9e252-41be-11e9-81d5-00a0986138f7'
    current = {'privileges': PRIVILEGES_MODIFY}
    error = expect_and_capture_ansible_exception(my_obj.modify_role, 'fail', current)['msg']
    print('Info: %s' % error)
    assert 'Error modifying privileges for path %2Fapi%2Fcluster%2Fjobs: calling: '\
           'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/%2Fapi%2Fcluster%2Fjobs: '\
           'got Expected error.' == error


def test_warnings_additional_commands_added_after_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/roles', SRR['empty_records']),
        ('POST', 'security/roles', SRR['empty_good']),
        ('GET', 'security/roles', SRR['user_role_volume'])
    ])
    args = {'privileges': [{'path': 'volume create', 'access': 'all'}]}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert_warning_was_raised("Create operation also affected additional related commands", partial_match=True)


def test_warnings_create_required_after_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/roles', SRR['user_role_volume']),
        ('GET', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['user_role_volume_privileges']),
        ('DELETE', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/volume modify', SRR['empty_good']),
        ('GET', 'security/roles', SRR['empty_records']),
    ])
    args = {'privileges': [{'path': 'volume create', 'access': 'readonly'}]}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert_warning_was_raised("Create role is required", partial_match=True)


def test_warnings_modify_required_after_original_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'security/roles', SRR['user_role_volume']),
        ('GET', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges', SRR['user_role_volume_privileges']),
        ('DELETE', 'security/roles/02c9e252-41be-11e9-81d5-00a0986138f7/admin/privileges/volume modify', SRR['error_4']),
        ('GET', 'security/roles', SRR['user_role_vserver']),
    ])
    args = {'privileges': [{'path': 'volume create', 'access': 'readonly'}]}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert_warning_was_raised("modify is required, desired", partial_match=True)


def test_error_with_legacy_commands_9_10_1():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    args = {'privileges': [{'path': 'volume create', 'access': 'readonly'}]}
    assert "Error: Invalid URI ['volume create']" in create_module(my_module, DEFAULT_ARGS, args, fail=True)['msg']
