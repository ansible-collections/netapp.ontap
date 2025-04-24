# Copyright: NetApp, Inc
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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_kerberos_interface \
    import NetAppOntapKerberosInterface as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'enabled': False,
    'interface_name': 'lif1',
    'vserver': 'ansibleSVM'
}


SRR = rest_responses({
    'kerberos_int_conf_enabled': (200, {"records": [{
        "spn": "nfs/life2@RELAM2",
        "machine_account": "account1",
        "interface": {
            "ip": {"address": "10.10.10.7"},
            "name": "lif1",
            "uuid": "1cd8a442"
        },
        "enabled": True,
    }], "num_records": 1}, None),
    'kerberos_int_conf_disabled': (200, {"records": [{
        "interface": {
            "ip": {"address": "10.10.10.7"},
            "name": "lif1",
            "uuid": "1cd8a442"
        },
        "enabled": False,
    }], "num_records": 1}, None),
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_enable_kerberos_int_conf():
    ''' enable kerberos int conf '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
        ('GET', 'protocols/nfs/kerberos/interfaces', SRR['kerberos_int_conf_disabled']),
        ('PATCH', 'protocols/nfs/kerberos/interfaces/1cd8a442', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
        ('GET', 'protocols/nfs/kerberos/interfaces', SRR['kerberos_int_conf_enabled'])
    ])
    args = {
        "spn": "nfs/life2@RELAM2",
        "machine_account": "account1",
        "admin_username": "user1",
        "admin_password": "pass1",
        "enabled": True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_all_methods_catch_exception():
    ''' test exception in get/create/modify/delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # GET/PATCH error.
        ('GET', 'protocols/nfs/kerberos/interfaces', SRR['generic_error']),
        ('PATCH', 'protocols/nfs/kerberos/interfaces/1cd8a442', SRR['generic_error'])
    ])
    ker_obj = create_module(my_module, DEFAULT_ARGS)
    ker_obj.uuid = '1cd8a442'
    assert 'Error fetching kerberos interface' in expect_and_capture_ansible_exception(ker_obj.get_kerberos_interface, 'fail')['msg']
    assert 'Error modifying kerberos interface' in expect_and_capture_ansible_exception(ker_obj.modify_kerberos_interface, 'fail')['msg']


def test_error_ontap97():
    ''' test module supported from 9.7 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])
    ])
    assert 'requires ONTAP 9.7.0 or later' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']
