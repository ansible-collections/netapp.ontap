# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, call_main
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_ssh import main as my_main      # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

SRR = rest_responses({
    'ssh_security': (200, {
        "records": [
            {
                "ciphers": [
                    "aes256_ctr",
                    "aes192_ctr",
                    "aes128_ctr"
                ],
                "max_authentication_retry_count": 0,
                "svm": {
                    "name": "ansibleSVM",
                    "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
                },
                "mac_algorithms": ["hmac_sha1", "hmac_sha2_512_etm"],
                "key_exchange_algorithms": [
                    "diffie_hellman_group_exchange_sha256",
                    "diffie_hellman_group14_sha1"
                ],
            }],
        "num_records": 1
    }, None),
    'ssh_security_no_svm': (200, {
        "records": [
            {
                "ciphers": [
                    "aes256_ctr",

                ],
            }],
        "num_records": 1
    }, None),
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
}


def test_get_security_ssh_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ssh/svms', SRR['generic_error']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ssh', SRR['generic_error'])
    ])
    module_args = {"vserver": "AnsibleSVM"}
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = 'calling: security/ssh/svms: got Expected error.'
    assert msg in error
    error = call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


def test_modify_security_ssh_algorithms_rest():
    ''' test modify algorithms '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ssh/svms', SRR['ssh_security']),
        ('PATCH', 'security/ssh/svms/02c9e252-41be-11e9-81d5-00a0986138f7', SRR['empty_good']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ssh', SRR['ssh_security']),
        ('PATCH', 'security/ssh', SRR['empty_good']),
    ])
    module_args = {
        "vserver": "AnsibleSVM",
        "ciphers": ["aes256_ctr", "aes192_ctr"],
        "mac_algorithms": ["hmac_sha1", "hmac_sha2_512_etm"],
        "key_exchange_algorithms": ["diffie_hellman_group_exchange_sha256"],
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args.pop('vserver')
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_modify_security_ssh_retry_rest():
    ''' test modify maximum retry count '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ssh/svms', SRR['ssh_security']),
        ('PATCH', 'security/ssh/svms/02c9e252-41be-11e9-81d5-00a0986138f7', SRR['empty_good']),
    ])
    module_args = {
        "vserver": "AnsibleSVM",
        "max_authentication_retry_count": 2,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)


def test_error_modify_security_ssh_rest():
    ''' test modify algorithms '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ssh/svms', SRR['ssh_security']),
        ('PATCH', 'security/ssh/svms/02c9e252-41be-11e9-81d5-00a0986138f7', SRR['generic_error']),
    ])
    module_args = {
        "vserver": "AnsibleSVM",
        "ciphers": ["aes256_ctr", "aes192_ctr"],
        "max_authentication_retry_count": 2,
        "mac_algorithms": ["hmac_sha1", "hmac_sha2_512_etm"],
        "key_exchange_algorithms": ["diffie_hellman_group_exchange_sha256"],
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = 'calling: security/ssh/svms/02c9e252-41be-11e9-81d5-00a0986138f7: got Expected error.'
    assert msg in error


def test_error_empty_security_ssh_rest():
    ''' Validation of input parameters '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    module_args = {
        "ciphers": []
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = 'Removing all SSH ciphers is not supported. SSH login would fail. ' + \
          'There must be at least one ciphers associated with the SSH configuration.'
    assert msg in error


def test_module_error_ontap_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    module_args = {'use_rest': 'always'}
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Error: na_ontap_security_ssh only supports REST, and requires ONTAP 9.10.1 or later' in error


def test_module_error_no_svm_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/ssh/svms', SRR['ssh_security_no_svm']),
    ])
    module_args = {
        "vserver": "AnsibleSVM",
        "ciphers": ["aes256_ctr", "aes192_ctr"]
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Error: no uuid found for the SVM' in error
