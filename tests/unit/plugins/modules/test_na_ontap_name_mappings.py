# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_name_mappings """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest


import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    patch_ansible, create_module, create_and_apply, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_name_mappings \
    import NetAppOntapNameMappings as my_module  # module under test


# REST API canned responses when mocking send_request
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'mapping_record': (
        200,
        {
            "records": [
                {
                    "client_match": "10.254.101.111/28",
                    "direction": "win_unix",
                    "index": 1,
                    "pattern": "ENGCIFS_AD_USER",
                    "replacement": "unix_user1",
                    "svm": {
                        "name": "svm1",
                        "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
                    }
                }
            ],
            "num_records": 1
        }, None
    ),
    'mapping_record1': (
        200,
        {
            "records": [
                {
                    "direction": "win_unix",
                    "index": 2,
                    "pattern": "ENGCIFS_AD_USERS",
                    "replacement": "unix_user",
                    "svm": {
                        "name": "svm1",
                        "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
                    }
                }
            ],
            "num_records": 1
        }, None
    ),
    "no_record": (
        200,
        {"num_records": 0},
        None)
})


DEFAULT_ARGS = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'vserver': 'svm1',
    'direction': 'win_unix',
    'index': '1'
}


def test_get_name_mappings_rest():
    ''' Test retrieving name mapping record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['mapping_record']),
    ])
    name_obj = create_module(my_module, DEFAULT_ARGS)
    result = name_obj.get_name_mappings_rest()
    assert result


def test_error_get_name_mappings_rest():
    ''' Test error retrieving name mapping record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, DEFAULT_ARGS, fail=True)['msg']
    msg = "calling: name-services/name-mappings: got Expected error."
    assert msg in error


def test_create_name_mappings_rest():
    ''' Test create name mapping record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['empty_records']),
        ('POST', 'name-services/name-mappings', SRR['empty_good']),
    ])
    module_args = {
        "pattern": "ENGCIFS_AD_USER",
        "replacement": "unix_user1",
        "client_match": "10.254.101.111/28",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_create_name_mappings_rest():
    ''' Test error create name mapping record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['empty_records']),
        ('POST', 'name-services/name-mappings', SRR['generic_error']),
    ])
    module_args = {
        "pattern": "ENGCIFS_AD_USER",
        "replacement": "unix_user1",
        "client_match": "10.254.101.111/28",
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error on creating name mappings rest:"
    assert msg in error


def test_delete_name_mappings_rest():
    ''' Test delete name mapping record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['mapping_record']),
        ('DELETE', 'name-services/name-mappings/02c9e252-41be-11e9-81d5-00a0986138f7/win_unix/1', SRR['empty_good']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_name_mappings_rest():
    ''' Test error delete name mapping record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['mapping_record']),
        ('DELETE', 'name-services/name-mappings/02c9e252-41be-11e9-81d5-00a0986138f7/win_unix/1', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error on deleting name mappings rest:"
    assert msg in error


def test_create_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['mapping_record'])
    ])
    module_args = {
        "pattern": "ENGCIFS_AD_USER",
        "replacement": "unix_user1",
        "client_match": "10.254.101.111/28",
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_idempotent_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['empty_records'])
    ])
    module_args = {
        'state': 'absent'
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_name_mappings_pattern_rest():
    ''' Test modify name mapping pattern '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['mapping_record']),
        ('PATCH', 'name-services/name-mappings/02c9e252-41be-11e9-81d5-00a0986138f7/win_unix/1', SRR['empty_good']),
    ])
    module_args = {
        "pattern": "ENGCIFS_AD_USERS",
        "replacement": "unix_user2",
        "client_match": "10.254.101.112/28",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_name_mappings_replacement_rest():
    ''' Test modify name mapping replacement '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['mapping_record1']),
        ('PATCH', 'name-services/name-mappings/02c9e252-41be-11e9-81d5-00a0986138f7/win_unix/1', SRR['empty_good']),
    ])
    module_args = {
        "replacement": "unix_user2"
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_name_mappings_client_match_rest():
    ''' Test modify name mapping client match '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['mapping_record']),
        ('PATCH', 'name-services/name-mappings/02c9e252-41be-11e9-81d5-00a0986138f7/win_unix/1', SRR['empty_good']),
    ])
    module_args = {
        "client_match": "10.254.101.112/28",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_modify_name_mappings_rest():
    ''' Test error modify name mapping '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['mapping_record']),
        ('PATCH', 'name-services/name-mappings/02c9e252-41be-11e9-81d5-00a0986138f7/win_unix/1', SRR['generic_error']),
    ])
    module_args = {
        "pattern": "ENGCIFS_AD_USERS",
        "replacement": "unix_user2",
        "client_match": "10.254.101.112/28",
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error on modifying name mappings rest:"
    assert msg in error


def test_swap_name_mappings_new_index_rest():
    ''' Test swap name mapping positions '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'name-services/name-mappings', SRR['empty_records']),
        ('GET', 'name-services/name-mappings', SRR['mapping_record1']),
        ('PATCH', 'name-services/name-mappings/02c9e252-41be-11e9-81d5-00a0986138f7/win_unix/2', SRR['empty_good']),
    ])
    module_args = {
        "index": "1",
        "from_index": "2"
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_parameters_for_create_name_mappings_rest():
    ''' Validate parameters for create name mapping record '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'name-services/name-mappings', SRR['empty_records']),
    ])
    module_args = {
        "client_match": "10.254.101.111/28",
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = "Error creating name mappings for an SVM, pattern and replacement are required in create."
    assert msg in error
