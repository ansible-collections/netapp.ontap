# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module unit test fixture amd helper mock_rest_and_zapi_requests """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
import ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests as uut
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke as patch_fixture
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import zapi_responses, build_zapi_response, build_zapi_error

# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses()

uut.DEBUG = True


@pytest.fixture(autouse=True, scope='module')
def patch_has_netapp_lib():
    with patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib') as has_netapp_lib:
        has_netapp_lib.return_value = False
        yield has_netapp_lib


def test_import_error_zapi_responses():
    # ZAPI canned responses when mocking invoke_elem.
    # The zapi_factory provides default responses shared across testcases.
    ZRR = zapi_responses()
    with pytest.raises(ImportError) as exc:
        zapi = ZRR['empty']
        print("ZAPI", zapi)
    msg = 'build_zapi_response: netapp-lib is missing'
    assert msg == exc.value.args[0]


def test_register_responses():
    get_version = build_zapi_response({})
    with pytest.raises(ImportError) as exc:
        uut.register_responses([
            ('get-version', get_version),
            ('get-bad-zapi', 'BAD_ZAPI')
        ], 'test_register_responses')
    msg = 'build_zapi_response: netapp-lib is missing'
    assert msg == exc.value.args[0]


def test_import_error_build_zapi_response():
    zapi = build_zapi_response({})
    expected = ('build_zapi_response: netapp-lib is missing', 'invalid')
    assert expected == zapi


def test_import_error_build_zapi_error():
    zapi = build_zapi_error(12345, 'test')
    expected = ('build_zapi_error: netapp-lib is missing', 'invalid')
    assert expected == zapi


class Module:
    def __init__(self):
        self.params = {
            'username': 'user',
            'password': 'pwd',
            'hostname': 'host',
            'use_rest': 'never',
            'cert_filepath': None,
            'key_filepath': None,
            'validate_certs': False,
            'http_port': None,
            'feature_flags': None,
        }


def test_fixture_no_netapp_lib(patch_fixture):
    uut.register_responses([
        ('GET', 'cluster', (200, {}, None))])
    mock_sr = patch_fixture
    cx = netapp_utils.OntapRestAPI(Module())
    cx.send_request('GET', 'cluster', None)
    assert 'test_fixture_no_netapp_lib' in uut._RESPONSES
    assert 'test_fixture_no_netapp_lib' in uut._REQUESTS
    uut.print_requests()
    uut.print_requests_and_responses()
    assert len(mock_sr.mock_calls) == 1
    calls = uut.get_mock_record()
    assert len([calls.get_requests()]) == 1
