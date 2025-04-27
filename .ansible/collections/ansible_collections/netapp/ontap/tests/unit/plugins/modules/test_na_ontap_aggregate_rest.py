
# (c) 2022-2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_aggregate when using REST """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_aggregate \
    import NetAppOntapAggregate as my_module, main as my_main  # module under test


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    'one_record': (200, {'records': [
        {'uuid': 'ansible', '_tags': ['resource:cloud', 'main:aggr'],
         'block_storage': {'primary': {'disk_count': 5}},
         'state': 'online', 'snaplock_type': 'snap'}
    ]}, None),
    'two_records': (200, {'records': [
        {'uuid': 'ansible',
         'block_storage': {'primary': {'disk_count': 5}},
         'state': 'online', 'snaplock_type': 'snap'},
        {'uuid': 'ansible',
         'block_storage': {'primary': {'disk_count': 5}},
         'state': 'online', 'snaplock_type': 'snap'},
    ]}, None),
    'no_uuid': (200, {'records': [
        {'block_storage': {'primary': {'disk_count': 5}},
         'state': 'online', 'snaplock_type': 'snap'},
    ]}, None),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'aggr_name'
}


def test_validate_options():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ], 'test_validate_options')
    # no error!
    my_obj = create_module(my_module, DEFAULT_ARGS)
    assert my_obj.validate_options() is None

    my_obj.parameters['nodes'] = [1, 2]

    msg = 'Error when validating options: only one node can be specified when using rest'
    assert msg in expect_and_capture_ansible_exception(my_obj.validate_options, 'fail')['msg']

    my_obj.parameters['disk_count'] = 7
    my_obj.parameters.pop('nodes')
    msg = 'Error when validating options: nodes is required when disk_count is present.'
    assert msg in expect_and_capture_ansible_exception(my_obj.validate_options, 'fail')['msg']

    my_obj.use_rest = False
    my_obj.parameters['mirror_disks'] = [1, 2]
    msg = 'Error when validating options: mirror_disks require disks options to be set.'
    assert msg in expect_and_capture_ansible_exception(my_obj.validate_options, 'fail')['msg']


def test_get_disk_size():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)

    my_obj.parameters['disk_size'] = 1
    assert my_obj.get_disk_size() == 4096
    my_obj.parameters['disk_size'] = 1000
    assert my_obj.get_disk_size() == 4096000

    my_obj.parameters.pop('disk_size')
    my_obj.parameters['disk_size_with_unit'] = '1567'
    assert my_obj.get_disk_size() == 1567
    my_obj.parameters['disk_size_with_unit'] = '1567K'
    assert my_obj.get_disk_size() == 1567 * 1024
    my_obj.parameters['disk_size_with_unit'] = '1567gb'
    assert my_obj.get_disk_size() == 1567 * 1024 * 1024 * 1024
    my_obj.parameters['disk_size_with_unit'] = '15.67gb'
    assert my_obj.get_disk_size() == int(15.67 * 1024 * 1024 * 1024)

    my_obj.parameters['disk_size_with_unit'] = '1567rb'
    error = expect_and_capture_ansible_exception(my_obj.get_disk_size, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error: unexpected unit in disk_size_with_unit: 1567rb' == error

    my_obj.parameters['disk_size_with_unit'] = 'error'
    error = expect_and_capture_ansible_exception(my_obj.get_disk_size, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error: unexpected value in disk_size_with_unit: error' == error


def test_get_aggr_rest_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['generic_error'])
    ])
    error = expect_and_capture_ansible_exception(create_module(my_module, DEFAULT_ARGS).get_aggr_rest, 'fail', 'aggr1')['msg']
    print('Info: %s' % error)
    assert 'Error: failed to get aggregate aggr1: calling: storage/aggregates: got Expected error.' == error


def test_get_aggr_rest_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    assert create_module(my_module, DEFAULT_ARGS).get_aggr_rest(None) is None


def test_get_aggr_rest_one_record():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record'])
    ])
    assert create_module(my_module, DEFAULT_ARGS).get_aggr_rest('aggr1') is not None


def test_get_aggr_rest_not_found():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),
    ])
    assert create_module(my_module, DEFAULT_ARGS).get_aggr_rest('aggr1') is None


def test_create_aggr():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'storage/aggregates', SRR['empty_good'])
    ])
    assert create_module(my_module, DEFAULT_ARGS).create_aggr_rest() is None
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'POST', 'storage/aggregates')


def test_aggr_tags():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_13_1']),
        ('GET', 'storage/aggregates', SRR['zero_records']),
        ('POST', 'storage/aggregates', SRR['empty_good']),
        # idempotent check
        ('GET', 'cluster', SRR['is_rest_9_13_1']),
        ('GET', 'storage/aggregates', SRR['one_record']),
        # modify tags
        ('GET', 'cluster', SRR['is_rest_9_13_1']),
        ('GET', 'storage/aggregates', SRR['one_record']),
        ('PATCH', 'storage/aggregates/ansible', SRR['success'])
    ])
    args = {'tags': ['resource:cloud', 'main:aggr']}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert create_and_apply(my_module, DEFAULT_ARGS, {'tags': ['main:aggr']})['changed']


def test_create_aggr_all_options():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'storage/aggregates', SRR['empty_good'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['disk_class'] = 'capacity'
    my_obj.parameters['disk_count'] = 12
    my_obj.parameters['disk_size_with_unit'] = '1567gb'
    my_obj.parameters['is_mirrored'] = True
    my_obj.parameters['nodes'] = ['node1']
    my_obj.parameters['raid_size'] = 4
    my_obj.parameters['raid_type'] = 'raid5'
    my_obj.parameters['encryption'] = True
    my_obj.parameters['snaplock_type'] = 'snap'

    assert my_obj.create_aggr_rest() is None
    assert get_mock_record().is_record_in_json(
        {'block_storage': {'primary': {'disk_class': 'capacity', 'disk_count': 12, 'raid_size': 4, 'raid_type': 'raid5'}, 'mirror': {'enabled': True}}},
        'POST', 'storage/aggregates')


def test_create_aggr_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'storage/aggregates', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['disk_count'] = 12
    my_obj.parameters['disk_size_with_unit'] = '1567gb'
    my_obj.parameters['is_mirrored'] = False
    my_obj.parameters['nodes'] = ['node1']
    my_obj.parameters['raid_size'] = 4
    my_obj.parameters['raid_type'] = 'raid5'
    my_obj.parameters['encryption'] = True

    error = expect_and_capture_ansible_exception(my_obj.create_aggr_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error: failed to create aggregate: calling: storage/aggregates: got Expected error.' == error


def test_delete_aggr():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('DELETE', 'storage/aggregates/aggr_uuid', SRR['empty_good'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.uuid = 'aggr_uuid'
    assert my_obj.delete_aggr_rest() is None


def test_delete_aggr_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('DELETE', 'storage/aggregates/aggr_uuid', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.parameters['disk_size_with_unit'] = '1567gb'
    my_obj.parameters['is_mirrored'] = False
    my_obj.parameters['nodes'] = ['node1']
    my_obj.parameters['raid_size'] = 4
    my_obj.parameters['raid_type'] = 'raid5'
    my_obj.parameters['encryption'] = True
    my_obj.uuid = 'aggr_uuid'

    error = expect_and_capture_ansible_exception(my_obj.delete_aggr_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error: failed to delete aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.' == error


def test_patch_aggr():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['empty_good'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.uuid = 'aggr_uuid'
    my_obj.patch_aggr_rest('act on', {'key': 'value'})
    assert get_mock_record().is_record_in_json({'key': 'value'}, 'PATCH', 'storage/aggregates/aggr_uuid')


def test_patch_aggr_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.uuid = 'aggr_uuid'

    error = expect_and_capture_ansible_exception(my_obj.patch_aggr_rest, 'fail', 'act on', {'key': 'value'})['msg']
    print('Info: %s' % error)
    assert 'Error: failed to act on aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.' == error


def test_set_disk_count():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    current = {'disk_count': 2}
    modify = {'disk_count': 5}
    my_obj.set_disk_count(current, modify)
    assert modify['disk_count'] == 3


def test_set_disk_count_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)

    current = {'disk_count': 9}
    modify = {'disk_count': 5}
    error = expect_and_capture_ansible_exception(my_obj.set_disk_count, 'fail', current, modify)['msg']
    print('Info: %s' % error)
    assert 'Error: specified disk_count is less than current disk_count. Only adding disks is allowed.' == error


def test_add_disks():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['empty_good'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['disk_class'] = 'performance'
    my_obj.parameters['disk_count'] = 12
    my_obj.uuid = 'aggr_uuid'
    my_obj.add_disks_rest(count=2)
    assert get_mock_record().is_record_in_json({'block_storage': {'primary': {'disk_count': 12}}}, 'PATCH', 'storage/aggregates/aggr_uuid')


def test_add_disks_error_local():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.uuid = 'aggr_uuid'

    error = expect_and_capture_ansible_exception(my_obj.add_disks_rest, 'fail', disks=[1, 2])['msg']
    print('Info: %s' % error)
    assert 'Error: disks or mirror disks are mot supported with rest: [1, 2], None.' == error


def test_add_disks_error_remote():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['disk_count'] = 12
    my_obj.uuid = 'aggr_uuid'

    error = expect_and_capture_ansible_exception(my_obj.add_disks_rest, 'fail', count=2)['msg']
    print('Info: %s' % error)
    assert 'Error: failed to increase disk count for aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.' == error


def test_change_raid_type():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record']),               # get
        ('PATCH', 'storage/aggregates/ansible', SRR['empty_good']),
        ('PATCH', 'storage/aggregates/ansible', SRR['empty_good']),     # patch (change raid type)
    ])
    module_args = {
        'disk_count': 12,
        'nodes': 'node1',
        'raid_type': 'raid_dp'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert get_mock_record().is_record_in_json({'block_storage': {'primary': {'raid_type': 'raid_dp'}}}, 'PATCH', 'storage/aggregates/ansible')


def test_rename_aggr():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['empty_good'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.uuid = 'aggr_uuid'
    my_obj.rename_aggr_rest()
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'PATCH', 'storage/aggregates/aggr_uuid')


def test_offline_online_aggr_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['generic_error']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.uuid = 'aggr_uuid'
    error = 'Error: failed to make service state online for aggregate'
    assert error in expect_and_capture_ansible_exception(my_obj.aggregate_online, 'fail')['msg']
    error = 'Error: failed to make service state offline for aggregate'
    assert error in expect_and_capture_ansible_exception(my_obj.aggregate_offline, 'fail')['msg']


def test_rename_aggr_error_remote():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.uuid = 'aggr_uuid'

    error = expect_and_capture_ansible_exception(my_obj.rename_aggr_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error: failed to rename aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.' == error


def test_get_object_store():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates/aggr_uuid/cloud-stores', SRR['one_record'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.uuid = 'aggr_uuid'
    record = my_obj.get_object_store_rest()
    assert record


def test_get_object_store_error_remote():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates/aggr_uuid/cloud-stores', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.uuid = 'aggr_uuid'

    error = expect_and_capture_ansible_exception(my_obj.get_object_store_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error: failed to get cloud stores for aggregate: calling: storage/aggregates/aggr_uuid/cloud-stores: got Expected error.' == error


def test_get_cloud_target_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cloud/targets', SRR['one_record'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'
    record = my_obj.get_cloud_target_uuid_rest()
    assert record


def test_get_cloud_target_uuid_error_remote():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cloud/targets', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'

    error = expect_and_capture_ansible_exception(my_obj.get_cloud_target_uuid_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error: failed to find cloud store with name os12: calling: cloud/targets: got Expected error.' == error


def test_attach_object_store_to_aggr():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cloud/targets', SRR['one_record']),                                # get object store UUID
        ('POST', 'storage/aggregates/aggr_uuid/cloud-stores', SRR['empty_good'])    # attach (POST)
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.parameters['allow_flexgroups'] = True
    my_obj.uuid = 'aggr_uuid'
    assert my_obj.attach_object_store_to_aggr_rest() == {}


def test_attach_object_store_to_aggr_error_remote():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cloud/targets', SRR['one_record']),                                    # get object store UUID
        ('POST', 'storage/aggregates/aggr_uuid/cloud-stores', SRR['generic_error'])     # attach (POST)
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'

    error = expect_and_capture_ansible_exception(my_obj.attach_object_store_to_aggr_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error: failed to attach cloud store with name os12: calling: storage/aggregates/aggr_uuid/cloud-stores: got Expected error.' == error


def test_apply_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),    # get
        ('POST', 'storage/aggregates', SRR['empty_good']),      # create (POST)
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'POST', 'storage/aggregates')


def test_apply_create_and_modify_service_state():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'storage/aggregates', SRR['empty_records']),    # get
        ('POST', 'storage/aggregates', SRR['empty_good']),      # create (POST)
        ('PATCH', 'storage/aggregates', SRR['success']),        # modify service state
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'service_state': 'offline'})['changed']
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'POST', 'storage/aggregates')


def test_apply_create_fail_to_read_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),    # get
        ('POST', 'storage/aggregates', SRR['two_records']),      # create (POST)
    ])
    msg = 'Error: failed to parse create aggregate response: calling: storage/aggregates: unexpected response'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, fail=True)['msg']


def test_apply_create_fail_to_read_uuid_key_missing():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),    # get
        ('POST', 'storage/aggregates', SRR['no_uuid']),         # create (POST)
    ])
    msg = 'Error: failed to parse create aggregate response: uuid key not present in'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, fail=True)['msg']


def test_apply_create_with_object_store():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),                        # get
        ('POST', 'storage/aggregates', SRR['one_record']),                          # create (POST)
        ('GET', 'cloud/targets', SRR['one_record']),                                # get object store uuid
        ('POST', 'storage/aggregates/ansible/cloud-stores', SRR['empty_good']),     # attach (POST)
    ])
    module_args = {
        'object_store_name': 'os12'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'POST', 'storage/aggregates')
    assert get_mock_record().is_record_in_json({'target': {'uuid': 'ansible'}}, 'POST', 'storage/aggregates/ansible/cloud-stores')


def test_apply_create_with_object_store_missing_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),                        # get
        ('POST', 'storage/aggregates', SRR['empty_good']),                          # create (POST)
    ])
    module_args = {
        'object_store_name': 'os12'
    }
    msg = 'Error: cannot attach cloud store with name os12: aggregate UUID is not set.'
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'POST', 'storage/aggregates')


def test_apply_create_check_mode():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),  # get
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, check_mode=True)['changed']


def test_apply_add_disks():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record']),               # get
        ('PATCH', 'storage/aggregates/ansible', SRR['empty_good']),     # patch (add disks)
    ])
    module_args = {
        'disk_count': 12,
        'nodes': 'node1'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert get_mock_record().is_record_in_json({'block_storage': {'primary': {'disk_count': 12}}}, 'PATCH', 'storage/aggregates/ansible')


def test_apply_add_object_store():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record']),                           # get
        ('GET', 'storage/aggregates/ansible/cloud-stores', SRR['empty_records']),   # get aggr cloud store
        ('GET', 'cloud/targets', SRR['one_record']),                                # get object store uuid
        ('POST', 'storage/aggregates/ansible/cloud-stores', SRR['empty_good']),     # attach
    ])
    module_args = {
        'object_store_name': 'os12',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert get_mock_record().is_record_in_json({'target': {'uuid': 'ansible'}}, 'POST', 'storage/aggregates/ansible/cloud-stores')


def test_apply_rename():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),            # get aggr
        ('GET', 'storage/aggregates', SRR['one_record']),               # get from_aggr
        ('PATCH', 'storage/aggregates/ansible', SRR['empty_good']),     # patch (rename)
    ])
    module_args = {
        'from_name': 'old_aggr',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'PATCH', 'storage/aggregates/ansible')


def test_apply_delete():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record']),               # get
        ('DELETE', 'storage/aggregates/ansible', SRR['empty_good']),    # delete
    ])
    module_args = {
        'state': 'absent',
        'disk_count': 4
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_get_aggr_actions_error_service_state_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    error = 'Error: Minimum version of ONTAP for service_state is (9, 11, 1)'
    assert error in create_module(my_module, DEFAULT_ARGS, {'service_state': 'online', 'use_rest': 'always'}, fail=True)['msg']


def test_get_aggr_actions_error_snaplock():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record']),  # get
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['snaplock_type'] = 'enterprise'

    error = expect_and_capture_ansible_exception(my_obj.get_aggr_actions, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error: snaplock_type is not modifiable.  Cannot change to: enterprise.' == error


def test_main_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),    # get
        ('POST', 'storage/aggregates', SRR['empty_good']),      # create
    ])
    set_module_args(DEFAULT_ARGS)

    assert expect_and_capture_ansible_exception(my_main, 'exit')['changed']
