# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible, create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, \
    register_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_igroup_initiator \
    import NetAppOntapIgroupInitiator as initiator  # module under test
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'state': 'present',
    'vserver': 'vserver',
    'name': 'init1',
    'initiator_group': 'test',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'use_rest': 'never'
}


initiator_info = {
    'num-records': 1,
    'attributes-list': {
        'initiator-group-info': {
            'initiators': [
                {'initiator-info': {'initiator-name': 'init1'}},
                {'initiator-info': {'initiator-name': 'init2'}}
            ]
        }
    }
}


ZRR = zapi_responses({
    'initiator_info': build_zapi_response(initiator_info)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        initiator()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_get_nonexistent_igroup():
    ''' Test if get_initiators returns None for non-existent initiator '''
    register_responses([
        ('igroup-get-iter', ZRR['empty'])
    ])
    initiator_obj = create_module(initiator, DEFAULT_ARGS)
    result = initiator_obj.get_initiators()
    assert result == []


def test_get_existing_initiator():
    ''' Test if get_initiator returns None for existing initiator '''
    register_responses([
        ('igroup-get-iter', ZRR['initiator_info'])
    ])
    initiator_obj = create_module(initiator, DEFAULT_ARGS)
    result = initiator_obj.get_initiators()
    assert DEFAULT_ARGS['name'] in result
    assert result == ['init1', 'init2']     # from build_igroup_initiators()


def test_successful_add():
    ''' Test successful add'''
    register_responses([
        ('igroup-get-iter', ZRR['initiator_info']),
        ('igroup-add', ZRR['success'])
    ])
    args = {'name': 'init3'}
    assert create_and_apply(initiator, DEFAULT_ARGS, args)['changed']


def test_successful_add_idempotency():
    ''' Test successful add idempotency '''
    register_responses([
        ('igroup-get-iter', ZRR['initiator_info'])
    ])
    assert create_and_apply(initiator, DEFAULT_ARGS)['changed'] is False


def test_successful_remove():
    ''' Test successful remove '''
    register_responses([
        ('igroup-get-iter', ZRR['initiator_info']),
        ('igroup-remove', ZRR['success'])
    ])
    args = {'state': 'absent'}
    assert create_and_apply(initiator, DEFAULT_ARGS, args)['changed']


def test_successful_remove_idempotency():
    ''' Test successful remove idempotency'''
    register_responses([
        ('igroup-get-iter', ZRR['initiator_info'])
    ])
    args = {'state': 'absent', 'name': 'alreadyremoved'}
    assert create_and_apply(initiator, DEFAULT_ARGS)['changed'] is False


def test_if_all_methods_catch_exception():
    register_responses([
        ('igroup-get-iter', ZRR['error']),
        ('igroup-add', ZRR['error']),
        ('igroup-remove', ZRR['error'])
    ])
    initiator_obj = create_module(initiator, DEFAULT_ARGS)

    error = expect_and_capture_ansible_exception(initiator_obj.get_initiators, 'fail')['msg']
    assert 'Error fetching igroup info' in error

    error = expect_and_capture_ansible_exception(initiator_obj.modify_initiator, 'fail', 'init4', 'igroup-add')['msg']
    assert 'Error modifying igroup initiator' in error

    error = expect_and_capture_ansible_exception(initiator_obj.modify_initiator, 'fail', 'init4', 'igroup-remove')['msg']
    assert 'Error modifying igroup initiator' in error


SRR = rest_responses({
    'initiator_info': (200, {"records": [
        {
            "svm": {"name": "svm1"},
            "uuid": "897de45f-bbbf-11ec-9f18-005056b3b297",
            "name": "init1",
            "initiators": [
                {"name": "iqn.2001-04.com.example:abc123"},
                {"name": "iqn.2001-04.com.example:abc124"},
                {'name': 'init3'}
            ]
        }
    ], "num_records": 1}, None),
    'igroup_without_intiators': (200, {"records": [
        {
            "svm": {"name": "svm1"},
            "uuid": "897de45f-bbbf-11ec-9f18-005056alr297",
            "name": "init22",
        }
    ], "num_records": 1}, None)
})


def test_successful_add_rest():
    ''' Test successful add'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['initiator_info']),
        ('POST', 'protocols/san/igroups/897de45f-bbbf-11ec-9f18-005056b3b297/initiators', SRR['success'])
    ])
    assert create_and_apply(initiator, DEFAULT_ARGS, {'use_rest': 'always'})['changed']


def test_successful_add_idempotency_rest():
    ''' Test successful add idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['initiator_info'])
    ])
    args = {'use_rest': 'always', 'name': 'iqn.2001-04.com.example:abc123'}
    assert create_and_apply(initiator, DEFAULT_ARGS, args)['changed'] is False


def test_successful_add_to_0_initiator_igroup_rest():
    ''' Test successful add'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['igroup_without_intiators']),
        ('POST', 'protocols/san/igroups/897de45f-bbbf-11ec-9f18-005056alr297/initiators', SRR['success'])
    ])
    assert create_and_apply(initiator, DEFAULT_ARGS, {'use_rest': 'always'})['changed']


def test_successful_remove_rest():
    ''' Test successful remove '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['initiator_info']),
        ('DELETE', 'protocols/san/igroups/897de45f-bbbf-11ec-9f18-005056b3b297/initiators/init3', SRR['success'])
    ])
    args = {'use_rest': 'always', 'name': 'init3', 'state': 'absent'}
    assert create_and_apply(initiator, DEFAULT_ARGS, args)['changed']


def test_successful_remove_idempotency_rest():
    ''' Test successful remove idempotency'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['initiator_info'])
    ])
    args = {'use_rest': 'always', 'name': 'alreadyremoved', 'state': 'absent'}
    assert create_and_apply(initiator, DEFAULT_ARGS, args)['changed'] is False


def test_get_initiator_catch_exception_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['generic_error'])
    ])
    error = create_and_apply(initiator, DEFAULT_ARGS, {'use_rest': 'always'}, 'fail')['msg']
    assert 'Error fetching igroup info' in error


def test_add_initiator_catch_exception_rest():
    ''' Test add error'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['initiator_info']),
        ('POST', 'protocols/san/igroups/897de45f-bbbf-11ec-9f18-005056b3b297/initiators', SRR['generic_error'])
    ])
    error = create_and_apply(initiator, DEFAULT_ARGS, {'use_rest': 'always'}, 'fail')['msg']
    assert 'Error modifying igroup initiator' in error


def test_remove_initiator_catch_exception_rest():
    ''' Test remove error'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['initiator_info']),
        ('DELETE', 'protocols/san/igroups/897de45f-bbbf-11ec-9f18-005056b3b297/initiators/init3', SRR['generic_error'])
    ])
    args = {'use_rest': 'always', 'name': 'init3', 'state': 'absent'}
    error = create_and_apply(initiator, DEFAULT_ARGS, args, 'fail')['msg']
    assert 'Error modifying igroup initiator' in error


def test_error_uuid_not_found():
    ''' Test uuid error'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['empty_records'])
    ])
    args = {'use_rest': 'always'}
    error = create_and_apply(initiator, DEFAULT_ARGS, args, 'fail')['msg']
    assert 'Error modifying igroup initiator init1: igroup not found' in error
