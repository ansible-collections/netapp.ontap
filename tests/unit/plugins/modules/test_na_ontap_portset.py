# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for ONTAP Ansible module: na_ontap_portset'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_portset \
    import NetAppONTAPPortset as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


DEFAULT_ARGS = {
    'state': 'present',
    'name': 'test',
    'type': 'mixed',
    'vserver': 'ansible_test',
    'ports': ['a1', 'a2'],
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'never'
}


portset_info = {
    'num-records': 1,
    'attributes-list': {
        'portset-info': {
            'portset-name': 'test',
            'vserver': 'ansible_test',
            'portset-type': 'mixed',
            'portset-port-total': '2',
            'portset-port-info': [
                {'portset-port-name': 'a1'},
                {'portset-port-name': 'a2'}
            ]
        }
    }
}


ZRR = zapi_responses({
    'portset_info': build_zapi_response(portset_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "name", "vserver"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_ensure_portset_get_called():
    ''' a more interesting test '''
    register_responses([
        ('portset-get-iter', ZRR['empty'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    portset = my_obj.portset_get()
    assert portset is None


def test_create_portset():
    ''' Test successful create '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('portset-get-iter', ZRR['empty']),
        ('portset-create', ZRR['success']),
        ('portset-add', ZRR['success']),
        ('portset-add', ZRR['success'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_modify_ports():
    ''' Test modify_portset method '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('portset-get-iter', ZRR['portset_info']),
        ('portset-add', ZRR['success']),
        ('portset-add', ZRR['success']),
        ('portset-remove', ZRR['success']),
        ('portset-remove', ZRR['success'])
    ])
    args = {'ports': ['l1', 'l2']}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_delete_portset():
    ''' Test successful delete '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('portset-get-iter', ZRR['portset_info']),
        ('portset-destroy', ZRR['success'])
    ])
    args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_error_type_create():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('portset-get-iter', ZRR['empty'])
    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['type']
    error = 'Error: Missing required parameter for create (type)'
    assert error in create_and_apply(my_module, DEFAULT_ARGS_COPY, fail=True)['msg']


def test_if_all_methods_catch_exception():
    register_responses([
        ('portset-get-iter', ZRR['error']),
        ('portset-create', ZRR['error']),
        ('portset-add', ZRR['error']),
        ('portset-remove', ZRR['error']),
        ('portset-destroy', ZRR['error'])
    ])
    portset_obj = create_module(my_module, DEFAULT_ARGS)

    error = expect_and_capture_ansible_exception(portset_obj.portset_get, 'fail')['msg']
    assert 'Error fetching portset' in error

    error = expect_and_capture_ansible_exception(portset_obj.create_portset, 'fail')['msg']
    assert 'Error creating portse' in error

    error = expect_and_capture_ansible_exception(portset_obj.modify_port, 'fail', 'a1', 'portset-add', 'adding')['msg']
    assert 'Error adding port in portset' in error

    error = expect_and_capture_ansible_exception(portset_obj.modify_port, 'fail', 'a2', 'portset-remove', 'removing')['msg']
    assert 'Error removing port in portset' in error

    error = expect_and_capture_ansible_exception(portset_obj.delete_portset, 'fail')['msg']
    assert 'Error deleting portset' in error


SRR = rest_responses({
    'mixed_portset_info': (200, {"records": [{
        "interfaces": [
            {
                "fc": {
                    "name": "lif_1",
                    "uuid": "d229cc03"
                }
            },
            {
                "ip": {
                    "name": "lif_2",
                    "uuid": "1cd8a442"
                }
            }
        ],
        "name": "mixed_ps",
        "protocol": "mixed",
        "uuid": "312aa85b"
    }], "num_records": 1}, None),
    'fc_portset_info': (200, {"records": [{
        "interfaces": [
            {
                "fc": {
                    "name": "fc_1",
                    "uuid": "3a09cd42"
                }
            },
            {
                "fc": {
                    "name": "fc_2",
                    "uuid": "d24e03c6"
                }
            }
        ],
        "name": "fc_ps",
        "protocol": "fcp",
        "uuid": "5056b3b297"
    }], "num_records": 1}, None),
    'lif_1': (200, {
        "num_records": 1,
        "records": [{"uuid": "d229cc03"}]
    }, None),
    'lif_2': (200, {
        "num_records": 1,
        "records": [{"uuid": "d24e03c6"}]
    }, None),
    'fc_1': (200, {
        "num_records": 1,
        "records": [{"uuid": "3a09cd42"}]
    }, None),
    'fc_2': (200, {
        "num_records": 1,
        "records": [{"uuid": "1cd8b542"}]
    }, None)
})


def test_create_portset_rest():
    ''' Test successful create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['empty_records']),
        ('GET', 'network/ip/interfaces', SRR['empty_records']),
        ('GET', 'network/fc/interfaces', SRR['lif_1']),
        ('GET', 'network/ip/interfaces', SRR['lif_2']),
        ('GET', 'network/fc/interfaces', SRR['empty_records']),
        ('POST', 'protocols/san/portsets', SRR['success'])
    ])
    args = {'use_rest': 'always'}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_create_portset_idempotency_rest():
    ''' Test successful create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['mixed_portset_info'])
    ])
    args = {'use_rest': 'always', "ports": ["lif_1", "lif_2"]}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed'] is False


def test_modify_remove_ports_rest():
    ''' Test modify_portset method '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['mixed_portset_info']),
        ('DELETE', 'protocols/san/portsets/312aa85b/interfaces/1cd8a442', SRR['success'])
    ])
    args = {'use_rest': 'always', "ports": ["lif_1"]}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_modify_add_ports_rest():
    ''' Test modify_portset method '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['mixed_portset_info']),
        ('GET', 'network/ip/interfaces', SRR['empty_records']),
        ('GET', 'network/fc/interfaces', SRR['fc_1']),
        ('POST', 'protocols/san/portsets/312aa85b/interfaces', SRR['success'])
    ])
    args = {'use_rest': 'always', "ports": ["lif_1", "lif_2", "fc_1"]}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_delete_portset_rest():
    ''' Test modify_portset method '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['mixed_portset_info']),
        ('DELETE', 'protocols/san/portsets/312aa85b', SRR['success'])
    ])
    args = {'use_rest': 'always', 'state': 'absent', 'ports': ['lif_1', 'lif_2']}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_get_portset_error_rest():
    ''' Test modify_portset method '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['generic_error'])
    ])
    args = {'use_rest': 'always', "ports": ["lif_1", "lif_2", "fc_1"]}
    error = 'Error fetching portset'
    assert error in create_and_apply(my_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_create_portset_error_rest():
    ''' Test modify_portset method '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['empty_records']),
        ('POST', 'protocols/san/portsets', SRR['generic_error'])
    ])
    args = {'use_rest': 'always', "ports": []}
    error = 'Error creating portset'
    assert error in create_and_apply(my_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_delete_portset_error_rest():
    ''' Test modify_portset method '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['mixed_portset_info']),
        ('DELETE', 'protocols/san/portsets/312aa85b', SRR['generic_error'])
    ])
    args = {'use_rest': 'always', 'state': 'absent', "ports": ["lif_1", "lif_2"]}
    error = 'Error deleting portset'
    assert error in create_and_apply(my_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_add_portset_error_rest():
    ''' Test modify_portset method '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['mixed_portset_info']),
        ('GET', 'network/ip/interfaces', SRR['empty_records']),
        ('GET', 'network/fc/interfaces', SRR['fc_1']),
        ('POST', 'protocols/san/portsets/312aa85b/interfaces', SRR['generic_error'])
    ])
    args = {'use_rest': 'always', "ports": ["lif_1", "lif_2", "fc_1"]}
    error = "Error adding port in portset"
    assert error in create_and_apply(my_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_remove_portset_error_rest():
    ''' Test modify_portset method '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['mixed_portset_info']),
        ('DELETE', 'protocols/san/portsets/312aa85b/interfaces/1cd8a442', SRR['generic_error'])
    ])
    args = {'use_rest': 'always', "ports": ["lif_1"]}
    error = "Error removing port in portset"
    assert error in create_and_apply(my_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_add_ip_port_to_fc_error_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['fc_portset_info']),
        ('GET', 'network/fc/interfaces', SRR['empty_records'])
    ])
    args = {'use_rest': 'always', "type": "fcp", "ports": ["fc_1", "fc_2", "lif_2"]}
    error = 'Error: lifs: lif_2 of type fcp not found in vserver'
    assert error in create_and_apply(my_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_get_lif_error_rest():
    ''' Test modify_portset method '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['mixed_portset_info']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('GET', 'network/fc/interfaces', SRR['generic_error'])
    ])
    args = {'use_rest': 'always', "ports": ["lif_1", "lif_2", "fc_1"]}
    error = "Error fetching lifs details for fc_1"
    assert error in create_and_apply(my_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_try_to_modify_protocol_error_rest():
    ''' Test modify_portset method '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/portsets', SRR['mixed_portset_info'])
    ])
    args = {'use_rest': 'always', "type": "iscsi", "ports": ["lif_1", "lif_2"]}
    error = "modify protocol(type) not supported"
    assert error in create_and_apply(my_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_invalid_value_port_rest():
    ''' Test invalid error '''
    args = {'use_rest': 'always', "type": "iscsi", "ports": ["lif_1", ""]}
    error = "Error: invalid value specified for ports"
    assert error in create_module(my_module, DEFAULT_ARGS, args, fail=True)['msg']


def test_module_ontap_9_9_0_rest_auto():
    ''' Test fall back to ZAPI '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    args = {'use_rest': 'auto'}
    assert create_module(my_module, DEFAULT_ARGS, args).use_rest is False


def test_module_ontap_9_9_0_rest_always():
    ''' Test error when rest below 9.9.1 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    args = {'use_rest': 'always'}
    msg = "Error: REST requires ONTAP 9.9.1 or later for portset APIs."
    assert msg in create_module(my_module, DEFAULT_ARGS, args, fail=True)['msg']
