# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_s3_policies \
    import NetAppOntapS3Policies as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    's3_policy': (200, {
        "records": [
            {
                "statements": [
                    {
                        "sid": "FullAccessToBucket1",
                        "resources": [
                            "bucket1",
                            "bucket1/*"
                        ],
                        "index": 0,
                        "actions": [
                            "GetObject",
                            "PutObject",
                            "DeleteObject",
                            "ListBucket"
                        ],
                        "effect": "allow"
                    }
                ],
                "comment": "S3 policy.",
                "name": "Policy1",
                "svm": {
                    "name": "policy_name",
                    "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
                },
                "read-only": True
            }
        ],
        "num_records": 1
    }, None),
    'svm_uuid': (200, {"records": [
        {
            'uuid': 'e3cb5c7f-cd20'
        }], "num_records": 1}, None)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'policy_name',
    'vserver': 'vserver'
}

STATEMENT = {
    "sid": "FullAccessToUser1",
    "resources": [
        "bucket1",
        "bucket1/*"
    ],
    "actions": [
        "GetObject",
        "PutObject",
        "DeleteObject",
        "ListBucket"
    ],
    "effect": "allow",
}

STATEMENT2 = {
    "sid": "FullAccessToUser1",
    "resources": [
        "bucket1",
        "bucket1/*",
        "bucket2",
        "bucket2/*"
    ],
    "actions": [
        "GetObject",
        "PutObject",
        "DeleteObject",
        "ListBucket"
    ],
    "effect": "allow",
}


def test_low_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_97'])
    ])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error: na_ontap_s3_policies only supports REST, and requires ONTAP 9.8.0 or later.  Found: 9.7.0.'
    assert msg in error


def test_get_s3_policies_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/policies', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_s3_policies() is None


def test_get_s3_policies_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/policies', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching S3 policy policy_name: calling: protocols/s3/services/e3cb5c7f-cd20/policies: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_s3_policies, 'fail')['msg']


def test_create_s3_policies():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/policies', SRR['empty_records']),
        ('POST', 'protocols/s3/services/e3cb5c7f-cd20/policies', SRR['empty_good'])
    ])
    module_args = {
        'comment': 'this is a s3 user',
        'statements': [STATEMENT]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_s3_policies_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('POST', 'protocols/s3/services/e3cb5c7f-cd20/policies', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'this is a s3 policies'
    my_obj.parameters['statements'] = [STATEMENT]
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    error = expect_and_capture_ansible_exception(my_obj.create_s3_policies, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error creating S3 policy policy_name: calling: protocols/s3/services/e3cb5c7f-cd20/policies: got Expected error.' == error


def test_delete_s3_policies():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/policies', SRR['s3_policy']),
        ('DELETE', 'protocols/s3/services/e3cb5c7f-cd20/policies/policy_name', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_s3_policies_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('DELETE', 'protocols/s3/services/e3cb5c7f-cd20/policies/policy_name', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    error = expect_and_capture_ansible_exception(my_obj.delete_s3_policies, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error deleting S3 policy policy_name: calling: protocols/s3/services/e3cb5c7f-cd20/policies/policy_name: got Expected error.' == error


def test_modify_s3_policies():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/policies', SRR['s3_policy']),
        ('PATCH', 'protocols/s3/services/e3cb5c7f-cd20/policies/policy_name', SRR['empty_good'])
    ])
    module_args = {'comment': 'this is a modify comment', 'statements': [STATEMENT2]}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_s3_policies_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('PATCH', 'protocols/s3/services/e3cb5c7f-cd20/policies/policy_name', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'this is a modified s3 service'
    my_obj.parameters['statements'] = [STATEMENT2]
    current = {'comment': 'this is a modified s3 service', 'statements': [STATEMENT2]}
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    error = expect_and_capture_ansible_exception(my_obj.modify_s3_policies, 'fail', current)['msg']
    print('Info: %s' % error)
    assert 'Error modifying S3 policy policy_name: calling: protocols/s3/services/e3cb5c7f-cd20/policies/policy_name: got Expected error.' == error
