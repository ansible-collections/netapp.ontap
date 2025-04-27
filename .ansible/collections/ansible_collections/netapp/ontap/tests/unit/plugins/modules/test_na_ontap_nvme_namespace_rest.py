# (c) 2022-2025, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_aggregate when using REST """

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_nvme_namespace \
    import NetAppONTAPNVMENamespace as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'is_ontap_system': (200, {'ASA_NEXT_STRICT': False, 'ASA_NEXT': False, 'ASA_LEGACY': False, 'ASA_ANY': False, 'ONTAP_X_STRICT': False,
                        'ONTAP_X': False, 'ONTAP_9_STRICT': True, 'ONTAP_9': True}, None),
    'is_asa_r2_system': (200, {'ASA_R2': True, 'ASA_LEGACY': False, 'ASA_ANY': True, 'ONTAP_AI_ML': False, 'ONTAP_X': True, 'ONTAP_9': False}, None),
    'nvme_namespace': (200, {"records": [
        {
            "name": "/vol/test/disk1",
            "uuid": "81068ae6-4674-4d78-a8b7-dadb23f67edf",
            "svm": {
                "name": "ansibleSVM"
            },
            "enabled": True,
            "space": {
                "size": 5
            }
        }
    ], "num_records": 1
    }, None),

    'nvme_namespace_get_one': (200, {"records": [
        {
            "name": "/vol/test/disk1",
            "uuid": "81068ae6-4674-4d78-a8b7-dadb23f67edf",
            "svm": {
                "name": "ansibleSVM"
            },
            "enabled": True,
            "space": {
                "size": 8
            }
        }
    ], "num_records": 1
    }, None),
    'nvme_namespace_asar2_modified': (200, {"records": [
        {
            "name": "ns_1",
            "uuid": "81068ae6-4674-4d78-a8b7-dadb23f67edf",
            "svm": {
                "name": "ansibleSVM"
            },
            "space": {
                "size": 8
            },
        }
    ], "num_records": 1
    }, None),
    'nvme_namespace_asar2_get_one': (200, {"records": [
        {
            "name": "ns_1",
            "uuid": "81068ae6-4674-4d78-a8b7-dadb23f67edf",
            "svm": {
                "name": "ansibleSVM"
            },
            "enabled": True,
            "space": {
                "size": 5
            },
            'ostype': 'linux'
        }
    ], "num_records": 1
    }, None),
    'nvme_namespace_asa_r2': (200, {"records": [
        {
            "name": "ns_1",
            "uuid": "81068ae6-4674-4d78-a8b7-dadb23f67edf",
            "svm": {
                "name": "ansibleSVM"
            },
            "enabled": True,
            "space": {
                "size": 5
            }
        },
        {
            "name": "ns_2",
            "uuid": "81068ae6-4674-4d78-a8b7-dadb23f57efg",
            "svm": {
                "name": "ansibleSVM"
            },
            "enabled": True,
            "space": {
                "size": 5
            }
        }
    ], "num_records": 2
    }, None),
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'vserver': 'ansibleSVM',
    'ostype': 'linux',
    'path': '/vol/test/disk1',
    'size': 5,
    'size_unit': 'b',
    'block_size': 4096
}


DEFAULT_ARGS_ASA_R2 = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'vserver': 'ansibleSVM',
    'ostype': 'linux',
    'path': 'ns',
    'size': 5,
    'size_unit': 'b',
    'block_size': 4096
}


DEFAULT_ARGS_ASA_R2_created = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'vserver': 'ansibleSVM',
    'ostype': 'linux',
    'path': 'ns_1',
    'size': 5,
    'size_unit': 'b',
    'block_size': 4096
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "path", "vserver"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_get_namespace_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/namespaces', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_namespace_rest() is None


def test_get_namespace_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/namespaces', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching namespace info for vserver: ansibleSVM'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_namespace_rest, 'fail')['msg']


def test_create_namespace():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/namespaces', SRR['empty_records']),
        ('POST', 'storage/namespaces', SRR['empty_good']),
    ])
    module_args = {'use_rest': 'always'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_namespace_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('POST', 'storage/namespaces', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.create_namespace_rest, 'fail')['msg']
    msg = 'Error creating namespace for vserver ansibleSVM: calling: storage/namespaces: got Expected error.'
    assert msg == error


def test_modify_namespace_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace_get_one']),
        ('PATCH', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['success']),
    ])
    args = {'size': 8}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_modify_namespace_error_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace_get_one']),
        ('PATCH', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['generic_error'])
    ])
    args = {'size': 8}
    error = create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    msg = 'Error modifying namespace for vserver ansibleSVM: calling: storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf: got Expected error.'
    assert msg in error


def test_delete_namespace():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace']),
        ('DELETE', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_namespace_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('DELETE', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.namespace_uuid = '81068ae6-4674-4d78-a8b7-dadb23f67edf'
    error = expect_and_capture_ansible_exception(my_obj.delete_namespace_rest, 'fail')['msg']
    msg = 'Error deleting namespace for vserver ansibleSVM: calling: storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf: got Expected error.'
    assert msg == error


def test_get_namespace_none_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/namespaces', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_namespace_rest() is None


def test_get_namespace_error_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/namespaces', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching namespace info for vserver: ansibleSVM'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_namespace_rest, 'fail')['msg']


def test_create_namespace_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/namespaces', SRR['empty_records']),
        ('POST', 'storage/namespaces', SRR['empty_good'])
    ])
    module_args = {'size': 5}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_namespace_error_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('POST', 'storage/namespaces', SRR['generic_error']),
    ])
    module_args = {}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = expect_and_capture_ansible_exception(my_obj.create_namespace_rest, 'fail')['msg']
    msg = 'Error creating namespace for vserver ansibleSVM: calling: storage/namespaces: got Expected error.'
    assert msg == error


def test_modify_namespace_rest_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace_get_one']),
        ('PATCH', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['success']),
    ])
    args = {'size': 8}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_modify_namespace_error_rest_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace_get_one']),
        ('PATCH', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['generic_error'])
    ])
    args = {'size': 8}
    error = create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    msg = 'Error modifying namespace for vserver ansibleSVM: calling: storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf: got Expected error.'
    assert msg in error


def test_delete_namespace_ontap_sytem():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace']),
        ('DELETE', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_namespace_error_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('DELETE', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.namespace_uuid = '81068ae6-4674-4d78-a8b7-dadb23f67edf'
    error = expect_and_capture_ansible_exception(my_obj.delete_namespace_rest, 'fail')['msg']
    msg = 'Error deleting namespace for vserver ansibleSVM: calling: storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf: got Expected error.'
    assert msg == error


def test_get_namespace_none_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/namespaces', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS_ASA_R2)
    my_obj = my_module()
    assert my_obj.get_namespace_rest() is None


def test_get_namespace_error_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/namespaces', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS_ASA_R2)
    msg = 'Error fetching namespace info for vserver: ansibleSVM'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_namespace_rest, 'fail')['msg']


def test_create_namespace_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/namespaces', SRR['empty_records']),
        ('POST', 'storage/namespaces', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace_asa_r2']),
    ])
    module_args = {'provisioning_options': {'count': 2}}
    assert create_and_apply(my_module, DEFAULT_ARGS_ASA_R2, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS_ASA_R2, module_args)['changed']


def test_create_namespace_error_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('POST', 'storage/namespaces', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS_ASA_R2)
    error = expect_and_capture_ansible_exception(my_obj.create_namespace_rest, 'fail')['msg']
    msg = 'Error creating namespace for vserver ansibleSVM: calling: storage/namespaces: got Expected error.'
    assert msg == error


def test_modify_namespace_rest_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace_asar2_get_one']),
        ('PATCH', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['success']),
    ])
    args = {'size': 10, 'path': 'ns_1', 'ostype': 'linux'}
    assert create_and_apply(my_module, DEFAULT_ARGS_ASA_R2_created, args)['changed']


def test_modify_namespace_error_rest_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace_asar2_get_one']),
        ('PATCH', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['generic_error'])
    ])
    args = {'size': 8}
    error = create_and_apply(my_module, DEFAULT_ARGS_ASA_R2_created, args, fail=True)['msg']
    msg = 'Error modifying namespace for vserver ansibleSVM: calling: storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf: got Expected error.'
    assert msg in error


def test_delete_namespace_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/namespaces', SRR['nvme_namespace_asar2_get_one']),
        ('DELETE', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/namespaces', SRR['empty_records']),
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS_ASA_R2_created, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS_ASA_R2_created, module_args)['changed']


def test_delete_namespace_error_asa_r2_sytem():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('DELETE', 'storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS_ASA_R2_created)
    my_obj.parameters['state'] = 'absent'
    my_obj.namespace_uuid = '81068ae6-4674-4d78-a8b7-dadb23f67edf'
    error = expect_and_capture_ansible_exception(my_obj.delete_namespace_rest, 'fail')['msg']
    msg = 'Error deleting namespace for vserver ansibleSVM: calling: storage/namespaces/81068ae6-4674-4d78-a8b7-dadb23f67edf: got Expected error.'
    assert msg == error


def test_error_get_asa_r2_rest():
    ''' Test error retrieving  '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['generic_error']),
    ])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    msg = "Failed while checking if the given host is an ASA r2 system or not"
    assert msg in error
