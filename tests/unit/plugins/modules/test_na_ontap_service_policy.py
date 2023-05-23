# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP service policy Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_no_warnings, expect_and_capture_ansible_exception, call_main, create_module, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_service_policy import NetAppOntapServicePolicy as my_module, main as my_main


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'name': 'sp123',
}


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'one_sp_record': (200, {
        "records": [{
            'name': 'sp123',
            'uuid': 'uuid123',
            'svm': dict(name='vserver'),
            'services': ['data_core'],
            'scope': 'svm',
            'ipspace': dict(name='ipspace')
        }],
        'num_records': 1
    }, None),
    'two_sp_records': (200, {
        "records": [
            {
                'name': 'sp123',
            },
            {
                'name': 'sp124',
            }],
        'num_records': 2
    }, None),
}, False)


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    module_args = {
        'hostname': ''
    }
    error = 'missing required arguments: name'
    assert error == call_main(my_main, module_args, fail=True)['msg']


def test_ensure_get_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['one_sp_record']),
    ])
    module_args = {
        'services': ['data_core'],
        'vserver': 'vserver',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is False
    assert_no_warnings()


def test_ensure_create_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['zero_records']),
        ('POST', 'network/ip/service-policies', SRR['empty_good']),
    ])
    module_args = {
        'services': ['data_core'],
        'vserver': 'vserver',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is True
    assert_no_warnings()


def test_ensure_create_called_cluster():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['zero_records']),
        ('POST', 'network/ip/service-policies', SRR['empty_good']),
    ])
    module_args = {
        'ipspace': 'ipspace',
        'services': ['data_core']
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is True
    assert_no_warnings()


def test_ensure_create_idempotent():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['one_sp_record']),
    ])
    module_args = {
        'services': ['data_core'],
        'vserver': 'vserver',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is False
    assert_no_warnings()


def test_ensure_modify_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['one_sp_record']),
        ('PATCH', 'network/ip/service-policies/uuid123', SRR['empty_good']),
    ])
    module_args = {
        'services': ['data_nfs'],
        'vserver': 'vserver',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is True
    assert_no_warnings()


def test_ensure_modify_called_no_service():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['one_sp_record']),
        ('PATCH', 'network/ip/service-policies/uuid123', SRR['empty_good']),
    ])
    module_args = {
        'services': ['no_service'],
        'vserver': 'vserver',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is True
    assert_no_warnings()


def test_ensure_delete_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['one_sp_record']),
        ('DELETE', 'network/ip/service-policies/uuid123', SRR['empty_good']),
    ])
    module_args = {
        'state': 'absent',
        'vserver': 'vserver',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is True
    assert_no_warnings()


def test_ensure_delete_idempotent():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['zero_records']),
    ])
    module_args = {
        'state': 'absent',
        'vserver': 'vserver',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is False
    assert_no_warnings()


def test_negative_extra_record():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['two_sp_records']),
    ])
    module_args = {
        'services': ['data_nfs'],
        'vserver': 'vserver',
    }
    error = 'Error in get_service_policy: calling: network/ip/service-policies: unexpected response'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_ipspace_required_1():
    module_args = {
        'services': ['data_nfs'],
        'vserver': None,
    }
    error = "vserver is None but all of the following are missing: ipspace"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_ipspace_required_2():
    module_args = {
        'scope': 'cluster',
        'services': ['data_nfs'],
        'vserver': None,
    }
    error = "scope is cluster but all of the following are missing: ipspace"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_ipspace_required_3():
    module_args = {
        'services': ['data_nfs'],
    }
    error = "one of the following is required: ipspace, vserver"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_vserver_required_1():
    module_args = {
        'scope': 'svm',
        'services': ['data_nfs'],
    }
    error = "one of the following is required: ipspace, vserver"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_vserver_required_2():
    module_args = {
        'ipspace': None,
        'scope': 'svm',
        'services': ['data_nfs'],
    }
    error = "scope is svm but all of the following are missing: vserver"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_vserver_required_3():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'ipspace': None,
        'scope': 'svm',
        'services': ['data_nfs'],
        'vserver': None,
    }
    error = 'Error: vserver cannot be None when "scope: svm" is specified.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_vserver_not_required():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'ipspace': None,
        'scope': 'cluster',
        'services': ['data_nfs'],
        'vserver': 'vserver',
    }
    error = 'Error: vserver cannot be set when "scope: cluster" is specified.  Got: vserver'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_no_service_not_alone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'scope': 'svm',
        'services': ['data_nfs', 'no_service'],
        'vserver': 'vserver',
    }
    error = "Error: no other service can be present when no_service is specified."
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_no_service_not_alone_with_cluster_scope():
    module_args = {
        'ipspace': 'ipspace',
        'scope': 'cluster',
        'services': ['data_nfs', 'no_service'],
        'vserver': 'vserver',
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    error = "Error: no other service can be present when no_service is specified."
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_extra_arg_in_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['one_sp_record']),
    ])
    module_args = {
        'ipspace': 'ipspace',
        'scope': 'cluster',
        'services': ['data_nfs'],
    }
    error = "Error: attributes not supported in modify: {'scope': 'cluster'}"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_empty_body_in_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'scope': 'svm',
        'services': ['data_nfs'],
        'vserver': 'vserver',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    current = dict(uuid='')
    modify = {}
    error = 'Error: nothing to change - modify called with: {}'
    assert error in expect_and_capture_ansible_exception(my_obj.modify_service_policy, 'fail', current, modify)['msg']
    assert_no_warnings()


def test_negative_create_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['zero_records']),
        ('POST', 'network/ip/service-policies', SRR['generic_error']),
    ])
    module_args = {
        'scope': 'svm',
        'services': ['data_nfs'],
        'vserver': 'vserver',
    }
    error = rest_error_message('Error in create_service_policy', 'network/ip/service-policies')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_delete_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['one_sp_record']),
        ('DELETE', 'network/ip/service-policies/uuid123', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent',
        'vserver': 'vserver',
    }
    error = rest_error_message('Error in delete_service_policy', 'network/ip/service-policies/uuid123')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_modify_called():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/ip/service-policies', SRR['one_sp_record']),
        ('PATCH', 'network/ip/service-policies/uuid123', SRR['generic_error']),
    ])
    module_args = {
        'services': ['data_nfs'],
        'vserver': 'vserver',
    }
    error = rest_error_message('Error in modify_service_policy', 'network/ip/service-policies/uuid123')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_negative_unknown_services():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'services': ['data_nfs9'],
        'vserver': 'vserver',
    }
    error = 'Error: unknown service: data_nfs9.  New services may need to be added to "additional_services".'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()
    module_args = {
        'services': ['data_nfs9', 'data_cifs', 'dummy'],
        'vserver': 'vserver',
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    for needle in ['Error: unknown services:', 'data_nfs9', 'dummy']:
        assert needle in error
    assert 'data_cifs' not in error
    assert_no_warnings()
