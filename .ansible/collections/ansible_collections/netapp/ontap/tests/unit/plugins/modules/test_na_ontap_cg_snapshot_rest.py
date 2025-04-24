# (c) 2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_cg_snapshot while using REST """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_and_apply, create_module
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cg_snapshot \
    import NetAppONTAPCGSnapshot as my_module  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'vserver': 'ansibleSVM'
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    'cg_info_by_cg_name': (200, {"records": [
        {
            "uuid": "af37131d-5dd2-11ee-b8da-005056b37403",
            "name": "cg1",
            "svm": {
                "uuid": "39c2a5a0-35e2-11ee-b8da-005056b37403",
                "name": "ansibleSVM"
            }
        }
    ],
        "num_records": 1
    }, None),
    'cg_info_by_volumes': (200, {"records": [
        {
            "uuid": "af37131d-5dd2-11ee-b8da-005056b37403",
            "name": "cg1",
            "svm": {
                "uuid": "39c2a5a0-35e2-11ee-b8da-005056b37403",
                "name": "ansibleSVM"
            },
            "volumes": [
                {
                    "name": "vol1"
                },
                {
                    "name": "vol2"
                }
            ]
        }
    ],
        "num_records": 1
    }, None),
    'cg_snapshot_info': (200, {"records": [
        {
            "consistency_group": {
                "name": "cg1"
            },
            "uuid": "695a3306-6361-11ee-b8da-005056b37403",
            "name": "snapshot1",
            "comment": "dummy comment",
            "snapmirror_label": "sm_label1"
        }
    ],
        "num_records": 1
    }, None),
})


cg_uuid = SRR['cg_info_by_cg_name'][1]['records'][0]['uuid']
snapshot_uuid = SRR['cg_snapshot_info'][1]['records'][0]['uuid']


def test_rest_successful_create_snapshot_given_consistency_group():
    '''Test successful rest create snapshot given consistency_group'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['cg_info_by_cg_name']),  # retrieve CG, given consistency_group
        ('GET', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['empty_records']),  # retrieve snapshots for the CG
        ('POST', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['success']),  # create CG snapshot
    ])
    module_args = {
        'state': 'present',
        'consistency_group': 'cg1',
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successful_create_snapshot_idempotency():
    '''Test successful rest create snapshot idempotency'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['cg_info_by_cg_name']),  # retrieve CG, given consistency_group
        ('GET', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['cg_snapshot_info']),  # retrieve snapshots for the CG
    ])
    module_args = {
        'state': 'present',
        'consistency_group': 'cg1',
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed'] is False


def test_rest_successful_create_snapshot_given_volumes():
    '''Test successful rest create snapshot given volumes'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['cg_info_by_volumes']),  # retrieve CG, given volumes
        ('GET', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['empty_records']),  # retrieve snapshots for the CG
        ('POST', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['success']),  # create CG snapshot
    ])
    module_args = {
        'state': 'present',
        'volumes': ['vol1', 'vol2'],
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_create_snapshot():
    '''Test error rest create snapshot'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['cg_info_by_cg_name']),  # retrieve CG, given consistency_group
        ('GET', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['empty_records']),  # retrieve snapshots for the CG
        ('POST', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['generic_error']),
    ])
    module_args = {
        'state': 'present',
        'consistency_group': 'cg1',
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Error creating consistency group snapshot' in error


def test_rest_successful_delete_snapshot_given_consistency_group():
    '''Test successful rest delete snapshot given consistency_group'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['cg_info_by_cg_name']),  # retrieve CG, given consistency_group
        ('GET', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['cg_snapshot_info']),  # retrieve snapshots for the CG
        ('DELETE', '/application/consistency-groups/%s/snapshots/%s' % (cg_uuid, snapshot_uuid), SRR['success']),  # delete CG snapshot
    ])
    module_args = {
        'state': 'absent',
        'consistency_group': 'cg1',
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successful_delete_snapshot_idempotency():
    '''Test successful rest delete snapshot idempotency'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['cg_info_by_cg_name']),  # retrieve CG, given consistency_group
        ('GET', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['empty_records']),  # retrieve snapshots for the CG
    ])
    module_args = {
        'state': 'absent',
        'consistency_group': 'cg1',
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed'] is False


def test_rest_successful_delete_snapshot_given_volumes():
    '''Test successful rest delete snapshot given volumes'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['cg_info_by_volumes']),  # retrieve CG, given volumes
        ('GET', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['cg_snapshot_info']),  # retrieve snapshots for the CG
        ('DELETE', '/application/consistency-groups/%s/snapshots/%s' % (cg_uuid, snapshot_uuid), SRR['success']),  # delete CG snapshot
    ])
    module_args = {
        'state': 'absent',
        'volumes': ['vol1', 'vol2'],
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_delete_snapshot():
    '''Test error rest delete snapshot'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['cg_info_by_cg_name']),  # retrieve CG, given consistency_group
        ('GET', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['cg_snapshot_info']),  # retrieve snapshots for the CG
        ('DELETE', '/application/consistency-groups/%s/snapshots/%s' % (cg_uuid, snapshot_uuid), SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent',
        'consistency_group': 'cg1',
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Error deleting consistency group snapshot' in error


def test_error_ontap_version():
    ''' Test module supported from 9.10 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    module_args = {
        'state': 'present',
        'consistency_group': 'cg1',
        'snapshot': 'snap1'
    }
    error = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'requires ONTAP 9.10.1 or later' in error


def test_rest_error_mutually_exclusive_params():
    '''Test error rest mutually exclusive parameters'''
    register_responses([
    ])
    module_args = {
        'state': 'present',
        'consistency_group': 'cg1',
        'volumes': ['vol1', 'vol2'],
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    error = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert "parameters are mutually exclusive: consistency_group|volumes" in error


def test_rest_error_cg_not_found_given_consistency_group():
    '''Test error rest consistency group not found, given consistency_group'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['empty_records']),  # retrieve CG, given consistency_group
    ])
    module_args = {
        'state': 'present',
        'consistency_group': 'cg1',
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert "Consistency group named 'cg1' not found" in error


def test_rest_error_cg_not_found_given_volumes():
    '''Test error rest consistency group not found, given volumes'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['empty_records']),  # retrieve CG, given volumes
    ])
    module_args = {
        'state': 'present',
        'volumes': ['vol3'],
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert "Consistency group having volumes '['vol3']' not found" in error


def test_rest_error_retrieve_cg():
    '''Test error rest retrieve consistency group'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['generic_error']),  # retrieve CG, given consistency_group
    ])
    module_args = {
        'state': 'absent',
        'consistency_group': 'cg1',
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Error searching for consistency group' in error


def test_rest_error_retrieve_cg_snapshot():
    '''Test error rest retrieve consistency group snapshot'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', '/application/consistency-groups', SRR['cg_info_by_cg_name']),  # retrieve CG, given consistency_group
        ('GET', '/application/consistency-groups/%s/snapshots' % (cg_uuid), SRR['generic_error']),  # retrieve snapshots for the CG
    ])
    module_args = {
        'state': 'absent',
        'consistency_group': 'cg1',
        'snapshot': 'snap1',
        'snapmirror_label': 'sm_label1',
        'comment': 'dummy comment'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Error searching for consistency group snapshot' in error
