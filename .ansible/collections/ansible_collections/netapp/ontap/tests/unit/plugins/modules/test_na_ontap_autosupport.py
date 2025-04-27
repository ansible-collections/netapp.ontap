# (c) 2018-2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP autosupport Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_warning_was_raised, call_main, create_module, patch_ansible, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_error_message, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_autosupport \
    import NetAppONTAPasup as my_module, main as my_main    # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'state': 'present',
    'hostname': '10.10.10.10',
    'username': 'admin',
    'https': 'true',
    'validate_certs': 'false',
    'password': 'password',
    'node_name': 'node1',
    'retry_count': '16',
    'transport': 'http',
    'ondemand_enabled': 'true'

}


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'one_asup_record': (200, {
        "records": [{
            'node': 'node1',
            'state': True,
            'from': 'Postmaster',
            'support': True,
            'transport': 'http',
            'url': 'support.netapp.com/asupprod/post/1.0/postAsup',
            'proxy_url': 'username1:********@host.com:8080',
            'hostname_subj': True,
            'nht': False,
            'perf': True,
            'retry_count': 16,
            'reminder': True,
            'max_http_size': 10485760,
            'max_smtp_size': 5242880,
            'remove_private_data': False,
            'local_collection': True,
            'ondemand_state': True,
            'ondemand_server_url': 'https://support.netapp.com/aods/asupmessage',
            'partner_address': ['test@example.com']
        }],
        'num_records': 1
    }, None)
})

autosupport_info = {
    'attributes': {
        'autosupport-config-info': {
            'is-enabled': 'true',
            'node-name': 'node1',
            'transport': 'http',
            'post-url': 'support.netapp.com/asupprod/post/1.0/postAsup',
            'from': 'Postmaster',
            'proxy-url': 'username1:********@host.com:8080',
            'retry-count': '16',
            'max-http-size': '10485760',
            'max-smtp-size': '5242880',
            'is-support-enabled': 'true',
            'is-node-in-subject': 'true',
            'is-nht-data-enabled': 'false',
            'is-perf-data-enabled': 'true',
            'is-reminder-enabled': 'true',
            'is-private-data-removed': 'false',
            'is-local-collection-enabled': 'true',
            'is-ondemand-enabled': 'true',
            'validate-digital-certificate': 'true',

        }
    }
}

ZRR = zapi_responses({
    'autosupport_info': build_zapi_response(autosupport_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    assert 'missing required arguments:' in call_main(my_main, {}, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_NETAPP_LIB', False)
def test_module_fail_when_netapp_lib_missing():
    ''' required lib missing '''
    module_args = {
        'use_rest': 'never',
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_ensure_get_called():
    register_responses([
        ('ZAPI', 'autosupport-config-get', ZRR['autosupport_info']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_autosupport_config() is not None


def test_successful_modify():
    ''' modifying asup and testing idempotency '''
    register_responses([
        ('ZAPI', 'autosupport-config-get', ZRR['autosupport_info']),
        ('ZAPI', 'autosupport-config-modify', ZRR['success']),
        # idempotency
        ('ZAPI', 'autosupport-config-get', ZRR['autosupport_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'ondemand_enabled': False,
        'partner_addresses': [],
        'post_url': 'some_url',
        'from_address': 'from_add',
        'to_addresses': 'to_add',
        'hostname_in_subject': False,
        'nht_data_enabled': True,
        'perf_data_enabled': False,
        'reminder_enabled': False,
        'private_data_removed': True,
        'local_collection_enabled': False,
        'retry_count': 3,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # idempotency
    module_args = {
        'use_rest': 'never',
        'ondemand_enabled': True,
        'partner_addresses': [],
        'post_url': 'support.netapp.com/asupprod/post/1.0/postAsup',
        'from_address': 'Postmaster',
        'hostname_in_subject': True,
        'nht_data_enabled': False,
        'perf_data_enabled': True,
        'reminder_enabled': True,
        'private_data_removed': False,
        'local_collection_enabled': True,
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('ZAPI', 'autosupport-config-get', ZRR['error']),
        # idempotency
        ('ZAPI', 'autosupport-config-get', ZRR['autosupport_info']),
        ('ZAPI', 'autosupport-config-modify', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
        'ondemand_enabled': False,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == zapi_error_message('Error fetching info')
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == zapi_error_message('Error modifying asup')


def test_rest_modify_no_action():
    ''' modify asup '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/system/node/autosupport', SRR['one_asup_record']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_modify_prepopulate():
    ''' modify asup '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/system/node/autosupport', SRR['one_asup_record']),
        ('PATCH', 'private/cli/system/node/autosupport', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        'ondemand_enabled': False,
        'partner_addresses': [],
        'post_url': 'some_url',
        'from_address': 'from_add',
        'to_addresses': 'to_add',
        'hostname_in_subject': False,
        'nht_data_enabled': True,
        'perf_data_enabled': False,
        'reminder_enabled': False,
        'private_data_removed': True,
        'local_collection_enabled': False,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_modify_pasword():
    ''' modify asup '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/system/node/autosupport', SRR['one_asup_record']),
        ('PATCH', 'private/cli/system/node/autosupport', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        # different password, but no action
        'proxy_url': 'username1:password2@host.com:8080'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised('na_ontap_autosupport is not idempotent because the password value in proxy_url cannot be compared.')


def test_rest_get_error():
    ''' modify asup '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/system/node/autosupport', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == rest_error_message('Error fetching info', 'private/cli/system/node/autosupport')


def test_rest_modify_error():
    ''' modify asup '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/system/node/autosupport', SRR['one_asup_record']),
        ('PATCH', 'private/cli/system/node/autosupport', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
        'ondemand_enabled': False,
        'partner_addresses': []
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == rest_error_message('Error modifying asup', 'private/cli/system/node/autosupport')
