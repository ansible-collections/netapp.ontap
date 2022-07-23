# (c) 2019-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_name_service_switch '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import create_module,\
    patch_ansible, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_name_service_switch \
    import NetAppONTAPNsswitch as nss_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'https': 'True',
    'use_rest': 'never',
    'state': 'present',
    'vserver': 'test_vserver',
    'database_type': 'namemap',
    'sources': 'files,ldap',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!'
}


nss_info = {
    'num-records': 1,
    'attributes-list': {
        'namservice-nsswitch-config-info': {
            'nameservice-database': 'namemap',
            'nameservice-sources': {'nss-source-type': 'files,ldap'}
        }
    }
}


ZRR = zapi_responses({
    'nss_info': build_zapi_response(nss_info)
})


def test_module_fail_when_required_args_missing():
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "vserver", "database_type"]
    error = create_module(nss_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_get_nonexistent_nss():
    register_responses([
        ('nameservice-nsswitch-get-iter', ZRR['no_records'])
    ])
    nss_obj = create_module(nss_module, DEFAULT_ARGS)
    assert nss_obj.get_name_service_switch() is None


def test_get_existing_nss():
    register_responses([
        ('nameservice-nsswitch-get-iter', ZRR['nss_info'])
    ])
    nss_obj = create_module(nss_module, DEFAULT_ARGS)
    assert nss_obj.get_name_service_switch()


def test_successfully_create():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('nameservice-nsswitch-get-iter', ZRR['no_records']),
        ('nameservice-nsswitch-create', ZRR['success'])
    ])
    assert create_and_apply(nss_module, DEFAULT_ARGS)['changed']


def test_successfully_modify():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('nameservice-nsswitch-get-iter', ZRR['nss_info']),
        ('nameservice-nsswitch-modify', ZRR['success'])
    ])
    assert create_and_apply(nss_module, DEFAULT_ARGS, {'sources': 'files'})['changed']


def test_successfully_delete():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('nameservice-nsswitch-get-iter', ZRR['nss_info']),
        ('nameservice-nsswitch-destroy', ZRR['success'])
    ])
    assert create_and_apply(nss_module, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_if_all_methods_catch_exception_zapi():
    ''' test error zapi - get/create/modify/delete'''
    register_responses([
        ('nameservice-nsswitch-get-iter', ZRR['error']),
        ('nameservice-nsswitch-create', ZRR['error']),
        ('nameservice-nsswitch-modify', ZRR['error']),
        ('nameservice-nsswitch-destroy', ZRR['error'])
    ])
    nss_obj = create_module(nss_module, DEFAULT_ARGS)

    assert 'Error fetching name service switch' in expect_and_capture_ansible_exception(nss_obj.get_name_service_switch, 'fail')['msg']
    assert 'Error on creating name service switch' in expect_and_capture_ansible_exception(nss_obj.create_name_service_switch, 'fail')['msg']
    assert 'Error on modifying name service switch' in expect_and_capture_ansible_exception(nss_obj.modify_name_service_switch, 'fail', {})['msg']
    assert 'Error on deleting name service switch' in expect_and_capture_ansible_exception(nss_obj.delete_name_service_switch, 'fail')['msg']


SRR = rest_responses({
    'nss_info': (200, {"records": [
        {
            'nsswitch': {
                'group': ['files'],
                'hosts': ['files', 'dns'],
                'namemap': ['files'],
                'netgroup': ['files'],
                'passwd': ['files']
            },
            'uuid': '6647fa13'}
    ], 'num_records': 1}, None),
    'nss_info_no_record': (200, {"records": [
        {'uuid': '6647fa13'}
    ], 'num_records': 1}, None),
    'svm_uuid': (200, {"records": [
        {'uuid': '6647fa13'}
    ], "num_records": 1}, None)
})


def test_successfully_modify_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['nss_info_no_record']),
        ('PATCH', 'svm/svms/6647fa13', SRR['success']),
    ])
    args = {'sources': 'files', 'use_rest': 'always'}
    assert create_and_apply(nss_module, DEFAULT_ARGS, args)['changed']


def test_error_get_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['zero_records'])
    ])
    error = "Error: Specified vserver test_vserver not found"
    assert error in create_and_apply(nss_module, DEFAULT_ARGS, {'use_rest': 'always'}, fail=True)['msg']


def test_error_delete_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['nss_info'])
    ])
    args = {'state': 'absent', 'use_rest': 'always'}
    error = "Error: deleting name service switch not supported in REST."
    assert error in create_and_apply(nss_module, DEFAULT_ARGS, args, fail=True)['msg']


def test_if_all_methods_catch_exception_rest():
    ''' test error rest - get/modify'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'svm/svms', SRR['generic_error']),
        ('PATCH', 'svm/svms/6647fa13', SRR['generic_error']),
    ])
    nss_obj = create_module(nss_module, DEFAULT_ARGS, {'use_rest': 'always'})
    nss_obj.svm_uuid = '6647fa13'
    assert 'Error fetching name service switch' in expect_and_capture_ansible_exception(nss_obj.get_name_service_switch, 'fail')['msg']
    assert 'Error on modifying name service switch' in expect_and_capture_ansible_exception(nss_obj.modify_name_service_switch_rest, 'fail')['msg']
