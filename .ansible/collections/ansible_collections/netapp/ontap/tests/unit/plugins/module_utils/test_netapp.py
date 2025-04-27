# Copyright (c) 2018-2022 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils netapp.py - general features '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys
import pytest
from ansible.module_utils import basic
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    patch_ansible, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

if sys.version_info < (3, 11):
    pytestmark = pytest.mark.skip("Skipping Unit Tests on 3.11")


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


def create_ontap_module(default_args=None, module_args=None):
    return create_module(MockONTAPModule, default_args, module_args).module


def test_has_feature_success_default():
    ''' existing feature_flag with default '''
    flag = 'deprecation_warning'
    module = create_ontap_module(DEFAULT_ARGS)
    assert netapp_utils.has_feature(module, flag)


def test_has_feature_success_user_true():
    ''' existing feature_flag with value set to True '''
    flag = 'user_deprecation_warning'
    module_args = {'feature_flags': {flag: True}}
    module = create_ontap_module(DEFAULT_ARGS, module_args)
    assert netapp_utils.has_feature(module, flag)


def test_has_feature_success_user_false():
    ''' existing feature_flag with value set to False '''
    flag = 'user_deprecation_warning'
    module_args = {'feature_flags': {flag: False}}
    module = create_ontap_module(DEFAULT_ARGS, module_args)
    assert not netapp_utils.has_feature(module, flag)


def test_has_feature_invalid_key():
    ''' existing feature_flag with unknown key '''
    flag = 'deprecation_warning_bad_key'
    module = create_ontap_module(DEFAULT_ARGS)
    msg = 'Internal error: unexpected feature flag: %s' % flag
    assert expect_and_capture_ansible_exception(netapp_utils.has_feature, 'fail', module, flag)['msg'] == msg


def test_has_feature_invalid_bool():
    ''' existing feature_flag with non boolean value '''
    flag = 'user_deprecation_warning'
    module_args = {'feature_flags': {flag: 'non bool'}}
    module = create_ontap_module(DEFAULT_ARGS, module_args)
    msg = 'Error: expected bool type for feature flag: %s' % flag
    assert expect_and_capture_ansible_exception(netapp_utils.has_feature, 'fail', module, flag)['msg'] == msg


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
    module = create_ontap_module(DEFAULT_ARGS)
    host_options = {}
    keys = ('hostname', 'username')
    netapp_utils.setup_host_options_from_module_params(host_options, module, keys)
    # we gave 2 keys
    assert len(host_options) == 2
    for key in keys:
        assert host_options[key] == DEFAULT_ARGS[key]


def test_setup_host_options_from_module_params_username_not_set_when_cert_present():
    ''' make sure module.params options are reflected in host_options '''
    module = create_ontap_module(DEFAULT_ARGS)
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
        assert host_options[key] == DEFAULT_ARGS[key]
    print(host_options)
    for key in unchanged_keys:
        assert host_options[key] != DEFAULT_ARGS[key]


def test_setup_host_options_from_module_params_not_none_fields_are_preserved():
    ''' make sure module.params options are reflected in host_options '''
    args = dict(DEFAULT_ARGS)
    args['cert_filepath'] = 'some_path'
    module = create_ontap_module(args)
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
    args = dict(DEFAULT_ARGS)
    args['cert_filepath'] = 'some_path'
    module = create_ontap_module(args)
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
    module = create_ontap_module(DEFAULT_ARGS)
    host_options = dict(username='some_name', key_filepath='not allowed')
    msg = 'Error: host cannot have both basic authentication (username/password) and certificate authentication (cert/key files).'
    assert expect_and_capture_ansible_exception(netapp_utils.setup_host_options_from_module_params,
                                                'fail', host_options, module, host_options.keys())['msg'] == msg


def test_set_auth_method():
    args = {'hostname': ''}
    # neither password nor cert
    error = expect_and_capture_ansible_exception(netapp_utils.set_auth_method, 'fail', create_ontap_module(args), None, None, None, None)['msg']
    assert 'Error: ONTAP module requires username/password or SSL certificate file(s)' in error
    # keyfile but no cert
    error = expect_and_capture_ansible_exception(netapp_utils.set_auth_method, 'fail', create_ontap_module(args), None, None, None, 'keyfile')['msg']
    assert 'Error: cannot have a key file without a cert file' in error
