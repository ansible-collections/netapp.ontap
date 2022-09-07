# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_s3_groups \
    import NetAppOntapS3Groups as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    's3_group': (200, {
        "records": [
            {
                "comment": "Admin group",
                "name": "carchi8py_group",
                "users": [
                    {
                        "name": "carchi8py",
                        "_links": {
                            "self": {
                                "href": "/api/resourcelink"
                            }
                        },
                    }
                ],
                "policies": [
                    {
                        "name": "my_policy",
                        "_links": {
                            "self": {
                                "href": "/api/resourcelink"
                            }
                        },
                    }
                ],
                "id": "5",
                "svm": {
                    "name": "svm1",
                    "uuid": "e3cb5c7f-cd20"
                }
            }
        ],
        "num_records": 1
    }, None),
    's3_group2': (200, {
        "records": [
            {
                "comment": "Admin group",
                "name": "carchi8py_group",
                "users": [
                    {
                        "name": "carchi8py",
                        "_links": {
                            "self": {
                                "href": "/api/resourcelink"
                            }
                        },
                    },
                    {
                        "name": "user2",
                        "_links": {
                            "self": {
                                "href": "/api/resourcelink"
                            }
                        },
                    }
                ],
                "policies": [
                    {
                        "name": "my_policy",
                        "_links": {
                            "self": {
                                "href": "/api/resourcelink"
                            }
                        },
                    },
                    {
                        "name": "my_policy2",
                        "_links": {
                            "self": {
                                "href": "/api/resourcelink"
                            }
                        },
                    }
                ],
                "id": "5",
                "svm": {
                    "name": "svm1",
                    "uuid": "e3cb5c7f-cd20"
                }
            }
        ],
        "num_records": 1
    }, None),
    'svm_uuid': (200, {"records": [
        {
            'uuid': 'e3cb5c7f-cd20'
        }], "num_records": 1}, None)
})

USER = {
    'name': 'carchi8py'
}

POLICY = {
    'name': 'my_policy'
}

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'carchi8py_group',
    'vserver': 'vserver',
    'users': [USER],
    'policies': [POLICY]
}


def test_low_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_97'])
    ])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error: na_ontap_s3_groups only supports REST, and requires ONTAP 9.8.0 or later.  Found: 9.7.0.'
    assert msg in error


def test_get_s3_groups_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/groups', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_s3_groups() is None


def test_get_s3_groups_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/groups', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching S3 groups carchi8py_group: calling: protocols/s3/services/e3cb5c7f-cd20/groups: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_s3_groups, 'fail')['msg']


def test_create_s3_group():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/groups', SRR['empty_records']),
        ('POST', 'protocols/s3/services/e3cb5c7f-cd20/groups', SRR['empty_good'])
    ])
    module_args = {
        'comment': 'this is a s3 group',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_s3_group_with_multi_user_policies():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/groups', SRR['empty_records']),
        ('POST', 'protocols/s3/services/e3cb5c7f-cd20/groups', SRR['empty_good'])
    ])
    module_args = {
        'comment': 'this is a s3 group',
        'users': [{'name': 'carchi8py'}, {'name': 'foo'}],
        'policies': [{'name': 'policy1'}, {'name': 'policy2'}]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_s3_group_error_no_users():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/groups', SRR['empty_records']),
    ])
    args = {
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'name': 'carchi8py_group',
        'vserver': 'vserver',
        'policies': [POLICY]
    }
    error = create_and_apply(my_module, args, {}, 'fail')['msg']
    print('Info: %s' % error)
    assert 'policies and users are required for a creating a group.' == error


def test_create_s3_group_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('POST', 'protocols/s3/services/e3cb5c7f-cd20/groups', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'this is a s3 group'
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    error = expect_and_capture_ansible_exception(my_obj.create_s3_groups, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error creating S3 groups carchi8py_group: calling: protocols/s3/services/e3cb5c7f-cd20/groups: got Expected error.' == error


def test_delete_s3_group():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/groups', SRR['s3_group']),
        ('DELETE', 'protocols/s3/services/e3cb5c7f-cd20/groups/5', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_s3_group_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('DELETE', 'protocols/s3/services/e3cb5c7f-cd20/groups/5', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    my_obj.group_id = 5
    error = expect_and_capture_ansible_exception(my_obj.delete_s3_groups, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error deleting S3 group carchi8py_group: calling: protocols/s3/services/e3cb5c7f-cd20/groups/5: got Expected error.' == error


def test_modify_s3_group():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/groups', SRR['s3_group']),
        ('PATCH', 'protocols/s3/services/e3cb5c7f-cd20/groups/5', SRR['empty_good'])
    ])
    module_args = {
        'comment': 'this is a modify comment',
        'users': [{'name': 'carchi8py'}, {'name': 'user2'}],
        'policies': [{'name': 'policy1'}, {'name': 'policy2'}]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_s3_group_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('PATCH', 'protocols/s3/services/e3cb5c7f-cd20/groups/5', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'this is a modified s3 service'
    current = {'comment': 'this is a modified s3 service'}
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    my_obj.group_id = 5
    error = expect_and_capture_ansible_exception(my_obj.modify_s3_groups, 'fail', current)['msg']
    print('Info: %s' % error)
    assert 'Error modifying S3 group carchi8py_group: calling: protocols/s3/services/e3cb5c7f-cd20/groups/5: got Expected error.' == error
