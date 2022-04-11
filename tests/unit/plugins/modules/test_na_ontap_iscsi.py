# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_iscsi '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_iscsi \
    import NetAppOntapISCSI as iscsi_module  # module under test
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


DEFAULT_ARGS = {
    "hostname": "10.10.10.10",
    "username": "admin",
    "password": "netapp1!",
    "validate_certs": "no",
    "https": "yes",
    "state": "present",
    "use_rest": "never",
    "vserver": "svm1",
    "service_state": "started"
}


iscsi_info_started = {
    'num-records': 1,
    'attributes-list': {
        'iscsi-service-info': {
            'is-available': 'true',
            'vserver': 'svm1'
        }
    }
}

iscsi_info_stopped = {
    'num-records': 1,
    'attributes-list': {
        'iscsi-service-info': {
            'is-available': 'false',
            'vserver': 'svm1'
        }
    }
}

ZRR = zapi_responses({
    'iscsi_started': build_zapi_response(iscsi_info_started),
    'iscsi_stopped': build_zapi_response(iscsi_info_stopped)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        iscsi_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_get_nonexistent_iscsi():
    register_responses([
        ('iscsi-service-get-iter', ZRR['empty'])
    ])
    iscsi_obj = create_module(iscsi_module, DEFAULT_ARGS)
    result = iscsi_obj.get_iscsi()
    assert not result


def test_get_existing_iscsi():
    register_responses([
        ('iscsi-service-get-iter', ZRR['iscsi_started'])
    ])
    iscsi_obj = create_module(iscsi_module, DEFAULT_ARGS)
    result = iscsi_obj.get_iscsi()
    assert result


def test_successfully_create():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('iscsi-service-get-iter', ZRR['empty']),
        ('iscsi-service-create', ZRR['success'])
    ])
    assert create_and_apply(iscsi_module, DEFAULT_ARGS)['changed']


def test_create_idempotency():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('iscsi-service-get-iter', ZRR['iscsi_started'])
    ])
    assert create_and_apply(iscsi_module, DEFAULT_ARGS)['changed'] is False


def test_successfully_create_stop_service():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('iscsi-service-get-iter', ZRR['empty']),
        ('iscsi-service-create', ZRR['success'])
    ])
    args = {'service_state': 'stopped'}
    assert create_and_apply(iscsi_module, DEFAULT_ARGS, args)['changed']


def test_successfully_delete_when_service_started():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('iscsi-service-get-iter', ZRR['iscsi_started']),
        ('iscsi-service-stop', ZRR['success']),
        ('iscsi-service-destroy', ZRR['success'])
    ])
    args = {'state': 'absent'}
    assert create_and_apply(iscsi_module, DEFAULT_ARGS, args)['changed']


def test_delete_idempotent():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('iscsi-service-get-iter', ZRR['empty'])
    ])
    args = {'state': 'absent'}
    assert create_and_apply(iscsi_module, DEFAULT_ARGS, args)['changed'] is False


def test_start_iscsi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('iscsi-service-get-iter', ZRR['iscsi_stopped']),
        ('iscsi-service-start', ZRR['success'])
    ])
    assert create_and_apply(iscsi_module, DEFAULT_ARGS)['changed']


def test_stop_iscsi():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('iscsi-service-get-iter', ZRR['iscsi_started']),
        ('iscsi-service-stop', ZRR['success'])
    ])
    args = {'service_state': 'stopped'}
    assert create_and_apply(iscsi_module, DEFAULT_ARGS, args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('iscsi-service-create', ZRR['error']),
        ('iscsi-service-start', ZRR['error']),
        ('iscsi-service-stop', ZRR['error']),
        ('iscsi-service-destroy', ZRR['error'])
    ])

    iscsi_obj = create_module(iscsi_module, DEFAULT_ARGS)

    error = expect_and_capture_ansible_exception(iscsi_obj.create_iscsi_service, 'fail')['msg']
    assert 'Error creating iscsi service: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(iscsi_obj.start_iscsi_service, 'fail')['msg']
    assert 'Error starting iscsi service on vserver svm1: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(iscsi_obj.stop_iscsi_service, 'fail')['msg']
    assert 'Error Stopping iscsi service on vserver svm1: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(iscsi_obj.delete_iscsi_service, 'fail')['msg']
    assert 'Error deleting iscsi service on vserver svm1: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error
