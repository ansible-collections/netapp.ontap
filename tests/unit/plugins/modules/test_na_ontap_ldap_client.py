# (c) 2018-2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_ldap_client '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, call_main, create_module, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ldap_client \
    import NetAppOntapLDAPClient as client_module, main as my_main      # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'ldap_record': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "vserver"
                    },
                    "servers": ['10.193.115.116'],
                    "schema": 'RFC-2307',
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    }
                }
            ],
            "num_records": 1
        }, None
    ),
    "no_record": (
        200,
        {"num_records": 0},
        None),
    "svm": (
        200,
        {"records": [{"uuid": "671aa46e"}]},
        None)
})


ldap_client_info = {'num-records': 1,
                    'attributes-list':
                        {'ldap-client':
                            {'ldap-client-config': 'test_ldap',
                             'schema': 'RFC-2307',
                             'ldap-servers': [{"ldap-server": '10.193.115.116'}, ]
                             }
                         },
                    }

ZRR = zapi_responses({
    'ldap_client_info': build_zapi_response(ldap_client_info)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'vserver',
    'name': 'test_ldap',
    'schema': 'RFC-2307',
    'use_rest': 'never',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        client_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_get_nonexistent_client():
    ''' Test if get ldap client returns None for non-existent job '''
    register_responses([
        ('ldap-client-get-iter', ZRR['empty'])
    ])
    ldap_obj = create_module(client_module, DEFAULT_ARGS)
    result = ldap_obj.get_ldap_client()
    assert result is None


def test_error_name_required_zapi():
    ''' name is required with ZAPI '''
    error = 'Error: name is a required field with ZAPI.'
    assert error in create_module(client_module, DEFAULT_ARGS, {'name': None}, fail=True)['msg']


def test_get_existing_client():
    ''' Test if get ldap client returns None for non-existent job '''
    register_responses([
        ('ldap-client-get-iter', ZRR['ldap_client_info'])
    ])
    ldap_obj = create_module(client_module, DEFAULT_ARGS)
    result = ldap_obj.get_ldap_client()
    assert result


def test_successfully_create_zapi():
    register_responses([
        ('ldap-client-get-iter', ZRR['empty']),
        ('ldap-client-create', ZRR['success']),
    ])
    module_args = {
        'name': 'test_ldap',
        'ldap_servers': ['10.193.115.116'],
        'schema': 'RFC-2307'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_create_zapi():
    register_responses([
        ('ldap-client-get-iter', ZRR['empty']),
        ('ldap-client-create', ZRR['error']),
    ])
    module_args = {
        'name': 'test_ldap',
        'ldap_servers': ['10.193.115.116'],
        'schema': 'RFC-2307'
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error creating LDAP client"
    assert msg in error


def test_error_create_ad_zapi():
    register_responses([
        ('ldap-client-get-iter', ZRR['empty']),
        ('ldap-client-create', ZRR['error']),
    ])
    module_args = {
        'name': 'test_ldap',
        'ad_domain': 'ad.netapp.com',
        'preferred_ad_servers': ['10.193.115.116'],
        'schema': 'RFC-2307'
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error creating LDAP client"
    assert msg in error


def test_create_idempotency():
    register_responses([
        ('ldap-client-get-iter', ZRR['ldap_client_info']),
    ])
    module_args = {
        'name': 'test_ldap',
        'servers': ['10.193.115.116'],
        'schema': 'RFC-2307',
        'state': 'present'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_delete():
    register_responses([
        ('ldap-client-get-iter', ZRR['ldap_client_info']),
        ('ldap-client-delete', ZRR['success']),
    ])
    module_args = {
        'name': 'test_ldap',
        'ldap_servers': ['10.193.115.116'],
        'schema': 'RFC-2307',
        'state': 'absent'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_delete_zapi():
    register_responses([
        ('ldap-client-get-iter', ZRR['ldap_client_info']),
        ('ldap-client-delete', ZRR['error']),
    ])
    module_args = {
        'name': 'test_ldap',
        'ldap_servers': ['10.193.115.116'],
        'schema': 'RFC-2307',
        'state': 'absent'
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error deleting LDAP client configuration"
    assert msg in error


def test_delete_idempotency():
    register_responses([
        ('ldap-client-get-iter', ZRR['empty']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_modify_ldap_servers():
    register_responses([
        ('ldap-client-get-iter', ZRR['ldap_client_info']),
        ('ldap-client-modify', ZRR['success']),
    ])
    module_args = {
        'name': 'test_ldap',
        'ldap_servers': ['10.195.64.121'],
        'schema': 'RFC-2307',
        'ldaps_enabled': True,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_modify_ldap_ad_servers():
    register_responses([
        ('ldap-client-get-iter', ZRR['ldap_client_info']),
        ('ldap-client-modify', ZRR['success']),
    ])
    module_args = {
        'name': 'test_ldap',
        'ad_domain': 'ad.netapp.com',
        'preferred_ad_servers': ['10.195.64.121'],
        'schema': 'RFC-2307',
        'ldaps_enabled': True,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_modify_ldap_schema_zapi():
    register_responses([
        ('ldap-client-get-iter', ZRR['ldap_client_info']),
        ('ldap-client-modify', ZRR['success']),
    ])
    module_args = {
        'name': 'test_ldap',
        'ldap_servers': ['10.195.64.121'],
        'schema': 'MS-AD-BIS',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('ldap-client-create', ZRR['error']),
        ('ldap-client-delete', ZRR['error']),
        ('ldap-client-modify', ZRR['error'])
    ])
    module_args = {'name': 'test_ldap'}
    my_obj = create_module(client_module, DEFAULT_ARGS, module_args)

    error = expect_and_capture_ansible_exception(my_obj.create_ldap_client, 'fail')['msg']
    assert 'Error creating LDAP client test_ldap: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.delete_ldap_client, 'fail')['msg']
    assert 'Error deleting LDAP client configuration test_ldap: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.modify_ldap_client, 'fail', 'ldap-client-modify')['msg']
    assert 'Error modifying LDAP client test_ldap: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error


ARGS_REST = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
    'vserver': 'vserver',
    'servers': ['10.193.115.116'],
    'schema': 'RFC-2307',
}


def test_get_nonexistent_ldap_config_rest():
    ''' Test if get_unix_user returns None for non-existent user '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['empty_records']),
    ])
    ldap_obj = create_module(client_module, ARGS_REST)
    result = ldap_obj.get_ldap_client_rest()
    assert result is None


def test_get_existent_ldap_config_rest():
    ''' Test if get_unix_user returns existent user '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['ldap_record']),
    ])
    ldap_obj = create_module(client_module, ARGS_REST)
    result = ldap_obj.get_ldap_client_rest()
    assert result


def test_get_error_ldap_config_rest():
    ''' Test if get_unix_user returns existent user '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['generic_error']),
    ])
    error = call_main(my_main, ARGS_REST, fail=True)['msg']
    msg = "Error on getting idap client info:"
    assert msg in error


def test_create_ldap_client_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['empty_records']),
        ('GET', 'svm/svms', SRR['svm']),
        ('POST', 'name-services/ldap', SRR['empty_good']),
    ])
    module_args = {
        'ldap_servers': ['10.193.115.116'],
        'schema': 'RFC-2307'
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_create_ldap_client_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['empty_records']),
        ('GET', 'svm/svms', SRR['svm']),
        ('POST', 'name-services/ldap', SRR['generic_error']),
    ])
    module_args = {
        'servers': ['10.193.115.116'],
        'schema': 'RFC-2307'
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on creating ldap client:"
    assert msg in error


def test_delete_ldap_client_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['ldap_record']),
        ('DELETE', 'name-services/ldap/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        'servers': ['10.193.115.116'],
        'schema': 'RFC-2307',
        'state': 'absent'
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_delete_ldap_client_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['ldap_record']),
        ('DELETE', 'name-services/ldap/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['generic_error']),
    ])
    module_args = {
        'servers': ['10.193.115.116'],
        'schema': 'RFC-2307',
        'state': 'absent'
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on deleting ldap client rest:"
    assert msg in error


def test_create_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['ldap_record']),
    ])
    module_args = {
        'state': 'present',
        'servers': ['10.193.115.116'],
        'schema': 'RFC-2307',
    }
    assert not call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_on_cluster_vserver():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['empty_records']),
        ('GET', 'svm/svms', SRR['empty_records']),
    ])
    module_args = {
        'state': 'present',
        'servers': ['10.193.115.116'],
        'schema': 'RFC-2307',
    }
    assert 'is not a data vserver.' in call_main(my_main, ARGS_REST, module_args, fail=True)['msg']


def test_delete_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['empty_records'])
    ])
    module_args = {
        'state': 'absent'
    }
    assert not call_main(my_main, ARGS_REST, module_args)['changed']


def test_modify_schema_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['ldap_record']),
        ('PATCH', 'name-services/ldap/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good'])
    ])
    module_args = {
        'state': 'present',
        'servers': ['10.193.115.116'],
        'schema': 'AD-IDMU',
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_modify_ldap_servers_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['ldap_record']),
        ('PATCH', 'name-services/ldap/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good'])
    ])
    module_args = {
        'state': 'present',
        'servers': ['10.195.64.121'],
        'schema': 'AD-IDMU',
        'ldaps_enabled': True,
        'skip_config_validation': True
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_negative_modify_ldap_servers_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['ldap_record']),
        ('PATCH', 'name-services/ldap/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['generic_error'])
    ])
    module_args = {
        'state': 'present',
        'servers': ['10.195.64.121'],
        'schema': 'AD-IDMU',
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on modifying ldap client config:"
    assert msg in error


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_NETAPP_LIB', False)
def test_module_fail_when_netapp_lib_missing():
    ''' required lib missing '''
    module_args = {
        'use_rest': 'never',
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_error_no_server():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/ldap', SRR['ldap_record']),
    ])
    args = dict(ARGS_REST)
    args.pop('servers')
    error = 'Required one of servers or ad_domain'
    assert error in call_main(my_main, args, fail=True)['msg']
