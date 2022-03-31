# (c) 2021-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP fpolicy ext engine Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    call_main, create_and_apply, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_disk_options \
    import NetAppOntapDiskOptions as my_module, main as my_main     # module under test


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'node': 'node1',
    'bkg_firmware_update': False,
    'autocopy': False,
    'autoassign': False,
    'autoassign_policy': 'default',
    'hostname': '10.10.10.10',
    'username': 'username',
    'password': 'password',
    'use_rest': 'always'
}


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'one_disk_options_record': (200, {
        "records": [{
            'node': 'node1',
            'bkg_firmware_update': False,
            'autocopy': False,
            'autoassign': False,
            'autoassign_policy': 'default'
        }]
    }, None),
    'one_disk_options_record_on_off': (200, {
        "records": [{
            'node': 'node1',
            'bkg_firmware_update': 'on',
            'autocopy': 'off',
            'autoassign': 'on',
            'autoassign_policy': 'default'
        }]
    }, None),
    'one_disk_options_record_bad_value': (200, {
        "records": [{
            'node': 'node1',
            'bkg_firmware_update': 'whatisthis',
            'autocopy': 'off',
            'autoassign': 'on',
            'autoassign_policy': 'default'
        }]
    }, None)

}, False)


def test_rest_modify_no_action():
    ''' modify fpolicy ext engine '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/storage/disk/option', SRR['one_disk_options_record']),
    ])
    assert not create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_rest_modify_prepopulate():
    ''' modify disk options '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/storage/disk/option', SRR['one_disk_options_record']),
        ('PATCH', 'private/cli/storage/disk/option', SRR['empty_good']),
    ])
    args = {'autoassign': True, 'autocopy': True, 'bkg_firmware_update': True}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_rest_modify_on_off():
    ''' modify disk options '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/storage/disk/option', SRR['one_disk_options_record_on_off']),
        ('PATCH', 'private/cli/storage/disk/option', SRR['empty_good']),
    ])
    args = {'autoassign': True, 'autocopy': True, 'bkg_firmware_update': True}
    assert create_and_apply(my_module, DEFAULT_ARGS, args)['changed']


def test_error_rest_get_not_on_off():
    ''' modify disk options '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/storage/disk/option', SRR['one_disk_options_record_bad_value']),
    ])
    args = {'autoassign': True, 'autocopy': True, 'bkg_firmware_update': True}
    assert create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg'] == 'Unexpected value for field bkg_firmware_update: whatisthis'


def test_error_rest_no_zapi_support():
    ''' modify disk options '''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
    ])
    args = {'use_rest': 'auto'}
    assert "na_ontap_disk_options only supports REST, and requires ONTAP 9.6 or later." in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']


def test_error_get():
    ''' get disk options '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/storage/disk/option', SRR['generic_error']),
    ])
    args = {'use_rest': 'auto'}
    assert "calling: private/cli/storage/disk/option: got Expected error." in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']


def test_error_get_empty():
    ''' get disk options '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/storage/disk/option', SRR['empty_records']),
    ])
    args = {'use_rest': 'auto'}
    assert "Error on GET private/cli/storage/disk/option, no record." == call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']


def test_error_patch():
    ''' modify disk options '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'private/cli/storage/disk/option', SRR['one_disk_options_record_on_off']),
        ('PATCH', 'private/cli/storage/disk/option', SRR['generic_error']),
    ])
    args = {'use_rest': 'auto'}
    assert "calling: private/cli/storage/disk/option: got Expected error." in call_main(my_main, DEFAULT_ARGS, args, fail=True)['msg']
