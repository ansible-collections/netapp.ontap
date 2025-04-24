# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# Author: Laurent Nicolas, laurentn@netapp.com

""" unit tests for Ansible modules for ONTAP:
    utility to build REST responses and errors, and register them to use them in testcases.

    1) at the module level, define the ZAPI responses:
       ZRR = zapi_responses()        if you're only interested in the default ones: 'empty', 'error', ...
       or
       ZRR = zapi_responses(dict)    to use the default ones and augment them:
                                     a key identifies a response name, and the value is an XML structure.

    2) create a ZAPI XML response or error using
       build_zapi_response(contents, num_records=None)
       build_zapi_error(errno, reason)

       Typically, these will be used with zapi_responses as

        ZRR = zapi_responses({
            'aggr_info': build_zapi_response(aggr_info),
            'object_store_info': build_zapi_response(object_store_info),
            'disk_info': build_zapi_response(disk_info),
        })

    3) in each test function, create a list of (event, response) using zapi_responses (and rest_responses)
        def test_create(self):
            register_responses([
                ('aggr-get-iter', ZRR['empty']),
                ('aggr-create', ZRR['empty']),
                ('aggr-get-iter', ZRR['empty']),
            ])

    See ansible_collections/netapp/ontap/tests/unit/plugins/modules/test_na_ontap_aggregate.py
    for an example.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

# name: (dict, num_records)
# dict is translated into an xml structure, num_records is None or an integer >= 0
_DEFAULT_RESPONSES = {
    'empty': ({}, None),
    'success': ({}, None),
    'no_records': ({'num-records': '0'}, None),
    'one_record_no_data': ({'num-records': '1'}, None),
    'version': ({'version': 'zapi_version'}, None),
    'cserver': ({
        'attributes-list': {
            'vserver-info': {
                'vserver-name': 'cserver'
            }
        }}, 1),
}
# name: (errno, reason)
# errno as int, reason as str
_DEFAULT_ERRORS = {
    'error': (12345, 'synthetic error for UT purpose'),
    'error_missing_api': (13005, 'Unable to find API: xxxx on data vserver')
}


def get_error_desc(error_code):
    return next((err_desc for err_num, err_desc in _DEFAULT_ERRORS.values() if err_num == error_code),
                'no registered error for %d' % error_code)


def zapi_error_message(error, error_code=12345, reason=None, addal=None):
    if reason is None:
        reason = get_error_desc(error_code)
    msg = "%s: NetApp API failed. Reason - %s:%s" % (error, error_code, reason)
    if addal:
        msg += addal
    return msg


def build_raw_xml_response(contents, num_records=None, force_dummy=False):
    top_contents = {'results': contents}
    xml, valid = build_zapi_response(top_contents)
    if valid == 'valid' and not force_dummy:
        return xml.to_string()
    return b'<xml><results status="netapp-lib is missing"/></xml>'


def build_zapi_response(contents, num_records=None):
    ''' build an XML response
        contents is translated into an xml structure
        num_records is None or an integer >= 0
    '''
    if not netapp_utils.has_netapp_lib():
        # do not report an error at init, as it breaks ansible-test checks
        return 'build_zapi_response: netapp-lib is missing', 'invalid'
    if num_records is not None:
        contents['num-records'] = str(num_records)
    response = netapp_utils.zapi.NaElement('results')
    response.translate_struct(contents)
    response.add_attr('status', 'passed')
    return (response, 'valid')


def build_zapi_error(errno, reason):
    ''' build an XML response
        errno as int
        reason as str
    '''
    if not netapp_utils.has_netapp_lib():
        return 'build_zapi_error: netapp-lib is missing', 'invalid'
    response = netapp_utils.zapi.NaElement('results')
    response.add_attr('errno', str(errno))
    response.add_attr('reason', reason)
    return (response, 'valid')


class zapi_responses:

    def __init__(self, adict=None, allow_override=True):
        self.responses = {}
        for key, value in _DEFAULT_RESPONSES.items():
            self.responses[key] = build_zapi_response(*value)
        for key, value in _DEFAULT_ERRORS.items():
            if key in self.responses:
                raise KeyError('duplicated key: %s' % key)
            self.responses[key] = build_zapi_error(*value)
        if adict:
            for key, value in adict.items():
                if not allow_override and key in self.responses:
                    raise KeyError('duplicated key: %s' % key)
                self.responses[key] = value

    def _get_response(self, name):
        try:
            value, valid = self.responses[name]
            # sanity checks for netapp-lib are deferred until the test is actually run
            if valid != 'valid':
                print("Error: Defer any runtime dereference, eg ZRR['key'], until runtime or protect dereference under has_netapp_lib().")
                raise ImportError(value)
            return value, valid
        except KeyError:
            raise KeyError('%s not registered, list of valid keys: %s' % (name, self.responses.keys()))

    def __getitem__(self, name):
        return self._get_response(name)

    def __contains__(self, name):
        return name in self.responses
