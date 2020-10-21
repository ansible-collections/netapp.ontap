# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_security_certificates """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_certificates \
    import NetAppOntapSecurityCertificates as my_module  # module under test


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'empty_records': (200, {'records': []}, None),
    'get_uuid': (200, {'records': [{'uuid': 'ansible'}]}, None),
    'error_unexpected_name': (200, None, {'message': 'Unexpected argument "name".'})
}

NAME_ERROR = "Error calling API: security/certificates - ONTAP 9.6 and 9.7 do not support 'name'.  Use 'common_name' and 'type' as a work-around."
TYPE_ERROR = "Error calling API: security/certificates - When using 'common_name', 'type' is required."
EXPECTED_ERROR = "Error calling API: security/certificates - Expected error"


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


def set_default_args():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'name': 'name_for_certificate'
    })


@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
def test_module_fail_when_required_args_missing(mock_fail):
    ''' required arguments are reported as errors '''
    mock_fail.side_effect = fail_json
    set_module_args({})
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_get_certificate_called(mock_request, mock_fail):
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    assert my_obj.get_certificate() is not None


@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_error(mock_request, mock_fail):
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['msg'] == EXPECTED_ERROR


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create_failed(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],   # get certificate -> not found
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'type': 'client_ca',
        'vserver': 'abc',
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = 'Error creating or installing certificate: one or more of the following options are missing:'
    assert exc.value.args[0]['msg'].startswith(msg)


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successful_create(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],   # get certificate -> not found
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'type': 'client_ca',
        'vserver': 'abc',
        'common_name': 'cname'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_idempotent_create(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],    # get certificate -> found
        SRR['end_of_sequence']
    ]
    data = {
        'type': 'client_ca',
        'vserver': 'abc',
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert not exc.value.args[0]['changed']


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successful_delete(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],    # get certificate -> found
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'state': 'absent',
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_idempotent_delete(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],   # get certificate -> not found
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'state': 'absent',
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert not exc.value.args[0]['changed']


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successful_sign(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],    # get certificate -> found
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'vserver': 'abc',
        'signing_request': 'CSR'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_failed_sign_missing_ca(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],   # get certificate -> not found
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'vserver': 'abc',
        'signing_request': 'CSR'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = "signing certificate with name '%s' not found on svm: %s" % (data['name'], data['vserver'])
    assert exc.value.args[0]['msg'] == msg


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_failed_sign_absent(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],    # get certificate -> found
        SRR['end_of_sequence']
    ]
    data = {
        'vserver': 'abc',
        'signing_request': 'CSR',
        'state': 'absent'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = "'signing_request' is not supported with 'state' set to 'absent'"
    assert exc.value.args[0]['msg'] == msg


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_failed_on_name(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['error_unexpected_name'],   # get certificate -> error
        SRR['end_of_sequence']
    ]
    data = {
        'vserver': 'abc',
        'signing_request': 'CSR',
        'state': 'absent',
        'ignore_name_if_not_supported': False,
        'common_name': 'common_name',
        'type': 'root_ca'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['msg'] == NAME_ERROR


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_cannot_ignore_name_error_no_common_name(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['error_unexpected_name'],   # get certificate -> error
        SRR['end_of_sequence']
    ]
    data = {
        'vserver': 'abc',
        'signing_request': 'CSR',
        'state': 'absent',
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['msg'] == NAME_ERROR


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_cannot_ignore_name_error_no_type(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['error_unexpected_name'],   # get certificate -> error
        SRR['end_of_sequence']
    ]
    data = {
        'vserver': 'abc',
        'signing_request': 'CSR',
        'state': 'absent',
        'common_name': 'common_name'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['msg'] == TYPE_ERROR


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_ignore_name_error(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['error_unexpected_name'],   # get certificate -> error
        SRR['get_uuid'],                # get certificate -> found
        SRR['end_of_sequence']
    ]
    data = {
        'vserver': 'abc',
        'signing_request': 'CSR',
        'state': 'absent',
        'common_name': 'common_name',
        'type': 'root_ca'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = "'signing_request' is not supported with 'state' set to 'absent'"
    assert exc.value.args[0]['msg'] == msg


@patch('ansible.module_utils.basic.AnsibleModule.exit_json')
@patch('ansible.module_utils.basic.AnsibleModule.fail_json')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successful_create_name_error(mock_request, mock_fail, mock_exit):
    mock_exit.side_effect = exit_json
    mock_fail.side_effect = fail_json
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['error_unexpected_name'],   # get certificate -> error
        SRR['empty_records'],           # get certificate -> not found
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'common_name': 'cname',
        'type': 'client_ca',
        'vserver': 'abc',
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']
    print(mock_request.mock_calls)
