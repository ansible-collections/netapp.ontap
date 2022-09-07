# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# Author: Laurent Nicolas, laurentn@netapp.com

""" unit tests for Ansible modules for ONTAP:
    utility to build REST responses and errors, and register them to use them in testcases.

    1) at the module level, define the REST responses:
       SRR = rest_responses()        if you're only interested in the default ones: 'empty', 'error', ...
       SRR = rest_responses(dict)    to use the default ones and augment them:
                                                a key identifies a response name, and the value is a tuple.

    3) in each test function, create a list of (event, response) using rest_response
        def test_create_aggr():
            register_responses([
                ('GET', 'cluster', SRR['is_rest']),
                ('POST', 'storage/aggregates', SRR['empty_good'])
            ])

    See ansible_collections/netapp/ontap/tests/unit/plugins/modules/test_na_ontap_aggregate_rest.py
    for an example.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


JOB_GET_API = ' cluster/jobs/94b6e6a7-d426-11eb-ac81-00505690980f'


def _build_job(state):
    return (200, {
        "uuid": "f03ccbb6-d8bb-11eb-ac81-00505690980f",
        "description": "job results with state: %s" % state,
        "state": state,
        "message": "job reported %s" % state
    }, None)


# name: (html_code, dict, None or error string)
# dict is translated into an xml structure, num_records is None or an integer >= 0
_DEFAULT_RESPONSES = {
    # common responses
    'is_rest': (200, {}, None),
    'is_rest_95': (200, dict(version=dict(generation=9, major=5, minor=0, full='dummy_9_5_0')), None),
    'is_rest_96': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy_9_6_0')), None),
    'is_rest_97': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy_9_7_0')), None),
    'is_rest_9_7_5': (200, dict(version=dict(generation=9, major=7, minor=5, full='dummy_9_7_5')), None),
    'is_rest_9_8_0': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy_9_8_0')), None),
    'is_rest_9_9_0': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy_9_9_0')), None),
    'is_rest_9_9_1': (200, dict(version=dict(generation=9, major=9, minor=1, full='dummy_9_9_1')), None),
    'is_rest_9_10_1': (200, dict(version=dict(generation=9, major=10, minor=1, full='dummy_9_10_1')), None),
    'is_rest_9_11_0': (200, dict(version=dict(generation=9, major=11, minor=0, full='dummy_9_11_0')), None),
    'is_rest_9_11_1': (200, dict(version=dict(generation=9, major=11, minor=1, full='dummy_9_11_1')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'success': (200, {}, None),
    'success_with_job_uuid': (200, {'job': {'_links': {'self': {'href': '/api/%s' % JOB_GET_API}}}}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'empty_records': (200, {'records': []}, None),
    'zero_records': (200, {'num_records': 0}, None),
    'one_record': (200, {'num_records': 1}, None),
    'generic_error': (400, None, "Expected error"),
    'error_record': (400, None, {'code': 6, 'message': 'Expected error'}),
    'job_generic_response_success': _build_job('success'),
    'job_generic_response_running': _build_job('running'),
    'job_generic_response_failure': _build_job('failure'),
}


def rest_error_message(error, api=None, extra='', got=None):
    if got is None:
        got = 'got Expected error.'
    msg = ('%s: ' % error) if error else ''
    msg += ('calling: %s: ' % api) if api else ''
    msg += got
    msg += extra
    return msg


class rest_responses:
    ''' return an object that behaves like a read-only dictionary
        supports [key] to read an entry, and 'in' keyword to check key existence.
    '''
    def __init__(self, adict=None, allow_override=True):
        self.responses = dict(_DEFAULT_RESPONSES.items())
        if adict:
            for key, value in adict.items():
                if not allow_override and key in self.responses:
                    raise KeyError('duplicated key: %s' % key)
                self.responses[key] = value

    def _get_response(self, name):
        try:
            return self.responses[name]
        except KeyError:
            raise KeyError('%s not registered, list of valid keys: %s' % (name, self.responses.keys()))

    def __getitem__(self, name):
        return self._get_response(name)

    def __contains__(self, name):
        return name in self.responses
