# (c) 2025, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_autoupdate_support \
    import NetAppONTAPAutoUpdateSupport as my_module, main as my_main  # module under test


SRR = rest_responses({
    'status_enabled': (200, {
        "records": [
            {
                "enabled": True,
            }],
        "num_records": 1
    }, None),
    'status_disabled': (200, {
        "records": [
            {
                "enabled": False,
            }],
        "num_records": 1
    }, None),
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'enabled': True
}


def test_get_auto_update_status():
    ''' Test retrieving auto_update_status '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/auto-update', SRR['status_enabled'])
    ])
    module_args = {}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_auto_update_status() is not None


def test_get_error_auto_update_status():
    ''' Test retrieving auto_update_status '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/auto-update', SRR['generic_error'])
    ])
    module_args = {}
    my_module_object = create_module(my_module, DEFAULT_ARGS, module_args)
    msg = 'Error retrieving the current status of the automatic update feature info:'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_auto_update_status, 'fail')['msg']


def test_modify_auto_update_status():
    ''' Test modifying auto_update_status with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/auto-update', SRR['status_enabled']),
        ('PATCH', 'support/auto-update', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/auto-update', SRR['status_disabled']),

        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'support/auto-update', SRR['status_disabled']),
        ('PATCH', 'support/auto-update', SRR['empty_good']),
    ])
    module_args = {
        'enabled': False
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        'enabled': True,
        'force': True,
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_modify_auto_update_status():
    ''' Test Error modifying auto_update_status '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('PATCH', 'support/auto-update', SRR['generic_error']),
    ])
    module_args = {
        'enabled': False
    }
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error on modifying the current status of the automatic update feature:'
    assert msg in expect_and_capture_ansible_exception(my_obj.modify_auto_update_status, 'fail', module_args)['msg']


def test_ontap_version_rest():
    ''' Test ONTAP version '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    module_args = {'use_rest': 'always'}
    error = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error: na_ontap_autoupdate_support only supports REST, and requires ONTAP 9.10.1 or later."
    assert msg in error


def test_error_modify_auto_update_status_with_force():
    ''' Test Error modifying auto_update_status with force'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    module_args = {
        'enabled': True,
        'force': True
    }
    error = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error: Minimum version of ONTAP for force is (9, 16, 1)."
    assert msg in error
