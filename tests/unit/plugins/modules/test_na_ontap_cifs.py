# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_cifs '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    patch_ansible, call_main, create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs \
    import NetAppONTAPCifsShare as my_module, main as my_main   # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # module specific responses
    'cifs_record': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansibleSVM"
                    },
                    "name": 'cifs_share_name',
                    "path": '/',
                    "comment": 'CIFS share comment',
                    "unix_symlink": 'widelink',
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    }
                }
            ],
            "num_records": 1
        }, None
    ),
    "no_record": (
        200,
        {"num_records": 0},
        None)
})

cifs_record_info = {
    'num-records': 1,
    'attributes-list': {
        'cifs-share': {
            'share-name': 'cifs_share_name',
            'path': '/test',
            'vscan-fileop-profile': 'standard',
            'share-properties': [{'cifs-share-properties': 'browsable'}, {'cifs-share-properties': 'show_previous_versions'}],
            'symlink-properties': [{'cifs-share-symlink-properties': 'enable'}]
        }
    }
}

ZRR = zapi_responses({
    'cifs_record_info': build_zapi_response(cifs_record_info)
})

DEFAULT_ARGS = {
    'hostname': 'test',
    'username': 'admin',
    'password': 'netapp1!',
    'name': 'cifs_share_name',
    'path': '/test',
    'share_properties': ['browsable', 'show-previous-versions'],
    'symlink_properties': 'enable',
    'vscan_fileop_profile': 'standard',
    'vserver': 'abc',
    'use_rest': 'never'
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    error = 'missing required arguments:'
    assert error in call_main(my_main, {}, fail=True)['msg']


def test_get():
    register_responses([
        ('cifs-share-get-iter', ZRR['cifs_record_info'])
    ])
    cifs_obj = create_module(my_module, DEFAULT_ARGS)
    result = cifs_obj.get_cifs_share()
    assert result


def test_error_create():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['empty']),
        ('cifs-share-create', ZRR['error']),
    ])
    module_args = {
        'state': 'present'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, fail=True)['msg']
    assert 'Error creating cifs-share' in error


def test_create():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['empty']),
        ('cifs-share-create', ZRR['success']),
    ])
    module_args = {
        'state': 'present',
        'comment': 'some_comment'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['cifs_record_info']),
        ('cifs-share-delete', ZRR['success']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_delete():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['cifs_record_info']),
        ('cifs-share-delete', ZRR['error']),
    ])
    module_args = {
        'state': 'absent'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Error deleting cifs-share' in error


def test_modify_path():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['cifs_record_info']),
        ('cifs-share-modify', ZRR['success']),
    ])
    module_args = {
        'path': '//'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_comment():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['cifs_record_info']),
        ('cifs-share-modify', ZRR['success']),
    ])
    module_args = {
        'comment': 'cifs modify'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_share_properties():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['cifs_record_info']),
        ('cifs-share-modify', ZRR['success']),
    ])
    module_args = {
        'share_properties': 'oplocks'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_symlink_properties():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['cifs_record_info']),
        ('cifs-share-modify', ZRR['success']),
    ])
    module_args = {
        'symlink_properties': 'read_only'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_vscan_fileop_profile():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['cifs_record_info']),
        ('cifs-share-modify', ZRR['success']),
    ])
    module_args = {
        'vscan_fileop_profile': 'strict'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_modify():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['cifs_record_info']),
        ('cifs-share-modify', ZRR['error']),
    ])
    module_args = {
        'symlink_properties': 'read'
    }
    error = create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Error modifying cifs-share' in error


def test_create_idempotency():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['cifs_record_info'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS)['changed'] is False


def test_delete_idempotency():
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('cifs-share-get-iter', ZRR['empty'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed'] is False


def test_if_all_methods_catch_exception():
    register_responses([
        ('cifs-share-create', ZRR['error']),
        ('cifs-share-modify', ZRR['error']),
        ('cifs-share-delete', ZRR['error'])
    ])
    module_args = {}

    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    error = expect_and_capture_ansible_exception(my_obj.create_cifs_share, 'fail')['msg']
    assert 'Error creating cifs-share cifs_share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.modify_cifs_share, 'fail')['msg']
    assert 'Error modifying cifs-share cifs_share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error

    error = expect_and_capture_ansible_exception(my_obj.delete_cifs_share, 'fail')['msg']
    assert 'Error deleting cifs-share cifs_share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose' in error


ARGS_REST = {
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'always',
    'vserver': 'test_vserver',
    'name': 'cifs_share_name',
    'path': '/',
    'unix_symlink': 'widelink',
}


def test_rest_successful_create():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['empty_records']),
        ('POST', 'protocols/cifs/shares', SRR['empty_good']),
    ])
    module_args = {
        'comment': 'CIFS share comment',
        'unix_symlink': 'disable'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_delete_rest():
    ''' Test delete with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('DELETE', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good']),
    ])
    module_args = {
        'state': 'absent',
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_rest_error_get():
    '''Test error rest get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on fetching cifs shares: calling: protocols/cifs/shares: got Expected error.' in error


def test_rest_error_create():
    '''Test error rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['empty_records']),
        ('POST', 'protocols/cifs/shares', SRR['generic_error']),
    ])
    error = create_and_apply(my_module, ARGS_REST, fail=True)['msg']
    assert 'Error on creating cifs shares:' in error


def test_error_delete_rest():
    ''' Test error delete with rest API'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('DELETE', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['generic_error']),
    ])
    module_args = {
        'state': 'absent'
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on deleting cifs shares:' in error


def test_modify_cifs_share_path():
    ''' test modify CIFS share path '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('PATCH', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/cifs_share_name', SRR['empty_good']),
    ])
    module_args = {
        'path': "\\vol1"
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_modify_cifs_share_properties():
    ''' test modify CIFS share properties '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('PATCH', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/cifs_share_name', SRR['empty_good']),
    ])
    module_args = {
        'unix_symlink': "disable"
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_modify_cifs_share_comment():
    ''' test modify CIFS share comment '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('PATCH', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/cifs_share_name', SRR['empty_good']),
    ])
    module_args = {
        'comment': "cifs comment modify"
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)


def test_error_modify_cifs_share_path():
    ''' test modify CIFS share path error'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('PATCH', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/cifs_share_name', SRR['generic_error']),
    ])
    module_args = {
        'path': "\\vol1"
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on modifying cifs shares:' in error


def test_error_modify_cifs_share_comment():
    ''' test modify CIFS share comment error'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record']),
        ('PATCH', 'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/cifs_share_name', SRR['generic_error']),
    ])
    module_args = {
        'comment': "cifs comment modify"
    }
    error = create_and_apply(my_module, ARGS_REST, module_args, fail=True)['msg']
    assert 'Error on modifying cifs shares:' in error


def test_rest_successful_create_idempotency():
    '''Test successful rest create'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['cifs_record'])
    ])
    module_args = {
        'use_rest': 'always'
    }
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed'] is False


def test_rest_successful_delete_idempotency():
    '''Test successful rest delete'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/cifs/shares', SRR['empty_records'])
    ])
    module_args = {'use_rest': 'always', 'state': 'absent'}
    assert create_and_apply(my_module, ARGS_REST, module_args)['changed'] is False


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_missing_netapp_lib(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    msg = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert msg == call_main(my_main, DEFAULT_ARGS, fail=True)['msg']
