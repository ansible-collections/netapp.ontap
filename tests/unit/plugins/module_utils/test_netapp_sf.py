# Copyright (c) 2018-2022 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils netapp.py - solidfire related methods '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    patch_ansible, create_module, expect_and_capture_ansible_exception
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

if not netapp_utils.has_sf_sdk():
    pytestmark = pytest.mark.skip("skipping as missing required solidfire")

DEFAULT_ARGS = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
}


class MockONTAPModule:
    def __init__(self):
        self.module = basic.AnsibleModule(netapp_utils.na_ontap_host_argument_spec())


def create_ontap_module(default_args=None):
    return create_module(MockONTAPModule, default_args).module


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_SF_SDK', 'dummy')
def test_has_sf_sdk():
    assert netapp_utils.has_sf_sdk() == 'dummy'


@patch('solidfire.factory.ElementFactory.create')
def test_create_sf_connection(mock_sf_create):
    module = create_ontap_module(DEFAULT_ARGS)
    mock_sf_create.return_value = 'dummy'
    assert netapp_utils.create_sf_connection(module) == 'dummy'


@patch('solidfire.factory.ElementFactory.create')
def test_negative_create_sf_connection_exception(mock_sf_create):
    module = create_ontap_module(DEFAULT_ARGS)
    mock_sf_create.side_effect = KeyError('dummy')
    assert str(expect_and_capture_ansible_exception(netapp_utils.create_sf_connection, Exception, module)) == "Unable to create SF connection: 'dummy'"


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_SF_SDK', False)
def test_negative_create_sf_connection_no_sdk():
    module = create_ontap_module(DEFAULT_ARGS)
    assert expect_and_capture_ansible_exception(netapp_utils.create_sf_connection, 'fail', module)['msg'] == 'the python SolidFire SDK module is required'


def test_negative_create_sf_connection_no_options():
    module = create_ontap_module(DEFAULT_ARGS)
    peer_options = {}
    assert expect_and_capture_ansible_exception(netapp_utils.create_sf_connection, 'fail', module, host_options=peer_options)['msg'] ==\
        'hostname, username, password are required for ElementSW connection.'


def test_negative_create_sf_connection_missing_and_extra_options():
    module = create_ontap_module(DEFAULT_ARGS)
    peer_options = {'hostname': 'host', 'username': 'user'}
    assert expect_and_capture_ansible_exception(netapp_utils.create_sf_connection, 'fail', module, host_options=peer_options)['msg'] ==\
        'password is required for ElementSW connection.'
    peer_options = {'hostname': 'host', 'username': 'user', 'cert_filepath': 'cert'}
    assert expect_and_capture_ansible_exception(netapp_utils.create_sf_connection, 'fail', module, host_options=peer_options)['msg'] ==\
        'password is required for ElementSW connection.  cert_filepath is not supported for ElementSW connection.'


def test_negative_create_sf_connection_extra_options():
    module = create_ontap_module(DEFAULT_ARGS)
    peer_options = {'hostname': 'host', 'username': 'user'}
    assert expect_and_capture_ansible_exception(netapp_utils.create_sf_connection, 'fail', module, host_options=peer_options)['msg'] ==\
        'password is required for ElementSW connection.'
    peer_options = {'hostname': 'host', 'username': 'user', 'password': 'pass', 'cert_filepath': 'cert', 'key_filepath': 'key'}
    assert expect_and_capture_ansible_exception(netapp_utils.create_sf_connection, 'fail', module, host_options=peer_options)['msg'] ==\
        'cert_filepath, key_filepath are not supported for ElementSW connection.'
