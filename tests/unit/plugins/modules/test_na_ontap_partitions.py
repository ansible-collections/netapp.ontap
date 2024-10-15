# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP disks Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_partitions \
    import NetAppOntapPartitions as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def default_args():
    args = {
        'disk_type': 'SAS',
        'partitioning_method': 'root_data',
        'partition_type': 'data',
        'partition_count': 13,
        'hostname': '10.10.10.10',
        'username': 'username',
        'password': 'password',
        'node': 'node1',
        'use_rest': 'always'
    }
    return args


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'owned_partitions_record': (200, {
        "records": [
            {
                "partition": "1.0.0.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "fas2552-rtp-13-02",
                "owner_node_name": "fas2552-rtp-13-02"
            },
            {
                "partition": "1.0.2.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "fas2552-rtp-13-02",
                "owner_node_name": "fas2552-rtp-13-02"
            },
            {
                "partition": "1.0.4.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "fas2552-rtp-13-02",
                "owner_node_name": "fas2552-rtp-13-02"
            }
        ],
        "num_records": 3
    }, None),

    'unassigned_partitions_record': (200, {
        "records": [
            {
                "partition": "1.0.25.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "fas2552-rtp-13-02",
                "owner_node_name": "fas2552-rtp-13-02"
            },
            {
                "partition": "1.0.27.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "fas2552-rtp-13-02",
                "owner_node_name": "fas2552-rtp-13-02"
            },
        ],
        "num_records": 2
    }, None),

    'unassigned_disks_record': (200, {
        "records": [
            {
                'name': '1.0.27',
                'type': 'sas',
                'container_type': 'unassigned',
                'home_node': {'name': 'node1'}},
            {
                'name': '1.0.28',
                'type': 'sas',
                'container_type': 'unassigned',
                'home_node': {'name': 'node1'}}
        ],
        'num_records': 2}, None),

    'home_spare_disk_info_record': (200, {
        'records': [],
        'num_records': 2}, None),

    'spare_partitions_record': (200, {
        "records": [
            {
                "partition": "1.0.0.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "fas2552-rtp-13-02",
                "owner_node_name": "fas2552-rtp-13-02"
            },
            {
                "partition": "1.0.1.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "fas2552-rtp-13-02",
                "owner_node_name": "fas2552-rtp-13-02"
            }
        ], 'num_records': 2
    }, None),

    'partner_spare_partitions_record': (200, {
        "records": [
            {
                "partition": "1.0.1.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "node2",
                "owner_node_name": "node2"
            },
            {
                "partition": "1.0.3.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "node2",
                "owner_node_name": "node2"
            },
            {
                "partition": "1.0.5.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "node2",
                "owner_node_name": "node2"
            },
            {
                "partition": "1.0.23.P1",
                "container_type": "spare",
                "partitioning_method": "root_data",
                "is_root": False,
                "disk_type": "sas",
                "home_node_name": "node2",
                "owner_node_name": "node2"
            }
        ], "num_records": 4
    }, None),

    'partner_node_name_record': (200, {
        'records': [
            {
                'uuid': 'c345c182-a6a0-11eb-af7b-00a0984839de',
                'name': 'node2',
                'ha': {
                    'partners': [
                        {'name': 'node1'}
                    ]
                }
            }
        ], 'num_records': 1
    }, None),

    'partner_spare_disks_record': (200, {
        'records': [
            {
                'name': '1.0.22',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node2'}
            },
            {
                'name': '1.0.20',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node2'}
            },
            {
                'name': '1.0.18',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node2'}
            },
            {
                'name': '1.0.16',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node2'}
            }
        ], 'num_records': 4
    }, None),

    'adp2_owned_partitions_record': (200, {
        "records": [
            {
                "partition": "1.0.0.P1",
                "container_type": "spare",
                "partitioning_method": "root_data1_data2",
                "is_root": False,
                "disk_type": "ssd",
                "home_node_name": "aff300-rtp-2b",
                "owner_node_name": "aff300-rtp-2b"
            },
            {
                "partition": "1.0.1.P1",
                "container_type": "spare",
                "partitioning_method": "root_data1_data2",
                "is_root": False,
                "disk_type": "ssd",
                "home_node_name": "aff300-rtp-2b",
                "owner_node_name": "aff300-rtp-2b"
            },
            {
                "partition": "1.0.23.P1",
                "container_type": "spare",
                "partitioning_method": "root_data1_data2",
                "is_root": False,
                "disk_type": "ssd",
                "home_node_name": "aff300-rtp-2b",
                "owner_node_name": "aff300-rtp-2b"
            }
        ], "num_records": 3
    }, None),
}


def test_rest_missing_arguments(patch_ansible):     # pylint: disable=redefined-outer-name,unused-argument ##WHAT DOES THIS METHOD DO
    ''' create  scope '''
    args = dict(default_args())
    del args['hostname']
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = 'missing required arguments: hostname'
    assert exc.value.args[0]['msg'] == msg


# get unassigned partitions
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_assign_unassigned_disks(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Steal disks from partner node and assign them to the requested node '''
    args = dict(default_args())
    args['partition_count'] = 5
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['owned_partitions_record'],
        SRR['home_spare_disk_info_record'],
        SRR['unassigned_partitions_record'],
        SRR['unassigned_disks_record'],
        SRR['partner_node_name_record'],
        SRR['partner_spare_partitions_record'],
        SRR['partner_spare_disks_record'],
        SRR['empty_good'],  # assign
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 6


# assign unassigned partitions + steal 2 partner spare partitions
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_assign_unassigned_and_partner_spare_disks(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Steal disks from partner node and assign them to the requested node '''
    args = dict(default_args())
    args['partition_count'] = 7
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['owned_partitions_record'],
        SRR['home_spare_disk_info_record'],
        SRR['unassigned_partitions_record'],
        SRR['unassigned_disks_record'],
        SRR['partner_node_name_record'],
        SRR['partner_spare_partitions_record'],
        SRR['partner_spare_disks_record'],
        SRR['empty_good'],  # unassign
        SRR['empty_good'],  # assign
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 9


# assign unassigned partitions + steal 2 partner spare partitions
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_assign_unassigned_and_partner_spare_partitions_and_disks(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Steal disks from partner node and assign them to the requested node '''
    args = dict(default_args())
    args['partition_count'] = 6
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['owned_partitions_record'],
        SRR['home_spare_disk_info_record'],
        SRR['unassigned_partitions_record'],
        SRR['unassigned_disks_record'],
        SRR['partner_node_name_record'],
        SRR['partner_spare_partitions_record'],
        SRR['partner_spare_disks_record'],
        SRR['empty_good'],  # unassign
        SRR['empty_good'],  # assign
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 8


# Should unassign partitions
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_unassign(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Steal disks from partner node and assign them to the requested node '''
    args = dict(default_args())
    args['partition_count'] = 2  # change this number to be less than currently assigned partions to the node
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['owned_partitions_record'],
        SRR['unassigned_partitions_record'],
        SRR['spare_partitions_record'],
        SRR['empty_good'],  # unassign
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 5


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_no_action(mock_request, patch_ansible):        # pylint: disable=redefined-outer-name,unused-argument
    ''' disk_count matches arguments, do nothing '''
    args = dict(default_args())
    args['partition_count'] = 3
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['owned_partitions_record'],
        SRR['unassigned_partitions_record'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is False
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3


# ADP2
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_assign_unassigned_disks_adp2(mock_request, patch_ansible):        # pylint: disable=redefined-outer-name,unused-argument
    ''' Steal disks from partner node and assign them to the requested node '''
    args = dict(default_args())
    args['partitioning_method'] = 'root_data1_data2'
    args['partition_type'] = 'data1'
    args['partition_count'] = 5  # change this dependant on data1 partitions
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['adp2_owned_partitions_record'],
        SRR['home_spare_disk_info_record'],
        SRR['unassigned_partitions_record'],
        SRR['unassigned_disks_record'],
        SRR['partner_node_name_record'],
        SRR['partner_spare_partitions_record'],
        SRR['partner_spare_disks_record'],
        SRR['empty_good'],  # assign
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 6


# assign unassigned partitions + steal 2 partner spare partitions
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_assign_unassigned_and_partner_spare_disks_adp2(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Steal disks from partner node and assign them to the requested node '''
    args = dict(default_args())
    args['partitioning_method'] = 'root_data1_data2'
    args['partition_type'] = 'data1'
    args['partition_count'] = 7  # data1 partitions
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['adp2_owned_partitions_record'],
        SRR['home_spare_disk_info_record'],
        SRR['unassigned_partitions_record'],
        SRR['unassigned_disks_record'],
        SRR['partner_node_name_record'],
        SRR['partner_spare_partitions_record'],
        SRR['partner_spare_disks_record'],
        SRR['empty_good'],  # unassign
        SRR['empty_good'],  # assign
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 9


# assign unassigned partitions + steal 2 partner spare partitions
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_assign_unassigned_and_partner_spare_partitions_and_disks_adp2(mock_request, patch_ansible):
    ''' Steal disks from partner node and assign them to the requested node '''
    args = dict(default_args())
    args['partitioning_method'] = 'root_data1_data2'
    args['partition_type'] = 'data1'
    args['partition_count'] = 6  # change this dependant on data1 partitions
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['adp2_owned_partitions_record'],
        SRR['home_spare_disk_info_record'],
        SRR['unassigned_partitions_record'],
        SRR['unassigned_disks_record'],
        SRR['partner_node_name_record'],
        SRR['partner_spare_partitions_record'],
        SRR['partner_spare_disks_record'],
        SRR['empty_good'],  # unassign
        SRR['empty_good'],  # assign
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 8


# Should unassign partitions
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_unassign_adp2(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Steal disks from partner node and assign them to the requested node '''
    args = dict(default_args())
    args['partitioning_method'] = 'root_data1_data2'
    args['partition_type'] = 'data1'
    args['partition_count'] = 2  # change this number to be less than currently assigned partions to the node
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['adp2_owned_partitions_record'],
        SRR['unassigned_partitions_record'],
        SRR['spare_partitions_record'],
        SRR['empty_good'],  # unassign
        # SRR['empty_good'],  # assign
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 5
