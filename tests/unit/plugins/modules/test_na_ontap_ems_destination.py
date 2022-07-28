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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ems_destination \
    import NetAppOntapEmsDestination as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


SRR = rest_responses({
    'ems_destination': (200, {
        "records": [
            {
                "name": "test",
                "type": "rest_api",
                "destination": "https://test.destination",
                "filters": [
                    {
                        "name": "test-filter"
                    }
                ]
            }],
        "num_records": 1
    }, None)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',

}


def test_get_ems_destination_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['empty_records'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_ems_destination('test') is None


def test_get_ems_destination_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['generic_error'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    my_module_object = create_module(my_module, DEFAULT_ARGS, module_args)
    msg = 'Error: calling: support/ems/destinations: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_ems_destination, 'fail')['msg']


def test_create_ems_destination():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['empty_records']),
        ('POST', 'support/ems/destinations', SRR['empty_good'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_ems_destination_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['empty_records']),
        ('POST', 'support/ems/destinations', SRR['generic_error'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.create_ems_destination, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error: calling: support/ems/destinations: got Expected error.' == error


def test_delete_ems_destination():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['ems_destination']),
        ('DELETE', 'support/ems/destinations/test', SRR['empty_good'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter'], 'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_ems_destination_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['ems_destination']),
        ('DELETE', 'support/ems/destinations/test', SRR['generic_error'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter'], 'state': 'absent'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.delete_ems_destination, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error deleting key with id 1: calling: support/ems/destinations/1: got Expected error.' == error


def test_modify_ems_destination():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['ems_destination']),
        ('PATCH', 'support/ems/destinations/test', SRR['empty_good'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['other-filter']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ems_destination_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['ems_destination']),
        ('PATCH', 'support/ems/destinations/test', SRR['generic_error'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['other-filter']}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.modify_ems_destination, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error modifying key with id 1: calling: support/ems/destinations/1: got Expected error.' == error
