# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible,\
    create_module, create_and_apply, expect_and_capture_ansible_exception
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_lun_copy \
    import NetAppOntapLUNCopy as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')

DEFAULT_ARGS = {
    'source_vserver': 'ansible',
    'destination_path': '/vol/test/test_copy_dest_dest_new_reviewd_new',
    'source_path': '/vol/test/test_copy_1',
    'destination_vserver': 'ansible',
    'state': 'present',
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'never'
}


ZRR = zapi_responses({
    'lun_info': build_zapi_response({'num-records': 1})
})


SRR = rest_responses({
    'lun_info': (200, {"records": [{
        "name": "/vol/vol0/lun1_10"
    }], "num_records": 1}, None)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "destination_vserver", "destination_path", "source_path"]
    error = create_module(my_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_create_error_missing_param():
    ''' Test if create throws an error if required param 'destination_vserver' is not specified'''
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['destination_vserver']
    msg = 'missing required arguments: destination_vserver'
    assert msg in create_module(my_module, DEFAULT_ARGS_COPY, fail=True)['msg']


def test_successful_copy():
    ''' Test successful create and idempotent check '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('lun-get-iter', ZRR['empty']),
        ('lun-copy-start', ZRR['success']),
        ('ems-autosupport-log', ZRR['empty']),
        ('lun-get-iter', ZRR['lun_info'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('lun-get-iter', ZRR['error']),
        ('lun-copy-start', ZRR['error']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/luns', SRR['generic_error']),
        ('POST', 'storage/luns', SRR['generic_error']),
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/luns', SRR['empty_records'])
    ])
    lun_obj = create_module(my_module, DEFAULT_ARGS)
    assert 'Error getting lun info' in expect_and_capture_ansible_exception(lun_obj.get_lun, 'fail')['msg']
    assert 'Error copying lun from' in expect_and_capture_ansible_exception(lun_obj.copy_lun, 'fail')['msg']
    lun_obj = create_module(my_module, DEFAULT_ARGS, {'use_rest': 'always'})
    assert 'Error getting lun info' in expect_and_capture_ansible_exception(lun_obj.get_lun_rest, 'fail')['msg']
    assert 'Error copying lun from' in expect_and_capture_ansible_exception(lun_obj.copy_lun_rest, 'fail')['msg']
    assert 'REST requires ONTAP 9.10.1 or later' in create_module(my_module, DEFAULT_ARGS, {'use_rest': 'always'}, fail=True)['msg']
    args = {'use_rest': 'always', 'destination_vserver': 'some_vserver'}
    assert 'REST does not supports inter-Vserver lun copy' in create_and_apply(my_module, DEFAULT_ARGS, args, fail=True)['msg']


def test_successful_copy_rest():
    ''' Test successful create and idempotent check in REST '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/luns', SRR['empty_records']),
        ('POST', 'storage/luns', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'storage/luns', SRR['lun_info']),
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {'use_rest': 'always'})['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, {'use_rest': 'always'})['changed']
