# Copyright (c) 2022 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""unit tests for module_utils netapp.py - ZAPI invoke_elem

    We cannot use the general UT framework as it patches invoke_elem
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    patch_ansible, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_raw_xml_response, zapi_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip("skipping as missing required netapp_lib")

ZRR = zapi_responses({
})


class MockModule:
    def __init__(self):
        self._name = 'testme'


class MockOpener:
    def __init__(self, response=None, exception=None):
        self.response = response
        self.exception = exception
        self.timeout = -1

    def open(self, request, timeout=None):
        self.timeout = timeout
        if self.exception:
            raise self.exception
        return self.response


class MockResponse:
    def __init__(self, contents, force_dummy=False):
        self.response = build_raw_xml_response(contents, force_dummy=force_dummy)
        print('RESPONSE', self.response)

    def read(self):
        return self.response


def create_ontapzapicx_object():
    return netapp_utils.OntapZAPICx(module=MockModule())


def test_error_invalid_naelement():
    ''' should fail when NaElement is None, empty, or not of type NaElement '''
    zapi_cx = create_ontapzapicx_object()
    assert str(expect_and_capture_ansible_exception(zapi_cx.invoke_elem, ValueError, {})) ==\
        'NaElement must be supplied to invoke API'
    assert str(expect_and_capture_ansible_exception(zapi_cx.invoke_elem, ValueError, {'x': 'yz'})) ==\
        'NaElement must be supplied to invoke API'


def test_exception_with_opener_generic_exception():
    zapi_cx = create_ontapzapicx_object()
    zapi_cx._refresh_conn = False
    zapi_cx._opener = MockOpener(exception=KeyError('testing'))
    exc = expect_and_capture_ansible_exception(zapi_cx.invoke_elem, netapp_utils.zapi.NaApiError, ZRR['success'][0])
    # KeyError('testing') in 3.x but KeyError('testing',) with 2.7
    assert str(exc.value).startswith("NetApp API failed. Reason - Unexpected error:KeyError('testing'")


def test_exception_with_opener_httperror():
    if not hasattr(netapp_utils.zapi.urllib.error.HTTPError, 'reason'):
        # skip the test in 2.6 as netapp_lib is not fully supported
        # HTTPError does not support reason, and it's not worth changing the code
        #   raise zapi.NaApiError(exc.code, exc.reason)
        #   AttributeError: 'HTTPError' object has no attribute 'reason'
        pytest.skip('this test requires HTTPError.reason which is not available in python 2.6')
    zapi_cx = create_ontapzapicx_object()
    zapi_cx._refresh_conn = False
    zapi_cx._opener = MockOpener(exception=netapp_utils.zapi.urllib.error.HTTPError('url', 400, 'testing', None, None))
    exc = expect_and_capture_ansible_exception(zapi_cx.invoke_elem, netapp_utils.zapi.NaApiError, ZRR['success'][0])
    assert str(exc.value) == 'NetApp API failed. Reason - 400:testing'


def test_exception_with_opener_urlerror():
    # ConnectionRefusedError is not defined in 2.7
    connection_error = ConnectionRefusedError('UT') if sys.version_info >= (3, 0) else 'connection_error'
    zapi_cx = create_ontapzapicx_object()
    zapi_cx._refresh_conn = False
    zapi_cx._opener = MockOpener(exception=netapp_utils.zapi.urllib.error.URLError(connection_error))
    exc = expect_and_capture_ansible_exception(zapi_cx.invoke_elem, netapp_utils.zapi.NaApiError, ZRR['success'][0])
    # skip the assert for 2.7
    # ConnectionRefusedError('UT'), with 3.x but ConnectionRefusedError('UT',), with 3.5
    assert str(exc.value).startswith("NetApp API failed. Reason - Unable to connect:(ConnectionRefusedError('UT'") or sys.version_info < (3, 0)

    zapi_cx._opener = MockOpener(exception=netapp_utils.zapi.urllib.error.URLError('connection_error'))
    exc = expect_and_capture_ansible_exception(zapi_cx.invoke_elem, netapp_utils.zapi.NaApiError, ZRR['success'][0])
    # URLError('connection_error') with 3.x but URL error:URLError('connection_error',) with 2.7
    assert str(exc.value).startswith("NetApp API failed. Reason - URL error:URLError('connection_error'")

    # force an exception when reading exc.reason
    exc = netapp_utils.zapi.urllib.error.URLError('connection_error')
    delattr(exc, 'reason')
    zapi_cx._opener = MockOpener(exception=exc)
    exc = expect_and_capture_ansible_exception(zapi_cx.invoke_elem, netapp_utils.zapi.NaApiError, ZRR['success'][0])
    # URLError('connection_error') with 3.x but URL error:URLError('connection_error',) with 2.7
    assert str(exc.value).startswith("NetApp API failed. Reason - URL error:URLError('connection_error'")


def test_response():
    zapi_cx = create_ontapzapicx_object()
    zapi_cx._refresh_conn = False
    zapi_cx._timeout = 10
    zapi_cx._trace = True
    zapi_cx._opener = MockOpener(MockResponse({}))
    response = zapi_cx.invoke_elem(ZRR['success'][0])
    print(response)
    assert response.to_string() == b'<results/>'
    assert zapi_cx._opener.timeout == 10


def test_response_no_netapp_lib():
    zapi_cx = create_ontapzapicx_object()
    zapi_cx._refresh_conn = False
    zapi_cx._timeout = 10
    zapi_cx._trace = True
    zapi_cx._opener = MockOpener(MockResponse({}, True))
    response = zapi_cx.invoke_elem(ZRR['success'][0])
    print(response)
    assert response.to_string() == b'<results status="netapp-lib is missing"/>'
    assert zapi_cx._opener.timeout == 10


def mock_build_opener(zapi_cx, opener):
    def build_opener():
        zapi_cx._opener = opener
    return build_opener


def test_response_build_opener():
    zapi_cx = create_ontapzapicx_object()
    zapi_cx._refresh_conn = False
    zapi_cx._trace = True
    zapi_cx._build_opener = mock_build_opener(zapi_cx, MockOpener(MockResponse({})))
    response = zapi_cx.invoke_elem(ZRR['success'][0])
    print(response)
    assert response.to_string() == b'<results/>'
    assert zapi_cx._opener.timeout is None
