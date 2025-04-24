# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_cifs_local_group_member '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, call_main, create_module, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_group_member \
    import NetAppOntapCifsLocalGroupMember as group_member_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'group_member_record': (200, {"records": [
        {
            "svm": {
                "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                "name": "vserver"
            },
            'group_name': 'BUILTIN\\Guests',
            'member': 'test',
            'sid': 'S-1-5-21-256008430-3394229847-3930036330-1001',
        }
    ], "num_records": 1}, None),
    'group_record': (200, {"records": [
        {
            "svm": {
                "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                "name": "vserver"
            },
            'group_name': 'BUILTIN\\Guests',
            'sid': 'S-1-5-21-256008430-3394229847-3930036330-1001',
        }
    ], "num_records": 1}, None),
    "no_record": (
        200,
        {"num_records": 0},
        None)
})

group_member_info = {'num-records': 1,
                     'attributes-list':
                         {'cifs-local-group-members':
                             {'group-name': 'BUILTIN\\GUESTS',
                              'member': 'test',
                              'vserver': 'ansible'
                              }
                          },
                     }

ZRR = zapi_responses({
    'group_member_info': build_zapi_response(group_member_info)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'ansible',
    'group': 'BUILTIN\\GUESTS',
    'member': 'test',
    'use_rest': 'never',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        group_member_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_get_nonexistent_cifs_group_member():
    register_responses([
        ('cifs-local-group-members-get-iter', ZRR['empty'])
    ])
    cifs_obj = create_module(group_member_module, DEFAULT_ARGS)
    result = cifs_obj.get_cifs_local_group_member()
    assert result is None


def test_get_existent_cifs_group_member():
    register_responses([
        ('cifs-local-group-members-get-iter', ZRR['group_member_info'])
    ])
    cifs_obj = create_module(group_member_module, DEFAULT_ARGS)
    result = cifs_obj.get_cifs_local_group_member()
    assert result


def test_successfully_add_members_zapi():
    register_responses([
        ('cifs-local-group-members-get-iter', ZRR['empty']),
        ('cifs-local-group-members-add-members', ZRR['success']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_add_members_zapi():
    register_responses([
        ('cifs-local-group-members-get-iter', ZRR['empty']),
        ('cifs-local-group-members-add-members', ZRR['error']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error adding member"
    assert msg in error


def test_successfully_remove_members_zapi():
    register_responses([
        ('cifs-local-group-members-get-iter', ZRR['group_member_info']),
        ('cifs-local-group-members-remove-members', ZRR['success']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
        'state': 'absent'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_remove_members_zapi():
    register_responses([
        ('cifs-local-group-members-get-iter', ZRR['group_member_info']),
        ('cifs-local-group-members-remove-members', ZRR['error']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
        'state': 'absent'
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error removing member"
    assert msg in error


def test_successfully_add_members_zapi_idempotency():
    register_responses([
        ('cifs-local-group-members-get-iter', ZRR['group_member_info']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_remove_members_zapi_idempotency():
    register_responses([
        ('cifs-local-group-members-get-iter', ZRR['empty']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


ARGS_REST = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'ansible',
    'group': 'BUILTIN\\GUESTS',
    'member': 'test',
    'use_rest': 'always',
}


def test_get_nonexistent_cifs_local_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['empty_records']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'nogroup',
        'member': 'test',
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = 'CIFS local group nogroup does not exist on vserver ansible'
    assert msg in error


def test_get_existent_cifs_local_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('GET', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['group_member_record']),
    ])
    cifs_obj = create_module(group_member_module, ARGS_REST)
    result = cifs_obj.get_cifs_local_group_member()
    assert result


def test_error_get_existent_cifs_local_group_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('GET', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['generic_error']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = 'Error getting CIFS local group members for group BUILTIN\\GUESTS on vserver ansible'
    assert msg in error


def test_add_cifs_group_member_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('GET', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['empty_records']),
        ('POST', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                 'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['empty_good']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_add_cifs_group_member_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('GET', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['empty_records']),
        ('POST', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                 'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['generic_error']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error adding member test to cifs local group BUILTIN\\GUESTS on vserver"
    assert msg in error


def test_remove_cifs_group_member_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('GET', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['group_member_record']),
        ('DELETE', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                   'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['empty_good']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
        'state': 'absent'
    }
    assert call_main(my_main, ARGS_REST, module_args)['changed']


def test_error_remove_cifs_group_member_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('GET', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['group_member_record']),
        ('DELETE', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                   'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['generic_error']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
        'state': 'absent'
    }
    error = call_main(my_main, ARGS_REST, module_args, fail=True)['msg']
    msg = "Error removing member test from cifs local group BUILTIN\\GUESTS on vserver ansible"
    assert msg in error


def test_successfully_add_members_rest_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('GET', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['group_member_record']),
    ])
    module_args = {
        'vserver': 'ansible',
        'group': 'BUILTIN\\GUESTS',
        'member': 'test',
    }
    assert not call_main(my_main, ARGS_REST, module_args)['changed']


def test_successfully_remove_members_rest_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/cifs/local-groups', SRR['group_record']),
        ('GET', 'protocols/cifs/local-groups/671aa46e-11ad-11ec-a267-005056b30cfa/'
                'S-1-5-21-256008430-3394229847-3930036330-1001/members', SRR['empty_records']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert not call_main(my_main, ARGS_REST, module_args)['changed']
