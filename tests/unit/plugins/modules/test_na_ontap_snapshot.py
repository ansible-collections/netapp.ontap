# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_nvme_snapshot'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    call_main, create_and_apply, create_module, expect_and_capture_ansible_exception, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapshot \
    import NetAppOntapSnapshot as my_module, main as my_main

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


SRR = rest_responses({
    'volume_uuid': (200,
                    {'records': [{"uuid": "test_uuid"}], 'num_records': 1}, None,
                    ),
    'snapshot_record': (200,
                        {'records': [{"volume": {"uuid": "d9cd4ec5-c96d-11eb-9271-005056b3ef5a",
                                                 "name": "ansible_vol"},
                                      "uuid": "343b5227-8c6b-4e79-a133-304bbf7537ce",
                                      "svm": {"uuid": "b663d6f0-c96d-11eb-9271-005056b3ef5a",
                                              "name": "ansible"},
                                      "name": "ss1",
                                      "create_time": "2021-06-10T17:24:41-04:00",
                                      "comment": "123",
                                      "expiry_time": "2022-02-04T14:00:00-05:00",
                                      "snapmirror_label": "321", }], 'num_records': 1}, None),
    'create_response': (200, {'job': {'uuid': 'd0b3eefe-cd59-11eb-a170-005056b338cd',
                                      '_links': {
                                          'self': {'href': '/api/cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd'}}}},
                        None),
    'job_response': (200, {'uuid': 'e43a40db-cd61-11eb-a170-005056b338cd',
                           'description': 'PATCH /api/storage/volumes/d9cd4ec5-c96d-11eb-9271-005056b3ef5a/'
                           'snapshots/da995362-cd61-11eb-a170-005056b338cd',
                           'state': 'success',
                           'message': 'success',
                           'code': 0,
                           'start_time': '2021-06-14T18:43:08-04:00',
                           'end_time': '2021-06-14T18:43:08-04:00',
                           'svm': {'name': 'ansible', 'uuid': 'b663d6f0-c96d-11eb-9271-005056b3ef5a',
                                   '_links': {'self': {'href': '/api/svm/svms/b663d6f0-c96d-11eb-9271-005056b3ef5a'}}},
                           '_links': {'self': {'href': '/api/cluster/jobs/e43a40db-cd61-11eb-a170-005056b338cd'}}},
                     None)
}, allow_override=False)


snapshot_info = {
    'num-records': 1,
    'attributes-list': {
        'snapshot-info': {
            'comment': 'new comment',
            'name': 'ansible',
            'snapmirror-label': 'label12'
        }
    }
}

ZRR = zapi_responses({
    'get_snapshot': build_zapi_response(snapshot_info)
})


DEFAULT_ARGS = {
    'state': 'present',
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'vserver',
    'comment': 'test comment',
    'snapshot': 'test_snapshot',
    'snapmirror_label': 'test_label',
    'volume': 'test_vol'
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    error = create_module(my_module, fail=True)['msg']
    assert 'missing required arguments:' in error
    for arg in ('hostname', 'snapshot', 'volume', 'vserver'):
        assert arg in error


def test_ensure_get_called():
    ''' test get_snapshot()  for non-existent snapshot'''
    register_responses([
        ('snapshot-get-iter', ZRR['empty']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_snapshot() is None


def test_ensure_get_called_existing():
    ''' test get_snapshot()  for existing snapshot'''
    register_responses([
        ('snapshot-get-iter', ZRR['get_snapshot']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_snapshot()


def test_successful_create():
    ''' creating snapshot and testing idempotency '''
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('snapshot-get-iter', ZRR['empty']),
        ('snapshot-create', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'async_bool': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify():
    ''' modifying snapshot and testing idempotency '''
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('snapshot-get-iter', ZRR['get_snapshot']),
        ('snapshot-modify-iter', ZRR['success']),
        ('ems-autosupport-log', ZRR['success']),
        ('snapshot-get-iter', ZRR['get_snapshot']),
    ])
    module_args = {
        'use_rest': 'never',
        'comment': 'adding comment',
        'snapmirror_label': 'label22',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        'use_rest': 'never',
        'comment': 'new comment',
        'snapmirror_label': 'label12',
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_rename():
    ''' modifying snapshot and testing idempotency '''
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('snapshot-get-iter', ZRR['empty']),
        ('snapshot-get-iter', ZRR['get_snapshot']),
        ('snapshot-rename', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'from_name': 'from_snapshot',
        'comment': 'new comment',
        'snapmirror_label': 'label12',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_delete():
    ''' deleting snapshot and testing idempotency '''
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('snapshot-get-iter', ZRR['get_snapshot']),
        ('snapshot-delete', ZRR['success']),
        ('ems-autosupport-log', ZRR['success']),
        ('snapshot-get-iter', ZRR['empty']),
    ])
    module_args = {
        'use_rest': 'never',
        'state': 'absent',
        'ignore_owners': True,
        'snapshot_instance_uuid': 'uuid',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('snapshot-create', ZRR['error']),
        ('snapshot-delete', ZRR['error']),
        ('snapshot-modify-iter', ZRR['error']),
        ('snapshot-rename', ZRR['error']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),           # get version
        ('POST', 'storage/volumes/None/snapshots', SRR['generic_error']),
        ('DELETE', 'storage/volumes/None/snapshots/None', SRR['generic_error']),
        ('PATCH', 'storage/volumes/None/snapshots/None', SRR['generic_error']),
        ('GET', 'storage/volumes', SRR['generic_error'])
    ])
    module_args = {
        'use_rest': 'never',
        'from_name': 'from_snapshot'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert 'Error creating snapshot test_snapshot:' in expect_and_capture_ansible_exception(my_obj.create_snapshot, 'fail')['msg']
    assert 'Error deleting snapshot test_snapshot:' in expect_and_capture_ansible_exception(my_obj.delete_snapshot, 'fail')['msg']
    assert 'Error modifying snapshot test_snapshot:' in expect_and_capture_ansible_exception(my_obj.modify_snapshot, 'fail')['msg']
    assert 'Error renaming snapshot from_snapshot to test_snapshot:' in expect_and_capture_ansible_exception(my_obj.rename_snapshot, 'fail')['msg']
    module_args = {'use_rest': 'always'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert 'Error when creating snapshot:' in expect_and_capture_ansible_exception(my_obj.create_snapshot, 'fail')['msg']
    assert 'Error when deleting snapshot:' in expect_and_capture_ansible_exception(my_obj.delete_snapshot, 'fail')['msg']
    assert 'Error when modifying snapshot:' in expect_and_capture_ansible_exception(my_obj.modify_snapshot, 'fail')['msg']
    assert 'Error getting volume info:' in expect_and_capture_ansible_exception(my_obj.get_volume_uuid, 'fail')['msg']


def test_module_fail_rest_ONTAP96():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])      # get version
    ])
    module_args = {'use_rest': 'always'}
    msg = 'snapmirror_label is supported with REST on Ontap 9.7 or higher'
    assert msg == create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_successfully_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volumes', SRR['volume_uuid']),
        ('GET', 'storage/volumes/test_uuid/snapshots', SRR['empty_good']),
        ('POST', 'storage/volumes/test_uuid/snapshots', SRR['create_response']),
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_response']),
    ])
    module_args = {
        'use_rest': 'always',
        'expiry_time': 'expiry'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_create_no_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volumes', SRR['empty_records']),
    ])
    module_args = {'use_rest': 'always'}
    msg = 'Error: volume test_vol not found for vserver vserver.'
    assert msg == create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_successfully_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volumes', SRR['volume_uuid']),
        ('GET', 'storage/volumes/test_uuid/snapshots', SRR['snapshot_record']),
        ('PATCH', 'storage/volumes/test_uuid/snapshots/343b5227-8c6b-4e79-a133-304bbf7537ce', SRR['create_response']),  # modify
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_response']),
    ])
    module_args = {
        'use_rest': 'always',
        'comment': 'new comment',
        'expiry_time': 'expiry'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_rename():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volumes', SRR['volume_uuid']),
        ('GET', 'storage/volumes/test_uuid/snapshots', SRR['empty_records']),
        ('GET', 'storage/volumes/test_uuid/snapshots', SRR['snapshot_record']),
        ('PATCH', 'storage/volumes/test_uuid/snapshots/343b5227-8c6b-4e79-a133-304bbf7537ce', SRR['create_response']),  # modify
        ('GET', 'cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd', SRR['job_response']),
    ])
    module_args = {
        'use_rest': 'always',
        'from_name': 'old_snapshot'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_rename_from_not_found():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volumes', SRR['volume_uuid']),
        ('GET', 'storage/volumes/test_uuid/snapshots', SRR['empty_records']),
        ('GET', 'storage/volumes/test_uuid/snapshots', SRR['empty_records']),
    ])
    module_args = {
        'use_rest': 'always',
        'from_name': 'old_snapshot'}
    msg = 'Error renaming snapshot: test_snapshot - no snapshot with from_name: old_snapshot.'
    assert msg == create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_successfully_delete():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volumes', SRR['volume_uuid']),
        ('GET', 'storage/volumes/test_uuid/snapshots', SRR['snapshot_record']),
        ('DELETE', 'storage/volumes/test_uuid/snapshots/343b5227-8c6b-4e79-a133-304bbf7537ce', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_delete():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volumes', SRR['volume_uuid']),
        ('GET', 'storage/volumes/test_uuid/snapshots', SRR['snapshot_record']),
        ('DELETE', 'storage/volumes/test_uuid/snapshots/343b5227-8c6b-4e79-a133-304bbf7537ce', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
        'state': 'absent'}
    msg = 'Error when deleting snapshot: calling: storage/volumes/test_uuid/snapshots/343b5227-8c6b-4e79-a133-304bbf7537ce: got Expected error.'
    assert msg == create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_call_main():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volumes', SRR['volume_uuid']),
        ('GET', 'storage/volumes/test_uuid/snapshots', SRR['snapshot_record']),
        ('DELETE', 'storage/volumes/test_uuid/snapshots/343b5227-8c6b-4e79-a133-304bbf7537ce', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
        'state': 'absent'}
    msg = 'Error when deleting snapshot: calling: storage/volumes/test_uuid/snapshots/343b5227-8c6b-4e79-a133-304bbf7537ce: got Expected error.'
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_unsupported_options():
    module_args = {
        'use_rest': 'always',
        'ignore_owners': True}
    error = "REST API currently does not support 'ignore_owners'"
    assert error == create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args = {
        'use_rest': 'never',
        'expiry_time': 'any'}
    error = "expiry_time is currently only supported with REST on Ontap 9.6 or higher"
    assert error == create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_missing_netapp_lib(mock_has_netapp_lib):
    module_args = {
        'use_rest': 'never',
    }
    mock_has_netapp_lib.return_value = False
    msg = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert msg == create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
