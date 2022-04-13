# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_snapshot_policy """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapshot_policy \
    import NetAppOntapSnapshotPolicy as my_module

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

SRR = rest_responses({
    'snapshot_record': (200, {"records": [
        {
            "svm": {
                "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                "name": "ansibleSVM"
            },
            "comment": "modified comment",
            "enabled": True,
            "name": "policy_name",
            "copies": [
                {
                    "count": 10,
                    "schedule": {
                        "name": "hourly"
                    },
                    "prefix": 'hourly',
                    "snapmirror_label": ''
                },
                {
                    "count": 30,
                    "schedule": {
                        "name": "weekly"
                    },
                    "prefix": 'weekly',
                    "snapmirror_label": ''
                }
            ],
            "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
        }
    ],
        "num_records": 1
    }, None),
    'schedule_record': (200, {"records": [
        {
            "svm": {
                "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                "name": "ansibleSVM"
            },
            "comment": "modified comment",
            "enabled": 'true',
            "name": "policy_name",
            "count": 10,
            "prefix": "hourly",
            "snapmirror_label": '',
            "schedule": {
                    "name": "hourly",
                    "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa"
            },
            "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
        },
        {
            "svm": {
                "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                "name": "ansibleSVM"
            },
            "comment": "modified comment",
            "enabled": 'true',
            "name": "policy_name",
            "count": 30,
            "prefix": "weekly",
            "snapmirror_label": '',
            "schedule": {
                    "name": "weekly",
                    "uuid": "671aa46e-11ad-11ec-a267-005056b30dsa"
            },
            "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
        }
    ], "num_records": 2}, None),
})


ARGS_REST = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'policy_name',
    'vserver': 'ansibleSVM',
    'enabled': True,
    'count': [10, 30],
    'schedule': "hourly,weekly",
    'comment': 'modified comment',
    'use_rest': 'always'
}

ARGS_REST_no_SVM = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'policy_name',
    'enabled': True,
    'count': [10, 30],
    'schedule': "hourly,weekly",
    'comment': 'modified comment',
    'use_rest': 'always'
}


def test_error_get_snapshot_policy_rest():
    ''' Test get error with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on fetching snapshot policy:' in error


def test_error_get_snapshot_schedule_rest():
    ''' Test get error with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('PATCH', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['empty_good']),
        ('GET', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['generic_error'])
    ])
    module_args = {
        'enabled': False,
        'comment': 'testing policy',
        'name': 'policy2'
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on fetching snapshot schedule:' in error


def test_module_error_ontap_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])
    ])
    module_args = {'use_rest': 'always'}
    msg = create_module(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error: REST requires ONTAP 9.8 or later for snapshot schedules.' == msg


def test_create_snapshot_polciy_rest():
    ''' Test create with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['empty_records']),
        ('POST', 'storage/snapshot-policies', SRR['empty_good']),
    ])
    assert create_and_apply(my_module, ARGS_REST)


def test_create_snapshot_polciy_with_snapmirror_label_rest():
    ''' Test create with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['empty_records']),
        ('POST', 'storage/snapshot-policies', SRR['empty_good']),
    ])
    module_args = {
        "snapmirror_label": ['hourly', 'weekly']
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_create_snapshot_polciy_with_prefix_rest():
    ''' Test create with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['empty_records']),
        ('POST', 'storage/snapshot-policies', SRR['empty_good']),
    ])
    module_args = {
        "prefix": ['', '']
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_error_create_snapshot_polciy_rest():
    ''' Test error create with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['empty_records']),
        ('POST', 'storage/snapshot-policies', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on creating snapshot policy:' in error


def test_delete_snapshot_policy_rest():
    ''' Test delete with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('DELETE', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['empty_good']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_error_delete_snapshot_policy_rest():
    ''' Test error delete with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('DELETE', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent'
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on deleting snapshot policy:' in error


def test_modify_snapshot_policy_rest():
    ''' Test modify comment, rename and disable policy with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('PATCH', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['empty_good']),
        ('GET', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['schedule_record'])
    ])
    module_args = {
        'enabled': False,
        'comment': 'testing policy',
        'name': 'policy2'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_error_modify_snapshot_policy_rest():
    ''' Neagtive test - modify snapshot policy with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('PATCH', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['generic_error']),
    ])
    module_args = {
        'enabled': 'no'
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on modifying snapshot policy:' in error


def test_modify_snapshot_schedule_rest():
    ''' Test modify snapshot schedule and disable policy with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('PATCH', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['empty_good']),
        ('GET', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['schedule_record']),
        ('PATCH', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules/671aa46e-11ad-11ec-a267-005056b30dsa', SRR['empty_good'])
    ])
    module_args = {
        "enabled": False,
        "count": ['10', '20'],
        "schedule": ['hourly', 'weekly']
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_modify_snapshot_schedule_count_label_rest():
    ''' Test modify snapmirror_label and count with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('GET', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['schedule_record']),
        ('PATCH', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules/671aa46e-11ad-11ec-a267-005056b30dsa', SRR['empty_good'])
    ])
    module_args = {
        "snapmirror_label": ['', 'weekly'],
        "count": [10, 20],
        "schedule": ['hourly', 'weekly']
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_modify_snapshot_schedule_count_rest():
    ''' Test modify snapshot count with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('GET', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['schedule_record']),
        ('PATCH', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules/671aa46e-11ad-11ec-a267-005056b30dsa', SRR['empty_good'])
    ])
    module_args = {
        "count": "10,40",
        "schedule": ['hourly', 'weekly'],
        "snapmirror_label": ['', '']
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_modify_snapshot_count_rest():
    ''' Test modify snapshot count, snapmirror_label and prefix with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('GET', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['schedule_record']),
        ('PATCH', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good'])
    ])
    module_args = {
        "count": "20,30",
        "schedule": ['hourly', 'weekly'],
        "snapmirror_label": ['hourly', ''],
        "prefix": ['', 'weekly']
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_delete_snapshot_schedule_rest():
    ''' Test delete snapshot schedule with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('GET', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['schedule_record']),
        ('DELETE', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good'])
    ])
    module_args = {
        "count": 30,
        "schedule": ['weekly']
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_delete_all_snapshot_schedule_rest():
    ''' Validate deleting all snapshot schedule with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record'])
    ])
    module_args = {
        "count": [],
        "schedule": []
    }
    msg = 'Error: A Snapshot policy must have at least 1 ' \
        'schedule and can have up to a maximum of 5 schedules, with a count ' \
        'representing the maximum number of Snapshot copies for each schedule'
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert msg in error


def test_add_snapshot_schedule_rest():
    ''' Test modify by adding schedule to a snapshot with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record']),
        ('GET', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['schedule_record']),
        ('POST', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['empty_good']),
        ('POST', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['success']),
        ('POST', 'storage/snapshot-policies/1cd8a442-86d1-11e0-ae1c-123478563412/schedules', SRR['success'])
    ])
    module_args = {
        "count": "10,30,20,1,2",
        "schedule": ['hourly', 'weekly', 'daily', 'monthly', '5min'],
        "snapmirror_label": ['', '', '', '', '']}
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_add_max_snapshot_schedule_rest():
    ''' Test modify by adding more than maximum number of schedule to a snapshot with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/snapshot-policies', SRR['snapshot_record'])
    ])
    module_args = {
        "count": "10,30,20,1,2,3",
        "schedule": ['hourly', 'weekly', 'daily', 'monthly', '5min', '10min'],
        "snapmirror_label": ['', '', '', '', '', '']}
    msg = 'Error: A Snapshot policy must have at least 1 ' \
        'schedule and can have up to a maximum of 5 schedules, with a count ' \
        'representing the maximum number of Snapshot copies for each schedule'
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert msg in error


def test_invalid_count_rest():
    ''' Test invalid count for a schedule with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    current = {
        'schedule': 'weekly',
        'count': []}
    my_module_object = create_module(my_module, ARGS_REST, current)
    msg = 'Error: A Snapshot policy must have at least 1 ' \
        'schedule and can have up to a maximum of 5 schedules, with a count ' \
        'representing the maximum number of Snapshot copies for each schedule'
    assert msg in expect_and_capture_ansible_exception(my_module_object.validate_parameters, 'fail')['msg']


def test_validate_schedule_count_with_snapmirror_labels_rest():
    ''' validate when schedule has same number of elements with snapmirror labels with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    current = {
        'schedule': ['hourly', 'daily', 'weekly', 'monthly', '5min'],
        'snapmirror_label': ['', '', ''],
        'count': [1, 2, 3, 4, 5]}
    my_module_object = create_module(my_module, ARGS_REST, current)
    msg = "Error: Each Snapshot Policy schedule must have an accompanying SnapMirror Label"
    assert msg in expect_and_capture_ansible_exception(my_module_object.validate_parameters, 'fail')['msg']


def test_validate_schedule_count_with_prefix_rest():
    ''' validate when schedule has same number of elements with prefix with rest API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    current = {
        'schedule': ['hourly', 'daily', 'weekly', 'monthly', '5min'],
        'prefix': ['hourly', 'daily', 'weekly'],
        'count': [1, 2, 3, 4, 5]}
    my_module_object = create_module(my_module, ARGS_REST, current)
    msg = "Error: Each Snapshot Policy schedule must have an accompanying prefix"
    assert msg in expect_and_capture_ansible_exception(my_module_object.validate_parameters, 'fail')['msg']


def test_validate_schedule_count_max_rest():
    ''' Validate maximum number of snapshot schedule and count with REST API '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    current = {
        'schedule': ['hourly', 'daily', 'weekly', 'monthly', '5min', '10min'],
        'count': [1, 2, 3, 4, 5, 6]}
    my_module_object = create_module(my_module, ARGS_REST, current)
    msg = 'Error: A Snapshot policy must have at least 1 ' \
        'schedule and can have up to a maximum of 5 schedules, with a count ' \
        'representing the maximum number of Snapshot copies for each schedule'
    assert msg in expect_and_capture_ansible_exception(my_module_object.validate_parameters, 'fail')['msg']


def test_invalid_count_number_rest():
    '''  validate when schedule has same number of elements with count with rest API  '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    current = {
        'schedule': ['hourly', 'daily', 'weekly'],
        'count': [1, 2, 3, 4, 5, 6]
    }
    my_module_object = create_module(my_module, ARGS_REST, current)
    msg = 'Error: A Snapshot policy must have at least 1 ' \
        'schedule and can have up to a maximum of 5 schedules, with a count ' \
        'representing the maximum number of Snapshot copies for each schedule'
    assert msg in expect_and_capture_ansible_exception(my_module_object.validate_parameters, 'fail')['msg']


def test_invalid_schedule_count_rest():
    '''  validate invalid number of schedule and count with rest API  '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    current = {
        'schedule': [],
        'count': []}
    my_module_object = create_module(my_module, ARGS_REST, current)
    msg = 'Error: A Snapshot policy must have at least 1 ' \
        'schedule and can have up to a maximum of 5 schedules, with a count ' \
        'representing the maximum number of Snapshot copies for each schedule'
    assert msg in expect_and_capture_ansible_exception(my_module_object.validate_parameters, 'fail')['msg']
