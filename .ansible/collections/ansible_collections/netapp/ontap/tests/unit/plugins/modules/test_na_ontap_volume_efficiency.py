''' unit tests ONTAP Ansible module: na_ontap_volume_efficiency '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_efficiency \
    import NetAppOntapVolumeEfficiency as volume_efficiency_module, main  # module under test


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


DEFAULT_ARGS = {
    'hostname': '10.10.10.10',
    'username': 'username',
    'password': 'password',
    'vserver': 'vs1',
    'path': '/vol/volTest',
    'policy': 'auto',
    'use_rest': 'never',
    'enable_compression': True,
    'enable_inline_compression': True,
    'enable_cross_volume_inline_dedupe': True,
    'enable_inline_dedupe': True,
    'enable_data_compaction': True,
    'enable_cross_volume_background_dedupe': True
}

DEFAULT_ARGS_REST = {
    'hostname': '10.10.10.10',
    'username': 'username',
    'password': 'password',
    'vserver': 'vs1',
    'path': '/vol/volTest',
    'policy': 'auto',
    'use_rest': 'always'
}


def return_vol_info(state='enabled', status='idle', policy='auto'):
    return {
        'num-records': 1,
        'attributes-list': {
            'sis-status-info': {
                'path': '/vol/volTest',
                'state': state,
                'schedule': None,
                'status': status,
                'policy': policy,
                'is-inline-compression-enabled': 'true',
                'is-compression-enabled': 'true',
                'is-inline-dedupe-enabled': 'true',
                'is-data-compaction-enabled': 'true',
                'is-cross-volume-inline-dedupe-enabled': 'true',
                'is-cross-volume-background-dedupe-enabled': 'true'
            }
        }
    }


ZRR = zapi_responses({
    'vol_eff_info': build_zapi_response(return_vol_info()),
    'vol_eff_info_disabled': build_zapi_response(return_vol_info(state='disabled')),
    'vol_eff_info_running': build_zapi_response(return_vol_info(status='running')),
    'vol_eff_info_policy': build_zapi_response(return_vol_info(policy='default'))
})


def return_vol_info_rest(state='enabled', status='idle', policy='auto', compaction='inline'):
    return {
        "records": [{
            "uuid": "25311eff",
            "name": "test_e",
            "efficiency": {
                "compression": "both",
                "storage_efficiency_mode": "default",
                "dedupe": "both",
                "cross_volume_dedupe": "both",
                "compaction": compaction,
                "schedule": "-",
                "volume_path": "/vol/test_e",
                "state": state,
                "op_state": status,
                "type": "regular",
                "progress": "Idle for 02:06:26",
                "last_op_begin": "Mon Jan 02 00:10:00 2023",
                "last_op_end": "Mon Jan 02 00:10:00 2023",
                "last_op_size": 0,
                "last_op_state": "Success",
                "policy": {"name": policy}
            }
        }],
        "num_records": 1
    }


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'volume_efficiency_info': (200, return_vol_info_rest(), None),
    'volume_efficiency_status_running': (200, return_vol_info_rest(status='active'), None),
    'volume_efficiency_disabled': (200, return_vol_info_rest(state='disabled'), None),
    'volume_efficiency_modify': (200, return_vol_info_rest(compaction='none'), None),
    "unauthorized": (403, None, {'code': 6, 'message': 'Unexpected argument "storage_efficiency_mode".'}),
    "unexpected_arg": (403, None, {'code': 6, 'message': "not authorized for that command"})
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "vserver"]
    error = create_module(volume_efficiency_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['path']
    assert 'one of the following is required: path, volume_name' in create_module(volume_efficiency_module, DEFAULT_ARGS_COPY, fail=True)['msg']


def test_ensure_get_called_existing():
    ''' test get_volume_efficiency for existing config '''
    register_responses([
        ('sis-get-iter', ZRR['vol_eff_info'])
    ])
    my_obj = create_module(volume_efficiency_module, DEFAULT_ARGS)
    assert my_obj.get_volume_efficiency()


def test_successful_enable():
    ''' enable volume_efficiency and testing idempotency '''
    register_responses([
        ('sis-get-iter', ZRR['vol_eff_info_disabled']),
        ('sis-enable', ZRR['success']),
        ('sis-get-iter', ZRR['vol_eff_info']),
        # idempotency check
        ('sis-get-iter', ZRR['vol_eff_info']),

    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['path']
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS_COPY, {'volume_name': 'volTest'})['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS)['changed']


def test_successful_disable():
    ''' disable volume_efficiency and testing idempotency '''
    register_responses([
        ('sis-get-iter', ZRR['vol_eff_info']),
        ('sis-disable', ZRR['success']),
        # idempotency check
        ('sis-get-iter', ZRR['vol_eff_info_disabled']),

    ])
    args = {
        'state': 'absent',
        'use_rest': 'never'
    }
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, args)['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, args)['changed']


def test_successful_modify():
    ''' modifying volume_efficiency config and testing idempotency '''
    register_responses([
        ('sis-get-iter', ZRR['vol_eff_info']),
        ('sis-set-config', ZRR['success']),
        # idempotency check
        ('sis-get-iter', ZRR['vol_eff_info_policy']),

    ])
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS, {'policy': 'default'})['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS, {'policy': 'default'})['changed']


def test_successful_start():
    ''' start volume_efficiency and testing idempotency '''
    register_responses([
        ('sis-get-iter', ZRR['vol_eff_info']),
        ('sis-start', ZRR['success']),
        # idempotency check
        ('sis-get-iter', ZRR['vol_eff_info_running']),

    ])
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS, {'volume_efficiency': 'start'})['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS, {'volume_efficiency': 'start'})['changed']


def test_successful_stop():
    ''' stop volume_efficiency and testing idempotency '''
    register_responses([
        ('sis-get-iter', ZRR['vol_eff_info_running']),
        ('sis-stop', ZRR['success']),
        # idempotency check
        ('sis-get-iter', ZRR['vol_eff_info']),

    ])
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS, {'volume_efficiency': 'stop'})['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS, {'volume_efficiency': 'stop'})['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('sis-get-iter', ZRR['error']),
        ('sis-set-config', ZRR['error']),
        ('sis-start', ZRR['error']),
        ('sis-stop', ZRR['error']),
        ('sis-enable', ZRR['error']),
        ('sis-disable', ZRR['error']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['generic_error']),
        ('PATCH', 'storage/volumes', SRR['generic_error']),
        ('PATCH', 'storage/volumes', SRR['unauthorized']),
        ('PATCH', 'storage/volumes', SRR['unexpected_arg'])
    ])
    vol_eff_obj = create_module(volume_efficiency_module, DEFAULT_ARGS)
    assert 'Error getting volume efficiency' in expect_and_capture_ansible_exception(vol_eff_obj.get_volume_efficiency, 'fail')['msg']
    assert 'Error modifying storage efficiency' in expect_and_capture_ansible_exception(vol_eff_obj.modify_volume_efficiency, 'fail', {})['msg']
    assert 'Error starting storage efficiency' in expect_and_capture_ansible_exception(vol_eff_obj.start_volume_efficiency, 'fail')['msg']
    assert 'Error stopping storage efficiency' in expect_and_capture_ansible_exception(vol_eff_obj.stop_volume_efficiency, 'fail')['msg']
    assert 'Error enabling storage efficiency' in expect_and_capture_ansible_exception(vol_eff_obj.enable_volume_efficiency, 'fail')['msg']
    assert 'Error disabling storage efficiency' in expect_and_capture_ansible_exception(vol_eff_obj.disable_volume_efficiency, 'fail')['msg']

    args = {'state': 'absent', 'enable_compression': True}
    modify = {'enabled': 'disabled'}
    vol_eff_obj = create_module(volume_efficiency_module, DEFAULT_ARGS_REST, args)
    assert 'Error getting volume efficiency' in expect_and_capture_ansible_exception(vol_eff_obj.get_volume_efficiency, 'fail')['msg']
    assert 'Error in volume/efficiency patch' in expect_and_capture_ansible_exception(vol_eff_obj.modify_volume_efficiency, 'fail', {'arg': 1})['msg']
    assert 'cannot modify storage_efficiency' in expect_and_capture_ansible_exception(vol_eff_obj.modify_volume_efficiency, 'fail', {'arg': 1})['msg']
    assert 'user is not authorized' in expect_and_capture_ansible_exception(vol_eff_obj.modify_volume_efficiency, 'fail', {'arg': 1})['msg']
    # Error: cannot set compression keys: ['enable_compression']
    assert 'when volume efficiency already disabled' in expect_and_capture_ansible_exception(vol_eff_obj.validate_efficiency_compression, 'fail', {})['msg']
    assert 'when trying to disable volume' in expect_and_capture_ansible_exception(vol_eff_obj.validate_efficiency_compression, 'fail', modify)['msg']


def test_successful_enable_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_disabled']),
        ('PATCH', 'storage/volumes/25311eff', SRR['success']),
        # idempotency check
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_info']),
    ])
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, {'use_rest': 'always'})['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, {'use_rest': 'always'})['changed']


def test_successful_disable_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_info']),
        ('PATCH', 'storage/volumes/25311eff', SRR['success']),
        # idempotency check
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_disabled']),
    ])
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, {'state': 'absent'})['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, {'state': 'absent'})['changed']


def test_successful_modify_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_info']),
        ('PATCH', 'storage/volumes/25311eff', SRR['success']),
        # idempotency check
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_modify']),
    ])
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, {'enable_data_compaction': False})['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, {'enable_data_compaction': False})['changed']


def test_successful_enable_vol_efficiency_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_disabled']),
        ('PATCH', 'storage/volumes/25311eff', SRR['success']),
        # idempotency check
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_info']),
    ])
    DEFAULT_ARGS_REST_COPY = DEFAULT_ARGS_REST.copy()
    del DEFAULT_ARGS_REST_COPY['path']
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST_COPY, {'volume_name': 'vol1'})['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST)['changed']


def test_successful_start_rest_all_options():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_info']),
        ('PATCH', 'storage/volumes/25311eff', SRR['success']),
        # idempotency check
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_status_running']),
    ])
    args = {
        'volume_efficiency': 'start',
        'start_ve_scan_old_data': True
    }
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, args)['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, args)['changed']


def test_successful_stop_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_status_running']),
        ('PATCH', 'storage/volumes/25311eff', SRR['success']),
        # idempotency check
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_info']),
    ])
    args = {'volume_efficiency': 'stop'}
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, args)['changed']
    assert not create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, args)['changed']


def test_negative_modify_rest_se_mode_no_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    error = 'Error: Minimum version of ONTAP for storage_efficiency_mode is (9, 10, 1)'
    assert error in create_module(volume_efficiency_module, DEFAULT_ARGS_REST, {'storage_efficiency_mode': 'default'}, fail=True)['msg']
    error = 'Error: cannot set storage_efficiency_mode in ZAPI'
    assert error in create_module(volume_efficiency_module, DEFAULT_ARGS, {'storage_efficiency_mode': 'default'}, fail=True)['msg']


def test_modify_rest_se_mode():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/volumes', SRR['volume_efficiency_info']),
        ('PATCH', 'storage/volumes/25311eff', SRR['success'])
    ])
    assert create_and_apply(volume_efficiency_module, DEFAULT_ARGS_REST, {'storage_efficiency_mode': 'efficient'})['changed']
