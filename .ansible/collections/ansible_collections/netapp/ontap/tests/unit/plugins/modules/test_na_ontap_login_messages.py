# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_login_messages'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import call_main, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_error_message, zapi_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_login_messages import main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')
HAS_NETAPP_ZAPI_MSG = "pip install netapp_lib is required"


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'svm_uuid': (200, {"records": [{"uuid": "test_uuid"}], "num_records": 1}, None),
    'login_info': (200, {
        "records": [{
            "banner": "banner",
            "message": "message",
            "show_cluster_message": True,
            "uuid": "uuid_uuid"
        }],
        "num_records": 1}, None),
    'login_info_trailing_newline': (200, {
        "records": [{
            "banner": "banner\n",
            "message": "message\n",
            "show_cluster_message": True,
            "uuid": "uuid_uuid"
        }],
        "num_records": 1}, None),
})


banner_info = {
    'num-records': 1,
    'attributes-list': [{'vserver-login-banner-info': {
        'message': 'banner message',
    }}]}


banner_info_empty = {
    'num-records': 1,
    'attributes-list': [{'vserver-login-banner-info': {
        'message': '-',
        'vserver': 'vserver'
    }}]}


motd_info = {
    'num-records': 1,
    'attributes-list': [{'vserver-motd-info': {
        'is-cluster-message-enabled': 'true',
        'message': 'motd message',
        'vserver': 'vserver'
    }}]}


motd_info_empty = {
    'num-records': 1,
    'attributes-list': [{'vserver-motd-info': {
        'is-cluster-message-enabled': 'true',
        'vserver': 'vserver'
    }}]}


ZRR = zapi_responses({
    'banner_info': build_zapi_response(banner_info),
    'banner_info_empty': build_zapi_response(banner_info_empty),
    'motd_info': build_zapi_response(motd_info),
    'motd_info_empty': build_zapi_response(motd_info_empty),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never',
    }
    assert "Error: vserver is a required parameter when using ZAPI." == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_NETAPP_LIB', False)
def test_module_fail_when_netapp_lib_missing():
    ''' required lib missing '''
    module_args = {
        'use_rest': 'never',
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_successfully_create_banner():
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_info']),
        ('ZAPI', 'vserver-login-banner-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-login-banner-modify-iter', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'vserver',
        'banner': 'test banner',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_banner_idempotency():
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_info']),
        ('ZAPI', 'vserver-login-banner-get-iter', ZRR['banner_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'vserver',
        'banner': 'banner message',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_create_motd():
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_info_empty']),
        ('ZAPI', 'vserver-login-banner-get-iter', ZRR['banner_info_empty']),
        ('ZAPI', 'vserver-motd-modify-iter', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'vserver',
        'motd_message': 'test message',
        'show_cluster_motd': False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_motd_idempotency():
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_info']),
        ('ZAPI', 'vserver-login-banner-get-iter', ZRR['banner_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'vserver',
        'motd_message': 'motd message',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_motd_modify():
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_info']),
        ('ZAPI', 'vserver-login-banner-get-iter', ZRR['banner_info']),
        ('ZAPI', 'vserver-motd-modify-iter', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'vserver',
        'motd_message': 'motd message',
        'show_cluster_motd': False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_get_banner_error():
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_info']),
        ('ZAPI', 'vserver-login-banner-get-iter', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'vserver',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == zapi_error_message('Error fetching login_banner info')


def test_get_motd_error():
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'vserver',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == zapi_error_message('Error fetching motd info')


def test_modify_banner_error():
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-login-banner-get-iter', ZRR['banner_info']),
        ('ZAPI', 'vserver-login-banner-modify-iter', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'vserver',
        'banner': 'modify to new banner',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == zapi_error_message('Error modifying login_banner')


def test_modify_motd_error():
    register_responses([
        ('ZAPI', 'vserver-motd-get-iter', ZRR['motd_info']),
        ('ZAPI', 'vserver-login-banner-get-iter', ZRR['banner_info']),
        ('ZAPI', 'vserver-motd-modify-iter', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'vserver',
        'motd_message': 'modify to new motd',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == zapi_error_message('Error modifying motd')


def test_successfully_create_banner_rest():
    register_responses([
        # no vserver, cluster scope
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['login_info']),
        ('PATCH', 'security/login/messages/uuid_uuid', SRR['success']),
        # with vserver
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['zero_records']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('PATCH', 'security/login/messages/test_uuid', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        'banner': 'test banner',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['vserver'] = 'vserver'
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_modify_banner_rest():
    register_responses([
        # no vserver, cluster scope
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['login_info']),
        ('PATCH', 'security/login/messages/uuid_uuid', SRR['success']),
        # idempotent check
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['login_info_trailing_newline'])
    ])
    module_args = {
        'use_rest': 'always',
        'banner': 'banner\n',
        'message': 'message\n',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is False


def test_successfully_create_motd_rest():
    register_responses([
        # no vserver, cluster scope
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['login_info']),
        ('PATCH', 'security/login/messages/uuid_uuid', SRR['success']),
        # with vserver
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['login_info']),
        ('PATCH', 'security/login/messages/uuid_uuid', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        'motd_message': 'test motd',
        'show_cluster_motd': False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['vserver'] = 'vserver'
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_banner_error_rest():
    register_responses([
        # no vserver, cluster scope
        # error fetching info
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['generic_error']),
        # error no info at cluster level
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['zero_records']),
        # with vserver
        # error fetching SVM UUID
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['zero_records']),
        ('GET', 'svm/svms', SRR['generic_error']),
        # error, SVM not found
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['zero_records']),
        ('GET', 'svm/svms', SRR['zero_records']),
        # error, on patch
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'security/login/messages', SRR['login_info']),
        ('PATCH', 'security/login/messages/uuid_uuid', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
        'banner': 'test banner',
        # 'show_cluster_motd': False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == rest_error_message(
        'Error fetching login_banner info', 'security/login/messages')
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == 'Error fetching login_banner info for cluster - no data.'
    module_args['vserver'] = 'vserver'
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == rest_error_message('Error fetching vserver vserver', 'svm/svms')
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] ==\
        'Error fetching vserver vserver. Please make sure vserver name is correct. For cluster vserver, don\'t set vserver.'
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == rest_error_message(
        'Error modifying banner', 'security/login/messages/uuid_uuid')
