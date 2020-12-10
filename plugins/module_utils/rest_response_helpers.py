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


def api_error(api, error):
    """format error message for api error, if error is present"""
    if error is not None:
        return "calling: %s: got %s" % (api, error)
    return None


def no_response_error(api, response):
    """format error message for empty response"""
    return "calling: %s: no response %s" % (api, repr(response))


def job_error(response, error):
    """format error message for job error"""
    return "job reported error: %s, received %s" % (error, repr(response))


def unexpected_response_error(api, response, query=None):
    """format error message for reponse not matching expectations"""
    msg = "calling: %s: unexpected response %s" % (api, repr(response))
    if query:
        msg += " for query: %s" % repr(query)
    return response, msg


def check_for_0_or_1_records(api, response, error, query=None):
    """return None if no record was returned by the API
       return record if one record was returned by the API
       return error otherwise (error, no response, more than 1 record)
    """
    if error:
        if api:
            return None, api_error(api, error)
        return None, error
    if not response:
        return None, no_response_error(api, response)
    if response['num_records'] == 0:
        return None, None     # not found
    if response['num_records'] != 1:
        return unexpected_response_error(api, response, query)
    return response['records'][0], None


def check_for_0_or_more_records(api, response, error):
    """return None if no record was returned by the API
       return records if one or more records was returned by the API
       return error otherwise (error, no response)
    """
    if error:
        if api:
            return None, api_error(api, error)
        return None, error
    if not response:
        return None, no_response_error(api, response)
    if response['num_records'] == 0:
        return None, None     # not found
    return response['records'], None


def check_for_error_and_job_results(api, response, error, rest_api):
    """report first error if present
       otherwise call wait_on_job and retrieve job response or error
    """
    if error:
        error = api_error(api, error)
    elif 'job' in response:
        job_response, error = rest_api.wait_on_job(response['job'])
        if error:
            error = job_error(response, error)
        else:
            response['job_response'] = job_response
    return response, error
