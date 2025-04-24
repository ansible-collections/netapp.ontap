# (c) 2021-2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
''' unit tests ONTAP Ansible module: na_ontap_security_config '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    call_main, create_module, create_and_apply, expect_and_capture_ansible_exception, AnsibleFailJson, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_config \
    import NetAppOntapSecurityConfig as security_config_module, main as my_main  # module under test


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'security_config_record': (200, {
        "records": [{
            "fips": {"enabled": False},
            "tls": {
                "protocol_versions": ['TLSv1.3', 'TLSv1.2', 'TLSv1.1'],
                "cipher_suites": ['TLS_RSA_WITH_AES_128_CCM_8']
            }
        }], "num_records": 1
    }, None),
    "no_record": (
        200,
        {"num_records": 0},
        None)
})


security_config_info = {
    'num-records': 1,
    'attributes': {
        'security-config-info': {
            "interface": 'ssl',
            "is-fips-enabled": False,
            "supported-protocols": ['TLSv1.2', 'TLSv1.1'],
            "supported-ciphers": 'ALL:!LOW:!aNULL:!EXP:!eNULL:!3DES:!DES:!RC4'
        }
    },
}


ZRR = zapi_responses({
    'security_config_info': build_zapi_response(security_config_info)
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'never',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        security_config_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_error_get_security_config_info():
    register_responses([
        ('ZAPI', 'security-config-get', ZRR['error'])
    ])
    module_args = {
        "name": 'ssl',
        "is_fips_enabled": False,
        "supported_protocols": ['TLSv1.2', 'TLSv1.1']
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error getting security config for interface"
    assert msg in error


def test_get_security_config_info():
    register_responses([
        ('security-config-get', ZRR['security_config_info'])
    ])
    security_obj = create_module(security_config_module, DEFAULT_ARGS)
    result = security_obj.get_security_config()
    assert result


def test_modify_security_config_fips():
    register_responses([
        ('ZAPI', 'security-config-get', ZRR['security_config_info']),
        ('ZAPI', 'security-config-modify', ZRR['success'])
    ])
    module_args = {
        "is_fips_enabled": True,
        "supported_protocols": ['TLSv1.3', 'TLSv1.2'],
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_modify_security_config_fips():
    register_responses([
        ('ZAPI', 'security-config-get', ZRR['security_config_info']),
        ('ZAPI', 'security-config-modify', ZRR['error'])
    ])
    module_args = {
        "is_fips_enabled": True,
        "supported_protocols": ['TLSv1.3', 'TLSv1.2'],
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert "Error modifying security config for interface" in error


def test_error_security_config():
    register_responses([
    ])
    module_args = {
        "is_fips_enabled": True,
        "supported_protocols": ['TLSv1.2', 'TLSv1.1', 'TLSv1'],
    }
    error = create_module(security_config_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'If fips is enabled then TLSv1 is not a supported protocol' in error


def test_error_security_config_supported_ciphers():
    register_responses([
    ])
    module_args = {
        "is_fips_enabled": True,
        "supported_ciphers": 'ALL:!LOW:!aNULL:!EXP:!eNULL:!3DES:!DES:!RC4',
    }
    error = create_module(security_config_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'If fips is enabled then supported ciphers should not be specified' in error


ARGS_REST = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always'
}


def test_rest_error_get():
    '''Test error rest get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/security', SRR['generic_error']),
    ])
    module_args = {
        "is_fips_enabled": False,
        "supported_protocols": ['TLSv1.2', 'TLSv1.1']
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    assert "Error on getting security config: calling: /security: got Expected error." in error


def test_rest_get_security_config():
    '''Test error rest get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/security', SRR['security_config_record']),
    ])
    module_args = {
        "is_fips_enabled": False,
        "supported_protocols": ['TLSv1.2', 'TLSv1.1']
    }
    security_obj = create_module(security_config_module, ARGS_REST, module_args)
    result = security_obj.get_security_config_rest()
    assert result


def test_rest_modify_security_config():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/security', SRR['security_config_record']),
        ('PATCH', '/security', SRR['success']),
        ('GET', '/security', SRR['security_config_record']),
    ])
    module_args = {
        "is_fips_enabled": False,
        "supported_protocols": ['TLSv1.3', 'TLSv1.2', 'TLSv1.1'],
        "supported_cipher_suites": ['TLS_RSA_WITH_AES_128_CCM']
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_rest_error_security_config():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    module_args = {
        "is_fips_enabled": True,
        "supported_protocols": ['TLSv1.2', 'TLSv1.1', 'TLSv1'],
        "supported_cipher_suites": 'TLS_RSA_WITH_AES_128_CCM'
    }
    error = create_module(security_config_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'If fips is enabled then TLSv1 is not a supported protocol' in error


def test_rest_error_security_config_protocol():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    module_args = {
        "is_fips_enabled": True,
        "supported_protocols": ['TLSv1.2', 'TLSv1.1'],
        "supported_cipher_suites": 'TLS_RSA_WITH_AES_128_CCM'
    }
    error = create_module(security_config_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'If fips is enabled then TLSv1.1 is not a supported protocol' in error


def test_rest_error_modify_security_config():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/security', SRR['security_config_record']),
        ('PATCH', '/security', SRR['generic_error']),
    ])
    module_args = {
        "is_fips_enabled": True,
        "supported_protocols": ['TLSv1.3', 'TLSv1.2'],
        "supported_cipher_suites": 'TLS_RSA_WITH_AES_128_CCM'
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    assert "Error on modifying security config: calling: /security: got Expected error." in error


def test_rest_modify_security_config_fips():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/security', SRR['security_config_record']),
        ('PATCH', '/security', SRR['success']),
        ('GET', '/security', SRR['security_config_record']),
    ])
    module_args = {
        "is_fips_enabled": True,
        "supported_protocols": ['TLSv1.3', 'TLSv1.2'],
        "supported_cipher_suites": ['TLS_RSA_WITH_AES_128_CCM']
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']
