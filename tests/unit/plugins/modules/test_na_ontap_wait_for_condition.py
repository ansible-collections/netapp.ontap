# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    call_main, create_module, expect_and_capture_ansible_exception, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_wait_for_condition \
    import NetAppONTAPWFC as my_module, main as my_main


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def sp_image_update_progress_info(in_progress=True):
    return {
        'attributes': {
            'service-processor-image-update-progress-info': {
                'is-in-progress': 'true' if in_progress else 'false',
            }
        }
    }


def sp_info(version):
    return {
        'attributes': {
            'service-processor--info': {
                'firmware-version': version,
            }
        }
    }


ZRR = zapi_responses({
    'sp_info_3_09': build_zapi_response(sp_info('3.09'), 1),
    'sp_info_3_10': build_zapi_response(sp_info('3.10'), 1),
    'sp_image_update_progress_info_in_progress': build_zapi_response(sp_image_update_progress_info(True), 1),
    'sp_image_update_progress_info_idle': build_zapi_response(sp_image_update_progress_info(False), 1),
})


SRR = rest_responses({
    'one_record_home_node': (200, {'records': [
        {'name': 'node2_abc_if',
         'uuid': '54321',
         'enabled': True,
         'location': {'home_port': {'name': 'e0c'}, 'home_node': {'name': 'node2'}, 'node': {'name': 'node2'}, 'port': {'name': 'e0c'}}
         }]}, None),
    'one_record_vserver': (200, {'records': [{
        'name': 'abc_if',
        'uuid': '54321',
        'svm': {'name': 'vserver', 'uuid': 'svm_uuid'},
        'data_protocol': ['nfs'],
        'enabled': True,
        'ip': {'address': '10.11.12.13', 'netmask': '255.192.0.0'},
        'location': {
            'home_port': {'name': 'e0c'},
            'home_node': {'name': 'node2'},
            'node': {'name': 'node2'},
            'port': {'name': 'e0c'},
            'auto_revert': True,
            'failover': True
        },
        'service_policy': {'name': 'data-mgmt'}
    }]}, None),
    'two_records': (200, {'records': [{'name': 'node2_abc_if'}, {'name': 'node2_abc_if'}]}, None),
    'error_precluster': (500, None, {'message': 'are available in precluster.'}),
    'cluster_identity': (200, {'location': 'Oz', 'name': 'abc'}, None),
    'node_309_online': (200, {'records': [
        {'service_processor': {'firmware_version': '3.09', 'state': 'online'}}
    ]}, None),
    'node_309_updating': (200, {'records': [
        {'service_processor': {'firmware_version': '3.09', 'state': 'updating'}}
    ]}, None),
    'node_310_online': (200, {'records': [
        {'service_processor': {'firmware_version': '3.10', 'state': 'online'}}
    ]}, None),
    'snapmirror_relationship': (200, {'records': [
        {'state': 'snapmirrored'}
    ]}, None),
}, False)

DEFAULT_ARGS = {
    'hostname': '10.10.10.10',
    'username': 'admin',
    'password': 'password',
    'attributes': {
        'node': 'node1',
        'expected_version': '3.10'
    }
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    module_args = {
        'use_rest': 'never'
    }
    error = create_module(my_module, module_args, fail=True)['msg']
    assert 'missing required arguments:' in error
    assert 'name' in error
    assert 'conditions' in error


@patch('time.sleep')
def test_rest_successful_wait_for_sp_upgrade(dont_sleep):
    ''' Test successful sp_upgrade check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster/nodes', SRR['node_309_online']),
        ('GET', 'cluster/nodes', SRR['node_309_online']),
        ('GET', 'cluster/nodes', SRR['node_309_updating']),
    ])
    module_args = {
        'use_rest': 'always',
        'name': 'sp_upgrade',
        'conditions': 'is_in_progress',
    }
    results = call_main(my_main, DEFAULT_ARGS, module_args)
    assert results['msg'] == 'matched condition: is_in_progress'
    assert results['states'] == 'online*2,updating'
    assert results['last_state'] == 'updating'


@patch('time.sleep')
def test_rest_successful_wait_for_snapmirror_relationship(dont_sleep):
    ''' Test successful snapmirror_relationship check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'snapmirror/relationships', SRR['snapmirror_relationship']),
    ])
    module_args = {
        'use_rest': 'always',
        'name': 'snapmirror_relationship',
        'conditions': 'transfer_state',
        'attributes': {
            'destination_path': 'path',
            'expected_transfer_state': 'idle'
        }
    }
    results = call_main(my_main, DEFAULT_ARGS, module_args)
    assert results['msg'] == 'matched condition: transfer_state'
    # these are generated from dictionaries keys, and sequence is not guaranteed with python 3.5
    assert results['states'] in ['snapmirrored,idle', 'idle']
    assert results['last_state'] == 'idle'


@patch('time.sleep')
def test_rest_successful_wait_for_sp_version(dont_sleep):
    ''' Test successful sp_version check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster/nodes', SRR['node_309_online']),
        ('GET', 'cluster/nodes', SRR['node_309_online']),
        ('GET', 'cluster/nodes', SRR['node_309_updating']),
        ('GET', 'cluster/nodes', SRR['generic_error']),
        ('GET', 'cluster/nodes', SRR['zero_records']),
        ('GET', 'cluster/nodes', SRR['node_309_updating']),
        ('GET', 'cluster/nodes', SRR['node_310_online']),
    ])
    module_args = {
        'use_rest': 'always',
        'name': 'sp_version',
        'conditions': 'firmware_version',
    }
    results = call_main(my_main, DEFAULT_ARGS, module_args)
    assert results['msg'] == 'matched condition: firmware_version'
    assert results['states'] == '3.09*4,3.10'
    assert results['last_state'] == '3.10'


@patch('time.sleep')
def test_rest_successful_wait_for_sp_version_not_matched(dont_sleep):
    ''' Test successful sp_version check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster/nodes', SRR['node_309_online']),
        ('GET', 'cluster/nodes', SRR['node_309_online']),
        ('GET', 'cluster/nodes', SRR['node_309_updating']),
        ('GET', 'cluster/nodes', SRR['generic_error']),
        ('GET', 'cluster/nodes', SRR['zero_records']),
        ('GET', 'cluster/nodes', SRR['node_309_updating']),
        ('GET', 'cluster/nodes', SRR['node_310_online']),
    ])
    module_args = {
        'use_rest': 'always',
        'name': 'sp_version',
        'conditions': ['firmware_version'],
        'state': 'absent',
        'attributes': {
            'node': 'node1',
            'expected_version': '3.09'
        }
    }
    results = call_main(my_main, DEFAULT_ARGS, module_args)
    assert results['msg'] == 'conditions not matched'
    assert results['states'] == '3.09*4,3.10'
    assert results['last_state'] == '3.10'


@patch('time.sleep')
def test_rest_negative_wait_for_sp_version_error(dont_sleep):
    ''' Test negative sp_version check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster/nodes', SRR['zero_records']),
        ('GET', 'cluster/nodes', SRR['zero_records']),
        ('GET', 'cluster/nodes', SRR['zero_records']),
    ])
    module_args = {
        'use_rest': 'always',
        'name': 'sp_version',
        'conditions': 'firmware_version',
    }
    error = 'Error: no record for node:'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_rest_negative_wait_for_sp_version_timeout(dont_sleep):
    ''' Test negative sp_version check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster/nodes', SRR['node_309_online']),
        ('GET', 'cluster/nodes', SRR['node_309_online']),
        ('GET', 'cluster/nodes', SRR['node_309_online']),
        ('GET', 'cluster/nodes', SRR['node_309_online']),
    ])
    module_args = {
        'use_rest': 'always',
        'name': 'sp_version',
        'conditions': 'firmware_version',
        'timeout': 40,
        'polling_interval': 12,
    }
    error = 'Error: timeout waiting for condition: firmware_version==3.10.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_zapi_successful_wait_for_sp_upgrade(dont_sleep):
    ''' Test successful sp_upgrade check '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'service-processor-image-update-progress-get', ZRR['sp_image_update_progress_info_idle']),
        ('ZAPI', 'service-processor-image-update-progress-get', ZRR['sp_image_update_progress_info_idle']),
        ('ZAPI', 'service-processor-image-update-progress-get', ZRR['sp_image_update_progress_info_in_progress']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'sp_upgrade',
        'conditions': 'is_in_progress',
    }
    results = call_main(my_main, DEFAULT_ARGS, module_args)
    assert results['msg'] == 'matched condition: is_in_progress'
    assert results['states'] == 'false*2,true'
    assert results['last_state'] == 'true'


@patch('time.sleep')
def test_zapi_successful_wait_for_sp_version(dont_sleep):
    ''' Test successful sp_version check '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'service-processor-get', ZRR['sp_info_3_09']),
        ('ZAPI', 'service-processor-get', ZRR['error']),
        ('ZAPI', 'service-processor-get', ZRR['sp_info_3_09']),
        ('ZAPI', 'service-processor-get', ZRR['sp_info_3_10']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'sp_version',
        'conditions': 'firmware_version',
    }
    results = call_main(my_main, DEFAULT_ARGS, module_args)
    assert results['msg'] == 'matched condition: firmware_version'
    assert results['states'] == '3.09*2,3.10'
    assert results['last_state'] == '3.10'


def test_zapi_negative_wait_for_snapmirror_relationship_error():
    ''' Test negative snapmirror_relationship check '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'snapmirror_relationship',
        'conditions': 'state',
        'attributes': {
            'destination_path': 'path',
            'expected_state': 'snapmirrored'
        }
    }
    error = 'Error: event snapmirror_relationship is not supported with ZAPI.  It requires REST.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_zapi_negative_wait_for_sp_version_error(dont_sleep):
    ''' Test negative sp_version check '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'service-processor-get', ZRR['no_records']),
        ('ZAPI', 'service-processor-get', ZRR['no_records']),
        ('ZAPI', 'service-processor-get', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'sp_version',
        'conditions': 'firmware_version',
    }
    error = 'Error: Cannot find element with name: firmware-version in results:'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_zapi_negative_wait_for_sp_version_timeout(dont_sleep):
    ''' Test negative sp_version check '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'service-processor-get', ZRR['sp_info_3_09']),
        ('ZAPI', 'service-processor-get', ZRR['error']),
        ('ZAPI', 'service-processor-get', ZRR['sp_info_3_09']),
        ('ZAPI', 'service-processor-get', ZRR['sp_info_3_09']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'sp_version',
        'conditions': 'firmware_version',
        'timeout': 30,
        'polling_interval': 9,
    }
    error = 'Error: timeout waiting for condition: firmware_version==3.10.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_invalid_name():
    ''' Test that name is valid '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'some_name',
        'conditions': 'firmware_version',
    }
    error = 'value of name must be one of:'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['use_rest'] = 'always'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_negative_validate_resource():
    ''' KeyError on unexpected name '''
    module_args = {
        'use_rest': 'never',
        'name': 'sp_version',
        'conditions': 'firmware_version',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert 'some_name' in expect_and_capture_ansible_exception(my_obj.validate_resource, KeyError, 'some_name')
    module_args['use_rest'] = 'always'
    assert 'some_name' in expect_and_capture_ansible_exception(my_obj.validate_resource, KeyError, 'some_name')


def test_negative_build_zapi():
    ''' KeyError on unexpected name '''
    module_args = {
        'use_rest': 'never',
        'name': 'sp_version',
        'conditions': 'firmware_version',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert 'some_name' in expect_and_capture_ansible_exception(my_obj.build_zapi, KeyError, 'some_name')


def test_negative_build_rest_api_kwargs():
    ''' KeyError on unexpected name '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'name': 'sp_version',
        'conditions': 'firmware_version',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert 'some_name' in expect_and_capture_ansible_exception(my_obj.build_rest_api_kwargs, KeyError, 'some_name')


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_wait_for_condition.NetAppONTAPWFC.get_record_rest')
@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_wait_for_condition.NetAppONTAPWFC.extract_condition')
def test_get_condition_other(mock_extract_condition, mock_get_record_rest):
    ''' condition not found, non expected condition ignored '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'name': 'sp_version',
        'conditions': 'firmware_version',
        'state': 'absent'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    condition = 'other_condition'
    mock_get_record_rest.return_value = None, None
    mock_extract_condition.side_effect = [
        (None, None),
        (condition, None),
    ]
    assert my_obj.get_condition('name', 'dummy') == ('conditions not matched', None)
    assert my_obj.get_condition('name', 'dummy') == ('conditions not matched: found other condition: %s' % condition, None)


def test_invalid_condition():
    ''' Test that condition is valid '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'sp_upgrade',
        'conditions': [
            'firmware_version',
            'some_condition'
        ]
    }
    error = 'firmware_version is not valid for resource name: sp_upgrade'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['use_rest'] = 'always'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


# def test_invalid_attributes():
def test_missing_attribute():
    ''' Test that required attributes are present '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'never',
        'name': 'sp_version',
        'conditions': [
            'firmware_version',
        ]
    }
    args = dict(DEFAULT_ARGS)
    del args['attributes']
    error = 'name is sp_version but all of the following are missing: attributes'
    assert error in call_main(my_main, args, module_args, fail=True)['msg']
    module_args['use_rest'] = 'always'
    assert error in call_main(my_main, args, module_args, fail=True)['msg']
    module_args['use_rest'] = 'never'
    args['attributes'] = {'node': 'node1'}
    error = 'Error: attributes: expected_version is required for resource name: sp_version'
    assert error in call_main(my_main, args, module_args, fail=True)['msg']
    module_args['use_rest'] = 'always'
    assert error in call_main(my_main, args, module_args, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_negative_missing_netapp_lib(mock_netapp_lib):
    ''' create cluster '''
    module_args = {
        'use_rest': 'never',
        'name': 'sp_version',
        'conditions': 'firmware_version',
    }
    mock_netapp_lib.return_value = False
    error = "the python NetApp-Lib module is required"
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
