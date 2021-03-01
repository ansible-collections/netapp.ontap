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


def get_flexcache(rest_api, vserver, name, fields=None):
    api = 'storage/flexcache/flexcaches'
    query = dict(name=name)
    query['svm.name'] = vserver
    if fields is not None:
        query['fields'] = fields
    response, error = rest_api.get(api, query)
    flexcache, error = rrh.check_for_0_or_1_records(api, response, error, query)
    return flexcache, error


def delete_flexcache(rest_api, uuid, timeout=180, return_timeout=5):
    api = 'storage/flexcache/flexcaches/%s' % uuid
    # without return_timeout, REST returns immediately with a 202 and a job link
    #   but the job status is 'running'
    # with return_timeout, REST returns quickly with a 200 and a job link
    #   and the job status is 'success'
    # I guess that if the operation was taking more than 30 seconds, we'd get a 202 with 'running'.
    # I tried with a value of 1 second, I got a 202, but the job showed as complete (success) :)

    # There may be a bug in ONTAP.  If return_timeout is >= 15, the call fails with uuid not found!
    # With 5, a job is queued, and completes with success.  With a big enough value, no job is
    # queued, and the API returns in around 15 seconds with a not found error.
    query = dict(return_timeout=return_timeout)
    response, error = rest_api.delete(api, params=query)
    response, error = rrh.check_for_error_and_job_results(api, response, error, rest_api, increment=10, timeout=timeout)
    return response, error


def post_flexcache(rest_api, body, query=None, timeout=180):
    api = 'storage/flexcache/flexcaches'
    # see delete_flexcache for async and sync operations and status codes
    params = None
    if timeout > 0:
        params = dict(return_timeout=min(30, timeout))
    if query is not None:
        params.update(query)
    response, error = rest_api.post(api, body=body, params=params)
    response, error = rrh.check_for_error_and_job_results(api, response, error, rest_api, increment=20, timeout=timeout)
    return response, error


def patch_flexcache(rest_api, uuid, body, query=None, timeout=180):
    api = 'storage/flexcache/flexcaches/%s' % uuid
    # see delete_flexcache for async and sync operations and status codes
    params = dict(return_timeout=30)
    if query is not None:
        params.update(query)
    response, error = rest_api.patch(api, body=body, params=params)
    response, error = rrh.check_for_error_and_job_results(api, response, error, rest_api, increment=20, timeout=timeout)
    return response, error
