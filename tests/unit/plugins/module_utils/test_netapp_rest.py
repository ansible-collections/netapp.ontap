# Copyright (c) 2018-2022 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils netapp.py - REST features '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os.path
import pytest
import sys
import tempfile

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat.mock import call, patch

# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    assert_no_warnings, assert_warning_was_raised, create_module, expect_and_capture_ansible_exception, patch_ansible, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

VERSION = {'version': {
    'full': '9.8.45',
    'generation': 9,
    'major': 8,
    'minor': 45
}}

SRR = rest_responses({
    'vservers_with_admin': (200, {
        'records': [
            {'vserver': 'vserver1', 'type': 'data '},
            {'vserver': 'vserver2', 'type': 'data '},
            {'vserver': 'cserver', 'type': 'admin'}
        ]}, None),
    'vservers_without_admin': (200, {
        'records': [
            {'vserver': 'vserver1', 'type': 'data '},
            {'vserver': 'vserver2', 'type': 'data '},
        ]}, None),
    'vservers_single': (200, {
        'records': [
            {'vserver': 'single', 'type': 'data '},
        ]}, None),
    'vservers_empty': (200, {}, None),
    'vservers_error': (200, {
        'records': [
            {'vserver': 'single', 'type': 'data '},
        ]}, 'some error'),
    'nodes': (200, {
        'records': [
            VERSION,
            {'node': 'node2', 'version': 'version'},
        ]}, None),
    'precluster_error': (400, {}, {'message': 'are available in precluster.'}),
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


def test_write_to_file():
    ''' check error and debug logs can be written to disk '''
    rest_api = create_restapi_object(DEFAULT_ARGS)
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

    # Empty data
    rest_api.write_to_file(tag='atag', filepath=filepath, append=False)
    with open(filepath, 'r') as log:
        lines = log.readlines()
        assert len(lines) == 1
        assert lines[0].strip() == 'atag'

    builtins = 'builtins' if sys.version_info > (3, 0) else '__builtin__'

    with patch('%s.open' % builtins) as mock_open:
        mock_open.side_effect = KeyError('Open error')
        exc = expect_and_capture_ansible_exception(rest_api.write_to_file, KeyError, tag='atag')
        assert str(exc) == 'Open error'
        print(mock_open.mock_calls)
        assert call('/tmp/ontap_log', 'a') in mock_open.mock_calls


def test_is_rest_true():
    ''' is_rest is expected to return True '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    is_rest = rest_api.is_rest()
    print(rest_api.errors)
    print(rest_api.debug_logs)
    assert is_rest


def test_is_rest_false():
    ''' is_rest is expected to return False '''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    is_rest = rest_api.is_rest()
    print(rest_api.errors)
    print(rest_api.debug_logs)
    assert not is_rest
    assert rest_api.errors[0] == SRR['is_zapi'][2]
    assert rest_api.debug_logs[0][0] == SRR['is_zapi'][0]    # status_code
    assert rest_api.debug_logs[0][1] == SRR['is_zapi'][2]    # error


def test_is_rest_false_9_5():
    ''' is_rest is expected to return False '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_95']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    is_rest = rest_api.is_rest()
    print(rest_api.errors)
    print(rest_api.debug_logs)
    assert not is_rest
    assert not rest_api.errors
    assert not rest_api.debug_logs


def test_is_rest_true_9_6():
    ''' is_rest is expected to return False '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    is_rest = rest_api.is_rest()
    print(rest_api.errors)
    print(rest_api.debug_logs)
    assert is_rest
    assert not rest_api.errors
    assert not rest_api.debug_logs


def test_fail_has_username_password_and_cert():
    ''' failure case in auth_method '''
    module_args = dict(cert_filepath='dummy')
    msg = 'Error: cannot have both basic authentication (username/password) and certificate authentication (cert/key files)'
    assert expect_and_capture_ansible_exception(create_restapi_object, 'fail', DEFAULT_ARGS, module_args)['msg'] == msg


def test_fail_has_username_password_and_key():
    ''' failure case in auth_method '''
    module_args = dict(key_filepath='dummy')
    msg = 'Error: cannot have both basic authentication (username/password) and certificate authentication (cert/key files)'
    assert expect_and_capture_ansible_exception(create_restapi_object, 'fail', DEFAULT_ARGS, module_args)['msg'] == msg


def test_fail_has_username_and_cert():
    ''' failure case in auth_method '''
    args = dict(DEFAULT_ARGS)
    module_args = dict(cert_filepath='dummy')
    del args['password']
    msg = 'Error: username and password have to be provided together and cannot be used with cert or key files'
    assert expect_and_capture_ansible_exception(create_restapi_object, 'fail', args, module_args)['msg'] == msg


def test_fail_has_password_and_cert():
    ''' failure case in auth_method '''
    args = dict(DEFAULT_ARGS)
    module_args = dict(cert_filepath='dummy')
    del args['username']
    msg = 'Error: username and password have to be provided together and cannot be used with cert or key files'
    assert expect_and_capture_ansible_exception(create_restapi_object, 'fail', args, module_args)['msg'] == msg


def test_has_username_password():
    ''' auth_method reports expected value '''
    rest_api = create_restapi_object(DEFAULT_ARGS)
    assert rest_api.auth_method == 'speedy_basic_auth'


def test_has_cert_no_key():
    ''' auth_method reports expected value '''
    args = dict(CERT_ARGS)
    del args['key_filepath']
    rest_api = create_restapi_object(args)
    assert rest_api.auth_method == 'single_cert'


def test_has_cert_and_key():
    ''' auth_method reports expected value '''
    rest_api = create_restapi_object(CERT_ARGS)
    assert rest_api.auth_method == 'cert_key'


def test_get_cserver():
    ''' using REST to get cserver - not sure if it's needed '''
    register_responses([
        ('GET', 'private/cli/vserver', SRR['vservers_with_admin']),
        ('GET', 'private/cli/vserver', SRR['vservers_without_admin']),
        ('GET', 'private/cli/vserver', SRR['vservers_single']),
        ('GET', 'private/cli/vserver', SRR['vservers_empty']),
        ('GET', 'private/cli/vserver', SRR['vservers_error']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    assert netapp_utils.get_cserver(rest_api, is_rest=True) == 'cserver'
    assert netapp_utils.get_cserver(rest_api, is_rest=True) is None
    assert netapp_utils.get_cserver(rest_api, is_rest=True) == 'single'
    assert netapp_utils.get_cserver(rest_api, is_rest=True) is None
    assert netapp_utils.get_cserver(rest_api, is_rest=True) is None


def test_ontaprestapi_init():
    module_args = {'http_port': 123}
    rest_api = create_restapi_object(DEFAULT_ARGS)
    assert rest_api.url == 'https://%s/api/' % DEFAULT_ARGS['hostname']
    rest_api = create_restapi_object(DEFAULT_ARGS, module_args)
    assert rest_api.url == 'https://%s:%d/api/' % (DEFAULT_ARGS['hostname'], module_args['http_port'])


@patch('logging.basicConfig')
def test_ontaprestapi_logging(mock_config):
    create_restapi_object(DEFAULT_ARGS)
    assert not mock_config.mock_calls
    module_args = {'feature_flags': {'trace_apis': True}}
    create_restapi_object(DEFAULT_ARGS, module_args)
    assert len(mock_config.mock_calls) == 1


def test_requires_ontap_9_6():
    rest_api = create_restapi_object(DEFAULT_ARGS)
    assert rest_api.requires_ontap_9_6('module_name') == 'module_name only supports REST, and requires ONTAP 9.6 or later.'


def test_requires_ontap_version():
    rest_api = create_restapi_object(DEFAULT_ARGS)
    assert rest_api.requires_ontap_version('module_name', '9.1.2') == 'module_name only supports REST, and requires ONTAP 9.1.2 or later.'


def test_options_require_ontap_version():
    rest_api = create_restapi_object(DEFAULT_ARGS)
    base = 'using %s requires ONTAP 9.1.2 or later and REST must be enabled'
    msg = base % 'option_name'
    msg_m = base % "any of ['op1', 'op2', 'op3']"
    assert rest_api.options_require_ontap_version('option_name', '9.1.2') == '%s.' % msg
    assert rest_api.options_require_ontap_version('option_name', '9.1.2', use_rest=True) == '%s - using REST.' % msg
    assert rest_api.options_require_ontap_version('option_name', '9.1.2', use_rest=False) == '%s - using ZAPI.' % msg
    assert rest_api.options_require_ontap_version(['op1', 'op2', 'op3'], '9.1.2') == '%s.' % msg_m
    rest_api.set_version(VERSION)
    assert rest_api.options_require_ontap_version(['option_name'], '9.1.2') == '%s - ONTAP version: %s.' % (msg, VERSION['version']['full'])
    assert rest_api.options_require_ontap_version(['op1', 'op2', 'op3'], '9.1.2', use_rest=True) ==\
        '%s - ONTAP version: %s - using REST.' % (msg_m, VERSION['version']['full'])


def test_meets_rest_minimum_version():
    rest_api = create_restapi_object(DEFAULT_ARGS)
    rest_api.set_version(VERSION)
    assert rest_api.meets_rest_minimum_version(True, VERSION['version']['generation'], VERSION['version']['major'])
    assert rest_api.meets_rest_minimum_version(True, VERSION['version']['generation'], VERSION['version']['major'] - 1)
    assert not rest_api.meets_rest_minimum_version(True, VERSION['version']['generation'], VERSION['version']['major'] + 1)
    assert not rest_api.meets_rest_minimum_version(True, VERSION['version']['generation'], VERSION['version']['major'], VERSION['version']['minor'] + 1)


def test_fail_if_not_rest_minimum_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['generic_error']),
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    rest_api.use_rest = 'never'
    # validate consistency bug in fail_if_not_rest_minimum_version
    assert expect_and_capture_ansible_exception(rest_api.fail_if_not_rest_minimum_version, 'fail', 'module_name', 9, 6)['msg'] ==\
        'Error: REST is required for this module, found: "use_rest: never".'
    # never
    rest_api = create_restapi_object(DEFAULT_ARGS, {'use_rest': 'never'})
    assert expect_and_capture_ansible_exception(rest_api.fail_if_not_rest_minimum_version, 'fail', 'module_name', 9, 6)['msg'] ==\
        'Error: REST is required for this module, found: "use_rest: never".'
    # REST error
    rest_api = create_restapi_object(DEFAULT_ARGS, {'use_rest': 'auto'})
    assert expect_and_capture_ansible_exception(rest_api.fail_if_not_rest_minimum_version, 'fail', 'module_name', 9, 6)['msg'] ==\
        'Error using REST for version, error: Expected error.  Error using REST for version, status_code: 400.'
    # version mismatch
    assert expect_and_capture_ansible_exception(rest_api.fail_if_not_rest_minimum_version, 'fail', 'module_name', 9, 7)['msg'] ==\
        'Error: module_name only supports REST, and requires ONTAP 9.7.0 or later.  Found: 9.6.0.'
    # version match
    assert rest_api.fail_if_not_rest_minimum_version('module_name', 9, 6) is None


def test_check_required_library():
    rest_api = create_restapi_object(DEFAULT_ARGS)
    msg = 'Failed to import the required Python library (requests)'
    with patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_REQUESTS', False):
        assert expect_and_capture_ansible_exception(rest_api.check_required_library, 'fail')['msg'].startswith(msg)


def test_build_headers():
    rest_api = create_restapi_object(DEFAULT_ARGS)
    app_version = 'basic.py/%s' % netapp_utils.COLLECTION_VERSION
    assert rest_api.build_headers() == {'X-Dot-Client-App': app_version}
    assert rest_api.build_headers(accept='accept') == {'X-Dot-Client-App': app_version, 'accept': 'accept'}
    assert rest_api.build_headers(vserver_name='vserver_name') == {'X-Dot-Client-App': app_version, 'X-Dot-SVM-Name': 'vserver_name'}
    assert rest_api.build_headers(vserver_uuid='vserver_uuid') == {'X-Dot-Client-App': app_version, 'X-Dot-SVM-UUID': 'vserver_uuid'}
    assert len(rest_api.build_headers(accept='accept', vserver_name='name', vserver_uuid='uuid')) == 4


def test_get_method():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    assert create_restapi_object(DEFAULT_ARGS).get('cluster') == (SRR['is_rest_96'][1], None)


def test_post_method():
    register_responses([
        ('POST', 'cluster', SRR['is_rest_96']),
    ])
    assert create_restapi_object(DEFAULT_ARGS).post('cluster', None) == (SRR['is_rest_96'][1], None)


def test_patch_method():
    register_responses([
        ('PATCH', 'cluster', SRR['is_rest_96']),
    ])
    assert create_restapi_object(DEFAULT_ARGS).patch('cluster', None) == (SRR['is_rest_96'][1], None)


def test_delete_method():
    register_responses([
        ('DELETE', 'cluster', SRR['is_rest_96']),
    ])
    assert create_restapi_object(DEFAULT_ARGS).delete('cluster', None) == (SRR['is_rest_96'][1], None)


def test_options_method():
    register_responses([
        ('OPTIONS', 'cluster', SRR['is_rest_96']),
    ])
    assert create_restapi_object(DEFAULT_ARGS).options('cluster', None) == (SRR['is_rest_96'][1], None)


def test_get_node_version_using_rest():
    register_responses([
        ('GET', 'cluster/nodes', SRR['nodes']),
    ])
    assert create_restapi_object(DEFAULT_ARGS).get_node_version_using_rest() == (200, SRR['nodes'][1]['records'][0], None)


def test_get_ontap_version_using_rest():
    register_responses([
        ('GET', 'cluster', SRR['precluster_error']),
        ('GET', 'cluster/nodes', SRR['nodes']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    assert rest_api.get_ontap_version_using_rest() == 200
    assert rest_api.ontap_version['major'] == VERSION['version']['major']
    assert rest_api.ontap_version['valid']


def test__is_rest():
    if not sys.version_info > (3, 0):
        return
    rest_api = create_restapi_object(DEFAULT_ARGS)
    rest_api.use_rest = 'invalid'
    msg = "use_rest must be one of: never, always, auto. Got: 'invalid'"
    assert rest_api._is_rest() == (False, msg)
    # testing always with used_unsupported_rest_properties
    rest_api.use_rest = 'always'
    msg = "REST API currently does not support 'xyz'"
    assert rest_api._is_rest(used_unsupported_rest_properties=['xyz']) == (True, msg)
    # testing never
    rest_api.use_rest = 'never'
    assert rest_api._is_rest() == (False, None)
    # we need the version
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    # testing always unconditionnally and with partially_supported_rest_properties
    rest_api.use_rest = 'always'
    msg = 'Error: Minimum version of ONTAP for xyz is (9, 7).  Current version: (9, 6, 0).'
    assert rest_api._is_rest(partially_supported_rest_properties=[('xyz', (9, 7))], parameters=['xyz']) == (True, msg)
    # No error when version requirement is matched
    assert rest_api._is_rest(partially_supported_rest_properties=[('xyz', (9, 6))], parameters=['xyz']) == (True, None)
    # No error when parameter is not used
    assert rest_api._is_rest(partially_supported_rest_properties=[('abc', (9, 6))], parameters=['xyz']) == (True, None)
    # testing auto with used_unsupported_rest_properties
    rest_api.use_rest = 'auto'
    assert rest_api._is_rest(used_unsupported_rest_properties=['xyz']) == (False, None)
    # TODO: check warning


def test_is_rest_supported_properties():
    rest_api = create_restapi_object(DEFAULT_ARGS)
    rest_api.use_rest = 'always'
    assert expect_and_capture_ansible_exception(rest_api.is_rest_supported_properties, 'fail', ['xyz'], ['xyz'])['msg'] ==\
        "REST API currently does not support 'xyz'"
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    assert rest_api.is_rest_supported_properties(['abc'], ['xyz'])
    assert rest_api.is_rest_supported_properties(['abc'], ['xyz'], report_error=True) == (True, None)


def test_is_rest_partially_supported_properties():
    if not sys.version_info > (3, 0):
        return
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    rest_api.use_rest = 'auto'
    assert not rest_api.is_rest_supported_properties(['xyz'], None, [('xyz', (9, 8, 1))])
    assert_warning_was_raised('Falling back to ZAPI because of unsupported option(s) or option value(s) "xyz" in REST require (9, 8, 1)')
    rest_api = create_restapi_object(DEFAULT_ARGS)
    rest_api.use_rest = 'auto'
    assert rest_api.is_rest_supported_properties(['xyz'], None, [('xyz', (9, 8, 1))])


def test_is_rest():
    rest_api = create_restapi_object(DEFAULT_ARGS)
    # testing always with used_unsupported_rest_properties
    rest_api.use_rest = 'always'
    msg = "REST API currently does not support 'xyz'"
    assert rest_api.is_rest(used_unsupported_rest_properties=['xyz']) == (True, msg)
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    assert rest_api.is_rest()


def test_set_version():
    rest_api = create_restapi_object(DEFAULT_ARGS)
    rest_api.set_version(VERSION)
    print('VERSION', rest_api.ontap_version)
    assert rest_api.ontap_version['generation'] == VERSION['version']['generation']
    assert rest_api.ontap_version['valid']
    rest_api.set_version({})
    assert not rest_api.ontap_version['valid']


def test_force_ontap_version_local():
    """ test get_ontap_version_from_params in isolation """
    rest_api = create_restapi_object(DEFAULT_ARGS)
    rest_api.set_version(VERSION)
    print('VERSION', rest_api.ontap_version)
    assert rest_api.ontap_version['generation'] == VERSION['version']['generation']
    # same version
    rest_api.force_ontap_version = VERSION['version']['full']
    assert not rest_api.get_ontap_version_from_params()
    # different versions
    rest_api.force_ontap_version = '10.8.1'
    warning = rest_api.get_ontap_version_from_params()
    assert rest_api.ontap_version['generation'] != VERSION['version']['generation']
    assert rest_api.ontap_version['generation'] == 10
    assert 'Forcing ONTAP version to 10.8.1 but current version is 9.8.45' in warning
    # version could not be read
    rest_api.set_version({})
    rest_api.force_ontap_version = '10.8'
    warning = rest_api.get_ontap_version_from_params()
    assert rest_api.ontap_version['generation'] != VERSION['version']['generation']
    assert rest_api.ontap_version['generation'] == 10
    assert rest_api.ontap_version['minor'] == 0
    assert 'Forcing ONTAP version to 10.8, unable to read current version:' in warning


def test_negative_force_ontap_version_local():
    """ test get_ontap_version_from_params in isolation """
    rest_api = create_restapi_object(DEFAULT_ARGS)
    # non numeric
    rest_api.force_ontap_version = '9.8P4'
    error = 'Error: unexpected format in force_ontap_version, expecting G.M.m or G.M, as in 9.10.1, got: 9.8P4,'
    assert error in expect_and_capture_ansible_exception(rest_api.get_ontap_version_from_params, 'fail')['msg']
    # too short
    rest_api.force_ontap_version = '9'
    error = 'Error: unexpected format in force_ontap_version, expecting G.M.m or G.M, as in 9.10.1, got: 9,'
    assert error in expect_and_capture_ansible_exception(rest_api.get_ontap_version_from_params, 'fail')['msg']
    # too long
    rest_api.force_ontap_version = '9.1.2.3'
    error = 'Error: unexpected format in force_ontap_version, expecting G.M.m or G.M, as in 9.10.1, got: 9.1.2.3,'
    assert error in expect_and_capture_ansible_exception(rest_api.get_ontap_version_from_params, 'fail')['msg']


def test_force_ontap_version_rest_call():
    """ test get_ontap_version_using_rest with force_ontap_version option """
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['generic_error']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    # same version
    rest_api.force_ontap_version = '9.7'
    assert rest_api.get_ontap_version_using_rest() == 200
    assert_no_warnings()
    # different versions
    rest_api.force_ontap_version = '10.8.1'
    assert rest_api.get_ontap_version_using_rest() == 200
    assert rest_api.ontap_version['generation'] == 10
    assert_warning_was_raised('Forcing ONTAP version to 10.8.1 but current version is dummy_9_9_0')
    # version could not be read
    assert rest_api.get_ontap_version_using_rest() == 200
    assert_warning_was_raised('Forcing ONTAP version to 10.8.1, unable to read current version: error: Expected error, status_code: 400')
    assert rest_api.ontap_version['generation'] == 10
