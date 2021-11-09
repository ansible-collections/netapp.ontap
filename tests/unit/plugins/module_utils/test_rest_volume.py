# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c) 2021, Laurent Nicolas <laurentn@netapp.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

""" unit tests for module_utils netapp_module.py

    Provides wrappers for storage/volumes REST APIs
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
import pytest
import sys

# from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
from ansible_collections.netapp.ontap.plugins.module_utils import rest_volume
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


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
    'one_volume_record': (200, dict(records=[
        dict(uuid='a1b2c3',
             name='test',
             svm=dict(name='vserver'),
             )
    ], num_records=1), None),
    'three_volume_records': (200, dict(records=[
        dict(uuid='a1b2c3_1',
             name='test1',
             svm=dict(name='vserver'),
             ),
        dict(uuid='a1b2c3_2',
             name='test2',
             svm=dict(name='vserver'),
             ),
        dict(uuid='a1b2c3_3',
             name='test3',
             svm=dict(name='vserver'),
             )
    ], num_records=3), None),
    'job': (200, dict(job=dict(
        uuid='a1b2c3_job',
        _links=dict(self=dict(href='api/some_link'))
    )), None),
    'job_bad_url': (200, dict(job=dict(
        uuid='a1b2c3_job',
        _links=dict(self=dict(href='some_link'))
    )), None),
    'job_status_success': (200, dict(
        state='success',
        message='success_message',
    ), None),
}


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


class MockModule(object):
    ''' rough mock for an Ansible module class '''
    def __init__(self):
        self.params = dict(
            username='my_username',
            password='my_password',
            hostname='my_hostname',
            use_rest='my_use_rest',
            cert_filepath=None,
            key_filepath=None,
            validate_certs='my_validate_certs',
            http_port=None,
            feature_flags=None,
        )

    def fail_json(self, *args, **kwargs):  # pylint: disable=unused-argument
        """function to simulate fail_json: package return data into an exception"""
        kwargs['failed'] = True
        raise AnsibleFailJson(kwargs)


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_volumes_none(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        SRR['zero_record'],
        SRR['end_of_sequence']]
    volumes, error = rest_volume.get_volumes(rest_api)
    assert error is None
    assert volumes is None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_volumes_one(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        SRR['one_volume_record'],
        SRR['end_of_sequence']]
    volumes, error = rest_volume.get_volumes(rest_api)
    assert error is None
    assert volumes == [SRR['one_volume_record'][1]['records'][0]]


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_volumes_three(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        SRR['three_volume_records'],
        SRR['end_of_sequence']]
    volumes, error = rest_volume.get_volumes(rest_api)
    assert error is None
    assert volumes == [SRR['three_volume_records'][1]['records'][x] for x in (0, 1, 2)]


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_volume_not_found(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        SRR['zero_record'],
        SRR['end_of_sequence']]
    volume, error = rest_volume.get_volume(rest_api, 'name', 'vserver')
    assert error is None
    assert volume is None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_volume_found(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        SRR['one_volume_record'],
        SRR['end_of_sequence']]
    volume, error = rest_volume.get_volume(rest_api, 'name', 'vserver')
    assert error is None
    assert volume == SRR['one_volume_record'][1]['records'][0]


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_get_volume_too_many(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        SRR['three_volume_records'],
        SRR['end_of_sequence']]
    dummy, error = rest_volume.get_volume(rest_api, 'name', 'vserver')
    expected = "calling: storage/volumes: unexpected response"
    assert expected in error


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_delete_volume_sync(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        SRR['empty_good'],
        SRR['end_of_sequence']]
    volume, error = rest_volume.delete_volume(rest_api, 'uuid')
    assert error is None
    assert volume == dict()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_delete_volume_async(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        copy.deepcopy(SRR['job']),      # deepcopy as job is modified in place!
        SRR['job_status_success'],
        SRR['end_of_sequence']]
    response, error = rest_volume.delete_volume(rest_api, 'uuid')
    job = dict(SRR['job'][1])           # deepcopy as job is modified in place!
    job['job_response'] = SRR['job_status_success'][1]['message']
    assert error is None
    assert response == job


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_delete_volume_async_bad_url(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        SRR['job_bad_url'],
        SRR['end_of_sequence']]
    try:
        response, error = rest_volume.delete_volume(rest_api, 'uuid')
    except UnboundLocalError:
        # TODO: DEVOPS-3627
        response = None
        error = 'DEVOPS-3627'
    # print(mock_request.mock_calls)
    print(error)
    print(response)
    # assert error is None
    # assert response is None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_patch_volume_async(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        copy.deepcopy(SRR['job']),      # deepcopy as job is modified in place!
        SRR['job_status_success'],
        SRR['end_of_sequence']]
    body = dict(a1=1, a2=True, a3='str')
    response, error = rest_volume.patch_volume(rest_api, 'uuid', body)
    job = dict(SRR['job'][1])           # deepcopy as job is modified in place!
    job['job_response'] = SRR['job_status_success'][1]['message']
    assert error is None
    assert response == job
    expected = call('PATCH', 'storage/volumes/uuid', {'return_timeout': 30}, json=body, headers=None)
    assert expected in mock_request.mock_calls


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_patch_volume_async_with_query(mock_request):
    module = MockModule()
    rest_api = netapp_utils.OntapRestAPI(module)
    mock_request.side_effect = [
        copy.deepcopy(SRR['job']),      # deepcopy as job is modified in place!
        SRR['job_status_success'],
        SRR['end_of_sequence']]
    body = dict(a1=1, a2=True, a3='str')
    query = dict(return_timeout=20)
    response, error = rest_volume.patch_volume(rest_api, 'uuid', body, query)
    job = dict(SRR['job'][1])           # deepcopy as job is modified in place!
    job['job_response'] = SRR['job_status_success'][1]['message']
    assert error is None
    assert response == job
    expected = call('PATCH', 'storage/volumes/uuid', {'return_timeout': 20}, json=body, headers=None)
    assert expected in mock_request.mock_calls
