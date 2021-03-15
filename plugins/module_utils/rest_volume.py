# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c) 2020, Laurent Nicolas <laurentn@netapp.com>
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

""" Support functions for NetApp ansible modules

    Provides common processing for responses and errors from REST calls
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import ansible_collections.netapp.ontap.plugins.module_utils.rest_response_helpers as rrh


def get_volumes(rest_api, vserver=None, name=None):
    api = 'storage/volumes/'
    query = dict()
    if vserver is not None:
        query['svm.name'] = vserver
    if name is not None:
        query['name'] = name
    if not query:
        query = None
    response, error = rest_api.get(api, query)
    volumes, error = rrh.check_for_0_or_more_records(api, response, error)
    return volumes, error


def get_volume(rest_api, vserver, name, fields=None):
    api = 'storage/volumes/'
    query = dict(name=name)
    query['svm.name'] = vserver
    if fields is not None:
        query['fields'] = fields
    response, error = rest_api.get(api, query)
    volume, error = rrh.check_for_0_or_1_records(api, response, error, query)
    return volume, error


def delete_volume(rest_api, uuid):
    api = 'storage/volumes/%s' % uuid
    # without return_timeout, REST returns immediately with a 202 and a job link
    #   but the job status is 'running'
    # with return_timeout, REST returns quickly with a 200 and a job link
    #   and the job status is 'success'
    # I guess that if the operation was taking more than 30 seconds, we'd get a 202 with 'running'.
    # I tried with a value of 1 second, I got a 202, but the job showed as complete (success) :)
    query = dict(return_timeout=30)
    response, error = rest_api.delete(api, params=query)
    response, error = rrh.check_for_error_and_job_results(api, response, error, rest_api, increment=20)
    return response, error


def patch_volume(rest_api, uuid, body, query=None):
    api = 'storage/volumes/%s' % uuid
    # see delete_volume for async and sync operations and status codes
    params = dict(return_timeout=30)
    if query is not None:
        params.update(query)
    response, error = rest_api.patch(api, body=body, params=params)
    response, error = rrh.check_for_error_and_job_results(api, response, error, rest_api, increment=20)
    return response, error
