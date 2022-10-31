# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''


from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import \
    assert_warning_was_raised, call_main, clear_warnings, create_and_apply, create_module, expect_and_capture_ansible_exception, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_svm \
    import NetAppOntapSVM as svm_module, main as my_main    # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

# REST API canned responses when mocking send_request

svm_info = {
    "uuid": "09e9fd5e-8ebd-11e9-b162-005056b39fe7",
    "name": "test_svm",
    "state": "running",
    "subtype": "default",
    "language": "c.utf_8",
    "aggregates": [{"name": "aggr_1",
                    "uuid": "850dd65b-8811-4611-ac8c-6f6240475ff9"},
                   {"name": "aggr_2",
                    "uuid": "850dd65b-8811-4611-ac8c-6f6240475ff9"}],
    "comment": "new comment",
    "ipspace": {"name": "ansible_ipspace",
                "uuid": "2b760d31-8dfd-11e9-b162-005056b39fe7"},
    "snapshot_policy": {"uuid": "3b611707-8dfd-11e9-b162-005056b39fe7",
                        "name": "old_snapshot_policy"},
    "nfs": {"enabled": True, "allowed": True},
    "cifs": {"enabled": False},
    "iscsi": {"enabled": False},
    "fcp": {"enabled": False},
    "nvme": {"enabled": False},
    'max_volumes': 3333
}

svm_info_cert1 = dict(svm_info)
svm_info_cert1['certificate'] = {'name': 'cert_1', 'uuid': 'cert_uuid_1'}
svm_info_cert2 = dict(svm_info)
svm_info_cert2['certificate'] = {'name': 'cert_2', 'uuid': 'cert_uuid_2'}

SRR = rest_responses({
    'svm_record': (200, {'records': [svm_info]}, None),
    'svm_record_cert1': (200, {'records': [svm_info_cert1]}, None),
    'svm_record_cert2': (200, {'records': [svm_info_cert2]}, None),
    'svm_record_ap': (200,
                      {'records': [{"name": "test_svm",
                                    "state": "running",
                                    "aggregates": [{"name": "aggr_1",
                                                    "uuid": "850dd65b-8811-4611-ac8c-6f6240475ff9"},
                                                   {"name": "aggr_2",
                                                    "uuid": "850dd65b-8811-4611-ac8c-6f6240475ff9"}],
                                    "ipspace": {"name": "ansible_ipspace",
                                                "uuid": "2b760d31-8dfd-11e9-b162-005056b39fe7"},
                                    "snapshot_policy": {"uuid": "3b611707-8dfd-11e9-b162-005056b39fe7",
                                                        "name": "old_snapshot_policy"},
                                    "nfs": {"enabled": False},
                                    "cifs": {"enabled": True, "allowed": True},
                                    "iscsi": {"enabled": True, "allowed": True},
                                    "fcp": {"enabled": False},
                                    "nvme": {"enabled": False}}]}, None),
    'cli_record': (200,
                   {'records': [{"max_volumes": 100, "allowed_protocols": ['nfs', 'iscsi']}]}, None),
    'certificate_record_1': (200,
                             {'records': [{"name": "cert_1",
                                           "uuid": "cert_uuid_1"}]}, None),
    'certificate_record_2': (200,
                             {'records': [{"name": "cert_2",
                                           "uuid": "cert_uuid_2"}]}, None),
    'svm_web_record_1': (200, {
        'records': [{
            'certificate': {
                "uuid": "cert_uuid_1"
            },
            'client_enabled': False,
            'ocsp_enabled': False,
        }]}, None),
    'svm_web_record_2': (200, {
        'records': [{
            'certificate': {
                "uuid": "cert_uuid_2"
            },
            'client_enabled': True,
            'ocsp_enabled': True,
        }]}, None)
}, False)

DEFAULT_ARGS = {
    'name': 'test_svm',
    'aggr_list': 'aggr_1,aggr_2',
    'ipspace': 'ansible_ipspace',
    'comment': 'new comment',
    'subtype': 'default',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!'
}

vserver_info = {
    'num-records': 1,
    'attributes-list': {
        'vserver-info': {
            'vserver-name': 'test_svm',
            'ipspace': 'ansible_ipspace',
            'root-volume': 'ansible_vol',
            'root-volume-aggregate': 'ansible_aggr',
            'language': 'c.utf_8',
            'comment': 'new comment',
            'snapshot-policy': 'old_snapshot_policy',
            'vserver-subtype': 'default',
            'allowed-protocols': [{'protocol': 'nfs'}, {'protocol': 'cifs'}],
            'aggr-list': [{'aggr-name': 'aggr_1'}, {'aggr-name': 'aggr_2'}],
        }}}


ZRR = zapi_responses({
    'svm_record': build_zapi_response(vserver_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    error = create_module(svm_module, {}, fail=True)['msg']
    assert 'missing required arguments:' in error
    assert 'hostname' in error
    assert 'name' in error


def test_error_missing_name():
    ''' Test if create throws an error if name is not specified'''
    register_responses([
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('name')
    assert create_module(svm_module, args, fail=True)['msg'] == 'missing required arguments: name'


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_error_missing_netapp_lib(mock_has_netapp_lib):
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
    ])
    mock_has_netapp_lib.return_value = False
    msg = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert msg == create_module(svm_module, DEFAULT_ARGS, fail=True)['msg']


def test_successful_create_zapi():
    '''Test successful create'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-create', ZRR['success']),
        ('ZAPI', 'vserver-modify', ZRR['success']),
    ])
    assert create_and_apply(svm_module, DEFAULT_ARGS)['changed']


def test_create_idempotency():
    '''Test API create'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
    ])
    assert not create_and_apply(svm_module, DEFAULT_ARGS)['changed']


def test_create_error():
    '''Test successful create'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-create', ZRR['error']),
    ])
    msg = 'Error provisioning SVM test_svm: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert create_and_apply(svm_module, DEFAULT_ARGS, fail=True)['msg'] == msg


def test_successful_delete():
    '''Test successful delete'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('ZAPI', 'vserver-destroy', ZRR['success']),
    ])
    _modify_options_with_expected_change('state', 'absent')


def test_error_delete():
    '''Test delete with ZAPI error
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('ZAPI', 'vserver-destroy', ZRR['error']),
    ])
    module_args = {
        'state': 'absent',
    }
    msg = 'Error deleting SVM test_svm: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_delete_idempotency():
    '''Test delete idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'state': 'absent',
    }
    assert not create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_init():
    '''Validate that:
          admin_state is ignored with ZAPI
          language is set to lower case for C.UTF-8
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
    ])
    module_args = {
        'admin_state': 'running',
        'language': 'C.uTf-8'
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    assert my_obj.parameters['language'] == 'c.utf_8'
    assert_warning_was_raised('admin_state is ignored when ZAPI is used.')


def test_init_error():
    '''Validate that:
          unallowed protocol raises an error
          services is not supported with ZAPI
    '''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('GET', 'cluster', SRR['is_zapi']),
    ])
    module_args = {
        'allowed_protocols': 'dummy,humpty,dumpty,cifs,nfs',
    }
    error = create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Unexpected value dummy in allowed_protocols.' in error
    assert 'Unexpected value humpty in allowed_protocols.' in error
    assert 'Unexpected value dumpty in allowed_protocols.' in error
    assert 'cifs' not in error
    assert 'nfs' not in error

    module_args = {
        'services': {},
    }
    error = create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert error == 'using services requires ONTAP 9.6 or later and REST must be enabled - Unreachable - using ZAPI.'


def test_successful_rename():
    '''Test successful rename'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('ZAPI', 'vserver-rename', ZRR['success']),
    ])
    module_args = {
        'from_name': 'test_svm',
        'name': 'test_new_svm',
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_error_rename_no_from():
    '''Test error rename'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'from_name': 'test_svm',
        'name': 'test_new_svm',
    }
    msg = 'Error renaming SVM test_new_svm: no SVM with from_name test_svm.'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_error_rename_zapi():
    '''Test error rename'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('ZAPI', 'vserver-rename', ZRR['error']),
    ])
    module_args = {
        'from_name': 'test_svm',
        'name': 'test_new_svm',
    }
    msg = 'Error renaming SVM test_svm: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_successful_modify_language():
    '''Test successful modify language'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('ZAPI', 'vserver-modify', ZRR['success']),
    ])
    _modify_options_with_expected_change('language', 'c')


def test_error_modify_language():
    '''Test error modify language'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('ZAPI', 'vserver-modify', ZRR['error']),
    ])
    module_args = {
        'language': 'c',
    }
    msg = 'Error modifying SVM test_svm: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_error_modify_fixed_properties():
    '''Test error modifying a fixed property'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
    ])
    module_args = {
        'ipspace': 'new',
    }
    msg = 'Error modifying SVM test_svm: cannot modify ipspace - current: ansible_ipspace - desired: new.'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg
    module_args = {
        'ipspace': 'new',
        'root_volume': 'new_root'
    }
    msg = 'Error modifying SVM test_svm: cannot modify root_volume - current: ansible_vol - desired: new_root, '\
          'ipspace - current: ansible_ipspace - desired: new.'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_successful_modify_snapshot_policy():
    '''Test successful modify language'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('ZAPI', 'vserver-modify', ZRR['success']),
    ])
    _modify_options_with_expected_change(
        'snapshot_policy', 'new_snapshot_policy'
    )


def test_successful_modify_allowed_protocols():
    '''Test successful modify allowed protocols'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('ZAPI', 'vserver-modify', ZRR['success']),
    ])
    _modify_options_with_expected_change(
        'allowed_protocols', 'nvme,fcp'
    )


def test_successful_modify_aggr_list():
    '''Test successful modify aggr-list'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('ZAPI', 'vserver-modify', ZRR['success']),
    ])
    _modify_options_with_expected_change(
        'aggr_list', 'aggr_3,aggr_4'
    )


def test_successful_modify_aggr_list_star():
    '''Test successful modify aggr-list'''
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'vserver-get-iter', ZRR['svm_record']),
        ('ZAPI', 'vserver-modify', ZRR['success']),
    ])
    module_args = {
        'aggr_list': '*'
    }
    results = create_and_apply(svm_module, DEFAULT_ARGS, module_args)
    assert results['changed']
    assert_warning_was_raised("na_ontap_svm: changed always 'True' when aggr_list is '*'.")


def _modify_options_with_expected_change(arg0, arg1):
    module_args = {
        arg0: arg1,
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['generic_error']),
    ])
    module_args = {
        'root_volume': 'whatever',
        'aggr_list': '*',
        'ignore_rest_unsupported_options': 'true',
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == 'calling: svm/svms: got Expected error.'


def test_rest_error_unsupported_parm():
    register_responses([
    ])
    module_args = {
        'root_volume': 'not_supported_by_rest',
        'use_rest': 'always',
    }
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == "REST API currently does not support 'root_volume'"


def test_rest_successfully_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('POST', 'svm/svms', SRR['success']),
    ])
    assert create_and_apply(svm_module, DEFAULT_ARGS)['changed']


def test_rest_error_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('POST', 'svm/svms', SRR['generic_error']),
    ])
    msg = 'Error in create: calling: svm/svms: got Expected error.'
    assert create_and_apply(svm_module, DEFAULT_ARGS, fail=True)['msg'] == msg


def test_rest_create_idempotency():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
    ])
    module_args = {
        'root_volume': 'whatever',
        'aggr_list': '*',
        'ignore_rest_unsupported_options': 'true',
    }
    assert not create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successful_delete():
    '''Test successful delete'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('DELETE', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['success']),
    ])
    module_args = {
        'state': 'absent',
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_error_delete():
    '''Test error delete'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('DELETE', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent',
    }
    msg = 'Error in delete: calling: svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7: got Expected error.'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_error_delete_no_svm():
    '''Test error delete'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
    ])
    my_obj = create_module(svm_module, DEFAULT_ARGS)
    msg = 'Internal error, expecting SVM object in delete'
    assert expect_and_capture_ansible_exception(my_obj.delete_vserver, 'fail')['msg'] == msg


def test_rest_delete_idempotency():
    '''Test delete idempotency'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['zero_records']),
    ])
    module_args = {
        'state': 'absent',
    }
    assert not create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successful_rename():
    '''Test successful rename'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('PATCH', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['success']),
    ])
    module_args = {
        'from_name': 'test_svm',
        'name': 'test_new_svm',
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successful_modify_language():
    '''Test successful modify language'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('PATCH', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['success']),
    ])
    module_args = {
        'language': 'c',
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successful_get():
    '''Test successful get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'svm/svms', SRR['svm_record_ap']),
    ])
    module_args = {
        'admin_state': 'running',
        'language': 'c'
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    current = my_obj.get_vserver()
    print(current)
    assert current['services']['nfs']['allowed']
    assert not current['services']['cifs']['enabled']
    current = my_obj.get_vserver()
    print(current)
    assert not current['services']['nfs']['enabled']
    assert current['services']['cifs']['allowed']
    assert current['services']['iscsi']['allowed']


def test_rest_successfully_create_ignore_zapi_option():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('POST', 'svm/svms', SRR['success']),
    ])
    module_args = {
        'root_volume': 'whatever',
        'aggr_list': '*',
        'ignore_rest_unsupported_options': 'true',
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_create_with_service():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('POST', 'svm/svms', SRR['success']),
    ])
    module_args = {
        'services': {'nfs': {'allowed': True, 'enabled': True}, 'fcp': {'allowed': True, 'enabled': True}}
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_modify_with_service():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('PATCH', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['success']),
        ('POST', 'protocols/san/fcp/services', SRR['success']),
    ])
    module_args = {
        'admin_state': 'stopped',
        'services': {'nfs': {'allowed': True, 'enabled': True}, 'fcp': {'allowed': True, 'enabled': True}}
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_enable_service():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('POST', 'protocols/san/fcp/services', SRR['success']),
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    modify = {'services': {'nfs': {'allowed': True}, 'fcp': {'enabled': True}}}
    current = {'services': {'nfs': {'allowed': True}}, 'uuid': 'uuid'}
    assert my_obj.modify_services(modify, current) is None


def test_rest_successfully_reenable_service():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('PATCH', 'protocols/san/fcp/services/uuid', SRR['success']),
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    modify = {'services': {'nfs': {'allowed': True}, 'fcp': {'enabled': True}}}
    fcp_dict = {'_links': {'self': {'href': 'fcp_link'}}}
    current = {'services': {'nfs': {'allowed': True}}, 'uuid': 'uuid', 'fcp': fcp_dict}
    assert my_obj.modify_services(modify, current) is None


def test_rest_negative_enable_service():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    modify = {'services': {'nfs': {'allowed': True}, 'bad_value': {'enabled': True}}, 'name': 'new_name'}
    current = {'services': {'nfs': {'allowed': True}}, 'uuid': 'uuid'}
    error = expect_and_capture_ansible_exception(my_obj.modify_services, 'fail', modify, current)['msg']
    assert error == 'Internal error, unexpecting service: bad_value.'


def test_rest_negative_modify_services():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('POST', 'protocols/san/fcp/services', SRR['generic_error']),
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    modify = {'services': {'nfs': {'allowed': True}, 'fcp': {'enabled': True}}, 'name': 'new_name'}
    current = {'services': {'nfs': {'allowed': True}}, 'uuid': 'uuid'}
    error = expect_and_capture_ansible_exception(my_obj.modify_services, 'fail', modify, current)['msg']
    assert error == 'Error in modify service for fcp: calling: protocols/san/fcp/services: got Expected error.'


def test_rest_negative_modify_current_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    modify = {'enabled_protocols': ['nfs', 'fcp']}
    current = None
    error = expect_and_capture_ansible_exception(my_obj.modify_vserver, 'fail', modify, current)['msg']
    assert error == 'Internal error, expecting SVM object in modify.'


def test_rest_negative_modify_modify_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    modify = {}
    current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
    error = expect_and_capture_ansible_exception(my_obj.modify_vserver, 'fail', modify, current)['msg']
    assert error == 'Internal error, expecting something to modify in modify.'


def test_rest_negative_modify_error_1():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('PATCH', 'svm/svms/uuid', SRR['generic_error']),   # rename
    ])
    module_args = {
        'admin_state': 'running',
        'language': 'klingon',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    modify = {'enabled_protocols': ['nfs', 'fcp'], 'name': 'new_name', 'language': 'klingon'}
    current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
    error = expect_and_capture_ansible_exception(my_obj.modify_vserver, 'fail', modify, current)['msg']
    assert error == 'Error in rename: calling: svm/svms/uuid: got Expected error.'


def test_rest_negative_modify_error_2():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('PATCH', 'svm/svms/uuid', SRR['success']),         # rename
        ('PATCH', 'svm/svms/uuid', SRR['generic_error']),   # modify
    ])
    module_args = {
        'admin_state': 'running',
        'language': 'klingon',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    modify = {'enabled_protocols': ['nfs', 'fcp'], 'name': 'new_name', 'language': 'klingon'}
    current = {'enabled_protocols': ['nfs'], 'disabled_protocols': ['fcp', 'iscsi', 'nvme'], 'uuid': 'uuid'}
    error = expect_and_capture_ansible_exception(my_obj.modify_vserver, 'fail', modify, current)['msg']
    assert error == 'Error in modify: calling: svm/svms/uuid: got Expected error.'


def test_rest_successfully_get_older_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),      # get protocols
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    assert not create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_add_protocols_on_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('POST', 'svm/svms', SRR['success']),
        ('PATCH', 'private/cli/vserver/add-protocols', SRR['success']),
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_add_remove_protocols_on_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),                  # get protocols
        ('PATCH', 'private/cli/vserver/add-protocols', SRR['success']),
        ('PATCH', 'private/cli/vserver/remove-protocols', SRR['success'])
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}, 'iscsi': {'allowed': False}, 'fcp': {'allowed': True}}
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_add_remove_protocols_on_modify_old_style():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),                  # get protocols
        ('PATCH', 'private/cli/vserver/add-protocols', SRR['success']),
        ('PATCH', 'private/cli/vserver/remove-protocols', SRR['success'])
    ])
    module_args = {
        'admin_state': 'running',
        'allowed_protocols': ['nfs', 'fcp']
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_validate_int_or_string_as_int():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    assert create_module(svm_module, DEFAULT_ARGS, module_args).validate_int_or_string('10', 'whatever') is None


def test_validate_int_or_string_as_str():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    assert create_module(svm_module, DEFAULT_ARGS, module_args).validate_int_or_string('whatever', 'whatever') is None


def test_negative_validate_int_or_string():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
    ])
    module_args = {
        'admin_state': 'running',
        'services': {'nfs': {'allowed': True, 'enabled': True}}
    }
    astring = 'testme'
    error = expect_and_capture_ansible_exception(create_module(svm_module, DEFAULT_ARGS, module_args).validate_int_or_string, 'fail', '10a', astring)['msg']
    assert "expecting int value or '%s'" % astring in error


def test_rest_successfully_modify_with_admin_state():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('PATCH', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['success'])   # change admin_state
    ])
    module_args = {'admin_state': 'stopped'}
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_modify_with_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('POST', 'svm/svms', SRR['success']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('PATCH', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['success'])   # change admin_state
    ])
    module_args = {'admin_state': 'stopped'}
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']

# Tests for web services - 4 cases
# ZAPI: not supported
# REST < 9.8: not supported
# REST 9.8, 9.9. 9.10.0: only certificate is supported, using deprecated certificate fields in svs/svms
# REST >= 9.10.1: all options are supported, using svm/svms/uuid/web


def test_web_services_error_zapi():
    register_responses([
        ('GET', 'cluster', SRR['is_zapi']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = 'using web requires ONTAP 9.8 or later and REST must be enabled - Unreachable - using ZAPI.'
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_error_9_7_5():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_7_5']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = 'using web requires ONTAP 9.8 or later and REST must be enabled - ONTAP version: 9.7.5 - using REST.'
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_error_9_8_0():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    msg = "using ('client_enabled', 'ocsp_enabled') requires ONTAP 9.10.1 or later and REST must be enabled - ONTAP version: 9.8.0 - using REST."
    module_args = {'web': {'certificate': 'cert_name', 'client_enabled': True}}
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg
    module_args = {'web': {'certificate': 'cert_name', 'ocsp_enabled': True}}
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_modify_certificate_9_8_0_none_set():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),                          # get protocols
        ('PATCH', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['success'])  # change certificate
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_web_services_modify_certificate_9_8_0_other_set():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
        ('GET', 'svm/svms', SRR['svm_record_cert2']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),                          # get protocols
        ('PATCH', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7', SRR['success'])  # change certificate
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_web_services_modify_certificate_9_8_0_idempotent():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
        ('GET', 'svm/svms', SRR['svm_record_cert1']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),                          # get protocols
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    assert not create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_web_services_modify_certificate_9_8_0_error_not_found():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = "Error certificate not found: {'name': 'cert_name'}.  Current certificates with type=server: ['cert_1']"
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_modify_certificate_9_8_0_error_api1():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/certificates', SRR['generic_error']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = "Error retrieving certificate {'name': 'cert_name'}: calling: security/certificates: got Expected error."
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_modify_certificate_9_8_0_error_api2():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['generic_error']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = "Error retrieving certificates: calling: security/certificates: got Expected error."
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_modify_certificate_9_10_1_none_set():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web', SRR['zero_records']),
        ('PATCH', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web', SRR['success'])  # change certificate
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_web_services_modify_certificate_9_10_1_other_set():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web', SRR['svm_web_record_2']),
        ('PATCH', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web', SRR['success'])  # change certificate
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_web_services_modify_certificate_9_10_1_idempotent():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web', SRR['svm_web_record_1']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    assert not create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_web_services_modify_certificate_9_10_1_error_not_found():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['zero_records']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = "Error certificate not found: {'name': 'cert_name'}.  Current certificates with type=server: ['cert_1']"
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg
    msg = "Error certificate not found: {'name': 'cert_name'}.  Current certificates with type=server: []"
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_modify_certificate_9_10_1_error_api1():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['generic_error']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = "Error retrieving certificate {'name': 'cert_name'}: calling: security/certificates: got Expected error."
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_modify_certificate_9_10_1_error_api2():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['zero_records']),
        ('GET', 'security/certificates', SRR['generic_error']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = "Error retrieving certificates: calling: security/certificates: got Expected error."
    assert create_module(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_modify_certificate_9_10_1_error_api3():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web', SRR['generic_error']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = 'Error retrieving web info: calling: svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web: got Expected error.'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_modify_certificate_9_10_1_error_api4():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
        ('GET', 'svm/svms', SRR['svm_record']),
        ('GET', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web', SRR['svm_web_record_2']),
        ('PATCH', 'svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web', SRR['generic_error'])  # change certificate
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = "Error in modify web service for {'certificate': {'uuid': 'cert_uuid_1'}}: "\
          "calling: svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web: got Expected error."
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_web_services_modify_certificate_9_10_1_warning():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'security/certificates', SRR['certificate_record_1']),
    ])
    module_args = {'web': {'certificate': 'cert_name'}}
    msg = "Error in modify web service for {'certificate': {'uuid': 'cert_uuid_1'}}: "\
          "calling: svm/svms/09e9fd5e-8ebd-11e9-b162-005056b39fe7/web: got Expected error."
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    assert my_obj.modify_web_services({}, {'uuid': 'uuid'}) is None
    assert_warning_was_raised('Nothing to change: {}')
    clear_warnings()
    assert my_obj.modify_web_services({'certificate': {'name': 'whatever'}}, {'uuid': 'uuid'}) is None
    assert_warning_was_raised("Nothing to change: {'certificate': {}}")
    clear_warnings()
    assert my_obj.modify_web_services({'certificate': {}}, {'uuid': 'uuid'}) is None
    assert_warning_was_raised("Nothing to change: {'certificate': {}}")


def test_rest_cli_max_volumes_get():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['svm_record_ap']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),
    ])
    module_args = {
        'max_volumes': 3333,
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    record = my_obj.get_vserver()
    assert 'name' in SRR['svm_record_ap'][1]['records'][0]
    assert 'max_volumes' not in SRR['svm_record_ap'][1]['records'][0]
    assert 'max_volumes' in record


def test_rest_cli_max_volumes_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('POST', 'svm/svms', SRR['success']),
        ('PATCH', 'private/cli/vserver', SRR['success']),
    ])
    module_args = {
        'max_volumes': 3333,
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_rest_cli_max_volumes_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['svm_record_ap']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),
        ('PATCH', 'private/cli/vserver', SRR['success']),
    ])
    module_args = {
        'max_volumes': 3333,
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_error_rest_cli_max_volumes_get():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['svm_record_ap']),
        ('GET', 'private/cli/vserver', SRR['generic_error']),
    ])
    module_args = {
        'max_volumes': 3333,
    }
    msg = 'Error getting vserver info: calling: private/cli/vserver: got Expected error. - None'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_error_rest_cli_max_volumes_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['svm_record_ap']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),
        ('PATCH', 'private/cli/vserver', SRR['generic_error']),
    ])
    module_args = {
        'max_volumes': 3333,
    }
    msg = 'Error updating max_volumes: calling: private/cli/vserver: got Expected error. - None'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_cli_add_remove_protocols_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('POST', 'svm/svms', SRR['success']),
        ('PATCH', 'private/cli/vserver/add-protocols', SRR['success']),
        ('PATCH', 'private/cli/vserver/remove-protocols', SRR['success']),
    ])
    module_args = {
        'allowed_protocols': 'nfs,cifs',
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_error_rest_cli_add_protocols_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['zero_records']),
        ('POST', 'svm/svms', SRR['success']),
        ('PATCH', 'private/cli/vserver/add-protocols', SRR['generic_error']),
    ])
    module_args = {
        'allowed_protocols': 'nfs,cifs',
    }
    msg = 'Error adding protocols: calling: private/cli/vserver/add-protocols: got Expected error. - None'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_rest_cli_remove_protocols_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['svm_record_ap']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),
        ('PATCH', 'private/cli/vserver/remove-protocols', SRR['success']),
    ])
    module_args = {
        'allowed_protocols': 'nfs,cifs',
    }
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args)['changed']


def test_error_rest_cli_remove_protocols_modify():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'svm/svms', SRR['svm_record_ap']),
        ('GET', 'private/cli/vserver', SRR['cli_record']),
        ('PATCH', 'private/cli/vserver/remove-protocols', SRR['generic_error']),
    ])
    module_args = {
        'allowed_protocols': 'nfs,cifs',
    }
    msg = 'Error removing protocols: calling: private/cli/vserver/remove-protocols: got Expected error. - None'
    assert create_and_apply(svm_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == msg


def test_add_parameter_to_dict():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'name': 'svm',
        'ipspace': 'ipspace',
        'max_volumes': 3333,
    }
    my_obj = create_module(svm_module, DEFAULT_ARGS, module_args)
    test_dict = {}
    my_obj.add_parameter_to_dict(test_dict, 'name', None)
    my_obj.add_parameter_to_dict(test_dict, 'ipspace', 'ipspace_key')
    my_obj.add_parameter_to_dict(test_dict, 'max_volumes', None, True)
    print(test_dict)
    assert test_dict['name'] == 'svm'
    assert test_dict['ipspace_key'] == 'ipspace'
    assert test_dict['max_volumes'] == '3333'
