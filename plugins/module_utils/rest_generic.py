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

""" Support functions for NetApp ansible modules

    Provides common processing for responses and errors from REST calls
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import ansible_collections.netapp.ontap.plugins.module_utils.rest_response_helpers as rrh


def get_one_record(rest_api, api, query=None, fields=None):
    if fields is not None and query is None:
        query = {}
    if fields is not None:
        query['fields'] = fields
    response, error = rest_api.get(api, query)
    record, error = rrh.check_for_0_or_1_records(api, response, error, query)
    return record, error


def get_0_or_more_records(rest_api, api, query=None, fields=None):
    if fields is not None and query is None:
        query = {}
    if fields is not None:
        query['fields'] = fields
    response, error = rest_api.get(api, query)
    records, error = rrh.check_for_0_or_more_records(api, response, error)
    return records, error


def post_async(rest_api, api, body, query=None, timeout=30, job_timeout=30):
    # see delete_async for async and sync operations and status codes
    params = {} if query else None
    if timeout > 0:
        params = dict(return_timeout=timeout)
    if query is not None:
        params.update(query)
    response, error = rest_api.post(api, body=body, params=params)
    increment = max(job_timeout / 6, 5)
    response, error = rrh.check_for_error_and_job_results(api, response, error, rest_api, increment=increment, timeout=job_timeout)
    return response, error


def patch_async(rest_api, api, uuid_or_name, body, query=None, timeout=30, job_timeout=30):
    # cluster does not use uuid or name
    api = '%s/%s' % (api, uuid_or_name) if uuid_or_name is not None else api
    # see delete_async for async and sync operations and status codes
    params = {} if query else None
    if timeout > 0:
        params = dict(return_timeout=timeout)
    if query is not None:
        params.update(query)
    response, error = rest_api.patch(api, body=body, params=params)
    increment = max(job_timeout / 6, 5)
    response, error = rrh.check_for_error_and_job_results(api, response, error, rest_api, increment=increment, timeout=job_timeout)
    return response, error


def delete_async(rest_api, api, uuid, timeout=30, job_timeout=30):
    api = '%s/%s' % (api, uuid)
    # without return_timeout, REST returns immediately with a 202 and a job link
    #   but the job status is 'running'
    # with return_timeout, REST returns quickly with a 200 and a job link
    #   and the job status is 'success'
    params = None
    if timeout > 0:
        params = dict(return_timeout=timeout)
    response, error = rest_api.delete(api, params=params)
    increment = max(job_timeout / 6, 5)
    response, error = rrh.check_for_error_and_job_results(api, response, error, rest_api, increment=increment, timeout=job_timeout)
    return response, error
