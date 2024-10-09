# (c) 2019-2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_security_certificates """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_certificates \
    import NetAppOntapSecurityCertificates as my_module, main as my_main  # module under test


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


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
    'get_multiple_records': (200, {'records': [{'uuid': 'ansible'}, {'uuid': 'second'}]}, None),
    'error_unexpected_name': (200, None, {'message': 'Unexpected argument "name".'}),
    'error_duplicate_entry': (200, None, {'message': 'duplicate entry', 'target': 'uuid'}),
    'error_some_error': (200, None, {'message': 'some error'}),
}

NAME_ERROR = "Error calling API: security/certificates - ONTAP 9.6 and 9.7 do not support 'name'.  Use 'common_name' and 'type' as a work-around."
TYPE_ERROR = "Error calling API: security/certificates - When using 'common_name', 'type' is required."
EXPECTED_ERROR = "Error calling API: security/certificates - Expected error"


def set_default_args():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'name': 'name_for_certificate'
    })


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    set_module_args({})
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_get_certificate_called(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    my_obj = my_module()
    assert my_obj.get_certificate() is not None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_error(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    with pytest.raises(AnsibleFailJson) as exc:
        my_main()
    assert exc.value.args[0]['msg'] == EXPECTED_ERROR


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create_failed(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],        # validate data vserver exist.
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successful_create(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],        # validate data vserver exists.
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_check_module_output(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],        # validate data vserver exists.
        SRR['empty_records'],   # get certificate -> not found
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'type': 'server',
        'vserver': 'abc',
        'common_name': 'cname'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['ontap_info'] is not None


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_idempotent_create(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],    # validate data vserver exist.
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_create_duplicate_entry(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],   # get certificate -> not found
        copy.deepcopy(SRR['error_duplicate_entry']),    # code under test modifies error in place
        SRR['end_of_sequence']
    ]
    data = {
        'type': 'client_ca',
        'common_name': 'cname'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('EXC', exc.value.args[0]['msg'])
    for fragment in ('Error creating or installing certificate: {',
                     "'message': 'duplicate entry.  Same certificate may already exist under a different name.'",
                     "'target': 'cluster'"):
        assert fragment in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successful_delete(mock_request):
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_idempotent_delete(mock_request):
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_delete(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],    # get certificate -> found
        SRR['error_some_error'],
        SRR['end_of_sequence']
    ]
    data = {
        'state': 'absent',
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = "Error deleting certificate: {'message': 'some error'}"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_multiple_records(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_multiple_records'],    # get certificate -> 2 records!
        SRR['end_of_sequence']
    ]
    data = {
        'state': 'absent',
        'common_name': 'cname',
        'type': 'client_ca',
    }
    data.update(set_default_args())
    data.pop('name')
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = "Duplicate records with same common_name are preventing safe operations: {'records': [{'uuid': 'ansible'}, {'uuid': 'second'}]}"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successful_sign(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
        SRR['get_uuid'],    # get certificate -> found
        SRR['empty_good'],
        SRR['end_of_sequence']
    ]
    data = {
        'vserver': 'abc',
        'signing_request': 'CSR',
        'expiry_time': 'et'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_sign(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
        SRR['get_uuid'],    # get certificate -> found
        SRR['error_some_error'],
        SRR['end_of_sequence']
    ]
    data = {
        'vserver': 'abc',
        'signing_request': 'CSR',
        'expiry_time': 'et'
    }
    data.update(set_default_args())
    set_module_args(data)
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    msg = "Error signing certificate: {'message': 'some error'}"
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_failed_sign_missing_ca(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_failed_sign_absent(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_failed_on_name(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_cannot_ignore_name_error_no_common_name(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_cannot_ignore_name_error_no_type(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_ignore_name_error(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successful_create_name_error(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['get_uuid'],
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


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_data_vserver_not_exist(mock_request):
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_records'],
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
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    assert 'Error vserver abc does not exist or is not a data vserver.' in exc.value.args[0]['msg']


def test_rest_negative_no_name_and_type():
    data = {
        'common_name': 'cname',
        # 'type': 'client_ca',
        'vserver': 'abc',
    }
    data.update(set_default_args())
    data.pop('name')
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = "Error: 'name' or ('common_name' and 'type') are required parameters."
    assert msg == exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_ZAPI_only(mock_request):
    mock_request.side_effect = [
        SRR['is_zapi'],
        SRR['end_of_sequence']
    ]
    set_module_args(set_default_args())
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = my_module()
    print(exc.value.args[0])
    msg = "na_ontap_security_certificates only supports REST, and requires ONTAP 9.6 or later. - Unreachable"
    assert msg == exc.value.args[0]['msg']
