# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c) 2022, Laurent Nicolas <laurentn@netapp.com>
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

""" unit tests for module_utils rest_vserver.py

    Provides wrappers for svm/svms REST APIs
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import create_module, expect_and_capture_ansible_exception, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.module_utils import rest_vserver


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'svm_uuid': (200, {"records": [{"uuid": "test_uuid"}], "num_records": 1}, None),
})


DEFAULT_ARGS = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'cert_filepath': None,
    'key_filepath': None,
}


class MockONTAPModule:
    def __init__(self):
        self.module = basic.AnsibleModule(netapp_utils.na_ontap_host_argument_spec())


def create_restapi_object(default_args, module_args=None):
    module = create_module(MockONTAPModule, default_args, module_args)
    return netapp_utils.OntapRestAPI(module.module)


def test_successfully_get_vserver():
    register_responses([
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'svm/svms', SRR['zero_records']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    assert rest_vserver.get_vserver(rest_api, 'svm_name') == ({'uuid': 'test_uuid'}, None)
    assert rest_vserver.get_vserver(rest_api, 'svm_name') == (None, None)


def test_negative_get_vserver():
    register_responses([
        ('GET', 'svm/svms', SRR['generic_error']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    assert rest_vserver.get_vserver(rest_api, 'svm_name') == (None, rest_error_message('', 'svm/svms'))


def test_successfully_get_vserver_uuid():
    register_responses([
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'svm/svms', SRR['zero_records']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    assert rest_vserver.get_vserver_uuid(rest_api, 'svm_name') == ('test_uuid', None)
    assert rest_vserver.get_vserver_uuid(rest_api, 'svm_name') == (None, None)


def test_negative_get_vserver_uuid():
    register_responses([
        ('GET', 'svm/svms', SRR['generic_error']),
        ('GET', 'svm/svms', SRR['generic_error']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('GET', 'svm/svms', SRR['zero_records']),
    ])
    rest_api = create_restapi_object(DEFAULT_ARGS)
    assert rest_vserver.get_vserver_uuid(rest_api, 'svm_name') == (None, rest_error_message('', 'svm/svms'))
    assert expect_and_capture_ansible_exception(rest_vserver.get_vserver_uuid, 'fail', rest_api, 'svm_name', rest_api.module)['msg'] ==\
        rest_error_message('Error fetching vserver svm_name', 'svm/svms')
    assert rest_vserver.get_vserver_uuid(rest_api, 'svm_name', error_on_none=True) == (None, 'vserver svm_name not found.')
    assert expect_and_capture_ansible_exception(rest_vserver.get_vserver_uuid, 'fail', rest_api, 'svm_name', rest_api.module, error_on_none=True)['msg'] ==\
        'Error vserver svm_name not found.', 'svm/svms'
