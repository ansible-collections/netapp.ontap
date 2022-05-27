# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception, AnsibleFailJson
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_vscan_on_demand_task \
    import NetAppOntapVscanOnDemandTask as my_module, main as my_main  # module under test

# needed for get and modify/delete as they still use ZAPI
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    'on_demand_task': (200, {"records": [
        {
            "log_path": "/vol0/report_dir",
            "scan_paths": [
                "/vol1/",
                "/vol2/cifs/"
            ],
            "name": "task-1",
            "svm": {
                "name": "svm1",
                "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
            },
            "scope": {
                "exclude_paths": [
                    "/vol1/cold-files/",
                    "/vol1/cifs/names"
                ],
                "scan_without_extension": True,
                "include_extensions": [
                    "vmdk",
                    "mp*"
                ],
                "exclude_extensions": [
                    "mp3",
                    "mp4"
                ],
                "max_file_size": "10737418240"
            },
            "schedule": {
                "name": "weekly",
                "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
            }
        }
    ]}, None),
    'svm_info': (200, {
        "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412",
        "name": "svm1",
    }, None),
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'svm1',
    'use_rest': 'always',
    'task_name': 'carchi8pytask',
    'scan_paths': ['/vol/vol1/'],
    'report_directory': '/',
}


def test_get_svm_uuid():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['svm_info'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_svm_uuid() is None


def test_get_svm_uuid_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['generic_error'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    msg = 'Error fetching svm uuid: calling: svm/svms: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.get_svm_uuid, 'fail')['msg']


def test_get_vscan_on_demand_task_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    my_obj.svm_uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    assert my_obj.get_demand_task_rest() is None


def test_get_vscan_on_demand_task_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies', SRR['generic_error'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    my_obj.svm_uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    msg = 'Error fetching on demand task carchi8pytask: calling: protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.get_demand_task_rest, 'fail')['msg']


def test_create_vscan_on_demand_task():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['svm_info']),
        ('GET', 'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies', SRR['empty_records']),
        ('POST', 'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {})['changed']


def test_create_vscan_on_demand_task_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies', SRR['generic_error'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    my_obj.svm_uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    msg = 'Error creating on demand task carchi8pytask: calling: protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.create_demand_task_rest, 'fail')['msg']


def test_create_vscan_on_demand_task_with_all_options():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['svm_info']),
        ('GET', 'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies', SRR['empty_records']),
        ('POST', 'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies', SRR['empty_good'])
    ])
    module_args = {'file_ext_to_exclude': ['mp3', 'mp4'],
                   'file_ext_to_include': ['vmdk', 'mp*'],
                   'max_file_size': '10737418240',
                   'paths_to_exclude': ['/vol1/cold-files/', '/vol1/cifs/names'],
                   'schedule': 'weekly'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_vscan_on_demand_task():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['svm_info']),
        ('GET', 'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies', SRR['on_demand_task']),
        ('DELETE', 'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies/carchi8pytask', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_vscan_on_demand_task_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('DELETE', 'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies/carchi8pytask', SRR['generic_error'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    my_obj.svm_uuid = '1cd8a442-86d1-11e0-ae1c-123478563412'
    msg = 'Error deleting on demand task carchi8pytask: calling: ' + \
          'protocols/vscan/1cd8a442-86d1-11e0-ae1c-123478563412/on-demand-policies/carchi8pytask: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_obj.delete_demand_task_rest, 'fail')['msg']
