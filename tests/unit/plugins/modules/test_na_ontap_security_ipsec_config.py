# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_and_apply, create_module, expect_and_capture_ansible_exception, call_main, assert_warning_was_raised, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_ipsec_config \
    import NetAppOntapSecurityIPsecConfig as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always'
}


SRR = rest_responses({
    'ipsec_config': (200, {"records": [{"enabled": True, "replay_window": "64"}]}, None),
    'ipsec_config_1': (200, {"records": [{"enabled": False, "replay_window": "0"}]}, None)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_modify_security_ipsec_config():
    ''' create ipsec policy with certificates '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec', SRR['ipsec_config_1']),
        ('PATCH', 'security/ipsec', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec', SRR['ipsec_config']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/ipsec', SRR['empty_records']),
    ])
    args = {
        "enabled": True,
        "replay_window": 64
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_all_methods_catch_exception():
    ''' test exception in get/create/modify/delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # GET/PATCH error.
        ('GET', 'security/ipsec', SRR['generic_error']),
        ('PATCH', 'security/ipsec', SRR['generic_error'])
    ])
    sec_obj = create_module(my_module, DEFAULT_ARGS)
    assert 'Error fetching security IPsec config' in expect_and_capture_ansible_exception(sec_obj.get_security_ipsec_config, 'fail')['msg']
    assert 'Error modifying security IPsec config' in expect_and_capture_ansible_exception(sec_obj.modify_security_ipsec_config, 'fail', {})['msg']


def test_error_ontap97():
    ''' test module supported from 9.8 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97'])
    ])
    assert 'requires ONTAP 9.8.0 or later' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']
