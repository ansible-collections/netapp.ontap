# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_storage_unit_snapshot """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_storage_unit_snapshot \
    import NetAppOntapStorageUnitSnapshot as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'state': 'present',
    'name': 'snap1',
    'vserver': 'svm1',
    'storage_unit': 'lun1'
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    "storage_unit_info": (200, {
        "records": [{
            "name": "lun1",
            "type": "lun",
            "uuid": "aab8aea1-108c-11f0-b03b-005056ae54f6"
        }]
    }, None),
    "snapshot_info": (200, {
        "records": [{
            "name": "snap1",
            "uuid": "a36e9692-15d5-11f0-b03b-005056ae54f6",
            "expiry_time": "2025-04-09T07:30:00-04:00",
            "snapmirror_label": "label",
            "comment": "snapshot for LUN lun1"
        }]
    }, None),
    "updated_snapshot_info": (200, {
        "records": [{
            "name": "snap10",
            "uuid": "a36e9692-15d5-11f0-b03b-005056ae54f6",
            "expiry_time": "2025-04-09T08:30:00-04:00",
            "snapmirror_label": "label",
            "comment": "snapshot for LUN lun1"
        }]
    }, None),
    'is_ontap_system': (200, {
        'ASA_NEXT_STRICT': False,
        'ASA_NEXT': False,
        'ASA_LEGACY': False,
        'ASA_ANY': False,
        'ONTAP_X_STRICT': False,
        'ONTAP_X': False,
        'ONTAP_9_STRICT': True,
        'ONTAP_9': True}, None),
    'is_asa_r2_system': (200, {
        'ASA_R2': True,
        'ASA_LEGACY': False,
        'ASA_ANY': True,
        'ONTAP_AI_ML': False,
        'ONTAP_X': True,
        'ONTAP_9': False}, None),
})

storage_unit_uuid = 'aab8aea1-108c-11f0-b03b-005056ae54f6'
snapshot_uuid = 'a36e9692-15d5-11f0-b03b-005056ae54f6'


def test_get_snapshot_none():
    ''' Test module no records '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['zero_records']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    my_obj.get_storage_unit()
    assert my_obj.get_storage_unit_snapshot() is None


def test_get_snapshot_error():
    ''' Test module GET method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.get_storage_unit()
    msg = 'Error while fetching storage unit snapshot named snap1: calling: '\
          'storage/storage-units/%s/snapshots: got Expected error.' % storage_unit_uuid
    assert msg in expect_and_capture_ansible_exception(my_obj.get_storage_unit_snapshot, 'fail')['msg']


def test_get_snapshot():
    ''' Test GET record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['snapshot_info']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    my_obj.get_storage_unit()
    assert my_obj.get_storage_unit_snapshot() is not None


def test_create_snapshot():
    ''' Test creating a snapshot with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['empty_records']),
        ('POST', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['snapshot_info']),
    ])
    module_args = {
        'expiry_time': '2025-04-09T07:30:00-04:00',
        'snapmirror_label': 'label',
        'comment': 'snapshot for LUN lun1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_snapshot_error():
    ''' Test module POST method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['empty_records']),
        ('POST', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['generic_error'])
    ])
    module_args = {
        'expiry_time': '2025-04-09T07:30:00-04:00',
        'snapmirror_label': 'label',
        'comment': 'snapshot for LUN lun1'
    }
    msg = 'Error while creating storage unit snapshot snap1: calling: '\
          'storage/storage-units/%s/snapshots: got Expected error.' % storage_unit_uuid
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_modify_snapshot():
    ''' Test modifying and renaming snapshot with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['snapshot_info']),
        ('PATCH', 'storage/storage-units/%s/snapshots/%s' % (storage_unit_uuid, snapshot_uuid), SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['updated_snapshot_info'])
    ])
    module_args = {
        'expiry_time': '2025-04-09T08:30:00-04:00',
        'from_name': 'snap1',
        'name': 'snap10'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_snapshot_error():
    ''' Test module PATCH method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['snapshot_info']),
        ('PATCH', 'storage/storage-units/%s/snapshots/%s' % (storage_unit_uuid, snapshot_uuid), SRR['generic_error']),
    ])
    module_args = {
        'expiry_time': '2025-04-09T08:30:00-04:00'
    }
    msg = 'Error while modifying storage unit snapshot snap1: calling: '\
          'storage/storage-units/%s/snapshots/%s: got Expected error.' % (storage_unit_uuid, snapshot_uuid)
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_delete_snapshot():
    ''' Test deleting snapshot with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['snapshot_info']),
        ('DELETE', 'storage/storage-units/%s/snapshots/%s' % (storage_unit_uuid, snapshot_uuid), SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['empty_records']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_snapshot_error():
    ''' Test module DELETE method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('GET', 'storage/storage-units/%s/snapshots' % storage_unit_uuid, SRR['snapshot_info']),
        ('DELETE', 'storage/storage-units/%s/snapshots/%s' % (storage_unit_uuid, snapshot_uuid), SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent'
    }
    msg = 'Error while deleting storage unit snapshot snap1: calling: '\
          'storage/storage-units/%s/snapshots/%s: got Expected error.' % (storage_unit_uuid, snapshot_uuid)
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_version():
    ''' Test module supported from 9.16.1 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    assert 'requires ONTAP 9.16.1 or later' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


def test_error_ontap_system():
    ''' Test module not supported with ONTAP systems '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
    ])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert "na_ontap_storage_unit_snapshot module is only supported with ASA r2 systems." in error


def test_error_check_asa_r2():
    ''' Test module ONTAP personality exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['generic_error']),
    ])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert "Failed while checking if the given host is an ASA r2 system or not" in error
