
# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# Author: Laurent Nicolas, laurentn@netapp.com

""" unit tests for Ansible modules for ONTAP:
    fixture to mock REST send_request and ZAPI invoke_elem to trap all network calls

    Note: errors are reported as exception.  Additional details are printed to the output.
          pytest suppresses the output unless -s is used.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from copy import deepcopy
from functools import partial
import inspect
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

# set this to true to print messages about the fixture itself.
DEBUG = False
# if true, an error is raised if register_responses was not called.
FORCE_REGISTRATION = False


@pytest.fixture(autouse=True)
def patch_request_and_invoke(request):
    if DEBUG:
        print('entering patch_request_and_invoke fixture for', request.function)
    function_name = request.function.__name__

    with patch('time.sleep') as mock_time_sleep:
        mock_time_sleep.side_effect = partial(_mock_time_sleep, function_name)
        with patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request') as mock_send_request:
            mock_send_request.side_effect = partial(_mock_netapp_send_request, function_name)
            if netapp_utils.has_netapp_lib():
                with patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem') as mock_invoke_elem:
                    mock_invoke_elem.side_effect = partial(_mock_netapp_invoke_elem, function_name)
                    yield mock_send_request, mock_invoke_elem
            else:
                yield mock_send_request

    # This part is executed after the test completes
    _patch_request_and_invoke_exit_checks(function_name)


def register_responses(responses, function_name=None):
    ''' When patching, the pytest request identifies the UT test function
        if the registration is happening in a helper function, function_name needs to identify the calling test function
        EG:
        test_me():
            for x in range:
                check_something()
        if the registration happens in check_something, function_name needs to be set to test_me (as a string)
    '''
    caller = inspect.currentframe().f_back.f_code.co_name
    if DEBUG:
        print('register_responses - caller:', caller, 'function_name:', function_name)
    if function_name is not None and function_name != caller and (caller.startswith('test') or not function_name.startswith('test')):
        raise KeyError('inspect reported a different name: %s, received: %s' % (caller, function_name))
    if function_name is None:
        function_name = caller
    fixed_records = []
    for record in responses:
        try:
            expected_method, expected_api, response = record
            if expected_method not in ['ZAPI', 'GET', 'OPTIONS', 'POST', 'PATCH', 'DELETE']:
                raise KeyError('Unexpected method %s in %s for function: %s' % (expected_method, record, function_name))
        except ValueError:
            expected_method = 'ZAPI'
            expected_api, response = record
        if expected_method == 'ZAPI':
            # sanity checks for netapp-lib are deferred until the test is actually run
            response, valid = response
            if valid != 'valid':
                raise ImportError(response)
        # some modules modify the record in place - keep the original intact
        fixed_records.append((expected_method, expected_api, deepcopy(response)))
    _RESPONSES[function_name] = fixed_records


def get_mock_record(function_name=None):
    if function_name is None:
        function_name = inspect.currentframe().f_back.f_code.co_name
    return _REQUESTS.get(function_name)


def print_requests(function_name=None):
    if function_name is None:
        function_name = inspect.currentframe().f_back.f_code.co_name
    if function_name not in _REQUESTS:
        print('No request processed for %s' % function_name)
        return
    print('--- %s - processed requests ---' % function_name)
    for record in _REQUESTS[function_name].get_requests():
        print(record)
    print('--- %s - end of processed requests ---' % function_name)


def print_requests_and_responses(function_name=None):
    if function_name is None:
        function_name = inspect.currentframe().f_back.f_code.co_name
    if function_name not in _REQUESTS:
        print('No request processed for %s' % function_name)
        return
    print('--- %s - processed requests and responses---' % function_name)
    for record in _REQUESTS[function_name].get_responses():
        print(record)
    print('--- %s - end of processed requests and responses---' % function_name)


class MockCalls:
    '''record calls'''
    def __init__(self, function_name):
        self.function_name = function_name
        self.requests = []
        self.responses = []

    def get_responses(self, method=None, api=None):
        for record in self.responses:
            if ((method is None or record.get('method') == method)
                    and (api is None or record.get('api') == api)):
                yield record

    def get_requests(self, method=None, api=None, response=None):
        for record in self.requests:
            if ((method is None or record.get('method') == method)
                    and (api is None or record.get('api') == api)
                    and (response is None or record.get('response') == response)):
                yield record

    def is_record_in_json(self, record, method, api, response=None):
        for request in self.get_requests(method, api, response):
            json = request.get('json')
            if json and self._record_in_dict(record, json):
                return True
        return False

    def is_zapi_called(self, zapi):
        return any(self.get_requests('ZAPI', zapi))

    def get_request(self, sequence):
        return self.requests[sequence]

    def is_text_in_zapi_request(self, text, sequence, present=True):
        found = text in str(self.get_request(sequence)['zapi_request'])
        if found != present:
            not_expected = 'not ' if present else ''
            print('Error: %s %sfound in %s' % (text, not_expected, self.get_request(sequence)['zapi_request']))
        return found

    # private methods

    def __del__(self):
        if DEBUG:
            print('Deleting MockCalls instance for', self.function_name)

    def _record_response(self, method, api, response):
        print(method, api, response)
        if method == 'ZAPI':
            try:
                response = response.to_string()
            except AttributeError:
                pass
        self.responses.append((method, api, response))

    @staticmethod
    def _record_in_dict(record, adict):
        for key, value in record.items():
            if key not in adict:
                print('key: %s not found in %s' % (key, adict))
                return False
            if value != adict[key]:
                print('Values differ for key: %s: - %s vs %s' % (key, value, adict[key]))
                return False
        return True

    def _record_rest_request(self, method, api, params, json, headers, files):
        record = {
            'params': params,
            'json': json,
            'headers': headers,
            'files': files,
        }
        self._record_request(method, api, record)

    def _record_zapi_request(self, zapi, na_element, enable_tunneling):
        try:
            zapi_request = na_element.to_string()
        except AttributeError:
            zapi_request = na_element
        record = {
            'na_element': na_element,
            'zapi_request': zapi_request,
            'tunneling': enable_tunneling
        }
        self._record_request('ZAPI', zapi, record)

    def _record_request(self, method, api, record=None):
        record = record or {}
        record['function'] = self.function_name
        record['method'] = method
        record['api'] = api
        self.requests.append(record)

    def _get_response(self, method, api):
        response = _get_response(self.function_name, method, api)
        self._record_response(method, api, response)
        return response


# private variables and methods

_REQUESTS = {}
_RESPONSES = {}


def _get_response(function, method, api):
    if function not in _RESPONSES:
        print('Error: make sure to add entries for %s in RESPONSES.' % function)
        raise KeyError('function %s is not registered - %s %s' % (function, method, api))
    if not _RESPONSES[function]:
        print('Error: exhausted all entries for %s in RESPONSES, received request for %s %s' % (function, method, api))
        print_requests(function)
        raise KeyError('function %s received unhandled call %s %s' % (function, method, api))
    expected_method, expected_api, response = _RESPONSES[function][0]
    if expected_method != method or expected_api not in ['*', api]:
        print_requests(function)
        raise KeyError('function %s received an unexpected call %s %s, expecting %s %s' % (function, method, api, expected_method, expected_api))
    _RESPONSES[function].pop(0)
    if isinstance(response, Exception):
        raise response
    # some modules modify the record in place - keep the original intact
    return deepcopy(response)


def _get_or_create_mock_record(function_name):
    if function_name not in _REQUESTS:
        _REQUESTS[function_name] = MockCalls(function_name)
    return _REQUESTS[function_name]


def _mock_netapp_send_request(function_name, method, api, params, json=None, headers=None, files=None):
    if DEBUG:
        print('Inside _mock_netapp_send_request')
    mock_calls = _get_or_create_mock_record(function_name)
    mock_calls._record_rest_request(method, api, params, json, headers, files)
    return mock_calls._get_response(method, api)


def _mock_netapp_invoke_elem(function_name, na_element, enable_tunneling=False):
    if DEBUG:
        print('Inside _mock_netapp_invoke_elem')
    zapi = na_element.get_name()
    mock_calls = _get_or_create_mock_record(function_name)
    mock_calls._record_zapi_request(zapi, na_element, enable_tunneling)
    return mock_calls._get_response('ZAPI', zapi)


def _mock_time_sleep(function_name, duration):
    if DEBUG:
        print('Inside _mock_time_sleep for %s' % function_name)
    raise KeyError("time.sleep(%s) was called - add: @patch('time.sleep')" % duration)


def _patch_request_and_invoke_exit_checks(function_name):
    # action to be performed afther a test is complete
    if DEBUG:
        print('exiting patch_request_and_invoke fixture for', function_name)
    if FORCE_REGISTRATION:
        assert function_name in _RESPONSES, 'Error: responses for ZAPI invoke or REST send requests are not registered.'
    # make sure all expected requests were consumed
    if _RESPONSES.get(function_name):
        print('Error: not all responses were processed.  It is expected if the test failed.')
        print('Error: remaining responses: %s' % _RESPONSES[function_name])
        msg = 'Error: not all responses were processed.  Use -s to see detailed error.  '\
              'Ignore this error if there is an earlier error in the test.'
        assert not _RESPONSES.get(function_name), msg
    if function_name in _RESPONSES:
        del _RESPONSES[function_name]
    if function_name in _REQUESTS:
        del _REQUESTS[function_name]
