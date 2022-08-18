# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_ucadapter '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible,\
    create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ucadapter \
    import NetAppOntapadapter as ucadapter_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')

DEFAULT_ARGS = {
    'hostname': '10.0.0.0',
    'username': 'user',
    'password': 'pass',
    'node_name': 'node1',
    'adapter_name': '0f',
    'mode': 'fc',
    'type': 'target',
    'use_rest': 'never'
}

ucm_info_mode_fc = {
    'attributes': {
        'uc-adapter-info': {
            'mode': 'fc',
            'pending-mode': 'abc',
            'type': 'target',
            'pending-type': 'intitiator',
            'status': 'up',
        }
    }
}

ucm_info_mode_cna = {
    'attributes': {
        'uc-adapter-info': {
            'mode': 'cna',
            'pending-mode': 'cna',
            'type': 'target',
            'pending-type': 'intitiator',
            'status': 'up',
        }
    }
}


ZRR = zapi_responses({
    'ucm_info': build_zapi_response(ucm_info_mode_fc),
    'ucm_info_cna': build_zapi_response(ucm_info_mode_cna)
})


SRR = rest_responses({
    'ucm_info': (200, {"records": [{
        'current_mode': 'fc',
        'current_type': 'target',
        'status_admin': 'up'
    }], "num_records": 1}, None),
    'ucm_info_cna': (200, {"records": [{
        'current_mode': 'cna',
        'current_type': 'target',
        'status_admin': 'up'
    }], "num_records": 1}, None),
    'fc_adapter_info': (200, {"records": [{
        'uuid': 'abcdef'
    }], "num_records": 1}, None)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "node_name", "adapter_name"]
    error = create_module(ucadapter_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_ensure_ucadapter_get_called():
    ''' fetching ucadapter details '''
    register_responses([
        ('ucm-adapter-get', ZRR['empty'])
    ])
    ucm_obj = create_module(ucadapter_module, DEFAULT_ARGS)
    assert ucm_obj.get_adapter() is None


def test_change_mode_from_cna_to_fc():
    ''' configuring ucadaptor and checking idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('ucm-adapter-get', ZRR['ucm_info_cna']),
        ('fcp-adapter-config-down', ZRR['success']),
        ('ucm-adapter-modify', ZRR['success']),
        ('fcp-adapter-config-up', ZRR['success']),
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('ucm-adapter-get', ZRR['ucm_info_cna'])
    ])
    assert create_and_apply(ucadapter_module, DEFAULT_ARGS)['changed']
    args = {'mode': 'cna'}
    assert not create_and_apply(ucadapter_module, DEFAULT_ARGS, args)['changed']


def test_change_mode_from_fc_to_cna():
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('ucm-adapter-get', ZRR['ucm_info']),
        ('fcp-adapter-config-down', ZRR['success']),
        ('ucm-adapter-modify', ZRR['success']),
        ('fcp-adapter-config-up', ZRR['success']),
    ])
    args = {'mode': 'cna'}
    assert create_and_apply(ucadapter_module, DEFAULT_ARGS, args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('ucm-adapter-get', ZRR['error']),
        ('ucm-adapter-modify', ZRR['error']),
        ('fcp-adapter-config-down', ZRR['error']),
        ('fcp-adapter-config-up', ZRR['error']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'network/fc/ports', SRR['generic_error']),
        ('GET', 'private/cli/ucadmin', SRR['generic_error']),
        ('PATCH', 'private/cli/ucadmin', SRR['generic_error']),
        ('PATCH', 'network/fc/ports/abcdef', SRR['generic_error']),
        ('PATCH', 'network/fc/ports/abcdef', SRR['generic_error']),
        ('GET', 'network/fc/ports', SRR['empty_records'])
    ])
    ucm_obj = create_module(ucadapter_module, DEFAULT_ARGS)
    assert 'Error fetching ucadapter' in expect_and_capture_ansible_exception(ucm_obj.get_adapter, 'fail')['msg']
    assert 'Error modifying adapter' in expect_and_capture_ansible_exception(ucm_obj.modify_adapter, 'fail')['msg']
    assert 'Error trying to down' in expect_and_capture_ansible_exception(ucm_obj.online_or_offline_adapter, 'fail', 'down', '0f')['msg']
    assert 'Error trying to up' in expect_and_capture_ansible_exception(ucm_obj.online_or_offline_adapter, 'fail', 'up', '0f')['msg']

    ucm_obj = create_module(ucadapter_module, DEFAULT_ARGS, {'use_rest': 'always'})
    ucm_obj.adapters_uuids = {'0f': 'abcdef'}
    assert 'Error fetching adapter 0f uuid' in expect_and_capture_ansible_exception(ucm_obj.get_adapter_uuid, 'fail', '0f')['msg']
    assert 'Error fetching ucadapter' in expect_and_capture_ansible_exception(ucm_obj.get_adapter, 'fail')['msg']
    assert 'Error modifying adapter' in expect_and_capture_ansible_exception(ucm_obj.modify_adapter, 'fail')['msg']
    assert 'Error trying to down' in expect_and_capture_ansible_exception(ucm_obj.online_or_offline_adapter, 'fail', 'down', '0f')['msg']
    assert 'Error trying to up' in expect_and_capture_ansible_exception(ucm_obj.online_or_offline_adapter, 'fail', 'up', '0f')['msg']
    assert 'Error: Adapter(s) 0f not exist' in expect_and_capture_ansible_exception(ucm_obj.get_adapters_uuids, 'fail')['msg']


def test_change_mode_from_cna_to_fc_rest():
    ''' configuring ucadaptor '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'private/cli/ucadmin', SRR['ucm_info_cna']),
        ('GET', 'network/fc/ports', SRR['fc_adapter_info']),
        ('PATCH', 'network/fc/ports/abcdef', SRR['success']),
        ('PATCH', 'private/cli/ucadmin', SRR['success']),
        ('PATCH', 'network/fc/ports/abcdef', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'private/cli/ucadmin', SRR['ucm_info_cna'])
    ])
    assert create_and_apply(ucadapter_module, DEFAULT_ARGS, {'use_rest': 'always'})['changed']
    args = {'mode': 'cna', 'use_rest': 'always'}
    assert not create_and_apply(ucadapter_module, DEFAULT_ARGS, args)['changed']
