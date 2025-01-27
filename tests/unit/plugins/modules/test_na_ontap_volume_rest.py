# (c) 2020-2024, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import copy
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_no_warnings, assert_warning_was_raised, print_warnings, call_main, create_and_apply, \
    create_module, expect_and_capture_ansible_exception, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume \
    import NetAppOntapVolume as volume_module, main as my_main      # module under test

# needed for get and modify/delete as they still use ZAPI
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


volume_info = {
    "uuid": "7882901a-1aef-11ec-a267-005056b30cfa",
    "comment": "carchi8py",
    "name": "test_svm",
    "state": "online",
    "style": "flexvol",
    "tiering": {
        "policy": "backup",
        "min_cooling_days": 0
    },
    "type": "rw",
    "aggregates": [
        {
            "name": "aggr1",
            "uuid": "aggr1_uuid"
        }
    ],
    "encryption": {
        "enabled": True
    },
    "efficiency": {
        "compression": "none",
        "policy": {
            "name": "-"
        }
    },
    "files": {
        "maximum": 2000
    },
    "nas": {
        "gid": 0,
        "security_style": "unix",
        "uid": 0,
        "unix_permissions": 654,
        "path": '/this/path',
        "export_policy": {
            "name": "default"
        }
    },
    "snapshot_policy": {
        "name": "default",
        "uuid": "0a42a3d9-0c29-11ec-a267-005056b30cfa"
    },
    "space": {
        "logical_space": {
            "enforcement": False,
            "reporting": False,
        },
        "size": 10737418240,
        "snapshot": {
            "reserve_percent": 5,
            "autodelete": {
                "enabled": False,
                "trigger": "volume",
                "delete_order": "oldest_first",
                "defer_delete": "user_created",
                "commitment": "try",
                "target_free_space": 20,
                "prefix": "(not specified)"
            }
        }
    },
    "guarantee": {
        "type": "volume"
    },
    "snaplock": {
        "type": "non_snaplock"
    },
    "analytics": {
        "state": "on"
    },
    "access_time_enabled": True,
    "snapshot_directory_access_enabled": True,
    "snapshot_locking_enabled": True
}

volume_info_mount = copy.deepcopy(volume_info)
volume_info_mount['nas']['path'] = ''
del volume_info_mount['nas']['path']
volume_info_encrypt_off = copy.deepcopy(volume_info)
volume_info_encrypt_off['encryption']['enabled'] = False
volume_info_sl_enterprise = copy.deepcopy(volume_info)
volume_info_sl_enterprise['snaplock']['type'] = 'enterprise'
volume_info_sl_enterprise['snaplock']['retention'] = {'default': 'P30Y'}
volume_analytics_disabled = copy.deepcopy(volume_info)
volume_analytics_disabled['analytics']['state'] = 'off'
volume_analytics_initializing = copy.deepcopy(volume_info)
volume_analytics_initializing['analytics']['state'] = 'initializing'
volume_info_offline = copy.deepcopy(volume_info)
volume_info_offline['state'] = 'offline'
volume_info_tags = copy.deepcopy(volume_info)
volume_info_tags['_tags'] = ["team:csi", "environment:test"]

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_rest_96': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy_9_6_0')), None),
    'is_rest_9_8_0': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy_9_8_0')), None),
    'is_rest_9_13_1': (200, dict(version=dict(generation=9, major=13, minor=1, full='dummy_9_13_1')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'no_record': (200, {'num_records': 0, 'records': []}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    # Volume
    'get_volume': (200, {'records': [volume_info]}, None),
    'get_volume_sl_enterprise': (200, {'records': [volume_info_sl_enterprise]}, None),
    'get_volume_mount': (200, {'records': [volume_info_mount]}, None),
    'get_volume_encrypt_off': (200, {'records': [volume_info_encrypt_off]}, None),
    # module specific responses
    'nas_app_record': (200,
                       {'records': [{"uuid": "09e9fd5e-8ebd-11e9-b162-005056b39fe7",
                                     "name": "test_app",
                                     "nas": {
                                         "application_components": [{'xxx': 1}],
                                     }}]}, None),
    'nas_app_record_by_uuid': (200,
                               {"uuid": "09e9fd5e-8ebd-11e9-b162-005056b39fe7",
                                "name": "test_app",
                                "nas": {
                                    "application_components": [{'xxx': 1}],
                                    "flexcache": {
                                        "origin": {'svm': {'name': 'org_name'}}
                                    }
                                }}, None),
    'get_aggr_one_object_store': (200,
                                  {'records': ['one']}, None),
    'get_aggr_two_object_stores': (200,
                                   {'records': ['two']}, None),
    'move_state_replicating': (200, {'movement': {'state': 'replicating'}}, None),
    'move_state_success': (200, {'movement': {'state': 'success'}}, None),
    'encrypting': (200, {'encryption': {'status': {'message': 'initializing'}}}, None),
    'encrypted': (200, {'encryption': {'state': 'encrypted'}}, None),
    'analytics_off': (200, {'records': [volume_analytics_disabled]}, None),
    'analytics_initializing': (200, {'records': [volume_analytics_initializing]}, None),
    'one_svm_record': (200, {'records': [{'uuid': 'svm_uuid'}]}, None),
    'volume_info_offline': (200, {'records': [volume_info_offline]}, None),
    'volume_info_tags': (200, {'records': [volume_info_tags]}, None)
})

DEFAULT_APP_ARGS = {
    'name': 'test_svm',
    'vserver': 'ansibleSVM',
    'nas_application_template': dict(
        tiering=None
    ),
    # 'aggregate_name': 'whatever',       # not used for create when using REST application/applications
    'size': 10,
    'size_unit': 'gb',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always'
}

DEFAULT_VOLUME_ARGS = {
    'name': 'test_svm',
    'vserver': 'ansibleSVM',
    'aggregate_name': 'aggr1',
    'size': 10,
    'size_unit': 'gb',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always'
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    exc = create_module(volume_module, fail=True)
    print('Info: %s' % exc['msg'])
    assert 'missing required arguments:' in exc['msg']


def test_fail_if_aggr_is_set():
    module_args = {'aggregate_name': 'should_fail'}
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    error = 'Conflict: aggregate_name is not supported when application template is enabled.  Found: aggregate_name: should_fail'
    assert create_module(volume_module, DEFAULT_APP_ARGS, module_args, fail=True)['msg'] == error


def test_missing_size():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),           # GET volume
        ('GET', 'svm/svms', SRR['one_svm_record']),             # GET svm
        ('GET', 'application/applications', SRR['no_record']),  # GET application/applications
    ])
    data = dict(DEFAULT_APP_ARGS)
    data.pop('size')
    error = 'Error: "size" is required to create nas application.'
    assert create_and_apply(volume_module, data, fail=True)['msg'] == error


def test_mismatched_tiering_policies():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    module_args = {
        'tiering_policy': 'none',
        'nas_application_template': {'tiering': {'policy': 'auto'}}
    }
    error = 'Conflict: if tiering_policy and nas_application_template tiering policy are both set, they must match.'\
            '  Found "none" and "auto".'
    assert create_module(volume_module, DEFAULT_APP_ARGS, module_args, fail=True)['msg'] == error


def test_rest_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),                   # GET volume
        ('GET', 'svm/svms', SRR['one_svm_record']),                     # GET svm
        ('GET', 'application/applications', SRR['no_record']),          # GET application/applications
        ('POST', 'application/applications', SRR['generic_error']),     # POST application/applications
    ])
    error = 'Error in create_application_template: calling: application/applications: got %s.' % SRR['generic_error'][2]
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, fail=True)['msg'] == error


def test_rest_successfully_created():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),               # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),                 # GET svm
        ('GET', 'application/applications', SRR['no_record']),      # GET application/applications
        ('POST', 'application/applications', SRR['empty_good']),    # POST application/applications
        ('GET', 'storage/volumes', SRR['get_volume']),
    ])
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS)['changed']


def test_rest_create_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),          # Get Volume
        ('GET', 'application/applications', SRR['no_record']),  # GET application/applications

    ])
    assert not create_and_apply(volume_module, DEFAULT_APP_ARGS)['changed']


def test_rest_successfully_created_with_modify():
    ''' since language is not supported in application, the module is expected to:
        1. create the volume using application REST API
        2. immediately modify the volume to update options which are not available in the nas template.
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume
        ('GET', 'application/applications', SRR['no_record']),                                  # GET application/applications
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['empty_good']),   # set unix_permissions
    ])
    module_args = {
        'language': 'fr',
        'unix_permissions': '---rw-r-xr-x'
    }
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']


def test_rest_successfully_resized():
    ''' make sure resize if using RESP API if sizing_method is present
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),              # Get Volume
        ('GET', 'application/applications', SRR['no_record']),      # GET application/applications
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['empty_good']),   # PATCH storage/volumes
    ])
    module_args = {
        'sizing_method': 'add_new_resources',
        'size': 20737418240
    }
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']


def test_rest_volume_create_modify_tags():
    ''' volume create, modify with tags
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_13_1']),
        ('GET', 'storage/volumes', SRR['no_record']),
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('POST', 'storage/volumes', SRR['success']),
        ('GET', 'storage/volumes', SRR['volume_info_tags']),
        # idempotent check
        ('GET', 'cluster', SRR['is_rest_9_13_1']),
        ('GET', 'storage/volumes', SRR['volume_info_tags']),
        # modify tags
        ('GET', 'cluster', SRR['is_rest_9_13_1']),
        ('GET', 'storage/volumes', SRR['volume_info_tags']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['success']),
    ])
    module_args = {'tags': ["team:csi", "environment:test"]}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']
    assert not create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']
    module_args = {'tags': ["team:csi"]}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_deleted():
    ''' delete volume using REST - no app
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),              # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['empty_good']),       # PATCH storage/volumes - unmount
        ('DELETE', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['empty_good']),      # DELETE storage/volumes
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']
    assert_no_warnings()


def test_rest_successfully_deleted_with_warning():
    ''' delete volume using REST - no app - unmount failed
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),              # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),    # PATCH storage/volumes - unmount
        ('DELETE', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['empty_good']),      # DELETE storage/volumes
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised('Volume was successfully deleted though unmount failed with: calling: '
                              'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error.')


def test_rest_successfully_deleted_with_app():
    ''' delete app
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                                      # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['empty_good']),               # PATCH storage/volumes - unmount
        ('DELETE', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['empty_good']),              # DELETE storage/volumes
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']


def test_rest_successfully_move_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # Move volume
    ])
    module_args = {'aggregate_name': 'aggr2'}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_error_move_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                              # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),    # Move volume
    ])
    module_args = {'aggregate_name': 'aggr2'}
    msg = "Error moving volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_error_rehost_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['zero_records']),                                            # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),                                                 # GET svm
    ])
    module_args = {'from_vserver': 'svm_orig'}
    msg = "Error: ONTAP REST API does not support Rehosting Volumes"
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_successfully_volume_unmount_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # Mount Volume
    ])
    module_args = {'junction_path': ''}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_error_volume_unmount_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                              # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),    # Mount Volume
    ])
    module_args = {'junction_path': ''}
    msg = 'Error unmounting volume test_svm with path "": calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error.'
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_successfully_volume_mount_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_mount']),                                    # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # Mount Volume
    ])
    module_args = {'junction_path': '/this/path'}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_volume_mount_do_nothing_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_mount']),                                    # Get Volume
    ])
    module_args = {'junction_path': ''}
    assert not create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_error_volume_mount_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_mount']),                                        # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),    # Mount Volume
    ])
    module_args = {'junction_path': '/this/path'}
    msg = 'Error mounting volume test_svm with path "/this/path": calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error.'
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_successfully_change_volume_state():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['success']),      # Move volume
    ])
    module_args = {'is_online': False}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_error_change_volume_state():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                              # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),    # Move volume
    ])
    module_args = {'is_online': False}
    msg = "Error changing state of volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_successfully_modify_attributes():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # Modify
    ])
    module_args = {
        'space_guarantee': 'volume',
        'percent_snapshot_space': 10,
        'snapshot_policy': 'default2',
        'export_policy': 'default2',
        'group_id': 5,
        'user_id': 5,
        'volume_security_style': 'mixed',
        'comment': 'carchi8py was here',
        'tiering_minimum_cooling_days': 10,
        'logical_space_enforcement': True,
        'logical_space_reporting': True
    }
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_error_modify_attributes():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                              # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),    # Modify
    ])
    module_args = {
        'space_guarantee': 'volume',
        'percent_snapshot_space': 10,
        'snapshot_policy': 'default2',
        'export_policy': 'default2',
        'group_id': 5,
        'user_id': 5,
        'volume_security_style': 'mixed',
        'comment': 'carchi8py was here',
    }
    msg = "Error modifying volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_version_error_with_atime_update():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])
    ])
    module_args = {
        'atime_update': False
    }
    error = create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg']
    assert 'Minimum version of ONTAP for atime_update is (9, 8)' in error


def test_rest_version_error_with_snapdir_access():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1'])
    ])
    module_args = {
        'snapdir_access': False
    }
    error = create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg']
    assert 'Minimum version of ONTAP for snapdir_access is (9, 13, 1)' in error


def test_rest_version_error_with_snapshot_auto_delete():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1'])
    ])
    module_args = {
        'snapshot_auto_delete': {'state': 'on'}
    }
    error = create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg']
    assert 'Minimum version of ONTAP for snapshot_auto_delete is (9, 13, 1)' in error


def test_rest_version_error_with_vol_nearly_full_threshold_percent():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0'])
    ])
    module_args = {
        'vol_nearly_full_threshold_percent': 96
    }
    error = create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg']
    assert 'Minimum version of ONTAP for vol_nearly_full_threshold_percent is (9, 9)' in error


def test_rest_version_error_with_large_size_enabled():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    module_args = {
        'large_size_enabled': False
    }
    error = create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg']
    assert 'Minimum version of ONTAP for large_size_enabled is (9, 12, 1)' in error


def test_rest_version_error_with_snapshot_locking():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0'])
    ])
    module_args = {
        'snapshot_locking': False
    }
    error = create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg']
    print('error', error)
    assert 'Minimum version of ONTAP for snapshot_locking is (9, 12, 1)' in error


def test_rest_version_error_with_activity_tracking():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0'])
    ])
    module_args = {
        'activity_tracking': 'on'
    }
    error = create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg']
    assert 'Minimum version of ONTAP for activity_tracking is (9, 10, 1)' in error


def test_rest_successfully_modify_attributes_atime_update():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # Modify
    ])
    module_args = {
        'atime_update': False,
    }
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_modify_attributes_snapdir_access_and_snapshot_auto_delete():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_13_1']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # Modify
    ])
    module_args = {
        'snapdir_access': False,
        'snapshot_auto_delete': {
            'state': 'on',
            'trigger': 'volume',
            'delete_order': 'oldest_first',
            'defer_delete': 'user_created',
            'commitment': 'try',
            'target_free_space': 25,
            'prefix': 'prefix1'
        }
    }
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_modify_vol_threshold_percent_params():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # Modify
    ])
    module_args = {
        'vol_nearly_full_threshold_percent': 98,
        'vol_full_threshold_percent': 99
    }
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_modify_large_size_enabled():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # Modify
    ])
    module_args = {
        'large_size_enabled': False
    }
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_create_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),   # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),     # GET svm
        ('POST', 'storage/volumes', SRR['no_record']),  # Create Volume
        ('GET', 'storage/volumes', SRR['get_volume']),
    ])
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS)['changed']


def test_rest_error_get_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['generic_error']),  # Get Volume
    ])
    msg = "calling: storage/volumes: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, fail=True)['msg'] == msg


def test_rest_error_create_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),       # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),         # GET svm
        ('POST', 'storage/volumes', SRR['generic_error']),  # Create Volume
    ])
    msg = "Error creating volume test_svm: calling: storage/volumes: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, fail=True)['msg'] == msg


def test_rest_successfully_create_volume_with_options():
    module_args = {
        'space_guarantee': 'volume',
        'percent_snapshot_space': 5,
        'snapshot_policy': 'default',
        'export_policy': 'default',
        'group_id': 0,
        'user_id': 0,
        'volume_security_style': 'unix',
        'comment': 'carchi8py',
        'type': 'RW',
        'language': 'en',
        'encrypt': True,
        'junction_path': '/this/path',
        'tiering_policy': 'backup',
        'tiering_minimum_cooling_days': 10,
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),   # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),     # GET svm
        ('POST', 'storage/volumes', SRR['no_record']),  # Create Volume
        ('GET', 'storage/volumes', SRR['get_volume']),
        # TODO - force a patch after create
        # ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),  # modify Volume
    ])
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS)['changed']


def test_rest_successfully_snapshot_restore_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),  # Get Volume
        ('GET', 'storage/volumes', SRR['get_volume']),  # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),  # Modify Snapshot restore
    ])
    module_args = {'snapshot_restore': 'snapshot_copy'}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_error_snapshot_restore_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),  # Get Volume
        ('GET', 'storage/volumes', SRR['get_volume']),  # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),  # Modify Snapshot restore
    ])
    module_args = {'snapshot_restore': 'snapshot_copy'}
    msg = "Error restoring snapshot snapshot_copy in volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_error_snapshot_restore_volume_no_parent():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['zero_records']),    # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),         # GET svm
    ])
    module_args = {'snapshot_restore': 'snapshot_copy'}
    msg = "Error restoring volume: cannot find parent: test_svm"
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_successfully_rename_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),                                           # Get Volume name
        ('GET', 'svm/svms', SRR['one_svm_record']),                                             # GET svm
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume from
        ('GET', 'storage/volumes', SRR['get_volume']),                                          # Get Volume from
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # Patch
    ])
    module_args = {
        'from_name': 'test_svm',
        'name': 'new_name'
    }
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_error_rename_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),                                               # Get Volume name
        ('GET', 'svm/svms', SRR['one_svm_record']),                                                 # GET svm
        ('GET', 'storage/volumes', SRR['get_volume']),                                              # Get Volume from
        ('GET', 'storage/volumes', SRR['get_volume']),                                              # Get Volume from
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),    # Patch
    ])
    module_args = {
        'from_name': 'test_svm',
        'name': 'new_name'
    }
    msg = "Error changing name of volume new_name: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_error_resizing_volume():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),                                              # Get Volume name
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),    # Resize volume
    ])
    module_args = {
        'sizing_method': 'add_new_resources',
        'size': 20737418240
    }
    msg = "Error resizing volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_successfully_create_volume_with_unix_permissions():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),   # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),     # GET svm
        ('POST', 'storage/volumes', SRR['no_record']),  # Create Volume
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),  # add unix permissions
    ])
    module_args = {'unix_permissions': '---rw-r-xr-x'}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_create_volume_with_qos_policy():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),                                           # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),                                             # GET svm
        ('POST', 'storage/volumes', SRR['no_record']),                                          # Create Volume
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # Set policy name
    ])
    module_args = {'qos_policy_group': 'policy-name'}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_create_volume_with_qos_adaptive_policy_group():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),   # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),     # GET svm
        ('POST', 'storage/volumes', SRR['no_record']),  # Create Volume
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),  # Set policy name
    ])
    module_args = {'qos_adaptive_policy_group': 'policy-name'}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_create_volume_with_qos_adaptive_policy_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    module_args = {
        'qos_adaptive_policy_group': 'policy-name',
        'qos_policy_group': 'policy-name'
    }
    msg = "Error: With Rest API qos_policy_group and qos_adaptive_policy_group are now the same thing, and cannot be set at the same time"
    assert create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_successfully_create_volume_with_tiering_policy():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),   # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),     # GET svm
        ('POST', 'storage/volumes', SRR['no_record']),  # Create Volume
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),  # Set Tiering_policy
    ])
    module_args = {'tiering_policy': 'all'}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_create_volume_encrypt():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),   # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),     # GET svm
        ('POST', 'storage/volumes', SRR['no_record']),  # Create Volume
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),  # Set Encryption
    ])
    module_args = {'encrypt': False}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


@patch('time.sleep')
def test_rest_successfully_modify_volume_encrypt(sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_encrypt_off']),  # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),  # Set Encryption
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_encrypt_off']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),
        ('GET', 'storage/volumes', SRR['encrypting']),
        ('GET', 'storage/volumes', SRR['encrypting']),
        ('GET', 'storage/volumes', SRR['encrypting']),
        ('GET', 'storage/volumes', SRR['encrypted']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_encrypt_off']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),
        ('GET', 'storage/volumes', SRR['generic_error']),
        ('GET', 'storage/volumes', SRR['generic_error']),
        ('GET', 'storage/volumes', SRR['generic_error']),
        ('GET', 'storage/volumes', SRR['generic_error']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume'])
    ])
    module_args = {'encrypt': True}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']
    module_args = {'encrypt': True, 'wait_for_completion': True}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']
    error = 'Error getting volume encryption_conversion status'
    assert error in create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg']
    error = 'unencrypting volume is only supported when moving the volume to another aggregate in REST'
    assert error in create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, {'encrypt': False}, fail=True)['msg']


def test_rest_error_modify_volume_encrypt():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_encrypt_off']),  # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),  # Set Encryption
    ])
    module_args = {'encrypt': True}
    msg = "Error enabling encryption for volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_successfully_modify_volume_compression():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_encrypt_off']),  # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),  # compression
    ])
    module_args = {
        'efficiency_policy': 'test',
        'compression': True
    }
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_successfully_modify_volume_inline_compression():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_encrypt_off']),  # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),  # compression
    ])
    module_args = {
        'efficiency_policy': 'test',
        'inline_compression': True
    }
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_error_modify_volume_efficiency_policy():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_encrypt_off']),                                  # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),    # Set Encryption
    ])
    module_args = {'efficiency_policy': 'test'}
    msg = "Error setting efficiency for volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_error_volume_compression_both():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume_encrypt_off']),  # Get Volume
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['generic_error']),  # Set Encryption
    ])
    module_args = {
        'compression': True,
        'inline_compression': True
    }
    msg = "Error setting efficiency for volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_error_modify_volume_efficiency_policy_with_ontap_96():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    module_args = {'efficiency_policy': 'test'}
    msg = "Error: Minimum version of ONTAP for efficiency_policy is (9, 7)."
    assert msg in create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg']


def test_rest_error_modify_volume_tiering_minimum_cooling_days_98():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    module_args = {'tiering_minimum_cooling_days': 2}
    msg = "Error: Minimum version of ONTAP for tiering_minimum_cooling_days is (9, 8)."
    assert msg in create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg']


def test_rest_successfully_created_with_logical_space():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),   # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),     # GET svm
        ('POST', 'storage/volumes', SRR['no_record']),  # Create Volume
        ('GET', 'storage/volumes', SRR['get_volume']),
    ])
    module_args = {
        'logical_space_enforcement': False,
        'logical_space_reporting': False
    }
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_rest_error_modify_backend_fabricpool():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('GET', 'storage/aggregates/aggr1_uuid/cloud-stores', SRR['no_record']),       # get_aggr_object_stores
    ])
    module_args = {
        'nas_application_template': {'tiering': {'control': 'required'}},
        'feature_flags': {'warn_or_fail_on_fabricpool_backend_change': 'fail'}
    }

    msg = "Error: changing a volume from one backend to another is not allowed.  Current tiering control: disallowed, desired: required."
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args, fail=True)['msg'] == msg

    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('GET', 'application/applications', SRR['no_record']),   # TODO: modify
    ])
    module_args['feature_flags'] = {'warn_or_fail_on_fabricpool_backend_change': 'invalid'}
    assert not create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']
    print_warnings()
    warning = "Unexpected value 'invalid' for warn_or_fail_on_fabricpool_backend_change, expecting: None, 'ignore', 'fail', 'warn'"
    assert_warning_was_raised(warning)

    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('GET', 'storage/aggregates/aggr1_uuid/cloud-stores', SRR['no_record']),   # get_aggr_object_stores
        ('GET', 'application/applications', SRR['no_record']),   # TODO: modify
    ])
    module_args['feature_flags'] = {'warn_or_fail_on_fabricpool_backend_change': 'warn'}
    assert not create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']
    warning = "Ignored %s" % msg
    print_warnings()
    assert_warning_was_raised(warning)


def test_rest_negative_modify_backend_fabricpool():
    ''' fail to get aggregate object store'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('GET', 'storage/aggregates/aggr1_uuid/cloud-stores', SRR['generic_error']),
    ])
    module_args = {
        'nas_application_template': {'tiering': {'control': 'required'}},
        'feature_flags': {'warn_or_fail_on_fabricpool_backend_change': 'fail'}
    }
    msg = "Error getting object store for aggregate: aggr1: calling: storage/aggregates/aggr1_uuid/cloud-stores: got Expected error."
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_tiering_control():
    ''' The volume is supported by one or more aggregates
        If all aggregates are associated with one or more object stores, the volume has a FabricPool backend.
        If all aggregates are not associated with one or more object stores, the volume meets the 'disallowed' criteria.
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates/uuid1/cloud-stores', SRR['no_record']),                   # get_aggr_object_stores aggr1
        ('GET', 'storage/aggregates/uuid2/cloud-stores', SRR['no_record']),                   # get_aggr_object_stores aggr2
        ('GET', 'storage/aggregates/uuid1/cloud-stores', SRR['get_aggr_one_object_store']),   # get_aggr_object_stores aggr1
        ('GET', 'storage/aggregates/uuid2/cloud-stores', SRR['no_record']),                   # get_aggr_object_stores aggr2
        ('GET', 'storage/aggregates/uuid1/cloud-stores', SRR['get_aggr_two_object_stores']),  # get_aggr_object_stores aggr1
        ('GET', 'storage/aggregates/uuid2/cloud-stores', SRR['get_aggr_one_object_store']),   # get_aggr_object_stores aggr2
    ])
    module_args = {
        'nas_application_template': {'tiering': {'control': 'required'}},
        'feature_flags': {'warn_or_fail_on_fabricpool_backend_change': 'fail'}
    }
    current = {'aggregates': [{'name': 'aggr1', 'uuid': 'uuid1'}, {'name': 'aggr2', 'uuid': 'uuid2'}]}
    vol_object = create_module(volume_module, DEFAULT_APP_ARGS, module_args)
    result = vol_object.tiering_control(current)
    assert result == 'disallowed'
    result = vol_object.tiering_control(current)
    assert result == 'best_effort'
    result = vol_object.tiering_control(current)
    assert result == 'required'
    current = {'aggregates': []}
    result = vol_object.tiering_control(current)
    assert result is None


def test_error_snaplock_volume_create_sl_type_not_changed():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('POST', 'storage/volumes', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['get_volume']),
    ])
    module_args = {'snaplock': {'type': 'enterprise'}}
    error = 'Error: volume snaplock type was not set properly at creation time.  Current: non_snaplock, desired: enterprise.'
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == error


def test_error_snaplock_volume_create_sl_type_not_supported():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('GET', 'svm/svms', SRR['one_svm_record']),
    ])
    module_args = {'snaplock': {'type': 'enterprise'}}
    error = 'Error: using snaplock type requires ONTAP 9.10.1 or later and REST must be enabled - ONTAP version: 9.6.0 - using REST.'
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == error


def test_error_snaplock_volume_create_sl_options_not_supported_when_non_snaplock():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('GET', 'svm/svms', SRR['one_svm_record']),
    ])
    module_args = {'snaplock': {
        'type': 'non_snaplock',
        'retention': {'default': 'P30Y'}
    }}
    error = "Error: snaplock options are not supported for non_snaplock volume, found: {'retention': {'default': 'P30Y'}}."
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == error

    # 'non_snaplock' is the default too
    module_args = {'snaplock': {
        'retention': {'default': 'P30Y'}
    }}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == error


def test_snaplock_volume_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('POST', 'storage/volumes', SRR['empty_records']),
        ('GET', 'storage/volumes', SRR['get_volume_sl_enterprise']),
    ])
    module_args = {'snaplock': {'type': 'enterprise', 'retention': {'maximum': 'P5D'}}}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_error_snaplock_volume_modify_type():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['get_volume_sl_enterprise']),
    ])
    module_args = {'snaplock': {'type': 'compliance'}}
    error = 'Error: changing a volume snaplock type after creation is not allowed.  Current: enterprise, desired: compliance.'
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == error


def test_snaplock_volume_modify_other_options():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['get_volume_sl_enterprise']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['success']),
    ])
    module_args = {'snaplock': {
        'retention': {'default': 'P20Y'}
    }}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_snaplock_volume_modify_other_options_idempotent():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['get_volume_sl_enterprise']),
    ])
    module_args = {'snaplock': {
        'retention': {'default': 'P30Y'}
    }}
    assert not create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


def test_max_files_volume_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['get_volume_sl_enterprise']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['success']),
    ])
    module_args = {'max_files': 3000}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_use_zapi_and_netapp_lib_missing(mock_has_netapp_lib):
    """ZAPI requires netapp_lib"""
    register_responses([
    ])
    mock_has_netapp_lib.return_value = False
    module_args = {'use_rest': 'never'}
    error = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == error


def test_fallback_to_zapi_and_nas_application_is_used():
    """fallback to ZAPI when use_rest: auto and some ZAPI only options are used"""
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    module_args = {'use_rest': 'auto', 'cutover_action': 'wait', 'nas_application_template': {'storage_service': 'value'}}
    error = "Error: nas_application_template requires REST support.  use_rest: auto.  "\
            "Conflict because of unsupported option(s) or option value(s) in REST: ['cutover_action']."
    assert create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == error
    assert_warning_was_raised("Falling back to ZAPI because of unsupported option(s) or option value(s) in REST: ['cutover_action']")


def test_fallback_to_zapi_and_rest_option_is_used():
    """fallback to ZAPI when use_rest: auto and some ZAPI only options are used"""
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    module_args = {'use_rest': 'auto', 'cutover_action': 'wait', 'sizing_method': 'use_existing_resources'}
    error = "Error: sizing_method option is not supported with ZAPI.  It can only be used with REST.  use_rest: auto.  "\
            "Conflict because of unsupported option(s) or option value(s) in REST: ['cutover_action']."
    assert create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args, fail=True)['msg'] == error
    assert_warning_was_raised("Falling back to ZAPI because of unsupported option(s) or option value(s) in REST: ['cutover_action']")


def test_error_conflict_export_policy_and_nfs_access():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    module_args = {
        'export_policy': 'auto',
        'nas_application_template': {
            'tiering': None,
            'nfs_access': [{'access': 'ro'}]
        },
        'tiering_policy': 'backup'
    }
    error = 'Conflict: export_policy option and nfs_access suboption in nas_application_template are mutually exclusive.'
    assert create_module(volume_module, DEFAULT_APP_ARGS, module_args, fail=True)['msg'] == error


def test_create_nas_app_nfs_access():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['no_record']),               # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('GET', 'application/applications', SRR['no_record']),      # GET application/applications
        ('POST', 'application/applications', SRR['empty_good']),    # POST application/applications
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['get_volume']),
    ])
    module_args = {
        'nas_application_template': {
            'exclude_aggregates': ['aggr_ex'],
            'nfs_access': [{'access': 'ro'}],
            'tiering': None,
        },
        'snapshot_policy': 'snspol'
    }
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']


def test_create_nas_app_tiering_object_store():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['no_record']),               # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('GET', 'application/applications', SRR['no_record']),      # GET application/applications
        ('POST', 'application/applications', SRR['empty_good']),    # POST application/applications
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('GET', 'storage/aggregates/aggr1_uuid/cloud-stores', SRR['get_aggr_one_object_store']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['get_volume']),
    ])
    module_args = {
        'nas_application_template': {
            'flexcache': {
                'dr_cache': True,
                'origin_component_name': 'ocn',
                'origin_svm_name': 'osn',
            },
            'storage_service': 'extreme',
            'tiering': {
                'control': 'required',
                'object_stores': ['obs1']
            },
        },
        'export_policy': 'exppol',
        'qos_policy_group': 'qospol',
        'snapshot_policy': 'snspol'
    }
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']


def test_create_nas_app_tiering_policy_flexcache():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['no_record']),               # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('GET', 'application/applications', SRR['no_record']),      # GET application/applications
        ('POST', 'application/applications', SRR['empty_good']),    # POST application/applications
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['get_volume']),
    ])
    module_args = {
        'nas_application_template': {
            'flexcache': {
                'dr_cache': True,
                'origin_component_name': 'ocn',
                'origin_svm_name': 'osn',
            },
            'storage_service': 'extreme',
        },
        'qos_policy_group': 'qospol',
        'snapshot_policy': 'snspol',
        'tiering_policy': 'snapshot-only',
    }
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']


def test_create_nas_app_tiering_flexcache():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['no_record']),               # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('GET', 'application/applications', SRR['no_record']),      # GET application/applications
        ('POST', 'application/applications', SRR['empty_good']),    # POST application/applications
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['get_volume']),
    ])
    module_args = {
        'nas_application_template': {
            'flexcache': {
                'dr_cache': True,
                'origin_component_name': 'ocn',
                'origin_svm_name': 'osn',
            },
            'storage_service': 'extreme',
            'tiering': {
                'control': 'best_effort'
            },
        },
        'qos_policy_group': 'qospol',
        'snapshot_policy': 'snspol'
    }
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']


def test_create_nas_app_cifs_options():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
        ('GET', 'storage/volumes', SRR['no_record']),               # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('GET', 'application/applications', SRR['no_record']),      # GET application/applications
        ('POST', 'application/applications', SRR['empty_good']),    # POST application/applications
        ('GET', 'storage/volumes', SRR['get_volume']),
    ])
    module_args = {
        'nas_application_template': {
            'cifs_access': [
                {
                    'access': 'read'
                }
            ],
            'cifs_share_name': 'test_share',
            'exclude_aggregates': ['aggr_ex'],
        }
    }
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']


def test_version_error_nas_app():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    module_args = {
        'nas_application_template': {
            'flexcache': {
                'dr_cache': True,
                'origin_component_name': 'ocn',
                'origin_svm_name': 'osn',
            },
        },
    }
    error = 'Error: using nas_application_template requires ONTAP 9.7 or later and REST must be enabled - ONTAP version: 9.6.0.'
    assert create_module(volume_module, DEFAULT_APP_ARGS, module_args, fail=True)['msg'] == error


def test_version_error_nas_app_dr_cache():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'nas_application_template': {
            'flexcache': {
                'dr_cache': True,
                'origin_component_name': 'ocn',
                'origin_svm_name': 'osn',
            },
        },
    }
    error = 'Error: using flexcache: dr_cache requires ONTAP 9.9 or later and REST must be enabled - ONTAP version: 9.8.0.'
    assert create_module(volume_module, DEFAULT_APP_ARGS, module_args, fail=True)['msg'] == error


def test_version_error_nas_app_cifs_share_name():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'nas_application_template': {
            'cifs_share_name': 'test_share2',
            'cifs_access': [{'access': 'read'}]
        }
    }
    error = 'Error: using nas_application_template: cifs_share_name requires ONTAP 9.11 or later and REST must be enabled - ONTAP version: 9.7.0.'
    assert create_module(volume_module, DEFAULT_APP_ARGS, module_args, fail=True)['msg'] == error


def test_error_volume_rest_patch():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    my_obj = create_module(volume_module, DEFAULT_APP_ARGS)
    my_obj.parameters['uuid'] = None
    error = 'Could not read UUID for volume test_svm in patch.'
    assert expect_and_capture_ansible_exception(my_obj.volume_rest_patch, 'fail', {})['msg'] == error


def test_error_volume_rest_delete():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    my_obj = create_module(volume_module, DEFAULT_APP_ARGS)
    my_obj.parameters['uuid'] = None
    error = 'Could not read UUID for volume test_svm in delete.'
    assert expect_and_capture_ansible_exception(my_obj.rest_delete_volume, 'fail', '')['msg'] == error


def test_error_modify_app_not_supported_no_volume_but_app():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['no_record']),
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('GET', 'application/applications', SRR['nas_app_record']),
        ('GET', 'application/applications/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['nas_app_record_by_uuid']),
    ])
    module_args = {}
    # TODO: we need to handle this error case with a better error mssage
    error = 'Error in create_application_template: function create_application should not be called when application uuid is set: '
    error += '09e9fd5e-8ebd-11e9-b162-005056b39fe7.'
    assert create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args, fail=True)['msg'] == error


def test_warning_modify_app_not_supported():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('GET', 'application/applications', SRR['nas_app_record']),
        ('GET', 'application/applications/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['nas_app_record_by_uuid']),
    ])
    module_args = {
        'nas_application_template': {
            'flexcache': {
                'dr_cache': True,
                'origin_component_name': 'ocn',
                'origin_svm_name': 'osn',
            },
        },
    }
    assert not create_and_apply(volume_module, DEFAULT_APP_ARGS, module_args)['changed']
    assert_warning_was_raised("Modifying an app is not supported at present: ignoring: {'flexcache': {'origin': {'svm': {'name': 'osn'}}}}")


def test_create_flexgroup_volume_from_main():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),   # Get Volume
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('POST', 'storage/volumes', SRR['no_record']),  # Create Volume
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # eff policy
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # modify
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['no_record']),    # offline
    ])
    args = copy.deepcopy(DEFAULT_VOLUME_ARGS)
    del args['aggregate_name']
    module_args = {
        'aggr_list': 'aggr_0,aggr_1',
        'aggr_list_multiplier': 2,
        'comment': 'some comment',
        'compression': False,
        'efficiency_policy': 'effpol',
        'export_policy': 'exppol',
        'group_id': 1001,
        'junction_path': '/this/path',
        'inline_compression': False,
        'is_online': False,
        'language': 'us',
        'percent_snapshot_space': 10,
        'snapshot_policy': 'snspol',
        'space_guarantee': 'file',
        'tiering_minimum_cooling_days': 30,
        'tiering_policy': 'snapshot-only',
        'type': 'rw',
        'user_id': 123,
        'volume_security_style': 'unix',
    }
    assert call_main(my_main, args, module_args)['changed']


def test_get_volume_style():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    args = copy.deepcopy(DEFAULT_VOLUME_ARGS)
    del args['aggregate_name']
    module_args = {
        'auto_provision_as': 'flexgroup',
    }
    my_obj = create_module(volume_module, args, module_args)
    assert my_obj.get_volume_style(None) == 'flexgroup'
    assert my_obj.parameters.get('aggr_list_multiplier') == 1


def test_move_volume_with_rest_passthrough():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('PATCH', 'private/cli/volume/move/start', SRR['success']),
        ('PATCH', 'private/cli/volume/move/start', SRR['generic_error']),
    ])
    module_args = {
        'aggregate_name': 'aggr2'
    }
    obj = create_module(volume_module, DEFAULT_VOLUME_ARGS, module_args)
    error = obj.move_volume_with_rest_passthrough(True)
    assert error is None
    error = obj.move_volume_with_rest_passthrough(True)
    assert 'Expected error' in error


def test_ignore_small_change():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    obj = create_module(volume_module, DEFAULT_VOLUME_ARGS)
    obj.parameters['attribute'] = 51
    assert obj.ignore_small_change({'attribute': 50}, 'attribute', .5) is None
    assert obj.parameters['attribute'] == 51
    assert_no_warnings()
    obj.parameters['attribute'] = 50.2
    assert obj.ignore_small_change({'attribute': 50}, 'attribute', .5) is None
    assert obj.parameters['attribute'] == 50
    print_warnings()
    assert_warning_was_raised('resize request for attribute ignored: 0.4% is below the threshold: 0.5%')


def test_set_efficiency_rest_empty_body():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    obj = create_module(volume_module, DEFAULT_VOLUME_ARGS)
    # no action
    assert obj.set_efficiency_rest() is None


@patch('time.sleep')
def test_volume_move_rest(sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'storage/volumes', SRR['get_volume_mount']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['success']),
        ('GET', 'storage/volumes', SRR['move_state_replicating']),
        ('GET', 'storage/volumes', SRR['move_state_success']),
        # error when trying to get volume status
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'storage/volumes', SRR['get_volume_mount']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['success']),
        ('GET', 'storage/volumes', SRR['generic_error']),
        ('GET', 'storage/volumes', SRR['generic_error']),
        ('GET', 'storage/volumes', SRR['generic_error']),
        ('GET', 'storage/volumes', SRR['generic_error'])
    ])
    args = {'aggregate_name': 'aggr2', 'wait_for_completion': True, 'max_wait_time': 280}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, args)['changed']
    error = "Error getting volume move status"
    assert error in create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, args, fail=True)['msg']


def test_analytics_option():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['no_record']),
        ('GET', 'svm/svms', SRR['one_svm_record']),
        ('POST', 'storage/volumes', SRR['success']),
        ('GET', 'storage/volumes', SRR['get_volume']),
        # idempotency check
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),
        # Disable analytics
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_volume']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['success']),
        # Enable analytics
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['analytics_off']),
        ('PATCH', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa', SRR['success']),
        # Try to Enable analytics which is initializing(no change required.)
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['analytics_initializing'])
    ])
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, {'analytics': 'on'})['changed']
    assert not create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, {'analytics': 'on'})['changed']
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, {'analytics': 'off'})['changed']
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, {'analytics': 'on'})['changed']
    assert not create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, {'analytics': 'on'})['changed']


def test_warn_rest_modify():
    """ Test skip snapshot_restore and modify when volume is offline """
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['volume_info_offline'])
    ])
    args = {'is_online': False, 'junction_path': '/test', 'use_rest': 'always', 'snapshot_restore': 'restore1'}
    assert create_and_apply(volume_module, DEFAULT_VOLUME_ARGS, args)['changed'] is False
    assert_warning_was_raised("Cannot perform action(s): ['snapshot_restore'] and modify: ['junction_path']", partial_match=True)
