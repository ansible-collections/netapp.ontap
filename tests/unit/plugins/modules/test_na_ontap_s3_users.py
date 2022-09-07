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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_s3_users \
    import NetAppOntapS3Users as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    's3_user': (200, {
        "records": [
            {
                "comment": "S3 user",
                "name": "carchi8py",
                "svm": {
                    "name": "svm1",
                    "uuid": "e3cb5c7f-cd20"
                }
            }
        ],
        "num_records": 1
    }, None),
    's3_user_created': (200, {
        "records": [
            {
                'access_key': 'random_access_key',
                'secret_key': 'random_secret_key'
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
    'name': 'carchi8py',
    'vserver': 'vserver'
}


def test_low_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_97'])
    ])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error: na_ontap_s3_users only supports REST, and requires ONTAP 9.8.0 or later.  Found: 9.7.0.'
    assert msg in error


def test_get_s3_users_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/users', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_s3_user() is None


def test_get_s3_users_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/users', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching S3 user carchi8py: calling: protocols/s3/services/e3cb5c7f-cd20/users: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_s3_user, 'fail')['msg']


def test_create_s3_users():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/users', SRR['empty_records']),
        ('POST', 'protocols/s3/services/e3cb5c7f-cd20/users', SRR['s3_user_created'])
    ])
    module_args = {
        'comment': 'this is a s3 user',
    }
    result = create_and_apply(my_module, DEFAULT_ARGS, module_args)
    assert result['changed']
    assert result['secret_key'] == 'random_secret_key'
    assert result['access_key'] == 'random_access_key'


def test_create_s3_users_fail_randomly():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/users', SRR['empty_records']),
        ('POST', 'protocols/s3/services/e3cb5c7f-cd20/users', SRR['empty_good'])
    ])
    module_args = {
        'comment': 'this is a s3 user',
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, 'fail')['msg']
    assert 'Error creating S3 user carchi8py' == error


def test_create_s3_user_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('POST', 'protocols/s3/services/e3cb5c7f-cd20/users', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'this is a s3 user'
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    error = expect_and_capture_ansible_exception(my_obj.create_s3_user, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error creating S3 user carchi8py: calling: protocols/s3/services/e3cb5c7f-cd20/users: got Expected error.' == error


def test_delete_s3_user():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/users', SRR['s3_user']),
        ('DELETE', 'protocols/s3/services/e3cb5c7f-cd20/users/carchi8py', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_s3_user_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('DELETE', 'protocols/s3/services/e3cb5c7f-cd20/users/carchi8py', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    error = expect_and_capture_ansible_exception(my_obj.delete_s3_user, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error deleting S3 user carchi8py: calling: protocols/s3/services/e3cb5c7f-cd20/users/carchi8py: got Expected error.' == error


def test_modify_s3_user():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/s3/services/e3cb5c7f-cd20/users', SRR['s3_user']),
        ('PATCH', 'protocols/s3/services/e3cb5c7f-cd20/users/carchi8py', SRR['empty_good'])
    ])
    module_args = {'comment': 'this is a modify comment'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_s3_user_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('PATCH', 'protocols/s3/services/e3cb5c7f-cd20/users/carchi8py', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'this is a modified s3 service'
    current = {'comment': 'this is a modified s3 service'}
    my_obj.svm_uuid = 'e3cb5c7f-cd20'
    error = expect_and_capture_ansible_exception(my_obj.modify_s3_user, 'fail', current)['msg']
    print('Info: %s' % error)
    assert 'Error modifying S3 user carchi8py: calling: protocols/s3/services/e3cb5c7f-cd20/users/carchi8py: got Expected error.' == error
