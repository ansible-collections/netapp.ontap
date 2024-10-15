# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP lun reporting nodes Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_module, create_and_apply, expect_and_capture_ansible_exception
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_lun_map_reporting_nodes \
    import NetAppOntapLUNMapReportingNodes as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


DEFAULT_ARGS = {
    'initiator_group_name': 'igroup1',
    "path": "/vol/lun1/lun1_1",
    "vserver": "svm1",
    'nodes': 'ontap910-01',
    'state': 'present',
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'never'
}


node_info = {
    'num-records': "1",
    'attributes-list': {
        'lun-map-info': {
            'reporting-nodes': [{"node-name": "ontap910-01"}]
        }
    }
}


nodes_info = {
    'num-records': "1",
    'attributes-list': {
        'lun-map-info': {
            'reporting-nodes': [{"node-name": "ontap910-01"}, {"node-name": "ontap910-02"}]
        }
    }
}


ZRR = zapi_responses({
    'node_info': build_zapi_response(node_info),
    'nodes_info': build_zapi_response(nodes_info)
})


SRR = rest_responses({
    'node_info': (200, {"records": [{
        "svm": {"name": "svm1"},
        "lun": {"uuid": "ea78ec41", "name": "/vol/ansibleLUN/ansibleLUN"},
        "igroup": {"uuid": "8b8aa177", "name": "testme_igroup"},
        "reporting_nodes": [{"uuid": "20f6b3d5", "name": "ontap910-01"}]
    }], "num_records": 1}, None),
    'nodes_info': (200, {"records": [{
        "svm": {"name": "svm1"},
        "lun": {"uuid": "ea78ec41", "name": "/vol/ansibleLUN/ansibleLUN"},
        "igroup": {"uuid": "8b8aa177", "name": "testme_igroup"},
        "reporting_nodes": [{"uuid": "20f6b3d5", "name": "ontap910-01"}, {"uuid": "20f6b3d6", "name": "ontap910-02"}]
    }], "num_records": 1}, None)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "initiator_group_name", "vserver", "path", "nodes"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_successful_add_node():
    ''' Test successful add and idempotent check '''
    register_responses([
        ('lun-map-get-iter', ZRR['node_info']),
        ('lun-map-add-reporting-nodes', ZRR['success']),
        ('lun-map-get-iter', ZRR['nodes_info']),
    ])
    args = {'nodes': ['ontap910-01', 'ontap910-02']}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_successful_remove_node():
    ''' Test successful remove and idempotent check '''
    register_responses([
        ('lun-map-get-iter', ZRR['nodes_info']),
        ('lun-map-remove-reporting-nodes', ZRR['success']),
        ('lun-map-get-iter', ZRR['node_info']),
    ])
    args = {'nodes': 'ontap910-02', 'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('lun-map-get-iter', ZRR['no_records']),
        ('lun-map-get-iter', ZRR['error']),
        ('lun-map-add-reporting-nodes', ZRR['error']),
        ('lun-map-remove-reporting-nodes', ZRR['error']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/san/lun-maps', SRR['generic_error']),
        ('POST', 'protocols/san/lun-maps/3edf6t/3edf62/reporting-nodes', SRR['generic_error']),
        ('DELETE', 'protocols/san/lun-maps/3edf6t/3edf62/reporting-nodes/3dr567', SRR['generic_error']),
        ('GET', 'cluster', SRR['is_rest_9_9_1'])
    ])
    node_obj = create_module(my_module, DEFAULT_ARGS)
    assert 'Error: LUN map not found' in expect_and_capture_ansible_exception(node_obj.apply, 'fail')['msg']
    assert 'Error getting LUN' in expect_and_capture_ansible_exception(node_obj.get_lun_map_reporting_nodes, 'fail')['msg']
    assert 'Error creating LUN map reporting nodes' in expect_and_capture_ansible_exception(node_obj.add_lun_map_reporting_nodes, 'fail', 'node1')['msg']
    assert 'Error deleting LUN map reporting node' in expect_and_capture_ansible_exception(node_obj.remove_lun_map_reporting_nodes, 'fail', 'node1')['msg']

    node_obj = create_module(my_module, DEFAULT_ARGS, {'use_rest': 'always'})
    node_obj.lun_uuid, node_obj.igroup_uuid = '3edf6t', '3edf62'
    node_obj.nodes_uuids = {'node1': '3dr567'}
    assert 'Error getting LUN' in expect_and_capture_ansible_exception(node_obj.get_lun_map_reporting_nodes, 'fail')['msg']
    assert 'Error creating LUN map reporting node' in expect_and_capture_ansible_exception(node_obj.add_lun_map_reporting_nodes_rest, 'fail', 'node1')['msg']
    assert 'Error deleting LUN map reporting node' in expect_and_capture_ansible_exception(node_obj.remove_lun_map_reporting_nodes_rest, 'fail', 'node1')['msg']
    assert 'REST requires ONTAP 9.10.1 or later' in create_module(my_module, DEFAULT_ARGS, {'use_rest': 'always'}, fail=True)['msg']


def test_successful_add_node_rest():
    ''' Test successful add and idempotent check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/san/lun-maps', SRR['node_info']),
        ('POST', 'protocols/san/lun-maps/ea78ec41/8b8aa177/reporting-nodes', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/san/lun-maps', SRR['nodes_info'])
    ])
    args = {'nodes': ['ontap910-01', 'ontap910-02'], 'use_rest': 'always'}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_successful_remove_node_rest():
    ''' Test successful remove and idempotent check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/san/lun-maps', SRR['nodes_info']),
        ('DELETE', 'protocols/san/lun-maps/ea78ec41/8b8aa177/reporting-nodes/20f6b3d6', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/san/lun-maps', SRR['node_info'])
    ])
    args = {'nodes': 'ontap910-02', 'state': 'absent', 'use_rest': 'always'}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, args)['changed']
