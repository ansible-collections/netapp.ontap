# (c) 2018-2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP net vlan Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import sys
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import assert_no_warnings, set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_vlan \
    import NetAppOntapVlan as my_module      # module under test


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


def default_args():
    args = {
        'state': 'present',
        'hostname': '10.10.10.10',
        'username': 'admin',
        'https': 'true',
        'validate_certs': 'false',
        'password': 'password',
        'use_rest': 'always'
    }
    return args


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_6': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy')), None),
    'is_rest_9_7': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'vlan_record': (200, {
        "num_records": 1,
        "records": [{
            'broadcast_domain': {
                'ipspace': {'name': 'Default'},
                'name': 'test1'
            },
            'enabled': True,
            'name': 'e0c-15',
            'node': {'name': 'mohan9cluster2-01'},
            'uuid': '97936a14-30de-11ec-ac4d-005056b3d8c8'
        }]
    }, None),
    'vlan_record_create': (200, {
        "num_records": 1,
        "records": [{
            'broadcast_domain': {
                'ipspace': {'name': 'Default'},
                'name': 'test2'
            },
            'enabled': True,
            'name': 'e0c-16',
            'node': {'name': 'mohan9cluster2-01'},
            'uuid': '97936a14-30de-11ec-ac4d-005056b3d8c8'
        }]
    }, None),
    'vlan_record_modify': (200, {
        "num_records": 1,
        "records": [{
            'broadcast_domain': {
                'ipspace': {'name': 'Default'},
                'name': 'test1'
            },
            'enabled': False,
            'name': 'e0c-16',
            'node': {'name': 'mohan9cluster2-01'},
            'uuid': '97936a14-30de-11ec-ac4d-005056b3d8c8'
        }]
    }, None)
}


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args(dict(hostname=''))
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'missing required arguments:'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_when_required_args_missing_ONTAP96(mock_request, patch_ansible):
    ''' required arguments are reported as errors for ONTAP 9.6'''
    args = dict(default_args())
    args['node'] = 'mohan9cluster2-01'
    args['vlanid'] = 154
    args['parent_interface'] = 'e0c'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_6']         # get version
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'broadcast_domain and ipspace are required fields with ONTAP 9.6 and 9.7'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_fail_when_required_args_missing_ONTAP97(mock_request, patch_ansible):
    ''' required arguments are reported as errors for ONTAP 9.7'''
    args = dict(default_args())
    args['node'] = 'mohan9cluster2-01'
    args['vlanid'] = 154
    args['parent_interface'] = 'e0c'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_7']         # get version
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'broadcast_domain and ipspace are required fields with ONTAP 9.6 and 9.7'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_get_vlan_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['node'] = 'mohan9cluster2-01'
    args['vlanid'] = 15
    args['parent_interface'] = 'e0c'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['vlan_record'],         # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_create_vlan_called(mock_request, patch_ansible):
    ''' test create'''
    args = dict(default_args())
    args['node'] = 'mohan9cluster2-01'
    args['vlanid'] = 16
    args['parent_interface'] = 'e0c'
    args['broadcast_domain'] = 'test2'
    args['ipspace'] = 'Default'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],          # get version
        SRR['zero_record'],          # get
        SRR['empty_good'],           # create
        SRR['vlan_record_create'],   # get created vlan record to check PATCH call required
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_modify_vlan_called(mock_request, patch_ansible):
    ''' test modify'''
    args = dict(default_args())
    args['node'] = 'mohan9cluster2-01'
    args['vlanid'] = 16
    args['parent_interface'] = 'e0c'
    args['broadcast_domain'] = 'test1'
    args['ipspace'] = 'Default'
    args['enabled'] = 'no'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],           # get version
        SRR['vlan_record_create'],    # get
        SRR['empty_good'],            # patch call
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_vlan_called(mock_request, patch_ansible):
    ''' test delete'''
    args = dict(default_args())
    args['node'] = 'mohan9cluster2-01'
    args['vlanid'] = 15
    args['parent_interface'] = 'e0c'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['vlan_record'],         # get
        SRR['empty_good'],          # delete
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_vlan_idempotent(mock_request, patch_ansible):
    ''' test delete idempotent'''
    args = dict(default_args())
    args['node'] = 'mohan9cluster2-01'
    args['vlanid'] = 15
    args['parent_interface'] = 'e0c'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['zero_record'],         # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()
