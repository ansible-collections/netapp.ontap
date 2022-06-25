''' unit tests ONTAP Ansible module: na_ontap_snapmirror '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_no_warnings, assert_warning_was_raised, expect_and_capture_ansible_exception, call_main, create_module, patch_ansible, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror \
    import NetAppONTAPSnapmirror as my_module, main as my_main

HAS_SF_COMMON = True
try:
    from solidfire.common import ApiServerError
except ImportError:
    HAS_SF_COMMON = False

if not HAS_SF_COMMON:
    pytestmark = pytest.mark.skip('skipping as missing required solidfire.common')

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


DEFAULT_ARGS = {
    "hostname": "10.193.189.206",
    "username": "admin",
    "password": "netapp123",
    "https": "yes",
    "validate_certs": "no",
    "state": "present",
    "initialize": "True",
    "relationship_state": "active",
    "source_path": "svmsrc3:volsrc1",
    "destination_path": "svmdst3:voldst1",
    "relationship_type": "extended_data_protection"
}


def sm_rest_info(state, healthy, transfer_state=None, destination_path=DEFAULT_ARGS['destination_path']):
    record = {
        'uuid': 'b5ee4571-5429-11ec-9779-005056b39a06',
        'destination': {
            'path': destination_path
        },
        'policy': {
            'name': 'MirrorAndVault'
        },
        'state': state,
        'healthy': healthy,
    }
    if transfer_state:
        record['transfer'] = {'state': transfer_state}
        if transfer_state == 'transferring':
            record['transfer']['uuid'] = 'xfer_uuid'
    if healthy is False:
        record['unhealthy_reason'] = 'this is why the relationship is not healthy.'

    return {
        'records': [record],
        'num_records': 1
    }


sm_policies = {
    # We query only on the policy name, as it can be at the vserver or cluster scope.
    # So we can have ghost records from other SVMs.
    'records': [
        {
            'type': 'sync',
            'svm': {'name': 'other'}
        },
        {
            'type': 'async',
            'svm': {'name': 'svmdst3'}
        },
        {
            'type': 'svm_invalid',
            'svm': {'name': 'bad_type'}
        },
        {
            'type': 'system_invalid',
        },
    ],
    'num_records': 4,
}


svm_peer_info = {
    'records': [{
        'peer': {
            'svm': {'name': 'vserver'},
            'cluster': {'name': 'cluster'},
        }
    }]
}


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'sm_get_uninitialized': (200, sm_rest_info('uninitialized', True), None),
    'sm_get_uninitialized_xfering': (200, sm_rest_info('uninitialized', True, 'transferring'), None),
    'sm_get_mirrored': (200, sm_rest_info('snapmirrored', True, 'success'), None),
    'sm_get_restore': (200, sm_rest_info('snapmirrored', True, 'success', destination_path=DEFAULT_ARGS['source_path']), None),
    'sm_get_paused': (200, sm_rest_info('paused', True, 'success'), None),
    'sm_get_broken': (200, sm_rest_info('broken_off', True, 'success'), None),
    'sm_get_data_transferring': (200, sm_rest_info('transferring', True, 'transferring'), None),
    'sm_get_abort': (200, sm_rest_info('sm_get_abort', False, 'failed'), None),
    'sm_get_resync': (200, {
        'uuid': 'b5ee4571-5429-11ec-9779-005056b39a06',
        'description': 'PATCH /api/snapmirror/relationships/1c4467ca-5434-11ec-9779-005056b39a06',
        'state': 'success',
        'message': 'success',
        'code': 0,
    }, None),
    'job_status': (201, {
        'job': {
            'uuid': '3a23a60e-542c-11ec-9779-005056b39a06',
            '_links': {
                'self': {
                    'href': '/api/cluster/jobs/3a23a60e-542c-11ec-9779-005056b39a06'
                }
            }
        }
    }, None),
    'sm_policies': (200, sm_policies, None),
    'svm_peer_info': (200, svm_peer_info, None),
})


def sm_info(mirror_state, status, quiesce_status, relationship_type='extended_data_protection', source='ansible:volsrc1'):

    return {
        'num-records': 1,
        'status': quiesce_status,
        'attributes-list': {
            'snapmirror-info': {
                'mirror-state': mirror_state,
                'schedule': None,
                'source-location': source,
                'relationship-status': status,
                'policy': 'ansible_policy',
                'relationship-type': relationship_type,
                'max-transfer-rate': 10000,
                'identity-preserve': 'true',
                'last-transfer-error': 'last_transfer_error',
                'is-healthy': 'true',
                'unhealthy-reason': 'unhealthy_reason',
            },
            'snapmirror-destination-info': {
                'destination-location': 'ansible'
            }
        }
    }


# we only test for existence, contents do not matter
volume_info = {
    'num-records': 1,
}


vserver_peer_info = {
    'num-records': 1,
    'attributes-list': {
        'vserver-peer-info': {
            'remote-vserver-name': 'svmsrc3',
            'peer-cluster': 'cluster',
        }
    }
}


ZRR = zapi_responses({
    'sm_info': build_zapi_response(sm_info(None, 'idle', 'passed')),
    'sm_info_broken_off': build_zapi_response(sm_info('broken_off', 'idle', 'passed')),
    'sm_info_snapmirrored': build_zapi_response(sm_info('snapmirrored', 'idle', 'passed')),
    'sm_info_snapmirrored_from_element': build_zapi_response(sm_info('snapmirrored', 'idle', 'passed', source='10.10.10.11:/lun/1000')),
    'sm_info_snapmirrored_to_element': build_zapi_response(sm_info('snapmirrored', 'idle', 'passed', source='svmsrc3:volsrc1')),
    'sm_info_snapmirrored_load_sharing': build_zapi_response(sm_info('snapmirrored', 'idle', 'passed', 'load_sharing')),
    'sm_info_snapmirrored_vault': build_zapi_response(sm_info('snapmirrored', 'idle', 'passed', 'vault')),
    'sm_info_snapmirrored_quiesced': build_zapi_response(sm_info('snapmirrored', 'quiesced', 'passed')),
    'sm_info_uninitialized': build_zapi_response(sm_info('uninitialized', 'idle', 'passed')),
    'sm_info_uninitialized_load_sharing': build_zapi_response(sm_info('uninitialized', 'idle', 'passed', 'load_sharing')),
    'volume_info': build_zapi_response(volume_info),
    'vserver_peer_info': build_zapi_response(vserver_peer_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    msg = "missing required arguments: hostname"
    assert create_module(my_module, {}, fail=True)['msg'] == msg


def test_module_fail_unsuuported_rest_options():
    ''' required arguments are reported as errors '''
    module_args = {
        "use_rest": "never",
        "create_destination": {"enabled": True},
    }
    errors = [
        'Error: using any of',
        'create_destination',
        'requires ONTAP 9.7 or later and REST must be enabled - using ZAPI.'
    ]
    for error in errors:
        assert error in create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


if netapp_utils.has_netapp_lib():
    zapi_create_responses = [
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),     # ONTAP to ONTAP
        ('ZAPI', 'snapmirror-create', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-initialize', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # check status
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # check health
    ]
else:
    zapi_create_responses = []


@patch('time.sleep')
def test_successful_create_with_source(dont_sleep):
    ''' creating snapmirror and testing idempotency '''
    # earlier versions of pythons don't support *zapi_create_responses
    responses = list(zapi_create_responses)
    responses.extend([
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # ONTAP to ONTAP
        ('ZAPI', 'vserver-peer-get-iter', ZRR['vserver_peer_info']),    # validate source svm
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # ONTAP to ONTAP, check for update
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check health
    ])
    register_responses(responses)
    module_args = {
        "use_rest": "never",
        "source_hostname": "10.10.10.10",
        "schedule": "abc",
        "identity_preserve": True,
        "relationship_type": "data_protection",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args.pop('schedule')
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_successful_create_with_peer(dont_sleep):
    ''' creating snapmirror and testing idempotency '''
    register_responses(zapi_create_responses)
    module_args = {
        "use_rest": "never",
        "peer_options": {"hostname": "10.10.10.10"},
        "schedule": "abc",
        "identity_preserve": True,
        "relationship_type": "data_protection",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_negative_break(dont_sleep):
    ''' breaking snapmirror to test quiesce time-delay failure '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'vserver-peer-get-iter', ZRR['vserver_peer_info']),    # validate source svm
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # 5 retries
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
    ])
    module_args = {
        "use_rest": "never",
        "source_hostname": "10.10.10.10",
        "relationship_state": "broken",
        "relationship_type": "data_protection",
    }
    msg = "Taking a long time to quiesce SnapMirror relationship, try again later"
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


@patch('time.sleep')
def test_successful_break(dont_sleep):
    ''' breaking snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'vserver-peer-get-iter', ZRR['vserver_peer_info']),    # validate source svm
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
        ('ZAPI', 'snapmirror-break', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check health
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_broken_off']),
        ('ZAPI', 'vserver-peer-get-iter', ZRR['vserver_peer_info']),    # validate source svm
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check health
    ])
    module_args = {
        "use_rest": "never",
        "source_hostname": "10.10.10.10",
        "relationship_state": "broken",
        "relationship_type": "data_protection",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_create_without_initialize():
    ''' creating snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),             # ONTAP to ONTAP
        ('ZAPI', 'snapmirror-create', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check health
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # ONTAP to ONTAP
        ('ZAPI', 'vserver-peer-get-iter', ZRR['vserver_peer_info']),    # validate source svm
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # ONTAP to ONTAP, check for update
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check health
    ])
    module_args = {
        "use_rest": "never",
        "source_hostname": "10.10.10.10",
        "schedule": "abc",
        "relationship_type": "data_protection",
        "initialize": False,
        "policy": 'ansible_policy',
        "max_transfer_rate": 10000,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args.pop('schedule')
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_negative_set_source_peer():
    module_args = {
        'connection_type': 'ontap_elementsw'
    }
    error = 'Error: peer_options are required to identify ONTAP cluster with connection_type: ontap_elementsw'
    assert error in create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args = {
        'connection_type': 'elementsw_ontap'
    }
    error = 'Error: peer_options are required to identify SolidFire cluster with connection_type: elementsw_ontap'
    assert error in create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.create_sf_connection')
def test_set_element_connection(mock_create_sf_cx):
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'peer_options': {'hostname': 'any'}
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    elementsw_helper, elem = my_obj.set_element_connection('source')
    assert elementsw_helper is not None
    assert elem is not None
    elementsw_helper, elem = my_obj.set_element_connection('destination')
    assert elementsw_helper is not None
    assert elem is not None


@patch('time.sleep')
@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror.NetAppONTAPSnapmirror.set_element_connection')
def test_successful_element_ontap_create(connection, dont_sleep):
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),             # element to ONTAP
        ('ZAPI', 'snapmirror-create', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-initialize', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check status
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check health
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_from_element']),      # element to ONTAP
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # element to ONTAP, check for update
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check health
    ])
    mock_elem, mock_helper = Mock(), Mock()
    connection.return_value = mock_helper, mock_elem
    mock_elem.get_cluster_info.return_value.cluster_info.svip = '10.10.10.11'
    module_args = {
        "use_rest": "never",
        "source_hostname": "10.10.10.10",
        "connection_type": "elementsw_ontap",
        "schedule": "abc",
        "source_path": "10.10.10.11:/lun/1000",
        "relationship_type": "data_protection",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args.pop('schedule')
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror.NetAppONTAPSnapmirror.set_element_connection')
def test_successful_ontap_element_create(connection, dont_sleep):
    ''' check elementsw parameters for source '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # an existing relationship is required element to ONTAP
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),             # ONTAP to element
        ('ZAPI', 'snapmirror-create', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-initialize', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check status
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # an existing relationship is required element to ONTAP
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_to_element']),    # ONTAP to element
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # ONTAP to element, check for update
    ])
    mock_elem, mock_helper = Mock(), Mock()
    connection.return_value = mock_helper, mock_elem
    mock_elem.get_cluster_info.return_value.cluster_info.svip = '10.10.10.11'
    module_args = {
        "use_rest": "never",
        "source_hostname": "10.10.10.10",
        "connection_type": "ontap_elementsw",
        "schedule": "abc",
        "destination_path": "10.10.10.11:/lun/1000",
        "relationship_type": "data_protection",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args.pop('schedule')
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_successful_delete(dont_sleep):
    ''' deleting snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'vserver-peer-get-iter', ZRR['vserver_peer_info']),    # validate source svm
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
        ('ZAPI', 'snapmirror-break', ZRR['success']),
        ('ZAPI', 'snapmirror-get-destination-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-release', ZRR['success']),
        ('ZAPI', 'snapmirror-destroy', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),                # check health
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),             # check health
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
        "source_hostname": "10.10.10.10",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_successful_delete_without_source_hostname_check(dont_sleep):
    ''' source cluster hostname is optional when source is unknown'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'vserver-peer-get-iter', ZRR['vserver_peer_info']),    # validate source svm
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
        ('ZAPI', 'snapmirror-break', ZRR['success']),
        ('ZAPI', 'snapmirror-destroy', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),             # check health
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_successful_delete_with_error_on_break(dont_sleep):
    ''' source cluster hostname is optional when source is unknown'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
        ('ZAPI', 'snapmirror-break', ZRR['error']),
        ('ZAPI', 'snapmirror-destroy', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
        "validate_source_path": False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised('Ignored error(s): Error breaking SnapMirror relationship: NetApp API failed. Reason - 12345:synthetic error for UT purpose')


@patch('time.sleep')
def test_negative_delete_error_with_error_on_break(dont_sleep):
    ''' source cluster hostname is optional when source is unknown'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
        ('ZAPI', 'snapmirror-break', ZRR['error']),
        ('ZAPI', 'snapmirror-destroy', ZRR['error']),
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
        "validate_source_path": False
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Previous error(s): Error breaking SnapMirror relationship: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error
    assert 'Error deleting SnapMirror:' in error


def test_negative_delete_with_destination_path_missing():
    ''' with misisng destination_path'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('destination_path')
    module_args = {
        "use_rest": "never",
        "state": "absent",
        "source_hostname": "source_host",
    }
    msg = "Missing parameters: Source path or Destination path"
    assert call_main(my_main, args, module_args, fail=True)['msg'] == msg


def test_successful_delete_check_get_destination():
    register_responses([
        ('ZAPI', 'snapmirror-get-destination-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-destination-iter', ZRR['no_records']),
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
        "source_hostname": "source_host",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.set_source_cluster_connection() is None
    assert my_obj.get_destination()
    assert my_obj.get_destination() is None


def test_snapmirror_release():
    register_responses([
        ('ZAPI', 'snapmirror-release', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never",
        "source_hostname": "source_host",
        "source_volume": "source_volume",
        "source_vserver": "source_vserver",
        "destination_volume": "destination_volume",
        "destination_vserver": "destination_vserver",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.set_source_cluster_connection() is None
    assert my_obj.snapmirror_release() is None


def test_snapmirror_resume():
    ''' resuming snapmirror '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
        ('ZAPI', 'snapmirror-resume', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # update reads mirror_state
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
        # idempotency test
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # update reads mirror_state
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
    ])
    module_args = {
        "use_rest": "never",
        "relationship_type": "data_protection",
        "validate_source_path": False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_snapmirror_restore():
    ''' restore snapmirror '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-restore', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
        # idempotency test - TODO
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-restore', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
    ])
    module_args = {
        "use_rest": "never",
        "relationship_type": "restore",
        "source_snapshot": "source_snapshot",
        "clean_up_failure": True,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    # TODO: should be idempotent!   But we don't read the current state!
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_successful_abort(dont_sleep):
    ''' aborting snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
        ('ZAPI', 'snapmirror-break', ZRR['success']),
        ('ZAPI', 'snapmirror-destroy', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
        # idempotency test
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
        "validate_source_path": False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify():
    ''' modifying snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-modify', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # update reads mirror_state
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
        # idempotency test
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # update reads mirror_state
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
    ])
    module_args = {
        "use_rest": "never",
        "relationship_type": "data_protection",
        "policy": "ansible2",
        "schedule": "abc2",
        "max_transfer_rate": 2000,
        "validate_source_path": False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        "use_rest": "never",
        "relationship_type": "data_protection",
        "validate_source_path": False
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_successful_initialize(dont_sleep):
    ''' initialize snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_uninitialized']),
        ('ZAPI', 'snapmirror-initialize', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check status
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # update reads mirror_state
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
        # 2nd run
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_uninitialized_load_sharing']),
        ('ZAPI', 'snapmirror-initialize-ls-set', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check status
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # update reads mirror_state
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
    ])
    module_args = {
        "use_rest": "never",
        "relationship_type": "data_protection",
        "validate_source_path": False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        "use_rest": "never",
        "relationship_type": "load_sharing",
        "validate_source_path": False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_update():
    ''' update snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['error']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored']),   # update reads mirror_state
        ('ZAPI', 'snapmirror-update', ZRR['success']),                  # update
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check health
        # 2nd run
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['error']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_load_sharing']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_load_sharing']),   # update reads mirror_state
        ('ZAPI', 'snapmirror-update-ls-set', ZRR['success']),           # update
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check health
    ])
    module_args = {
        "use_rest": "never",
        "relationship_type": "data_protection",
        "validate_source_path": False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        "use_rest": "never",
        "relationship_type": "load_sharing",
        "validate_source_path": False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror.NetAppONTAPSnapmirror.set_element_connection')
def test_elementsw_no_source_path(connection):
    ''' elementsw_volume_exists '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),
    ])
    mock_elem, mock_helper = Mock(), Mock()
    connection.return_value = mock_helper, mock_elem
    mock_elem.get_cluster_info.return_value.cluster_info.svip = '10.11.12.13'
    module_args = {
        "use_rest": "never",
        "source_hostname": "source_host",
        "source_username": "source_user",
        "connection_type": "ontap_elementsw",
        "destination_path": "10.11.12.13:/lun/1234"
    }
    error = 'Error: creating an ONTAP to ElementSW snapmirror relationship requires an established SnapMirror relation from ElementSW to ONTAP cluster'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_elementsw_volume_exists():
    ''' elementsw_volume_exists '''
    mock_helper = Mock()
    mock_helper.volume_id_exists.side_effect = [1000, None]
    module_args = {
        "use_rest": "never",
        "source_hostname": "source_host",
        "source_username": "source_user",
        "source_path": "10.10.10.10:/lun/1000",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.check_if_elementsw_volume_exists('10.10.10.10:/lun/1000', mock_helper) is None
    expect_and_capture_ansible_exception(my_obj.check_if_elementsw_volume_exists, 'fail', '10.10.10.11:/lun/1000', mock_helper)
    mock_helper.volume_id_exists.side_effect = ApiServerError('function_name', {})
    error = 'Error fetching Volume details'
    assert error in expect_and_capture_ansible_exception(my_obj.check_if_elementsw_volume_exists, 'fail', '1234', mock_helper)['msg']


def test_elementsw_svip_exists():
    ''' svip_exists '''
    mock_elem = Mock()
    mock_elem.get_cluster_info.return_value.cluster_info.svip = '10.10.10.10'
    module_args = {
        "use_rest": "never",
        "source_hostname": "source_host",
        "source_username": "source_user",
        # "source_password": "source_password",
        "source_path": "10.10.10.10:/lun/1000",
        # "source_volume": "source_volume",
        # "source_vserver": "source_vserver",
        # "destination_volume": "destination_volume",
        # "destination_vserver": "destination_vserver",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.validate_elementsw_svip('10.10.10.10:/lun/1000', mock_elem) is None


def test_elementsw_svip_exists_negative():
    ''' svip_exists negative testing'''
    mock_elem = Mock()
    mock_elem.get_cluster_info.return_value.cluster_info.svip = '10.10.10.10'
    module_args = {
        "use_rest": "never",
        "source_hostname": "source_host",
        "source_username": "source_user",
        "source_path": "10.10.10.10:/lun/1000",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    expect_and_capture_ansible_exception(my_obj.validate_elementsw_svip, 'fail', '10.10.10.11:/lun/1000', mock_elem)
    mock_elem.get_cluster_info.side_effect = ApiServerError('function_name', {})
    error = 'Error fetching SVIP'
    assert error in expect_and_capture_ansible_exception(my_obj.validate_elementsw_svip, 'fail', 'svip', mock_elem)['msg']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror.NetAppONTAPSnapmirror.set_element_connection')
def test_check_elementsw_params_source(connection):
    ''' check elementsw parameters for source '''
    mock_elem, mock_helper = Mock(), Mock()
    connection.return_value = mock_helper, mock_elem
    mock_elem.get_cluster_info.return_value.cluster_info.svip = '10.10.10.10'
    module_args = {
        "use_rest": "never",
        "source_hostname": "source_host",
        "source_username": "source_user",
        "source_path": "10.10.10.10:/lun/1000",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.check_elementsw_parameters('source') is None


def test_check_elementsw_params_negative():
    ''' check elementsw parameters for source negative testing '''
    args = dict(DEFAULT_ARGS)
    del args['source_path']
    module_args = {
        "use_rest": "never",
    }
    msg = 'Error: Missing required parameter source_path'
    my_obj = create_module(my_module, args, module_args)
    assert msg in expect_and_capture_ansible_exception(my_obj.check_elementsw_parameters, 'fail', 'source')['msg']


def test_check_elementsw_params_invalid():
    ''' check elementsw parameters for source invalid testing '''
    module_args = {
        "use_rest": "never",
        "source_hostname": "source_host",
        "source_volume": "source_volume",
        "source_vserver": "source_vserver",
        "destination_volume": "destination_volume",
        "destination_vserver": "destination_vserver",
    }
    msg = 'Error: invalid source_path'
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert msg in expect_and_capture_ansible_exception(my_obj.check_elementsw_parameters, 'fail', 'source')['msg']


def test_elementsw_source_path_format():
    ''' test element_source_path_format_matches '''
    register_responses([
        ('ZAPI', 'volume-get-iter', ZRR['volume_info']),
    ])
    module_args = {
        "use_rest": "never",
        "source_hostname": "source_host",
        "source_volume": "source_volume",
        "source_vserver": "source_vserver",
        "destination_volume": "destination_volume",
        "destination_vserver": "destination_vserver",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.check_if_remote_volume_exists()
    assert my_obj.element_source_path_format_matches('1.1.1.1:dummy') is None
    assert my_obj.element_source_path_format_matches('10.10.10.10:/lun/10') is not None


def test_remote_volume_exists():
    ''' test check_if_remote_volume_exists '''
    register_responses([
        ('ZAPI', 'volume-get-iter', ZRR['volume_info']),
    ])
    module_args = {
        "use_rest": "never",
        "source_hostname": "source_host",
        "source_volume": "source_volume",
        "source_vserver": "source_vserver",
        "destination_volume": "destination_volume",
        "destination_vserver": "destination_vserver",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.check_if_remote_volume_exists()


@patch('time.sleep')
def test_if_all_methods_catch_exception(dont_sleep):
    module_args = {
        "use_rest": "never",
        "source_hostname": "source_host",
        "source_volume": "source_volume",
        "source_vserver": "source_vserver",
        "destination_volume": "destination_volume",
        "destination_vserver": "destination_vserver",
    }
    ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    my_obj.source_server = my_obj.server     # for get_destination
    tests = [
        (my_obj.check_if_remote_volume_exists, [('volume-get-iter', 'error')], 'Error fetching source volume details source_volume:'),
        (my_obj.get_destination, [('snapmirror-get-destination-iter', 'error')], 'Error fetching snapmirror destinations info:'),
        (my_obj.get_svm_peer, [('vserver-peer-get-iter', 'error')], 'Error fetching vserver peer info:'),
        (my_obj.snapmirror_abort, [('snapmirror-abort', 'error')], 'Error aborting SnapMirror relationship:'),
        (my_obj.snapmirror_break, [('snapmirror-quiesce', 'success'), ('snapmirror-get-iter', 'sm_info_snapmirrored_quiesced'), ('snapmirror-break', 'error')],
         'Error breaking SnapMirror relationship:'),
        (my_obj.snapmirror_create, [('volume-get-iter', 'success')], 'Source volume does not exist. Please specify a volume that exists'),
        (my_obj.snapmirror_create, [('volume-get-iter', 'volume_info'), ('snapmirror-create', 'error')], 'Error creating SnapMirror'),
        (my_obj.snapmirror_delete, [('snapmirror-destroy', 'error')], 'Error deleting SnapMirror:'),
        (my_obj.snapmirror_get, [('snapmirror-get-iter', 'error')], 'Error fetching snapmirror info:'),
        (my_obj.snapmirror_initialize, [('snapmirror-get-iter', 'sm_info'), ('snapmirror-initialize', 'error')], 'Error initializing SnapMirror:'),
        (my_obj.snapmirror_modify, [('snapmirror-modify', 'error')], 'Error modifying SnapMirror schedule or policy:'),
        (my_obj.snapmirror_quiesce, [('snapmirror-quiesce', 'error')], 'Error quiescing SnapMirror:'),
        (my_obj.snapmirror_release, [('snapmirror-release', 'error')], 'Error releasing SnapMirror relationship:'),
        (my_obj.snapmirror_resume, [('snapmirror-resume', 'error')], 'Error resuming SnapMirror relationship:'),
        (my_obj.snapmirror_restore, [('snapmirror-restore', 'error')], 'Error restoring SnapMirror relationship:'),
        (my_obj.snapmirror_resync, [('snapmirror-resync', 'error')], 'Error resyncing SnapMirror relationship:'),
        (my_obj.snapmirror_update, [('snapmirror-update', 'error')], 'Error updating SnapMirror:'),
    ]
    for (function, zapis, error) in tests:
        calls = [('ZAPI', zapi[0], ZRR[zapi[1]]) for zapi in zapis]
        register_responses(calls)
        if function in (my_obj.get_svm_peer,):
            assert error in expect_and_capture_ansible_exception(function, 'fail', 's_svm', 'd_svm')['msg']
        elif function in (my_obj.snapmirror_update, my_obj.snapmirror_modify):
            assert error in expect_and_capture_ansible_exception(function, 'fail', {})['msg']
        else:
            assert error in expect_and_capture_ansible_exception(function, 'fail')['msg']


@patch('time.sleep')
def test_successful_rest_create(dont_sleep):
    ''' creating snapmirror and testing idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
        ('POST', 'snapmirror/relationships', SRR['success']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_uninitialized']),
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),    # check initialized
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),    # check health
    ])
    module_args = {
        "use_rest": "always",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_negative_rest_create():
    ''' creating snapmirror with unsupported REST options '''
    module_args = {
        "use_rest": "always",
        "identity_preserve": True,
        "schedule": "abc",
        "relationship_type": "data_protection",
    }
    msg = "REST API currently does not support 'identity_preserve, schedule, relationship_type: data_protection'"
    assert create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_negative_rest_get_error():
    ''' creating snapmirror with API error '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['generic_error']),
    ])
    module_args = {
        "use_rest": "always",
    }
    msg = "Error getting SnapMirror svmdst3:voldst1: calling: snapmirror/relationships: got Expected error."
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_negative_rest_create_error():
    ''' creating snapmirror with API error '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
        ('POST', 'snapmirror/relationships', SRR['generic_error']),
    ])
    module_args = {
        "use_rest": "always",
    }
    msg = "Error creating SnapMirror: calling: snapmirror/relationships: got Expected error."
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


@patch('time.sleep')
def test_rest_snapmirror_initialize(dont_sleep):
    ''' snapmirror initialize testing '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_uninitialized_xfering']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_uninitialized_xfering']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_uninitialized']),
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),             # Inside SM init patch response
        ('GET', 'snapmirror/relationships', SRR['sm_get_data_transferring']),                                   # get to check status after initialize
        ('GET', 'snapmirror/relationships', SRR['sm_get_data_transferring']),                                   # get to check status after initialize
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),                                            # get to check status after initialize
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),                                            # check for update
        ('POST', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06/transfers', SRR['success']),    # update
        ('GET', 'snapmirror/relationships', SRR['sm_get_uninitialized']),   # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_snapmirror_update():
    ''' snapmirror initialize testing '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # first sm_get
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # apply update calls again sm_get
        ('POST', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06/transfers', SRR['success']),  # sm update
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),   # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_rest_sm_break_success_no_data_transfer(dont_sleep):
    ''' testing snapmirror break when no_data are transferring '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # apply first sm_get with no data transfer
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # SM quiesce response to pause
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # sm quiesce api fn calls again sm_get
        # sm quiesce validate the state which calls sm_get
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),
        # sm quiesce validate the state which calls sm_get after wait
        ('GET', 'snapmirror/relationships', SRR['sm_get_paused']),
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm break response
        ('GET', 'snapmirror/relationships', SRR['sm_get_paused']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
        "relationship_state": "broken",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_sm_break_success_no_data_transfer_idempotency():
    ''' testing snapmirror break when no_data are transferring idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_broken']),  # apply first sm_get with no data transfer
        ('GET', 'snapmirror/relationships', SRR['sm_get_broken']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
        "relationship_state": "broken",
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_sm_break_fails_if_uninit():
    ''' testing snapmirror break fails if sm state uninitialized '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # apply first sm_get with state uninitialized
        ('GET', 'snapmirror/relationships', SRR['sm_get_uninitialized']),
    ])
    module_args = {
        "use_rest": "always",
        "relationship_state": "broken",
    }
    msg = "SnapMirror relationship cannot be broken if mirror state is uninitialized"
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_sm_break_fails_if_load_sharing_or_vault():
    ''' testing snapmirror break fails for load_sharing or vault types '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_load_sharing']),
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_vault']),
    ])
    module_args = {
        "use_rest": "never",
        "relationship_state": "broken",
        "relationship_type": "load_sharing",
        "validate_source_path": False
    }
    msg = "SnapMirror break is not allowed in a load_sharing or vault relationship"
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg
    module_args['relationship_type'] = 'vault'
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


@patch('time.sleep')
def test_rest_snapmirror_quiesce_fail_when_state_not_paused(dont_sleep):
    ''' testing snapmirror break when no_data are transferring '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # apply first sm_get with no data transfer
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # SM quiesce response
        # SM quiesce validate the state which calls sm_get after wait
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),   # first fail
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),   # second fail
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),   # third fail
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),   # fourth fail
    ])
    module_args = {
        "use_rest": "always",
        "relationship_state": "broken",
        "validate_source_path": False
    }
    msg = "Taking a long time to quiesce SnapMirror relationship, try again later"
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_snapmirror_break_fails_if_data_is_transferring():
    ''' testing snapmirror break when no_data are transferring '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # apply first sm_get with data transfer
        ('GET', 'snapmirror/relationships', SRR['sm_get_data_transferring']),
    ])
    module_args = {
        "use_rest": "always",
        "relationship_state": "broken",
    }
    msg = "snapmirror data are transferring"
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


@patch('time.sleep')
def test_rest_resync_when_state_is_broken(dont_sleep):
    ''' resync when snapmirror state is broken and relationship_state active  '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_broken']),  # apply first sm_get with state broken_off
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm resync response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # check for idle
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_resume_when_state_quiesced():
    ''' resync when snapmirror state is broken and relationship_state active  '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_paused']),  # apply first sm_get with state quiesced
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),             # sm resync response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # sm update calls sm_get
        ('POST', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06/transfers', SRR['success']),   # sm update response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_rest_snapmirror_delete(dont_sleep):
    ''' snapmirror delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # apply first sm_get with no data transfer
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm quiesce response
        # sm quiesce validate the state which calls sm_get
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),
        # sm quiesce validate the state which calls sm_get after wait with 0 iter
        ('GET', 'snapmirror/relationships', SRR['sm_get_paused']),
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm break response
        ('DELETE', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm delete response
        ('GET', 'snapmirror/relationships', SRR['zero_records']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
        "state": "absent",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_rest_snapmirror_delete_with_error_on_break(dont_sleep):
    ''' snapmirror delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # apply first sm_get with no data transfer
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),         # sm quiesce response
        # sm quiesce validate the state which calls sm_get
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),
        # sm quiesce validate the state which calls sm_get after wait with 0 iter
        ('GET', 'snapmirror/relationships', SRR['sm_get_paused']),
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['generic_error']),   # sm break response
        ('DELETE', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),        # sm delete response
        ('GET', 'snapmirror/relationships', SRR['zero_records']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
        "state": "absent",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised("Ignored error(s): Error patching SnapMirror: {'state': 'broken_off'}: "
                              "calling: snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06: got Expected error.")


@patch('time.sleep')
def test_rest_snapmirror_delete_with_error_on_break_and_delete(dont_sleep):
    ''' snapmirror delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # apply first sm_get with no data transfer
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),         # sm quiesce response
        # sm quiesce validate the state which calls sm_get
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),
        # sm quiesce validate the state which calls sm_get after wait with 0 iter
        ('GET', 'snapmirror/relationships', SRR['sm_get_paused']),
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['generic_error']),   # sm break response
        ('DELETE', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['generic_error']),  # sm delete response
    ])
    module_args = {
        "use_rest": "always",
        "state": "absent",
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    print_warnings()
    assert "Previous error(s): Error patching SnapMirror: {'state': 'broken_off'}" in error
    assert "Error deleting SnapMirror: calling: snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06: got Expected error" in error


@patch('time.sleep')
def test_rest_snapmirror_delete_calls_abort(dont_sleep):
    ''' snapmirror delete calls abort when transfer state is in transferring'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # apply first sm_get with data transfer
        ('GET', 'snapmirror/relationships', SRR['sm_get_data_transferring']),
        # abort
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06/transfers/xfer_uuid', SRR['empty_good']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_abort']),       # wait_for_status calls again sm_get
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm quiesce response
        # sm quiesce validate the state which calls sm_get
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),
        # sm quiesce validate the state which calls sm_get after wait with 0 iter
        ('GET', 'snapmirror/relationships', SRR['sm_get_paused']),
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm break response
        ('DELETE', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm delete response
        ('GET', 'snapmirror/relationships', SRR['zero_records']),       # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
        "state": "absent",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_snapmirror_modify():
    ''' snapmirror modify'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # apply first sm_get
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),             # sm modify response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # sm update calls sm_get to check mirror state
        ('POST', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06/transfers', SRR['success']),    # sm update response
        ('GET', 'snapmirror/relationships', SRR['zero_records']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
        "policy": "Asynchronous",
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_snapmirror_restore():
    ''' snapmirror restore '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # apply first sm_get
        ('POST', 'snapmirror/relationships', SRR['success']),  # first post response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # After first post call to get relationship uuid
        ('POST', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06/transfers', SRR['success']),  # second post response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
        "relationship_type": "restore",
        "source_snapshot": "source_snapshot",
        "clean_up_failure": False,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_snapmirror_create_and_initialize_not_found():
    ''' snapmirror restore '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),   # apply first sm_get
        ('GET', 'snapmirror/policies', SRR['zero_records']),        # policy not found
    ])
    module_args = {
        "use_rest": "always",
        "create_destination": {"enabled": True},
        "policy": "sm_policy"
    }
    error = 'Error: cannot find policy sm_policy for vserver svmdst3'
    assert error == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_error_snapmirror_create_and_initialize_bad_type():
    ''' snapmirror restore '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),   # apply first sm_get
        ('GET', 'snapmirror/policies', SRR['sm_policies']),         # policy
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),   # apply first sm_get
        ('GET', 'snapmirror/policies', SRR['sm_policies']),         # policy
    ])
    module_args = {
        "use_rest": "always",
        "create_destination": {"enabled": True},
        "policy": "sm_policy",
        "destination_vserver": "bad_type",
        "source_vserver": "any"
    }
    error = 'Error: unexpected type: svm_invalid for policy sm_policy for vserver bad_type'
    assert error == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['destination_vserver'] = 'cluster_scope_only'
    error = 'Error: unexpected type: system_invalid for policy sm_policy for vserver cluster_scope_only'
    assert error == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_errors():
    ''' generic REST errors '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # set_initialization_state
        ('GET', 'snapmirror/policies', SRR['generic_error']),
        # snapmirror_restore_rest
        ('POST', 'snapmirror/relationships', SRR['generic_error']),
        # snapmirror_restore_rest
        ('POST', 'snapmirror/relationships', SRR['success']),
        ('POST', 'snapmirror/relationships/1234/transfers', SRR['generic_error']),
        # snapmirror_mod_init_resync_break_quiesce_resume_rest
        ('PATCH', 'snapmirror/relationships/1234', SRR['generic_error']),
        # snapmirror_update_rest
        ('POST', 'snapmirror/relationships/1234/transfers', SRR['generic_error']),
        # snapmirror_abort_rest
        ('PATCH', 'snapmirror/relationships/1234/transfers/5678', SRR['generic_error']),
    ])
    module_args = {
        "use_rest": "always",
        "policy": "policy"
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = rest_error_message("Error fetching SnapMirror policy", 'snapmirror/policies')
    assert error in expect_and_capture_ansible_exception(my_obj.set_initialization_state, 'fail')['msg']
    my_obj.parameters['uuid'] = '1234'
    my_obj.parameters['transfer_uuid'] = '5678'
    error = rest_error_message("Error restoring SnapMirror", 'snapmirror/relationships')
    assert error in expect_and_capture_ansible_exception(my_obj.snapmirror_restore_rest, 'fail')['msg']
    error = rest_error_message("Error restoring SnapMirror Transfer", 'snapmirror/relationships/1234/transfers')
    assert error in expect_and_capture_ansible_exception(my_obj.snapmirror_restore_rest, 'fail')['msg']
    my_obj.na_helper.changed = True
    assert my_obj.snapmirror_mod_init_resync_break_quiesce_resume_rest() is None
    assert not my_obj.na_helper.changed
    error = rest_error_message("Error patching SnapMirror: {'state': 'broken_off'}", 'snapmirror/relationships/1234')
    assert error in expect_and_capture_ansible_exception(my_obj.snapmirror_mod_init_resync_break_quiesce_resume_rest, 'fail', 'broken_off')['msg']
    error = rest_error_message('Error updating SnapMirror relationship', 'snapmirror/relationships/1234/transfers')
    assert error in expect_and_capture_ansible_exception(my_obj.snapmirror_update_rest, 'fail')['msg']
    error = rest_error_message('Error aborting SnapMirror', 'snapmirror/relationships/1234/transfers/5678')
    assert error in expect_and_capture_ansible_exception(my_obj.snapmirror_abort_rest, 'fail')['msg']


def test_rest_error_no_uuid():
    ''' snapmirror restore '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        # snapmirror_restore_rest
        ('POST', 'snapmirror/relationships', SRR['success']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
        # snapmirror_mod_init_resync_break_quiesce_resume_rest
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
        # snapmirror_update_rest
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
        # others, no call
    ])
    module_args = {
        "use_rest": "always",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = 'Error restoring SnapMirror: unable to get UUID for the SnapMirror relationship.'
    assert error in expect_and_capture_ansible_exception(my_obj.snapmirror_restore_rest, 'fail')['msg']
    error = 'Error in updating SnapMirror relationship: unable to get UUID for the SnapMirror relationship.'
    assert error in expect_and_capture_ansible_exception(my_obj.snapmirror_mod_init_resync_break_quiesce_resume_rest, 'fail')['msg']
    error = 'Error in updating SnapMirror relationship: unable to get UUID for the SnapMirror relationship.'
    assert error in expect_and_capture_ansible_exception(my_obj.snapmirror_update_rest, 'fail')['msg']
    error = 'Error in aborting SnapMirror: unable to get either uuid: None or transfer_uuid: None.'
    assert error in expect_and_capture_ansible_exception(my_obj.snapmirror_abort_rest, 'fail')['msg']
    error = 'Error in deleting SnapMirror: None, unable to get UUID for the SnapMirror relationship.'
    assert error in expect_and_capture_ansible_exception(my_obj.snapmirror_delete_rest, 'fail')['msg']


@patch('time.sleep')
def test_rest_snapmirror_create_and_initialize(dont_sleep):
    ''' snapmirror restore '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),       # apply first sm_get
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'storage/volumes', SRR['one_record']),
        ('GET', 'snapmirror/policies', SRR['sm_policies']),             # policy
        ('POST', 'snapmirror/relationships', SRR['success']),           # first post response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),    # check status
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),    # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
        "create_destination": {"enabled": True},
        "policy": "sm_policy",
        # force a call to check_if_remote_volume_exists
        "peer_options": {"hostname": "10.10.10.10"},
        "source_volume": "source_volume",
        "source_vserver": "source_vserver",
        "destination_volume": "destination_volume",
        "destination_vserver": "svmdst3"

    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_set_new_style():
    # validate the old options are set properly using new endpoints
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('source_path')
    args.pop('destination_path')
    module_args = {
        "use_rest": "always",
        "source_endpoint": {
            "cluster": "source_cluster",
            "consistency_group_volumes": "source_consistency_group_volumes",
            "path": "source_path",
            "svm": "source_svm",
        },
        "destination_endpoint": {
            "cluster": "destination_cluster",
            "consistency_group_volumes": "destination_consistency_group_volumes",
            "path": "destination_path",
            "svm": "destination_svm",
        },
    }
    my_obj = create_module(my_module, args, module_args)
    assert my_obj.set_new_style() is None
    assert my_obj.new_style
    assert my_obj.parameters['destination_vserver'] == 'destination_svm'
    assert my_obj.set_initialization_state() == 'in_sync'


def test_negative_set_new_style():
    # validate the old options are set properly using new endpoints
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('source_path')
    args.pop('destination_path')
    module_args = {
        "use_rest": "always",
        "source_endpoint": {
            "cluster": "source_cluster",
            "consistency_group_volumes": "source_consistency_group_volumes",
            "path": "source_path",
            "svm": "source_svm",
        },
        "destination_endpoint": {
            "cluster": "destination_cluster",
            "consistency_group_volumes": "destination_consistency_group_volumes",
            "path": "destination_path",
            "svm": "destination_svm",
        },
    }
    # errors on source_endpoint
    my_obj = create_module(my_module, args, module_args)
    error = expect_and_capture_ansible_exception(my_obj.set_new_style, 'fail')['msg']
    assert "Error: using any of ['cluster', 'ipspace'] requires ONTAP 9.7 or later and REST must be enabled" in error
    assert "ONTAP version: 9.6.0 - using REST" in error
    my_obj = create_module(my_module, args, module_args)
    error = expect_and_capture_ansible_exception(my_obj.set_new_style, 'fail')['msg']
    assert "Error: using consistency_group_volumes requires ONTAP 9.8 or later and REST must be enabled" in error
    assert "ONTAP version: 9.7.0 - using REST" in error
    # errors on destination_endpoint
    module_args['source_endpoint'].pop('cluster')
    my_obj = create_module(my_module, args, module_args)
    error = expect_and_capture_ansible_exception(my_obj.set_new_style, 'fail')['msg']
    assert "Error: using any of ['cluster', 'ipspace'] requires ONTAP 9.7 or later and REST must be enabled" in error
    assert "ONTAP version: 9.6.0 - using REST" in error
    module_args['source_endpoint'].pop('consistency_group_volumes')
    my_obj = create_module(my_module, args, module_args)
    error = expect_and_capture_ansible_exception(my_obj.set_new_style, 'fail')['msg']
    assert "Error: using consistency_group_volumes requires ONTAP 9.8 or later and REST must be enabled" in error
    assert "ONTAP version: 9.7.0 - using REST" in error
    module_args.pop('source_endpoint')
    module_args.pop('destination_endpoint')
    my_obj = create_module(my_module, args, module_args)
    error = expect_and_capture_ansible_exception(my_obj.set_new_style, 'fail')['msg']
    assert error == 'Missing parameters: Source endpoint or Destination endpoint'


def test_check_parameters_new_style():
    # validate the old options are set properly using new endpoints
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('source_path')
    args.pop('destination_path')
    module_args = {
        "use_rest": "always",
        "source_endpoint": {
            "cluster": "source_cluster",
            "consistency_group_volumes": "source_consistency_group_volumes",
            "path": "source_path",
            "svm": "source_svm",
        },
        "destination_endpoint": {
            "cluster": "destination_cluster",
            "consistency_group_volumes": "destination_consistency_group_volumes",
            "path": "destination_path",
            "svm": "destination_svm",
        },
    }
    my_obj = create_module(my_module, args, module_args)
    assert my_obj.check_parameters() is None
    assert my_obj.new_style
    assert my_obj.parameters['destination_vserver'] == 'destination_svm'


def test_negative_check_parameters_new_style():
    # validate version checks
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('source_path')
    args.pop('destination_path')
    module_args = {
        "use_rest": "always",
        "source_endpoint": {
            "cluster": "source_cluster",
            "consistency_group_volumes": "source_consistency_group_volumes",
            "path": "source_path",
            "svm": "source_svm",
        },
        "destination_endpoint": {
            "cluster": "destination_cluster",
            "consistency_group_volumes": "destination_consistency_group_volumes",
            "path": "destination_path",
            "svm": "destination_svm",
        },
        "create_destination": {"enabled": True}
    }
    # errors on source_endpoint
    error = 'Minimum version of ONTAP for create_destination is (9, 7).'
    assert error in create_module(my_module, args, module_args, fail=True)['msg']
    my_obj = create_module(my_module, args, module_args)
    error = expect_and_capture_ansible_exception(my_obj.check_parameters, 'fail')['msg']
    assert "Error: using consistency_group_volumes requires ONTAP 9.8 or later and REST must be enabled" in error
    assert "ONTAP version: 9.7.0 - using REST" in error
    module_args['destination_endpoint'].pop('path')
    error = create_module(my_module, args, module_args, fail=True)['msg']
    assert "missing required arguments: path found in destination_endpoint" in error


def test_check_parameters_old_style():
    # validate the old options are set properly using new endpoints
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    # using paths
    module_args = {
        "use_rest": "always",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.check_parameters() is None
    assert not my_obj.new_style
    # using volume and vserver, paths are constructed
    args = dict(DEFAULT_ARGS)
    args.pop('source_path')
    args.pop('destination_path')
    module_args = {
        "use_rest": "always",
        "source_volume": "source_vol",
        "source_vserver": "source_svm",
        "destination_volume": "dest_vol",
        "destination_vserver": "dest_svm",
    }
    my_obj = create_module(my_module, args, module_args)
    assert my_obj.check_parameters() is None
    assert not my_obj.new_style
    assert my_obj.parameters['source_path'] == "source_svm:source_vol"
    assert my_obj.parameters['destination_path'] == "dest_svm:dest_vol"
    # vserver DR
    module_args = {
        "use_rest": "always",
        "source_vserver": "source_svm",
        "destination_vserver": "dest_svm",
    }
    my_obj = create_module(my_module, args, module_args)
    assert my_obj.check_parameters() is None
    assert not my_obj.new_style
    assert my_obj.parameters['source_path'] == "source_svm:"
    assert my_obj.parameters['destination_path'] == "dest_svm:"
    body, dummy = my_obj.get_create_body()
    assert body["source"] == {"path": "source_svm:"}
    module_args = {
        "use_rest": "always",
        "source_volume": "source_vol",
        "source_vserver": "source_svm",
        "destination_volume": "dest_vol",
        "destination_vserver": "dest_svm",
    }
    my_obj = create_module(my_module, args, module_args)
    my_obj.parameters.pop("source_vserver")
    error = 'Missing parameters: source vserver or destination vserver or both'
    assert error in expect_and_capture_ansible_exception(my_obj.check_parameters, 'fail')['msg']


def test_validate_source_path():
    # validate source path when vserver local name is different
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/peers', SRR['zero_records']),
        ('GET', 'svm/peers', SRR['svm_peer_info']),
        ('GET', 'svm/peers', SRR['svm_peer_info']),
        # error
        ('GET', 'svm/peers', SRR['generic_error']),
        # warnings
    ])
    # using paths
    module_args = {
        "use_rest": "always",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    current = None
    assert my_obj.validate_source_path(current) is None
    current = {}
    assert my_obj.validate_source_path(current) is None
    current = {'source_path': 'svmsrc3:volsrc1'}
    assert my_obj.validate_source_path(current) is None
    current = {'source_path': 'svmsrc3:volsrc1'}
    assert my_obj.validate_source_path(current) is None
    current = {'source_path': 'vserver:volume'}
    error = 'Error: another relationship is present for the same destination with source_path: "vserver:volume" '\
            '(vserver:volume on cluster cluster).  Desired: svmsrc3:volsrc1 on None'
    assert error in expect_and_capture_ansible_exception(my_obj.validate_source_path, 'fail', current)['msg']
    current = {'source_path': 'vserver:volume1'}
    my_obj.parameters['connection_type'] = 'other'
    error = 'Error: another relationship is present for the same destination with source_path: "vserver:volume1".'\
            '  Desired: svmsrc3:volsrc1 on None'
    assert error in expect_and_capture_ansible_exception(my_obj.validate_source_path, 'fail', current)['msg']
    my_obj.parameters['connection_type'] = 'ontap_ontap'
    current = {'source_path': 'vserver:volume'}
    error = rest_error_message('Error retrieving SVM peer', 'svm/peers')
    assert error in expect_and_capture_ansible_exception(my_obj.validate_source_path, 'fail', current)['msg']
    current = {'source_path': 'vserver/volume'}
    assert my_obj.validate_source_path(current) is None
    assert_warning_was_raised('Unexpected source path: vserver/volume, skipping validation.')
    my_obj.parameters['destination_endpoint'] = {'path': 'vserver/volume'}
    current = {'source_path': 'vserver:volume'}
    assert my_obj.validate_source_path(current) is None
    assert_warning_was_raised('Unexpected destination path: vserver/volume, skipping validation.')


@patch('time.sleep')
def test_wait_for_idle_status(dont_sleep):
    # validate wait time and time-out
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),
        # time-out
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
    ])
    # using paths
    module_args = {
        "use_rest": "always",
        "transferring_time_out": 0,
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.wait_for_idle_status() is None
    assert my_obj.wait_for_idle_status() is not None
    module_args = {
        "use_rest": "always",
        "transferring_time_out": 60,
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.wait_for_idle_status() is not None
    assert my_obj.wait_for_idle_status() is None
    assert_warning_was_raised('SnapMirror relationship is still transferring after 60 seconds.')


def test_dp_to_xdp():
    # with ZAPI, DP is transformed to XDP to match ONTAP behavior
    register_responses([
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored']),
    ])
    # using paths
    module_args = {
        "use_rest": "never",
        "relationship_type": 'data_protection',
        "validate_source_path": False
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_actions() is not None
    assert my_obj.parameters['relationship_type'] == 'extended_data_protection'


def test_cannot_change_rtype():
    # with ZAPI, can't change relationship_type
    register_responses([
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored']),
    ])
    # using paths
    module_args = {
        "use_rest": "never",
        "relationship_type": 'load_sharing',
        "validate_source_path": False
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = 'Error: cannot modify relationship_type from extended_data_protection to load_sharing.'
    assert error in expect_and_capture_ansible_exception(my_obj.get_actions, 'fail', )['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_NETAPP_LIB', False)
def test_module_fail_when_netapp_lib_missing():
    ''' required lib missing '''
    module_args = {
        'use_rest': 'never',
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_check_health():
    # validate source path when vserver local name is different
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_abort']),
    ])
    module_args = {
        "use_rest": "always",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.check_health() is None
    assert_no_warnings()
    assert my_obj.check_health() is None
    assert_warning_was_raised('SnapMirror relationship exists but is not healthy.  '
                              'Unhealthy reason: this is why the relationship is not healthy.  '
                              'Last transfer error: this is why the relationship is not healthy.')


def test_negative_check_if_remote_volume_exists_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/volumes', SRR['zero_records']),
        ('GET', 'storage/volumes', SRR['generic_error']),
    ])
    module_args = {
        "use_rest": "always",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = 'REST is not supported on Source'
    assert error in expect_and_capture_ansible_exception(my_obj.check_if_remote_volume_exists_rest, 'fail')['msg']
    my_obj.src_use_rest = True
    assert not my_obj.check_if_remote_volume_exists_rest()
    my_obj.parameters['peer_options'] = {}
    netapp_utils.setup_host_options_from_module_params(my_obj.parameters['peer_options'], my_obj.module, netapp_utils.na_ontap_host_argument_spec_peer().keys())
    my_obj.parameters['source_volume'] = 'volume'
    my_obj.parameters['source_vserver'] = 'vserver'
    assert my_obj.set_source_cluster_connection() is None
    assert not my_obj.check_if_remote_volume_exists_rest()
    error = rest_error_message('Error fetching source volume', 'storage/volumes')
    assert error in expect_and_capture_ansible_exception(my_obj.check_if_remote_volume_exists_rest, 'fail')['msg']


def test_snapmirror_release_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    module_args = {
        "use_rest": "always",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.snapmirror_release() is None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_negative_set_source_cluster_connection(mock_netapp_lib):
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    module_args = {
        "use_rest": "never",
        "source_volume": "source_volume",
        "source_vserver": "source_vserver",
        "destination_volume": "destination_volume",
        "destination_vserver": "destination_vserver",
        "relationship_type": "vault",
        "peer_options": {
            "use_rest": "always",
            "hostname": "source_host",
        }
    }
    mock_netapp_lib.side_effect = [True, False]
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = "REST API currently does not support 'relationship_type: vault'"
    assert error in expect_and_capture_ansible_exception(my_obj.set_source_cluster_connection, 'fail')['msg']
    my_obj.parameters['peer_options']['use_rest'] = 'auto'
    error = "Error: the python NetApp-Lib module is required.  Import error: None"
    assert error in expect_and_capture_ansible_exception(my_obj.set_source_cluster_connection, 'fail')['msg']
