# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP na_ontap_fdspt Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest
import sys

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_fdspt \
    import NetAppOntapFDSPT as my_module  # module under test


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


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
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


def default_args():
    args = {
        'name': 'policy1',
        'vserver': 'vserver1',
        'hostname': '10.10.10.10',
        'username': 'username',
        'password': 'password',
        'use_rest': 'always',
        'ntfs_mode': 'ignore',
        'security_type': 'ntfs',
        'path': '/'
    }
    return args


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'policy_task_record': (
        200, {
            'records': [{
                'vserver': 'vserver1',
                'policy_name': 'policy1',
                'index_num': 1,
                'path': '/',
                'security_type': 'ntfs',
                'ntfs_mode': 'ignore',
                'access_control': 'file_directory'}],
            'num_records': 1},
        None),
}


# using pytest natively, without unittest.TestCase
@pytest.fixture
def patch_ansible():
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json) as mocks:
        yield mocks


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_rest_missing_arguments(patch_ansible):     # pylint: disable=redefined-outer-name,unused-argument
    ''' test missing arguements '''
    args = dict(default_args())
    del args['hostname']
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = 'missing required arguments: hostname'
    assert exc.value.args[0]['msg'] == msg


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Create security policies'''
    args = dict(default_args())
    args['name'] = 'new_policy_task'
    print(args)
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],
        SRR['empty_good'],  # create
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_remove(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' remove Security policies '''
    args = dict(default_args())
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['policy_task_record'],
        SRR['empty_good'],  # delete
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_modify(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' remove Security policies '''
    args = dict(default_args())
    args['state'] = 'present'
    args['name'] = 'policy1'
    args['ntfs_mode'] = 'replace'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['policy_task_record'],
        SRR['empty_good'],  # delete
        SRR['empty_good'],  # add
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_no_action(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Idempotent test '''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['policy_task_record'],
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is False
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 2
