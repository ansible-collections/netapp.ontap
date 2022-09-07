# Copyright (c) 2022 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils rest_generic.py - REST features '''
from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import create_module, expect_and_capture_ansible_exception, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils import rest_owning_resource

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'get_uuid_policy_id_export_policy': (
        200,
        {
            "records": [{
                "svm": {
                    "uuid": "uuid",
                    "name": "svm"},
                "id": 123,
                "name": "ansible"
            }],
            "num_records": 1}, None),
    'get_uuid_from_volume': (
        200,
        {
            "records": [{
                "svm": {
                    "uuid": "uuid",
                    "name": "svm"},
                "uuid": "028baa66-41bd-11e9-81d5-00a0986138f7"
            }]
        }, None
    )
})

DEFAULT_ARGS = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
}


class MockONTAPModule:
    def __init__(self):
        self.module = basic.AnsibleModule(netapp_utils.na_ontap_host_argument_spec())


def create_restapi_object(default_args, module_args=None):
    module = create_module(MockONTAPModule, default_args, module_args)
    return netapp_utils.OntapRestAPI(module.module)


def test_get_policy_id():
    register_responses([
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record = rest_owning_resource.get_export_policy_id(rest_api, 'ansible', 'svm', rest_api.module)
    assert record == SRR['get_uuid_policy_id_export_policy'][1]['records'][0]['id']


def test_error_get_policy_id():
    register_responses([
        ('GET', 'protocols/nfs/export-policies', SRR['generic_error'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    error = 'Could not find export policy ansible on SVM svm'
    assert error in expect_and_capture_ansible_exception(rest_owning_resource.get_export_policy_id, 'fail', rest_api, 'ansible', 'svm', rest_api.module)['msg']


def test_get_volume_uuid():
    register_responses([
        ('GET', 'storage/volumes', SRR['get_uuid_from_volume'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    record = rest_owning_resource.get_volume_uuid(rest_api, 'ansible', 'svm', rest_api.module)
    assert record == SRR['get_uuid_from_volume'][1]['records'][0]['uuid']


def test_error_get_volume_uuid():
    register_responses([
        ('GET', 'storage/volumes', SRR['generic_error'])
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    error = 'Could not find volume ansible on SVM svm'
    assert error in expect_and_capture_ansible_exception(rest_owning_resource.get_volume_uuid, 'fail', rest_api, 'ansible', 'svm', rest_api.module)['msg']
