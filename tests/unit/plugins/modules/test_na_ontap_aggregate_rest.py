
# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_aggregate when using REST """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
# import copy
import json
import pytest
import sys

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_aggregate \
    import NetAppOntapAggregate as my_module, main as my_main  # module under test


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'empty_records': (200, {'records': []}, None),
    'one_record': (200, {'records': [
        {'uuid': 'ansible',
         'block_storage': {'primary': {'disk_count': 5}},
         'state': 'online', 'snaplock_type': 'snap'}]}, None),
    # 'get_multiple_records': (200, {'records': [{'uuid': 'ansible'}, {'uuid': 'second'}]}, None),
    # 'error_unexpected_name': (200, None, {'message': 'Unexpected argument "name".'}),
    # 'error_duplicate_entry': (200, None, {'message': 'duplicate entry', 'target': 'uuid'}),
    # 'error_some_error': (200, None, {'message': 'some error'}),
}


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


def exit_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


def set_default_args():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'name': 'aggr_name'
    })


# using pytest natively, without unittest.TestCase
@pytest.fixture
def patch_ansible():
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json) as mocks:
        yield mocks


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_validate_options(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    # no error!
    assert my_obj.validate_options() is None

    my_obj.parameters['nodes'] = [1, 2]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.validate_options()
    print('Info: %s' % exc.value.args[0]['msg'])
    print(mock_request.mock_calls, '\n---\n')
    msg = 'Error when validating options: only one node can be specified when using rest'
    assert msg in exc.value.args[0]['msg']

    my_obj.parameters['disk_count'] = 7
    my_obj.parameters.pop('nodes')
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.validate_options()
    print('Info: %s' % exc.value.args[0]['msg'])
    print(mock_request.mock_calls, '\n---\n')
    msg = 'Error when validating options: nodes is required when disk_count is present.'
    assert msg == exc.value.args[0]['msg']

    my_obj.use_rest = False
    my_obj.parameters['mirror_disks'] = [1, 2]
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.validate_options()
    print('Info: %s' % exc.value.args[0]['msg'])
    print(mock_request.mock_calls, '\n---\n')
    msg = 'Error when validating options: mirror_disks require disks options to be set.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_disk_size(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_aggr_rest_error(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_aggr_rest('aggr1')
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to get aggregate aggr1: calling: storage/aggregates: got Expected error.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_aggr_rest_none(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    assert my_obj.get_aggr_rest(None) is None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_aggr_rest_one_record(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    assert my_obj.get_aggr_rest('aggr1') is not None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_aggr_rest_not_found(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    assert my_obj.get_aggr_rest('aggr1') is None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_create_aggr(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.create_aggr_rest()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('POST', 'storage/aggregates', {'return_timeout': 30}, json={'name': 'aggr_name'}, headers=None)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_create_aggr_all_options(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
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
    print(mock_request.mock_calls, '\n---\n')
    expected_call = "'POST', 'storage/aggregates'"
    post_call = str(mock_request.mock_calls[1])
    print(post_call)
    assert expected_call in post_call
    assert "'disk_class': 'capacity'" in post_call


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_create_aggr_error(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_delete_aggr(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['state'] = 'absent'
    my_obj.uuid = 'aggr_uuid'
    my_obj.delete_aggr_rest()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('DELETE', 'storage/aggregates/aggr_uuid', {'return_timeout': 30}, json=None, headers=None)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_delete_aggr_error(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_patch_aggr(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'
    my_obj.patch_aggr_rest('act on', {'key': 'value'})
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('PATCH', 'storage/aggregates/aggr_uuid', {'return_timeout': 30}, json={'key': 'value'}, headers=None)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_patch_aggr_error(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.patch_aggr_rest('act on', {'key': 'value'})
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to act on aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_set_disk_count(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    current = {'disk_count': 2}
    modify = {'disk_count': 5}
    my_obj.set_disk_count(current, modify)
    assert modify['disk_count'] == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_set_disk_count_error(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()

    current = {'disk_count': 9}
    modify = {'disk_count': 5}
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.set_disk_count(current, modify)
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: specified disk_count is less than current disk_count. Only adding disks is allowed.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_add_disks(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['disk_class'] = 'performance'
    my_obj.parameters['disk_count'] = 12
    my_obj.uuid = 'aggr_uuid'
    my_obj.add_disks_rest(count=2)
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('PATCH', 'storage/aggregates/aggr_uuid', {'return_timeout': 30}, json={'block_storage': {'primary': {'disk_count': 12}}}, headers=None)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_add_disks_error_local(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.add_disks_rest(disks=[1, 2])
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: disks or mirror disks are mot supported with rest: [1, 2], None.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_add_disks_error_remote(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['disk_count'] = 12
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.add_disks_rest(count=2)
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to increase disk count for aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rename_aggr(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'
    my_obj.rename_aggr_rest()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('PATCH', 'storage/aggregates/aggr_uuid', {'return_timeout': 30}, json={'name': 'aggr_name'}, headers=None)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rename_aggr_error_remote(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.rename_aggr_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to rename aggregate: calling: storage/aggregates/aggr_uuid: got Expected error.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_object_store(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'
    record = my_obj.get_object_store_rest()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('GET', 'storage/aggregates/aggr_uuid/cloud-stores', {'primary': True}, headers=None)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_object_store_error_remote(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_object_store_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to get cloud stores for aggregate: calling: storage/aggregates/aggr_uuid/cloud-stores: got Expected error.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_cloud_target_uuid(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'
    record = my_obj.get_cloud_target_uuid_rest()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('GET', 'cloud/targets', {'name': 'os12'}, headers=None)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_cloud_target_uuid_error_remote(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_cloud_target_uuid_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to find cloud store with name os12: calling: cloud/targets: got Expected error.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_attach_object_store_to_aggr(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record'],  # get object store UUID
        SRR['empty_good'],  # attach (POST)
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'
    record = my_obj.attach_object_store_to_aggr_rest()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('GET', 'cloud/targets', {'name': 'os12'}, headers=None)
    assert expected_call in mock_request.mock_calls
    expected_call = call('POST', 'storage/aggregates/aggr_uuid/cloud-stores', {'return_timeout': 30}, json={'target': {'uuid': 'ansible'}}, headers=None)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_attach_object_store_to_aggr_error_remote(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record'],  # get object store UUID
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    my_obj.uuid = 'aggr_uuid'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.attach_object_store_to_aggr_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: failed to attach cloud store with name os12: calling: storage/aggregates/aggr_uuid/cloud-stores: got Expected error.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_apply_create(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],  # get
        SRR['empty_good'],     # create (POST)
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('POST', 'storage/aggregates', {'return_timeout': 30}, json={'name': 'aggr_name'}, headers=None)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_apply_create_with_object_store(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],  # get
        SRR['empty_good'],     # create (POST)
        SRR['one_record'],     # get object store uuid
        SRR['empty_good'],     # attach (POST)
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('POST', 'storage/aggregates', {'return_timeout': 30}, json={'name': 'aggr_name'}, headers=None)
    assert expected_call in mock_request.mock_calls
    expected_call = call('POST', 'storage/aggregates/None/cloud-stores', {'return_timeout': 30}, json={'target': {'uuid': 'ansible'}}, headers=None)
    assert expected_call in mock_request.mock_calls
    assert len(mock_request.mock_calls) == 5


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_apply_create_check_mode(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],  # get
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.module.check_mode = True
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls, '\n---\n')
    assert len(mock_request.mock_calls) == 2


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_apply_add_disks(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record'],      # get
        SRR['empty_good'],      # patch (add disks)
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['disk_count'] = 12
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('PATCH', 'storage/aggregates/ansible', {'return_timeout': 30}, json={'block_storage': {'primary': {'disk_count': 12}}}, headers=None)
    assert expected_call in mock_request.mock_calls
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_apply_add_object_store(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record'],      # get
        SRR['empty_records'],   # get aggr cloud store
        SRR['one_record'],      # get object store uuid
        SRR['empty_good'],      # attach
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['object_store_name'] = 'os12'
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('POST', 'storage/aggregates/ansible/cloud-stores', {'return_timeout': 30}, json={'target': {'uuid': 'ansible'}}, headers=None)
    assert expected_call in mock_request.mock_calls
    assert len(mock_request.mock_calls) == 5


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_apply_rename(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],   # get aggr
        SRR['one_record'],      # get from_aggr
        SRR['empty_good'],      # patch (rename)
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['from_name'] = 'old_aggr'
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('PATCH', 'storage/aggregates/ansible', {'return_timeout': 30}, json={'name': 'aggr_name'}, headers=None)
    assert expected_call in mock_request.mock_calls
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_apply_delete(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record'],      # get
        SRR['empty_good'],      # delete
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['state'] = 'absent'
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print(mock_request.mock_calls, '\n---\n')
    expected_call = call('DELETE', 'storage/aggregates/ansible', {'return_timeout': 30}, json=None, headers=None)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_aggr_actions_error_service_state_rest(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record'],  # get
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['service_state'] = 'offline'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_aggr_actions()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: modifying state is not supported with REST.  Cannot change to: offline.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_aggr_actions_error_snaplock(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_record'],  # get
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['snaplock_type'] = 'enterprise'

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_aggr_actions()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'Error: snaplock_type is not modifiable.  Cannot change to: enterprise.'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_main_rest(mock_request, patch_ansible):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],   # get
        SRR['empty_good'],      # create
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())

    with pytest.raises(AnsibleExitJson) as exc:
        my_main()
    print(mock_request.mock_calls, '\n---\n')
    assert exc.value.args[0]['changed']
