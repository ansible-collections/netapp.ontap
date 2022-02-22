# Copyright (c) 2018 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils netapp.py '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    create_module, expect_and_capture_ansible_exception

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

DEFAULT_ARGS = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'cert_filepath': None,
    'key_filepath': None,
}

SINGLE_CERT_ARGS = {
    'hostname': 'test',
    'username': None,
    'password': None,
    'cert_filepath': 'cert_file',
    'key_filepath': None,
}

CERT_KEY_ARGS = {
    'hostname': 'test',
    'username': None,
    'password': None,
    'cert_filepath': 'cert_file',
    'key_filepath': 'key_file',
}


class MockONTAPModule:
    def __init__(self):
        self.module = basic.AnsibleModule(netapp_utils.na_ontap_host_argument_spec())


def create_restapi_object(args):
    module = create_module(MockONTAPModule, args)
    return netapp_utils.OntapRestAPI(module.module)


class mockResponse:
    def __init__(self, json_data, status_code, raise_action=None):
        self.json_data = json_data
        self.status_code = status_code
        self.content = json_data
        self.raise_action = raise_action

    def raise_for_status(self):
        pass

    def json(self):
        if self.raise_action == 'bad_json':
            raise ValueError(self.raise_action)
        return self.json_data


@patch('requests.request')
def test_empty_get_sent_bad_json(mock_request):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data='anything', status_code=200, raise_action='bad_json')
    rest_api = create_restapi_object(DEFAULT_ARGS)
    message, error = rest_api.get('api', None)
    assert error
    assert 'Expecting json, got: anything' in error
    print('errors:', rest_api.errors)
    print('debug:', rest_api.debug_logs)


@patch('requests.request')
def test_empty_get_sent_bad_but_empty_json(mock_request):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data='', status_code=200, raise_action='bad_json')
    rest_api = create_restapi_object(DEFAULT_ARGS)
    message, error = rest_api.get('api', None)
    assert not error


def test_wait_on_job_bad_url():
    ''' URL format error '''
    rest_api = create_restapi_object(DEFAULT_ARGS)
    api = 'testme'
    job = dict(_links=dict(self=dict(href=api)))
    message, error = rest_api.wait_on_job(job)
    msg = "URL Incorrect format: list index out of range - Job: {'_links': {'self': {'href': 'testme'}}}"
    assert msg in error


@patch('time.sleep')
@patch('requests.request')
def test_wait_on_job_timeout(mock_request, sleep_mock):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data='', status_code=200, raise_action='bad_json')
    rest_api = create_restapi_object(DEFAULT_ARGS)
    api = 'api/testme'
    job = dict(_links=dict(self=dict(href=api)))
    message, error = rest_api.wait_on_job(job)
    msg = 'Timeout error: Process still running'
    assert msg in error


@patch('time.sleep')
@patch('requests.request')
def test_wait_on_job_job_error(mock_request, sleep_mock):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data=dict(error='Job error message'), status_code=200)
    rest_api = create_restapi_object(DEFAULT_ARGS)
    api = 'api/testme'
    job = dict(_links=dict(self=dict(href=api)))
    message, error = rest_api.wait_on_job(job)
    msg = 'Job error message'
    assert msg in error


@patch('requests.request')
def test_wait_on_job_job_failure(mock_request):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data=dict(error='Job error message', state='failure', message='failure message'), status_code=200)
    rest_api = create_restapi_object(DEFAULT_ARGS)
    api = 'api/testme'
    job = dict(_links=dict(self=dict(href=api)))
    message, error = rest_api.wait_on_job(job)
    msg = 'failure message'
    assert msg in error
    assert not message


@patch('time.sleep')
@patch('requests.request')
def test_wait_on_job_timeout_running(mock_request, sleep_mock):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data=dict(error='Job error message', state='running', message='any message'), status_code=200)
    rest_api = create_restapi_object(DEFAULT_ARGS)
    api = 'api/testme'
    job = dict(_links=dict(self=dict(href=api)))
    message, error = rest_api.wait_on_job(job)
    msg = 'Timeout error: Process still running'
    assert msg in error
    assert message == 'any message'


@patch('requests.request')
def test_wait_on_job(mock_request):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data=dict(error='Job error message', state='other', message='any message'), status_code=200)
    rest_api = create_restapi_object(DEFAULT_ARGS)
    api = 'api/testme'
    job = dict(_links=dict(self=dict(href=api)))
    message, error = rest_api.wait_on_job(job)
    msg = 'Job error message'
    assert msg in error
    assert message == 'any message'


@patch('requests.request')
def test_get_auth_single_cert(mock_request):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data='', status_code=200)
    rest_api = create_restapi_object(SINGLE_CERT_ARGS)
    api = 'api/testme'
    # rest_api.auth_method = 'single_cert'
    message, error = rest_api.get(api, None)
    print(mock_request.mock_calls)
    assert rest_api.auth_method == 'single_cert'
    assert "cert='cert_file'" in str(mock_request.mock_calls[0])


@patch('requests.request')
def test_get_auth_cert_key(mock_request):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data='', status_code=200)
    rest_api = create_restapi_object(CERT_KEY_ARGS)
    api = 'api/testme'
    # rest_api.auth_method = 'single_cert'
    message, error = rest_api.get(api, None)
    print(mock_request.mock_calls)
    assert rest_api.auth_method == 'cert_key'
    assert "cert=('cert_file', 'key_file')" in str(mock_request.mock_calls[0])


def test_get_auth_method_keyerror():
    # args = {'hostname': None, 'cert_filepath': 'cert_file'}
    my_cx = create_restapi_object(CERT_KEY_ARGS)
    my_cx.auth_method = 'invalid_method'
    args = ('method', 'api', 'params')
    msg = 'xxxx'
    assert expect_and_capture_ansible_exception(my_cx.send_request, KeyError, *args) == 'invalid_method'
