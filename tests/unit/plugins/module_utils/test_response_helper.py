# Copyright (c) 2022 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils rest_generic.py - REST features '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.plugins.module_utils import rest_response_helpers

RECORD = {'key': 'value'}

RESPONSES = {
    'empty': {},
    'zero_record': {'num_records': 0},
    'empty_records': {'records': []},
    'one_record': {'records': [RECORD], 'num_records': 1},
    'one_record_no_num_records': {'records': [RECORD]},
    'one_record_no_num_records_no_records': RECORD,
    'two_records': {'records': [RECORD, RECORD], 'num_records': 2},
}


def test_check_for_0_or_1_records():
    # no records --> None
    response_in, error_in, response_out, error_out = RESPONSES['zero_record'], None, None, None
    assert rest_response_helpers.check_for_0_or_1_records('cluster', response_in, error_in) == (response_out, error_out)
    response_in, error_in, response_out, error_out = RESPONSES['empty_records'], None, None, None
    assert rest_response_helpers.check_for_0_or_1_records('cluster', response_in, error_in) == (response_out, error_out)

    # one record
    response_in, error_in, response_out, error_out = RESPONSES['one_record'], None, RECORD, None
    assert rest_response_helpers.check_for_0_or_1_records('cluster', response_in, error_in) == (response_out, error_out)
    response_in, error_in, response_out, error_out = RESPONSES['one_record_no_num_records'], None, RECORD, None
    assert rest_response_helpers.check_for_0_or_1_records('cluster', response_in, error_in) == (response_out, error_out)
    response_in, error_in, response_out, error_out = RESPONSES['one_record_no_num_records_no_records'], None, RECORD, None
    assert rest_response_helpers.check_for_0_or_1_records('cluster', response_in, error_in) == (response_out, error_out)


def test_check_for_0_or_1_records_errors():
    # bad input
    response_in, error_in, response_out, error_out = None, None, None, 'calling: cluster: no response None.'
    assert rest_response_helpers.check_for_0_or_1_records('cluster', response_in, error_in) == (response_out, error_out)
    response_in, error_in, response_out, error_out = RESPONSES['empty'], None, None, 'calling: cluster: no response {}.'
    assert rest_response_helpers.check_for_0_or_1_records('cluster', response_in, error_in) == (response_out, error_out)

    # error in
    response_in, error_in, response_out, error_out = None, 'some_error', None, 'calling: cluster: got some_error.'
    assert rest_response_helpers.check_for_0_or_1_records('cluster', response_in, error_in) == (response_out, error_out)

    # more than 1 record
    response_in, error_in, response_out, error_out = RESPONSES['two_records'], None, RESPONSES['two_records'], 'calling: cluster: unexpected response'
    response, error = rest_response_helpers.check_for_0_or_1_records('cluster', response_in, error_in)
    assert response == response_out
    assert error.startswith(error_out)
    assert 'for query' not in error
    response, error = rest_response_helpers.check_for_0_or_1_records('cluster', response_in, error_in, query=RECORD)
    assert response == response_out
    assert error.startswith(error_out)
    expected = 'for query: %s' % RECORD
    assert expected in error


def test_check_for_0_or_more_records():
    # no records --> None
    response_in, error_in, response_out, error_out = RESPONSES['zero_record'], None, None, None
    assert rest_response_helpers.check_for_0_or_more_records('cluster', response_in, error_in) == (response_out, error_out)
    response_in, error_in, response_out, error_out = RESPONSES['empty_records'], None, None, None
    assert rest_response_helpers.check_for_0_or_more_records('cluster', response_in, error_in) == (response_out, error_out)

    # one record
    response_in, error_in, response_out, error_out = RESPONSES['one_record'], None, [RECORD], None
    assert rest_response_helpers.check_for_0_or_more_records('cluster', response_in, error_in) == (response_out, error_out)
    response_in, error_in, response_out, error_out = RESPONSES['one_record_no_num_records'], None, [RECORD], None
    assert rest_response_helpers.check_for_0_or_more_records('cluster', response_in, error_in) == (response_out, error_out)

    # more than 1 record
    response_in, error_in, response_out, error_out = RESPONSES['two_records'], None, [RECORD, RECORD], None
    assert rest_response_helpers.check_for_0_or_more_records('cluster', response_in, error_in) == (response_out, error_out)


def test_check_for_0_or_more_records_errors():
    # bad input
    response_in, error_in, response_out, error_out = None, None, None, 'calling: cluster: no response None.'
    assert rest_response_helpers.check_for_0_or_more_records('cluster', response_in, error_in) == (response_out, error_out)
    response_in, error_in, response_out, error_out = RESPONSES['empty'], None, None, 'calling: cluster: no response {}.'
    assert rest_response_helpers.check_for_0_or_more_records('cluster', response_in, error_in) == (response_out, error_out)
    error = "calling: cluster: got No \"records\" key in {'key': 'value'}."
    response_in, error_in, response_out, error_out = RESPONSES['one_record_no_num_records_no_records'], None, None, error
    assert rest_response_helpers.check_for_0_or_more_records('cluster', response_in, error_in) == (response_out, error_out)

    # error in
    response_in, error_in, response_out, error_out = None, 'some_error', None, 'calling: cluster: got some_error.'
    assert rest_response_helpers.check_for_0_or_more_records('cluster', response_in, error_in) == (response_out, error_out)


class MockOntapRestAPI:
    def __init__(self, job_response=None, error=None, raise_if_called=False):
        self.job_response, self.error, self.raise_if_called = job_response, error, raise_if_called

    def wait_on_job(self, job):
        if self.raise_if_called:
            raise AttributeError('wait_on_job should not be called in this test!')
        return self.job_response, self.error


def test_check_for_error_and_job_results_no_job():
    rest_api = MockOntapRestAPI(raise_if_called=True)
    response_in, error_in, response_out, error_out = None, None, None, None
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api) == (response_out, error_out)

    response_in, error_in, response_out, error_out = 'any', None, 'any', None
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api) == (response_out, error_out)

    response = {'no_job': 'entry'}
    response_in, error_in, response_out, error_out = response, None, response, None
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api) == (response_out, error_out)


def test_check_for_error_and_job_results_with_job():
    rest_api = MockOntapRestAPI(job_response='job_response', error=None)
    response = {'job': 'job_entry'}
    expected_response = {'job': 'job_entry', 'job_response': 'job_response'}
    response_in, error_in, response_out, error_out = response, None, expected_response, None
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api) == (response_out, error_out)

    response = {'jobs': ['job_entry'], 'num_records': 1}
    expected_response = {'jobs': ['job_entry'], 'num_records': 1, 'job_response': 'job_response'}
    response_in, error_in, response_out, error_out = response, None, expected_response, None
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api) == (response_out, error_out)


def test_negative_check_for_error_and_job_results_error_in():
    rest_api = MockOntapRestAPI(raise_if_called=True)
    response_in, error_in, response_out, error_out = None, 'forced_error', None, 'calling: cluster: got forced_error.'
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api) == (response_out, error_out)
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api, raw_error=False) == (response_out, error_out)
    error_out = 'forced_error'
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api, raw_error=True) == (response_out, error_out)


def test_negative_check_for_error_and_job_results_job_error():
    rest_api = MockOntapRestAPI(job_response='job_response', error='job_error')
    response = {'job': 'job_entry'}
    response_in, error_in, response_out, error_out = response, None, response, "job reported error: job_error, received {'job': 'job_entry'}."
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api) == (response_out, error_out)
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api, raw_error=False) == (response_out, error_out)
    error_out = 'job_error'
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api, raw_error=True) == (response_out, error_out)


def test_negative_check_for_error_and_job_results_multiple_jobs_error():
    rest_api = MockOntapRestAPI(raise_if_called=True)
    response = {'jobs': 'job_entry', 'num_records': 3}
    response_in, error_in, response_out, error_out = response, None, response, "multiple jobs in progress, can't check status"
    assert rest_response_helpers.check_for_error_and_job_results('cluster', response_in, error_in, rest_api) == (response_out, error_out)
