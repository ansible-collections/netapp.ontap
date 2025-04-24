# Copyright (c) 2022 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils netapp_ipaddress.py - REST features '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import expect_and_capture_ansible_exception, patch_ansible, create_module
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils import netapp_ipaddress

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


class MockONTAPModule(object):
    def __init__(self):
        self.module = basic.AnsibleModule(netapp_utils.na_ontap_host_argument_spec())


def create_ontap_module(args=None):
    if args is None:
        args = {'hostname': 'xxx'}
    return create_module(MockONTAPModule, args)


def test_check_ipaddress_is_present():
    assert netapp_ipaddress._check_ipaddress_is_present(None) is None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp_ipaddress.HAS_IPADDRESS_LIB', False)
def test_module_fail_when_netapp_lib_missing():
    ''' required lib missing '''
    error = 'Error: the python ipaddress package is required for this module.  Import error: None'
    assert error in expect_and_capture_ansible_exception(netapp_ipaddress._check_ipaddress_is_present, 'fail', create_ontap_module().module)['msg']


def test_validate_and_compress_ip_address():
    module = create_ontap_module().module
    valid_addresses = [
        # IPv4
        ['10.11.12.13', '10.11.12.13'],
        # IPv6
        ['1111:0123:0012:0001:abcd:0abc:9891:abcd', '1111:123:12:1:abcd:abc:9891:abcd'],
        ['1111:0000:0000:0000:abcd:0abc:9891:abcd', '1111::abcd:abc:9891:abcd'],
        ['1111:0000:0000:0012:abcd:0000:0000:abcd', '1111::12:abcd:0:0:abcd'],
        ['ffff:ffff:0000:0000:0000:0000:0000:0000', 'ffff:ffff::'],
    ]
    for before, after in valid_addresses:
        assert after == netapp_ipaddress.validate_and_compress_ip_address(before, module)


def test_negative_validate_and_compress_ip_address():
    module = create_ontap_module().module
    invalid_addresses = [
        # IPv4
        ['10.11.12.345', 'Invalid IP address value 10.11.12.345'],
        # IPv6
        ['1111:0123:0012:0001:abcd:0abc:9891:abcg', 'Invalid IP address value'],
        ['1111:0000:0000:0000:abcd:9891:abcd', 'Invalid IP address value'],
        ['1111:::0012:abcd::abcd', 'Invalid IP address value'],
    ]
    for before, error in invalid_addresses:
        assert error in expect_and_capture_ansible_exception(netapp_ipaddress.validate_and_compress_ip_address, 'fail', before, module)['msg']


def test_netmask_to_len():
    module = create_ontap_module().module
    assert netapp_ipaddress.netmask_to_netmask_length('10.10.10.10', '255.255.0.0', module) == 16
    assert netapp_ipaddress.netmask_to_netmask_length('1111::', 16, module) == 16
    assert netapp_ipaddress.netmask_to_netmask_length('1111::', '16', module) == 16
    error = 'Error: only prefix_len is supported for IPv6 addresses, got ffff::'
    assert error in expect_and_capture_ansible_exception(netapp_ipaddress.netmask_to_netmask_length, 'fail', '1111::', 'ffff::', module)['msg']
    error = 'Error: Invalid IP network value 10.11.12.13/abc.'
    assert error in expect_and_capture_ansible_exception(netapp_ipaddress.netmask_to_netmask_length, 'fail', '10.11.12.13', 'abc', module)['msg']


def test_len_to_netmask():
    module = create_ontap_module().module
    assert netapp_ipaddress.netmask_length_to_netmask('10.10.10.10', 16, module) == '255.255.0.0'
    assert netapp_ipaddress.netmask_length_to_netmask('1111::', 16, module) == 'ffff::'


def test_validate_ip_address_is_network_address():
    module = create_ontap_module().module
    assert netapp_ipaddress.validate_ip_address_is_network_address('10.11.12.0', module) is None
    assert netapp_ipaddress.validate_ip_address_is_network_address('10.11.12.0/24', module) is None
    error = 'Error: Invalid IP network value 10.11.12.0/21'
    assert error in expect_and_capture_ansible_exception(netapp_ipaddress.validate_ip_address_is_network_address, 'fail', '10.11.12.0/21', module)['msg']
