# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_storage_unit """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception, \
    assert_warning_was_raised, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_storage_unit \
    import NetAppOntapStorageUnit as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'state': 'present',
    'name': 'lun1_clone1',
    'vserver': 'svm1',
    'wait_for_completion': True
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    "storage_unit_info": (200, {
        "records": [{
            "name": "lun1_clone1",
            "type": "lun",
            "uuid": "3b6bca66-3ebe-f0cc-c3d0-8fb9d5bad2cd",
            "clone": {
                "is_flexclone": True,
                "split_initiated": False
            },
            "location": {
                "storage_availability_zone": {
                    "name": "storage_availability_zone_0"
                }
            },
        }]
    }, None),
    "split_storage_unit_info": (200, {
        "records": [{
            "name": "lun1_clone1",
            "type": "lun",
            "uuid": "3b6bca66-3ebe-f0cc-c3d0-8fb9d5bad2cd",
            "clone": {
                "is_flexclone": False,
                "split_initiated": False
            }
        }]
    }, None),
    "moved_storage_unit_info": (200, {
        "records": [{
            "name": "lun1_clone1",
            "type": "lun",
            "uuid": "3b6bca66-3ebe-f0cc-c3d0-8fb9d5bad2cd",
            "clone": {
                "is_flexclone": False,
                "split_initiated": False
            },
            "location": {
                "storage_availability_zone": {
                    "name": "storage_availability_zone_1"
                }
            },
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
    'process_running_error': (400, None, "calling: storage/storage-units: got job reported error: Timeout error: Process still running, \
                                          received {'job': {'uuid': 'ea6959a9-1eb7-11f0-b03b-005056ae54f6', '_links': {'self': {'href': \
                                          '/api/cluster/jobs/ea6959a9-1eb7-11f0-b03b-005056ae54f6'}}}}.."),
})

storage_unit_uuid = '3b6bca66-3ebe-f0cc-c3d0-8fb9d5bad2cd'


def test_get_storage_unit_none():
    ''' Test module no records '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['zero_records']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_storage_unit() is None


def test_get_storage_unit_error():
    ''' Test module GET method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error while fetching storage unit named lun1_clone1: calling: '\
          'storage/storage-units: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.get_storage_unit, 'fail')['msg']


def test_get_storage_unit():
    ''' Test GET record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_storage_unit() is not None


def test_clone_storage_unit():
    ''' Test cloning a storage unit with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['empty_records']),
        ('POST', 'storage/storage-units', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
    ])
    module_args = {
        'clone': {
            'storage_unit': 'lun1'
        }
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_clone_still_running_background_warning():
    ''' Test storage cloning in background warning '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['empty_records']),
        ('POST', 'storage/storage-units', SRR['process_running_error'])
    ])
    module_args = {
        'clone': {
            'storage_unit': 'lun1'
        }
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised("Storage unit cloning is still in progress after 180 seconds.")


def test_clone_still_running_warning():
    ''' Test storage cloning still running warning '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['empty_records']),
        ('POST', 'storage/storage-units', SRR['process_running_error'])
    ])
    module_args = {
        'clone': {
            'storage_unit': 'lun1'
        },
        'wait_for_completion': False
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised("Process is still running in the background, "
                              "exiting with no further waiting as 'wait_for_completion' is set to false.")


def test_clone_storage_unit_error():
    ''' Test module POST method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['empty_records']),
        ('POST', 'storage/storage-units', SRR['generic_error'])
    ])
    module_args = {
        'clone': {
            'storage_unit': 'lun1'
        }
    }
    msg = 'Error while cloning storage unit lun1_clone1: calling: '\
          'storage/storage-units: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_split_storage_unit_clone():
    ''' Test clone splitting storage unit with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('PATCH', 'storage/storage-units/%s' % storage_unit_uuid, SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['split_storage_unit_info'])
    ])
    module_args = {
        'split_initiated': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_split_storage_unit_clone_warning():
    ''' Test warning for splitting a flexvol storage unit '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['split_storage_unit_info']),
    ])
    module_args = {
        'split_initiated': True
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised("Clone split operation can be performed only for a FlexClone storage unit.")


def test_clone_split_still_running_background_warning():
    ''' Test storage clone splitting in background warning '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('PATCH', 'storage/storage-units/%s' % storage_unit_uuid, SRR['process_running_error']),
    ])
    module_args = {
        'split_initiated': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised("Storage unit clone split is still in progress after 180 seconds.")


def test_split_storage_unit_clone_error():
    ''' Test module PATCH method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('PATCH', 'storage/storage-units/%s' % storage_unit_uuid, SRR['generic_error']),
    ])
    module_args = {
        'split_initiated': True
    }
    msg = 'Error while splitting storage unit clone lun1_clone1: calling: '\
          'storage/storage-units/%s: got Expected error.' % (storage_unit_uuid)
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_restore_storage_unit():
    ''' Test restoring storage unit using snapshot '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('PATCH', 'storage/storage-units/%s' % storage_unit_uuid, SRR['empty_good']),
    ])
    module_args = {
        'restore_to': 'hourly.2025-04-21_0905'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_restore_still_running_background_warning():
    ''' Test storage clone restore running in background warning '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('PATCH', 'storage/storage-units/%s' % storage_unit_uuid, SRR['process_running_error']),
    ])
    module_args = {
        'restore_to': 'hourly.2025-04-21_0905'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised("Storage unit is still restoring after 180 seconds.")


def test_restore_storage_unit_error():
    ''' Test module PATCH method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('PATCH', 'storage/storage-units/%s' % storage_unit_uuid, SRR['generic_error']),
    ])
    module_args = {
        'restore_to': 'hourly.2025-04-21_0905'
    }
    msg = 'Error while restoring storage unit lun1_clone1: calling: '\
          'storage/storage-units/%s: got Expected error.' % (storage_unit_uuid)
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_move_storage_unit():
    ''' Test moving storage unit to a different storage availability zone with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('PATCH', 'storage/storage-units/%s' % storage_unit_uuid, SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['moved_storage_unit_info']),
    ])
    module_args = {
        'target_location': 'storage_availability_zone_1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_move_still_running_background_warning():
    ''' Test storage unit getting moved in background warning '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('PATCH', 'storage/storage-units/%s' % storage_unit_uuid, SRR['process_running_error']),
    ])
    module_args = {
        'target_location': 'storage_availability_zone_1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised("Storage unit is still getting moved after 180 seconds.")


def test_move_storage_unit_error():
    ''' Test module PATCH method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_asa_r2_system']),
        ('GET', 'storage/storage-units', SRR['storage_unit_info']),
        ('PATCH', 'storage/storage-units/%s' % storage_unit_uuid, SRR['generic_error']),
    ])
    module_args = {
        'target_location': 'storage_availability_zone_1'
    }
    msg = 'Error while moving storage unit lun1_clone1: calling: '\
          'storage/storage-units/%s: got Expected error.' % (storage_unit_uuid)
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
    assert "na_ontap_storage_unit module is only supported with ASA r2 systems." in error


def test_error_check_asa_r2():
    ''' Test module ONTAP personality exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['generic_error']),
    ])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert "Failed while checking if the given host is an ASA r2 system or not" in error
