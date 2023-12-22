# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_cifs_unix_symlink_mapping """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    create_and_apply, create_module, call_main, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_unix_symlink_mapping \
    import NetAppOntapCifsUnixSymlink as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip(
        'Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always'
}


# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    'symlink_mapping': (200, {"records": [
        {
            "svm": {
                "uuid": "a7d278fb-2d2d-11ee-b8da-005056b37403",
                "name": "ansibleSVM"
            },
            "unix_path": "/example1/",
            "target": {
                "share": "share1",
                "path": "/path1/test_dir/",
                "server": "CIFS",
                "locality": "local",
                "home_directory": False
            }
        }
    ]
    }, None),
})


svm_uuid = 'a7d278fb-2d2d-11ee-b8da-005056b37403'
unix_path = '/example1/'
unix_path_encoded = unix_path.replace('/', '%2F')


def test_successful_create():
    ''' Test successful rest create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/cifs/unix-symlink-mapping', SRR['empty_records']),
        ('POST', 'protocols/cifs/unix-symlink-mapping', SRR['empty_good']),
    ])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/',
        'share_name': 'share1',
        'cifs_path': '/path1/test_dir/'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_successful_create_idempotency():
    ''' Test successful rest create idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/cifs/unix-symlink-mapping', SRR['symlink_mapping']),
    ])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/',
        'share_name': 'share1',
        'cifs_path': '/path1/test_dir/'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed'] is False


def test_successful_delete():
    ''' Test successful rest delete '''
    unix_path_encoded = '%2Fexample1%2F'
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/cifs/unix-symlink-mapping', SRR['symlink_mapping']),
        ('DELETE', 'protocols/cifs/unix-symlink-mapping/%s/%s' % (svm_uuid, unix_path_encoded), SRR['success']),
    ])
    args = {
        'state': 'absent',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_successful_delete_idempotency():
    ''' Test successful rest delete idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/cifs/unix-symlink-mapping', SRR['empty_records']),
    ])
    args = {
        'state': 'absent',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed'] is False


def test_successful_modify():
    ''' Test successful rest modify '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/cifs/unix-symlink-mapping', SRR['symlink_mapping']),
        ('PATCH', 'protocols/cifs/unix-symlink-mapping/%s/%s' % (svm_uuid, unix_path_encoded), SRR['success']),
    ])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/',
        'share_name': 'share2',
        'cifs_path': '/path2/test_dir/'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_error_get():
    ''' Test error rest get '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/cifs/unix-symlink-mapping', SRR['generic_error']),
    ]),
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/',
        'share_name': 'share1',
        'cifs_path': '/path1/test_dir/'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error while fetching cifs unix symlink mapping' in error


def test_error_create():
    ''' Test error rest create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/cifs/unix-symlink-mapping', SRR['empty_records']),
        ('POST', 'protocols/cifs/unix-symlink-mapping', SRR['generic_error']),
    ]),
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/',
        'share_name': 'share1',
        'cifs_path': '/path1/test_dir/'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error while creating cifs unix symlink mapping' in error


def test_error_modify():
    ''' Test error rest modify '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/cifs/unix-symlink-mapping', SRR['symlink_mapping']),
        ('PATCH', 'protocols/cifs/unix-symlink-mapping/%s/%s' % (svm_uuid, unix_path_encoded), SRR['generic_error']),
    ])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/',
        'share_name': 'share2',
        'cifs_path': '/path2/test_dir/'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error while modifying cifs unix symlink mapping' in error


def test_error_delete():
    ''' Test error rest delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'protocols/cifs/unix-symlink-mapping', SRR['symlink_mapping']),
        ('DELETE', 'protocols/cifs/unix-symlink-mapping/%s/%s' % (svm_uuid, unix_path_encoded), SRR['generic_error']),
    ])
    args = {
        'state': 'absent',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'Error while deleting cifs unix symlink mapping' in error


def test_error_ontap96():
    ''' Test error module supported from 9.6 '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest'])
    ])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'unix_path': 'example1',
        'share_name': 'share1',
        'cifs_path': '/path1/test_dir/'
    }
    assert 'requires ONTAP 9.6.0 or later' in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']


def test_missing_options_state_present():
    ''' Test error missing options with state=present '''
    register_responses([])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/'
    }
    error = create_module(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'state is present but all of the following are missing: share_name, cifs_path' in error


def test_missing_options_locality_widelink():
    ''' Test error missing cifs_server with locality=widelink '''
    register_responses([])
    args = {
        'state': 'present',
        'vserver': 'ansibleSVM',
        'unix_path': '/example1/',
        'share_name': 'share1',
        'cifs_path': '/path1/test_dir/',
        'locality': 'widelink'
    }
    error = create_module(my_module, DEFAULT_ARGS, args, fail=True)['msg']
    assert 'locality is widelink but all of the following are missing: cifs_server' in error
