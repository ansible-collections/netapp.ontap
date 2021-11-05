# Copyright (c) 2018 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils netapp.py '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import os.path
import sys
import tempfile

import pytest

from ansible.module_utils.ansible_release import __version__ as ansible_version
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import COLLECTION_VERSION
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip("skipping as missing required netapp_lib")


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_rest_95': (200, dict(version=dict(generation=9, major=5, minor=0, full='dummy_9_5_0')), None),
    'is_rest_96': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy_9_6_0')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': ({}, None),
    'end_of_sequence': (None, "Unexpected call to send_request"),
    'generic_error': (None, "Expected error"),
}


class MockONTAPConnection(object):
    ''' mock a server connection to ONTAP host '''

    def __init__(self, kind=None, parm1=None):
        ''' save arguments '''
        self.type = kind
        self.parm1 = parm1
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'vserver':
            xml = self.build_vserver_info(self.parm1)
        if self.type == 'no_vserver':
            xml = self.build_no_info()
        if self.type == 'error_no_vserver':
            raise netapp_utils.zapi.NaApiError(message='Vserver API missing vserver parameter.')
        if self.type == 'error_other_error':
            raise netapp_utils.zapi.NaApiError(message='Some other error message.')
        self.xml_out = xml
        return xml

    @staticmethod
    def build_vserver_info(vserver):
        ''' build xml data for vserser-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = netapp_utils.zapi.NaElement('attributes-list')
        attributes.add_node_with_children('vserver-info',
                                          **{'vserver-name': vserver})
        xml.add_child_elem(attributes)
        return xml

    @staticmethod
    def build_no_info():
        ''' build xml data for vserser-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        xml.add_new_child('num_records', '0')
        return xml


def test_ems_log_event_version():
    ''' validate Ansible version is correctly read '''
    source = 'unittest'
    server = MockONTAPConnection()
    netapp_utils.ems_log_event(source, server)
    xml = server.xml_in
    version = xml.get_child_content('app-version')
    if version == ansible_version:
        assert version == ansible_version
    else:
        assert version == COLLECTION_VERSION
    print("Ansible version: %s" % ansible_version)


def test_get_cserver():
    ''' validate cluster vserser name is correctly retrieved '''
    svm_name = 'svm1'
    server = MockONTAPConnection('vserver', svm_name)
    cserver = netapp_utils.get_cserver(server)
    assert cserver == svm_name


def test_get_cserver_none():
    ''' validate cluster vserser name is correctly retrieved '''
    svm_name = 'svm1'
    server = MockONTAPConnection('no_vserver', svm_name)
    cserver = netapp_utils.get_cserver(server)
    assert cserver is None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.setup_na_ontap_zapi')
def test_ems_log_event_cserver(mock_setup):
    ''' validate Ansible version is correctly read '''
    source = 'unittest'
    svm_name = 'svm1'
    module = 'na'
    server = MockONTAPConnection('vserver', svm_name)
    mock_setup.return_value = MockONTAPConnection('vserver', 'cserver')
    netapp_utils.ems_log_event_cserver(source, server, module)
    xml = mock_setup.return_value.xml_in
    print(xml.to_string())
    version = xml.get_child_content('app-version')
    if version == ansible_version:
        assert version == ansible_version
    else:
        assert version == COLLECTION_VERSION
    print("Ansible version: %s" % ansible_version)


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.setup_na_ontap_zapi')
def test_ems_log_event_cserver_no_admin(mock_setup):
    ''' no error is a vserser missing error is reported '''
    source = 'unittest'
    svm_name = 'svm1'
    module = 'na'
    server = MockONTAPConnection('vserver', svm_name)
    mock_setup.return_value = MockONTAPConnection('error_no_vserver')
    netapp_utils.ems_log_event_cserver(source, server, module)
    xml = mock_setup.return_value.xml_in
    print(xml.to_string())
    version = xml.get_child_content('app-version')
    if version == ansible_version:
        assert version == ansible_version
    else:
        assert version == COLLECTION_VERSION
    print("Ansible version: %s" % ansible_version)


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.setup_na_ontap_zapi')
def test_ems_log_event_cserver_other_error(mock_setup):
    ''' exception is raised for other errors '''
    source = 'unittest'
    svm_name = 'svm1'
    module = 'na'
    server = MockONTAPConnection('vserver', svm_name)
    mock_setup.return_value = MockONTAPConnection('error_other_error')
    with pytest.raises(netapp_utils.zapi.NaApiError) as exc:
        netapp_utils.ems_log_event_cserver(source, server, module)
    xml = mock_setup.return_value.xml_in
    print(xml.to_string())
    version = xml.get_child_content('app-version')
    if version == ansible_version:
        assert version == ansible_version
    else:
        assert version == COLLECTION_VERSION
    print("Ansible version: %s" % ansible_version)


def mock_args(feature_flags=None):
    args = {
        'hostname': 'test',
        'username': 'test_user',
        'password': 'test_pass!',
        'cert_filepath': None,
        'key_filepath': None,
    }
    if feature_flags is not None:
        args.update({'feature_flags': feature_flags})
    return args


def cert_args(feature_flags=None):
    args = {
        'hostname': 'test',
        'cert_filepath': 'test_pem.pem',
        'key_filepath': 'test_key.key'
    }
    if feature_flags is not None:
        args.update({'feature_flags': feature_flags})
    return args


def create_module(args):
    argument_spec = netapp_utils.na_ontap_host_argument_spec()
    set_module_args(args)
    return basic.AnsibleModule(argument_spec)


def create_restapi_object(args):
    module = create_module(args)
    module.fail_json = fail_json
    return netapp_utils.OntapRestAPI(module)


def create_ontapzapicx_object(args, feature_flags=None):
    module_args = dict(args)
    if feature_flags is not None:
        module_args['feature_flags'] = feature_flags
    module = create_module(module_args)
    module.fail_json = fail_json
    my_args = dict(args)
    my_args.update(dict(module=module))
    return netapp_utils.OntapZAPICx(**my_args)


def test_write_to_file():
    ''' check error and debug logs can be written to disk '''
    rest_api = create_restapi_object(mock_args())
    # logging an error also add a debug record
    rest_api.log_error(404, '404 error')
    print(rest_api.errors)
    print(rest_api.debug_logs)
    # logging a debug record only
    rest_api.log_debug(501, '501 error')
    print(rest_api.errors)
    print(rest_api.debug_logs)

    try:
        tempdir = tempfile.TemporaryDirectory()
        filepath = os.path.join(tempdir.name, 'log.txt')
    except AttributeError:
        # python 2.7 does not support tempfile.TemporaryDirectory
        # we're taking a small chance that there is a race condition
        filepath = '/tmp/deleteme354.txt'
    rest_api.write_debug_log_to_file(filepath=filepath, append=False)
    with open(filepath, 'r') as log:
        lines = log.readlines()
        assert len(lines) == 4
        assert lines[0].strip() == 'Debug: 404'
        assert lines[2].strip() == 'Debug: 501'

    # Idempotent, as append is False
    rest_api.write_debug_log_to_file(filepath=filepath, append=False)
    with open(filepath, 'r') as log:
        lines = log.readlines()
        assert len(lines) == 4
        assert lines[0].strip() == 'Debug: 404'
        assert lines[2].strip() == 'Debug: 501'

    # Duplication, as append is True
    rest_api.write_debug_log_to_file(filepath=filepath, append=True)
    with open(filepath, 'r') as log:
        lines = log.readlines()
        assert len(lines) == 8
        assert lines[0].strip() == 'Debug: 404'
        assert lines[2].strip() == 'Debug: 501'
        assert lines[4].strip() == 'Debug: 404'
        assert lines[6].strip() == 'Debug: 501'

    rest_api.write_errors_to_file(filepath=filepath, append=False)
    with open(filepath, 'r') as log:
        lines = log.readlines()
        assert len(lines) == 1
        assert lines[0].strip() == 'Error: 404 error'

    # Idempotent, as append is False
    rest_api.write_errors_to_file(filepath=filepath, append=False)
    with open(filepath, 'r') as log:
        lines = log.readlines()
        assert len(lines) == 1
        assert lines[0].strip() == 'Error: 404 error'

    # Duplication, as append is True
    rest_api.write_errors_to_file(filepath=filepath, append=True)
    with open(filepath, 'r') as log:
        lines = log.readlines()
        assert len(lines) == 2
        assert lines[0].strip() == 'Error: 404 error'
        assert lines[1].strip() == 'Error: 404 error'


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_is_rest_true(mock_request):
    ''' is_rest is expected to return True '''
    mock_request.side_effect = [
        SRR['is_rest'],
    ]
    rest_api = create_restapi_object(mock_args())
    is_rest = rest_api.is_rest()
    print(rest_api.errors)
    print(rest_api.debug_logs)
    assert is_rest


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_is_rest_false(mock_request):
    ''' is_rest is expected to return False '''
    mock_request.side_effect = [
        SRR['is_zapi'],
    ]
    rest_api = create_restapi_object(mock_args())
    is_rest = rest_api.is_rest()
    print(rest_api.errors)
    print(rest_api.debug_logs)
    assert not is_rest
    assert rest_api.errors[0] == SRR['is_zapi'][2]
    assert rest_api.debug_logs[0][0] == SRR['is_zapi'][0]    # status_code
    assert rest_api.debug_logs[0][1] == SRR['is_zapi'][2]    # error


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_is_rest_false_9_5(mock_request):
    ''' is_rest is expected to return False '''
    mock_request.side_effect = [
        SRR['is_rest_95'],
    ]
    rest_api = create_restapi_object(mock_args())
    is_rest = rest_api.is_rest()
    print(rest_api.errors)
    print(rest_api.debug_logs)
    assert not is_rest
    assert not rest_api.errors
    assert not rest_api.debug_logs


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_is_rest_true_9_6(mock_request):
    ''' is_rest is expected to return False '''
    mock_request.side_effect = [
        SRR['is_rest_96'],
    ]
    rest_api = create_restapi_object(mock_args())
    is_rest = rest_api.is_rest()
    print(rest_api.errors)
    print(rest_api.debug_logs)
    assert is_rest
    assert not rest_api.errors
    assert not rest_api.debug_logs


def test_has_feature_success_default():
    ''' existing feature_flag with default '''
    flag = 'deprecation_warning'
    module = create_module(mock_args())
    value = netapp_utils.has_feature(module, flag)
    assert value


def test_has_feature_success_user_true():
    ''' existing feature_flag with value set to True '''
    flag = 'user_deprecation_warning'
    args = dict(mock_args({flag: True}))
    module = create_module(args)
    value = netapp_utils.has_feature(module, flag)
    assert value


def test_has_feature_success_user_false():
    ''' existing feature_flag with value set to False '''
    flag = 'user_deprecation_warning'
    args = dict(mock_args({flag: False}))
    print(args)
    module = create_module(args)
    value = netapp_utils.has_feature(module, flag)
    assert not value


def test_has_feature_invalid_key():
    ''' existing feature_flag with unknown key '''
    flag = 'deprecation_warning_bad_key'
    module = create_module(mock_args())
    # replace ANsible fail method with ours
    module.fail_json = fail_json
    with pytest.raises(AnsibleFailJson) as exc:
        netapp_utils.has_feature(module, flag)
    msg = 'Internal error: unexpected feature flag: %s' % flag
    assert exc.value.args[0]['msg'] == msg


def test_fail_has_username_password_and_cert():
    ''' failure case in auth_method '''
    args = mock_args()
    args.update(dict(cert_filepath='dummy'))
    with pytest.raises(AnsibleFailJson) as exc:
        create_restapi_object(args)
    msg = 'Error: cannot have both basic authentication (username/password) and certificate authentication (cert/key files)'
    assert exc.value.args[0]['msg'] == msg


def test_fail_has_username_password_and_key():
    ''' failure case in auth_method '''
    args = mock_args()
    args.update(dict(key_filepath='dummy'))
    with pytest.raises(AnsibleFailJson) as exc:
        create_restapi_object(args)
    msg = 'Error: cannot have both basic authentication (username/password) and certificate authentication (cert/key files)'
    assert exc.value.args[0]['msg'] == msg


def test_fail_has_username_and_cert():
    ''' failure case in auth_method '''
    args = mock_args()
    args.update(dict(cert_filepath='dummy'))
    del args['password']
    with pytest.raises(AnsibleFailJson) as exc:
        create_restapi_object(args)
    msg = 'Error: username and password have to be provided together and cannot be used with cert or key files'
    assert exc.value.args[0]['msg'] == msg


def test_fail_has_password_and_cert():
    ''' failure case in auth_method '''
    args = mock_args()
    args.update(dict(cert_filepath='dummy'))
    del args['username']
    with pytest.raises(AnsibleFailJson) as exc:
        create_restapi_object(args)
    msg = 'Error: username and password have to be provided together and cannot be used with cert or key files'
    assert exc.value.args[0]['msg'] == msg


def test_has_username_password():
    ''' auth_method reports expected value '''
    args = mock_args()
    rest_api = create_restapi_object(args)
    assert rest_api.auth_method == 'speedy_basic_auth'


def test_has_cert_no_key():
    ''' auth_method reports expected value '''
    args = cert_args()
    del args['key_filepath']
    rest_api = create_restapi_object(args)
    assert rest_api.auth_method == 'single_cert'


def test_has_cert_and_key():
    ''' auth_method reports expected value '''
    args = cert_args()
    rest_api = create_restapi_object(args)
    assert rest_api.auth_method == 'cert_key'


def test_certificate_method_zapi():
    ''' should fail when trying to read the certificate file '''
    args = cert_args()
    zapi_cx = create_ontapzapicx_object(args)
    with pytest.raises(AnsibleFailJson) as exc:
        zapi_cx._create_certificate_auth_handler()
    msg1 = 'Cannot load SSL certificate, check files exist.'
    # for python 2,6 :(
    msg2 = 'SSL certificate authentication requires python 2.7 or later.'
    assert exc.value.args[0]['msg'].startswith((msg1, msg2))


def test_classify_zapi_exception_cluster_only():
    ''' verify output matches expectations '''
    code = 13005
    message = 'Unable to find API: diagnosis-alert-get-iter on data vserver trident_svm'
    zapi_exception = netapp_utils.zapi.NaApiError(code, message)
    kind, new_message = netapp_utils.classify_zapi_exception(zapi_exception)
    assert kind == 'missing_vserver_api_error'
    assert new_message.endswith("%d:%s" % (code, message))


def test_classify_zapi_exception_rpc_error():
    ''' verify output matches expectations '''
    code = 13001
    message = "RPC: Couldn't make connection [from mgwd on node \"laurentn-vsim1\" (VSID: -1) to mgwd at 172.32.78.223]"
    error_message = 'NetApp API failed. Reason - %d:%s' % (code, message)
    zapi_exception = netapp_utils.zapi.NaApiError(code, message)
    kind, new_message = netapp_utils.classify_zapi_exception(zapi_exception)
    assert kind == 'rpc_error'
    assert new_message == error_message


def test_classify_zapi_exception_other_error():
    ''' verify output matches expectations '''
    code = 13008
    message = 'whatever'
    error_message = 'NetApp API failed. Reason - %d:%s' % (code, message)
    zapi_exception = netapp_utils.zapi.NaApiError(code, message)
    kind, new_message = netapp_utils.classify_zapi_exception(zapi_exception)
    assert kind == 'other_error'
    assert new_message == error_message


def test_zapi_parse_response_sanitized():
    ''' should not fail when trying to read invalid XML characters (\x08) '''
    args = mock_args()
    zapi_cx = create_ontapzapicx_object(args)
    response = b"<?xml version='1.0' encoding='UTF-8' ?>\n<!DOCTYPE netapp SYSTEM 'file:/etc/netapp_gx.dtd'>\n"
    response += b"<netapp version='1.180' xmlns='http://www.netapp.com/filer/admin'>\n<results status=\"passed\">"
    response += b"<cli-output>  (cluster log-forwarding create)\n\n"
    response += b"Testing network connectivity to the destination host 10.10.10.10.              \x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\n\n"
    response += b"Error: command failed: Cannot contact destination host (10.10.10.10) from node\n"
    response += b"       &quot;laurentn-vsim1&quot;. Verify connectivity to desired host or skip the\n"
    response += b"       connectivity check with the &quot;-force&quot; parameter.</cli-output>"
    response += b"<cli-result-value>0</cli-result-value></results></netapp>\n"
    # Manually extract cli-output contents
    cli_output = response.split(b'<cli-output>')[1]
    cli_output = cli_output.split(b'</cli-output>')[0]
    cli_output = cli_output.replace(b'&quot;', b'"')
    # the XML parser would chole on \x08, zapi_cx._parse_response replaces them with '.'
    cli_output = cli_output.replace(b'\x08', b'.')
    # Use xml parser to extract cli-output contents
    xml = zapi_cx._parse_response(response)
    results = xml.get_child_by_name('results')
    new_cli_output = results.get_child_content('cli-output')
    assert cli_output.decode() == new_cli_output


def test_zapi_parse_response_unsanitized():
    ''' should fail when trying to read invalid XML characters (\x08) '''
    args = mock_args()
    # use feature_flags to disable sanitization
    zapi_cx = create_ontapzapicx_object(args, dict(sanitize_xml=False))
    response = b"<?xml version='1.0' encoding='UTF-8' ?>\n<!DOCTYPE netapp SYSTEM 'file:/etc/netapp_gx.dtd'>\n"
    response += b"<netapp version='1.180' xmlns='http://www.netapp.com/filer/admin'>\n<results status=\"passed\">"
    response += b"<cli-output>  (cluster log-forwarding create)\n\n"
    response += b"Testing network connectivity to the destination host 10.10.10.10.              \x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\x08\n\n"
    response += b"Error: command failed: Cannot contact destination host (10.10.10.10) from node\n"
    response += b"       &quot;laurentn-vsim1&quot;. Verify connectivity to desired host or skip the\n"
    response += b"       connectivity check with the &quot;-force&quot; parameter.</cli-output>"
    response += b"<cli-result-value>0</cli-result-value></results></netapp>\n"
    with pytest.raises(netapp_utils.zapi.etree.XMLSyntaxError) as exc:
        zapi_cx._parse_response(response)
    msg = 'PCDATA invalid Char value 8'
    assert exc.value.msg.startswith(msg)


def test_zapi_cx_add_auth_header():
    ''' should add header '''
    args = mock_args()
    module = create_module(args)
    zapi_cx = netapp_utils.setup_na_ontap_zapi(module)
    assert isinstance(zapi_cx, netapp_utils.OntapZAPICx)
    assert zapi_cx.base64_creds is not None
    request, dummy = zapi_cx._create_request(netapp_utils.zapi.NaElement('dummy_tag'))
    assert "Authorization" in [x[0] for x in request.header_items()]


def test_zapi_cx_add_auth_header_explicit():
    ''' should add header '''
    args = mock_args()
    args['feature_flags'] = dict(classic_basic_authorization=False)
    module = create_module(args)
    zapi_cx = netapp_utils.setup_na_ontap_zapi(module)
    assert isinstance(zapi_cx, netapp_utils.OntapZAPICx)
    assert zapi_cx.base64_creds is not None
    request, dummy = zapi_cx._create_request(netapp_utils.zapi.NaElement('dummy_tag'))
    assert "Authorization" in [x[0] for x in request.header_items()]


def test_zapi_cx_no_auth_header():
    ''' should add header '''
    args = mock_args()
    args['feature_flags'] = dict(classic_basic_authorization=True, always_wrap_zapi=False)
    module = create_module(args)
    zapi_cx = netapp_utils.setup_na_ontap_zapi(module)
    assert not isinstance(zapi_cx, netapp_utils.OntapZAPICx)
    request, dummy = zapi_cx._create_request(netapp_utils.zapi.NaElement('dummy_tag'))
    assert "Authorization" not in [x[0] for x in request.header_items()]


def test_get_na_ontap_host_argument_spec_peer():
    ''' validate spec does not have default key and feature_flags option '''
    spec = netapp_utils.na_ontap_host_argument_spec_peer()
    for key in ('username', 'https'):
        assert key in spec
    assert 'feature_flags' not in spec
    for entry in spec.values():
        assert 'type' in entry
        assert 'default' not in entry


def test_setup_host_options_from_module_params_from_empty():
    ''' make sure module.params options are reflected in host_options '''
    args = mock_args()
    module = create_module(args)
    host_options = {}
    keys = ('hostname', 'username')
    netapp_utils.setup_host_options_from_module_params(host_options, module, keys)
    # we gave 2 keys
    assert len(host_options) == 2
    for key in keys:
        assert host_options[key] == args[key]


def test_setup_host_options_from_module_params_username_not_set_when_cert_present():
    ''' make sure module.params options are reflected in host_options '''
    args = mock_args()
    module = create_module(args)
    host_options = dict(cert_filepath='some_path')
    unchanged_keys = tuple(host_options.keys())
    copied_over_keys = ('hostname',)
    ignored_keys = ('username',)
    keys = unchanged_keys + copied_over_keys + ignored_keys
    netapp_utils.setup_host_options_from_module_params(host_options, module, keys)
    # we gave 2 keys
    assert len(host_options) == 2
    for key in ignored_keys:
        assert key not in host_options
    for key in copied_over_keys:
        assert host_options[key] == args[key]
    print(host_options)
    for key in unchanged_keys:
        assert host_options[key] != args[key]


def test_setup_host_options_from_module_params_not_none_fileds_are_preserved():
    ''' make sure module.params options are reflected in host_options '''
    args = mock_args()
    args['cert_filepath'] = 'some_path'
    module = create_module(args)
    host_options = dict(cert_filepath='some_other_path')
    unchanged_keys = tuple(host_options.keys())
    copied_over_keys = ('hostname',)
    ignored_keys = ('username',)
    keys = unchanged_keys + copied_over_keys + ignored_keys
    netapp_utils.setup_host_options_from_module_params(host_options, module, keys)
    # we gave 2 keys
    assert len(host_options) == 2
    for key in ignored_keys:
        assert key not in host_options
    for key in copied_over_keys:
        assert host_options[key] == args[key]
    print(host_options)
    for key in unchanged_keys:
        assert host_options[key] != args[key]


def test_setup_host_options_from_module_params_cert_not_set_when_username_present():
    ''' make sure module.params options are reflected in host_options '''
    args = mock_args()
    args['cert_filepath'] = 'some_path'
    module = create_module(args)
    host_options = dict(username='some_name')
    unchanged_keys = tuple(host_options.keys())
    copied_over_keys = ('hostname',)
    ignored_keys = ('cert_filepath',)
    keys = unchanged_keys + copied_over_keys + ignored_keys
    netapp_utils.setup_host_options_from_module_params(host_options, module, keys)
    # we gave 2 keys
    assert len(host_options) == 2
    for key in ignored_keys:
        assert key not in host_options
    for key in copied_over_keys:
        assert host_options[key] == args[key]
    print(host_options)
    for key in unchanged_keys:
        assert host_options[key] != args[key]


def test_setup_host_options_from_module_params_conflict():
    ''' make sure module.params options are reflected in host_options '''
    args = mock_args()
    module = create_module(args)
    host_options = dict(username='some_name', key_filepath='not allowed')
    module.fail_json = fail_json
    with pytest.raises(AnsibleFailJson) as exc:
        netapp_utils.setup_host_options_from_module_params(host_options, module, host_options.keys())
    msg = 'Error: host cannot have both basic authentication (username/password) and certificate authentication (cert/key files).'
    assert exc.value.args[0]['msg'] == msg


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
    rest_api = create_restapi_object(mock_args())
    message, error = rest_api.get('api', None)
    assert error
    assert 'Expecting json, got: anything' in error
    print('errors:', rest_api.errors)
    print('debug:', rest_api.debug_logs)


@patch('requests.request')
def test_empty_get_sent_bad_but_empty_json(mock_request):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data='', status_code=200, raise_action='bad_json')
    rest_api = create_restapi_object(mock_args())
    message, error = rest_api.get('api', None)
    assert not error


def test_wait_on_job_bad_url():
    ''' URL format error '''
    rest_api = create_restapi_object(mock_args())
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
    rest_api = create_restapi_object(mock_args())
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
    rest_api = create_restapi_object(mock_args())
    api = 'api/testme'
    job = dict(_links=dict(self=dict(href=api)))
    message, error = rest_api.wait_on_job(job)
    msg = 'Job error message'
    assert msg in error


@patch('requests.request')
def test_wait_on_job_job_failure(mock_request):
    ''' get with no data '''
    mock_request.return_value = mockResponse(json_data=dict(error='Job error message', state='failure', message='failure message'), status_code=200)
    rest_api = create_restapi_object(mock_args())
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
    rest_api = create_restapi_object(mock_args())
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
    rest_api = create_restapi_object(mock_args())
    api = 'api/testme'
    job = dict(_links=dict(self=dict(href=api)))
    message, error = rest_api.wait_on_job(job)
    msg = 'Job error message'
    assert msg in error
    assert message == 'any message'


def test_is_zapi_connection_error():
    message = 'URLError'
    assert netapp_utils.is_zapi_connection_error(message)
    if sys.version_info >= (3, 5, 0):
        # not defined in python 2.7
        message = (ConnectionError(), '')
    assert netapp_utils.is_zapi_connection_error(message)
    message = []
    assert not netapp_utils.is_zapi_connection_error(message)


def test_is_zapi_write_access_error():
    message = 'Insufficient privileges: XXXXXXX does not have write access'
    assert netapp_utils.is_zapi_write_access_error(message)
    message = 'URLError'
    assert not netapp_utils.is_zapi_write_access_error(message)
    message = []
    assert not netapp_utils.is_zapi_write_access_error(message)


def test_is_zapi_missing_vserver_error():
    message = 'Vserver API missing vserver parameter.'
    assert netapp_utils.is_zapi_missing_vserver_error(message)
    message = 'URLError'
    assert not netapp_utils.is_zapi_missing_vserver_error(message)
    message = []
    assert not netapp_utils.is_zapi_missing_vserver_error(message)
