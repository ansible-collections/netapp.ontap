# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_aggregate """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses, build_zapi_error

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_aggregate \
    import NetAppOntapAggregate as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


AGGR_NAME = 'aggr_name'
OS_NAME = 'abc'

aggr_info = {'num-records': 3,
             'attributes-list':
                 {'aggr-attributes':
                     {'aggregate-name': AGGR_NAME,
                      'aggr-raid-attributes': {
                          'state': 'online',
                          'disk-count': '4',
                          'encrypt-with-aggr-key': 'true'},
                      'aggr-snaplock-attributes': {'snaplock-type': 'snap_t'}}
                  },
             }

object_store_info = {'num-records': 1,
                     'attributes-list':
                         {'object-store-information': {'object-store-name': OS_NAME}}
                     }

disk_info = {'num-records': 1,
             'attributes-list': [
                 {'disk-info':
                  {'disk-name': '1',
                   'disk-raid-info':
                   {'disk-aggregate-info':
                    {'plex-name': 'plex0'}
                    }}},
                 {'disk-info':
                  {'disk-name': '2',
                   'disk-raid-info':
                   {'disk-aggregate-info':
                    {'plex-name': 'plex0'}
                    }}},
                 {'disk-info':
                  {'disk-name': '3',
                   'disk-raid-info':
                   {'disk-aggregate-info':
                    {'plex-name': 'plexM'}
                    }}},
                 {'disk-info':
                  {'disk-name': '4',
                   'disk-raid-info':
                   {'disk-aggregate-info':
                    {'plex-name': 'plexM'}
                    }}},
             ]}

ZRR = zapi_responses({
    'aggr_info': build_zapi_response(aggr_info),
    'object_store_info': build_zapi_response(object_store_info),
    'disk_info': build_zapi_response(disk_info),
    'error_disk_add': build_zapi_error(13003, 'disk add operation is in progress'),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': AGGR_NAME,
    'use_rest': 'never',
    'feature_flags': {'no_cserver_ems': True}
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    error = create_module(my_module, fail=True)['msg']
    print('Info: %s' % error)
    assert 'missing required arguments:' in error
    assert 'name' in error


def test_create():
    register_responses([
        ('aggr-get-iter', ZRR['empty']),
        ('aggr-create', ZRR['empty']),
        ('aggr-get-iter', ZRR['empty']),
    ])
    module_args = {
        'disk_type': 'ATA',
        'raid_type': 'raid_dp',
        'snaplock_type': 'non_snaplock',
        # 'spare_pool': 'Pool0',
        'disk_count': 4,
        'raid_size': 5,
        'disk_size': 10,
        # 'disk_size_with_unit': 'dsize_unit',
        'is_mirrored': True,
        'ignore_pool_checks': True,
        'encryption': True,
        'nodes': ['node1', 'node2']
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('aggr-destroy', ZRR['empty'])
    ])
    module_args = {
        'state': 'absent',
        'disk_count': 3
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_with_spare_pool():
    register_responses([
        ('aggr-get-iter', ZRR['empty']),
        ('aggr-create', ZRR['empty']),
        ('aggr-get-iter', ZRR['empty']),
    ])
    module_args = {
        'disk_type': 'ATA',
        'raid_type': 'raid_dp',
        'snaplock_type': 'non_snaplock',
        'spare_pool': 'Pool0',
        'disk_count': 2,
        'raid_size': 5,
        'disk_size_with_unit': '10m',
        # 'disk_size_with_unit': 'dsize_unit',
        'ignore_pool_checks': True,
        'encryption': True,
        'nodes': ['node1', 'node2']
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_with_disks():
    register_responses([
        ('aggr-get-iter', ZRR['empty']),
        ('aggr-create', ZRR['empty']),
        ('aggr-get-iter', ZRR['empty']),
    ])
    module_args = {
        'disk_type': 'ATA',
        'raid_type': 'raid_dp',
        'snaplock_type': 'non_snaplock',
        'disks': [1, 2],
        'mirror_disks': [11, 12],
        'raid_size': 5,
        'disk_size_with_unit': '10m',
        'ignore_pool_checks': True,
        'encryption': True,
        'nodes': ['node1', 'node2']
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_create_wait_for_completion(mock_time):
    register_responses([
        ('aggr-get-iter', ZRR['empty']),
        ('aggr-create', ZRR['empty']),
        ('aggr-get-iter', ZRR['empty']),
        ('aggr-get-iter', ZRR['empty']),
        ('aggr-get-iter', ZRR['aggr_info']),
    ])
    module_args = {
        'disk_count': '2',
        'is_mirrored': 'true',
        'wait_for_online': 'true'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_with_object_store():
    register_responses([
        ('aggr-get-iter', ZRR['empty']),
        ('aggr-create', ZRR['empty']),
        ('aggr-get-iter', ZRR['empty']),
        ('aggr-object-store-attach', ZRR['empty']),
    ])
    module_args = {
        'disk_class': 'capacity',
        'disk_count': '2',
        'is_mirrored': 'true',
        'object_store_name': 'abc',
        'allow_flexgroups': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_is_mirrored():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
    ])
    module_args = {
        'disk_count': '4',
        'is_mirrored': 'true',
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_disks_list():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
    ])
    module_args = {
        'disks': ['1', '2'],
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_mirror_disks():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
    ])
    module_args = {
        'disks': ['1', '2'],
        'mirror_disks': ['3', '4']
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_spare_pool():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
    ])
    module_args = {
        'disk_count': '4',
        'spare_pool': 'Pool1'
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_negative_modify_encryption():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
    ])
    module_args = {
        'encryption': False
    }
    exc = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    msg = 'Error: modifying encryption is not supported with ZAPI.'
    assert msg in exc['msg']


def test_rename():
    register_responses([
        ('aggr-get-iter', ZRR['empty']),      # target does not exist
        ('aggr-get-iter', ZRR['aggr_info']),  # from exists
        ('aggr-rename', ZRR['empty']),
    ])
    module_args = {
        'from_name': 'test_name2'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rename_error_no_from():
    register_responses([
        ('aggr-get-iter', ZRR['empty']),      # target does not exist
        ('aggr-get-iter', ZRR['empty']),      # from does not exist
    ])
    module_args = {
        'from_name': 'test_name2'
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    msg = 'Error renaming aggregate %s: no aggregate with from_name %s.' % (AGGR_NAME, module_args['from_name'])
    assert msg in exception['msg']


def test_rename_with_add_object_store():        # TODO:
    register_responses([
        ('aggr-get-iter', ZRR['empty']),                  # target does not exist
        ('aggr-get-iter', ZRR['aggr_info']),              # from exists
        ('aggr-object-store-get-iter', ZRR['empty']),     # from does not have an OS
        ('aggr-rename', ZRR['empty']),
        ('aggr-object-store-attach', ZRR['empty']),
    ])
    module_args = {
        'from_name': 'test_name2',
        'object_store_name': 'abc',
        'allow_flexgroups': False
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_object_store_present():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('aggr-object-store-get-iter', ZRR['object_store_info']),
    ])
    module_args = {
        'object_store_name': 'abc'
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_object_store_create():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('aggr-object-store-get-iter', ZRR['empty']),     # object_store is not attached
        ('aggr-object-store-attach', ZRR['empty']),
    ])
    module_args = {
        'object_store_name': 'abc',
        'allow_flexgroups': True
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_object_store_modify():
    ''' not supported '''
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('aggr-object-store-get-iter', ZRR['object_store_info']),
    ])
    module_args = {
        'object_store_name': 'def'
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    msg = 'Error: object store %s is already associated with aggregate %s.' % (OS_NAME, AGGR_NAME)
    assert msg in exception['msg']


def test_if_all_methods_catch_exception():
    register_responses([
        ('aggr-get-iter', ZRR['error']),
        ('aggr-online', ZRR['error']),
        ('aggr-offline', ZRR['error']),
        ('aggr-create', ZRR['error']),
        ('aggr-destroy', ZRR['error']),
        ('aggr-rename', ZRR['error']),
        ('aggr-get-iter', ZRR['error']),
    ])
    module_args = {
        'service_state': 'online',
        'unmount_volumes': 'True',
        'from_name': 'test_name2',
    }

    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    error = expect_and_capture_ansible_exception(my_obj.aggr_get_iter, 'fail', module_args.get('name'))['msg']
    assert 'Error getting aggregate: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.aggregate_online, 'fail')['msg']
    assert 'Error changing the state of aggregate' in error

    error = expect_and_capture_ansible_exception(my_obj.aggregate_offline, 'fail')['msg']
    assert 'Error changing the state of aggregate' in error

    error = expect_and_capture_ansible_exception(my_obj.create_aggr, 'fail')['msg']
    assert 'Error provisioning aggregate' in error

    error = expect_and_capture_ansible_exception(my_obj.delete_aggr, 'fail')['msg']
    assert 'Error removing aggregate' in error

    error = expect_and_capture_ansible_exception(my_obj.rename_aggregate, 'fail')['msg']
    assert 'Error renaming aggregate' in error

    my_obj.asup_log_for_cserver = Mock(return_value=None)
    error = expect_and_capture_ansible_exception(my_obj.apply, 'fail')['msg']
    assert '12345:synthetic error for UT purpose' in error


def test_disks_bad_mapping():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
    ])
    module_args = {
        'disks': ['0'],
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    msg = "Error mapping disks for aggregate %s: cannot match disks with current aggregate disks." % AGGR_NAME
    assert exception['msg'].startswith(msg)


def test_disks_overlapping_mirror():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
    ])
    module_args = {
        'disks': ['1', '2', '3'],
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    msg = "Error mapping disks for aggregate %s: found overlapping plexes:" % AGGR_NAME
    assert exception['msg'].startswith(msg)


def test_disks_removing_disk():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
    ])
    module_args = {
        'disks': ['1'],
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    msg = "Error removing disks is not supported.  Aggregate %s: these disks cannot be removed: ['2']." % AGGR_NAME
    assert exception['msg'].startswith(msg)


def test_disks_removing_mirror_disk():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
    ])
    module_args = {
        'disks': ['1', '2'],
        'mirror_disks': ['4', '6']
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    msg = "Error removing disks is not supported.  Aggregate %s: these disks cannot be removed: ['3']." % AGGR_NAME
    assert exception['msg'].startswith(msg)


def test_disks_add():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
    ])
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
        ('aggr-add', ZRR['empty']),
    ])
    module_args = {
        'disks': ['1', '2', '5'],
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_disks_add_and_offline():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
        ('aggr-add', ZRR['empty']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['success']),
        # error if max tries attempted.
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
        ('aggr-add', ZRR['empty']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add']),
        ('aggr-offline', ZRR['error_disk_add'])
    ])
    module_args = {
        'disks': ['1', '2', '5'], 'service_state': 'offline'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert 'disk add operation is in progres' in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_mirror_disks_add():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
        ('aggr-add', ZRR['empty']),
    ])
    module_args = {
        'disks': ['1', '2', '5'],
        'mirror_disks': ['3', '4', '6']
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_mirror_disks_add_unbalanced():
    register_responses([
        ('aggr-get-iter', ZRR['aggr_info']),
        ('storage-disk-get-iter', ZRR['disk_info']),
    ])
    module_args = {
        'disks': ['1', '2'],
        'mirror_disks': ['3', '4', '6']
    }
    exception = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)
    msg = "Error cannot add mirror disks ['6'] without adding disks for aggregate %s." % AGGR_NAME
    assert exception['msg'].startswith(msg)


def test_map_plex_to_primary_and_mirror_error_overlap():
    my_obj = create_module(my_module, DEFAULT_ARGS)
    kwargs = {
        'plex_disks': {'plex1': [1, 2, 3], 'plex2': [4, 5, 6]},
        'disks': [1, 4, 5],
        'mirror_disks': []
    }
    error = expect_and_capture_ansible_exception(my_obj.map_plex_to_primary_and_mirror, 'fail', **kwargs)['msg']
    msg = "Error mapping disks for aggregate aggr_name: found overlapping plexes:"
    assert error.startswith(msg)


def test_map_plex_to_primary_and_mirror_error_overlap_mirror():
    my_obj = create_module(my_module, DEFAULT_ARGS)
    kwargs = {
        'plex_disks': {'plex1': [1, 2, 3], 'plex2': [4, 5, 6]},
        'disks': [1, 4, 5],
        'mirror_disks': [1, 4, 5]
    }
    error = expect_and_capture_ansible_exception(my_obj.map_plex_to_primary_and_mirror, 'fail', **kwargs)['msg']
    msg = "Error mapping disks for aggregate aggr_name: found overlapping mirror plexes:"
    error.startswith(msg)


def test_map_plex_to_primary_and_mirror_error_no_match():
    my_obj = create_module(my_module, DEFAULT_ARGS)
    kwargs = {
        'plex_disks': {'plex1': [1, 2, 3], 'plex2': [4, 5, 6]},
        'disks': [7, 8, 9],
        'mirror_disks': [10, 11, 12]
    }
    error = expect_and_capture_ansible_exception(my_obj.map_plex_to_primary_and_mirror, 'fail', **kwargs)['msg']
    msg = ("Error mapping disks for aggregate aggr_name: cannot match disks with current aggregate disks, "
           "and cannot match mirror_disks with current aggregate disks.")
    assert error.startswith(msg)


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_missing_netapp_lib(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    msg = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert msg == create_module(my_module, DEFAULT_ARGS, fail=True)['msg']


def test_disk_get_iter_error():
    register_responses([
        ('storage-disk-get-iter', ZRR['error']),
    ])
    msg = 'Error getting disks: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg == expect_and_capture_ansible_exception(create_module(my_module, DEFAULT_ARGS).disk_get_iter, 'fail', 'name')['msg']


def test_object_store_get_iter_error():
    register_responses([
        ('aggr-object-store-get-iter', ZRR['error']),
    ])
    msg = 'Error getting object store: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg == expect_and_capture_ansible_exception(create_module(my_module, DEFAULT_ARGS).object_store_get_iter, 'fail', 'name')['msg']


def test_attach_object_store_to_aggr_error():
    register_responses([
        ('aggr-object-store-attach', ZRR['error']),
    ])
    module_args = {
        'object_store_name': 'os12',
    }
    msg = 'Error attaching object store os12 to aggregate aggr_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg == expect_and_capture_ansible_exception(create_module(my_module, DEFAULT_ARGS, module_args).attach_object_store_to_aggr, 'fail')['msg']


def test_add_disks_all_options_class():
    register_responses([
        ('aggr-add', ZRR['empty']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['ignore_pool_checks'] = True
    my_obj.parameters['disk_class'] = 'performance'
    assert my_obj.add_disks(count=2, disks=['1', '2'], disk_size=1, disk_size_with_unit='12GB') is None


def test_add_disks_all_options_type():
    register_responses([
        ('aggr-add', ZRR['empty']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['ignore_pool_checks'] = True
    my_obj.parameters['disk_type'] = 'SSD'
    assert my_obj.add_disks(count=2, disks=['1', '2'], disk_size=1, disk_size_with_unit='12GB') is None


def test_add_disks_error():
    register_responses([
        ('aggr-add', ZRR['error']),
    ])
    msg = 'Error adding additional disks to aggregate aggr_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg == expect_and_capture_ansible_exception(create_module(my_module, DEFAULT_ARGS).add_disks, 'fail')['msg']


def test_modify_aggr_offline():
    register_responses([
        ('aggr-offline', ZRR['empty']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    assert my_obj.modify_aggr({'service_state': 'offline'}) is None


def test_modify_aggr_online():
    register_responses([
        ('aggr-online', ZRR['empty']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    assert my_obj.modify_aggr({'service_state': 'online'}) is None
