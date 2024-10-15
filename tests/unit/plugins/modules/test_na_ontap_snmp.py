# (c) 2018-2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP snmp Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import assert_no_warnings, set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snmp \
    import NetAppONTAPSnmp as my_module, main as uut_main      # module under test


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


def default_args():
    args = {
        'state': 'present',
        'hostname': '10.10.10.10',
        'username': 'admin',
        'https': 'true',
        'validate_certs': 'false',
        'password': 'password',
        'use_rest': 'always'
    }
    return args


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_6': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'server_error': (500, None, "Internal Server error"),
    'generic_error': (400, None, "Expected error"),
    'community_user_record': (200, {
        'records': [{
            "name": "snmpv3user2",
            "authentication_method": "community",
            'engine_id': "80000315058e02057c0fb8e911bc9f005056bb942e"
        }],
        'num_records': 1
    }, None),
    'snmp_usm_user_record': (200, {
        'records': [{
            "name": "snmpv3user3",
            "authentication_method": "usm",
            'engine_id': "80000315058e02057c0fb8e911bc9f005056bb942e",
            'snmpv3': {
                'privacy_protocol': 'aes128',
                'authentication_password': 'humTdumt*@t0nAwa11',
                'authentication_protocol': 'sha',
                'privacy_password': 'p@**GOandCLCt*200'
            }
        }],
        'num_records': 1
    }, None),
}


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args(dict(hostname=''))
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'missing required arguments: snmp_username'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_get_snmp_community_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['snmp_username'] = 'snmpv3user2'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['community_user_record'],       # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_get_snmp_usm_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['snmp_username'] = 'snmpv3user3'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['snmp_usm_user_record'],       # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_create_snmp_community_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['snmp_username'] = 'snmpv3user2'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['zero_record'],         # get
        SRR['empty_good'],          # create
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_create_snmp_usm_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['snmp_username'] = 'snmpv3user3'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['zero_record'],         # get
        SRR['empty_good'],          # create
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


def test_fail_to_create_snmp_usm_without_snmpv3_passwords(patch_ansible):
    ''' required arguments are reported as errors '''
    usm_record = {
        'snmp_username': 'usm19',
        'authentication_method': 'usm',
        'snmpv3': {
            'privacy_protocol': 'aes128',
            'authentication_protocol': 'sha'
        }
    }
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args(usm_record)
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'missing required arguments:'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_snmp_community_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['snmp_username'] = 'snmpv3user2'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['community_user_record'],       # get
        SRR['community_user_record'],
        SRR['empty_good'],          # delete
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_snmp_usm_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['snmp_username'] = 'snmpv3user3'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['snmp_usm_user_record'],       # get
        SRR['snmp_usm_user_record'],
        SRR['empty_good'],          # delete
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_snmp_community_idempotent(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['snmp_username'] = 'snmpv3user2'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['zero_record'],         # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_snmp_usm_idempotent(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['snmp_username'] = 'snmpv3user3'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['zero_record'],         # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert_no_warnings()
