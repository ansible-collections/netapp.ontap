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

from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    patch_ansible, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
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
