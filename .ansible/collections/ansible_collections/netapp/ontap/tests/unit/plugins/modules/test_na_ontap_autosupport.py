# (c) 2018-2025, NetApp, Inc
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
    assert_warning_was_raised, call_main, create_module, patch_ansible, create_and_apply
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


DEFAULT_ARGS_REST = {
    'hostname': '10.10.10.10',
    'username': 'admin',
    'https': 'true',
    'validate_certs': 'false',
    'password': 'password',
    'use_rest': 'always',
}


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'one_asup_record': (200, {
        "records": [{
            'transport': 'https',
            'mail_hosts': ['10.20.30.40:25', '1.2.3.4:20'],
            'proxy_url': 'user:proxyhost@url',
            'to': ['rst@xyz.com'],
            'from': 'testmail@abc.com',
            'ondemand_enabled': True,
            'support': True,
            'enabled': True,
            'is_minimal': True,
            'smtp_encryption': 'none',
            'partner_addresses': ['test1@xyz.com', 'test@abc.com']
        }],
        'num_records': 1
    }, None),
    'one_asup_record_modified': (200, {
        "records": [{
            'transport': 'http',
            'mail_hosts': ['10.20.30.40:25'],
            'proxy_url': 'proxyhost.local.com',
            'to': ['rst@xyz.com', 'rst1@abc.com'],
            'from': 'testmail@xyz.com',
            'ondemand_enabled': False,
            'support': False,
            'enabled': True,
            'is_minimal': False,
            'smtp_encryption': 'start_tls',
            'partner_addresses': ['test1@xyz.com']
        }],
        'num_records': 1
    }, None),
    'one_asup_disabled_record': (200, {
        "records": [{
            'enabled': False
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


def test_rest_get_error():
    ''' get asup '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'support/autosupport', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    error = call_main(my_main, DEFAULT_ARGS_REST, module_args, fail=True)['msg']
    msg = 'Error fetching auto support configuration info:'
    assert msg in error


def test_rest_error_modify_auto_support_config():
    ''' modify asup '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'support/autosupport', SRR['one_asup_record']),
        ('PATCH', 'support/autosupport', SRR['generic_error']),
    ])
    module_args = {
        'transport': 'http',
        'mail_hosts': ['10.20.30.40:25'],
        'proxy_url': 'proxyhost.local.com',
        'to_addresses': ['rst@xyz.com', 'rst1@abc.com'],
        'from_address': 'testmail@xyz.com',
        'ondemand_enabled': False,
        'support': False,
        'state': 'absent',
        'is_minimal': False,
        'smtp_encryption': 'start_tls',
        'partner_addresses': ['test1@xyz.com']
    }
    error = create_and_apply(my_module, DEFAULT_ARGS_REST, module_args, fail=True)['msg']
    msg = "Error modifying auto support configuration:"
    assert msg in error


def test_rest_modify_auto_support_config():
    ''' modify asup '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'support/autosupport', SRR['one_asup_record']),
        ('PATCH', 'support/autosupport', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'support/autosupport', SRR['one_asup_record_modified']),
    ])
    module_args = {
        'transport': 'http',
        'mail_hosts': ['10.20.30.40:25'],
        'proxy_url': 'proxyhost.local.com',
        'to_addresses': ['rst@xyz.com', 'rst1@abc.com'],
        'from_address': "testmail@xyz.com",
        'ondemand_enabled': False,
        'support': False,
        'state': 'present',
        'force': True,
        'is_minimal': False,
        'smtp_encryption': 'start_tls',
        'partner_addresses': ['test1@xyz.com']
    }
    assert create_and_apply(my_module, DEFAULT_ARGS_REST, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS_REST, module_args)['changed']


def test_rest_disable_auto_support_config():
    ''' Disable asup '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'support/autosupport', SRR['one_asup_record']),
        ('PATCH', 'support/autosupport', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'support/autosupport', SRR['one_asup_disabled_record']),
    ])
    module_args = {
        'state': 'absent',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS_REST, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS_REST, module_args)['changed']
