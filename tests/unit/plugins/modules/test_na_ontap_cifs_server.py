# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_cifs_server '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_server \
    import NetAppOntapcifsServer as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'cifs_record': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansibleSVM"
                    },
                    "enabled": True,
                    "security": {
                        "encrypt_dc_connection": False,
                        "smb_encryption": False,
                        "kdc_encryption": False,
                        "smb_signing": False,
                        "restrict_anonymous": "no_enumeration",
                        "aes_netlogon_enabled": False,
                        "ldap_referral_enabled": False,
                        "session_security": "none",
                        "try_ldap_channel_binding": True,
                        "use_ldaps": False,
                        "use_start_tls": False
                    },
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    },
                    "name": "cifs_server_name"
                }
            ],
            "num_records": 1
        }, None
    ),
    'cifs_record_disabled': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansibleSVM"
                    },
                    "enabled": False,
                    "security": {
                        "encrypt_dc_connection": False,
                        "smb_encryption": False,
                        "kdc_encryption": False,
                        "smb_signing": False,
                        "restrict_anonymous": "no_enumeration",
                        "aes_netlogon_enabled": False,
                        "ldap_referral_enabled": False,
                        "session_security": "none",
                        "try_ldap_channel_binding": True,
                        "use_ldaps": False,
                        "use_start_tls": False
                    },
                    "target": {
                        "nam,e": "20:05:00:50:56:b3:0c:fa"
                    },
                    "name": "cifs_server_name"
                }
            ],
            "num_records": 1
        }, None
    ),
    'cifs_records_renamed': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansibleSVM"
                    },
                    "enabled": True,
                    "security": {
                        "encrypt_dc_connection": False,
                        "smb_encryption": False,
                        "kdc_encryption": False,
                        "smb_signing": False,
                        "restrict_anonymous": "no_enumeration",
                        "aes_netlogon_enabled": False,
                        "ldap_referral_enabled": False,
                        "session_security": "none",
                        "try_ldap_channel_binding": True,
                        "use_ldaps": False,
                        "use_start_tls": False
                    },
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    },
                    "name": "cifs"
                }
            ],
            "num_records": 1
        }, None
    ),
    "no_record": (
        200,
        {"num_records": 0},
        None)
})


cifs_record_info = {
    'num-records': 1,
    'attributes-list': {
        'cifs-server-config': {
            'cifs-server': 'cifs_server',
            'administrative-status': 'up'}
    }
}
cifs_record_disabled_info = {
    'num-records': 1,
    'attributes-list': {
        'cifs-server-config': {
            'cifs-server': 'cifs_server',
            'administrative-status': 'down'}
    }
}

ZRR = zapi_responses({
    'cifs_record_info': build_zapi_response(cifs_record_info),
    'cifs_record_disabled_info': build_zapi_response(cifs_record_disabled_info)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'cifs_server_name': 'cifs_server',
    'vserver': 'vserver',
    'use_rest': 'never',
    'feature_flags': {'no_cserver_ems': True}
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_get():
    register_responses([
        ('cifs-server-get-iter', ZRR['cifs_record_info'])
    ])
    cifs_obj = create_module(my_module, DEFAULT_ARGS)
    result = cifs_obj.get_cifs_server()
    assert result


def test_error_create():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-server-get-iter', ZRR['empty']),
        ('cifs-server-create', ZRR['error']),
    ])
    module_args = {
        'state': 'present'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'Error Creating cifs_server' in error


def test_create_unsupport_zapi():
    """ check for zapi unsupported options """
    module_args = {
        "use_rest": "never",
        "encrypt_dc_connection": "false",
        "smb_encryption": "false",
        "kdc_encryption": "false",
        "smb_signing": "false"
    }
    msg = 'Error: smb_signing ,encrypt_dc_connection ,kdc_encryption ,smb_encryption ,restrict_anonymous ,' + \
          'aes_netlogon_enabled ,ldap_referral_enabled ,try_ldap_channel_binding ,session_security ,use_ldaps ,use_start_tls options supported only with REST.'
    assert msg == create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_create():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-server-get-iter', ZRR['empty']),
        ('cifs-server-create', ZRR['success']),
    ])
    module_args = {
        'workgroup': 'test',
        'ou': 'ou',
        'domain': 'test',
        'admin_user_name': 'user1',
        'admin_password': 'password'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_with_force():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-server-get-iter', ZRR['empty']),
        ('cifs-server-create', ZRR['success']),
    ])
    module_args = {
        'workgroup': 'test',
        'ou': 'ou',
        'domain': 'test',
        'admin_user_name': 'user1',
        'admin_password': 'password',
        'force': 'true'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_idempotent():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-server-get-iter', ZRR['cifs_record_info'])
    ])
    module_args = {
        'state': 'present'
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_idempotent():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-server-get-iter', ZRR['empty'])
    ])
    module_args = {
        'state': 'absent'
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-server-get-iter', ZRR['cifs_record_info']),
        ('cifs-server-delete', ZRR['success']),
    ])
    module_args = {
        'workgroup': 'test',
        'ou': 'ou',
        'domain': 'test',
        'admin_user_name': 'user1',
        'admin_password': 'password',
        'force': 'false',
        'state': 'absent'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_delete():
    register_responses([
        ('cifs-server-delete', ZRR['error']),
    ])
    module_args = {
        'workgroup': 'test',
        'ou': 'ou',
        'domain': 'test',
        'force': 'false',
        'state': 'absent'
    }
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = "Error deleting cifs_server"
    assert msg in expect_and_capture_ansible_exception(my_module_object.delete_cifs_server, 'fail')['msg']


def test_start_service_state():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-server-get-iter', ZRR['cifs_record_info']),
        ('cifs-server-stop', ZRR['success']),
    ])
    module_args = {
        'service_state': 'stopped'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)


def test_stop_service_state():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-server-get-iter', ZRR['cifs_record_disabled_info']),
        ('cifs-server-start', ZRR['success']),
    ])
    module_args = {
        'service_state': 'started'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)


def test_if_all_methods_catch_exception():
    register_responses([
        ('cifs-server-create', ZRR['error']),
        ('cifs-server-start', ZRR['error']),
        ('cifs-server-stop', ZRR['error']),
        ('cifs-server-delete', ZRR['error'])
    ])
    module_args = {}

    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    error = expect_and_capture_ansible_exception(my_obj.create_cifs_server, 'fail')['msg']
    assert 'Error Creating cifs_server cifs_server: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.start_cifs_server, 'fail')['msg']
    assert 'Error modifying cifs_server cifs_server: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.stop_cifs_server, 'fail')['msg']
    assert 'Error modifying cifs_server cifs_server: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.delete_cifs_server, 'fail')['msg']
    assert 'Error deleting cifs_server cifs_server: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error


ARGS_REST = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
    'vserver': 'test_vserver',
    'name': 'cifs_server_name',
}


def test_rest_error_get():
    '''Test error rest get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on fetching cifs:' in error


def test_module_error_ontap_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    module_args = {'use_rest': 'always', 'force': True}
    error = create_module(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Minimum version of ONTAP for force is (9, 11)' in error


def test_rest_successful_create():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('POST', 'protocols/cifs/services', SRR['empty_good']),
    ])
    assert create_and_apply(my_module, ARGS_REST)


def test_rest_successful_create_with_force():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('POST', 'protocols/cifs/services', SRR['empty_good']),
    ])
    module_args = {
        'force': True
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_successful_create_with_user():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('POST', 'protocols/cifs/services', SRR['empty_good']),
    ])
    module_args = {
        'admin_user_name': 'test_user',
        'admin_password': 'pwd'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_successful_create_with_ou():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('POST', 'protocols/cifs/services', SRR['empty_good']),
    ])
    module_args = {
        'ou': 'ou'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_successful_create_with_domain():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('POST', 'protocols/cifs/services', SRR['empty_good']),
    ])
    module_args = {
        'domain': 'domain'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_successful_create_with_security():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('POST', 'protocols/cifs/services', SRR['empty_good']),
    ])
    module_args = {
        'smb_encryption': True,
        'smb_signing': True,
        'kdc_encryption': True,
        'encrypt_dc_connection': True,
        'restrict_anonymous': 'no_enumeration'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_version_error_with_security_encryption():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])
    ])
    module_args = {
        'use_rest': 'always',
        'encrypt_dc_connection': True,
    }
    error = create_module(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Minimum version of ONTAP for encrypt_dc_connection is (9, 8)' in error


def test_module_error_ontap_version_security():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0'])
    ])
    module_args = {
        "aes_netlogon_enabled": False
    }
    error = create_module(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Minimum version of ONTAP for aes_netlogon_enabled is (9, 10, 1)' in error


def test_rest_error_create():
    '''Test error rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('POST', 'protocols/cifs/services', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on creating cifs:' in error


def test_delete_rest():
    ''' Test delete with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record']),
        ('DELETE', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        'state': 'absent',
        'admin_user_name': 'test_user',
        'admin_password': 'pwd'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_delete_with_force_rest():
    ''' Test delete with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record']),
        ('DELETE', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        'state': 'absent',
        'force': True,
        'admin_user_name': 'test_user',
        'admin_password': 'pwd'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_error_delete_rest():
    ''' Test error delete with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record']),
        ('DELETE', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent'
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on deleting cifs server:' in error


def test_rest_successful_disable():
    '''Test successful rest disable'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        'service_state': 'stopped'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_successful_enable():
    '''Test successful rest enable'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record_disabled']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        'service_state': 'started'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_successful_security_modify():
    '''Test successful rest enable'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record_disabled']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        'smb_encryption': True,
        'smb_signing': True,
        'kdc_encryption': True,
        'restrict_anonymous': "no_enumeration"
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_successful_security_modify():
    '''Test successful rest enable'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record_disabled']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        'encrypt_dc_connection': True
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_negative_security_options_modify():
    '''Test error rest enable'''
    register_responses([
    ])
    module_args = {
        "aes_netlogon_enabled": True,
        "ldap_referral_enabled": True,
        "session_security": "seal",
        "try_ldap_channel_binding": False,
        "use_ldaps": True,
        "use_start_tls": True
    }
    msg = 'parameters are mutually exclusive: use_ldaps|use_start_tls'
    assert msg in create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_successful_security_options_modify():
    '''Test successful rest enable'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record_disabled']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        "aes_netlogon_enabled": True,
        "ldap_referral_enabled": True,
        "session_security": "seal",
        "try_ldap_channel_binding": False,
        "use_ldaps": True
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_successful_rename_cifs():
    '''Test successful rest rename'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record_disabled']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        'from_name': 'cifs_server_name',
        'name': 'cifs',
        'force': True,
        'admin_user_name': 'test_user',
        'admin_password': 'pwd'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_successful_rename_modify_cifs():
    '''Test successful rest rename'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        'from_name': 'cifs_server_name',
        'name': 'cifs',
        'force': True,
        'admin_user_name': 'test_user',
        'admin_password': 'pwd',
        'service_state': 'stopped'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_error_rest_rename_cifs_without_force():
    '''Test error rest rename with force false'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record']),
    ])
    module_args = {
        'from_name': 'cifs_servers',
        'name': 'cifs1',
        'force': False,
        'admin_user_name': 'test_user',
        'admin_password': 'pwd'
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error renaming cifs server from cifs_servers to cifs1 without force.' in error


def test_error_rest_rename_error_state():
    '''Test error rest rename with service state as started'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['generic_error']),
    ])
    module_args = {
        'from_name': 'cifs_servers',
        'name': 'cifs1',
        'force': True,
        'admin_user_name': 'test_user',
        'admin_password': 'pwd',
        'service_state': 'started'
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    msg = 'Error on modifying cifs server: calling: protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa:'
    assert msg in error


def test_error_rest_rename_cifs():
    '''Test error rest rename'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
        ('GET', 'protocols/cifs/services', SRR['empty_records']),
    ])
    module_args = {
        'from_name': 'cifs_servers_test',
        'name': 'cifs1',
        'force': True,
        'admin_user_name': 'test_user',
        'admin_password': 'pwd'
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error renaming cifs server: cifs1 - no cifs server with from_name: cifs_servers_test' in error


def test_rest_error_disable():
    '''Test error rest disable'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record']),
        ('PATCH', 'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['generic_error']),
    ])
    module_args = {
        'service_state': 'stopped'
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on modifying cifs server:' in error


def test_rest_successful_create_idempotency():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['cifs_record'])
    ])
    module_args = {'use_rest': 'always'}
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed'] is False


def test_rest_successful_delete_idempotency():
    '''Test successful rest delete'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/services', SRR['empty_records'])
    ])
    module_args = {'use_rest': 'always', 'state': 'absent'}
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed'] is False
