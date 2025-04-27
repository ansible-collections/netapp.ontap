# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_bgp_config """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_bgp_config \
    import NetAppOntapBgpConfiguration as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'state': 'present',
    'node': 'csahu-vsim1'
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    'bgp_config': (200, {
        'records': [{
            'node': 'csahu-vsim1',
            'asn': 65501,
            'hold_time': 180,
            'router_id': '10.193.73.189'
        }]
    }, None),
    'bgp_config_modified': (200, {
        'records': [{
            'node': 'csahu-vsim1',
            'asn': 65501,
            'hold_time': 200,
            'router_id': '10.193.73.189'
        }]
    }, None),
})


def test_get_bgp_config_none():
    ''' Test module no records '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/network/bgp/config', SRR['zero_records']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_bgp_config() is None


def test_get_bgp_config_error():
    ''' Test module GET method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/network/bgp/config', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching BGP configuration for csahu-vsim1: calling: private/cli/network/bgp/config: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.get_bgp_config, 'fail')['msg']


def test_get_bgp_config():
    ''' Test GET record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/network/bgp/config', SRR['bgp_config']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_bgp_config() is not None


def test_create_bgp_config():
    ''' Test creating BGP configuration with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/network/bgp/config', SRR['empty_records']),
        ('POST', 'private/cli/network/bgp/config', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/network/bgp/config', SRR['bgp_config'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_create_bgp_config_error():
    ''' Test module POST method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('POST', 'private/cli/network/bgp/config', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error creating BGP configuration for csahu-vsim1: calling: private/cli/network/bgp/config: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.create_bgp_config, 'fail')['msg']


def test_modify_bgp_config():
    ''' Test modifying BGP configuration with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/network/bgp/config', SRR['bgp_config']),
        ('PATCH', 'private/cli/network/bgp/config', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/network/bgp/config', SRR['bgp_config_modified'])
    ])
    module_args = {
        'hold_time': 200
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_bgp_config_error():
    ''' Test module PATCH method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('PATCH', 'private/cli/network/bgp/config', SRR['generic_error']),
    ])
    module_args = {
        'hold_time': 200
    }
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error modifying BGP configuration for csahu-vsim1: calling: '\
          'private/cli/network/bgp/config: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.modify_bgp_config, 'fail', module_args)['msg']


def test_delete_bgp_config():
    ''' Test deleting BGP configuration with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/network/bgp/config', SRR['bgp_config']),
        ('DELETE', 'private/cli/network/bgp/config', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'private/cli/network/bgp/config', SRR['empty_records'])
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_bgp_config_error():
    ''' Test module DELETE method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('DELETE', 'private/cli/network/bgp/config', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    msg = 'Error deleting BGP configuration for csahu-vsim1: calling: '\
          'private/cli/network/bgp/config: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.delete_bgp_config, 'fail')['msg']


def test_missing_options():
    ''' Test error missing required option node '''
    register_responses([])
    DEFAULT_ARGS.pop('node')
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'missing required arguments: node' in error


def test_earlier_version():
    ''' Test module supported from 9.6 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    module_args = {
        'node': 'csahu-vsim1'
    }
    assert 'requires ONTAP 9.6.0 or later' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
