# (c) 2018-2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP publickey Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest
import sys

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_service_policy \
    import NetAppOntapServicePolicy as my_module, main as uut_main      # module under test


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


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
        'state': 'present',
        'hostname': '10.10.10.10',
        'username': 'admin',
        'https': 'true',
        'validate_certs': 'false',
        'password': 'password',
        'name': 'sp123',
        'vserver': 'vserver',
    }
    return args


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'one_sp_record': (200, {
        "records": [{
            'name': 'sp123',
            'uuid': 'uuid123',
            'vserver': dict(name='vserver'),
            'services': ['data_core'],
            'scope': 'svm',
        }],
        'num_records': 1
    }, None),
    'two_sp_records': (200, {
        "records": [
            {
                'name': 'sp123',
            },
            {
                'name': 'sp124',
            }],
        'num_records': 2
    }, None),
}


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


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args(dict(hostname=''))
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'missing required arguments: name'
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_get_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['services'] = ['data_core']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_sp_record'],     # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_create_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['services'] = ['data_core']
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
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_create_called_cluster(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['services'] = ['data_core']
    args.pop('vserver')
    args['ipspace'] = 'ipspace'
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
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_create_idempotent(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'always'
    args['services'] = ['data_core']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_sp_record'],       # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_modify_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['services'] = ['data_nfs']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_sp_record'],       # get
        SRR['empty_good'],          # modify
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_modify_called_no_service(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['services'] = ['no_service']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_sp_record'],       # get
        SRR['empty_good'],          # modify
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['services'] = ['data_core']
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_sp_record'],       # get
        SRR['empty_good'],          # delete
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    print(mock_request.mock_calls)
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_delete_idempotent(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'always'
    args['services'] = ['data_core']
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
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_extra_record(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['two_sp_records'],      # get
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error in get_service_policy: calling: network/ip/service-policies: unexpected response'
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


def test_negative_ipspace_required_1(patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs']
    args['vserver'] = None      # cluster scope
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = "vserver is None but all of the following are missing: ipspace"
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


def test_negative_ipspace_required_2(patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs']
    args['scope'] = 'cluster'   # cluster scope
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = "scope is cluster but all of the following are missing: ipspace"
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


def test_negative_ipspace_required_3(patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs']
    args.pop('vserver')         # cluster scope
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = "one of the following is required: ipspace, vserver"
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


def test_negative_vserver_required_1(patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs']
    args.pop('vserver')
    args['scope'] = 'svm'
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = "one of the following is required: ipspace, vserver"
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


def test_negative_vserver_required_2(patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs']
    args.pop('vserver')
    args['scope'] = 'svm'
    args['ipspace'] = 'ipspace'
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = "scope is svm but all of the following are missing: vserver"
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_vserver_required_3(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs']
    args['vserver'] = None
    args['scope'] = 'svm'
    args['ipspace'] = 'ipspace'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error: vserver cannot be None when "scope: svm" is specified.'
    print(mock_request.mock_calls)
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_vserver_not_required(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs']
    args['scope'] = 'cluster'
    args['ipspace'] = 'ipspace'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error: vserver cannot be set when "scope: cluster" is specified.  Got: vserver'
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_no_service_not_alone(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs', 'no_service']
    args['scope'] = 'svm'
    args['ipspace'] = 'ipspace'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: no other service can be present when no_service is specified."
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_vserver_set_with_cluster_scope(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs', 'no_service']
    args['scope'] = 'cluster'
    args['ipspace'] = 'ipspace'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: no other service can be present when no_service is specified."
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_extra_arg_in_modify(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'present'
    args['services'] = ['data_nfs']
    args['vserver'] = None      # cluster scope
    args['ipspace'] = 'ipspace'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_sp_record'],       # get
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        uut_main()
    print('Info: %s' % exc.value.args[0])
    msg = "Error: attributes not supported in modify: {'scope': 'cluster'}"
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_empty_body_in_modify(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    current = dict(uuid='')
    modify = dict()
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.modify_service_policy(current, modify)
    print('Info: %s' % exc.value.args[0])
    msg = 'Error: nothing to change - modify called with: {}'
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_create_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['zero_record'],         # get
        SRR['generic_error'],       # create
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error in create_service_policy: Expected error'
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_delete_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_sp_record'],       # get
        SRR['generic_error'],       # delete
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error in delete_service_policy: Expected error'
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_negative_modify_called(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    args['use_rest'] = 'auto'
    args['services'] = ['data_nfs']
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['one_sp_record'],       # get
        SRR['generic_error'],       # modify
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'Error in modify_service_policy: Expected error'
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS
