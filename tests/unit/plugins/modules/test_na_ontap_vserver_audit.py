# (c) 2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_vserver_audit '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, call_main, create_module, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_audit \
    import NetAppONTAPVserverAudit as my_module, main as my_main      # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'audit_record': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "vserver"
                    },
                    "enabled": True,
                    "events": {
                        "authorization_policy": True,
                        "cap_staging": True,
                        "cifs_logon_logoff": False,
                        "file_operations": False,
                        "file_share": True,
                        "security_group": True,
                        "user_account": True
                    },
                    "log_path": "/",
                    "log": {
                        "format": "xml",
                        "retention": {"count": 4},
                        "rotation": {"size": 1048576}
                    },
                    "guarantee": False
                }
            ],
            "num_records": 1
        }, None
    ),
    'audit_record_modified': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "vserver"
                    },
                    "enabled": False,
                    "events": {
                        "authorization_policy": True,
                        "cap_staging": True,
                        "cifs_logon_logoff": False,
                        "file_operations": False,
                        "file_share": True,
                        "security_group": True,
                        "user_account": True
                    },
                    "log_path": "/",
                    "log": {
                        "format": "xml",
                        "retention": {"count": 4},
                        "rotation": {"size": 1048576}
                    },
                    "guarantee": False
                }
            ],
            "num_records": 1
        }, None
    ),
    "no_record": (
        200,
        {"num_records": 0},
        None),
    'audit_record_time_based_rotation': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "vserver"
                    },
                    "enabled": True,
                    "events": {
                        "authorization_policy": True,
                        "cap_staging": True,
                        "cifs_logon_logoff": False,
                        "file_operations": False,
                        "file_share": True,
                        "security_group": True,
                        "user_account": True
                    },
                    "log_path": "/",
                    "log": {
                        "format": "xml",
                        "rotation": {
                            "schedule": {
                                "hours": [
                                    6,
                                    12,
                                    18
                                ],
                                "minutes": [
                                    15,
                                    30,
                                    45
                                ],
                                "months": [
                                    1,
                                    3
                                ],
                                "weekdays": [
                                    0,
                                    2,
                                    4
                                ]
                            }
                        }
                    },
                    "guarantee": False
                }
            ],
            "num_records": 1
        }, None
    ),
})

ARGS_REST = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
    'vserver': 'vserver',
}


def test_get_nonexistent_audit_config_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['empty_records']),
    ])
    audit_obj = create_module(my_module, ARGS_REST)
    result = audit_obj.get_vserver_audit_configuration_rest()
    assert result is None


def test_get_existent_audit_config_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['audit_record']),
    ])
    audit_obj = create_module(my_module, ARGS_REST)
    result = audit_obj.get_vserver_audit_configuration_rest()
    assert result


def test_error_get_existent_audit_config_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['generic_error']),
    ])
    error = call_main(my_main, ARGS_REST, fail=True)['msg']
    msg = "Error on fetching vserver audit configuration"
    assert msg in error


def test_create_audit_config_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['empty_records']),
        ('POST', 'protocols/audit', SRR['empty_good']),
    ])
    module_args = {
        "enabled": False,
        "events": {
            "authorization_policy": False,
            "cap_staging": False,
            "cifs_logon_logoff": True,
            "file_operations": True,
            "file_share": False,
            "security_group": False,
            "user_account": False
        },
        "log_path": "/",
        "log": {
            "format": "xml",
            "retention": {"count": 4},
            "rotation": {"size": 1048576}
        }
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_create_audit_config_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['empty_records']),
        ('POST', 'protocols/audit', SRR['generic_error']),
    ])
    module_args = {
        "enabled": False,
        "events": {
            "authorization_policy": False,
            "cap_staging": False,
            "cifs_logon_logoff": True,
            "file_operations": True,
            "file_share": False,
            "security_group": False,
            "user_account": False
        },
        "log_path": "/",
        "log": {
            "format": "xml",
            "retention": {"count": 4},
            "rotation": {"size": 1048576}
        },
        "guarantee": False
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on creating vserver audit configuration"
    assert msg in error


def test_modify_audit_config_sizebased_rotation_rest():
    ''' Rotates logs based on log size '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['audit_record']),
        ('PATCH', 'protocols/audit/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        "enabled": True,
        "events": {
            "authorization_policy": True,
            "cap_staging": True,
            "cifs_logon_logoff": False,
            "file_operations": False,
            "file_share": True,
            "security_group": True,
            "user_account": True
        },
        "log_path": "/tmp",
        "log": {
            "format": "evtx",
            "retention": {"count": 5},
            "rotation": {"size": 10485760}
        }

    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_modify_audit_config_timebased_rotation_rest():
    ''' Rotates the audit logs based on a schedule '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['audit_record_time_based_rotation']),
        ('PATCH', 'protocols/audit/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        "enabled": True,
        "events": {
            "authorization_policy": True,
            "cap_staging": True,
            "cifs_logon_logoff": False,
            "file_operations": False,
            "file_share": True,
            "security_group": True,
            "user_account": True
        },
        "log_path": "/tmp",
        "log": {
            "format": "xml",
            "rotation": {
                "schedule": {
                    "hours": [12],
                    "minutes": [30],
                    "months": [-1],
                    "weekdays": [-1]
                }
            }
        },
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_enable_audit_config_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['audit_record']),
        ('PATCH', 'protocols/audit/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        "enabled": False
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_modify_audit_config_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['audit_record']),
        ('PATCH', 'protocols/audit/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['generic_error']),
    ])
    module_args = {
        "enabled": True,
        "events": {
            "authorization_policy": True,
            "cap_staging": True,
            "cifs_logon_logoff": False,
            "file_operations": False,
            "file_share": True,
            "security_group": True,
            "user_account": True
        },
        "log_path": "/tmp",
        "log": {
            "format": "evtx",
            "retention": {"count": 5},
            "rotation": {"size": 10485760}
        }
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on modifying vserver audit configuration"
    assert msg in error


def test_error_enabling_audit_config_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['audit_record']),
        ('PATCH', 'protocols/audit/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
        ('PATCH', 'protocols/audit/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        "enabled": False,
        "events": {
            "authorization_policy": False,
            "cap_staging": False,
            "cifs_logon_logoff": False,
            "file_operations": False,
            "file_share": True,
            "security_group": True,
            "user_account": True
        },
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_disabling_events_audit_config_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    module_args = {
        "events": {
            "authorization_policy": False,
            "cap_staging": False,
            "cifs_logon_logoff": False,
            "file_operations": False,
            "file_share": False,
            "security_group": False,
            "user_account": False
        },
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "At least one event should be enabled"
    assert msg in error


@patch('time.sleep')
def test_delete_audit_config_rest(sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['audit_record']),
        ('PATCH', 'protocols/audit/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
        ('GET', 'protocols/audit', SRR['audit_record_modified']),
        ('DELETE', 'protocols/audit/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        "state": "absent"
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


@patch('time.sleep')
def test_error_delete_audit_config_rest(sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['audit_record']),
        ('PATCH', 'protocols/audit/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
        ('GET', 'protocols/audit', SRR['audit_record_modified']),
        ('DELETE', 'protocols/audit/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['generic_error']),
    ])
    module_args = {
        "state": "absent"
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on deleting vserver audit configuration"
    assert msg in error


def test_create_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['audit_record']),
    ])
    module_args = {
        'state': 'present'
    }
    assert not call_main(my_main, ARGS_REST, module_args)['changed']


def test_delete_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/audit', SRR['empty_records'])
    ])
    module_args = {
        'state': 'absent'
    }
    assert not call_main(my_main, ARGS_REST, module_args)['changed']
