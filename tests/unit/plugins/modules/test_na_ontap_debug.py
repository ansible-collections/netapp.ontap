# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP debug Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_debug \
    import NetAppONTAPDebug as my_module, main as uut_main      # module under test
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    assert_no_warnings, call_main, create_and_apply, create_module, expect_and_capture_ansible_exception, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_error, zapi_responses

# not available on 2.6 anymore
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

DEFAULT_ARGS = {
    'hostname': '10.10.10.10',
    'username': 'admin',
    'https': 'true',
    'validate_certs': 'false',
    'password': 'password',
    'vserver': 'vserver',
}

# REST API canned responses when mocking send_request
SRR = rest_responses({
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy_9_8_0')), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'one_vserver_record': (200, {
        "records": [{
            'name': 'vserver1',
            'ip_interfaces': [
                dict(services=['management'])],
        }],
        'num_records': 1
    }, None),
    'one_user_record': (200, {
        "records": [{
            'name': 'user1',
            'applications': [
                dict(application='http'),
                dict(application='ontapi'),
            ],
            'locked': False,
            'owner': {'name': 'vserver'}
        }],
        'num_records': 1
    }, None),
    'one_user_record_admin': (200, {
        "records": [{
            'name': 'user1',
            'applications': [
                dict(application='http'),
                dict(application='ontapi'),
            ],
            'locked': False,
            'owner': {'name': 'vserver'},
            'role': {'name': 'admin'}
        }],
        'num_records': 1
    }, None),
    'ConnectTimeoutError': (400, None, "Connection timed out"),
    'Name or service not known': (400, None, "Name or service not known"),
    'not_authorized': (400, None, "not authorized for that command"),
}, allow_override=False)

ZRR = zapi_responses({
    'ConnectTimeoutError': build_zapi_error('123', 'ConnectTimeoutError'),
    'Name or service not known': build_zapi_error('123', 'Name or service not known'),
}, allow_override=False)


if netapp_utils.has_netapp_lib():
    REST_ZAPI_FLOW = [
        ('system-get-version', ZRR['version']),                 # get version
        ('GET', 'cluster', SRR['is_rest_9_8']),                 # get_version
        ('vserver-get-iter', ZRR['cserver']),                   # for EMS event
        ('ems-autosupport-log', ZRR['success']),                # EMS log
    ]
else:
    REST_ZAPI_FLOW = [
        ('GET', 'cluster', SRR['is_rest_9_8']),                 # get_version
    ]


def test_success_no_vserver():
    ''' test get'''
    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record_admin'])  # get user
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('vserver')
    results = create_and_apply(my_module, args)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'notes' in results
    assert 'msg' in results
    assert "NOTE: application console not found for user: user1: ['http', 'ontapi']" in results['notes']
    assert 'ZAPI connected successfully.' in results['msg']


def test_success_with_vserver():
    ''' test get'''
    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record']),   # get user
        ('GET', 'svm/svms', SRR['one_vserver_record']),         # get_svms
        ('GET', 'security/accounts', SRR['one_user_record'])    # get_users
    ])

    results = create_and_apply(my_module, DEFAULT_ARGS)
    print('Info: %s' % results)
    # assert results['changed'] is False
    assert_no_warnings()
    assert 'notes' not in results


def test_fail_with_vserver_locked():
    ''' test get'''
    user = copy.deepcopy(SRR['one_user_record'])
    user[1]['records'][0]['locked'] = True
    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record']),   # get user
        ('GET', 'svm/svms', SRR['one_vserver_record']),         # get_svms
        ('GET', 'security/accounts', user)                      # get_users
    ])

    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'notes' in results
    assert 'user: user1 is locked on vserver: vserver' in results['notes'][0]


def test_fail_with_vserver_missing_app():
    ''' test get'''
    user = copy.deepcopy(SRR['one_user_record'])
    user[1]['records'][0]['applications'] = [dict(application='http')]

    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record']),   # get user
        ('GET', 'svm/svms', SRR['one_vserver_record']),         # get_svms
        ('GET', 'security/accounts', user)                      # get_users
    ])

    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'notes' in results
    assert 'application ontapi not found for user: user1' in results['notes'][0]
    assert 'Error: no unlocked user for ontapi on vserver: vserver' in results['msg']


def test_fail_with_vserver_list_user_not_found():
    ''' test get'''
    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record']),   # get user
        ('GET', 'svm/svms', SRR['one_vserver_record']),         # get_svms
        ('GET', 'security/accounts', SRR['empty_records'])      # get_users
    ])

    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'Error getting accounts for: vserver: none found' in results['msg']


def test_fail_with_vserver_list_user_error_on_get_users():
    ''' test get'''
    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record']),   # get user
        ('GET', 'svm/svms', SRR['one_vserver_record']),         # get_svms
        ('GET', 'security/accounts', SRR['generic_error'])      # get_users
    ])

    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'Error getting accounts for: vserver: calling: security/accounts: got Expected error.' in results['msg']


def test_success_with_vserver_list_user_not_authorized():
    ''' test get'''
    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record']),   # get user
        ('GET', 'svm/svms', SRR['one_vserver_record']),         # get_svms
        ('GET', 'security/accounts', SRR['not_authorized'])     # get_users
    ])

    results = create_and_apply(my_module, DEFAULT_ARGS)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'Not autorized to get accounts for: vserver: calling: security/accounts: got not authorized for that command.' in results['msg']


def test_fail_with_vserver_no_interface():
    ''' test get'''
    vserver = copy.deepcopy(SRR['one_vserver_record'])
    vserver[1]['records'][0].pop('ip_interfaces')
    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record_admin']),     # get user
        ('GET', 'svm/svms', vserver),                                   # get_svms
        ('GET', 'security/accounts', SRR['one_user_record'])            # get_users
    ])

    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'notes' in results
    assert "NOTE: application console not found for user: user1: ['http', 'ontapi']" in results['notes']
    assert 'Error vserver is not associated with a network interface: vserver' in results['msg']


def test_fail_with_vserver_not_found():
    ''' test get'''
    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record_admin']),     # get user
        ('GET', 'svm/svms', SRR['empty_records']),                      # get_svms
        ('GET', 'security/accounts', SRR['one_user_record'])            # get_users
    ])

    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'notes' in results
    assert "NOTE: application console not found for user: user1: ['http', 'ontapi']" in results['notes']
    assert 'Error getting vserver in list_interfaces: vserver: not found' in results['msg']


def test_fail_with_vserver_error_on_get_svms():
    ''' test get'''
    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record_admin']),     # get user
        ('GET', 'svm/svms', SRR['generic_error']),                      # get_svms
        ('GET', 'security/accounts', SRR['one_user_record'])            # get_users
    ])

    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'notes' in results
    assert "NOTE: application console not found for user: user1: ['http', 'ontapi']" in results['notes']
    assert 'Error getting vserver in list_interfaces: vserver: calling: svm/svms: got Expected error.' in results['msg']


def test_note_with_vserver_no_management_service():
    ''' test get'''
    vserver = copy.deepcopy(SRR['one_vserver_record'])
    vserver[1]['records'][0]['ip_interfaces'][0]['services'] = ['data_core']
    register_responses(REST_ZAPI_FLOW + [
        ('GET', 'security/accounts', SRR['one_user_record_admin']),     # get user
        ('GET', 'svm/svms', vserver),                                   # get_svms
        ('GET', 'security/accounts', SRR['one_user_record'])            # get_users
    ])

    results = create_and_apply(my_module, DEFAULT_ARGS)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'notes' in results
    assert 'no management policy in services' in results['notes'][2]


def test_fail_zapi_error():
    ''' test get'''
    register_responses([
        ('system-get-version', ZRR['error']),
        ('GET', 'cluster', SRR['is_rest_9_8']),                     # get_version
        ('GET', 'security/accounts', SRR['one_user_record']),       # get_user
        ('GET', 'svm/svms', SRR['one_vserver_record']),             # get_vservers
        ('GET', 'security/accounts', SRR['one_user_record']),       # get_users
        ('system-get-version', ZRR['ConnectTimeoutError']),
        ('GET', 'cluster', SRR['is_rest_9_8']),                     # get_version
        ('GET', 'security/accounts', SRR['one_user_record']),       # get_user
        ('GET', 'svm/svms', SRR['one_vserver_record']),             # get_vservers
        ('GET', 'security/accounts', SRR['one_user_record']),       # get_users
        ('system-get-version', ZRR['Name or service not known']),
        ('GET', 'cluster', SRR['is_rest_9_8']),                     # get_version
        ('GET', 'security/accounts', SRR['one_user_record']),       # get_user
        ('GET', 'svm/svms', SRR['one_vserver_record']),             # get_vservers
        ('GET', 'security/accounts', SRR['one_user_record'])        # get_users
    ])
    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'notes' not in results
    assert 'Unclassified, see msg' in results['msg']
    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    assert 'Error in hostname - Address does not exist or is not reachable: NetApp API failed. Reason - 123:ConnectTimeoutError' in results['msg']
    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    assert 'Error in hostname - DNS name cannot be resolved: NetApp API failed. Reason - 123:Name or service not known' in results['msg']


def test_fail_rest_error():
    ''' test get'''
    register_responses([
        ('system-get-version', ZRR['version']),
        ('GET', 'cluster', SRR['is_zapi']),                     # get_version
        ('vserver-get-iter', ZRR['cserver']),                   # for EMS event
        ('ems-autosupport-log', ZRR['success']),                # EMS log
        ('system-get-version', ZRR['version']),
        ('GET', 'cluster', SRR['ConnectTimeoutError']),         # get_version
        ('vserver-get-iter', ZRR['cserver']),                   # for EMS event
        ('ems-autosupport-log', ZRR['success']),                # EMS log
        ('system-get-version', ZRR['version']),
        ('GET', 'cluster', SRR['Name or service not known']),   # get_version
        ('vserver-get-iter', ZRR['cserver']),                   # for EMS event
        ('ems-autosupport-log', ZRR['success']),                # EMS log
    ])
    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'notes' not in results
    assert 'Other error for hostname: 10.10.10.10 using REST: Unreachable.' in results['msg']
    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    assert 'Error in hostname - Address does not exist or is not reachable: Connection timed out' in results['msg']
    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    assert 'Error in hostname - DNS name cannot be resolved: Name or service not known' in results['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_netapp_lib_error(mock_has_netapp_lib):
    ''' test get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8']),                     # get_version
        ('GET', 'security/accounts', SRR['one_user_record']),       # get_user
        ('GET', 'svm/svms', SRR['one_vserver_record']),             # get_vservers
        ('GET', 'security/accounts', SRR['one_user_record'])        # get_users
    ])

    mock_has_netapp_lib.return_value = False

    results = create_and_apply(my_module, DEFAULT_ARGS, fail=True)
    print('Info: %s' % results)
    assert_no_warnings()
    assert 'notes' not in results
    assert 'Install the python netapp-lib module or a missing dependency' in results['msg'][0]


def test_check_connection_internal_error():
    ''' expecting REST or ZAPI '''
    error = 'Internal error, unexpected connection type: rest'
    assert error == expect_and_capture_ansible_exception(create_module(my_module, DEFAULT_ARGS).check_connection, 'fail', 'rest')['msg']


def test_call_main_no_cserver():
    register_responses([
        ('system-get-version', ZRR['version']),
        ('GET', 'cluster', SRR['is_rest_9_8']),                 # get_version
        ('vserver-get-iter', ZRR['empty']),                     # for EMS event
        ('ems-autosupport-log', ZRR['success']),                # EMS log
        ('GET', 'security/accounts', SRR['one_user_record']),   # get_user
        ('GET', 'svm/svms', SRR['one_vserver_record']),         # get_vservers
        ('GET', 'security/accounts', SRR['one_user_record'])    # get_users
    ])
    results = call_main(uut_main, DEFAULT_ARGS)
    assert 'notes' in results
    assert 'cserver not found' in results['notes']


def test_call_main_error_on_ems_log():
    register_responses([
        ('system-get-version', ZRR['version']),
        ('GET', 'cluster', SRR['is_rest_9_8']),                 # get_version
        ('vserver-get-iter', ZRR['empty']),                     # for EMS event
        ('ems-autosupport-log', ZRR['error']),                  # EMS log
        ('GET', 'security/accounts', SRR['one_user_record']),   # get_user
        ('GET', 'svm/svms', SRR['one_vserver_record']),         # get_vservers
        ('GET', 'security/accounts', SRR['one_user_record'])    # get_users
    ])
    results = call_main(uut_main, DEFAULT_ARGS, fail=True)
    assert 'notes' in results
    assert 'cserver not found' in results['notes']
    assert 'Failed to log EMS message: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in results['msg']
