# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_cg """

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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cg \
    import NetAppOntapConsistencyGroup as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'state': 'present',
    'vserver': 'svm1',
    'name': 'test_cg1'
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    "cg_with_single_volume_info": (200, {
        "records": [{
            "name": "test_cg1",
            "uuid": "faca8bd2-0326-11f1-968d-005056b35ed4",
            "svm": {"name": "svm1"},
            "volumes": [
                {
                    "name": "test_vol1",
                    "space": {"size": 20971520},
                    "snapshot_policy": {"name": "default"},
                    "qos": {
                        "policy": {"name": "value-fixed"}
                    }
                }
            ]
        }]
    }, None),
    "cg_with_single_volume_updated_info": (200, {
        "records": [{
            "name": "test_cg1",
            "uuid": "faca8bd2-0326-11f1-968d-005056b35ed4",
            "svm": {"name": "svm1"},
            "snapshot_policy": {"name": "default-1weekly"},
            "volumes": [
                {
                    "name": "test_vol1",
                    "space": {"size": 20971520},
                    "snapshot_policy": {"name": "default"},
                    "qos": {
                        "policy": {"name": "value-fixed"}
                    }
                }
            ]
        }]
    }, None),
    "cg_with_two_volumes_info": (200, {
        "records": [{
            "name": "test_cg1",
            "uuid": "faca8bd2-0326-11f1-968d-005056b35ed4",
            "svm": {"name": "svm1"},
            "volumes": [
                {
                    "name": "test_vol1",
                    "space": {"size": 20971520},
                    "snapshot_policy": {"name": "default"},
                    "qos": {
                        "policy": {"name": "value-fixed"}
                    }
                },
                {
                    "name": "test_vol2",
                    "space": {"size": 20971520},
                    "snapshot_policy": {"name": "default"},
                    "qos": {
                        "policy": {"name": "value-fixed"}
                    }
                }
            ]
        }]
    }, None),
    "cg_with_lun_info": (200, {
        "records": [{
            "name": "test_cg1",
            "uuid": "faca8bd2-0326-11f1-968d-005056b35ed4",
            "svm": {"name": "svm1"},
            "volumes": [
                {
                    "name": "test_vol1",
                    "space": {"size": 20971520},
                    "snapshot_policy": {"name": "default"},
                    "qos": {
                        "policy": {"name": "value-fixed"}
                    }
                }
            ],
            "luns": [
                {
                    "name": "/vol/test_vol1/test_lun1",
                    "space": {"size": 5242880},
                    "os_type": "linux"
                }
            ]
        }]
    }, None),
    "cg_with_namespace_info": (200, {
        "records": [{
            "name": "test_cg1",
            "uuid": "faca8bd2-0326-11f1-968d-005056b35ed4",
            "svm": {"name": "svm1"},
            "volumes": [
                {
                    "name": "test_vol1",
                    "space": {"size": 20971520},
                    "snapshot_policy": {"name": "default"},
                    "qos": {
                        "policy": {"name": "value-fixed"}
                    }
                }
            ],
            "namespaces": [
                {
                    "name": "/vol/test_vol1/test_namespace1",
                    "space": {"size": 5242880},
                    "os_type": "linux"
                }
            ]
        }]
    }, None),
    "cg_with_one_child_info": (200, {
        "records": [{
            "name": "test_cg1",
            "uuid": "faca8bd2-0326-11f1-968d-005056b35ed4",
            "svm": {"name": "svm1"},
            "consistency_groups": [
                {
                    "name": "child_1",
                    "volumes": [
                        {
                            "name": "test_vol1",
                            "space": {"size": 20971520},
                            "snapshot_policy": {"name": "default"},
                            "qos": {
                                "policy": {"name": "value-fixed"}
                            }
                        }
                    ]
                }
            ]
        }]
    }, None),
    "cg_with_two_childs_info": (200, {
        "records": [{
            "name": "test_cg1",
            "uuid": "faca8bd2-0326-11f1-968d-005056b35ed4",
            "svm": {"name": "svm1"},
            "consistency_groups": [
                {
                    "name": "child_1",
                    "volumes": [
                        {
                            "name": "test_vol1",
                            "space": {"size": 20971520}
                        }
                    ]
                },
                {
                    "name": "child_2",
                    "volumes": [
                        {
                            "name": "test_vol2",
                            "space": {"size": 20971520}
                        }
                    ]
                }
            ]
        }]
    }, None),
})


def test_get_consistency_group_none():
    ''' Test module no records '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['zero_records']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_consistency_group_rest() is None


def test_get_consistency_group_error():
    ''' Test module GET method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error retrieving consistency group test_cg1: calling: application/consistency-groups: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.get_consistency_group_rest, 'fail')['msg']


def test_get_consistency_group():
    ''' Test GET record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_info']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_consistency_group_rest() is not None


def test_create_consistency_group_with_new_volume():
    ''' Test creating a consistency group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['empty_records']),
        ('POST', 'application/consistency-groups', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_info'])
    ])
    module_args = {
        'name': 'test_cg1',
        'vserver': 'svm1',
        'volumes': [
            {
                'name': 'test_vol1',
                'size': 20,
                'size_unit': 'mb',
                'provisioning_options': {
                    'action': 'create'
                }
            }
        ]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_consistency_group_with_new_child_existing_volume():
    ''' Test creating a consistency group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['empty_records']),
        ('POST', 'application/consistency-groups', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_one_child_info'])
    ])
    module_args = {
        'name': 'test_cg1',
        'vserver': 'svm1',
        'consistency_groups': [
            {
                'name': 'child_1',
                'provisioning_options': {
                    'action': 'create'
                },
                'volumes': [
                    {
                        'name': 'test_vol1',
                        'provisioning_options': {
                            'action': 'add'
                        }
                    }
                ]
            }
        ]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_consistency_group_with_two_childs_existing_volume():
    ''' Test creating a consistency group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['empty_records']),
        ('POST', 'application/consistency-groups', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_two_childs_info'])
    ])
    module_args = {
        'name': 'test_cg1',
        'vserver': 'svm1',
        'consistency_groups': [
            {
                'name': 'child_1',
                'volumes': [
                    {
                        'name': 'test_vol1',
                        'provisioning_options': {
                            'action': 'add'
                        }
                    }
                ]
            },
            {
                'name': 'child_2',
                'volumes': [
                    {
                        'name': 'test_vol2',
                        'provisioning_options': {
                            'action': 'add'
                        }
                    }
                ]
            }
        ]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_consistency_group_error():
    ''' Test module POST method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['empty_records']),
        ('POST', 'application/consistency-groups', SRR['generic_error'])
    ])
    msg = 'Error creating consistency group test_cg1: calling: '\
          'application/consistency-groups: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, fail=True)['msg']


def test_modify_consistency_group_add_existing_volume():
    ''' Test modifying consistency group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_info']),
        ('PATCH', 'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_two_volumes_info'])
    ])
    module_args = {
        'name': 'test_cg1',
        'vserver': 'svm1',
        'volumes': [
            {
                'name': 'test_vol2',
                'provisioning_options': {
                    'action': 'add'
                }
            }
        ]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_consistency_group_remove_volume():
    ''' Test modifying consistency group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_two_volumes_info']),
        ('PATCH', 'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_info'])
    ])
    module_args = {
        'name': 'test_cg1',
        'vserver': 'svm1',
        'volumes': [
            {
                'name': 'test_vol2',
                'provisioning_options': {
                    'action': 'remove'
                }
            }
        ]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_consistency_group_add_luns():
    ''' Test modifying consistency group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_info']),
        ('PATCH', 'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_lun_info'])
    ])
    module_args = {
        'name': 'test_cg1',
        'vserver': 'svm1',
        'luns': [
            {
                'name': '/vol/test_vol1/test_lun1',
                'size': 5,
                'size_unit': 'mb',
                'os_type': 'linux',
                'provisioning_options': {
                    'action': 'create'
                }
            }
        ]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_consistency_group_add_namespaces():
    ''' Test modifying consistency group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_info']),
        ('PATCH', 'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_namespace_info'])
    ])
    module_args = {
        'name': 'test_cg1',
        'vserver': 'svm1',
        'namespaces': [
            {
                'name': '/vol/test_vol1/test_namespace1',
                'size': 5,
                'size_unit': 'mb',
                'os_type': 'linux',
                'provisioning_options': {
                    'action': 'create'
                }
            }
        ]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_consistency_group_remove_child():
    ''' Test modifying consistency group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_13_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_two_childs_info']),
        ('PATCH', 'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_13_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_one_child_info'])
    ])
    module_args = {
        'name': 'test_cg1',
        'vserver': 'svm1',
        'consistency_groups': [
            {
                'name': 'child_2',
                'provisioning_options': {
                    'action': 'remove',
                    'name': 'new_single_cg'
                }
            }
        ]
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_consistency_group_update_snapshot_policy():
    ''' Test modifying consistency group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_info']),
        ('PATCH', 'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_updated_info'])
    ])
    module_args = {
        'name': 'test_cg1',
        'vserver': 'svm1',
        'snapshot_policy': 'default-1weekly'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_consistency_group_error():
    ''' Test module PATCH method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_info']),
        ('PATCH', 'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4', SRR['generic_error']),
    ])
    module_args = {
        'name': 'test_cg1',
        'vserver': 'svm1',
        'volumes': [
            {
                'name': 'test_vol2',
                'provisioning_options': {
                    'action': 'add'
                }
            }
        ]
    }
    msg = 'Error modifying consistency group test_cg1: calling: '\
          'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_delete_consistency_group():
    ''' Test deleting consistency group with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_info']),
        ('DELETE', 'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['empty_records'])
    ])
    module_args = {
        'state': 'absent',
        'name': 'test_cg1',
        'vserver': 'svm1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_consistency_group_error():
    ''' Test module DELETE method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'application/consistency-groups', SRR['cg_with_single_volume_info']),
        ('DELETE', 'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent',
        'name': 'test_cg1',
        'vserver': 'svm1'
    }
    msg = 'Error deleting consistency group test_cg1: calling: '\
          'application/consistency-groups/faca8bd2-0326-11f1-968d-005056b35ed4: got Expected error.'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_earlier_version():
    ''' Test module supported from 9.10.1 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    assert 'requires ONTAP 9.10.1 or later' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


def test_missing_option():
    ''' Test error missing options '''
    register_responses([

    ])
    DEFAULT_ARGS.pop('name')
    msg = 'missing required arguments: name'
    assert msg in create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
