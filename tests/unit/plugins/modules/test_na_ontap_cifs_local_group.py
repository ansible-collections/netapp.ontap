# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_cifs_local_group '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, call_main, create_module, expect_and_capture_ansible_exception, AnsibleFailJson, create_and_apply
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_group \
    import NetAppOntapCifsLocalGroup as group_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'group_record': (200, {"records": [
        {
            "svm": {
                "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                "name": "ansible"
            },
            'name': 'BUILTIN\\Guests',
            'sid': 'S-1-5-21-256008430-3394229847-3930036330-1001',
        }
    ], "num_records": 1}, None),
    "no_record": (
        200,
        {"num_records": 0},
        None)
})


ARGS_REST = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'ansible',
    'name': 'BUILTIN\\GUESTS',
}


def test_get_existent_cifs_local_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
    ])
    cifs_obj = create_module(group_module, ARGS_REST)
    result = cifs_obj.get_cifs_local_group_rest()
    assert result


def test_error_get_existent_cifs_local_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['generic_error']),
    ])
    module_args = {
        'vserver': 'ansible',
        'name': 'BUILTIN\\GUESTS',
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = 'Error on fetching cifs local-group:'
    assert msg in error


def test_create_cifs_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['empty_records']),
        ('POST', 'protocols/cifs/local-groups', SRR['empty_good']),
    ])
    module_args = {
        'vserver': 'ansible',
        'name': 'BUILTIN\\GUESTS'
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_create_cifs_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['empty_records']),
        ('POST', 'protocols/cifs/local-groups', SRR['generic_error']),
    ])
    module_args = {
        'vserver': 'ansible',
        'name': 'BUILTIN\\GUESTS',
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on creating cifs local-group:"
    assert msg in error


def test_delete_cifs_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('DELETE', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                   'S-1-5-21-256008430-3394229847-3930036330-1001', SRR['empty_good']),
    ])
    module_args = {
        'vserver': 'ansible',
        'name': 'BUILTIN\\GUESTS',
        'state': 'absent'
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_delete_cifs_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('DELETE', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                   'S-1-5-21-256008430-3394229847-3930036330-1001', SRR['generic_error']),
    ])
    module_args = {
        'vserver': 'ansible',
        'name': 'BUILTIN\\GUESTS',
        'state': 'absent'
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on deleting cifs local-group:"
    assert msg in error


def test_modify_cifs_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('PATCH', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                  'S-1-5-21-256008430-3394229847-3930036330-1001', SRR['empty_good']),
    ])
    module_args = {
        'vserver': 'ansible',
        'name': 'BUILTIN\\GUESTS',
        'description': 'This is local group'
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_modify_cifs_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('PATCH', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                  'S-1-5-21-256008430-3394229847-3930036330-1001', SRR['generic_error']),
    ])
    module_args = {
        'vserver': 'ansible',
        'name': 'BUILTIN\\GUESTS',
        'description': 'This is local group'
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error on modifying cifs local-group:"
    assert msg in error


def test_rename_cifs_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('PATCH', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                  'S-1-5-21-256008430-3394229847-3930036330-1001', SRR['empty_good']),
    ])
    module_args = {
        'vserver': 'ansible',
        'from_name': 'BUILTIN\\GUESTS',
        'name': 'ANSIBLE_CIFS\\test_users'
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_rest_rename_cifs_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_0']),
        ('GET', 'protocols/cifs/local-groups', SRR['empty_records']),
        ('GET', 'protocols/cifs/local-groups', SRR['empty_records']),
    ])
    module_args = {
        'vserver': 'ansible',
        'from_name': 'BUILTIN\\GUESTS_user',
        'name': 'ANSIBLE_CIFS\\test_users'
    }
    error = create_and_apply(group_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error renaming cifs local group:' in error


def test_successfully_create_group_rest_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
    ])
    module_args = {
        'vserver': 'ansible',
        'name': 'BUILTIN\\GUESTS',
    }
    assert not call_main(my_main, ARGS_REST, module_args)['changed']


def test_successfully_destroy_group_rest_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['empty_records']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert not call_main(my_main, ARGS_REST, module_args)['changed']
