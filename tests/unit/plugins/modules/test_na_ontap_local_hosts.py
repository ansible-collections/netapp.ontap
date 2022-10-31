# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_local_hosts \
    import NetAppOntapLocalHosts as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'host_record': (200, {
        "records": [
            {
                "owner": {"name": "svm", "uuid": "e3cb5c7fcd20"},
                "address": "10.10.10.10",
                "host": "example.com",
                "aliases": ["ex1.com", "ex2.com"]
            }],
        "num_records": 1
    }, None),
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'address': '10.10.10.10',
    'owner': 'svm',
}


def test_get_local_host_rest_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'name-services/local-hosts', SRR['empty_records'])
    ])
    module_args = {'address': '10.10.10.10', 'owner': 'svm'}
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_local_host_rest() is None


def test_get_local_host_rest_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'name-services/local-hosts', SRR['generic_error'])
    ])
    module_args = {'address': '10.10.10.10', 'owner': 'svm'}
    my_module_object = create_module(my_module, DEFAULT_ARGS, module_args)
    msg = 'Error fetching IP to hostname mappings for svm: calling: name-services/local-hosts: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_local_host_rest, 'fail')['msg']


def test_create_local_host_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'name-services/local-hosts', SRR['empty_records']),
        ('POST', 'name-services/local-hosts', SRR['empty_good'])
    ])
    module_args = {
        'address': '10.10.10.10',
        'owner': 'svm',
        'host': 'example.com',
        'aliases': ['ex.com', 'ex1.com']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_create_local_host_rest_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'name-services/local-hosts', SRR['empty_records']),
        ('POST', 'name-services/local-hosts', SRR['generic_error'])
    ])
    module_args = {
        'address': '10.10.10.10',
        'owner': 'svm',
        'host': 'example.com',
        'aliases': ['ex.com', 'ex1.com']}
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error creating IP to hostname mappings for svm: calling: name-services/local-hosts: got Expected error.'
    assert msg in error


def test_create_local_host_rest_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'name-services/local-hosts', SRR['host_record'])
    ])
    module_args = {'state': 'present'}
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_local_host():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'name-services/local-hosts', SRR['host_record']),
        ('DELETE', 'name-services/local-hosts/e3cb5c7fcd20/10.10.10.10', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_local_host_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'name-services/local-hosts', SRR['host_record']),
        ('DELETE', 'name-services/local-hosts/e3cb5c7fcd20/10.10.10.10', SRR['generic_error'])
    ])
    module_args = {'state': 'absent'}
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error deleting IP to hostname mappings for svm: calling: name-services/local-hosts/e3cb5c7fcd20/10.10.10.10: got Expected error.'
    assert msg in error


def test_delete_local_host_rest_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'name-services/local-hosts', SRR['empty_records'])
    ])
    module_args = {'state': 'absent'}
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_local_host():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'name-services/local-hosts', SRR['host_record']),
        ('PATCH', 'name-services/local-hosts/e3cb5c7fcd20/10.10.10.10', SRR['empty_good'])
    ])
    module_args = {
        'address': '10.10.10.10',
        'owner': 'svm',
        'host': 'example1.com',
        'aliases': ['ex.com', 'ex1.com', 'ex2.com']}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_local_host_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'name-services/local-hosts', SRR['host_record']),
        ('PATCH', 'name-services/local-hosts/e3cb5c7fcd20/10.10.10.10', SRR['generic_error'])
    ])
    module_args = {
        'address': '10.10.10.10',
        'owner': 'svm',
        'host': 'example1.com',
        'aliases': ['ex.com', 'ex1.com', 'ex2.com']}
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error updating IP to hostname mappings for svm: calling: name-services/local-hosts/e3cb5c7fcd20/10.10.10.10: got Expected error.'
    assert msg in error


def validate_input_ipaddress():
    register_responses([
    ])
    module_args = {'address': '2001:0000:3238:DFE1:63:0000:0000:FEFBSS', 'owner': 'svm'}
    error = create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error: Invalid IP address value 2001:0000:3238:DFE1:63:0000:0000:FEFBSS'
    assert msg in error
