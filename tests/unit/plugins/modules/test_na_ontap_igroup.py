# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, patch_ansible, create_module, create_and_apply, assert_warning_was_raised, assert_no_warnings, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_igroup \
    import NetAppOntapIgroup as igroup  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')


DEFAULT_ARGS = {
    'vserver': 'vserver',
    'name': 'test',
    'initiator_names': 'init1',
    'ostype': 'linux',
    'initiator_group_type': 'fcp',
    'bind_portset': 'true',
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'never'
}

igroup_with_initiator = {
    'num-records': 1,
    'attributes-list': {
        'vserver': 'vserver',
        'initiator-group-os-type': 'linux',
        'initiator-group-info': {
            'initiators': [
                {'initiator-info': {'initiator-name': 'init1'}},
                {'initiator-info': {'initiator-name': 'init2'}}
            ]
        }
    }
}

igroup_without_initiator = {
    'num-records': 1,
    'attributes-list': {
        'initiator-group-info': {'vserver': 'test'}
    }
}

ZRR = zapi_responses({
    'igroup_with_initiator_info': build_zapi_response(igroup_with_initiator),
    'igroup_without_initiator_info': build_zapi_response(igroup_without_initiator)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        igroup()
    msg = 'missing required arguments:'
    assert msg in exc.value.args[0]['msg']


def test_get_nonexistent_igroup():
    ''' Test if get_igroup returns None for non-existent igroup '''
    register_responses([
        ('igroup-get-iter', ZRR['empty'])
    ])
    igroup_obj = create_module(igroup, DEFAULT_ARGS)
    result = igroup_obj.get_igroup('dummy')
    assert result is None


def test_get_existing_igroup_with_initiators():
    ''' Test if get_igroup returns list of existing initiators '''
    register_responses([
        ('igroup-get-iter', ZRR['igroup_with_initiator_info'])
    ])
    igroup_obj = create_module(igroup, DEFAULT_ARGS)
    result = igroup_obj.get_igroup('igroup')
    assert DEFAULT_ARGS['initiator_names'] in result['initiator_names']
    assert result['initiator_names'] == ['init1', 'init2']


def test_get_existing_igroup_without_initiators():
    ''' Test if get_igroup returns empty list() '''
    register_responses([
        ('igroup-get-iter', ZRR['igroup_without_initiator_info'])
    ])
    igroup_obj = create_module(igroup, DEFAULT_ARGS)
    result = igroup_obj.get_igroup('igroup')
    assert result['initiator_names'] == []


def test_modify_initiator_calls_add_and_remove():
    '''Test remove_initiator() is called followed by add_initiator() on modify operation'''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('igroup-get-iter', ZRR['igroup_with_initiator_info']),
        ('igroup-remove', ZRR['success']),
        ('igroup-remove', ZRR['success']),
        ('igroup-add', ZRR['success'])
    ])
    igroup_obj = create_and_apply(igroup, DEFAULT_ARGS, {'initiator_names': 'replacewithme'})['changed']


def test_modify_called_from_add():
    '''Test remove_initiator() and add_initiator() calls modify'''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('igroup-get-iter', ZRR['igroup_without_initiator_info']),
        ('igroup-add', ZRR['success'])
    ])
    igroup_obj = create_and_apply(igroup, DEFAULT_ARGS, {'initiator_names': 'replacewithme'})['changed']


def test_modify_called_from_remove():
    '''Test remove_initiator() and add_initiator() calls modify'''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('igroup-get-iter', ZRR['igroup_with_initiator_info']),
        ('igroup-remove', ZRR['success']),
        ('igroup-remove', ZRR['success'])
    ])
    igroup_obj = create_and_apply(igroup, DEFAULT_ARGS, {'initiator_names': ''})['changed']


def test_successful_create():
    ''' Test successful create '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('igroup-get-iter', ZRR['empty']),
        ('igroup-create', ZRR['success']),
        ('igroup-add', ZRR['success'])
    ])
    igroup_obj = create_and_apply(igroup, DEFAULT_ARGS)['changed']


def test_successful_delete():
    ''' Test successful delete '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('igroup-get-iter', ZRR['igroup_with_initiator_info']),
        ('igroup-destroy', ZRR['success'])
    ])
    igroup_obj = create_and_apply(igroup, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_successful_rename():
    '''Test successful rename'''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('igroup-get-iter', ZRR['empty']),
        ('igroup-get-iter', ZRR['igroup_with_initiator_info']),
        ('igroup-rename', ZRR['success']),
        ('igroup-remove', ZRR['success']),
    ])
    args = {
        'from_name': 'test',
        'name': 'test_new'
    }
    assert create_and_apply(igroup, DEFAULT_ARGS, args)['changed']


def test_negative_modify_anything_zapi():
    ''' Test ZAPI option not currently supported in REST is rejected '''
    register_responses([
        ('ems-autosupport-log', ZRR['empty']),
        ('igroup-get-iter', ZRR['igroup_with_initiator_info']),
    ])
    args = {
        'vserver': 'my_vserver',
        'use_rest': 'never'
    }
    msg = "Error: modifying  {'vserver': 'my_vserver'} is not supported in ZAPI"
    assert msg in create_and_apply(igroup, DEFAULT_ARGS, args, fail=True)['msg']


def test_negative_mutually_exclusive():
    ''' Test ZAPI option not currently supported in REST is rejected '''
    args = {
        'use_rest': 'auto',
        'igroups': 'my_group'
    }
    msg = "parameters are mutually exclusive: igroups|initiator_names"
    assert msg in create_module(igroup, DEFAULT_ARGS, args, fail=True)['msg']


def test_negative_igroups_require_rest():
    ''' Test ZAPI option not currently supported in REST is rejected '''
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['initiator_names']
    args = {
        'igroups': 'my_group'
    }
    msg = "requires ONTAP 9.9.1 or later and REST must be enabled"
    assert msg in create_module(igroup, DEFAULT_ARGS_COPY, args, fail=True)['msg']


SRR = rest_responses({
    'one_igroup_record': (200, dict(records=[
        dict(uuid='a1b2c3',
             name='test',
             svm=dict(name='vserver'),
             initiators=[{'name': 'todelete'}],
             protocol='fcp',
             os_type='aix')
    ], num_records=1), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None)
})


def test_successful_create_rest():
    ''' Test successful create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['empty_records']),
        ('POST', 'protocols/san/igroups', SRR['success'])
    ])
    assert create_and_apply(igroup, DEFAULT_ARGS, {'use_rest': 'always'})['changed']


def test_incomplete_record_rest():
    ''' Test successful create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['one_record_uuid'])
    ])
    msg = "Error: unexpected igroup body:"
    assert msg in create_and_apply(igroup, DEFAULT_ARGS, {'use_rest': 'always'}, fail=True)['msg']


def test_successful_delete_rest():
    ''' Test successful delete '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['one_igroup_record']),
        ('DELETE', 'protocols/san/igroups/a1b2c3', SRR['success'])
    ])
    args = {'state': 'absent', 'use_rest': 'always'}
    assert create_and_apply(igroup, DEFAULT_ARGS, args)['changed']


def test_successful_modify_rest():
    ''' Test successful modify '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['one_igroup_record']),
        ('DELETE', 'protocols/san/igroups/a1b2c3/initiators/todelete', SRR['success']),
        ('POST', 'protocols/san/igroups/a1b2c3/initiators', SRR['success']),
        ('PATCH', 'protocols/san/igroups/a1b2c3', SRR['success'])
    ])
    assert create_and_apply(igroup, DEFAULT_ARGS, {'use_rest': 'always'})['changed']


def test_successful_modify_initiator_objects_rest():
    ''' Test successful modify '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/igroups', SRR['one_igroup_record']),
        ('DELETE', 'protocols/san/igroups/a1b2c3/initiators/todelete', SRR['success']),
        ('POST', 'protocols/san/igroups/a1b2c3/initiators', SRR['success']),
        ('PATCH', 'protocols/san/igroups/a1b2c3', SRR['success'])
    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['initiator_names']
    DEFAULT_ARGS_COPY['initiator_objects'] = [{'name': 'init1', 'comment': 'comment1'}]
    assert create_and_apply(igroup, DEFAULT_ARGS_COPY, {'use_rest': 'always'})['changed']


def test_successful_modify_initiator_objects_comment_rest():
    ''' Test successful modify '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/igroups', SRR['one_igroup_record']),
        ('PATCH', 'protocols/san/igroups/a1b2c3/initiators/todelete', SRR['success']),
        ('PATCH', 'protocols/san/igroups/a1b2c3', SRR['success'])
    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['initiator_names']
    DEFAULT_ARGS_COPY['initiator_objects'] = [{'name': 'todelete', 'comment': 'comment1'}]
    assert create_and_apply(igroup, DEFAULT_ARGS_COPY, {'use_rest': 'always'})['changed']


def test_successful_modify_igroups_rest():
    ''' Test successful modify '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/igroups', SRR['one_igroup_record']),
        ('DELETE', 'protocols/san/igroups/a1b2c3/initiators/todelete', SRR['success']),
        ('POST', 'protocols/san/igroups/a1b2c3/igroups', SRR['success']),
        ('PATCH', 'protocols/san/igroups/a1b2c3', SRR['success'])
    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['initiator_names']
    args = {
        'igroups': ['test_igroup'],
        'use_rest': 'auto',
        'force_remove_initiator': True
    }
    assert create_and_apply(igroup, DEFAULT_ARGS_COPY, args)['changed']


def test_9_9_0_no_igroups_rest():
    ''' Test failed to use igroups '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['initiator_names']
    args = {
        'igroups': ['test_igroup'],
        'use_rest': 'always'
    }
    msg = 'Error: using igroups requires ONTAP 9.9.1 or later and REST must be enabled - ONTAP version: 9.9.0.'
    assert msg in create_module(igroup, DEFAULT_ARGS_COPY, args, fail=True)['msg']


def test_successful_rename_rest():
    '''Test successful rename'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'protocols/san/igroups', SRR['empty_records']),
        ('GET', 'protocols/san/igroups', SRR['one_igroup_record']),
        ('DELETE', 'protocols/san/igroups/a1b2c3/initiators/todelete', SRR['success']),
        ('POST', 'protocols/san/igroups/a1b2c3/initiators', SRR['success']),
        ('PATCH', 'protocols/san/igroups/a1b2c3', SRR['success'])
    ])
    args = {
        'use_rest': 'always',
        'from_name': 'test',
        'name': 'test_new'
    }
    assert create_and_apply(igroup, DEFAULT_ARGS, args)['changed']


def test_negative_zapi_or_rest99_option():
    ''' Test ZAPI option not currently supported in REST is rejected '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0'])
    ])
    args = {
        'use_rest': 'always',
        'bind_portset': 'my_portset'
    }
    create_module(igroup, DEFAULT_ARGS, args)
    msg = "Warning: falling back to ZAPI: using bind_portset requires ONTAP 9.9 or later and REST must be enabled - ONTAP version: 9.8.0."
    print_warnings()
    assert_warning_was_raised(msg)


def test_positive_zapi_or_rest99_option():
    ''' Test ZAPI option not currently supported in REST forces ZAPI calls '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0'])
    ])
    args = {
        'use_rest': 'auto',
        'bind_portset': 'my_portset'
    }
    create_module(igroup, DEFAULT_ARGS, args)
    msg = "Warning: falling back to ZAPI: using bind_portset requires ONTAP 9.9 or later and REST must be enabled - ONTAP version: 9.8.0."
    print_warnings()
    assert_warning_was_raised(msg)


def test_create_rest_99():
    ''' Test 9.9 option works with REST '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['empty_records']),
        ('POST', 'protocols/san/igroups', SRR['success'])
    ])
    args = {
        'use_rest': 'auto',
        'bind_portset': 'my_portset'
    }
    assert create_and_apply(igroup, DEFAULT_ARGS, args)['changed']
    print_warnings
    assert_no_warnings()


def test_negative_modify_vserver_rest():
    ''' Test ZAPI option not currently supported in REST is rejected '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'protocols/san/igroups', SRR['one_igroup_record'])
    ])
    args = {
        'vserver': 'my_vserver',
        'use_rest': 'always'
    }
    msg = "Error: modifying  {'vserver': 'my_vserver'} is not supported in REST"
    assert msg in create_and_apply(igroup, DEFAULT_ARGS, args, fail=True)['msg']


def test_negative_igroups_require_9_9():
    ''' Test ZAPI option not currently supported in REST is rejected '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0'])
    ])
    DEFAULT_ARGS_COPY = DEFAULT_ARGS.copy()
    del DEFAULT_ARGS_COPY['initiator_names']
    args = {
        'igroups': 'test_igroup',
        'use_rest': 'always'
    }
    msg = "requires ONTAP 9.9.1 or later and REST must be enabled"
    assert msg in create_module(igroup, DEFAULT_ARGS_COPY, args, fail=True)['msg']
