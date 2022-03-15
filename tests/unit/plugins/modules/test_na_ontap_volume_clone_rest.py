# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_clone \
    import NetAppONTAPVolumeClone as my_module  # module under test

# needed for get and modify/delete as they still use ZAPI
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request

clone_info = {
    "clone": {
        "is_flexclone": True,
        "parent_snapshot": {
            "name": "clone_ansibleVolume12_.2022-01-25_211704.0"
        },
        "parent_svm": {
            "name": "ansibleSVM"
        },
        "parent_volume": {
            "name": "ansibleVolume12"
        }
    },
    "name": "ansibleVolume12_clone",
    "nas": {
        "gid": 0,
        "uid": 0
    },
    "svm": {
        "name": "ansibleSVM"
    },
    "uuid": "2458688d-7e24-11ec-a267-005056b30cfa"
}

clone_info_no_uuid = dict(clone_info)
clone_info_no_uuid.pop('uuid')
clone_info_not_a_clone = copy.deepcopy(clone_info)
clone_info_not_a_clone['clone']['is_flexclone'] = False

SRR = rest_responses({
    'volume_clone': (
        200,
        {'records': [
            clone_info,
        ]}, None
    ),
    'volume_clone_no_uuid': (
        200,
        {'records': [
            clone_info_no_uuid,
        ]}, None
    ),
    'volume_clone_not_a_clone': (
        200,
        {'records': [
            clone_info_not_a_clone,
        ]}, None
    ),
    'two_records': (
        200,
        {'records': [
            clone_info,
            clone_info_no_uuid,
        ]}, None
    )
})


DEFAULT_ARGS = {
    'vserver': 'ansibleSVM',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
    'name': 'clone_of_parent_volume',
    'parent_volume': 'parent_volume'
}


def test_successfully_create_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('POST', 'storage/volumes', SRR['volume_clone']),
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {})['changed']


def test_error_getting_volume_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['generic_error']),
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error getting volume clone clone_of_parent_volume: calling: storage/volumes: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_volume_clone_rest, 'fail')['msg']


def test_error_creating_volume_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'storage/volumes', SRR['generic_error']),
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error creating volume clone clone_of_parent_volume: calling: storage/volumes: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.create_volume_clone_rest, 'fail')['msg']


def test_error_space_reserve_volume_clone():
    error = create_module(my_module, fail=True)['msg']
    print('Info: %s' % error)
    assert 'missing required arguments:' in error
    assert 'name' in error


def test_successfully_create_with_optional_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('POST', 'storage/volumes', SRR['volume_clone']),
    ])
    module_args = {
        'qos_policy_group_name': 'test_policy_name',
        'parent_snapshot': 'test_snapshot',
        'volume_type': 'rw',
        'junction_path': '/test_junction_path',
        'uid': 10,
        'gid': 20,
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successfully_create_with_parent_vserver_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('POST', 'storage/volumes', SRR['volume_clone']),
    ])
    module_args = {
        'qos_policy_group_name': 'test_policy_name',
        'parent_snapshot': 'test_snapshot',
        'volume_type': 'rw',
        'parent_vserver': 'test_vserver',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successfully_create_and_split_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('POST', 'storage/volumes', SRR['volume_clone']),
        ('PATCH', 'storage/volumes/2458688d-7e24-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {'split': True}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_negative_create_no_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('POST', 'storage/volumes', SRR['empty_records']),
    ])
    module_args = {'split': True}
    msg = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert msg == 'Error starting volume clone split clone_of_parent_volume: clone UUID is not set'


def test_negative_create_no_uuid_in_response():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('POST', 'storage/volumes', SRR['volume_clone_no_uuid']),
    ])
    module_args = {'split': True}
    msg = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert msg.startswith('Error: failed to parse create clone response: uuid key not present in')


def test_negative_create_bad_response():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('POST', 'storage/volumes', SRR['two_records']),
    ])
    module_args = {'split': True}
    msg = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert msg.startswith('Error: failed to parse create clone response: calling: storage/volumes: unexpected response ')


def test_successfully_split_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['volume_clone']),
        ('PATCH', 'storage/volumes/2458688d-7e24-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {'split': True}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_split_volume_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/volumes/2458688d-7e24-11ec-a267-005056b30cfa', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.uuid = '2458688d-7e24-11ec-a267-005056b30cfa'
    my_obj.parameters['split'] = True
    msg = "Error starting volume clone split clone_of_parent_volume: calling: storage/volumes/2458688d-7e24-11ec-a267-005056b30cfa: got Expected error."
    assert msg == expect_and_capture_ansible_exception(my_obj.start_volume_clone_split_rest, 'fail')['msg']


def test_volume_not_a_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['volume_clone_not_a_clone']),
    ])
    module_args = {'split': True}
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_volume_not_a_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['volume_clone_not_a_clone']),
    ])
    module_args = {'split': False}
    msg = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert msg == 'Error: a volume clone_of_parent_volume which is not a FlexClone already exists, and split not requested.'
