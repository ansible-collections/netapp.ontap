# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_qos_policy_group \
    import NetAppOntapQosPolicyGroup as qos_policy_group_module  # module under test
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'name': 'policy_1',
    'vserver': 'policy_vserver',
    'max_throughput': '800KB/s,800IOPS',
    'is_shared': True,
    'min_throughput': '100IOPS',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'https': 'True',
    'use_rest': 'never'
}


qos_policy_group_info = {
    'num-records': 1,
    'attributes-list': {
        'qos-policy-group-info': {
            'is-shared': 'true',
            'max-throughput': '800KB/s,800IOPS',
            'min-throughput': '100IOPS',
            'num-workloads': 0,
            'pgid': 8690,
            'policy-group': 'policy_1',
            'vserver': 'policy_vserver'
        }
    }
}


ZRR = zapi_responses({
    'qos_policy_info': build_zapi_response(qos_policy_group_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        qos_policy_group_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_get_nonexistent_policy():
    ''' Test if get_policy_group returns None for non-existent policy_group '''
    register_responses([
        ('qos-policy-group-get-iter', ZRR['empty'])
    ])
    qos_policy_obj = create_module(qos_policy_group_module, DEFAULT_ARGS)
    result = qos_policy_obj.get_policy_group()
    assert result is None


def test_get_existing_policy_group():
    ''' Test if get_policy_group returns details for existing policy_group '''
    register_responses([
        ('qos-policy-group-get-iter', ZRR['qos_policy_info'])
    ])
    qos_policy_obj = create_module(qos_policy_group_module, DEFAULT_ARGS)
    result = qos_policy_obj.get_policy_group()
    assert result['name'] == DEFAULT_ARGS['name']
    assert result['vserver'] == DEFAULT_ARGS['vserver']


def test_create_error_missing_param():
    ''' Test if create throws an error if name is not specified'''
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['name']
    error = create_module(qos_policy_group_module, DEFAULT_ARGS_COPY, fail=True)['msg']
    assert 'missing required arguments: name' in error


def test_error_if_fixed_qos_options_present():
    ''' Test hrows an error if fixed_qos_options is specified in ZAPI'''
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['max_throughput']
    del DEFAULT_ARGS_COPY['min_throughput']
    del DEFAULT_ARGS_COPY['is_shared']
    DEFAULT_ARGS_COPY['fixed_qos_options'] = {'max_throughput_iops': 100}
    error = create_module(qos_policy_group_module, DEFAULT_ARGS_COPY, fail=True)['msg']
    assert "Error: 'fixed_qos_options' not supported with ZAPI, use 'max_throughput' and 'min_throughput'" in error


def test_successful_create():
    ''' Test successful create '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['empty']),
        ('qos-policy-group-create', ZRR['success'])
    ])
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS)['changed']


def test_create_idempotency():
    ''' Test create idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['qos_policy_info'])
    ])
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS)['changed'] is False


def test_create_error():
    ''' Test create error '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['empty']),
        ('qos-policy-group-create', ZRR['error'])
    ])
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'Error creating qos policy group policy_1' in error


def test_successful_delete():
    ''' Test delete existing volume '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['qos_policy_info']),
        ('qos-policy-group-delete', ZRR['success'])
    ])
    args = {
        'state': 'absent',
        'force': True
    }
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS, args)['changed']


def test_delete_idempotency():
    ''' Test delete idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['empty'])
    ])
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS, {'state': 'absent'})['changed'] is False


def test_delete_error():
    ''' Test create idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['qos_policy_info']),
        ('qos-policy-group-delete', ZRR['error'])
    ])
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS, {'state': 'absent'}, fail=True)['msg']
    assert 'Error deleting qos policy group policy_1' in error


def test_successful_modify_max_throughput():
    ''' Test successful modify max throughput '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['qos_policy_info']),
        ('qos-policy-group-modify', ZRR['success'])
    ])
    args = {'max_throughput': '900KB/s,800iops'}
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS, args)['changed']


def test_modify_max_throughput_idempotency():
    ''' Test modify idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['qos_policy_info'])
    ])
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS)['changed'] is False


def test_modify_error():
    ''' Test create idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['qos_policy_info']),
        ('qos-policy-group-modify', ZRR['error'])
    ])
    args = {'max_throughput': '900KB/s,800iops'}
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error modifying qos policy group policy_1' in error


def test_modify_is_shared_error():
    ''' Test create idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['qos_policy_info'])
    ])
    args = {
        'is_shared': False,
        'max_throughput': '900KB/s,900IOPS'
    }
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert "Error cannot modify 'is_shared' attribute." in error


def test_rename():
    ''' Test rename idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['qos_policy_info']),
        ('qos-policy-group-rename', ZRR['success'])
    ])
    args = {
        'name': 'policy_2',
        'from_name': 'policy_1'
    }
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS, args)['changed']


def test_rename_idempotency():
    ''' Test rename idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['qos_policy_info'])
    ])
    args = {
        'from_name': 'policy_1'
    }
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS, args)['changed'] is False


def test_rename_error():
    ''' Test create idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['qos_policy_info']),
        ('qos-policy-group-rename', ZRR['error'])
    ])
    args = {
        'name': 'policy_2',
        'from_name': 'policy_1'
    }
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error renaming qos policy group policy_1' in error


def test_rename_non_existent_policy():
    ''' Test create idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['empty'])
    ])
    args = {
        'name': 'policy_10',
        'from_name': 'policy_11'
    }
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error renaming qos policy group: cannot find' in error


def test_get_policy_error():
    ''' Test create idempotency '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('qos-policy-group-get-iter', ZRR['error'])
    ])
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'Error fetching qos policy group' in error


DEFAULT_ARGS_REST = {
    'name': 'policy_1',
    'vserver': 'policy_vserver',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'https': 'True',
    'use_rest': 'always',
    'fixed_qos_options': {
        'capacity_shared': False,
        'max_throughput_iops': 1000,
        'max_throughput_mbps': 100,
        'min_throughput_iops': 100,
        'min_throughput_mbps': 50
    }
}


SRR = rest_responses({
    'qos_policy_info': (200, {"records": [
        {
            "uuid": "e4f703dc-bfbc-11ec-a164-005056b3bd39",
            "svm": {"name": "policy_vserver"},
            "name": "policy_1",
            "fixed": {
                "max_throughput_iops": 1000,
                "max_throughput_mbps": 100,
                "min_throughput_iops": 100,
                'min_throughput_mbps': 50,
                "capacity_shared": False
            }
        }
    ], 'num_records': 1}, None),
    'adaptive_policy_info': (200, {"records": [
        {
            'uuid': '30d2fdd6-c45a-11ec-a164-005056b3bd39',
            'svm': {'name': 'policy_vserver'},
            'name': 'policy_1_',
            'adaptive': {
                'expected_iops': 200,
                'peak_iops': 500,
                'absolute_min_iops': 100
            }
        }
    ], 'num_records': 1}, None)
})


def test_successful_create_rest():
    ''' Test successful create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['empty_records']),
        ('POST', 'storage/qos/policies', SRR['success']),
    ])
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST)['changed']


def test_create_idempotency_rest():
    ''' Test create idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['qos_policy_info']),
    ])
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST)['changed'] is False


def test_successful_create_adaptive_rest():
    ''' Test successful create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['empty_records']),
        ('POST', 'storage/qos/policies', SRR['success']),
    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS_REST.copy()
    del DEFAULT_ARGS_COPY['fixed_qos_options']
    DEFAULT_ARGS_COPY['adaptive_qos_options'] = {
        "absolute_min_iops": 100,
        "expected_iops": 200,
        "peak_iops": 500
    }
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS_COPY)['changed']


def test_error_create_adaptive_rest():
    ''' Test successful create '''
    DEFAULT_ARGS_COPY = DEFAULT_ARGS_REST.copy()
    del DEFAULT_ARGS_COPY['fixed_qos_options']
    DEFAULT_ARGS_COPY['adaptive_qos_options'] = {
        "absolute_min_iops": 100,
        "expected_iops": 200
    }
    error = create_module(qos_policy_group_module, DEFAULT_ARGS_COPY, fail=True)['msg']
    assert "missing required arguments: peak_iops found in adaptive_qos_options" in error


def test_create_error_rest():
    ''' Test create error '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['empty_records']),
        ('POST', 'storage/qos/policies', SRR['generic_error']),
    ])
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST, fail=True)['msg']
    assert 'Error creating qos policy group policy_1' in error


def test_successful_delete_rest():
    ''' Test delete existing volume '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['qos_policy_info']),
        ('DELETE', 'storage/qos/policies/e4f703dc-bfbc-11ec-a164-005056b3bd39', SRR['success'])
    ])
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST, {'state': 'absent'})['changed']


def test_delete_idempotency_rest():
    ''' Test delete idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['empty_records'])
    ])
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST, {'state': 'absent'})['changed'] is False


def test_create_error_fixed_adaptive_qos_options_missing():
    ''' Error if fixed_qos_optios not present in create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['empty_records'])
    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS_REST.copy()
    del DEFAULT_ARGS_COPY['fixed_qos_options']
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS_COPY, fail=True)['msg']
    assert "Error: atleast one throughput in 'fixed_qos_options' or all 'adaptive_qos_options'" in error


def test_delete_error_rest():
    ''' Test delete error '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['qos_policy_info']),
        ('DELETE', 'storage/qos/policies/e4f703dc-bfbc-11ec-a164-005056b3bd39', SRR['generic_error'])
    ])
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST, {'state': 'absent'}, fail=True)['msg']
    assert 'Error deleting qos policy group policy_1' in error


def test_successful_modify_max_throughput_rest():
    ''' Test successful modify max throughput '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['qos_policy_info']),
        ('PATCH', 'storage/qos/policies/e4f703dc-bfbc-11ec-a164-005056b3bd39', SRR['success'])
    ])
    args = {'fixed_qos_options': {
        'max_throughput_iops': 2000,
        'max_throughput_mbps': 300,
        'min_throughput_iops': 400,
        'min_throughput_mbps': 700
    }}
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST, args)['changed']


def test_modify_max_throughput_idempotency_rest():
    ''' Test modify idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['qos_policy_info'])
    ])
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST)['changed'] is False


def test_successful_modify_adaptive_qos_options_rest():
    ''' Test successful modify max throughput '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['adaptive_policy_info']),
        ('PATCH', 'storage/qos/policies/30d2fdd6-c45a-11ec-a164-005056b3bd39', SRR['success'])
    ])
    DEFAULT_ARGS_REST_COPY = DEFAULT_ARGS_REST.copy()
    del DEFAULT_ARGS_REST_COPY['fixed_qos_options']
    args = {
        'adaptive_qos_options': {
            'expected_iops': 300,
            'peak_iops': 600,
            'absolute_min_iops': 200
        }
    }
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST_COPY, args)['changed']


def test_error_adaptive_qos_options_zapi():
    ''' Test error adaptive_qos_options zapi '''
    DEFAULT_ARGS_REST_COPY = DEFAULT_ARGS_REST.copy()
    del DEFAULT_ARGS_REST_COPY['fixed_qos_options']
    DEFAULT_ARGS_REST_COPY['use_rest'] = 'never'
    args = {
        'adaptive_qos_options': {
            'expected_iops': 300,
            'peak_iops': 600,
            'absolute_min_iops': 200
        }
    }
    error = create_module(qos_policy_group_module, DEFAULT_ARGS_REST_COPY, args, fail=True)['msg']
    assert "Error: use 'na_ontap_qos_adaptive_policy_group' module for create/modify/delete adaptive policy with ZAPI" in error


def test_modify_error_rest():
    ''' Test modify error rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['qos_policy_info']),
        ('PATCH', 'storage/qos/policies/e4f703dc-bfbc-11ec-a164-005056b3bd39', SRR['generic_error'])
    ])
    args = {'fixed_qos_options': {
        'max_throughput_iops': 2000,
        'max_throughput_mbps': 300,
        'min_throughput_iops': 400,
        'min_throughput_mbps': 700
    }}
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST, args, fail=True)['msg']
    assert 'Error modifying qos policy group policy_1' in error


def test_rename_rest():
    ''' Test rename '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['empty_records']),
        ('GET', 'storage/qos/policies', SRR['qos_policy_info']),
        ('PATCH', 'storage/qos/policies/e4f703dc-bfbc-11ec-a164-005056b3bd39', SRR['success'])
    ])
    args = {
        'name': 'policy_2',
        'from_name': 'policy_1'
    }
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST, args)['changed']


def test_rename_idempotency_rest():
    ''' Test rename idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['qos_policy_info'])
    ])
    args = {
        'from_name': 'policy_1'
    }
    assert create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST, args)['changed'] is False


def test_rename_error_rest():
    ''' Test create idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['empty_records']),
        ('GET', 'storage/qos/policies', SRR['qos_policy_info']),
        ('PATCH', 'storage/qos/policies/e4f703dc-bfbc-11ec-a164-005056b3bd39', SRR['generic_error'])
    ])
    args = {
        'name': 'policy_2',
        'from_name': 'policy_1'
    }
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST, args, fail=True)['msg']
    assert 'Error renaming qos policy group policy_1' in error


def test_get_policy_error_rest():
    ''' Test get policy error rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'storage/qos/policies', SRR['generic_error'])
    ])
    error = create_and_apply(qos_policy_group_module, DEFAULT_ARGS_REST, fail=True)['msg']
    assert 'Error fetching qos policy group policy_1' in error
