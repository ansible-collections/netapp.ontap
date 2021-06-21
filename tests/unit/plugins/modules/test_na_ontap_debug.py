# (c) 2018-2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP debug Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_debug \
    import NetAppONTAPDebug as my_module, main as uut_main      # module under test
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

# not available on 2.6 anymore
if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


def exit_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


WARNINGS = list()


def warn(dummy, msg):
    WARNINGS.append(msg)


def default_args():
    args = {
        'hostname': '10.10.10.10',
        'username': 'admin',
        'https': 'true',
        'validate_certs': 'false',
        'password': 'password',
        'vserver': 'vserver',
    }
    return args


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy_9_8_0')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
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
        }],
        'num_records': 1
    }, None),
}


if netapp_utils.has_netapp_lib():
    def zapi_response(contents):
        response = netapp_utils.zapi.NaElement('xml')
        response.translate_struct(contents)
        response.add_attr('status', 'passed')
        return response

    def zapi_error(errno, reason):
        response = netapp_utils.zapi.NaElement('xml')
        response.add_attr('errno', errno)
        response.add_attr('reason', reason)
        return response

    ZRR = {
        'success': zapi_response({}),
        'version': zapi_response({'version': 'zapi_version'}),
        'cserver': zapi_response({
            'attributes-list': {
                'vserver-info': {
                    'vserver-name': 'vserver'
                }
            },
            # 'num-records': '1'
        })
    }

    ZAPI_FLOW = [
        ZRR['version'],     # get version
        ZRR['cserver'],     # for EMS event
        ZRR['success'],     # EMS log
    ]


# using pytest natively, without unittest.TestCase
@pytest.fixture
def patch_ansible():
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json,
                        warn=warn) as mocks:
        global WARNINGS
        WARNINGS = list()
        yield mocks


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_success_no_vserver(mock_request, mock_invoke, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args.pop('vserver')
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],     # get version
        SRR['end_of_sequence']
    ]
    mock_invoke.side_effect = ZAPI_FLOW

    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_invoke.mock_calls)
    print(mock_request.mock_calls)
    assert not WARNINGS
    assert 'notes' not in exc.value.args[0]


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_success_with_vserver(mock_request, mock_invoke, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_vserver_record'],  # get vserver
        SRR['one_user_record'],     # get users
        SRR['end_of_sequence']
    ]

    mock_invoke.side_effect = ZAPI_FLOW
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_invoke.mock_calls)
    print(mock_request.mock_calls)
    # assert exc.value.args[0]['changed'] is False
    assert not WARNINGS
    assert 'notes' not in exc.value.args[0]


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_fail_with_vserver_locked(mock_request, mock_invoke, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    user = copy.deepcopy(SRR['one_user_record'])
    user[1]['records'][0]['locked'] = True

    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_vserver_record'],  # get vserver
        user,                       # get users
        SRR['end_of_sequence']
    ]

    mock_invoke.side_effect = ZAPI_FLOW
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_invoke.mock_calls)
    print(mock_request.mock_calls)
    assert not WARNINGS
    assert 'notes' in exc.value.args[0]
    assert 'user: user1 is locked for: vserver' in exc.value.args[0]['notes'][0]


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_fail_with_vserver_missing_app(mock_request, mock_invoke, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    user = copy.deepcopy(SRR['one_user_record'])
    user[1]['records'][0]['applications'] = [dict(application='http')]

    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_vserver_record'],  # get vserver
        user,                       # get users
        SRR['end_of_sequence']
    ]

    mock_invoke.side_effect = ZAPI_FLOW
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_invoke.mock_calls)
    print(mock_request.mock_calls)
    assert not WARNINGS
    assert 'notes' in exc.value.args[0]
    assert 'application ontapi not found for user: user1' in exc.value.args[0]['notes'][0]
    assert 'Error: no unlocked user for ontapi on vserver: vserver' in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_fail_with_vserver_no_interface(mock_request, mock_invoke, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    vserver = copy.deepcopy(SRR['one_vserver_record'])
    vserver[1]['records'][0].pop('ip_interfaces')

    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        vserver,                    # get vserver
        SRR['one_user_record'],     # get users
        SRR['end_of_sequence']
    ]

    mock_invoke.side_effect = ZAPI_FLOW
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_invoke.mock_calls)
    print(mock_request.mock_calls)
    assert not WARNINGS
    assert 'notes' not in exc.value.args[0]


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_note_with_vserver_no_management_service(mock_request, mock_invoke, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    vserver = copy.deepcopy(SRR['one_vserver_record'])
    vserver[1]['records'][0]['ip_interfaces'][0]['services'] = ['data_core']

    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        vserver,                    # get vserver
        SRR['one_user_record'],     # get users
        SRR['end_of_sequence']
    ]

    mock_invoke.side_effect = ZAPI_FLOW
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_invoke.mock_calls)
    print(mock_request.mock_calls)
    assert not WARNINGS
    assert 'notes' in exc.value.args[0]
    assert 'no management policy in services' in exc.value.args[0]['notes'][0]


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_fail_zapi_error(mock_request, mock_invoke, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    vserver = copy.deepcopy(SRR['one_vserver_record'])
    vserver[1]['records'][0].pop('ip_interfaces')

    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_vserver_record'],  # get vserver
        SRR['one_user_record'],     # get users
        SRR['end_of_sequence']
    ]

    mock_invoke.side_effect = [zapi_error('123', 'fake_zapi_error')]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_invoke.mock_calls)
    print(mock_request.mock_calls)
    assert not WARNINGS
    assert 'notes' not in exc.value.args[0]


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_fail_rest_error(mock_request, mock_invoke, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    vserver = copy.deepcopy(SRR['one_vserver_record'])
    vserver[1]['records'][0].pop('ip_interfaces')

    mock_request.side_effect = [
        SRR['is_zapi'],             # get version
        SRR['end_of_sequence']
    ]

    mock_invoke.side_effect = ZAPI_FLOW
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_invoke.mock_calls)
    print(mock_request.mock_calls)
    assert not WARNINGS
    assert 'notes' not in exc.value.args[0]


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapZAPICx.invoke_elem')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_fail_netapp_lib_error(mock_request, mock_invoke, mock_has_netapp_lib, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    vserver = copy.deepcopy(SRR['one_vserver_record'])
    vserver[1]['records'][0].pop('ip_interfaces')

    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_vserver_record'],  # get vserver
        SRR['one_user_record'],     # get users
        SRR['end_of_sequence']
    ]

    mock_invoke.side_effect = ZAPI_FLOW

    mock_has_netapp_lib.return_value = False

    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_invoke.mock_calls)
    print(mock_request.mock_calls)
    assert not WARNINGS
    assert 'notes' not in exc.value.args[0]
    assert 'Install the python netapp-lib module or a missing dependency' in exc.value.args[0]['msg'][0]
