# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module unit test fixture amd helper mock_rest_and_zapi_requests """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
import ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests as uut
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke as patch_fixture
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import zapi_responses, build_zapi_response

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')    # pragma: no cover

# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses()
# ZAPI canned responses when mocking invoke_elem.
# The zapi_factory provides default responses shared across testcases.
ZRR = zapi_responses()

uut.DEBUG = True


def test_register_responses():
    uut.register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('get-version', build_zapi_response({})),
        ('get-bad-zapi', ('BAD_ZAPI', 'valid'))
    ], 'test_register_responses')
    assert uut._get_response('test_register_responses', 'GET', 'cluster') == SRR['is_rest']
    assert uut._get_response('test_register_responses', 'ZAPI', 'get-version').to_string() == build_zapi_response({})[0].to_string()
    # If to_string() is not available, the ZAPI is registered as is.
    assert uut._get_response('test_register_responses', 'ZAPI', 'get-bad-zapi') == 'BAD_ZAPI'


def test_negative_register_responses():
    with pytest.raises(KeyError) as exc:
        uut.register_responses([
            ('MOVE', 'cluster', SRR['is_rest']),
        ], 'not_me')
    assert exc.value.args[0] == 'inspect reported a different name: test_negative_register_responses, received: not_me'

    with pytest.raises(KeyError) as exc:
        uut.register_responses([
            ('MOVE', 'cluster', SRR['is_rest']),
        ])
    assert 'Unexpected method MOVE' in exc.value.args[0]


def test_negative_get_response():
    with pytest.raises(KeyError) as exc:
        uut._get_response('test_negative_get_response', 'POST', 'cluster')
    assert exc.value.args[0] == 'function test_negative_get_response is not registered - POST cluster'

    uut.register_responses([
        ('GET', 'cluster', SRR['is_rest'])])
    with pytest.raises(KeyError) as exc:
        uut._get_response('test_negative_get_response', 'POST', 'cluster')
    assert exc.value.args[0] == 'function test_negative_get_response received an unexpected call POST cluster, expecting GET cluster'

    uut._get_response('test_negative_get_response', 'GET', 'cluster')
    with pytest.raises(KeyError) as exc:
        uut._get_response('test_negative_get_response', 'POST', 'cluster')
    assert exc.value.args[0] == 'function test_negative_get_response received unhandled call POST cluster'


def test_record_rest_request():
    function_name = 'testme'
    method = 'METHOD'
    api = 'API'
    params = 'PARAMS'
    json = {'record': {'key': 'value'}}
    headers = {}
    files = {'data': 'value'}
    calls = uut.MockCalls(function_name)
    calls._record_rest_request(method, api, params, json, headers, files)
    uut.print_requests(function_name)
    assert len([calls.get_requests(method, api)]) == 1
    assert calls.is_record_in_json({'record': {'key': 'value'}}, 'METHOD', 'API')
    assert not calls.is_record_in_json({'record': {'key': 'value1'}}, 'METHOD', 'API')
    assert not calls.is_record_in_json({'key': 'value'}, 'METHOD', 'API')


def test_record_zapi_request():
    function_name = 'testme'
    api = 'API'
    zapi = build_zapi_response({})
    tunneling = False
    calls = uut.MockCalls(function_name)
    calls._record_zapi_request(api, zapi, tunneling)
    uut.print_requests(function_name)
    assert len([calls.get_requests('ZAPI', api)]) == 1
    assert calls.is_zapi_called('API')
    assert not calls.is_zapi_called('version')


def test_negative_record_zapi_request():
    function_name = 'testme'
    api = 'API'
    zapi = 'STRING'     # AttributeError is handled in the function
    tunneling = False
    calls = uut.MockCalls(function_name)
    calls._record_zapi_request(api, zapi, tunneling)
    uut.print_requests(function_name)
    assert len([calls.get_requests('ZAPI', api)]) == 1


def test_negative_record_zapi_response():
    function_name = 'testme'
    api = 'API'
    zapi = 'STRING'     # AttributeError is handled in the function
    calls = uut.MockCalls(function_name)
    calls._record_response('ZAPI', api, zapi)
    uut.print_requests_and_responses(function_name)
    assert len([calls.get_responses('ZAPI', api)]) == 1


def test_mock_netapp_send_request():
    function_name = 'test_mock_netapp_send_request'
    method = 'GET'
    api = 'cluster'
    params = 'PARAMS'
    uut.register_responses([
        ('GET', 'cluster', SRR['is_rest'])])
    response = uut._mock_netapp_send_request(function_name, method, api, params)
    assert response == SRR['is_rest']


def test_mock_netapp_invoke_elem():
    function_name = 'test_mock_netapp_invoke_elem'
    method = 'ZAPI'
    api = 'cluster'
    params = 'PARAMS'
    zapi = netapp_utils.zapi.NaElement.create_node_with_children('get-version')
    uut.register_responses([
        ('get-version', build_zapi_response({}))])
    response = uut._mock_netapp_invoke_elem(function_name, zapi)
    assert response.to_string() == build_zapi_response({})[0].to_string()


def test_print_requests_and_responses():
    uut.print_requests_and_responses()


def test_fixture(patch_fixture):
    uut.register_responses([
        ('get-version', build_zapi_response({}))])
    mock_sr, mock_invoke = patch_fixture
    cx = netapp_utils.OntapZAPICx()
    cx.invoke_elem(netapp_utils.zapi.NaElement.create_node_with_children('get-version'))
    assert 'test_fixture' in uut._RESPONSES
    assert 'test_fixture' in uut._REQUESTS
    uut.print_requests()
    uut.print_requests_and_responses()
    assert len(mock_sr.mock_calls) == 0
    assert len(mock_invoke.mock_calls) == 1
    calls = uut.get_mock_record()
    assert len([calls.get_requests()]) == 1


def test_fixture_exit_unregistered(patch_fixture):
    uut.FORCE_REGISTRATION = True
    with pytest.raises(AssertionError) as exc:
        uut._patch_request_and_invoke_exit_checks('test_fixture_exit_unregistered')
    msg = 'Error: responses for ZAPI invoke or REST send requests are not registered.'
    assert msg in exc.value.args[0]
    uut.FORCE_REGISTRATION = False


def test_fixture_exit_unused_response(patch_fixture):
    uut.FORCE_REGISTRATION = True
    uut.register_responses([
        ('get-version', build_zapi_response({}))])
    # report an error if any response is not consumed
    with pytest.raises(AssertionError) as exc:
        uut._patch_request_and_invoke_exit_checks('test_fixture_exit_unused_response')
    msg = 'Error: not all responses were processed.  Use -s to see detailed error.  Ignore this error if there is an earlier error in the test.'
    assert msg in exc.value.args[0]
    # consume the response
    cx = netapp_utils.OntapZAPICx()
    cx.invoke_elem(netapp_utils.zapi.NaElement.create_node_with_children('get-version'))
    uut.FORCE_REGISTRATION = False
