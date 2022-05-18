# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_cifs_security \
    import NetAppONTAPCifsSecurity as cifs_security_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


cifs_security_info = {
    'num-records': 1,
    'attributes-list': {
        'cifs-security': {
            'is_aes_encryption_enabled': False,
            'lm_compatibility_level': 'krb',
            'kerberos_clock_skew': 20
        }
    }
}

ZRR = zapi_responses({
    'cifs_security_info': build_zapi_response(cifs_security_info)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'vserver',
    'use_rest': 'never',
    'is_aes_encryption_enabled': False,
    'lm_compatibility_level': 'krb',
    'kerberos_clock_skew': 20
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        cifs_security_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_get():
    register_responses([
        ('cifs-security-get-iter', ZRR['cifs_security_info'])
    ])
    cifs_obj = create_module(cifs_security_module, DEFAULT_ARGS)
    result = cifs_obj.cifs_security_get_iter()
    assert result


def test_modify_int_option():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-security-get-iter', ZRR['cifs_security_info']),
        ('cifs-security-modify', ZRR['success']),
    ])
    module_args = {
        'kerberos_clock_skew': 15
    }
    assert create_and_apply(cifs_security_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_bool_option():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-security-get-iter', ZRR['cifs_security_info']),
        ('cifs-security-modify', ZRR['success']),
    ])
    module_args = {
        'is_aes_encryption_enabled': True
    }
    assert create_and_apply(cifs_security_module, DEFAULT_ARGS, module_args)['changed']


def test_error_modify_bool_option():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-security-get-iter', ZRR['cifs_security_info']),
        ('cifs-security-modify', ZRR['error']),
    ])
    module_args = {
        'is_aes_encryption_enabled': True
    }
    error = create_and_apply(cifs_security_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'Error modifying cifs security' in error


def test_if_all_methods_catch_exception():
    register_responses([
        ('cifs-security-modify', ZRR['error'])
    ])
    module_args = {'use_rest': 'never', 'is_aes_encryption_enabled': True}
    current = {}
    my_obj = create_module(cifs_security_module, DEFAULT_ARGS, module_args)

    error = expect_and_capture_ansible_exception(my_obj.cifs_security_modify, 'fail', current)['msg']
    assert 'Error modifying cifs security on vserver: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error
