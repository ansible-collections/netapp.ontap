# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_ems_destination module '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception, call_main
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
                "type": "rest-api",
                "destination": "https://test.destination",
                "filters": [
                    {
                        "name": "test-filter"
                    }
                ]
            }],
        "num_records": 1
    }, None),
    'missing_key': (200, {
        "records": [
            {
                "name": "test",
                "type": "rest_api",
                "destination": "https://test.destination"
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
    msg = 'Error fetching EMS destination for test: calling: support/ems/destinations: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_ems_destination, 'fail', 'test')['msg']


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
        ('POST', 'support/ems/destinations', SRR['generic_error'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.create_ems_destination, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error creating EMS destinations for test: calling: support/ems/destinations: got Expected error.' == error


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
        ('DELETE', 'support/ems/destinations/test', SRR['generic_error'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter'], 'state': 'absent'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.delete_ems_destination, 'fail', 'test')['msg']
    print('Info: %s' % error)
    assert 'Error deleting EMS destination for test: calling: support/ems/destinations/test: got Expected error.' == error


def test_modify_ems_destination_filter():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['missing_key']),
        ('PATCH', 'support/ems/destinations/test', SRR['empty_good'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['other-filter']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ems_destination_rest_api_idempotent():
    """ verify that rest-api is equivalent to rest_api """
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['ems_destination']),
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ems_destination_target():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['ems_destination']),
        ('PATCH', 'support/ems/destinations/test', SRR['empty_good'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://different.destination', 'filters': ['test-filter']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ems_destination_type():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['ems_destination']),
        ('DELETE', 'support/ems/destinations/test', SRR['empty_good']),
        ('POST', 'support/ems/destinations', SRR['empty_good'])
    ])
    module_args = {'name': 'test', 'type': 'email', 'destination': 'test@hq.com', 'filters': ['test-filter']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ems_destination_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('PATCH', 'support/ems/destinations/test', SRR['generic_error'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['other-filter']}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    modify = {'filters': ['other-filter']}
    error = expect_and_capture_ansible_exception(my_obj.modify_ems_destination, 'fail', 'test', modify)['msg']
    print('Info: %s' % error)
    assert 'Error modifying EMS destination for test: calling: support/ems/destinations/test: got Expected error.' == error


def test_module_fail_without_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_zapi'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    assert 'na_ontap_ems_destination is only supported with REST API' == error


def test_apply_returns_errors_from_get_destination():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['generic_error'])
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    assert 'Error fetching EMS destination for test: calling: support/ems/destinations: got Expected error.' == error


def test_check_mode_creates_no_destination():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['empty_records']),
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, check_mode=True)['changed']


def test_changed_set_to_ok_for_expected_values():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/destinations', SRR['ems_destination']),
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args, check_mode=True)['changed']


def test_empty_modify_skips_patch():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    module_args = {'name': 'test', 'type': 'rest_api', 'destination': 'https://test.destination', 'filters': ['test-filter']}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    my_obj.modify_ems_destination('test', {})
