# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_zapit '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    expect_and_capture_ansible_exception, call_main, create_module, create_and_apply, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_zapit \
    import NetAppONTAPZapi as my_module, main as my_main      # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def cluster_image_info():
    version = 'Fattire__9.3.0'
    return {
        'num-records': 1,
        # composite response, attributes-list for cluster-image-get-iter and attributes for cluster-image-get
        'attributes-list': [
            {'cluster-image-info': {
                'node-id': 'node4test',
                'current-version': version}},
            {'cluster-image-info': {
                'node-id': 'node4test',
                'current-version': version}},
        ],
        'attributes': {
            'cluster-image-info': {
                'node-id': 'node4test',
                'current-version': version
            }},
    }


def build_zapi_error_custom(errno, reason, results='results'):
    ''' build an XML response
        errno as int
        reason as str
    '''
    if not netapp_utils.has_netapp_lib():
        return 'build_zapi_error: netapp-lib is missing', 'invalid'
    if results != 'results':
        return (netapp_utils.zapi.NaElement(results), 'valid')
    xml = {}
    if errno is not None:
        xml['errorno'] = errno
    if reason is not None:
        xml['reason'] = reason
    response = netapp_utils.zapi.NaElement('results')
    if xml:
        response.translate_struct(xml)
    return (response, 'valid')


ZRR = zapi_responses({
    'cluster_image_info': build_zapi_response(cluster_image_info()),
    'error_no_errno': build_zapi_error_custom(None, 'some reason'),
    'error_no_reason': build_zapi_error_custom(18408, None),
    'error_no_results': build_zapi_error_custom(None, None, 'no_results')
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'zapi': {'cluster-image-get-iter': None}
}


def test_ensure_zapi_called_cluster():
    register_responses([

        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
    ])
    module_args = {
        "use_rest": "never",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_ensure_zapi_called_vserver():
    register_responses([
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
    ])
    module_args = {
        "use_rest": "never",
        "vserver": "vserver",
        "zapi": {'cluster-image-get-iter': {'attributes': None}}
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_negative_zapi_called_attributes():
    register_responses([
        ('ZAPI', 'cluster-image-get-iter', ZRR['error']),
    ])
    module_args = {
        "use_rest": "never",
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    assert exception['msg'] == 'ZAPI failure: check errno and reason.'
    assert exception['errno'] == '12345'
    assert exception['reason'] == 'synthetic error for UT purpose'


def test_negative_zapi_called_element_no_errno():
    register_responses([
        ('ZAPI', 'cluster-image-get-iter', ZRR['error_no_errno']),
    ])
    module_args = {
        "use_rest": "never",
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    assert exception['msg'] == 'ZAPI failure: check errno and reason.'
    assert exception['errno'] == 'ESTATUSFAILED'
    assert exception['reason'] == 'some reason'


def test_negative_zapi_called_element_no_reason():
    register_responses([
        ('ZAPI', 'cluster-image-get-iter', ZRR['error_no_reason']),
    ])
    module_args = {
        "use_rest": "never",
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    assert exception['msg'] == 'ZAPI failure: check errno and reason.'
    assert exception['errno'] == '18408'
    assert exception['reason'] == 'Execution failure with unknown reason.'


def test_negative_zapi_unexpected_error():
    register_responses([
        ('ZAPI', 'cluster-image-get-iter', (netapp_utils.zapi.NaApiError(), 'valid')),
    ])
    module_args = {
        "use_rest": "never",
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    assert exception['msg'] == "Error running zapi cluster-image-get-iter: NetApp API failed. Reason - unknown:unknown"


def test_negative_two_zapis():
    register_responses([
    ])
    module_args = {
        "use_rest": "never",
        "zapi": {"1": 1, "2": 2}
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    assert 'A single ZAPI can be called at a time, received: ' in exception['msg']


def test_negative_bad_zapi_type():
    register_responses([
    ])
    module_args = {
        "use_rest": "never",
    }
    obj = create_module(my_module, DEFAULT_ARGS, module_args)
    obj.zapi = "1"
    error = 'A directory entry is expected, eg: system-get-version: , received: 1'
    assert expect_and_capture_ansible_exception(obj.run_zapi, 'fail')['msg'] == error
    obj.zapi = [3, 1]
    error = 'A directory entry is expected, eg: system-get-version: , received: [3, 1]'
    assert expect_and_capture_ansible_exception(obj.run_zapi, 'fail')['msg'] == error


# python 2.7 does not have bytes but str
BYTES_MARKER_BEGIN = "b'" if sys.version_info >= (3, 0) else ''
BYTES_MARKER_END = "'" if sys.version_info >= (3, 0) else ''
BYTES_TYPE = 'bytes' if sys.version_info >= (3, 0) else 'str'


def test_negative_zapi_called_element_no_results():
    register_responses([
        ('ZAPI', 'cluster-image-get-iter', ZRR['error_no_results']),
    ])
    module_args = {
        "use_rest": "never",
    }
    error = "Error running zapi, no results field: %s<no_results/>" % BYTES_MARKER_BEGIN
    assert error in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_bad_zapi_response_to_string():
    module_args = {
        "use_rest": "never",
    }
    obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = "Error running zapi in to_string: '%s' object has no attribute 'to_string'" % BYTES_TYPE
    assert expect_and_capture_ansible_exception(obj.jsonify_and_parse_output, 'fail', b'<bad_xml')['msg'] == error


class xml_mock:
    def __init__(self, data, action=None):
        self.data = data
        self.action = action

    def to_string(self):
        if self.action == 'raise_on_to_string':
            raise ValueError(self.data)
        return self.data


def test_negative_bad_zapi_response_bad_xml():
    module_args = {
        "use_rest": "never",
    }
    obj = create_module(my_module, DEFAULT_ARGS, module_args)
    xml = xml_mock(b'<bad_xml')
    error = "Error running zapi in xmltodict: %s<bad_xml%s: unclosed token" % (BYTES_MARKER_BEGIN, BYTES_MARKER_END)
    assert error in expect_and_capture_ansible_exception(obj.jsonify_and_parse_output, 'fail', xml)['msg']


def test_negative_bad_zapi_response_bad_json():
    # TODO: need to find some valid XML that cannot be converted in JSON.  Is it possible?
    module_args = {
        "use_rest": "never",
    }
    obj = create_module(my_module, DEFAULT_ARGS, module_args)
    xml = xml_mock(b'<bad_json><elemX-1>elem_value</elemX-1><elem-2>elem_value</elem-2></bad_json>')
    error = "Error running zapi, no results field"
    assert error in expect_and_capture_ansible_exception(obj.jsonify_and_parse_output, 'fail', xml)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_netapp_lib_error(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' == call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_zapit.HAS_JSON', False)
def test_fail_netapp_lib_error():
    assert 'the python json module is required' == call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_zapit.HAS_XMLTODICT', False)
def test_fail_netapp_lib_error():
    assert 'the python xmltodict module is required' == call_main(my_main, DEFAULT_ARGS, fail=True)['msg']
