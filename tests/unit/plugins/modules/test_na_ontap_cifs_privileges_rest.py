# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_cifs_privileges """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_privileges \
    import NetAppOntapCifsPrivileges as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always',
    'state': 'present',
    'vserver': 'vserver',
    'name': 'local_user1',
    'privileges': ['SeTcbPrivilege']
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    'svm_uuid': (200, {'records': [
        {
            'uuid': '23a7e7f0-23d9-11ef-b005-000c2962c157'
        }], 'num_records': 1}, None),
    'local_user_privileges': (200, {
        'records': [{
            'svm': {
                'uuid': '23a7e7f0-23d9-11ef-b005-000c2962c157',
                'name': 'ansibleSVM'
            },
            'name': 'CIFS\\local_user1',
            'privileges': [
                'setcbprivilege'
            ]
        }]
    }, None),
    'local_user_privileges_updated': (200, {
        'records': [{
            'svm': {
                'uuid': '23a7e7f0-23d9-11ef-b005-000c2962c157',
                'name': 'ansibleSVM'
            },
            'name': 'CIFS\\local_user1',
            'privileges': [
                'sebackupprivilege',
                'setcbprivilege'
            ]
        }]
    }, None),
})


def test_get_cifs_privileges_none():
    ''' Test module no records '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/users-and-groups/privileges', SRR['zero_records']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_cifs_privileges() is None


def test_get_cifs_privileges_error():
    ''' Test module GET method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/users-and-groups/privileges', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching CIFS privileges for local_user1: calling: protocols/cifs/users-and-groups/privileges: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.get_cifs_privileges, 'fail')['msg']


def test_get_cifs_privileges():
    ''' Test GET record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/users-and-groups/privileges', SRR['local_user_privileges']),
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_cifs_privileges() is not None


def test_add_cifs_privileges():
    ''' Test adding privileges with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/users-and-groups/privileges', SRR['empty_records']),
        ('POST', 'protocols/cifs/users-and-groups/privileges', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/users-and-groups/privileges', SRR['local_user_privileges'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_add_cifs_privileges_error():
    ''' Test module POST method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('POST', 'protocols/cifs/users-and-groups/privileges', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error adding CIFS privileges for local_user1: calling: protocols/cifs/users-and-groups/privileges: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.add_cifs_privileges, 'fail')['msg']


def test_modify_cifs_privileges():
    ''' Test modifying privileges with idempotency check '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/users-and-groups/privileges', SRR['local_user_privileges']),
        ('PATCH', 'protocols/cifs/users-and-groups/privileges/23a7e7f0-23d9-11ef-b005-000c2962c157/CIFS\\local_user1', SRR['empty_good']),

        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/cifs/users-and-groups/privileges', SRR['local_user_privileges_updated'])
    ])
    module_args = {
        'privileges': ['SeTcbPrivilege', 'SeBackupPrivilege']
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_cifs_privileges_error():
    ''' Test module PATCH method exception '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('PATCH', 'protocols/cifs/users-and-groups/privileges/23a7e7f0-23d9-11ef-b005-000c2962c157/local_user1', SRR['generic_error']),
    ])
    module_args = {
        'privileges': ['SeTcbPrivilege', 'SeBackupPrivilege']
    }
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.svm_uuid = '23a7e7f0-23d9-11ef-b005-000c2962c157'
    my_obj.parameters['name'] = 'local_user1'
    my_obj.parameters['privileges'] = ['SeTcbPrivilege', 'SeBackupPrivilege']
    current = {'privileges': ['SeTcbPrivilege']}
    msg = 'Error modifying CIFS privileges for local_user1: calling: '\
          'protocols/cifs/users-and-groups/privileges/23a7e7f0-23d9-11ef-b005-000c2962c157/local_user1: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.modify_cifs_privileges, 'fail', current)['msg']


def test_earlier_version():
    ''' Test module supported from 9.10.1 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    module_args = {
        'name': 'local_user1',
        'privileges': ['SeTcbPrivilege']
    }
    assert 'requires ONTAP 9.10.1 or later' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_get_svm_uuid_error():
    ''' Test error fetch SVM UUID '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    error = expect_and_capture_ansible_exception(my_obj.get_svm_uuid, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error fetching vserver vserver: calling: svm/svms: got Expected error.' == error
