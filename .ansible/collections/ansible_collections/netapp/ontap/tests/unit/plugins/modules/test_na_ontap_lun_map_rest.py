# (c) 2022-2025, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_lun_map \
    import NetAppOntapLUNMap as my_module, main as my_main  # module under test

# needed for get and modify/delete as they still use ZAPI
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

# REST API canned responses when mocking send_request

SRR = rest_responses({
    'is_ontap_system': (200, {'ASA_NEXT_STRICT': False, 'ASA_NEXT': False, 'ASA_LEGACY': False, 'ASA_ANY': False, 'ONTAP_X_STRICT': False,
                        'ONTAP_X': False, 'ONTAP_9_STRICT': True, 'ONTAP_9': True}, None),
    'is_asa_r2_system': (200, {'ASA_R2': True, 'ASA_LEGACY': False, 'ASA_ANY': True, 'ONTAP_AI_ML': False, 'ONTAP_X': True, 'ONTAP_9': False}, None),
    'lun_asa_r2': (200, {"records": [
        {
            "uuid": "2f030603-3daa-4e19-9888-f9c3ac9a9117",
            "name": "ansibleLUN",
            "os_type": "linux",
            "serial_number": "wOpku+Rjd-YL",
            "space": {
                "size": 5242880
            },
            "status": {
                "state": "online"
            }
        }]}, None),
    'lun_map_asa_r2': (200, {"records": [
        {
            "igroup": {
                "uuid": "1ad8544d-8cd1-91e0-9e1c-723478563412",
                "name": "igroup1",
            },
            "logical_unit_number": 1,
            "lun": {
                "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412",
                "name": "path",
            },
            "svm": {
                "name": "svm1",
                "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
            }
        }
    ]}, None),
    'lun': (200, {"records": [
        {
            "uuid": "2f030603-3daa-4e19-9888-f9c3ac9a9117",
            "name": "/vol/ansibleLUN_vol1/ansibleLUN",
            "os_type": "linux",
            "serial_number": "wOpku+Rjd-YL",
            "space": {
                "size": 5242880
            },
            "status": {
                "state": "online"
            }
        }]}, None),
    'lun_map': (200, {"records": [
        {
            "igroup": {
                "uuid": "1ad8544d-8cd1-91e0-9e1c-723478563412",
                "name": "igroup1",
            },
            "logical_unit_number": 1,
            "lun": {
                "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412",
                "name": "this/is/a/path",
            },
            "svm": {
                "name": "svm1",
                "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
            }
        }
    ]}, None)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'path': 'this/is/a/path',
    'initiator_group_name': 'igroup1',
    'vserver': 'svm1',
    'use_rest': 'always',
}


DEFAULT_ARGS_ASA_R2 = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'path': 'path',
    'initiator_group_name': 'igroup1',
    'vserver': 'svm1',
    'use_rest': 'always',
}


def test_get_lun_map_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/san/lun-maps', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_lun_map_rest() is None


def test_get_lun_map_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/san/lun-maps', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error getting lun_map this/is/a/path: calling: protocols/san/lun-maps: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_lun_map_rest, 'fail')['msg']


def test_get_lun_map_one_record():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_lun_map_rest() is not None


def test_get_lun_one_record():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['lun'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_lun_rest() is not None


def test_get_lun_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error getting lun this/is/a/path: calling: storage/luns: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_lun_rest, 'fail')['msg']


def test_create_lun_map():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['empty_records']),
        ('POST', 'protocols/san/lun-maps', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {})['changed']


def test_create_lun_map_with_lun_id():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['empty_records']),
        ('POST', 'protocols/san/lun-maps', SRR['empty_good'])
    ])
    module_args = {'lun_id': '1'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_lun_map_with_lun_id_idempotent():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['lun']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'lun_id': '1'})['changed'] is False


def test_create_lun_map_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'protocols/san/lun-maps', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error creating lun_map this/is/a/path: calling: protocols/san/lun-maps: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.create_lun_map_rest, 'fail')['msg']


def test_delete_lun_map():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map']),
        ('DELETE', 'protocols/san/lun-maps/1cd8a442-86d1-11e0-ae1c-123478563412/1ad8544d-8cd1-91e0-9e1c-723478563412',
         SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_lun_map_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map']),
    ])
    module_args = {'initiator_group_name': 'new name'}
    msg = 'Modification of lun_map not allowed'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, 'fail')['msg']


def test_delete_lun_map_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('DELETE', 'protocols/san/lun-maps/1cd8a442-86d1-11e0-ae1c-123478563412/1ad8544d-8cd1-91e0-9e1c-723478563412',
         SRR['generic_error'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    my_obj.parameters['state'] = 'absent'
    my_obj.igroup_uuid = '1ad8544d-8cd1-91e0-9e1c-723478563412'
    my_obj.lun_uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    msg = 'Error deleting lun_map this/is/a/path: calling: ' \
          'protocols/san/lun-maps/1cd8a442-86d1-11e0-ae1c-123478563412/1ad8544d-8cd1-91e0-9e1c-723478563412: got Expected error.'
    assert msg == expect_and_capture_ansible_exception(my_obj.delete_lun_map_rest, 'fail')['msg']


def test_get_lun_map_none_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'protocols/san/lun-maps', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_lun_map_rest() is None


def test_get_lun_map_error_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'protocols/san/lun-maps', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error getting lun_map this/is/a/path: calling: protocols/san/lun-maps: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_lun_map_rest, 'fail')['msg']


def test_get_lun_map_one_record_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_lun_map_rest() is not None


def test_get_lun_one_record_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/luns', SRR['lun'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_lun_rest() is not None


def test_get_lun_error_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/luns', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error getting lun this/is/a/path: calling: storage/luns: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_lun_rest, 'fail')['msg']


def test_create_lun_map_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['empty_records']),
        ('POST', 'protocols/san/lun-maps', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {})['changed']


def test_create_lun_map_with_lun_id_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['empty_records']),
        ('POST', 'protocols/san/lun-maps', SRR['empty_good'])
    ])
    module_args = {'lun_id': '1'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_lun_map_with_lun_id_idempotent_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/luns', SRR['lun']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'lun_id': '1'})['changed'] is False


def test_create_lun_map_error_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('POST', 'protocols/san/lun-maps', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error creating lun_map this/is/a/path: calling: protocols/san/lun-maps: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.create_lun_map_rest, 'fail')['msg']


def test_delete_lun_map_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map']),
        ('DELETE', 'protocols/san/lun-maps/1cd8a442-86d1-11e0-ae1c-123478563412/1ad8544d-8cd1-91e0-9e1c-723478563412',
         SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_lun_map_error_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map']),
    ])
    module_args = {'initiator_group_name': 'new name'}
    msg = 'Modification of lun_map not allowed'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS, module_args, 'fail')['msg']


def test_delete_lun_map_error_ontap_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_16_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapMode', SRR['is_ontap_system']),
        ('DELETE', 'protocols/san/lun-maps/1cd8a442-86d1-11e0-ae1c-123478563412/1ad8544d-8cd1-91e0-9e1c-723478563412',
         SRR['generic_error'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    my_obj.parameters['state'] = 'absent'
    my_obj.igroup_uuid = '1ad8544d-8cd1-91e0-9e1c-723478563412'
    my_obj.lun_uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    msg = 'Error deleting lun_map this/is/a/path: calling: ' \
          'protocols/san/lun-maps/1cd8a442-86d1-11e0-ae1c-123478563412/1ad8544d-8cd1-91e0-9e1c-723478563412: got Expected error.'
    assert msg == expect_and_capture_ansible_exception(my_obj.delete_lun_map_rest, 'fail')['msg']


def test_get_lun_map_none_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'protocols/san/lun-maps', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS_ASA_R2)
    my_obj = my_module()
    assert my_obj.get_lun_map_rest() is None


def test_get_lun_map_error_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'protocols/san/lun-maps', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS_ASA_R2)
    msg = 'Error getting lun_map path: calling: protocols/san/lun-maps: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_lun_map_rest, 'fail')['msg']


def test_get_lun_map_one_record_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map_asa_r2'])
    ])
    set_module_args(DEFAULT_ARGS_ASA_R2)
    my_obj = my_module()
    assert my_obj.get_lun_map_rest() is not None


def test_get_lun_one_record_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/luns', SRR['lun_asa_r2'])
    ])
    set_module_args(DEFAULT_ARGS_ASA_R2)
    my_obj = my_module()
    assert my_obj.get_lun_rest() is not None


def test_get_lun_error_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/luns', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS_ASA_R2)
    msg = 'Error getting lun path: calling: storage/luns: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_lun_rest, 'fail')['msg']


def test_create_lun_map_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['empty_records']),
        ('POST', 'protocols/san/lun-maps', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS_ASA_R2, {})['changed']


def test_create_lun_map_with_lun_id_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['empty_records']),
        ('POST', 'protocols/san/lun-maps', SRR['empty_good'])
    ])
    module_args = {'lun_id': '1'}
    assert create_and_apply(my_module, DEFAULT_ARGS_ASA_R2, module_args)['changed']


def test_create_lun_map_with_lun_id_idempotent_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/luns', SRR['lun_asa_r2']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map_asa_r2'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS_ASA_R2, {'lun_id': '1'})['changed'] is False


def test_create_lun_map_error_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('POST', 'protocols/san/lun-maps', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS_ASA_R2)
    msg = 'Error creating lun_map path: calling: protocols/san/lun-maps: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.create_lun_map_rest, 'fail')['msg']


def test_delete_lun_map_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map_asa_r2']),
        ('DELETE', 'protocols/san/lun-maps/1cd8a442-86d1-11e0-ae1c-123478563412/1ad8544d-8cd1-91e0-9e1c-723478563412',
         SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS_ASA_R2, module_args)['changed']


def test_modify_lun_map_error_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'protocols/san/lun-maps', SRR['lun_map_asa_r2']),
    ])
    module_args = {'initiator_group_name': 'new name'}
    msg = 'Modification of lun_map not allowed'
    assert msg in create_and_apply(my_module, DEFAULT_ARGS_ASA_R2, module_args, 'fail')['msg']


def test_delete_lun_map_error_asa_r2_system():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['is_asa_r2_system']),
        ('DELETE', 'protocols/san/lun-maps/1cd8a442-86d1-11e0-ae1c-123478563412/1ad8544d-8cd1-91e0-9e1c-723478563412',
         SRR['generic_error'])
    ])
    set_module_args(DEFAULT_ARGS_ASA_R2)
    my_obj = my_module()
    my_obj.parameters['state'] = 'absent'
    my_obj.igroup_uuid = '1ad8544d-8cd1-91e0-9e1c-723478563412'
    my_obj.lun_uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    msg = 'Error deleting lun_map path: calling: ' \
          'protocols/san/lun-maps/1cd8a442-86d1-11e0-ae1c-123478563412/1ad8544d-8cd1-91e0-9e1c-723478563412: got Expected error.'
    assert msg == expect_and_capture_ansible_exception(my_obj.delete_lun_map_rest, 'fail')['msg']


def test_error_get_asa_r2_rest():
    ''' Test error retrieving  '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_17_1']),
        ('GET', 'private/cli/debug/smdb/table/OntapPersonality', SRR['generic_error']),
    ])
    error = create_module(my_module, DEFAULT_ARGS_ASA_R2, fail=True)['msg']
    msg = "Failed while checking if the given host is an ASA r2 system or not"
    assert msg in error
