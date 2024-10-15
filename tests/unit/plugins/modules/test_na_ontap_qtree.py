# (c) 2018-2024, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_quotas '''
from __future__ import (absolute_import, division, print_function)

__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, \
    call_main, create_module, create_and_apply, expect_and_capture_ansible_exception, assert_warning_was_raised, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_qtree \
    import NetAppOntapQTree as qtree_module, main as my_main    # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


DEFAULT_ARGS = {
    'state': 'present',
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'ansible',
    'vserver': 'ansible',
    'flexvol_name': 'ansible',
    'export_policy': 'ansible',
    'security_style': 'unix',
    'unix_permissions': '755',
    'use_rest': 'never'
}


qtree_info = {
    'num-records': 1,
    'attributes-list': {
        'qtree-info': {
            'export-policy': 'ansible',
            'vserver': 'ansible',
            'qtree': 'ansible',
            'oplocks': 'enabled',
            'security-style': 'unix',
            'mode': '755',
            'volume': 'ansible'
        }
    }
}


ZRR = zapi_responses({
    'qtree_info': build_zapi_response(qtree_info)
})


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'qtree_record': (200, {"records": [{
        "svm": {"name": "ansible"},
        "id": 1,
        "name": "ansible",
        "security_style": "unix",
        "unix_permissions": 755,
        "export_policy": {"name": "ansible"},
        "volume": {"uuid": "uuid", "name": "volume1"}}
    ]}, None),
    'job_info': (200, {
        "job": {
            "uuid": "d78811c1-aebc-11ec-b4de-005056b30cfa",
            "_links": {"self": {"href": "/api/cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa"}}
        }}, None),
    'job_not_found': (404, "", {"message": "entry doesn't exist", "code": "4", "target": "uuid"}),
    'process_running_error': (400, None, "calling: storage/qtrees/1: got job reported error: Timeout error: Process still running, \
                                          received {'job': {'uuid': 'd708b0a5-d197-11ee-9138-d039ea45654b', '_links': {'self': {'href': \
                                          '/api/cluster/jobs/d708b0a5-d197-11ee-9138-d039ea45654b'}}}}.."),
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname", "name", "vserver", "flexvol_name"]
    error = create_module(qtree_module, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_ensure_get_called():
    ''' test get_qtree for non-existent qtree'''
    register_responses([
        ('qtree-list-iter', ZRR['empty'])
    ])
    my_obj = create_module(qtree_module, DEFAULT_ARGS)
    portset = my_obj.get_qtree()
    assert portset is None


def test_ensure_get_called_existing():
    ''' test get_qtree for existing qtree'''
    register_responses([
        ('qtree-list-iter', ZRR['qtree_info'])
    ])
    my_obj = create_module(qtree_module, DEFAULT_ARGS)
    assert my_obj.get_qtree()


def test_successful_create():
    ''' creating qtree '''
    register_responses([
        ('qtree-list-iter', ZRR['empty']),
        ('qtree-create', ZRR['success'])
    ])
    module_args = {
        'oplocks': 'enabled'
    }
    assert create_and_apply(qtree_module, DEFAULT_ARGS, module_args)['changed']


def test_successful_delete():
    ''' deleting qtree '''
    register_responses([
        ('qtree-list-iter', ZRR['qtree_info']),
        ('qtree-delete', ZRR['success'])
    ])
    args = {'state': 'absent'}
    assert create_and_apply(qtree_module, DEFAULT_ARGS, args)['changed']


def test_successful_delete_idempotency():
    ''' deleting qtree idempotency '''
    register_responses([
        ('qtree-list-iter', ZRR['empty'])
    ])
    args = {'state': 'absent'}
    assert create_and_apply(qtree_module, DEFAULT_ARGS, args)['changed'] is False


def test_successful_modify():
    ''' modifying qtree '''
    register_responses([
        ('qtree-list-iter', ZRR['qtree_info']),
        ('qtree-modify', ZRR['success'])
    ])
    args = {
        'export_policy': 'test',
        'oplocks': 'enabled'
    }
    assert create_and_apply(qtree_module, DEFAULT_ARGS, args)['changed']


def test_failed_rename():
    ''' test error rename qtree '''
    register_responses([
        ('qtree-list-iter', ZRR['empty']),
        ('qtree-list-iter', ZRR['empty'])
    ])
    args = {'from_name': 'test'}
    error = 'Error renaming: qtree %s does not exist' % args['from_name']
    assert error in create_and_apply(qtree_module, DEFAULT_ARGS, args, fail=True)['msg']


def test_successful_rename():
    ''' rename qtree '''
    register_responses([
        ('qtree-list-iter', ZRR['empty']),
        ('qtree-list-iter', ZRR['qtree_info']),
        ('qtree-rename', ZRR['success'])
    ])
    args = {'from_name': 'ansible_old'}
    assert create_and_apply(qtree_module, DEFAULT_ARGS, args)['changed']


def test_if_all_methods_catch_exception():
    ''' test error zapi - get/create/rename/modify/delete'''
    register_responses([
        ('qtree-list-iter', ZRR['error']),
        ('qtree-create', ZRR['error']),
        ('qtree-rename', ZRR['error']),
        ('qtree-modify', ZRR['error']),
        ('qtree-delete', ZRR['error'])
    ])
    qtree_obj = create_module(qtree_module, DEFAULT_ARGS, {'from_name': 'name'})

    assert 'Error fetching qtree' in expect_and_capture_ansible_exception(qtree_obj.get_qtree, 'fail')['msg']
    assert 'Error creating qtree' in expect_and_capture_ansible_exception(qtree_obj.create_qtree, 'fail')['msg']
    assert 'Error renaming qtree' in expect_and_capture_ansible_exception(qtree_obj.rename_qtree, 'fail')['msg']
    assert 'Error modifying qtree' in expect_and_capture_ansible_exception(qtree_obj.modify_qtree, 'fail')['msg']
    assert 'Error deleting qtree' in expect_and_capture_ansible_exception(qtree_obj.delete_qtree, 'fail')['msg']


def test_get_error_rest():
    ''' test get qtree error in rest'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['generic_error'])
    ])
    error = 'Error fetching qtree'
    assert error in create_and_apply(qtree_module, DEFAULT_ARGS, {'use_rest': 'always'}, 'fail')['msg']


def test_create_error_rest():
    ''' test get qtree error in rest'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['empty_records']),
        ('POST', 'storage/qtrees', SRR['generic_error'])
    ])
    error = 'Error creating qtree'
    assert error in create_and_apply(qtree_module, DEFAULT_ARGS, {'use_rest': 'always'}, 'fail')['msg']


def test_modify_error_rest():
    ''' test get qtree error in rest'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['qtree_record']),
        ('PATCH', 'storage/qtrees/uuid/1', SRR['generic_error'])
    ])
    args = {'use_rest': 'always', 'unix_permissions': '777'}
    error = 'Error modifying qtree'
    assert error in create_and_apply(qtree_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_rename_error_rest():
    ''' test get qtree error in rest'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['empty_records']),
        ('GET', 'storage/qtrees', SRR['empty_records'])
    ])
    args = {'use_rest': 'always', 'from_name': 'abcde', 'name': 'qtree'}
    error = 'Error renaming: qtree'
    assert error in create_and_apply(qtree_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_delete_error_rest():
    ''' test get qtree error in rest'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['qtree_record']),
        ('DELETE', 'storage/qtrees/uuid/1', SRR['generic_error'])
    ])
    args = {'use_rest': 'always', 'state': 'absent'}
    error = 'Error deleting qtree'
    assert error in create_and_apply(qtree_module, DEFAULT_ARGS, args, 'fail')['msg']


def test_successful_create_rest():
    ''' test create qtree rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['empty_records']),
        ('POST', 'storage/qtrees', SRR['success'])
    ])
    assert create_and_apply(qtree_module, DEFAULT_ARGS, {'use_rest': 'always'})['changed']


def test_idempotent_create_rest():
    ''' test create qtree idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['qtree_record'])
    ])
    assert create_and_apply(qtree_module, DEFAULT_ARGS, {'use_rest': 'always'})['changed'] is False


@patch('time.sleep')
def test_successful_create_rest_job_error(sleep):
    ''' test create qtree rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['empty_records']),
        ('POST', 'storage/qtrees', SRR['job_info']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found']),
        ('GET', 'cluster/jobs/d78811c1-aebc-11ec-b4de-005056b30cfa', SRR['job_not_found'])
    ])
    assert create_and_apply(qtree_module, DEFAULT_ARGS, {'use_rest': 'always'})['changed']
    print_warnings()
    assert_warning_was_raised('Ignoring job status, assuming success.')


def test_successful_delete_rest():
    ''' test delete qtree rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['qtree_record']),
        ('DELETE', 'storage/qtrees/uuid/1', SRR['success'])
    ])
    args = {'use_rest': 'always', 'state': 'absent'}
    assert create_and_apply(qtree_module, DEFAULT_ARGS, args)['changed']


def test_idempotent_delete_rest():
    ''' test delete qtree idempotency'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['empty_records'])
    ])
    args = {'use_rest': 'always', 'state': 'absent'}
    assert create_and_apply(qtree_module, DEFAULT_ARGS, args)['changed'] is False


def test_successful_delete_rest_job_running_warning():
    ''' test delete qtree warning in rest'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['qtree_record']),
        ('DELETE', 'storage/qtrees/uuid/1', SRR['process_running_error'])
    ])
    args = {'use_rest': 'always', 'state': 'absent', 'wait_for_completion': False}
    assert create_and_apply(qtree_module, DEFAULT_ARGS, args)['changed']
    print_warnings()
    assert_warning_was_raised("Process is still running in the background, exiting with no further waiting as 'wait_for_completion' is set to false.")


def test_successful_modify_rest():
    ''' test modify qtree rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['qtree_record']),
        ('PATCH', 'storage/qtrees/uuid/1', SRR['success'])
    ])
    args = {'use_rest': 'always', 'unix_permissions': '777'}
    assert create_and_apply(qtree_module, DEFAULT_ARGS, args)['changed']


def test_idempotent_modify_rest():
    ''' test modify qtree idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['qtree_record'])
    ])
    args = {'use_rest': 'always'}
    assert create_and_apply(qtree_module, DEFAULT_ARGS, {'use_rest': 'always'})['changed'] is False


def test_successful_rename_rest():
    ''' test rename qtree rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['zero_records']),
        ('GET', 'storage/qtrees', SRR['qtree_record']),
        ('PATCH', 'storage/qtrees/uuid/1', SRR['success'])
    ])
    args = {'use_rest': 'always', 'from_name': 'abcde', 'name': 'qtree'}
    assert create_and_apply(qtree_module, DEFAULT_ARGS, args)['changed']


def test_successful_rename_rest_idempotent():
    ''' test rename qtree in rest - idempotency'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['qtree_record'])
    ])
    args = {'use_rest': 'always', 'from_name': 'abcde'}
    assert create_and_apply(qtree_module, DEFAULT_ARGS, args)['changed'] is False


def test_successful_rename_and_modify_rest():
    ''' test rename and modify qtree rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['empty_records']),
        ('GET', 'storage/qtrees', SRR['qtree_record']),
        ('PATCH', 'storage/qtrees/uuid/1', SRR['success'])
    ])
    args = {
        'use_rest': 'always',
        'from_name': 'abcde',
        'name': 'qtree',
        'unix_permissions': '744',
        'unix_user': 'user',
        'unix_group': 'group',
    }
    assert call_main(my_main, DEFAULT_ARGS, args)['changed']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_missing_netapp_lib(mock_has_netapp_lib):
    module_args = {
        'use_rest': 'never'
    }
    mock_has_netapp_lib.return_value = False
    error = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert error == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_force_delete_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'storage/qtrees', SRR['qtree_record']),
    ])
    module_args = {
        'use_rest': 'always',
        'force_delete': False,
        'state': 'absent'
    }
    error = 'Error: force_delete option is not supported for REST, unless set to true.'
    assert error == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rename_qtree_not_used_with_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    my_obj = create_module(qtree_module, DEFAULT_ARGS, module_args)
    error = 'Internal error, use modify with REST'
    assert error in expect_and_capture_ansible_exception(my_obj.rename_qtree, 'fail')['msg']
