# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_volume_autosize '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import call_main, patch_ansible, create_module, create_and_apply
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_autosize \
    import NetAppOntapVolumeAutosize as autosize_module, main as my_main                # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


# REST API canned responses when mocking send_request
SRR = rest_responses({
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'get_uuid': (200, {'records': [{'uuid': 'testuuid'}]}, None),
    'get_autosize': (200,
                     {'uuid': 'testuuid',
                      'name': 'testname',
                      'autosize': {"maximum": 10737418240,
                                   "minimum": 22020096,
                                   "grow_threshold": 99,
                                   "shrink_threshold": 40,
                                   "mode": "grow"
                                   }
                      }, None),
    'get_autosize_empty': (200, {
        'uuid': 'testuuid',
        'name': 'testname',
        'autosize': {}
    }, None)
})


MOCK_AUTOSIZE = {
    'grow_threshold_percent': 99,
    'maximum_size': '10g',
    'minimum_size': '21m',
    'increment_size': '10m',
    'mode': 'grow',
    'shrink_threshold_percent': 40,
    'vserver': 'test_vserver',
    'volume': 'test_volume'
}


autosize_info = {
    'grow-threshold-percent': MOCK_AUTOSIZE['grow_threshold_percent'],
    'maximum-size': '10485760',
    'minimum-size': '21504',
    'increment-size': '10240',
    'mode': MOCK_AUTOSIZE['mode'],
    'shrink-threshold-percent': MOCK_AUTOSIZE['shrink_threshold_percent']
}


ZRR = zapi_responses({
    'get_autosize': build_zapi_response(autosize_info)
})


DEFAULT_ARGS = {
    'vserver': MOCK_AUTOSIZE['vserver'],
    'volume': MOCK_AUTOSIZE['volume'],
    'grow_threshold_percent': MOCK_AUTOSIZE['grow_threshold_percent'],
    'maximum_size': MOCK_AUTOSIZE['maximum_size'],
    'minimum_size': MOCK_AUTOSIZE['minimum_size'],
    'mode': MOCK_AUTOSIZE['mode'],
    'shrink_threshold_percent': MOCK_AUTOSIZE['shrink_threshold_percent'],
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!'
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    args = dict(DEFAULT_ARGS)
    args.pop('vserver')
    error = 'missing required arguments: vserver'
    assert create_module(autosize_module, args, fail=True)['msg'] == error


def test_idempotent_modify():
    register_responses([
        ('ZAPI', 'volume-autosize-get', ZRR['get_autosize']),
    ])
    module_args = {
        'use_rest': 'never'
    }
    assert not create_and_apply(autosize_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify():
    register_responses([
        ('ZAPI', 'volume-autosize-get', ZRR['get_autosize']),
        ('ZAPI', 'volume-autosize-set', ZRR['success']),
    ])
    module_args = {
        'increment_size': MOCK_AUTOSIZE['increment_size'],
        'maximum_size': '11g',
        'use_rest': 'never'
    }
    assert create_and_apply(autosize_module, DEFAULT_ARGS, module_args)['changed']


def test_zapi__create_get_volume_return_no_data():
    module_args = {
        'use_rest': 'never'
    }
    my_obj = create_module(autosize_module, DEFAULT_ARGS, module_args)
    assert my_obj._create_get_volume_return(build_zapi_response({'unsupported_key': 'value'})[0]) is None


def test_error_get():
    register_responses([
        ('ZAPI', 'volume-autosize-get', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never'
    }
    error = 'Error fetching volume autosize info for test_volume: NetApp API failed. Reason - 12345:synthetic error for UT purpose.'
    assert create_and_apply(autosize_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_error_modify():
    register_responses([
        ('ZAPI', 'volume-autosize-get', ZRR['get_autosize']),
        ('ZAPI', 'volume-autosize-set', ZRR['error']),
    ])
    module_args = {
        'increment_size': MOCK_AUTOSIZE['increment_size'],
        'maximum_size': '11g',
        'use_rest': 'never'
    }
    error = 'Error modifying volume autosize for test_volume: NetApp API failed. Reason - 12345:synthetic error for UT purpose.'
    assert create_and_apply(autosize_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_successful_reset():
    register_responses([
        ('ZAPI', 'volume-autosize-get', ZRR['get_autosize']),
        ('ZAPI', 'volume-autosize-set', ZRR['success']),
    ])
    args = dict(DEFAULT_ARGS)
    for arg in ('maximum_size', 'minimum_size', 'grow_threshold_percent', 'shrink_threshold_percent', 'mode'):
        # remove args that are eclusive with reset
        args.pop(arg)
    module_args = {
        'reset': True,
        'use_rest': 'never'
    }
    assert create_and_apply(autosize_module, args, module_args)['changed']


def test_rest_error_volume_not_found():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['zero_records']),
    ])
    error = 'Error fetching volume autosize info for test_volume: volume not found for vserver test_vserver.'
    assert create_and_apply(autosize_module, DEFAULT_ARGS, fail=True)['msg'] == error


def test_rest_error_get():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['generic_error']),
    ])
    module_args = {
        'maximum_size': '11g'
    }
    error = 'Error fetching volume autosize info for test_volume: calling: storage/volumes: got Expected error.'
    assert create_and_apply(autosize_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_rest_error_patch():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_autosize']),
        ('PATCH', 'storage/volumes/testuuid', SRR['generic_error']),
    ])
    module_args = {
        'maximum_size': '11g'
    }
    error = 'Error modifying volume autosize for test_volume: calling: storage/volumes/testuuid: got Expected error.'
    assert create_and_apply(autosize_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_rest_successful_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_autosize']),
        ('PATCH', 'storage/volumes/testuuid', SRR['success']),
    ])
    module_args = {
        'maximum_size': '11g'
    }
    assert create_and_apply(autosize_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_idempotent_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_autosize']),
    ])
    assert not create_and_apply(autosize_module, DEFAULT_ARGS)['changed']


def test_rest_idempotent_modify_no_attributes():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_autosize_empty']),
    ])
    module_args = {
        'maximum_size': '11g'
    }
    assert not create_and_apply(autosize_module, DEFAULT_ARGS)['changed']


def test_rest__create_get_volume_return_no_data():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(autosize_module, DEFAULT_ARGS)
    assert my_obj._create_get_volume_return({'unsupported_key': 'value'}) == {'uuid': None}


def test_rest_modify_no_data():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(autosize_module, DEFAULT_ARGS)
    # remove all attributes
    for arg in ('maximum_size', 'minimum_size', 'grow_threshold_percent', 'shrink_threshold_percent', 'mode'):
        my_obj.parameters.pop(arg)
    assert my_obj.modify_volume_autosize('uuid') is None


def test_rest_convert_to_bytes():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(autosize_module, DEFAULT_ARGS)

    module_args = {
        'minimum_size': '11k'
    }
    assert my_obj.convert_to_byte('minimum_size', module_args) == 11 * 1024

    module_args = {
        'minimum_size': '11g'
    }
    assert my_obj.convert_to_byte('minimum_size', module_args) == 11 * 1024 * 1024 * 1024


def test_rest_convert_to_kb():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    my_obj = create_module(autosize_module, DEFAULT_ARGS)

    module_args = {
        'minimum_size': '11k'
    }
    assert my_obj.convert_to_kb('minimum_size', module_args) == 11

    module_args = {
        'minimum_size': '11g'
    }
    assert my_obj.convert_to_kb('minimum_size', module_args) == 11 * 1024 * 1024


def test_rest_invalid_values():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_autosize']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_autosize']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_autosize']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_autosize'])
    ])
    module_args = {
        'minimum_size': '11kb'
    }
    error = 'minimum_size must end with a k, m, g or t, found b in 11kb.'
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == error

    module_args = {
        'minimum_size': '11kk'
    }
    error = 'minimum_size must start with a number, found 11k in 11kk.'
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == error

    module_args = {
        'minimum_size': ''
    }
    error = "minimum_size must start with a number, and must end with a k, m, g or t, found ''."
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == error

    module_args = {
        'minimum_size': 10
    }
    error = 'minimum_size must end with a k, m, g or t, found 0 in 10.'
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_rest_unsupported_parameters():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'storage/volumes', SRR['get_autosize'])
    ])
    module_args = {
        'increment_size': '11k'
    }
    error = 'Rest API does not support increment size, please switch to ZAPI'
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == error

    # reset is not supported - when set to True
    module_args = {
        'reset': True
    }
    args = dict(DEFAULT_ARGS)
    for arg in ('maximum_size', 'minimum_size', 'grow_threshold_percent', 'shrink_threshold_percent', 'mode'):
        # remove args that are eclusive with reset
        args.pop(arg)
    error = 'Rest API does not support reset, please switch to ZAPI'
    assert call_main(my_main, args, module_args, fail=True)['msg'] == error

    # reset is ignored when False
    module_args = {
        'reset': False
    }
    assert not call_main(my_main, args, module_args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_missing_netapp_lib(mock_has_netapp_lib):
    module_args = {
        'use_rest': 'never',
    }
    mock_has_netapp_lib.return_value = False
    msg = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert msg == create_module(autosize_module, DEFAULT_ARGS, module_args, fail=True)['msg']
