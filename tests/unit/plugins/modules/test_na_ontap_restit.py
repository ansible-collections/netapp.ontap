# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_cluster '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_restit \
    import NetAppONTAPRestAPI as my_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


def exit_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over exit_json; package return data into an exception"""
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


# using pytest natively, without unittest.TestCase
@pytest.fixture
def patch_ansible():
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json) as mocks:
        yield mocks


SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy_9_7_0')), None),
    'is_rest_95': (200, dict(version=dict(generation=9, major=5, minor=0, full='dummy_9_5_0')), None),
    'is_rest_96': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy_9_6_0')), None),
    'is_rest_97': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy_9_7_0')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': ({}, None, None),
    'zero_record': (200, {'records': []}, None),
    'job_id_record': (
        200, {
            'job': {
                'uuid': '94b6e6a7-d426-11eb-ac81-00505690980f',
                '_links': {'self': {'href': '/api/cluster/jobs/94b6e6a7-d426-11eb-ac81-00505690980f'}}},
            'cli_output': ' Use the "job show -id 2379" command to view the status of this operation.'}, None),
    'job_response_record': (
        200, {
            "uuid": "f03ccbb6-d8bb-11eb-ac81-00505690980f",
            "description": "File Directory Security Apply Job",
            "state": "success",
            "message": "Complete: Operation completed successfully. File ACLs modified using policy \"policy1\" on Vserver \"GBSMNAS80LD\". File count: 0. [0]",
            "code": 0,
            "start_time": "2021-06-29T05:25:26-04:00",
            "end_time": "2021-06-29T05:25:26-04:00"
        }, None),
    'job_response_record_running': (
        200, {
            "uuid": "f03ccbb6-d8bb-11eb-ac81-00505690980f",
            "description": "File Directory Security Apply Job",
            "state": "running",
            "message": "Complete: Operation completed successfully. File ACLs modified using policy \"policy1\" on Vserver \"GBSMNAS80LD\". File count: 0. [0]",
            "code": 0,
            "start_time": "2021-06-29T05:25:26-04:00",
            "end_time": "2021-06-29T05:25:26-04:00"
        }, None),
    'job_response_record_failure': (
        200, {
            "uuid": "f03ccbb6-d8bb-11eb-ac81-00505690980f",
            "description": "File Directory Security Apply Job",
            "state": "failure",
            "message": "Forcing some error for UT.",
            "code": 0,
            "start_time": "2021-06-29T05:25:26-04:00",
            "end_time": "2021-06-29T05:25:26-04:00"
        }, None),
    'generic_error': (500, None, "Expected error"),
    'rest_error': (400, None, {'message': '-error_message-', 'code': '-error_code-'}),
    'end_of_sequence': (None, None, "Unexpected call to send_request"),
}


def set_default_args(use_rest='auto'):
    hostname = '10.10.10.10'
    username = 'admin'
    password = 'password'
    api = 'abc'
    return dict({
        'hostname': hostname,
        'username': username,
        'password': password,
        'api': api,
        'use_rest': use_rest
    })


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_run_default_get(mock_request, patch_ansible):
    ''' if no method is given, GET is the default '''
    args = dict(set_default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 1


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_run_any(mock_request, patch_ansible):
    ''' We don't validate the method name, so ANYthing goes '''
    args = dict(set_default_args())
    args['method'] = 'ANY'
    args['body'] = {'bkey1': 'bitem1', 'bkey2': 'bitem2'}
    args['query'] = {'qkey1': 'qitem1', 'qkey2': 'qitem2'}
    set_module_args(args)
    mock_request.side_effect = [
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 1
    headers = my_obj.rest_api.build_headers(accept='application/json')
    expected_call = call('ANY', 'abc', args['query'], args['body'], headers)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_run_any_rest_error(mock_request, patch_ansible):
    ''' We don't validate the method name, so ANYthing goes '''
    args = dict(set_default_args())
    args['method'] = 'ANY'
    args['body'] = {'bkey1': 'bitem1', 'bkey2': 'bitem2'}
    args['query'] = {'qkey1': 'qitem1', 'qkey2': 'qitem2'}
    set_module_args(args)
    mock_request.side_effect = [
        SRR['rest_error'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = "Error when calling 'abc': check error_message and error_code for details."
    assert msg == exc.value.args[0]['msg']
    assert '-error_message-' == exc.value.args[0]['error_message']
    assert '-error_code-' == exc.value.args[0]['error_code']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_run_any_other_error(mock_request, patch_ansible):
    ''' We don't validate the method name, so ANYthing goes '''
    args = dict(set_default_args())
    args['method'] = 'ANY'
    args['body'] = {'bkey1': 'bitem1', 'bkey2': 'bitem2'}
    args['query'] = {'qkey1': 'qitem1', 'qkey2': 'qitem2'}
    set_module_args(args)
    mock_request.side_effect = [
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = "Error when calling 'abc': Expected error"
    assert msg == exc.value.args[0]['msg']
    assert 'Expected error' == exc.value.args[0]['error_message']
    assert exc.value.args[0]['error_code'] is None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_run_post_async_no_job(mock_request, patch_ansible):
    ''' POST async, but returns immediately '''
    args = dict(set_default_args())
    args['method'] = 'POST'
    args['body'] = {'bkey1': 'bitem1', 'bkey2': 'bitem2'}
    args['query'] = {'qkey1': 'qitem1', 'qkey2': 'qitem2'}
    args['wait_for_completion'] = True
    set_module_args(args)
    mock_request.side_effect = [
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 1
    headers = my_obj.rest_api.build_headers(accept='application/json')
    args['query'].update({'return_timeout': 30})
    expected_call = call('POST', 'abc', args['query'], json=args['body'], headers=headers)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_run_post_async_with_job(mock_request, patch_ansible):
    ''' POST async, but returns immediately '''
    args = dict(set_default_args())
    args['method'] = 'POST'
    args['body'] = {'bkey1': 'bitem1', 'bkey2': 'bitem2'}
    args['query'] = {'qkey1': 'qitem1', 'qkey2': 'qitem2'}
    args['wait_for_completion'] = True
    set_module_args(args)
    mock_request.side_effect = [
        SRR['job_id_record'],
        SRR['job_response_record'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 2
    headers = my_obj.rest_api.build_headers(accept='application/json')
    args['query'].update({'return_timeout': 30})
    expected_call = call('POST', 'abc', args['query'], json=args['body'], headers=headers)
    assert expected_call in mock_request.mock_calls


# patch time to not wait between job retries
@patch('time.sleep')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_run_patch_async_with_job_loop(mock_request, mock_sleep, patch_ansible):
    ''' POST async, but returns immediately '''
    args = dict(set_default_args())
    args['method'] = 'PATCH'
    args['body'] = {'bkey1': 'bitem1', 'bkey2': 'bitem2'}
    args['query'] = {'qkey1': 'qitem1', 'qkey2': 'qitem2'}
    args['wait_for_completion'] = True
    set_module_args(args)
    mock_request.side_effect = [
        SRR['job_id_record'],
        SRR['job_response_record_running'],
        SRR['job_response_record'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3
    headers = my_obj.rest_api.build_headers(accept='application/json')
    args['query'].update({'return_timeout': 30})
    expected_call = call('PATCH', 'abc', args['query'], json=args['body'], headers=headers)
    assert expected_call in mock_request.mock_calls


@patch('time.sleep')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_run_negative_delete(mock_request, mock_sleep, patch_ansible):
    ''' POST async, but returns immediately '''
    args = dict(set_default_args())
    args['method'] = 'DELETE'
    args['body'] = {'bkey1': 'bitem1', 'bkey2': 'bitem2'}
    args['query'] = {'qkey1': 'qitem1', 'qkey2': 'qitem2'}
    args['wait_for_completion'] = True
    set_module_args(args)
    mock_request.side_effect = [
        SRR['job_id_record'],
        SRR['job_response_record_running'],
        SRR['job_response_record_failure'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = "Error when calling 'abc': Forcing some error for UT."
    assert msg == exc.value.args[0]['msg']
    assert 'Forcing some error for UT.' == exc.value.args[0]['error_message']
    assert exc.value.args[0]['error_code'] is None
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3
    headers = my_obj.rest_api.build_headers(accept='application/json')
    args['query'].update({'return_timeout': 30})
    expected_call = call('DELETE', 'abc', args['query'], json=None, headers=headers)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_run_any_async(mock_request, patch_ansible):
    ''' We don't validate the method name, so ANYthing goes '''
    args = dict(set_default_args())
    args['method'] = 'ANY'
    args['body'] = {'bkey1': 'bitem1', 'bkey2': 'bitem2'}
    args['query'] = {'qkey1': 'qitem1', 'qkey2': 'qitem2'}
    args['wait_for_completion'] = True
    set_module_args(args)
    mock_request.side_effect = [
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 1
    headers = my_obj.rest_api.build_headers(accept='application/json')
    expected_call = call('ANY', 'abc', args['query'], args['body'], headers)
    assert expected_call in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_run_main(mock_request, patch_ansible):
    ''' We don't validate the method name, so ANYthing goes '''
    args = dict(set_default_args())
    args['method'] = 'ANY'
    args['body'] = {'bkey1': 'bitem1', 'bkey2': 'bitem2'}
    args['query'] = {'qkey1': 'qitem1', 'qkey2': 'qitem2'}
    args['wait_for_completion'] = True
    set_module_args(args)
    mock_request.side_effect = [
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleExitJson) as exc:
        my_main()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 1


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_build_headers(mock_request, patch_ansible):
    ''' create cluster '''
    args = dict(set_default_args())
    set_module_args(args)
    my_obj = my_module()
    headers = my_obj.build_headers()
    # TODO: in UT (and only in UT) module._name is not set properly.  It shows as basic.py instead of 'na_ontap_restit'
    assert headers == {'X-Dot-Client-App': 'basic.py/%s' % netapp_utils.COLLECTION_VERSION, 'accept': 'application/json'}
    args['hal_linking'] = True
    set_module_args(args)
    my_obj = my_module()
    headers = my_obj.build_headers()
    assert headers == {'X-Dot-Client-App': 'basic.py/%s' % netapp_utils.COLLECTION_VERSION, 'accept': 'application/hal+json'}
