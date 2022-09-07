# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_nvme_subsystem when using REST """

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    patch_ansible, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_nvme_subsystem\
    import NetAppONTAPNVMESubsystem as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'nvme_subsystem': (200, {
        "hosts": [{
            "nqn": "nqn.1992-08.com.netapp:sn.f2207584d03611eca164005056b3bd39:subsystem.test3"
        }],
        "name": "subsystem1",
        "uuid": "81068ae6-4674-4d78-a8b7-dadb23f67edf",
        "comment": "string",
        "svm": {
            "name": "svm1",
            "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
        },
        "os_type": "hyper_v",
        "subsystem_maps": [{
            "namespace": {
                "name": "/vol/test3/disk1",
                "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
            },
        }],
        "enabled": True,
    }, None),
    # 'nvme_host': (200, [{
    #         "nqn": "nqn.1992-08.com.netapp:sn.f2207584d03611eca164005056b3bd39:subsystem.test3"
    # }], None),
    'nvme_map': (200, {
        "records": [{
            "namespace": {
                "name": "/vol/test3/disk1",
                "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412",
            },
        }], "num_records": 1,
    }, None),

    'nvme_host': (200, {
        "records": [
            {
                "nqn": "nqn.1992-08.com.netapp:sn.f2207584d03611eca164005056b3bd39:subsystem.test3",
                "subsystem": {
                    "uuid": "81068ae6-4674-4d78-a8b7-dadb23f67edf"
                }
            }
        ],
        "num_records": 1
    }, None),

    'error_svm_not_found': (400, None, 'SVM "ansibleSVM" does not exist.')
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'vserver': 'ansibleSVM',
    'ostype': 'linux',
    'subsystem': 'subsystem1',
}


def test_get_subsystem_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['empty_records'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    assert my_module_object.get_subsystem_rest() is None


def test_get_subsystem_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['generic_error']),
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching subsystem info for vserver: ansibleSVM'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_subsystem_rest, 'fail')['msg']


def test_create_subsystem():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['empty_records']),
        ('POST', 'protocols/nvme/subsystems', SRR['empty_good']),
        ('GET', 'protocols/nvme/subsystems', SRR['nvme_subsystem']),
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_create_subsystem_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('POST', 'protocols/nvme/subsystems', SRR['generic_error']),
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['zero_records']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    error = 'Error creating subsystem for vserver ansibleSVM: calling: protocols/nvme/subsystems: got Expected error.'
    assert error in expect_and_capture_ansible_exception(my_obj.create_subsystem_rest, 'fail')['msg']
    args = dict(DEFAULT_ARGS)
    del args['ostype']
    error = "Error: Missing required parameter 'ostype' for creating subsystem"
    assert error in call_main(my_main, args, fail=True)['msg']


def test_delete_subsystem():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['nvme_subsystem']),
        ('DELETE', 'protocols/nvme/subsystems/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_subsystem_no_vserver():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['error_svm_not_found']),
    ])
    module_args = {'state': 'absent'}
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_subsystem_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('DELETE', 'protocols/nvme/subsystems/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.subsystem_uuid = '81068ae6-4674-4d78-a8b7-dadb23f67edf'
    error = expect_and_capture_ansible_exception(my_obj.delete_subsystem_rest, 'fail')['msg']
    msg = 'Error deleting subsystem for vserver ansibleSVM: calling: protocols/nvme/subsystems/81068ae6-4674-4d78-a8b7-dadb23f67edf: got Expected error.'
    assert msg == error


def test_add_subsystem_host():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['empty_records']),
        ('POST', 'protocols/nvme/subsystems', SRR['empty_good']),
        ('GET', 'protocols/nvme/subsystems', SRR['nvme_subsystem']),
        ('POST', 'protocols/nvme/subsystems/81068ae6-4674-4d78-a8b7-dadb23f67edf/hosts', SRR['empty_good'])
    ])
    module_args = {'hosts': ['nqn.1992-08.com.netapp:sn.f2207584d03611eca164005056b3bd39:subsystem.test3']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_add_only_subsystem_host():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['nvme_subsystem']),
        ('GET', 'protocols/nvme/subsystems/81068ae6-4674-4d78-a8b7-dadb23f67edf/hosts', SRR['empty_records']),
        ('POST', 'protocols/nvme/subsystems/81068ae6-4674-4d78-a8b7-dadb23f67edf/hosts', SRR['empty_good'])
    ])
    module_args = {'hosts': ['nqn.1992-08.com.netapp:sn.f2207584d03611eca164005056b3bd39:subsystem.test3']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_add_subsystem_map():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['empty_records']),
        ('POST', 'protocols/nvme/subsystems', SRR['empty_good']),
        ('GET', 'protocols/nvme/subsystems', SRR['nvme_subsystem']),
        ('POST', 'protocols/nvme/subsystem-maps', SRR['empty_good'])
    ])
    module_args = {'paths': ['/vol/test3/disk1']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_add_only_subsystem_map():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['nvme_subsystem']),
        ('GET', 'protocols/nvme/subsystem-maps', SRR['empty_records']),
        ('POST', 'protocols/nvme/subsystem-maps', SRR['empty_good'])
    ])
    module_args = {'paths': ['/vol/test3/disk1']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_remove_only_subsystem_host():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['nvme_subsystem']),
        ('GET', 'protocols/nvme/subsystems/81068ae6-4674-4d78-a8b7-dadb23f67edf/hosts', SRR['nvme_host']),
        ('POST', 'protocols/nvme/subsystems/81068ae6-4674-4d78-a8b7-dadb23f67edf/hosts', SRR['empty_good']),
        ('DELETE', 'protocols/nvme/subsystems/81068ae6-4674-4d78-a8b7-dadb23f67edf/'
                   'hosts/nqn.1992-08.com.netapp:sn.f2207584d03611eca164005056b3bd39:subsystem.test3', SRR['empty_good'])
    ])
    module_args = {'hosts': ['nqn.1992-08.com.netapp:sn.f2207584d03611eca164005056b3bd39:subsystem.test']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_remove_only_subsystem_map():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems', SRR['nvme_subsystem']),
        ('GET', 'protocols/nvme/subsystem-maps', SRR['nvme_map']),
        ('POST', 'protocols/nvme/subsystem-maps', SRR['empty_good']),
        ('DELETE', 'protocols/nvme/subsystem-maps/81068ae6-4674-4d78-a8b7-dadb23f67edf/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['empty_good'])
    ])
    module_args = {'paths': ['/vol/test2/disk1']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_errors():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/nvme/subsystems/None/hosts', SRR['generic_error']),
        ('GET', 'protocols/nvme/subsystem-maps', SRR['generic_error']),
        ('POST', 'protocols/nvme/subsystems/None/hosts', SRR['generic_error']),
        ('POST', 'protocols/nvme/subsystem-maps', SRR['generic_error']),
        ('DELETE', 'protocols/nvme/subsystems/None/hosts/host', SRR['generic_error']),
        ('DELETE', 'protocols/nvme/subsystem-maps/None/None', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    error = rest_error_message('Error fetching subsystem host info for vserver: ansibleSVM', 'protocols/nvme/subsystems/None/hosts')
    assert error in expect_and_capture_ansible_exception(my_module_object.get_subsystem_host_map_rest, 'fail', 'hosts')['msg']
    error = rest_error_message('Error fetching subsystem map info for vserver: ansibleSVM', 'protocols/nvme/subsystem-maps')
    assert error in expect_and_capture_ansible_exception(my_module_object.get_subsystem_host_map_rest, 'fail', 'paths')['msg']
    error = rest_error_message('Error adding [] for subsystem subsystem1', 'protocols/nvme/subsystems/None/hosts')
    assert error in expect_and_capture_ansible_exception(my_module_object.add_subsystem_host_map_rest, 'fail', [], 'hosts')['msg']
    error = rest_error_message('Error adding path for subsystem subsystem1', 'protocols/nvme/subsystem-maps')
    assert error in expect_and_capture_ansible_exception(my_module_object.add_subsystem_host_map_rest, 'fail', ['path'], 'paths')['msg']
    error = rest_error_message('Error removing host for subsystem subsystem1', 'protocols/nvme/subsystems/None/hosts/host')
    assert error in expect_and_capture_ansible_exception(my_module_object.remove_subsystem_host_map_rest, 'fail', ['host'], 'hosts')['msg']
    error = rest_error_message('Error removing path for subsystem subsystem1', 'protocols/nvme/subsystem-maps/None/None')
    assert error in expect_and_capture_ansible_exception(my_module_object.remove_subsystem_host_map_rest, 'fail', ['path'], 'paths')['msg']
