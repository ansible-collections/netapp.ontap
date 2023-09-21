# (c) 2022-2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_lun \
    import NetAppOntapLUN as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'one_lun': (200, {
        "records": [
            {
                "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412",
                "qos_policy": {
                    "name": "qos1",
                    "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
                },
                "os_type": "aix",
                "enabled": True,
                "location": {
                    "volume": {
                        "name": "volume1",
                        "uuid": "028baa66-41bd-11e9-81d5-00a0986138f7"
                    },
                    "qtree": {
                        "name": "qtree1",
                        "id": 1,
                    },
                },
                "name": "/vol/volume1/qtree1/lun1",
                "space": {
                    "scsi_thin_provisioning_support_enabled": True,
                    "guarantee": {
                        "requested": True,
                    },
                    "size": 1073741824
                },
                "lun_maps": [
                    {
                        "igroup": {
                            "name": "igroup1",
                            "uuid": "4ea7a442-86d1-11e0-ae1c-123478563412"
                        },
                        "logical_unit_number": 0,
                    }
                ],
                "comment": "string",
                "svm": {
                    "name": "svm1",
                    "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
                },
            }
        ],
    }, None),
    'two_luns': (200, {
        "records": [
            {
                "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412",
                "qos_policy": {
                    "name": "qos1",
                    "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
                },
                "os_type": "aix",
                "enabled": True,
                "location": {
                    "volume": {
                        "name": "volume1",
                        "uuid": "028baa66-41bd-11e9-81d5-00a0986138f7"
                    },
                    "qtree": {
                        "name": "qtree1",
                        "id": 1,
                    },
                },
                "name": "/vol/volume1/qtree1/lun1",
                "space": {
                    "scsi_thin_provisioning_support_enabled": True,
                    "guarantee": {
                        "requested": True,
                    },
                    "size": 1073741824
                },
                "lun_maps": [
                    {
                        "igroup": {
                            "name": "igroup1",
                            "uuid": "4ea7a442-86d1-11e0-ae1c-123478563412"
                        },
                        "logical_unit_number": 0,
                    }
                ],
                "comment": "string",
                "svm": {
                    "name": "svm1",
                    "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
                },
            },
            {
                "uuid": "1cd8a442-86d1-11e0-ae1c-123478563413",
                "qos_policy": {
                    "name": "qos2",
                    "uuid": "1cd8a442-86d1-11e0-ae1c-123478563413"
                },
                "os_type": "aix",
                "enabled": True,
                "location": {
                    "volume": {
                        "name": "volume2",
                        "uuid": "028baa66-41bd-11e9-81d5-00a0986138f3"
                    },
                    "qtree": {
                        "name": "qtree1",
                        "id": 1,
                    },
                },
                "name": "/vol/volume1/qtree1/lun2",
                "space": {
                    "scsi_thin_provisioning_support_enabled": True,
                    "guarantee": {
                        "requested": True,
                    },
                    "size": 1073741824
                },
                "lun_maps": [
                    {
                        "igroup": {
                            "name": "igroup2",
                            "uuid": "4ea7a442-86d1-11e0-ae1c-123478563413"
                        },
                        "logical_unit_number": 0,
                    }
                ],
                "comment": "string",
                "svm": {
                    "name": "svm1",
                    "uuid": "02c9e252-41be-11e9-81d5-00a0986138f3"
                },
            }
        ],
    }, None),
    'error_same_size': (400, None, 'New LUN size is the same as the old LUN size - this mau happen ...')
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': '/vol/volume1/qtree1/lun1',
    'flexvol_name': 'volume1',
    'vserver': 'svm1',
    'use_rest': 'always',
}

DEFAULT_ARGS_NO_VOL = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': '/vol/volume1/qtree1/lun1',
    'vserver': 'svm1',
    'use_rest': 'always',
}

DEFAULT_ARGS_MIN = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'svm1',
    'use_rest': 'always',
}


def test_get_lun_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['empty_records'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    assert my_obj.get_luns_rest() is None


def test_get_lun_one():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['one_lun'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    get_results = my_obj.get_luns_rest()
    assert len(get_results) == 1
    assert get_results[0]['name'] == '/vol/volume1/qtree1/lun1'


def test_get_lun_one_no_path():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['one_lun'])
    ])
    module_args = {
        'name': 'lun1',
        'flexvol_name': 'volume1',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS_MIN, module_args)
    get_results = my_obj.get_luns_rest()
    assert len(get_results) == 1
    assert get_results[0]['name'] == '/vol/volume1/qtree1/lun1'


def test_get_lun_more():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['two_luns'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    get_results = my_obj.get_luns_rest()
    assert len(get_results) == 2
    assert get_results[0]['name'] == '/vol/volume1/qtree1/lun1'
    assert get_results[1]['name'] == '/vol/volume1/qtree1/lun2'


def test_error_get_lun_with_flexvol():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.get_luns_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert "Error getting LUN's for flexvol volume1: calling: storage/luns: got Expected error." == error


def test_error_get_lun_with_lun_path():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['lun_path'] = '/vol/volume1/qtree1/lun1'
    my_obj.parameters.pop('flexvol_name')

    error = expect_and_capture_ansible_exception(my_obj.get_luns_rest, 'fail', '/vol/volume1/qtree1/lun1')['msg']
    print('Info: %s' % error)
    assert "Error getting lun_path /vol/volume1/qtree1/lun1: calling: storage/luns: got Expected error." == error


def test_successfully_create_lun():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('POST', 'storage/luns', SRR['one_lun']),
    ])
    module_args = {
        'size': 1073741824,
        'size_unit': 'bytes',
        'os_type': 'linux',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successfully_create_lun_without_path():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('POST', 'storage/luns', SRR['one_lun']),
    ])
    module_args = {
        'size': 1073741824,
        'size_unit': 'bytes',
        'os_type': 'linux',
        'flexvol_name': 'volume1',
        'name': 'lun'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_create_lun_missing_os_type():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['empty_records']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['size'] = 1073741824
    my_obj.parameters['size_unit'] = 'bytes'
    error = expect_and_capture_ansible_exception(my_obj.apply, 'fail')['msg']
    print('Info: %s' % error)
    assert "The os_type parameter is required for creating a LUN with REST." == error


def test_error_create_lun_missing_size():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['empty_records']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['os_type'] = 'linux'
    error = expect_and_capture_ansible_exception(my_obj.apply, 'fail')['msg']
    print('Info: %s' % error)
    assert "size is a required parameter for create." == error


def test_error_create_lun_missing_name():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        # Not sure why test_error_create_lun_missing_os_type require this... but this test dosn't. they should follow the
        # same path (unless we don't do a get with flexvol_name isn't set)
        # ('GET', 'storage/luns', SRR['empty_records']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters.pop('flexvol_name')
    my_obj.parameters['os_type'] = 'linux'
    my_obj.parameters['size'] = 1073741824
    my_obj.parameters['size_unit'] = 'bytes'
    error = expect_and_capture_ansible_exception(my_obj.apply, 'fail')['msg']
    print('Info: %s' % error)
    assert "The flexvol_name parameter is required for creating a LUN." == error


def test_successfully_create_lun_all_options():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('POST', 'storage/luns', SRR['one_lun']),
    ])
    module_args = {
        'size': '1073741824',
        'os_type': 'linux',
        'space_reserve': True,
        'space_allocation': True,
        'comment': 'carchi8py was here',
        'qos_policy_group': 'qos_policy_group_1',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_create_lun():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'storage/luns', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['size'] = 1073741824
    my_obj.parameters['size_unit'] = 'bytes'
    my_obj.parameters['os_type'] = 'linux'

    error = expect_and_capture_ansible_exception(my_obj.create_lun_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert "Error creating LUN /vol/volume1/qtree1/lun1: calling: storage/luns: got Expected error." == error


def test_successfully_delete_lun():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['one_lun']),
        ('DELETE', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['empty_records']),
    ])
    module_args = {
        'size': 1073741824,
        'size_unit': 'bytes',
        'os_type': 'linux',
        'state': 'absent',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_delete_lun():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('DELETE', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['size'] = 1073741824
    my_obj.parameters['size_unit'] = 'bytes'
    my_obj.parameters['os_type'] = 'linux'
    my_obj.parameters['os_type'] = 'absent'
    my_obj.uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'

    error = expect_and_capture_ansible_exception(my_obj.delete_lun_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert "Error deleting LUN /vol/volume1/qtree1/lun1: calling: storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412: got Expected error." == error


def test_error_delete_lun_missing_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['size'] = 1073741824
    my_obj.parameters['size_unit'] = 'bytes'
    my_obj.parameters['os_type'] = 'linux'
    my_obj.parameters['os_type'] = 'absent'

    error = expect_and_capture_ansible_exception(my_obj.delete_lun_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert "Error deleting LUN /vol/volume1/qtree1/lun1: UUID not found" == error


def test_successfully_rename_lun():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('GET', 'storage/luns', SRR['one_lun']),
        ('PATCH', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['empty_records']),
    ])
    module_args = {
        'name': '/vol/volume1/qtree12/lun1',
        'from_name': '/vol/volume1/qtree1/lun1',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_rename_lun():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['name'] = '/vol/volume1/qtree12/lun1'
    my_obj.parameters['from_name'] = '/vol/volume1/qtree1/lun1'
    my_obj.uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    error = expect_and_capture_ansible_exception(my_obj.rename_lun_rest, 'fail', '/vol/volume1/qtree12/lun1')['msg']
    print('Info: %s' % error)
    assert "Error renaming LUN /vol/volume1/qtree12/lun1: calling: storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412: got Expected error." == error


def test_error_rename_lun_missing_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['name'] = '/vol/volume1/qtree12/lun1'
    my_obj.parameters['from_name'] = '/vol/volume1/qtree1/lun1'
    error = expect_and_capture_ansible_exception(my_obj.rename_lun_rest, 'fail', '/vol/volume1/qtree12/lun1')['msg']
    print('Info: %s' % error)
    assert "Error renaming LUN /vol/volume1/qtree12/lun1: UUID not found" == error


def test_successfully_resize_lun():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['one_lun']),
        ('PATCH', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['empty_records']),
    ])
    module_args = {
        'size': 2147483648,
        'size_unit': 'bytes',
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_resize_lun():
    ''' assert that
        resize fails on error, except for a same size issue because of rounding errors
        resize correctly return True/False to indicate that the size was changed or not
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['generic_error']),
        ('PATCH', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['error_same_size']),
        ('PATCH', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['success'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['size'] = 2147483648
    my_obj.parameters['size_unit'] = 'bytes'
    my_obj.uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    error = expect_and_capture_ansible_exception(my_obj.resize_lun_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert "Error resizing LUN /vol/volume1/qtree1/lun1: calling: storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412: got Expected error." == error
    assert not my_obj.resize_lun_rest()
    assert my_obj.resize_lun_rest()


def test_error_resize_lun_missing_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['size'] = 2147483648
    my_obj.parameters['size_unit'] = 'bytes'
    error = expect_and_capture_ansible_exception(my_obj.resize_lun_rest, 'fail')['msg']
    print('Info: %s' % error)
    assert "Error resizing LUN /vol/volume1/qtree1/lun1: UUID not found" == error


def test_successfully_modify_lun():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/luns', SRR['one_lun']),
        ('PATCH', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['empty_records']),
    ])
    module_args = {
        'comment': 'carchi8py was here',
        'qos_policy_group': 'qos_policy_group_12',
        'space_reserve': False,
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_successfully_modify_lun_9_10():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/luns', SRR['one_lun']),
        ('PATCH', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['empty_records']),
    ])
    module_args = {
        'comment': 'carchi8py was here',
        'qos_policy_group': 'qos_policy_group_12',
        'space_allocation': False,
        'space_reserve': False,
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_modify_lun():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'carchi8py was here'
    my_obj.parameters['qos_policy_group'] = 'qos_policy_group_12'
    my_obj.parameters['space_allocation'] = False
    my_obj.parameters['space_reserve'] = False
    my_obj.uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    modify = {'comment': 'carchi8py was here', 'qos_policy_group': 'qos_policy_group_12', 'space_reserve': False, 'space_allocation': False}
    error = expect_and_capture_ansible_exception(my_obj.modify_lun_rest, 'fail', modify)['msg']
    print('Info: %s' % error)
    assert "Error modifying LUN /vol/volume1/qtree1/lun1: calling: storage/luns/1cd8a442-86d1-11e0-ae1c-123478563412: got Expected error." == error


def test_error_modify_lun_missing_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'carchi8py was here'
    my_obj.parameters['qos_policy_group'] = 'qos_policy_group_12'
    my_obj.parameters['space_allocation'] = False
    my_obj.parameters['space_reserve'] = False
    modify = {'comment': 'carchi8py was here', 'qos_policy_group': 'qos_policy_group_12', 'space_reserve': False, 'space_allocation': False}
    error = expect_and_capture_ansible_exception(my_obj.modify_lun_rest, 'fail', modify)['msg']
    print('Info: %s' % error)
    assert "Error modifying LUN /vol/volume1/qtree1/lun1: UUID not found" == error


def test_error_modify_lun_extra_option():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'carchi8py was here'
    my_obj.parameters['qos_policy_group'] = 'qos_policy_group_12'
    my_obj.parameters['space_allocation'] = False
    my_obj.parameters['space_reserve'] = False
    my_obj.uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    modify = {'comment': 'carchi8py was here', 'qos_policy_group': 'qos_policy_group_12', 'space_reserve': False, 'space_allocation': False, 'fake': 'fake'}
    error = expect_and_capture_ansible_exception(my_obj.modify_lun_rest, 'fail', modify)['msg']
    print('Info: %s' % error)
    assert "Error modifying LUN /vol/volume1/qtree1/lun1: Unknown parameters: {'fake': 'fake'}" == error
