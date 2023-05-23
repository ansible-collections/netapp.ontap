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
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import create_module, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.module_utils import rest_application


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'app_uuid': (200, {"records": [{"uuid": "test_uuid"}], "num_records": 1}, None),
    'app_details': (200, {"details": "test_details"}, None),
    'app_components': (200, {"records": [{"component": "test_component", "uuid": "component_uuid"}], "num_records": 1}, None),
    'app_component_details': (200, {"component": "test_component", "uuid": "component_uuid", 'backing_storage': 'backing_storage'}, None),
    'unexpected_argument': (200, None, 'Unexpected argument: exclude_aggregates'),
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


def create_app(svm_name='vserver_name', app_name='application_name'):
    rest_api = create_restapi_object(DEFAULT_ARGS)
    return rest_application.RestApplication(rest_api, svm_name, app_name)


def test_successfully_create_object():
    register_responses([
        # ('GET', 'svm/svms', SRR['svm_uuid']),
        # ('GET', 'svm/svms', SRR['zero_records']),
    ])
    assert create_app().svm_name == 'vserver_name'


def test_successfully_get_application_uuid():
    register_responses([
        ('GET', 'application/applications', SRR['zero_records']),
        ('GET', 'application/applications', SRR['app_uuid']),
    ])
    my_app = create_app()
    assert my_app.get_application_uuid() == (None, None)
    assert my_app.get_application_uuid() == ('test_uuid', None)
    # UUID is cached if not None, so no API call
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.get_application_uuid() == ('test_uuid', None)


def test_negative_get_application_uuid():
    register_responses([
        ('GET', 'application/applications', SRR['generic_error']),
    ])
    my_app = create_app()
    assert my_app.get_application_uuid() == (None, rest_error_message('', 'application/applications'))


def test_successfully_get_application_details():
    register_responses([
        ('GET', 'application/applications', SRR['zero_records']),
        ('GET', 'application/applications', SRR['app_uuid']),
        ('GET', 'application/applications/test_uuid', SRR['app_details']),
        ('GET', 'application/applications/test_uuid', SRR['app_details']),
        ('GET', 'application/applications/test_uuid', SRR['app_details']),
    ])
    my_app = create_app()
    assert my_app.get_application_details() == (None, None)
    assert my_app.get_application_details() == (SRR['app_details'][1], None)
    # UUID is cached if not None, so no API call
    assert my_app.get_application_details(template='test') == (SRR['app_details'][1], None)
    assert my_app.get_application_details() == (SRR['app_details'][1], None)


def test_negative_get_application_details():
    register_responses([
        ('GET', 'application/applications', SRR['generic_error']),
        ('GET', 'application/applications', SRR['app_uuid']),
        ('GET', 'application/applications/test_uuid', SRR['generic_error']),
    ])
    my_app = create_app()
    assert my_app.get_application_details() == (None, rest_error_message('', 'application/applications'))
    assert my_app.get_application_details() == (None, rest_error_message('', 'application/applications/test_uuid'))


def test_successfully_create_application():
    register_responses([
        ('POST', 'application/applications', SRR['success']),
    ])
    my_app = create_app()
    assert my_app.create_application({'option': 'option'}) == ({}, None)


def test_negative_create_application():
    register_responses([
        ('POST', 'application/applications', SRR['generic_error']),
        ('POST', 'application/applications', SRR['unexpected_argument']),
        # third call, create fails if app already exists
        ('GET', 'application/applications', SRR['app_uuid']),
    ])
    my_app = create_app()
    assert my_app.create_application({'option': 'option'}) == (None, rest_error_message('', 'application/applications'))
    assert my_app.create_application({'option': 'option'}) == (
        None, 'calling: application/applications: got Unexpected argument: exclude_aggregates.  "exclude_aggregates" requires ONTAP 9.9.1 GA or later.')

    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.create_application({'option': 'option'}) ==\
        (None, 'function create_application should not be called when application uuid is set: test_uuid.')


def test_successfully_patch_application():
    register_responses([
        ('GET', 'application/applications', SRR['app_uuid']),
        ('PATCH', 'application/applications/test_uuid', SRR['success']),
    ])
    my_app = create_app()
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.patch_application({'option': 'option'}) == ({}, None)


def test_negative_patch_application():
    register_responses([
        # first call, patch fails if app does not exist
        # second call
        ('GET', 'application/applications', SRR['app_uuid']),
        ('PATCH', 'application/applications/test_uuid', SRR['generic_error']),
    ])
    my_app = create_app()
    assert my_app.patch_application({'option': 'option'}) == (None, 'function should not be called before application uuid is set.')

    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.patch_application({'option': 'option'}) == (None, rest_error_message('', 'application/applications/test_uuid'))


def test_successfully_delete_application():
    register_responses([
        ('GET', 'application/applications', SRR['app_uuid']),
        ('DELETE', 'application/applications/test_uuid', SRR['success']),
    ])
    my_app = create_app()
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.delete_application() == ({}, None)


def test_negative_delete_application():
    register_responses([
        # first call, delete fails if app does not exist
        # second call
        ('GET', 'application/applications', SRR['app_uuid']),
        ('DELETE', 'application/applications/test_uuid', SRR['generic_error']),
    ])
    my_app = create_app()
    assert my_app.delete_application() == (None, 'function should not be called before application uuid is set.')

    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.delete_application() == (None, rest_error_message('', 'application/applications/test_uuid'))


def test_successfully_get_application_components():
    register_responses([
        ('GET', 'application/applications', SRR['app_uuid']),
        ('GET', 'application/applications/test_uuid/components', SRR['zero_records']),
        ('GET', 'application/applications/test_uuid/components', SRR['app_components']),
        ('GET', 'application/applications/test_uuid/components', SRR['app_components']),
    ])
    my_app = create_app()
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.get_application_components() == (None, None)
    assert my_app.get_application_components() == (SRR['app_components'][1]['records'], None)
    assert my_app.get_application_components() == (SRR['app_components'][1]['records'], None)


def test_negative_get_application_components():
    register_responses([
        ('GET', 'application/applications', SRR['app_uuid']),
        ('GET', 'application/applications/test_uuid/components', SRR['generic_error']),
    ])
    my_app = create_app()
    assert my_app.get_application_components() == (None, 'function should not be called before application uuid is set.')
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.get_application_components() == (None, rest_error_message('', 'application/applications/test_uuid/components'))


def test_successfully_get_application_component_uuid():
    register_responses([
        ('GET', 'application/applications', SRR['app_uuid']),
        ('GET', 'application/applications/test_uuid/components', SRR['zero_records']),
        ('GET', 'application/applications/test_uuid/components', SRR['app_components']),
        ('GET', 'application/applications/test_uuid/components', SRR['app_components']),
    ])
    my_app = create_app()
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.get_application_component_uuid() == (None, None)
    assert my_app.get_application_component_uuid() == ('component_uuid', None)
    assert my_app.get_application_component_uuid() == ('component_uuid', None)


def test_negative_get_application_component_uuid():
    register_responses([
        ('GET', 'application/applications', SRR['app_uuid']),
        ('GET', 'application/applications/test_uuid/components', SRR['generic_error']),
    ])
    my_app = create_app()
    assert my_app.get_application_component_uuid() == (None, 'function should not be called before application uuid is set.')
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.get_application_component_uuid() == (None, rest_error_message('', 'application/applications/test_uuid/components'))


def test_successfully_get_application_component_details():
    register_responses([
        ('GET', 'application/applications', SRR['app_uuid']),
        ('GET', 'application/applications/test_uuid/components', SRR['app_components']),
        ('GET', 'application/applications/test_uuid/components/component_uuid', SRR['app_components']),
    ])
    my_app = create_app()
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.get_application_component_details() == (SRR['app_components'][1]['records'][0], None)


def test_negative_get_application_component_details():
    register_responses([
        # first call, fail as UUID not set
        # second call, fail to retrieve UUID
        ('GET', 'application/applications', SRR['app_uuid']),
        ('GET', 'application/applications/test_uuid/components', SRR['zero_records']),
        # fail to retrieve UUID
        ('GET', 'application/applications/test_uuid/components', SRR['generic_error']),
        # fail to retrieve component_details
        ('GET', 'application/applications/test_uuid/components', SRR['app_components']),
        ('GET', 'application/applications/test_uuid/components/component_uuid', SRR['generic_error']),
    ])
    my_app = create_app()
    assert my_app.get_application_component_details() == (None, 'function should not be called before application uuid is set.')
    # second call, set UUI first
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.get_application_component_details() == (None, 'no component for application application_name')
    # third call
    assert my_app.get_application_component_details() == (None, rest_error_message('', 'application/applications/test_uuid/components'))
    # fourth call
    assert my_app.get_application_component_details() == (None, rest_error_message('', 'application/applications/test_uuid/components/component_uuid'))


def test_successfully_get_application_component_backing_storage():
    register_responses([
        ('GET', 'application/applications', SRR['app_uuid']),
        ('GET', 'application/applications/test_uuid/components', SRR['app_components']),
        ('GET', 'application/applications/test_uuid/components/component_uuid', SRR['app_component_details']),
    ])
    my_app = create_app()
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.get_application_component_backing_storage() == ('backing_storage', None)


def test_negative_get_application_component_backing_storage():
    register_responses([
        # first call, fail as UUID not set
        # second call, fail to retrieve UUID
        ('GET', 'application/applications', SRR['app_uuid']),
        ('GET', 'application/applications/test_uuid/components', SRR['zero_records']),
        # fail to retrieve UUID
        ('GET', 'application/applications/test_uuid/components', SRR['generic_error']),
        # fail to retrieve component_backing_storage
        ('GET', 'application/applications/test_uuid/components', SRR['app_components']),
        ('GET', 'application/applications/test_uuid/components/component_uuid', SRR['generic_error']),
    ])
    my_app = create_app()
    assert my_app.get_application_component_backing_storage() == (None, 'function should not be called before application uuid is set.')
    # second call, set UUI first
    assert my_app.get_application_uuid() == ('test_uuid', None)
    assert my_app.get_application_component_backing_storage() == (None, 'no component for application application_name')
    # third call
    assert my_app.get_application_component_backing_storage() == (None, rest_error_message('', 'application/applications/test_uuid/components'))
    # fourth call
    assert my_app.get_application_component_backing_storage() == (None, rest_error_message('', 'application/applications/test_uuid/components/component_uuid'))


def test_create_application_body():
    my_app = create_app()
    body = {
        'name': my_app.app_name,
        'svm': {'name': my_app.svm_name},
        'smart_container': True,
        'tname': 'tbody'
    }
    assert my_app.create_application_body('tname', 'tbody') == (body, None)
    body['smart_container'] = False
    assert my_app.create_application_body('tname', 'tbody', False) == (body, None)
    assert my_app.create_application_body('tname', 'tbody', 'False') == (None, 'expecting bool value for smart_container, got: False')
