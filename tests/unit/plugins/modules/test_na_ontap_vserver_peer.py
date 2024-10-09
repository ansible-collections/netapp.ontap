# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import call_main, set_module_args, \
    AnsibleFailJson, patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception, assert_warning_was_raised, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_vserver_peer \
    import NetAppONTAPVserverPeer as vserver_peer, main as my_main      # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

DEFAULT_ARGS = {
    'vserver': 'test',
    'peer_vserver': 'test_peer',
    'peer_cluster': 'test_cluster_peer',
    'local_name_for_peer': 'peer_name',
    'local_name_for_source': 'source_name',
    'applications': ['snapmirror'],
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'feature_flags': {'no_cserver_ems': True},
    'use_rest': 'never'
}

vserver_peer_info = {
    'num-records': 1,
    'attributes-list': {
        'vserver-peer-info': {
            'remote-vserver-name': 'test_peer',
            'vserver': 'test',
            'peer-vserver': 'test_peer',
            'peer-state': 'peered'
        }
    }
}

cluster_info = {
    'attributes': {
        'cluster-identity-info': {'cluster-name': 'test_cluster_peer'}
    }
}

ZRR = zapi_responses({
    'vserver_peer_info': build_zapi_response(vserver_peer_info),
    'cluster_info': build_zapi_response(cluster_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_obj = vserver_peer()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_successful_create():
    ''' Test successful create '''
    register_responses([
        ('vserver-peer-get-iter', ZRR['empty']),
        ('vserver-peer-create', ZRR['success']),
        ('vserver-peer-get-iter', ZRR['vserver_peer_info']),
        ('vserver-peer-accept', ZRR['success'])
    ])
    args = {'dest_hostname': 'test_destination'}
    assert create_and_apply(vserver_peer, DEFAULT_ARGS, args)['changed']


def test_successful_create_new_style():
    ''' Test successful create '''
    register_responses([
        ('vserver-peer-get-iter', ZRR['empty']),
        ('vserver-peer-create', ZRR['success']),
        ('vserver-peer-get-iter', ZRR['vserver_peer_info']),
        ('vserver-peer-accept', ZRR['success'])
    ])
    default_args = DEFAULT_ARGS
    # test without local name
    del default_args['local_name_for_peer']
    del default_args['local_name_for_source']
    args = {'peer_options': {'hostname': 'test_destination'}}
    assert create_and_apply(vserver_peer, default_args, args)['changed']


def test_create_idempotency():
    ''' Test create idempotency '''
    register_responses([
        ('vserver-peer-get-iter', ZRR['vserver_peer_info'])
    ])
    args = {'peer_options': {'hostname': 'test_destination'}}
    assert create_and_apply(vserver_peer, DEFAULT_ARGS, args)['changed'] is False


def test_successful_delete():
    ''' Test successful delete peer '''
    register_responses([
        ('vserver-peer-get-iter', ZRR['vserver_peer_info']),
        ('vserver-peer-delete', ZRR['success'])
    ])
    args = {
        'peer_options': {'hostname': 'test_destination'},
        'state': 'absent'
    }
    assert create_and_apply(vserver_peer, DEFAULT_ARGS, args)['changed']


def test_delete_idempotency():
    ''' Test delete idempotency '''
    register_responses([
        ('vserver-peer-get-iter', ZRR['empty'])
    ])
    args = {'dest_hostname': 'test_destination', 'state': 'absent'}
    assert create_and_apply(vserver_peer, DEFAULT_ARGS, args)['changed'] is False


def test_helper_vserver_peer_get_iter():
    ''' Test vserver_peer_get_iter method '''
    args = {'dest_hostname': 'test_destination'}
    obj = create_module(vserver_peer, DEFAULT_ARGS, args)
    result = obj.vserver_peer_get_iter('source')
    print(result.to_string(pretty=True))
    assert result['query'] is not None
    assert result['query']['vserver-peer-info'] is not None
    info = result['query']['vserver-peer-info']
    assert info['vserver'] == DEFAULT_ARGS['vserver']
    assert info['remote-vserver-name'] == DEFAULT_ARGS['peer_vserver']


def test_dest_hostname_absent():
    my_obj = create_module(vserver_peer, DEFAULT_ARGS)
    assert my_obj.parameters['hostname'] == my_obj.parameters['dest_hostname']


def test_get_packet():
    ''' Test vserver_peer_get method '''
    register_responses([
        ('vserver-peer-get-iter', ZRR['vserver_peer_info'])
    ])
    args = {'dest_hostname': 'test_destination'}
    obj = create_module(vserver_peer, DEFAULT_ARGS, args)
    result = obj.vserver_peer_get()
    assert 'vserver' in result.keys()
    assert 'peer_vserver' in result.keys()
    assert 'peer_state' in result.keys()


def test_error_on_missing_params_create():
    ''' Test error thrown from vserver_peer_create '''
    register_responses([
        ('vserver-peer-get-iter', ZRR['empty'])
    ])
    default_args = DEFAULT_ARGS.copy()
    del default_args['applications']
    args = {'dest_hostname': 'test_destination'}
    msg = create_and_apply(vserver_peer, default_args, args, fail=True)['msg']
    assert 'applications parameter is missing' in msg


def test_get_peer_cluster_called():
    ''' Test get_peer_cluster_name called if peer_cluster is missing '''
    register_responses([
        ('vserver-peer-get-iter', ZRR['empty']),
        ('cluster-identity-get', ZRR['cluster_info']),
        ('vserver-peer-create', ZRR['success']),
        ('vserver-peer-get-iter', ZRR['vserver_peer_info']),
        ('vserver-peer-accept', ZRR['success'])
    ])
    default_args = DEFAULT_ARGS.copy()
    del default_args['peer_cluster']
    args = {'dest_hostname': 'test_destination'}
    assert create_and_apply(vserver_peer, default_args, args)['changed']


def test_get_peer_cluster_packet():
    ''' Test get_peer_cluster_name xml packet '''
    register_responses([
        ('cluster-identity-get', ZRR['cluster_info'])
    ])
    args = {'dest_hostname': 'test_destination'}
    obj = create_module(vserver_peer, DEFAULT_ARGS, args)
    result = obj.get_peer_cluster_name()
    assert result == DEFAULT_ARGS['peer_cluster']


def test_error_on_first_ZAPI_call():
    ''' Test error thrown from vserver_peer_get '''
    register_responses([
        ('vserver-peer-get-iter', ZRR['error'])
    ])
    args = {'dest_hostname': 'test_destination'}
    msg = create_and_apply(vserver_peer, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error fetching vserver peer' in msg


def test_error_create_new_style():
    ''' Test error in create - peer not visible '''
    register_responses([
        ('vserver-peer-get-iter', ZRR['empty']),
        ('vserver-peer-create', ZRR['success']),
        ('vserver-peer-get-iter', ZRR['empty'])
    ])
    args = {'peer_options': {'hostname': 'test_destination'}}
    msg = create_and_apply(vserver_peer, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error retrieving vserver peer information while accepting' in msg


def test_if_all_methods_catch_exception():
    register_responses([
        ('vserver-peer-delete', ZRR['error']),
        ('cluster-identity-get', ZRR['error']),
        ('vserver-peer-create', ZRR['error'])
    ])
    args = {'dest_hostname': 'test_destination'}
    my_obj = create_module(vserver_peer, DEFAULT_ARGS, args)

    error = expect_and_capture_ansible_exception(my_obj.vserver_peer_delete, 'fail', current={'local_peer_vserver': 'test_peer'})['msg']
    assert 'Error deleting vserver peer test: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.get_peer_cluster_name, 'fail')['msg']
    assert 'Error fetching peer cluster name for peer vserver test_peer: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.vserver_peer_create, 'fail')['msg']
    assert 'Error creating vserver peer test: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error


def test_error_in_vserver_accept():
    register_responses([
        ('vserver-peer-get-iter', ZRR['empty']),
        ('vserver-peer-create', ZRR['success']),
        ('vserver-peer-get-iter', ZRR['vserver_peer_info']),
        ('vserver-peer-accept', ZRR['error'])
    ])
    args = {'dest_hostname': 'test_destination'}
    msg = create_and_apply(vserver_peer, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error accepting vserver peer test_peer: NetApp API failed. Reason - 12345:synthetic error for UT purpose' == msg


DEFAULT_ARGS_REST = {
    "hostname": "10.193.177.97",
    "username": "admin",
    "password": "netapp123",
    "https": "yes",
    "validate_certs": "no",
    "use_rest": "always",
    "state": "present",
    "dest_hostname": "0.0.0.0",
    "vserver": "svmsrc3",
    "peer_vserver": "svmdst3",
    "applications": ['snapmirror']
}


SRR = rest_responses({
    'vserver_peer_info': (200, {
        "records": [{
            "vserver": "svmsrc1",
            "peer_vserver": "svmdst1",
            "name": "svmdst1",
            "state": "peered",
            "local_peer_vserver_uuid": "545d2562-2fca-11ec-8016-005056b3f5d5"
        }],
        'num_records': 1
    }, None),
    'cluster_info': (200, {"name": "mohanontap98cluster"}, None),
    'job_info': (200, {
        "job": {
            "uuid": "d78811c1-aebc-11ec-b4de-005056b30cfa",
            "_links": {"self": {"href": "/api/cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa"}}
        }}, None),
    'job_not_found': (404, "", {"message": "entry doesn't exist", "code": "4", "target": "uuid"})
})


def test_ensure_get_server_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['vserver_peer_info'])
    ])
    assert create_and_apply(vserver_peer, DEFAULT_ARGS_REST)['changed'] is False


def test_ensure_create_server_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['empty_records']),
        ('POST', 'svm/peers', SRR['success']),
        ('GET', 'svm/peers', SRR['vserver_peer_info']),
        ('PATCH', 'svm/peers', SRR['success'])
    ])
    assert create_and_apply(vserver_peer, DEFAULT_ARGS_REST, {'peer_cluster': 'peer_cluster'})['changed']


def test_ensure_delete_server_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['vserver_peer_info']),
        ('DELETE', 'svm/peers', SRR['success'])
    ])
    assert create_and_apply(vserver_peer, DEFAULT_ARGS_REST, {'state': 'absent'})['changed']


def test_create_vserver_peer_without_cluster_name_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['empty_records']),
        ('GET', 'cluster', SRR['cluster_info']),
        ('POST', 'svm/peers', SRR['success']),
        ('GET', 'svm/peers', SRR['vserver_peer_info']),
        ('PATCH', 'svm/peers', SRR['success'])
    ])
    assert create_and_apply(vserver_peer, DEFAULT_ARGS_REST)['changed']


def test_create_vserver_peer_with_local_name_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['empty_records']),
        ('GET', 'cluster', SRR['cluster_info']),
        ('POST', 'svm/peers', SRR['success']),
        ('GET', 'svm/peers', SRR['vserver_peer_info']),
        ('PATCH', 'svm/peers', SRR['success'])
    ])
    args = {
        'local_name_for_peer': 'peer',
        'local_name_for_source': 'source'
    }
    assert create_and_apply(vserver_peer, DEFAULT_ARGS_REST, args)['changed']


def test_error_in_vserver_accept_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['empty_records']),
        ('GET', 'cluster', SRR['cluster_info']),
        ('POST', 'svm/peers', SRR['success']),
        ('GET', 'svm/peers', SRR['vserver_peer_info']),
        ('PATCH', 'svm/peers', SRR['generic_error'])
    ])
    msg = create_and_apply(vserver_peer, DEFAULT_ARGS_REST, fail=True)['msg']
    assert 'Error accepting vserver peer relationship on svmdst3: calling: svm/peers: got Expected error.' == msg


def test_error_in_vserver_get_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['generic_error'])
    ])
    msg = create_and_apply(vserver_peer, DEFAULT_ARGS_REST, fail=True)['msg']
    assert 'Error fetching vserver peer svmsrc3: calling: svm/peers: got Expected error.' == msg


def test_error_in_vserver_delete_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['vserver_peer_info']),
        ('DELETE', 'svm/peers', SRR['generic_error'])
    ])
    msg = create_and_apply(vserver_peer, DEFAULT_ARGS_REST, {'state': 'absent'}, fail=True)['msg']
    assert 'Error deleting vserver peer relationship on svmsrc3: calling: svm/peers: got Expected error.' == msg


def test_error_in_peer_cluster_get_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['empty_records']),
        ('GET', 'cluster', SRR['generic_error'])
    ])
    msg = create_and_apply(vserver_peer, DEFAULT_ARGS_REST, fail=True)['msg']
    assert 'Error fetching peer cluster name for peer vserver svmdst3: calling: cluster: got Expected error.' == msg


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_missing_netapp_lib(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    msg = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert msg == create_module(vserver_peer, DEFAULT_ARGS, fail=True)['msg']


@patch('time.sleep')
def test_job_error_in_vserver_delete_rest(dont_sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['vserver_peer_info']),
        ('DELETE', 'svm/peers', SRR['job_info']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found'])
    ])
    assert create_and_apply(vserver_peer, DEFAULT_ARGS_REST, {'state': 'absent'})['changed']
    print_warnings()
    assert_warning_was_raised('Ignoring job status, assuming success - Issue #45.')


@patch('time.sleep')
def test_job_error_in_vserver_create_rest(dont_sleep):
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/peers', SRR['empty_records']),
        ('GET', 'cluster', SRR['empty_records']),
        ('POST', 'svm/peers', SRR['job_info']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'svm/peers', SRR['empty_records']),
    ])
    assert call_main(my_main, DEFAULT_ARGS_REST, fail=True)['msg'] == 'Error reading vserver peer information on peer svmdst3'
    print_warnings()
    assert_warning_was_raised('Ignoring job status, assuming success - Issue #45.')
