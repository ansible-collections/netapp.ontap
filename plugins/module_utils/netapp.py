# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c) 2017, Sumit Kumar <sumit4@netapp.com>
# Copyright (c) 2017, Michael Price <michael.price@netapp.com>
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

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
from ansible.module_utils.basic import AnsibleModule, missing_required_lib

try:
    from ansible.module_utils.ansible_release import __version__ as ansible_version
except ImportError:
    ansible_version = 'unknown'

COLLECTION_VERSION = "20.6.0"

try:
    from netapp_lib.api.zapi import zapi
    HAS_NETAPP_LIB = True
except ImportError:
    HAS_NETAPP_LIB = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

import ssl
try:
    from urlparse import urlparse, urlunparse
except ImportError:
    from urllib.parse import urlparse, urlunparse


HAS_SF_SDK = False
SF_BYTE_MAP = dict(
    # Management GUI displays 1024 ** 3 as 1.1 GB, thus use 1000.
    bytes=1,
    b=1,
    kb=1000,
    mb=1000 ** 2,
    gb=1000 ** 3,
    tb=1000 ** 4,
    pb=1000 ** 5,
    eb=1000 ** 6,
    zb=1000 ** 7,
    yb=1000 ** 8
)

POW2_BYTE_MAP = dict(
    # Here, 1 kb = 1024
    bytes=1,
    b=1,
    kb=1024,
    mb=1024 ** 2,
    gb=1024 ** 3,
    tb=1024 ** 4,
    pb=1024 ** 5,
    eb=1024 ** 6,
    zb=1024 ** 7,
    yb=1024 ** 8
)

ERROR_MSG = dict(
    no_cserver='This module is expected to run as cluster admin'
)

try:
    from solidfire.factory import ElementFactory
    from solidfire.custom.models import TimeIntervalFrequency
    from solidfire.models import Schedule, ScheduleInfo

    HAS_SF_SDK = True
except Exception:
    HAS_SF_SDK = False


def has_netapp_lib():
    return HAS_NETAPP_LIB


def has_sf_sdk():
    return HAS_SF_SDK


def na_ontap_host_argument_spec():

    return dict(
        hostname=dict(required=True, type='str'),
        username=dict(required=True, type='str', aliases=['user']),
        password=dict(required=True, type='str', aliases=['pass'], no_log=True),
        https=dict(required=False, type='bool', default=False),
        validate_certs=dict(required=False, type='bool', default=True),
        http_port=dict(required=False, type='int'),
        ontapi=dict(required=False, type='int'),
        use_rest=dict(required=False, type='str', default='Auto', choices=['Never', 'Always', 'Auto']),
        feature_flags=dict(required=False, type='dict', default=dict())
    )


def has_feature(module, feature_name):
    ''' if the user has configured the feature, use it
        otherwise, use our default
    '''
    default_flags = dict(
        deprecation_warning=True,
        check_required_params_for_none=True
    )

    if feature_name in module.params['feature_flags']:
        return module.params['feature_flags'][feature_name]
    if feature_name in default_flags:
        return default_flags[feature_name]
    module.fail_json(msg="Internal error: unexpected feature flag: %s" % feature_name)


def create_sf_connection(module, port=None):
    hostname = module.params['hostname']
    username = module.params['username']
    password = module.params['password']

    if HAS_SF_SDK and hostname and username and password:
        try:
            return_val = ElementFactory.create(hostname, username, password, port=port)
            return return_val
        except Exception:
            raise Exception("Unable to create SF connection")
    else:
        module.fail_json(msg="the python SolidFire SDK module is required")


def setup_na_ontap_zapi(module, vserver=None):
    hostname = module.params['hostname']
    username = module.params['username']
    password = module.params['password']
    https = module.params['https']
    validate_certs = module.params['validate_certs']
    port = module.params['http_port']
    version = module.params['ontapi']

    if HAS_NETAPP_LIB:
        # set up zapi
        server = zapi.NaServer(hostname)
        server.set_username(username)
        server.set_password(password)
        if vserver:
            server.set_vserver(vserver)
        if version:
            minor = version
        else:
            minor = 110
        server.set_api_version(major=1, minor=minor)
        # default is HTTP
        if https:
            if port is None:
                port = 443
            transport_type = 'HTTPS'
            # HACK to bypass certificate verification
            if validate_certs is False:
                if not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
                    ssl._create_default_https_context = ssl._create_unverified_context
        else:
            if port is None:
                port = 80
            transport_type = 'HTTP'
        server.set_transport_type(transport_type)
        server.set_port(port)
        server.set_server_type('FILER')
        return server
    else:
        module.fail_json(msg="the python NetApp-Lib module is required")


def ems_log_event(source, server, name="Ansible", id="12345", version=COLLECTION_VERSION,
                  category="Information", event="setup", autosupport="false"):
    ems_log = zapi.NaElement('ems-autosupport-log')
    # Host name invoking the API.
    ems_log.add_new_child("computer-name", name)
    # ID of event. A user defined event-id, range [0..2^32-2].
    ems_log.add_new_child("event-id", id)
    # Name of the application invoking the API.
    ems_log.add_new_child("event-source", source)
    # Version of application invoking the API.
    ems_log.add_new_child("app-version", version)
    # Application defined category of the event.
    ems_log.add_new_child("category", category)
    # Description of event to log. An application defined message to log.
    ems_log.add_new_child("event-description", event)
    ems_log.add_new_child("log-level", "6")
    ems_log.add_new_child("auto-support", autosupport)
    server.invoke_successfully(ems_log, True)


def get_cserver_zapi(server):
    ''' returns None if not run on the management or cluster IP '''
    vserver_info = zapi.NaElement('vserver-get-iter')
    query_details = zapi.NaElement.create_node_with_children('vserver-info', **{'vserver-type': 'admin'})
    query = zapi.NaElement('query')
    query.add_child_elem(query_details)
    vserver_info.add_child_elem(query)
    result = server.invoke_successfully(vserver_info,
                                        enable_tunneling=False)
    attribute_list = result.get_child_by_name('attributes-list')
    if attribute_list is not None:
        vserver_list = attribute_list.get_child_by_name('vserver-info')
        if vserver_list is not None:
            return vserver_list.get_child_content('vserver-name')
    return None


def get_cserver(connection, is_rest=False):
    if not is_rest:
        return get_cserver_zapi(connection)

    params = {'fields': 'type'}
    api = "private/cli/vserver"
    json, error = connection.get(api, params)
    if json is None or error is not None:
        # exit if there is an error or no data
        return None
    vservers = json.get('records')
    if vservers is not None:
        for vserver in vservers:
            if vserver['type'] == 'admin':     # cluster admin
                return vserver['vserver']
        if len(vservers) == 1:                  # assume vserver admin
            return vservers[0]['vserver']

    return None


class OntapRestAPI(object):
    def __init__(self, module, timeout=60):
        self.module = module
        self.username = self.module.params['username']
        self.password = self.module.params['password']
        self.hostname = self.module.params['hostname']
        self.use_rest = self.module.params['use_rest']
        self.verify = self.module.params['validate_certs']
        self.timeout = timeout
        port = self.module.params['http_port']
        if port is None:
            self.url = 'https://' + self.hostname + '/api/'
        else:
            self.url = 'https://%s:%d/api/' % (self.hostname, port)
        self.errors = list()
        self.debug_logs = list()
        self.check_required_library()

    def check_required_library(self):
        if not HAS_REQUESTS:
            self.module.fail_json(msg=missing_required_lib('requests'))

    def send_request(self, method, api, params, json=None, return_status_code=False, accept=None,
                     vserver_name=None, vserver_uuid=None):
        ''' send http request and process reponse, including error conditions '''
        url = self.url + api
        status_code = None
        content = None
        json_dict = None
        json_error = None
        error_details = None
        headers = None
        if accept is not None or vserver_name is not None or vserver_uuid is not None:
            headers = dict()
            # accept is used to turn on/off HAL linking
            if accept is not None:
                headers['accept'] = accept
            # vserver tunneling using vserver name and/or UUID
            if vserver_name is not None:
                headers['X-Dot-SVM-Name'] = vserver_name
            if vserver_uuid is not None:
                headers['X-Dot-SVM-UUID'] = vserver_uuid

        def get_json(response):
            ''' extract json, and error message if present '''
            try:
                json = response.json()
            except ValueError:
                return None, None
            error = json.get('error')
            return json, error

        try:
            response = requests.request(method, url, verify=self.verify, auth=(self.username, self.password),
                                        params=params, timeout=self.timeout, json=json, headers=headers)
            content = response.content  # for debug purposes
            status_code = response.status_code
            # If the response was successful, no Exception will be raised
            response.raise_for_status()
            json_dict, json_error = get_json(response)
        except requests.exceptions.HTTPError as err:
            __, json_error = get_json(response)
            if json_error is None:
                self.log_error(status_code, 'HTTP error: %s' % err)
                error_details = str(err)
            # If an error was reported in the json payload, it is handled below
        except requests.exceptions.ConnectionError as err:
            self.log_error(status_code, 'Connection error: %s' % err)
            error_details = str(err)
        except Exception as err:
            self.log_error(status_code, 'Other error: %s' % err)
            error_details = str(err)
        if json_error is not None:
            self.log_error(status_code, 'Endpoint error: %d: %s' % (status_code, json_error))
            error_details = json_error
        self.log_debug(status_code, content)
        if not json_dict and method == 'OPTIONS':
            # OPTIONS provides the list of supported verbs
            json_dict['Allow'] = response.headers['Allow']
        if return_status_code:
            return status_code, json_dict, error_details
        return json_dict, error_details

    def get(self, api, params):
        method = 'GET'
        return self.send_request(method, api, params)

    def post(self, api, data, params=None):
        method = 'POST'
        return self.send_request(method, api, params, json=data)

    def patch(self, api, data, params=None):
        method = 'PATCH'
        return self.send_request(method, api, params, json=data)

    def delete(self, api, data, params=None):
        method = 'DELETE'
        return self.send_request(method, api, params, json=data)

    def options(self, api, params=None):
        method = 'OPTIONS'
        return self.send_request(method, api, params)

    def _is_rest(self, used_unsupported_rest_properties=None):
        if self.use_rest == "Always":
            if used_unsupported_rest_properties:
                error = "REST API currently does not support '%s'" % \
                        ', '.join(used_unsupported_rest_properties)
                return True, error
            else:
                return True, None
        if self.use_rest == 'Never' or used_unsupported_rest_properties:
            # force ZAPI if requested or if some parameter requires it
            return False, None
        method = 'HEAD'
        api = 'svm/svms'
        status_code, dummy, error = self.send_request(method, api, params=None, return_status_code=True)
        if status_code == 200:
            return True, None
        self.log_error(status_code, str(error))
        return False, None

    def is_rest(self, used_unsupported_rest_properties=None):
        ''' only return error if there is a reason to '''
        use_rest, error = self._is_rest(used_unsupported_rest_properties)
        if used_unsupported_rest_properties is None:
            return use_rest
        return use_rest, error

    def log_error(self, status_code, message):
        self.errors.append(message)
        self.debug_logs.append((status_code, message))

    def log_debug(self, status_code, content):
        self.debug_logs.append((status_code, content))

    def write_to_file(self, tag, data=None, filepath=None, append=True):
        '''
        This function is only for debug purposes, all calls to write_to_file should be removed
        before submitting.
        If data is None, tag is considered as data
        else tag is a label, and data is data.
        '''
        if filepath is None:
            filepath = '/tmp/ontap_log'
        if append:
            mode = 'a'
        else:
            mode = 'w'
        with open(filepath, mode) as f:
            if data is not None:
                f.write("%s: %s\n" % (str(tag), str(data)))
            else:
                f.write(str(tag))
                f.write('\n')

    def write_errors_to_file(self, tag=None, filepath=None, append=True):
        if tag is None:
            tag = 'Error'
        for error in self.errors:
            self.write_to_file(tag, error, filepath, append)
            if not append:
                append = True

    def write_debug_log_to_file(self, tag=None, filepath=None, append=True):
        if tag is None:
            tag = 'Debug'
        for status_code, message in self.debug_logs:
            self.write_to_file(tag, status_code, filepath, append)
            if not append:
                append = True
            self.write_to_file(tag, message, filepath, append)
