# Copyright (c) 2022 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils rest_generic.py - REST features '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch

from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, create_module
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'vservers_with_admin': (200, {
        'records': [
            {'vserver': 'vserver1', 'type': 'data '},
            {'vserver': 'vserver2', 'type': 'data '},
            {'vserver': 'cserver', 'type': 'admin'}
        ]}, None),
    'vservers_single': (200, {
        'records': [
            {'vserver': 'single', 'type': 'data '},
        ]}, None),
    'accepted_response': (202, {
        'job': {
            'uuid': 'd0b3eefe-cd59-11eb-a170-005056b338cd',
            '_links': {'self': {'href': '/api/cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd'}}
        }}, None),
    'job_in_progress': (200, {
        'job': {
            'uuid': 'a1b2c3_job',
            '_links': {'self': {'href': 'api/some_link'}}
        }}, None),
    'job_success': (200, {
        'state': 'success',
        'message': 'success_message',
        'job': {
            'uuid': 'a1b2c3_job',
            '_links': {'self': {'href': 'some_link'}}
        }}, None),
    'job_failed': (200, {
        'state': 'error',
        'message': 'error_message',
        'job': {
            'uuid': 'a1b2c3_job',
            '_links': {'self': {'href': 'some_link'}}
        }}, None),
})

DEFAULT_ARGS = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'cert_filepath': None,
    'key_filepath': None,
}

CERT_ARGS = {
    'hostname': 'test',
    'cert_filepath': 'test_pem.pem',
    'key_filepath': 'test_key.key'
}


class MockONTAPModule:
    def __init__(self):
        self.module = basic.AnsibleModule(netapp_utils.na_ontap_host_argument_spec())


def create_restapi_object(default_args, module_args=None):
    module = create_module(MockONTAPModule, default_args, module_args)
    return netapp_utils.OntapRestAPI(module.module)


def test_build_query_with_fields():
    assert rest_generic.build_query_with_fields(None, None) is None
    assert rest_generic.build_query_with_fields(query=None, fields=None) is None
    assert rest_generic.build_query_with_fields(query={'aaa': 'vvv'}, fields=None) == {'aaa': 'vvv'}
    assert rest_generic.build_query_with_fields(query=None, fields='aaa,bbb') == {'fields': 'aaa,bbb'}
    assert rest_generic.build_query_with_fields(query={'aaa': 'vvv'}, fields='aaa,bbb') == {'aaa': 'vvv', 'fields': 'aaa,bbb'}


def test_build_query_with_timeout():
    assert rest_generic.build_query_with_timeout(query=None, timeout=30) == {'return_timeout': 30}

    # when timeout is 0, return_timeout is not added
    assert rest_generic.build_query_with_timeout(query=None, timeout=0) is None
    assert rest_generic.build_query_with_timeout(query={'aaa': 'vvv'}, timeout=0) == {'aaa': 'vvv'}

    # when return_timeout is in the query, it has precedence
    query = {'return_timeout': 55}
    assert rest_generic.build_query_with_timeout(query, timeout=0) == query
    assert rest_generic.build_query_with_timeout(query, timeout=20) == query
    query = {'aaa': 'vvv', 'return_timeout': 55}
    assert rest_generic.build_query_with_timeout(query, timeout=0) == query
    assert rest_generic.build_query_with_timeout(query, timeout=20) == query


def test_successful_get_one_record_no_records_field():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record, error = rest_generic.get_one_record(rest_api, 'cluster')
    assert error is None
    assert record == SRR['is_rest_9_10_1'][1]


def test_successful_get_one_record():
    register_responses([
        ('GET', 'cluster', SRR['vservers_single'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record, error = rest_generic.get_one_record(rest_api, 'cluster')
    assert error is None
    assert record == SRR['vservers_single'][1]['records'][0]


def test_successful_get_one_record_no_record():
    register_responses([
        ('GET', 'cluster', SRR['zero_records'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record, error = rest_generic.get_one_record(rest_api, 'cluster')
    assert error is None
    assert record is None


def test_successful_get_one_record_NN():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record, error = rest_generic.get_one_record(rest_api, 'cluster', query=None, fields=None)
    assert error is None
    assert record == SRR['is_rest_9_10_1'][1]


def test_successful_get_one_record_NV():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record, error = rest_generic.get_one_record(rest_api, 'cluster', query=None, fields='aaa,bbb')
    assert error is None
    assert record == SRR['is_rest_9_10_1'][1]


def test_successful_get_one_record_VN():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record, error = rest_generic.get_one_record(rest_api, 'cluster', query={'aaa': 'value'}, fields=None)
    assert error is None
    assert record == SRR['is_rest_9_10_1'][1]


def test_successful_get_one_record_VV():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record, error = rest_generic.get_one_record(rest_api, 'cluster', query={'aaa': 'value'}, fields='aaa,bbb')
    assert error is None
    assert record == SRR['is_rest_9_10_1'][1]


def test_error_get_one_record_empty():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record, error = rest_generic.get_one_record(rest_api, 'cluster', query=None, fields=None)
    assert error == 'calling: cluster: no response {}.'
    assert record is None


def test_error_get_one_record_multiple():
    register_responses([
        ('GET', 'cluster', SRR['vservers_with_admin'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record, error = rest_generic.get_one_record(rest_api, 'cluster', query={'aaa': 'vvv'}, fields=None)
    assert "calling: cluster: unexpected response {'records':" in error
    assert "for query: {'aaa': 'vvv'}" in error
    assert record == SRR['vservers_with_admin'][1]


def test_error_get_one_record_rest_error():
    register_responses([
        ('GET', 'cluster', SRR['generic_error'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record, error = rest_generic.get_one_record(rest_api, 'cluster', query=None, fields=None)
    assert error == 'calling: cluster: got Expected error.'
    assert record is None


def test_successful_get_0_or_more_records():
    register_responses([
        ('GET', 'cluster', SRR['vservers_with_admin'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    records, error = rest_generic.get_0_or_more_records(rest_api, 'cluster')
    assert error is None
    assert records == SRR['vservers_with_admin'][1]['records']


def test_successful_get_0_or_more_records_NN():
    register_responses([
        ('GET', 'cluster', SRR['vservers_with_admin'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    records, error = rest_generic.get_0_or_more_records(rest_api, 'cluster', query=None, fields=None)
    assert error is None
    assert records == SRR['vservers_with_admin'][1]['records']


def test_successful_get_0_or_more_records_NV():
    register_responses([
        ('GET', 'cluster', SRR['vservers_with_admin'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    records, error = rest_generic.get_0_or_more_records(rest_api, 'cluster', query=None, fields='aaa,bbb')
    assert error is None
    assert records == SRR['vservers_with_admin'][1]['records']


def test_successful_get_0_or_more_records_VN():
    register_responses([
        ('GET', 'cluster', SRR['vservers_with_admin'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    records, error = rest_generic.get_0_or_more_records(rest_api, 'cluster', query={'aaa': 'value'}, fields=None)
    assert error is None
    assert records == SRR['vservers_with_admin'][1]['records']


def test_successful_get_0_or_more_records_VV():
    register_responses([
        ('GET', 'cluster', SRR['vservers_with_admin'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    records, error = rest_generic.get_0_or_more_records(rest_api, 'cluster', query={'aaa': 'value'}, fields='aaa,bbb')
    assert error is None
    assert records == SRR['vservers_with_admin'][1]['records']


def test_successful_get_0_or_more_records_VV_1_record():
    register_responses([
        ('GET', 'cluster', SRR['vservers_single'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    records, error = rest_generic.get_0_or_more_records(rest_api, 'cluster', query={'aaa': 'value'}, fields='aaa,bbb')
    assert error is None
    assert records == SRR['vservers_single'][1]['records']


def test_successful_get_0_or_more_records_VV_0_record():
    register_responses([
        ('GET', 'cluster', SRR['zero_records'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    records, error = rest_generic.get_0_or_more_records(rest_api, 'cluster', query={'aaa': 'value'}, fields='aaa,bbb')
    assert error is None
    assert records is None


def test_error_get_0_or_more_records():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    records, error = rest_generic.get_0_or_more_records(rest_api, 'cluster', query=None, fields=None)
    assert error == 'calling: cluster: no response {}.'
    assert records is None


def test_error_get_0_or_more_records_rest_error():
    register_responses([
        ('GET', 'cluster', SRR['generic_error'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    records, error = rest_generic.get_0_or_more_records(rest_api, 'cluster', query=None, fields=None)
    assert error == 'calling: cluster: got Expected error.'
    assert records is None


def test_successful_post_async():
    register_responses([
        ('POST', 'cluster', SRR['vservers_single'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.post_async(rest_api, 'cluster', {})
    assert error is None
    assert response == SRR['vservers_single'][1]


def test_error_post_async():
    register_responses([
        ('POST', 'cluster', SRR['generic_error'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.post_async(rest_api, 'cluster', {})
    assert error == 'calling: cluster: got Expected error.'
    assert response is None


@patch('time.sleep')
def test_successful_post_async_with_job(dont_sleep):
    register_responses([
        ('POST', 'cluster', SRR['accepted_response']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_success'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.post_async(rest_api, 'cluster', {})
    assert error is None
    assert 'job_response' in response
    assert response['job_response'] == 'success_message'


@patch('time.sleep')
def test_successful_post_async_with_job_failure(dont_sleep):
    register_responses([
        ('POST', 'cluster', SRR['accepted_response']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_failed'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.post_async(rest_api, 'cluster', {})
    assert error is None
    assert 'job_response' in response
    assert response['job_response'] == 'error_message'


@patch('time.sleep')
def test_error_post_async_with_job(dont_sleep):
    register_responses([
        ('POST', 'cluster', SRR['accepted_response']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.post_async(rest_api, 'cluster', {})
    assert 'job reported error: Expected error - Expected error - Expected error - Expected error, received' in error
    assert response == SRR['accepted_response'][1]


def test_successful_patch_async():
    register_responses([
        ('PATCH', 'cluster/uuid', SRR['vservers_single'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.patch_async(rest_api, 'cluster', 'uuid', {})
    assert error is None
    assert response == SRR['vservers_single'][1]


def test_error_patch_async():
    register_responses([
        ('PATCH', 'cluster/uuid', SRR['generic_error'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.patch_async(rest_api, 'cluster', 'uuid', {})
    assert error == 'calling: cluster/uuid: got Expected error.'
    assert response is None


@patch('time.sleep')
def test_successful_patch_async_with_job(dont_sleep):
    register_responses([
        ('PATCH', 'cluster/uuid', SRR['accepted_response']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_success'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.patch_async(rest_api, 'cluster', 'uuid', {})
    assert error is None
    assert 'job_response' in response
    assert response['job_response'] == 'success_message'


@patch('time.sleep')
def test_successful_patch_async_with_job_failure(dont_sleep):
    register_responses([
        ('PATCH', 'cluster/uuid', SRR['accepted_response']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_failed'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.patch_async(rest_api, 'cluster', 'uuid', {})
    assert error is None
    assert 'job_response' in response
    assert response['job_response'] == 'error_message'


@patch('time.sleep')
def test_error_patch_async_with_job(dont_sleep):
    register_responses([
        ('PATCH', 'cluster/uuid', SRR['accepted_response']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.patch_async(rest_api, 'cluster', 'uuid', {})
    assert 'job reported error: Expected error - Expected error - Expected error - Expected error, received' in error
    assert response == SRR['accepted_response'][1]


def test_successful_delete_async():
    register_responses([
        ('DELETE', 'cluster/uuid', SRR['vservers_single'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.delete_async(rest_api, 'cluster', 'uuid')
    assert error is None
    assert response == SRR['vservers_single'][1]


def test_error_delete_async():
    register_responses([
        ('DELETE', 'cluster/uuid', SRR['generic_error'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.delete_async(rest_api, 'cluster', 'uuid')
    assert error == 'calling: cluster/uuid: got Expected error.'
    assert response is None


@patch('time.sleep')
def test_successful_delete_async_with_job(dont_sleep):
    register_responses([
        ('DELETE', 'cluster/uuid', SRR['accepted_response']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_success'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.delete_async(rest_api, 'cluster', 'uuid')
    assert error is None
    assert 'job_response' in response
    assert response['job_response'] == 'success_message'


@patch('time.sleep')
def test_successful_delete_async_with_job_failure(dont_sleep):
    register_responses([
        ('DELETE', 'cluster/uuid', SRR['accepted_response']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_failed'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.delete_async(rest_api, 'cluster', 'uuid')
    assert error is None
    assert 'job_response' in response
    assert response['job_response'] == 'error_message'


@patch('time.sleep')
def test_error_delete_async_with_job(dont_sleep):
    register_responses([
        ('DELETE', 'cluster/uuid', SRR['accepted_response']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_in_progress']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['generic_error'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    response, error = rest_generic.delete_async(rest_api, 'cluster', 'uuid')
    assert 'job reported error: Expected error - Expected error - Expected error - Expected error, received' in error
    assert response == SRR['accepted_response'][1]
