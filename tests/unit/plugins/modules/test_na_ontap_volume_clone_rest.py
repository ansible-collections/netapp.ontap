# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_clone \
    import NetAppONTAPVolumeClone as my_module  # module under test

# needed for get and modify/delete as they still use ZAPI
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request

SRR = rest_responses({
    'volume_clone': (
        200,
        {'records': [{
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
        ('POST', 'storage/volumes', SRR['empty_good']),
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
    error = expect_and_capture_ansible_exception(create_module, 'fail', my_module)['msg']
    print('Info: %s' % error)
    assert 'missing required arguments:' in error
    assert 'name' in error


def test_successfully_create_with_optional_clone():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['empty_records']),
        ('POST', 'storage/volumes', SRR['empty_good']),
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
        ('POST', 'storage/volumes', SRR['empty_good']),
    ])
    module_args = {
        'qos_policy_group_name': 'test_policy_name',
        'parent_snapshot': 'test_snapshot',
        'volume_type': 'rw',
        'parent_vserver': 'test_vserver',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


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
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    my_obj.parameters['uuid'] = '2458688d-7e24-11ec-a267-005056b30cfa'
    my_obj.parameters['split'] = True
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.start_volume_clone_split_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = "Error starting volume clone split clone_of_parent_volume: calling: storage/volumes/2458688d-7e24-11ec-a267-005056b30cfa: got Expected error."
    assert msg == exc.value.args[0]['msg']
