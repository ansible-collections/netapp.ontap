# (c) 2019-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_rest_cli'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    call_main, create_module, expect_and_capture_ansible_exception, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_rest_cli import NetAppONTAPCommandREST as my_module, main as my_main   # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    'allow': (200, {'Allow': ['GET', 'WHATEVER']}, None)
}, False)


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'auto',
    'command': 'volume',
    'verb': 'GET',
    'params': {'fields': 'size,percent_used'}
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('verb')
    error = 'missing required arguments: verb'
    assert error in call_main(my_main, args, fail=True)['msg']


def test_rest_cli():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/volume', SRR['empty_good']),
    ])
    assert call_main(my_main, DEFAULT_ARGS)['changed']


def test_rest_cli_options():
    module_args = {'verb': 'OPTIONS'}
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('OPTIONS', 'private/cli/volume', SRR['allow']),
    ])
    exit_json = call_main(my_main, DEFAULT_ARGS, module_args)
    assert exit_json['changed']
    assert 'Allow' in exit_json['msg']


def test_negative_connection_error():
    module_args = {'verb': 'OPTIONS'}
    register_responses([
        ('GET', 'cluster', SRR['generic_error']),
    ])
    msg = "failed to connect to REST over hostname: ['Expected error'].  Use na_ontap_command for non-rest CLI."
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def check_verb(verb):
    module_args = {'verb': verb}
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        (verb, 'private/cli/volume', SRR['allow']),
    ], "test_verbs")

    exit_json = call_main(my_main, DEFAULT_ARGS, module_args)
    assert exit_json['changed']
    assert 'Allow' in exit_json['msg']
    # assert mock_request.call_args[0][0] == verb


def test_verbs():
    for verb in ['POST', 'DELETE', 'PATCH', 'OPTIONS', 'PATCH']:
        check_verb(verb)


def test_check_mode():
    module_args = {'verb': 'GET'}
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    my_obj.module.check_mode = True
    result = expect_and_capture_ansible_exception(my_obj.apply, 'exit')
    assert result['changed']
    msg = "Would run command: 'volume'"
    assert msg in result['msg']


def test_negative_verb():
    module_args = {'verb': 'GET'}
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    my_obj.verb = 'INVALID'
    msg = 'Error: unexpected verb INVALID'
    assert msg in expect_and_capture_ansible_exception(my_obj.apply, 'fail')['msg']


def test_negative_error():
    module_args = {'verb': 'GET'}
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/volume', SRR['generic_error']),
    ])
    msg = 'Error: Expected error'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
