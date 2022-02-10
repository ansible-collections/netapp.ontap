
# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_aggregate when using REST """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible
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
        {'uuid': 'ansible',
         'block_storage': {'primary': {'disk_count': 5}},
         'state': 'online', 'snaplock_type': 'snap'}]}, None),
})


def set_default_args():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'name': 'aggr_name'
    })


def test_validate_options():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ], 'test_validate_options')
    set_module_args(set_default_args())
    my_obj = my_module()
    # no error!
    assert my_obj.validate_options() is None

    my_obj.parameters['nodes'] = [1, 2]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.validate_options()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error when validating options: only one node can be specified when using rest'
    assert msg in exc.value.args[0]['msg']

    my_obj.parameters['disk_count'] = 7
    my_obj.parameters.pop('nodes')
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.validate_options()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error when validating options: nodes is required when disk_count is present.'
    assert msg == exc.value.args[0]['msg']

    my_obj.use_rest = False
    my_obj.parameters['mirror_disks'] = [1, 2]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.validate_options()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error when validating options: mirror_disks require disks options to be set.'
    assert msg == exc.value.args[0]['msg']


def test_get_disk_size():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()

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
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_disk_size()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: unexpected unit in disk_size_with_unit: 1567rb'
    assert msg == exc.value.args[0]['msg']

    my_obj.parameters['disk_size_with_unit'] = 'error'
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_disk_size()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: unexpected value in disk_size_with_unit: error'
    assert msg == exc.value.args[0]['msg']


def test_get_aggr_rest_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['generic_error'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_aggr_rest('aggr1')
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to get aggregate aggr1: calling: storage/aggregates: got Expected error.'
    assert msg == exc.value.args[0]['msg']


def test_get_aggr_rest_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    assert my_obj.get_aggr_rest(None) is None


def test_get_aggr_rest_one_record():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    assert my_obj.get_aggr_rest('aggr1') is not None


def test_get_aggr_rest_not_found():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    assert my_obj.get_aggr_rest('aggr1') is None


def test_create_aggr():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'storage/aggregates', SRR['empty_good'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.create_aggr_rest()
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'POST', 'storage/aggregates')


def test_create_aggr_all_options():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'storage/aggregates', SRR['empty_good'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['disk_class'] = 'capacity'
    my_obj.parameters['disk_count'] = 12
    my_obj.parameters['disk_size_with_unit'] = '1567gb'
    my_obj.parameters['is_mirrored'] = True
    my_obj.parameters['nodes'] = ['node1']
    my_obj.parameters['raid_size'] = 4
    my_obj.parameters['raid_type'] = 'raid5'
    my_obj.parameters['encryption'] = True
    my_obj.parameters['snaplock_type'] = 'snap'

    my_obj.create_aggr_rest()
    assert get_mock_record().is_record_in_json(
        {'block_storage': {'primary': {'disk_class': 'capacity', 'disk_count': 12, 'raid_size': 4, 'raid_type': 'raid5'}, 'mirror': {'enabled': True}}},
        'POST', 'storage/aggregates')


def test_create_aggr_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'storage/aggregates', SRR['generic_error'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['disk_count'] = 12
    my_obj.parameters['disk_size_with_unit'] = '1567gb'
    my_obj.parameters['is_mirrored'] = False
    my_obj.parameters['nodes'] = ['node1']
    my_obj.parameters['raid_size'] = 4
    my_obj.parameters['raid_type'] = 'raid5'
    my_obj.parameters['encryption'] = True

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.create_aggr_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to create aggregate: calling: storage/aggregates: got Expected error.'
    assert msg == exc.value.args[0]['msg']


def test_delete_aggr():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('DELETE', 'storage/aggregates/aggr_uuid', SRR['empty_good'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['state'] = 'absent'
    my_obj.uuid = 'aggr_uuid'
    assert my_obj.delete_aggr_rest() is None


def test_delete_aggr_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('DELETE', 'storage/aggregates/aggr_uuid', SRR['generic_error'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['state'] = 'absent'
    my_obj.parameters['disk_size_with_unit'] = '1567gb'
    my_obj.parameters['is_mirrored'] = False
    my_obj.parameters['nodes'] = ['node1']
    my_obj.parameters['raid_size'] = 4
    my_obj.parameters['raid_type'] = 'raid5'
    my_obj.parameters['encryption'] = True
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.delete_aggr_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to delete aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.'
    assert msg == exc.value.args[0]['msg']


def test_patch_aggr():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['empty_good'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'
    my_obj.patch_aggr_rest('act on', {'key': 'value'})
    assert get_mock_record().is_record_in_json({'key': 'value'}, 'PATCH', 'storage/aggregates/aggr_uuid')


def test_patch_aggr_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['generic_error'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.patch_aggr_rest('act on', {'key': 'value'})
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to act on aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.'
    assert msg == exc.value.args[0]['msg']


def test_set_disk_count():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    current = {'disk_count': 2}
    modify = {'disk_count': 5}
    my_obj.set_disk_count(current, modify)
    assert modify['disk_count'] == 3


def test_set_disk_count_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()

    current = {'disk_count': 9}
    modify = {'disk_count': 5}
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.set_disk_count(current, modify)
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: specified disk_count is less than current disk_count. Only adding disks is allowed.'
    assert msg == exc.value.args[0]['msg']


def test_add_disks():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['empty_good'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['disk_class'] = 'performance'
    my_obj.parameters['disk_count'] = 12
    my_obj.uuid = 'aggr_uuid'
    my_obj.add_disks_rest(count=2)
    assert get_mock_record().is_record_in_json({'block_storage': {'primary': {'disk_count': 12}}}, 'PATCH', 'storage/aggregates/aggr_uuid')


def test_add_disks_error_local():
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.add_disks_rest(disks=[1, 2])
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: disks or mirror disks are mot supported with rest: [1, 2], None.'
    assert msg == exc.value.args[0]['msg']


def test_add_disks_error_remote():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['generic_error'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['disk_count'] = 12
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.add_disks_rest(count=2)
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to increase disk count for aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.'
    assert msg == exc.value.args[0]['msg']


def test_rename_aggr():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['empty_good'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'
    my_obj.rename_aggr_rest()
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'PATCH', 'storage/aggregates/aggr_uuid')


def test_rename_aggr_error_remote():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/aggregates/aggr_uuid', SRR['generic_error'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.rename_aggr_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to rename aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.'
    assert msg == exc.value.args[0]['msg']


def test_get_object_store():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates/aggr_uuid/cloud-stores', SRR['one_record'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'
    record = my_obj.get_object_store_rest()
    assert record


def test_get_object_store_error_remote():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates/aggr_uuid/cloud-stores', SRR['generic_error'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_object_store_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to get cloud stores for aggregate: calling: storage/aggregates/aggr_uuid/cloud-stores: got Expected error.'
    assert msg == exc.value.args[0]['msg']


def test_get_cloud_target_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cloud/targets', SRR['one_record'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'
    record = my_obj.get_cloud_target_uuid_rest()
    assert record


def test_get_cloud_target_uuid_error_remote():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cloud/targets', SRR['generic_error'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_cloud_target_uuid_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to find cloud store with name os12: calling: cloud/targets: got Expected error.'
    assert msg == exc.value.args[0]['msg']


def test_attach_object_store_to_aggr():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cloud/targets', SRR['one_record']),                                # get object store UUID
        ('POST', 'storage/aggregates/aggr_uuid/cloud-stores', SRR['empty_good'])    # attach (POST)
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'
    assert my_obj.attach_object_store_to_aggr_rest() == {}


def test_attach_object_store_to_aggr_error_remote():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cloud/targets', SRR['one_record']),                                    # get object store UUID
        ('POST', 'storage/aggregates/aggr_uuid/cloud-stores', SRR['generic_error'])     # attach (POST)
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.attach_object_store_to_aggr_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to attach cloud store with name os12: calling: storage/aggregates/aggr_uuid/cloud-stores: got Expected error.'
    assert msg == exc.value.args[0]['msg']


def test_apply_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),    # get
        ('POST', 'storage/aggregates', SRR['empty_good']),      # create (POST)
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'POST', 'storage/aggregates')


def test_apply_create_with_object_store():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),                        # get
        ('POST', 'storage/aggregates', SRR['empty_good']),                          # create (POST)
        ('GET', 'cloud/targets', SRR['one_record']),                                # get object store uuid
        ('POST', 'storage/aggregates/None/cloud-stores', SRR['empty_good']),        # attach (POST)
    ])
    # TODO: why None in storage/aggregates/None/cloud-stores? JIRA-4645
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'POST', 'storage/aggregates')
    assert get_mock_record().is_record_in_json({'target': {'uuid': 'ansible'}}, 'POST', 'storage/aggregates/None/cloud-stores')


def test_apply_create_check_mode():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),  # get
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.module.check_mode = True
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


def test_apply_add_disks():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record']),               # get
        ('PATCH', 'storage/aggregates/ansible', SRR['empty_good']),     # patch (add disks)
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['disk_count'] = 12
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert get_mock_record().is_record_in_json({'block_storage': {'primary': {'disk_count': 12}}}, 'PATCH', 'storage/aggregates/ansible')


def test_apply_add_object_store():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record']),                           # get
        ('GET', 'storage/aggregates/ansible/cloud-stores', SRR['empty_records']),   # get aggr cloud store
        ('GET', 'cloud/targets', SRR['one_record']),                                # get object store uuid
        ('POST', 'storage/aggregates/ansible/cloud-stores', SRR['empty_good']),     # attach
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert get_mock_record().is_record_in_json({'target': {'uuid': 'ansible'}}, 'POST', 'storage/aggregates/ansible/cloud-stores')


def test_apply_rename():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),            # get aggr
        ('GET', 'storage/aggregates', SRR['one_record']),               # get from_aggr
        ('PATCH', 'storage/aggregates/ansible', SRR['empty_good']),     # patch (rename)
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['from_name'] = 'old_aggr'
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert get_mock_record().is_record_in_json({'name': 'aggr_name'}, 'PATCH', 'storage/aggregates/ansible')


def test_apply_delete():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record']),               # get
        ('DELETE', 'storage/aggregates/ansible', SRR['empty_good']),    # delete
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['state'] = 'absent'
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


def test_get_aggr_actions_error_service_state_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record']),  # get
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['service_state'] = 'offline'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_aggr_actions()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: modifying state is not supported with REST.  Cannot change to: offline.'
    assert msg == exc.value.args[0]['msg']


def test_get_aggr_actions_error_snaplock():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['one_record']),  # get
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['snaplock_type'] = 'enterprise'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_aggr_actions()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: snaplock_type is not modifiable.  Cannot change to: enterprise.'
    assert msg == exc.value.args[0]['msg']


def test_main_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/aggregates', SRR['empty_records']),    # get
        ('POST', 'storage/aggregates', SRR['empty_good']),      # create
    ])
    set_module_args(set_default_args())

    with pytest.raises(AnsibleExitJson) as exc:
        my_main()
    assert exc.value.args[0]['changed']
