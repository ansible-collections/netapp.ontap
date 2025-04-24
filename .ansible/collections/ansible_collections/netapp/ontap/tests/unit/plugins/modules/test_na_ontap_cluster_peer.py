''' unit tests ONTAP Ansible module: na_ontap_cluster_peer '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, patch_ansible, create_and_apply
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster_peer \
    import NetAppONTAPClusterPeer as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


def update_cluster_peer_info_zapi(cluster_name, peer_addresses):
    return {
        'num-records': 1,
        'attributes-list': {
            'cluster-peer-info': {
                'cluster-name': cluster_name,
                'peer-addresses': peer_addresses
            }
        }
    }


ZRR = zapi_responses({
    'cluster_peer_info_source': build_zapi_response(update_cluster_peer_info_zapi('cluster1', '1.2.3.6,1.2.3.7')),
    'cluster_peer_info_remote': build_zapi_response(update_cluster_peer_info_zapi('cluster2', '1.2.3.4,1.2.3.5'))
})


DEFAULT_ARGS_ZAPI = {
    'source_intercluster_lifs': '1.2.3.4,1.2.3.5',
    'dest_intercluster_lifs': '1.2.3.6,1.2.3.7',
    'passphrase': 'netapp123',
    'dest_hostname': '10.20.30.40',
    'dest_cluster_name': 'cluster2',
    'encryption_protocol_proposed': 'none',
    'ipspace': 'Default',
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'never',
    'feature_flags': {'no_cserver_ems': True}
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_successful_create():
    ''' Test successful create '''
    register_responses([
        ('cluster-peer-get-iter', ZRR['empty']),
        ('cluster-peer-get-iter', ZRR['empty']),
        ('cluster-peer-create', ZRR['empty']),
        ('cluster-peer-create', ZRR['empty'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS_ZAPI)


def test_create_idempotency():
    ''' Test create idempotency '''
    register_responses([
        ('cluster-peer-get-iter', ZRR['cluster_peer_info_source']),
        ('cluster-peer-get-iter', ZRR['cluster_peer_info_remote'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS_ZAPI)


def test_successful_delete():
    ''' Test delete existing cluster peer '''
    module_args = {
        'state': 'absent',
        'source_cluster_name': 'cluster1'
    }
    register_responses([
        ('cluster-peer-get-iter', ZRR['cluster_peer_info_source']),
        ('cluster-peer-get-iter', ZRR['cluster_peer_info_remote']),
        ('cluster-peer-delete', ZRR['empty']),
        ('cluster-peer-delete', ZRR['empty'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS_ZAPI, module_args)


def test_delete_idempotency():
    ''' Test delete idempotency '''
    module_args = {
        'state': 'absent',
        'source_cluster_name': 'cluster1'
    }
    register_responses([
        ('cluster-peer-get-iter', ZRR['empty']),
        ('cluster-peer-get-iter', ZRR['empty'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS_ZAPI, module_args)


def test_error_get_cluster_peer():
    ''' Test get error '''
    register_responses([
        ('cluster-peer-get-iter', ZRR['error']),
    ])
    error = create_and_apply(my_module, DEFAULT_ARGS_ZAPI, fail=True)['msg']
    assert 'Error fetching cluster peer source: NetApp API failed. Reason - 12345:synthetic error for UT purpose' == error


def test_error_delete_cluster_peer():
    ''' Test delete error '''
    module_args = {
        'state': 'absent',
        'source_cluster_name': 'cluster1'
    }
    register_responses([
        ('cluster-peer-get-iter', ZRR['cluster_peer_info_source']),
        ('cluster-peer-get-iter', ZRR['cluster_peer_info_remote']),
        ('cluster-peer-delete', ZRR['error'])
    ])
    error = create_and_apply(my_module, DEFAULT_ARGS_ZAPI, module_args, fail=True)['msg']
    assert 'Error deleting cluster peer cluster2: NetApp API failed. Reason - 12345:synthetic error for UT purpose' == error


def test_error_create_cluster_peer():
    ''' Test create error '''
    register_responses([
        ('cluster-peer-get-iter', ZRR['empty']),
        ('cluster-peer-get-iter', ZRR['empty']),
        ('cluster-peer-create', ZRR['error'])
    ])
    error = create_and_apply(my_module, DEFAULT_ARGS_ZAPI, fail=True)['msg']
    assert 'Error creating cluster peer [\'1.2.3.6\', \'1.2.3.7\']: NetApp API failed. Reason - 12345:synthetic error for UT purpose' == error


SRR = rest_responses({
    'cluster_peer_dst': (200, {"records": [
        {
            "uuid": "1e698aba-2aa6-11ec-b7be-005056b366e1",
            "name": "mohan9cluster2",
            "remote": {
                "name": "mohan9cluster2",
                "serial_number": "1-80-000011",
                "ip_addresses": ["10.193.179.180"]
            }
        }
    ], "num_records": 1}, None),
    'cluster_peer_src': (200, {"records": [
        {
            "uuid": "1fg98aba-2aa6-11ec-b7be-005fgvb366e1",
            "name": "mohanontap98cluster",
            "remote": {
                "name": "mohanontap98cluster",
                "serial_number": "1-80-000031",
                "ip_addresses": ["10.193.179.57"]
            }
        }
    ], "num_records": 1}, None),
    'passphrase_response': (200, {"records": [
        {
            "uuid": "4b71a7fb-45ff-11ec-95ea-005056b3b297",
            "name": "",
            "authentication": {
                "passphrase": "ajdHOvAFSs0LOO0S27GtJZfV",
                "expiry_time": "2022-02-22T22:30:18-05:00"
            }
        }
    ], "num_records": 1}, None)
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'source_cluster_name': 'mohan9cluster2',
    'source_intercluster_lifs': ['10.193.179.180'],
    'dest_hostname': '10.193.179.197',
    'dest_cluster_name': 'mohanontap98cluster',
    'dest_intercluster_lifs': ['10.193.179.57'],
    'passphrase': 'ontapcluster_peer',
    'encryption_protocol_proposed': 'none',
    'ipspace': 'Default'
}


def test_successful_create_rest():
    ''' Test successful create '''
    args = DEFAULT_ARGS
    del args['encryption_protocol_proposed']
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['empty_records']),
        ('GET', 'cluster/peers', SRR['empty_records']),
        ('POST', 'cluster/peers', SRR['empty_good']),
        ('POST', 'cluster/peers', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, args)


def test_create_idempotency_rest():
    ''' Test successful create idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['cluster_peer_src']),
        ('GET', 'cluster/peers', SRR['cluster_peer_dst'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)


def test_successful_create_without_passphrase_rest():
    ''' Test successful create '''
    args = DEFAULT_ARGS
    del args['passphrase']
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['empty_records']),
        ('GET', 'cluster/peers', SRR['empty_records']),
        ('POST', 'cluster/peers', SRR['passphrase_response']),
        ('POST', 'cluster/peers', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, args)


def test_successful_delete_rest():
    ''' Test successful delete '''
    module_args = {'state': 'absent'}
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['cluster_peer_src']),
        ('GET', 'cluster/peers', SRR['cluster_peer_dst']),
        ('DELETE', 'cluster/peers/1fg98aba-2aa6-11ec-b7be-005fgvb366e1', SRR['empty_good']),
        ('DELETE', 'cluster/peers/1e698aba-2aa6-11ec-b7be-005056b366e1', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)


def test_delete_idempotency_rest():
    ''' Test delete idempotency '''
    module_args = {'state': 'absent'}
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['empty_records']),
        ('GET', 'cluster/peers', SRR['empty_records'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)


def test_successful_modify_rest():
    ''' Test successful modify '''
    module_args = DEFAULT_ARGS
    module_args['dest_intercluster_lifs'] = ['10.193.179.58']
    module_args['source_intercluster_lifs'] = ['10.193.179.181']
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['cluster_peer_src']),
        ('GET', 'cluster/peers', SRR['cluster_peer_dst']),
        ('PATCH', 'cluster/peers/1fg98aba-2aa6-11ec-b7be-005fgvb366e1', SRR['empty_good']),
        ('PATCH', 'cluster/peers/1e698aba-2aa6-11ec-b7be-005056b366e1', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, module_args)


def test_modify_idempotency_rest():
    ''' Test successful modify idempotency '''
    module_args = DEFAULT_ARGS
    module_args['dest_intercluster_lifs'] = ['10.193.179.58']
    module_args['source_intercluster_lifs'] = ['10.193.179.181']
    SRR['cluster_peer_src'][1]['records'][0]['remote']['ip_addresses'] = ['10.193.179.58']
    SRR['cluster_peer_dst'][1]['records'][0]['remote']['ip_addresses'] = ['10.193.179.181']
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['cluster_peer_src']),
        ('GET', 'cluster/peers', SRR['cluster_peer_dst'])
    ])
    assert create_and_apply(my_module, module_args)


def test_error_get_cluster_peer_rest():
    ''' Test get error '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'calling: cluster/peers: got Expected error.' == error


def test_error_delete_cluster_peer_rest():
    ''' Test delete error '''
    module_args = {'state': 'absent'}
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['cluster_peer_src']),
        ('GET', 'cluster/peers', SRR['cluster_peer_dst']),
        ('DELETE', 'cluster/peers/1fg98aba-2aa6-11ec-b7be-005fgvb366e1', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'calling: cluster/peers/1fg98aba-2aa6-11ec-b7be-005fgvb366e1: got Expected error.' == error


def test_error_create_cluster_peer_rest():
    ''' Test create error '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['empty_records']),
        ('GET', 'cluster/peers', SRR['empty_records']),
        ('POST', 'cluster/peers', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'calling: cluster/peers: got Expected error.' == error


def test_error_modify_cluster_peer_rest():
    ''' Test modify error '''
    module_args = DEFAULT_ARGS
    module_args['dest_intercluster_lifs'] = ['10.193.179.59']
    module_args['source_intercluster_lifs'] = ['10.193.179.180']
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster/peers', SRR['cluster_peer_src']),
        ('GET', 'cluster/peers', SRR['cluster_peer_dst']),
        ('PATCH', 'cluster/peers/1fg98aba-2aa6-11ec-b7be-005fgvb366e1', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'calling: cluster/peers/1fg98aba-2aa6-11ec-b7be-005fgvb366e1: got Expected error.' == error
