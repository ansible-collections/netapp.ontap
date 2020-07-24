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
import time
from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible.module_utils._text import to_native

try:
    from ansible.module_utils.ansible_release import __version__ as ansible_version
except ImportError:
    ansible_version = 'unknown'

COLLECTION_VERSION = "20.8.0"

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
        username=dict(required=False, type='str', aliases=['user']),
        password=dict(required=False, type='str', aliases=['pass'], no_log=True),
        https=dict(required=False, type='bool', default=False),
        validate_certs=dict(required=False, type='bool', default=True),
        http_port=dict(required=False, type='int'),
        ontapi=dict(required=False, type='int'),
        use_rest=dict(required=False, type='str', default='auto'),
        feature_flags=dict(required=False, type='dict', default=dict()),
        cert_filepath=dict(required=False, type='str'),
        key_filepath=dict(required=False, type='str'),
    )


def has_feature(module, feature_name):
    feature = get_feature(module, feature_name)
    if isinstance(feature, bool):
        return feature
    module.fail_json(msg="Error: expected bool type for feature flag: %s" % feature_name)


def get_feature(module, feature_name):
    ''' if the user has configured the feature, use it
        otherwise, use our default
    '''
    default_flags = dict(
        deprecation_warning=True,
        check_required_params_for_none=True,
        sanitize_xml=True,
        sanitize_code_points=[8]     # unicode values, 8 is backspace
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


def set_auth_method(module, username, password, cert_filepath, key_filepath):
    error = None
    if password is None and username is None:
        if cert_filepath is None and key_filepath is not None:
            error = 'Error: cannot have a key file without a cert file'
        elif cert_filepath is None:
            error = 'Error: ONTAP module requires username/password or SSL certificate file(s)'
        elif key_filepath is None:
            auth_method = 'single_cert'
        else:
            auth_method = 'cert_key'
    elif password is not None and username is not None:
        if cert_filepath is not None or key_filepath is not None:
            error = 'Error: cannot have both basic authentication (username/password) ' +\
                    'and certificate authentication (cert/key files)'
        else:
            auth_method = 'basic_auth'
    else:
        error = 'Error: username and password have to be provided together'
        if cert_filepath is not None or key_filepath is not None:
            error += ' and cannot be used with cert or key files'
    if error:
        module.fail_json(msg=error)
    return auth_method


def setup_na_ontap_zapi(module, vserver=None, wrap_zapi=False):
    hostname = module.params['hostname']
    username = module.params['username']
    password = module.params['password']
    https = module.params['https']
    validate_certs = module.params['validate_certs']
    port = module.params['http_port']
    version = module.params['ontapi']
    cert_filepath = module.params['cert_filepath']
    key_filepath = module.params['key_filepath']
    auth_method = set_auth_method(module, username, password, cert_filepath, key_filepath)

    if HAS_NETAPP_LIB:
        # set up zapi
        if auth_method != 'basic_auth':
            # override NaServer in netapp-lib to enable certificate authentication
            server = OntapZAPICx(hostname, module=module, username=username, password=password,
                                 validate_certs=validate_certs, cert_filepath=cert_filepath,
                                 key_filepath=key_filepath, style=zapi.NaServer.STYLE_CERTIFICATE)
            # SSL certificate authentication requires SSL
            https = True
        elif wrap_zapi:
            server = OntapZAPICx(hostname, module=module, username=username, password=password,
                                 validate_certs=validate_certs)
        else:
            # legacy netapp-lib
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


def classify_zapi_exception(error):
    ''' return type of error '''
    try:
        # very unlikely to fail, but don't take any chance
        err_code = int(error.code)
    except (AttributeError, ValueError):
        err_code = 0
    try:
        # very unlikely to fail, but don't take any chance
        err_msg = error.message
    except AttributeError:
        err_msg = ""
    if err_code == 13005 and err_msg.startswith('Unable to find API:') and 'data vserver' in err_msg:
        return 'missing_vserver_api_error', 'Most likely running a cluster level API as vserver: %s' % to_native(error)
    if err_code == 13001 and err_msg.startswith("RPC: Couldn't make connection"):
        return 'rpc_error', to_native(error)
    return "other_error", to_native(error)


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


if HAS_NETAPP_LIB:
    class OntapZAPICx(zapi.NaServer):
        def __init__(self, hostname=None, server_type=zapi.NaServer.SERVER_TYPE_FILER,
                     transport_type=zapi.NaServer.TRANSPORT_TYPE_HTTP,
                     style=zapi.NaServer.STYLE_LOGIN_PASSWORD, username=None,
                     password=None, port=None, trace=False, module=None,
                     cert_filepath=None, key_filepath=None, validate_certs=None):
            # python 2.x syntax, but works for python 3 as well
            super(OntapZAPICx, self).__init__(hostname, server_type=server_type,
                                              transport_type=transport_type,
                                              style=style, username=username,
                                              password=password, port=port, trace=trace)
            self.cert_filepath = cert_filepath
            self.key_filepath = key_filepath
            self.validate_certs = validate_certs
            self.module = module

        def _create_certificate_auth_handler(self):
            import ssl
            try:
                context = ssl.create_default_context()
            except AttributeError as exc:
                msg = 'SSL certificate authentication requires python 2.7 or later.'
                msg += '  More info: %s' % repr(exc)
                self.module.fail_json(msg=msg)
            if not self.validate_certs:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            try:
                context.load_cert_chain(self.cert_filepath, keyfile=self.key_filepath)
            except IOError as exc:      # python 2.7 does not have FileNotFoundError
                msg = 'Cannot load SSL certificate, check files exist.'
                msg += '  More info: %s' % repr(exc)
                self.module.fail_json(msg=msg)
            return zapi.urllib.request.HTTPSHandler(context=context)

        def _parse_response(self, response):
            ''' handling XML parsing exception '''
            try:
                return super(OntapZAPICx, self)._parse_response(response)
            except zapi.etree.XMLSyntaxError as exc:
                if has_feature(self.module, 'sanitize_xml'):
                    # some ONTAP CLI commands return BEL on error
                    new_response = response.replace(b'\x07\n', b'')
                    # And 9.1 uses \r\n rather than \n !
                    new_response = new_response.replace(b'\x07\r\n', b'')
                    # And 9.7 may send backspaces
                    for code_point in get_feature(self.module, 'sanitize_code_points'):
                        if bytes([8]) == b'\x08':   # python 3
                            byte = bytes([code_point])
                        elif chr(8) == b'\x08':     # python 2
                            byte = chr(code_point)
                        else:                       # very unlikely, noop
                            byte = b'.'
                        new_response = new_response.replace(byte, b'.')
                    try:
                        return super(OntapZAPICx, self)._parse_response(new_response)
                    except Exception:
                        pass
                try:
                    # report first exception, but include full response
                    exc.msg += ".  Received: %s" % response
                except Exception:
                    # in case the response is very badly formatted, ignore it
                    pass
                raise exc


class OntapRestAPI(object):
    def __init__(self, module, timeout=60):
        self.module = module
        self.username = self.module.params['username']
        self.password = self.module.params['password']
        self.hostname = self.module.params['hostname']
        self.use_rest = self.module.params['use_rest'].lower()
        self.cert_filepath = self.module.params['cert_filepath']
        self.key_filepath = self.module.params['key_filepath']
        self.verify = self.module.params['validate_certs']
        self.timeout = timeout
        port = self.module.params['http_port']
        if port is None:
            self.url = 'https://' + self.hostname + '/api/'
        else:
            self.url = 'https://%s:%d/api/' % (self.hostname, port)
        self.errors = list()
        self.debug_logs = list()
        self.auth_method = set_auth_method(self.module, self.username, self.password, self.cert_filepath, self.key_filepath)
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

        if self.auth_method == 'single_cert':
            kwargs = dict(cert=self.cert_filepath)
        elif self.auth_method == 'cert_key':
            kwargs = dict(cert=(self.cert_filepath, self.key_filepath))
        elif self.auth_method == 'basic_auth':
            kwargs = dict(auth=(self.username, self.password))
        else:
            raise KeyError(self.auth_method)

        try:
            response = requests.request(method, url, verify=self.verify, params=params,
                                        timeout=self.timeout, json=json, headers=headers, **kwargs)
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

    def wait_on_job(self, job, timeout=600, increment=60):
        try:
            url = job['_links']['self']['href'].split('api/')[1]
        except Exception as err:
            self.log_error(0, 'URL Incorrect format: %s\n Job: %s' % (err, job))
        # Expecting job to be in the following format
        """
        {'job':
            {'uuid': 'fde79888-692a-11ea-80c2-005056b39fe7',
            '_links':
                {'self':
                    {'href': '/api/cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7'}
                }
            }
        }
        """
        keep_running = True
        error = None
        message = None
        runtime = 0
        retries = 0
        max_retries = 3
        while keep_running:
            # Will run every every <increment> seconds for <timeout> seconds
            job_json, job_error = self.get(url, None)
            if job_error:
                error = job_error
                retries += 1
                if retries > max_retries:
                    self.log_error(0, 'Job error: Reach max retries.')
                    break
            else:
                retries = 0
                # a job looks like this
                """
                {
                  "uuid": "cca3d070-58c6-11ea-8c0c-005056826c14",
                  "description": "POST /api/cluster/metrocluster",
                  "state": "failure",
                  "message": "There are not enough disks in Pool1.",
                  "code": 2432836,
                  "start_time": "2020-02-26T10:35:44-08:00",
                  "end_time": "2020-02-26T10:47:38-08:00",
                  "_links": {
                    "self": {
                      "href": "/api/cluster/jobs/cca3d070-58c6-11ea-8c0c-005056826c14"
                    }
                  }
                }
                """
                message = job_json['message']
                if job_json['state'] != 'running':
                    keep_running = False
                else:
                    # Would like to post a message to user (not sure how)
                    if runtime >= timeout:
                        keep_running = False
                        if job_json['state'] != 'success':
                            self.log_error(0, 'Timeout error: Process still running')
            if keep_running:
                time.sleep(increment)
                runtime += increment
        return message, error

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
        if self.use_rest not in ['always', 'auto', 'never']:
            error = "use_rest must be one of: never, always, auto. Got: '%s'" % self.use_rest
            return False, error
        if self.use_rest == "always":
            if used_unsupported_rest_properties:
                error = "REST API currently does not support '%s'" % \
                        ', '.join(used_unsupported_rest_properties)
                return True, error
            else:
                return True, None
        if self.use_rest == 'never' or used_unsupported_rest_properties:
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
