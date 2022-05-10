''' unit tests ONTAP Ansible module: na_ontap_snapmirror '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    expect_and_capture_ansible_exception, create_module, create_and_apply, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror \
    import NetAppONTAPSnapmirror as my_module

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

# REST API canned responses when mocking send_request
SRR = rest_responses({
    'sm_get_uninitialized': (200, sm_rest_info('uninitialized', True), None),
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
    'sm_policies': (200, sm_policies, None)
})


def sm_info(mirror_state, status, quiesce_status):
    return {
        'num-records': 1,
        'status': quiesce_status,
        'attributes-list': {
            'snapmirror-info': {
                'mirror-state': mirror_state,
                'schedule': None,
                'source-location': 'ansible:ansible',
                'relationship-status': status,
                'policy': 'ansible_policy',
                'relationship-type': 'data_protection',
                'max-transfer-rate': 1000,
                'identity-preserve': 'true'
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


ZRR = zapi_responses({
    'sm_info': build_zapi_response(sm_info(None, 'idle', 'passed')),
    'sm_info_broken_off': build_zapi_response(sm_info('broken_off', 'idle', 'passed')),
    'sm_info_snapmirrored': build_zapi_response(sm_info('snapmirrored', 'idle', 'passed')),
    'sm_info_snapmirrored_quiesced': build_zapi_response(sm_info('snapmirrored', 'quiesced', 'passed')),
    'sm_info_uninitialized': build_zapi_response(sm_info('uninitialized', 'idle', 'passed')),
    'volume_info': build_zapi_response(volume_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    msg = "missing required arguments: hostname"
    assert create_module(my_module, {}, fail=True)['msg'] == msg


def test_successful_create():
    ''' creating snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),     # ONTAP to ONTAP
        ('ZAPI', 'snapmirror-create', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-initialize', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # check health
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # ONTAP to ONTAP
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # ONTAP to ONTAP, check for update
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # check health
    ])
    module_args = {
        "use_rest": "never",
        "source_hostname": "10.10.10.10",
        "schedule": "abc",
        "identity_preserve": True,
        "relationship_type": "data_protection",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args.pop('schedule')
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_negative_break(dont_sleep):
    ''' breaking snapmirror to test quiesce time-delay failure '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # 5 retries
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
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


@patch('time.sleep')
def test_successful_break(dont_sleep):
    ''' breaking snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
        ('ZAPI', 'snapmirror-break', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # check health
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_broken_off']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # check health
    ])
    module_args = {
        "use_rest": "never",
        "source_hostname": "10.10.10.10",
        "relationship_state": "broken",
        "relationship_type": "data_protection",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_create_without_initialize():
    ''' creating snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),     # ONTAP to ONTAP
        ('ZAPI', 'snapmirror-create', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # check health
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # ONTAP to ONTAP
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # ONTAP to ONTAP, check for update
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # check health
    ])
    module_args = {
        "use_rest": "never",
        "source_hostname": "10.10.10.10",
        "schedule": "abc",
        "relationship_type": "data_protection",
        "initialize": False,
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args.pop('schedule')
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror.NetAppONTAPSnapmirror.set_element_connection')
def test_successful_element_ontap_create(connection):
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),     # element to ONTAP
        ('ZAPI', 'snapmirror-create', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-initialize', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # check health
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # element to ONTAP
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # element to ONTAP, check for update
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # check health
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
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args.pop('schedule')
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror.NetAppONTAPSnapmirror.set_element_connection')
def test_successful_ontap_element_create(connection):
    ''' check elementsw parameters for source '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # an existing relationship is required element to ONTAP
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),     # ONTAP to element
        ('ZAPI', 'snapmirror-create', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-initialize', ZRR['sm_info']),
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # an existing relationship is required element to ONTAP
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # ONTAP to element
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),        # ONTAP to element, check for update
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
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args.pop('schedule')
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_successful_delete(dont_sleep):
    ''' deleting snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
        ('ZAPI', 'snapmirror-break', ZRR['success']),
        ('ZAPI', 'snapmirror-get-destination-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-release', ZRR['success']),
        ('ZAPI', 'snapmirror-destroy', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
        # idempotency
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
        "source_hostname": "10.10.10.10",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_successful_delete_without_source_hostname_check(dont_sleep):
    ''' source cluster hostname is optional when source is unknown'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-quiesce', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored_quiesced']),
        ('ZAPI', 'snapmirror-break', ZRR['success']),
        ('ZAPI', 'snapmirror-destroy', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
    assert create_and_apply(my_module, args, module_args, fail=True)['msg'] == msg


def test_successful_delete_check_get_destination():
    register_responses([
        ('ZAPI', 'snapmirror-get-destination-iter', ZRR['sm_info']),
    ])
    module_args = {
        "use_rest": "never",
        "state": "absent",
        "source_hostname": "source_host",
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.set_source_cluster_connection() is None
    assert my_obj.get_destination()


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
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        "use_rest": "never",
        "relationship_type": "data_protection",
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_snapmirror_restore():
    ''' restore snapmirror '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        # ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-restore', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
        # idempotency test - TODO
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-restore', ZRR['success']),
        # ('ZAPI', 'snapmirror-get-iter', ZRR['no_records']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
    ])
    module_args = {
        "use_rest": "never",
        "relationship_type": "restore",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    # TODO: should be idempotent!   But we don't read the current state!
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        "use_rest": "never",
        "state": "absent",
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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

    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        "use_rest": "never",
        "relationship_type": "data_protection",
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_initialize():
    ''' initialize snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_uninitialized']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # update reads mirror_state
        ('ZAPI', 'snapmirror-initialize', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # update reads mirror_state
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),    # check health
    ])
    module_args = {
        "use_rest": "never",
        "relationship_type": "data_protection",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_update():
    ''' update snapmirror and testing idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['volume_info']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info_snapmirrored']),   # update reads mirror_state
        ('ZAPI', 'snapmirror-update', ZRR['success']),                  # check health
        ('ZAPI', 'snapmirror-get-iter', ZRR['sm_info']),                # check health
    ])
    module_args = {
        "use_rest": "never",
        "relationship_type": "data_protection",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_elementsw_volume_exists():
    ''' elementsw_volume_exists '''
    mock_helper = Mock()
    mock_helper.volume_id_exists.side_effect = [1000, None]
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
    assert my_obj.check_if_elementsw_volume_exists('10.10.10.10:/lun/1000', mock_helper) is None
    expect_and_capture_ansible_exception(my_obj.check_if_elementsw_volume_exists, 'fail', '10.10.10.11:/lun/1000', mock_helper)


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
    tests = [
        (my_obj.snapmirror_abort, [('snapmirror-abort', 'error')], 'Error aborting SnapMirror relationship :'),
        (my_obj.snapmirror_break, [('snapmirror-quiesce', 'success'), ('snapmirror-get-iter', 'sm_info_snapmirrored_quiesced'), ('snapmirror-break', 'error')],
         'Error breaking SnapMirror relationship :'),
        (my_obj.snapmirror_get, [('snapmirror-get-iter', 'error')], 'Error fetching snapmirror info:'),
        (my_obj.snapmirror_initialize, [('snapmirror-get-iter', 'sm_info'), ('snapmirror-initialize', 'error')], 'Error initializing SnapMirror :'),
        (my_obj.snapmirror_update, [('snapmirror-update', 'error')], 'Error updating SnapMirror :'),
        (my_obj.check_if_remote_volume_exists, [('volume-get-iter', 'error')], 'Error fetching source volume details source_volume :'),
        (my_obj.snapmirror_create, [('volume-get-iter', 'success')], 'Source volume does not exist. Please specify a volume that exists'),
        (my_obj.snapmirror_create, [('volume-get-iter', 'volume_info'), ('snapmirror-create', 'error')], 'Error creating SnapMirror '),
        (my_obj.snapmirror_delete, [('snapmirror-destroy', 'error')], 'Error deleting SnapMirror :'),
        (my_obj.snapmirror_modify, [('snapmirror-modify', 'error')], 'Error modifying SnapMirror schedule or policy :'),

    ]
    for (function, zapis, error) in tests:
        calls = [('ZAPI', zapi[0], ZRR[zapi[1]]) for zapi in zapis]
        register_responses(calls)
        if function in (my_obj.snapmirror_update, my_obj.snapmirror_modify):
            assert error in expect_and_capture_ansible_exception(function, 'fail', {})['msg']
        else:
            assert error in expect_and_capture_ansible_exception(function, 'fail')['msg']


def test_successful_rest_create():
    ''' creating snapmirror and testing idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),
        ('POST', 'snapmirror/relationships', SRR['success']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_uninitialized']),
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),
    ])
    module_args = {
        "use_rest": "always",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


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
    msg = "Error Creating Snapmirror: calling: snapmirror/relationships: got Expected error."
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_snapmirror_initialize():
    ''' snapmirror initialize testing '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_uninitialized']),
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # Inside SM init patch response
        ('GET', 'snapmirror/relationships', SRR['sm_get_uninitialized']),   # get to check if update is needed
        ('GET', 'snapmirror/relationships', SRR['sm_get_uninitialized']),   # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_snapmirror_update():
    ''' snapmirror initialize testing '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # first sm_get
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # apply update calls again sm_get
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm update
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),   # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


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
    }
    msg = "Taking a long time to quiesce SnapMirror relationship, try again later"
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


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
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_resync_when_state_is_broken():
    ''' resync when snapmirror state is broken and relationship_state active  '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_broken']),  # apply first sm_get with state broken_off
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm resync response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_resume_when_state_quiesced():
    ''' resync when snapmirror state is broken and relationship_state active  '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_paused']),  # apply first sm_get with state quiesced
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm resync response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # sm update calls sm_get
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm update response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_snapmirror_modify():
    ''' snapmirror modify'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # apply first sm_get
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm modify response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),  # sm update calls sm_get to check mirror state
        ('PATCH', 'snapmirror/relationships/b5ee4571-5429-11ec-9779-005056b39a06', SRR['success']),  # sm update response
        ('GET', 'snapmirror/relationships', SRR['zero_records']),  # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
        "policy": "Asynchronous",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
        "relationship_type": "restore"
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
    assert error == create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


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
    assert error == create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['destination_vserver'] = 'cluster_scope_only'
    error = 'Error: unexpected type: system_invalid for policy sm_policy for vserver cluster_scope_only'
    assert error == create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_snapmirror_create_and_initialize():
    ''' snapmirror restore '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'snapmirror/relationships', SRR['zero_records']),       # apply first sm_get
        ('GET', 'snapmirror/policies', SRR['sm_policies']),             # policy
        ('POST', 'snapmirror/relationships', SRR['success']),           # first post response
        ('GET', 'snapmirror/relationships', SRR['sm_get_mirrored']),    # check_health calls sm_get
    ])
    module_args = {
        "use_rest": "always",
        "create_destination": {"enabled": True},
        "policy": "sm_policy"
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
