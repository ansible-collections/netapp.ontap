# (c) 2024, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_and_apply, create_module, expect_and_capture_ansible_exception, call_main
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_bgp_peer_group \
    import NetAppOntapBgpPeerGroup as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'bgpv4peer',
    'use_rest': 'always',
    'local': {
        'interface': {
            'name': 'lif1'
        }
    },
    'peer': {
        'address': '10.10.10.7',
        'asn': 0
    }
}


SRR = rest_responses({
    'bgp_peer_info': (200, {"records": [
        {
            "ipspace": {"name": "exchange"},
            "local": {
                "interface": {"ip": {"address": "10.10.10.7"}, "name": "lif1"},
                "port": {"name": "e1b", "node": {"name": "node1"}}
            },
            "name": "bgpv4peer",
            "peer": {"address": "10.10.10.7", "asn": 0, "is_next_hop": False},
            "state": "up",
            "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
        }], "num_records": 1}, None),
    'bgp_modified': (200, {"records": [
        {
            "ipspace": {"name": "exchange"},
            "local": {
                "interface": {"ip": {"address": "10.10.10.7"}, "name": "lif1"},
                "port": {"name": "e1b", "node": {"name": "node1"}}
            },
            "name": "bgpv4peer",
            "peer": {"address": "10.10.10.8", "asn": 0},
            "state": "up",
            "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
        }], "num_records": 1}, None),
    'bgp_name_modified': (200, {"records": [
        {
            "ipspace": {"name": "exchange"},
            "local": {
                "interface": {"ip": {"address": "10.10.10.7"}, "name": "lif1"},
                "port": {"name": "e1b", "node": {"name": "node1"}}
            },
            "name": "newbgpv4peer",
            "peer": {"address": "10.10.10.8", "asn": 0},
            "state": "up",
            "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
        }], "num_records": 1}, None),
    'bgp_peer_info_ipv6': (200, {"records": [
        {
            "ipspace": {"name": "exchange"},
            "name": "bgpv6peer",
            "peer": {"address": "2402:940::45", "asn": 0},
            "state": "up",
            "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
        }], "num_records": 1}, None),
    'bgp_modified_ipv6': (200, {"records": [
        {
            "ipspace": {"name": "exchange"},
            "name": "bgpv6peer",
            "peer": {"address": "2402:940::46", "asn": 0},
            "state": "up",
            "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
        }], "num_records": 1}, None),
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "name"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_create_bgp_peer_group():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['empty_records']),
        ('POST', 'network/ip/bgp/peer-groups', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['bgp_peer_info'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_modify_bgp_peer_group():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['bgp_peer_info']),
        ('PATCH', 'network/ip/bgp/peer-groups/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['bgp_modified']),
        # ipv6 modify
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['bgp_peer_info_ipv6']),
        ('PATCH', 'network/ip/bgp/peer-groups/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['bgp_modified_ipv6'])
    ])
    args = {'peer': {'address': '10.10.10.8'}}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    args = {'name': 'bgpv6peer', 'peer': {'address': '2402:0940:000:000:00:00:0000:0046'}}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_rename_modify_bgp_peer_group():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['bgp_peer_info']),
        ('PATCH', 'network/ip/bgp/peer-groups/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['bgp_name_modified'])
    ])
    args = {'from_name': 'bgpv4peer', 'name': 'newbgpv4peer', 'peer': {'address': '10.10.10.8'}}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_delete_bgp_peer_group():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['bgp_peer_info']),
        ('DELETE', 'network/ip/bgp/peer-groups/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['empty_records'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_all_methods_catch_exception():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # GET/POST/PATCH/DELETE error.
        ('GET', 'network/ip/bgp/peer-groups', SRR['generic_error']),
        ('POST', 'network/ip/bgp/peer-groups', SRR['generic_error']),
        ('PATCH', 'network/ip/bgp/peer-groups/1cd8a442', SRR['generic_error']),
        ('DELETE', 'network/ip/bgp/peer-groups/1cd8a442', SRR['generic_error'])
    ])
    bgp_obj = create_module(my_module, DEFAULT_ARGS)
    bgp_obj.uuid = '1cd8a442'
    assert 'Error fetching BGP peer' in expect_and_capture_ansible_exception(bgp_obj.get_bgp_peer_group, 'fail')['msg']
    assert 'Error creating BGP peer' in expect_and_capture_ansible_exception(bgp_obj.create_bgp_peer_group, 'fail')['msg']
    assert 'Error modifying BGP peer' in expect_and_capture_ansible_exception(bgp_obj.modify_bgp_peer_group, 'fail', {})['msg']
    assert 'Error deleting BGP peer' in expect_and_capture_ansible_exception(bgp_obj.delete_bgp_peer_group, 'fail')['msg']


def test_modify_rename_create_error():
    register_responses([
        # Error if both name and from_name not exist.
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['empty_records']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['empty_records']),
        # Error if try to modify asn.
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['bgp_peer_info']),
        # Error if peer and local not present in args when creating peer groups.
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['empty_records'])
    ])
    assert 'Error renaming BGP peer group' in create_and_apply(my_module, DEFAULT_ARGS, {'from_name': 'name'}, fail=True)['msg']
    args = {'peer': {'asn': 5}}
    assert 'Error: cannot modify peer asn.' in create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['peer']
    del DEFAULT_ARGS_COPY['local']
    assert 'Error creating BGP peer group' in create_and_apply(my_module, DEFAULT_ARGS_COPY, fail=True)['msg']


def test_successfully_modify_attributes_is_next_hop():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'network/ip/bgp/peer-groups', SRR['bgp_peer_info']),
        ('PATCH', 'network/ip/bgp/peer-groups/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success']),
    ])
    module_args = {
        'use_peer_as_next_hop': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_ontap96():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])
    ])
    assert 'requires ONTAP 9.7.0 or later' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


def test_version_error_with_is_next_hop():
    """ Test version error for 'use_peer_as_next_hop' """
    import traceback
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97'])
    ])
    module_args = {
        'use_peer_as_next_hop': True
    }
    error = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Minimum version of ONTAP for use_peer_as_next_hop is (9, 9, 1)' in error
