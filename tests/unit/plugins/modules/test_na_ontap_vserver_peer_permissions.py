# (c) 2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception, call_main
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer_permissions \
    import NetAppONTAPVserverPeerPermissions as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'peer_record': (200, {
        "records": [
            {
                "svm": {"name": "ansibleSVM", "uuid": "e3cb5c7fcd20"},
                "cluster_peer": {"name": "test912-2", "uuid": "1e3cb5c7fcd20"},
                "applications": ['snapmirror', 'flexcache'],
            }],
        "num_records": 1
    }, None),
    "no_record": (
        200,
        {"num_records": 0},
        None)
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'ansibleSVM',
    'cluster_peer': 'test912-2',
    'applications': ['snapmirror'],
}


def test_error_validate_vserver_name_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])
    ])
    module_args = {
        'vserver': '*',
        'cluster_peer': 'test912-2'
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'As svm name * represents all svms and created by default, please provide a specific SVM name'
    assert msg in error


def test_error_validate_vserver_apps_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])
    ])
    module_args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2',
        'applications': ['']
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Applications field cannot be empty, at least one application must be specified'
    assert msg in error


def test_get_vserver_peer_permission_rest_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peer-permissions', SRR['empty_records'])
    ])
    module_args = {
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    result = my_obj.get_vserver_peer_permission_rest()
    assert result is None


def test_get_vserver_peer_permission_rest_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peer-permissions', SRR['generic_error'])
    ])
    module_args = {
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2',
    }
    my_module_object = create_module(my_module, DEFAULT_ARGS, module_args)
    msg = 'Error on fetching vserver peer permissions'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_vserver_peer_permission_rest, 'fail')['msg']


def test_create_vserver_peer_permission_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peer-permissions', SRR['empty_records']),
        ('POST', 'svm/peer-permissions', SRR['empty_good'])
    ])
    module_args = {
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2',
        'applications': ['snapmirror']
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_vserver_peer_permission_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peer-permissions', SRR['empty_records']),
        ('POST', 'svm/peer-permissions', SRR['generic_error'])
    ])
    module_args = {
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2',
        'applications': ['snapmirror']
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error on creating vserver peer permissions'
    assert msg in error


def test_modify_vserver_peer_permission_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peer-permissions', SRR['peer_record']),
        ('PATCH', 'svm/peer-permissions/1e3cb5c7fcd20/e3cb5c7fcd20', SRR['empty_good'])
    ])
    module_args = {
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2',
        'applications': ['snapmirror']
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_modify_vserver_peer_permission_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peer-permissions', SRR['peer_record']),
        ('PATCH', 'svm/peer-permissions/1e3cb5c7fcd20/e3cb5c7fcd20', SRR['generic_error'])
    ])
    module_args = {
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2',
        'applications': ['snapmirror']
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error on modifying vserver peer permissions'
    assert msg in error


def test_delete_vserver_peer_permission_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peer-permissions', SRR['peer_record']),
        ('DELETE', 'svm/peer-permissions/1e3cb5c7fcd20/e3cb5c7fcd20', SRR['empty_good'])
    ])
    module_args = {
        'state': 'absent',
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_delete_vserver_peer_permission_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peer-permissions', SRR['peer_record']),
        ('DELETE', 'svm/peer-permissions/1e3cb5c7fcd20/e3cb5c7fcd20', SRR['generic_error'])
    ])
    module_args = {
        'state': 'absent',
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2'
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error on deleting vserver peer permissions'
    assert msg in error


def test_successfully_vserver_peer_permission_rest_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peer-permissions', SRR['peer_record']),
    ])
    module_args = {
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2',
        'applications': ['snapmirror', 'flexcache']
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successfully_delete_vserver_peer_permission_rest_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peer-permissions', SRR['empty_records']),
    ])
    module_args = {
        'state': 'absent',
        'vserver': 'ansibleSVM',
        'cluster_peer': 'test912-2',
        'applications': ['snapmirror', 'flexcache']
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
