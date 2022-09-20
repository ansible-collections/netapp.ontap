# Copyright (c) 2018-2022 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils netapp.py - ZAPI related features '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    patch_ansible, create_module, expect_and_capture_ansible_exception, assert_warning_was_raised, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_raw_xml_response, build_zapi_error, zapi_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip("skipping as missing required netapp_lib")

if not hasattr(netapp_utils.ssl, 'create_default_context') or not hasattr(netapp_utils.ssl, 'SSLContext'):
    pytestmark = pytest.mark.skip("skipping as missing required ssl package with SSLContext support")

ZRR = zapi_responses({
    'error_no_vserver': build_zapi_error(12345, 'Vserver API missing vserver parameter.'),
    'error_connection_error': build_zapi_error(12345, 'URLError'),
    'error_other_error': build_zapi_error(12345, 'Some other error message.'),
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


def create_ontap_module(default_args, module_args=None):
    return create_module(MockONTAPModule, default_args, module_args).module


def create_ontapzapicx_object(default_args, module_args=None):
    ontap_mock = create_module(MockONTAPModule, default_args, module_args)
    my_args = {'module': ontap_mock.module}
    for key in 'hostname', 'username', 'password', 'cert_filepath', 'key_filepath':
        if key in ontap_mock.module.params:
            my_args[key] = ontap_mock.module.params[key]
    return netapp_utils.OntapZAPICx(**my_args)


def test_ems_log_event_version():
    ''' validate Ansible version is correctly read '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
    ])
    server = netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS))
    source = 'unittest'
    netapp_utils.ems_log_event(source, server)
    request = next(get_mock_record().get_requests(api='ems-autosupport-log'))['na_element']
    version = request.get_child_content('app-version')
    assert version == netapp_utils.COLLECTION_VERSION


def test_get_cserver():
    ''' validate cluster vserser name is correctly retrieved '''
    register_responses([
        ('vserver-get-iter', ZRR['cserver']),
    ])
    server = netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS))
    cserver = netapp_utils.get_cserver(server)
    assert cserver == 'cserver'


def test_get_cserver_none():
    ''' validate cluster vserser name is correctly retrieved '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
    ])
    server = netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS))
    cserver = netapp_utils.get_cserver(server)
    assert cserver is None


def test_negative_get_cserver():
    ''' validate NaApiError is correctly reported '''
    register_responses([
        ('vserver-get-iter', ZRR['error']),
    ])
    server = netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS))
    assert expect_and_capture_ansible_exception(netapp_utils.get_cserver, netapp_utils.zapi.NaApiError, server)


def test_negative_get_cserver_connection_error():
    ''' validate NaApiError error is correctly ignore for connection or autorization issues '''
    register_responses([
        ('vserver-get-iter', ZRR['error_connection_error']),
    ])
    server = netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS))
    cserver = netapp_utils.get_cserver(server)
    assert cserver is None


def test_setup_na_ontap_zapi_logging():
    module_args = {'feature_flags': {'trace_apis': False}}
    server = netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS, module_args))
    assert not server._trace
    module_args = {'feature_flags': {'trace_apis': True}}
    server = netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS, module_args))
    assert server._trace


def test_setup_na_ontap_zapi_auth_method_and_https():
    module_args = {'feature_flags': {'trace_apis': False}}
    server = netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS, module_args))
    assert server._auth_style == server.STYLE_LOGIN_PASSWORD
    assert server.get_port() == '80'
    module_args = {'feature_flags': {'trace_apis': True}}
    server = netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(CERT_ARGS, module_args))
    assert server._auth_style == server.STYLE_CERTIFICATE
    assert server.get_port() == '443'


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_NETAPP_LIB', False)
def test_negative_setup_na_ontap_zapi():
    error = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert expect_and_capture_ansible_exception(netapp_utils.setup_na_ontap_zapi, 'fail', create_ontap_module(DEFAULT_ARGS))['msg'] == error


def test_set_zapi_port_and_transport():
    server = netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS))
    netapp_utils.set_zapi_port_and_transport(server, True, None, False)
    assert server.get_port() == '443'
    assert server.get_transport_type() == 'https'
    netapp_utils.set_zapi_port_and_transport(server, False, None, False)
    assert server.get_port() == '80'
    assert server.get_transport_type() == 'http'


def test_ems_log_event_cserver():
    ''' validate Ansible version is correctly read '''
    register_responses([
        ('vserver-get-iter', ZRR['cserver']),
        ('ems-autosupport-log', ZRR['success']),
    ])
    module = create_ontap_module(DEFAULT_ARGS)
    server = netapp_utils.setup_na_ontap_zapi(module)
    source = 'unittest'
    netapp_utils.ems_log_event_cserver(source, server, module)
    request = next(get_mock_record().get_requests(api='ems-autosupport-log'))['na_element']
    version = request.get_child_content('app-version')
    assert version == netapp_utils.COLLECTION_VERSION


def test_ems_log_event_cserver_no_admin():
    ''' no error if a vserser missing error is reported '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['success']),
    ])
    module = create_ontap_module(DEFAULT_ARGS)
    server = netapp_utils.setup_na_ontap_zapi(module)
    source = 'unittest'
    netapp_utils.ems_log_event_cserver(source, server, module)
    request = next(get_mock_record().get_requests(api='ems-autosupport-log'))['na_element']
    version = request.get_child_content('app-version')
    assert version == netapp_utils.COLLECTION_VERSION


def test_ems_log_event_cserver_other_error():
    ''' exception is raised for other errors '''
    register_responses([
        ('vserver-get-iter', ZRR['cserver']),
        ('ems-autosupport-log', ZRR['error_other_error']),
    ])
    module = create_ontap_module(DEFAULT_ARGS)
    server = netapp_utils.setup_na_ontap_zapi(module)
    source = 'unittest'
    netapp_utils.ems_log_event_cserver(source, server, module)
    request = next(get_mock_record().get_requests(api='ems-autosupport-log'))['na_element']
    version = request.get_child_content('app-version')
    assert version == netapp_utils.COLLECTION_VERSION


def test_ems_log_event_cserver_disabled():
    ''' feature flag disables cserver EMS '''
    module_args = {'feature_flags': {'no_cserver_ems': True}}
    module = create_ontap_module(DEFAULT_ARGS, module_args)
    source = 'unittest'
    assert netapp_utils.ems_log_event_cserver(source, 'dummy', module) is None


@patch('ssl.SSLContext.load_cert_chain')
def test_certificate_method_zapi(mock_ssl):
    ''' should fail when trying to read the certificate file '''
    zapi_cx = create_ontapzapicx_object(CERT_ARGS)
    assert isinstance(zapi_cx._create_certificate_auth_handler(), netapp_utils.zapi.urllib.request.HTTPSHandler)
    assert zapi_cx._get_url() == 'http://test:80/servlets/netapp.servlets.admin.XMLrequest_filer'


def test_certificate_method_zapi_missing_files():
    ''' should fail when trying to read the certificate file '''
    zapi_cx = create_ontapzapicx_object(CERT_ARGS)
    msg1 = 'Cannot load SSL certificate, check files exist.'
    # for python 2,6 :(
    msg2 = 'SSL certificate authentication requires python 2.7 or later.'
    assert expect_and_capture_ansible_exception(zapi_cx._create_certificate_auth_handler, 'fail')['msg'].startswith((msg1, msg2))
    assert zapi_cx._get_url() == 'http://test:80/servlets/netapp.servlets.admin.XMLrequest_filer'


@patch('ssl.create_default_context')
def test_negative_certificate_method_zapi(mock_ssl):
    ''' should fail when trying to set context '''
    mock_ssl.side_effect = AttributeError('for test purpose')
    zapi_cx = create_ontapzapicx_object(CERT_ARGS)
    # AttributeError('for test purpose') with 3.x but AttributeError('for test purpose',) with 2.7
    error = "SSL certificate authentication requires python 2.7 or later.  More info: AttributeError('for test purpose'"
    assert expect_and_capture_ansible_exception(zapi_cx._create_certificate_auth_handler, 'fail')['msg'].startswith(error)


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


def test_classify_zapi_exception_attributeerror():
    ''' verify output matches expectations '''
    zapi_exception = 'invalid'
    kind, new_message = netapp_utils.classify_zapi_exception(zapi_exception)
    assert kind == 'other_error'
    assert new_message == zapi_exception


def test_zapi_parse_response_sanitized():
    ''' should not fail when trying to read invalid XML characters (\x08) '''
    zapi_cx = create_ontapzapicx_object(DEFAULT_ARGS)
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
    # use feature_flags to disable sanitization
    module_args = {'feature_flags': {'sanitize_xml': False}}
    zapi_cx = create_ontapzapicx_object(DEFAULT_ARGS, module_args)
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
    module = create_ontap_module(DEFAULT_ARGS)
    zapi_cx = netapp_utils.setup_na_ontap_zapi(module)
    assert isinstance(zapi_cx, netapp_utils.OntapZAPICx)
    assert zapi_cx.base64_creds is not None
    request, dummy = zapi_cx._create_request(netapp_utils.zapi.NaElement('dummy_tag'))
    assert "Authorization" in [x[0] for x in request.header_items()]


def test_zapi_cx_add_auth_header_explicit():
    ''' should add header '''
    module_args = {'feature_flags': {'classic_basic_authorization': False}}
    module = create_ontap_module(DEFAULT_ARGS, module_args)
    zapi_cx = netapp_utils.setup_na_ontap_zapi(module)
    assert isinstance(zapi_cx, netapp_utils.OntapZAPICx)
    assert zapi_cx.base64_creds is not None
    request, dummy = zapi_cx._create_request(netapp_utils.zapi.NaElement('dummy_tag'))
    assert "Authorization" in [x[0] for x in request.header_items()]


def test_zapi_cx_no_auth_header():
    ''' should add header '''
    module_args = {'feature_flags': {'classic_basic_authorization': True, 'always_wrap_zapi': False}}
    module = create_ontap_module(DEFAULT_ARGS, module_args)
    zapi_cx = netapp_utils.setup_na_ontap_zapi(module)
    assert not isinstance(zapi_cx, netapp_utils.OntapZAPICx)
    request, dummy = zapi_cx._create_request(netapp_utils.zapi.NaElement('dummy_tag'))
    assert "Authorization" not in [x[0] for x in request.header_items()]


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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.IMPORT_EXCEPTION', 'test_exc')
def test_netapp_lib_is_required():
    msg = 'Error: the python NetApp-Lib module is required.  Import error: %s' % 'test_exc'
    assert netapp_utils.netapp_lib_is_required() == msg


def test_warn_when_rest_is_not_supported_http():
    assert netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS, {'use_rest': 'always'}))
    print_warnings()
    assert_warning_was_raised("Using ZAPI for basic.py, ignoring 'use_rest: always'.  Note: https is set to false.")


def test_warn_when_rest_is_not_supported_https():
    assert netapp_utils.setup_na_ontap_zapi(module=create_ontap_module(DEFAULT_ARGS, {'use_rest': 'always', 'https': True}))
    print_warnings()
    assert_warning_was_raised("Using ZAPI for basic.py, ignoring 'use_rest: always'.")


def test_sanitize_xml():
    zapi_cx = create_ontapzapicx_object(CERT_ARGS)
    xml = build_raw_xml_response({'test_key': 'test_Value'})
    print('XML', xml)
    assert zapi_cx.sanitize_xml(xml) == xml

    # these tests require that 'V' is not used, and 3.x because of bytes
    if sys.version_info > (3, 0):
        test_xml = zapi_cx.sanitize_xml(xml.replace(b'V', bytes([8])))
        sanitized_xml = xml.replace(b'V', b'.')
        assert zapi_cx.sanitize_xml(test_xml) == sanitized_xml

        with patch('builtins.bytes') as mock_bytes:
            # forcing bytes to return some unexpected value to force the older paths
            mock_bytes.return_value = 0
            assert zapi_cx.sanitize_xml(test_xml) == sanitized_xml
            with patch('builtins.chr') as mock_chr:
                # forcing python 2.7 behavior
                mock_chr.return_value = b'\x08'
                assert zapi_cx.sanitize_xml(test_xml) == sanitized_xml


def test_parse_response_exceptions_single():
    zapi_cx = create_ontapzapicx_object(CERT_ARGS)
    exc = expect_and_capture_ansible_exception(zapi_cx._parse_response, netapp_utils.zapi.etree.XMLSyntaxError, b'response')
    print(exc.value)
    assert str(exc.value).startswith('Start tag expected')


@patch('netapp_lib.api.zapi.zapi.NaServer._parse_response')
def test_parse_response_exceptions_double(mock_parse_response):
    xml_exc = netapp_utils.zapi.etree.XMLSyntaxError('UT', 'code', 101, 22, 'filename')
    mock_parse_response.side_effect = [xml_exc, KeyError('second exception')]
    zapi_cx = create_ontapzapicx_object(CERT_ARGS)
    exc = expect_and_capture_ansible_exception(zapi_cx._parse_response, netapp_utils.zapi.etree.XMLSyntaxError, 'response')
    print(exc)
    assert str(exc.value) == 'UT.  Received: response (filename, line 101)'

    # force an exception while processing exception
    delattr(xml_exc, 'msg')
    mock_parse_response.side_effect = [xml_exc, KeyError('second exception')]
    zapi_cx = create_ontapzapicx_object(CERT_ARGS)
    exc = expect_and_capture_ansible_exception(zapi_cx._parse_response, netapp_utils.zapi.etree.XMLSyntaxError, 'response')
    print(exc)
    assert str(exc.value) == 'None (filename, line 101)'
