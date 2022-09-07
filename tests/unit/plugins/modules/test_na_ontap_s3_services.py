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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_s3_services \
    import NetAppOntapS3Services as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    's3_service': (200, {
        "svm": {
            "uuid": "08c8a385-b1ac-11ec-bd2e-005056b3b297",
            "name": "ansibleSVM",
        },
        "name": "carchi-test",
        "enabled": True,
        "buckets": [
            {
                "name": "carchi-test-bucket2"
            },
            {
                "name": "carchi-test-bucket"
            }
        ],
        "users": [
            {
                "name": "root"
            }
        ],
        "comment": "this is a s3 service",
        "certificate": {
            "name": "ansibleSVM_16E1C1284D889609",
        },
    }, None)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'service1',
    'vserver': 'vserver'
}


def test_low_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_97'])
    ])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error: na_ontap_s3_services only supports REST, and requires ONTAP 9.8.0 or later.  Found: 9.7.0.'
    assert msg in error


def test_get_s3_service_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/services', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_s3_service() is None


def test_get_s3_service_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/services', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching S3 service service1: calling: protocols/s3/services: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_s3_service, 'fail')['msg']


def test_create_s3_service():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/services', SRR['empty_records']),
        ('POST', 'protocols/s3/services', SRR['empty_good'])
    ])
    module_args = {
        'enabled': True,
        'comment': 'this is a s3 service',
        'certificate_name': 'cert1',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_s3_service_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('POST', 'protocols/s3/services', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['enabled'] = True
    my_obj.parameters['comment'] = 'this is a s3 service'
    my_obj.parameters['certificate_name'] = 'cert1',
    error = expect_and_capture_ansible_exception(my_obj.create_s3_service, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error creating S3 service service1: calling: protocols/s3/services: got Expected error.' == error


def test_delete_s3_service():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/services', SRR['s3_service']),
        ('DELETE', 'protocols/s3/services/08c8a385-b1ac-11ec-bd2e-005056b3b297', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_s3_service_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('DELETE', 'protocols/s3/services/08c8a385-b1ac-11ec-bd2e-005056b3b297', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.svm_uuid = '08c8a385-b1ac-11ec-bd2e-005056b3b297'
    error = expect_and_capture_ansible_exception(my_obj.delete_s3_service, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error deleting S3 service service1: calling: protocols/s3/services/08c8a385-b1ac-11ec-bd2e-005056b3b297: got Expected error.' == error


def test_modify_s3_service():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/services', SRR['s3_service']),
        ('PATCH', 'protocols/s3/services/08c8a385-b1ac-11ec-bd2e-005056b3b297', SRR['empty_good'])
    ])
    module_args = {'comment': 'this is a modified s3 service',
                   'enabled': False,
                   'certificate_name': 'cert2',
                   }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_s3_service_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('PATCH', 'protocols/s3/services/08c8a385-b1ac-11ec-bd2e-005056b3b297', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'this is a modified s3 service'
    current = {'comment': 'this is a modified s3 service'}
    my_obj.svm_uuid = '08c8a385-b1ac-11ec-bd2e-005056b3b297'
    error = expect_and_capture_ansible_exception(my_obj.modify_s3_service, 'fail', current)['msg']
    print('Info: %s' % error)
    assert 'Error modifying S3 service service1: calling: protocols/s3/services/08c8a385-b1ac-11ec-bd2e-005056b3b297: got Expected error.' == error
