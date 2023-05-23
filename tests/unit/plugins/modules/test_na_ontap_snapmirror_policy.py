# (c) 2019-2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_snapmirror_policy '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_error, build_zapi_response, zapi_error_message, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    call_main, create_module, patch_ansible, expect_and_capture_ansible_exception, create_and_apply

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapmirror_policy import NetAppOntapSnapMirrorPolicy as my_module, main as my_main

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'success': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'get_snapmirror_policy_async': (200, {
        'svm': {'name': 'ansible'},
        'name': 'ansible',
        'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
        'comment': 'created by ansible',
        'type': 'async',
        'snapmirror_label': [],
        'keep': [],
        'schedule': [],
        'prefix': [],
        'network_compression_enabled': True,
        'identity_preservation': 'exclude_network_config'
    }, None),
    'get_snapmirror_policy_async_with_options': (200, {
        'svm': {'name': 'ansible'},
        'name': 'ansible',
        'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
        'comment': 'created by ansible',
        'type': 'async',
        'snapmirror_label': [],
        'keep': [],
        'schedule': [],
        'prefix': [],
        'copy_latest_source_snapshot': True,
        'network_compression_enabled': True,
        'identity_preservation': 'exclude_network_config'
    }, None),
    'get_snapmirror_policy_sync': (200, {
        'svm': {'name': 'ansible'},
        'name': 'ansible',
        'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
        'comment': 'created by ansible',
        'type': 'sync',
        'snapmirror_label': [],
        'keep': [],
        'schedule': [],
        'prefix': [],
        'network_compression_enabled': False
    }, None),
    'get_snapmirror_policy_async_with_rules': (200, {
        'svm': {'name': 'ansible'},
        'name': 'ansible',
        'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
        'comment': 'created by ansible',
        'type': 'async',
        'retention': [
            {
                'label': 'daily',
                'count': 7,
                'creation_schedule': {'name': ''},
                'prefix': '',
            },
            {
                'label': 'weekly',
                'count': 5,
                'creation_schedule': {'name': 'weekly'},
                'prefix': 'weekly',
            },
            {
                'label': 'monthly',
                'count': 12,
                'creation_schedule': {'name': 'monthly'},
                'prefix': 'monthly',
            },
        ],
        'network_compression_enabled': False
    }, None),
    'get_snapmirror_policy_async_with_rules_dash': (200, {
        'svm': {'name': 'ansible'},
        'name': 'ansible',
        'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
        'comment': 'created by ansible',
        'type': 'async',
        'retention': [
            {
                'label': 'daily',
                'count': 7,
                'creation_schedule': {'name': ''},
                'prefix': '',
            },
            {
                'label': 'weekly',
                'count': 5,
                'creation_schedule': {'name': 'weekly'},
                'prefix': 'weekly',
            },
            {
                'label': 'monthly',
                'count': 12,
                'creation_schedule': {'name': '-'},
                'prefix': '-',
            },
        ],
        'network_compression_enabled': False
    }, None),
    'get_snapmirror_policy_async_with_create_snapshot_on_source': (200, {
        'svm': {'name': 'ansible'},
        'name': 'ansible',
        'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
        'comment': 'created by ansible',
        'type': 'async',
        'retention': [
            {
                'label': 'daily',
                'count': 7,
                'creation_schedule': {'name': ''},
                'prefix': '',
            },
        ],
        'create_snapshot_on_source': False,
        'is_network_compression_enabled': True,
        'transfer_schedule': {'name': 'yearly'},
    }, None),
    'get_snapmirror_policy_sync_with_sync_type': (200, {
        'svm': {'name': 'ansible'},
        'name': 'ansible',
        'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
        'comment': 'created by ansible',
        'type': 'sync',
        'sync_type': 'automated_failover',
        # does not make sense, but does not hurt
        'copy_all_source_snapshots': False
    }, None),
})


snapmirror_policy_info = {
    'comment': 'created by ansible',
    'policy-name': 'ansible',
    'type': 'async_mirror',
    'tries': '8',
    'transfer-priority': 'normal',
    'restart': 'always',
    'is-network-compression-enabled': 'false',
    'ignore-atime': 'false',
    'vserver-name': 'ansible',
    'common-snapshot-schedule': 'monthly'
}

snapmirror_policy_rules = {
    'snapmirror-policy-rules': [
        {'info': {
            'snapmirror-label': 'daily',
            'keep': 7,
            'schedule': '',
            'prefix': '',
        }},
        {'info': {
            'snapmirror-label': 'weekly',
            'keep': 5,
            'schedule': 'weekly',
            'prefix': 'weekly',
        }},
        {'info': {
            'snapmirror-label': 'monthly',
            'keep': 12,
            'schedule': 'monthly',
            'prefix': 'monthly',
        }},
        {'info': {
            'snapmirror-label': 'sm_created',
            'keep': 12,
            'schedule': 'monthly',
            'prefix': 'monthly',
        }},
    ]
}


def get_snapmirror_policy_info(with_rules=False):
    info = dict(snapmirror_policy_info)
    if with_rules:
        info.update(snapmirror_policy_rules)
    return {'attributes-list': {'snapmirror-policy-info': info}}


ZRR = zapi_responses({
    'snapmirror-policy-info': build_zapi_response(get_snapmirror_policy_info()),
    'snapmirror-policy-info-with-rules': build_zapi_response(get_snapmirror_policy_info(True)),
    'error_13001': build_zapi_error(13001, 'policy not found'),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'use_rest',
    'policy_name': 'ansible',
    'vserver': 'ansible',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('policy_name')
    error = 'missing required arguments: policy_name'
    assert error in call_main(my_main, args, fail=True)['msg']


def test_ensure_get_called():
    ''' test get_snapmirror_policy for non-existent snapmirror policy'''
    register_responses([
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_snapmirror_policy() is None


def test_ensure_get_called_existing():
    ''' test get_snapmirror_policy for existing snapmirror policy'''
    register_responses([
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['snapmirror-policy-info']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.get_snapmirror_policy()


def test_successful_create():
    ''' creating snapmirror policy without rules and testing idempotency '''
    register_responses([
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['no_records']),
        ('ZAPI', 'snapmirror-policy-create', ZRR['success']),
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['snapmirror-policy-info']),
    ])
    module_args = {
        'use_rest': 'never',
        'transfer_priority': 'normal'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_create_with_rest():
    ''' creating snapmirror policy without rules via REST and testing idempotency '''
    register_responses([
        # default is async
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['zero_records']),
        ('POST', 'snapmirror/policies', SRR['success']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async']),
        # explicitly async
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['zero_records']),
        ('POST', 'snapmirror/policies', SRR['success']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async_with_options']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async_with_options']),
        # sync
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['zero_records']),
        ('POST', 'snapmirror/policies', SRR['success']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_sync']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_sync']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['policy_type'] = 'async_mirror'
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['policy_type'] = 'sync_mirror'
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_create_with_rules():
    ''' creating snapmirror policy with rules and testing idempotency '''
    register_responses([
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['error_13001']),
        ('ZAPI', 'snapmirror-policy-create', ZRR['success']),
        ('ZAPI', 'snapmirror-policy-add-rule', ZRR['success']),
        ('ZAPI', 'snapmirror-policy-add-rule', ZRR['success']),
        ('ZAPI', 'snapmirror-policy-add-rule', ZRR['success']),
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['snapmirror-policy-info-with-rules']),
    ])
    module_args = {
        'use_rest': 'never',
        'snapmirror_label': ['daily', 'weekly', 'monthly'],
        'keep': [7, 5, 12],
        'schedule': ['', 'weekly', 'monthly'],
        'prefix': ['', 'weekly', 'monthly']
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_create_with_rules_via_rest():
    ''' creating snapmirror policy with rules via rest and testing idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['zero_records']),
        ('POST', 'snapmirror/policies', SRR['success']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async']),
        ('PATCH', 'snapmirror/policies/abcdef12-3456-7890-abcd-ef1234567890', SRR['success']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async_with_rules']),
    ])
    module_args = {
        'use_rest': 'always',
        'snapmirror_label': ['daily', 'weekly', 'monthly'],
        'keep': [7, 5, 12],
        'schedule': ['', 'weekly', 'monthly'],
        'prefix': ['', 'weekly', 'monthly']
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_delete():
    ''' deleting snapmirror policy and testing idempotency '''
    register_responses([
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['snapmirror-policy-info']),
        ('ZAPI', 'snapmirror-policy-delete', ZRR['success']),
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'use_rest': 'never',
        'state': 'absent'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_delete_with_rest():
    ''' deleting snapmirror policy via REST and testing idempotency '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async_with_rules_dash']),
        ('DELETE', 'snapmirror/policies/abcdef12-3456-7890-abcd-ef1234567890', SRR['success']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async_with_rules']),
        ('DELETE', 'snapmirror/policies/abcdef12-3456-7890-abcd-ef1234567890', SRR['success']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['zero_records']),
    ])
    module_args = {
        'state': 'absent',
        'use_rest': 'always',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify():
    ''' modifying snapmirror policy without rules.  idempotency was tested in create '''
    register_responses([
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['snapmirror-policy-info']),
        ('ZAPI', 'snapmirror-policy-modify', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'comment': 'old comment',
        'ignore_atime': True,
        'is_network_compression_enabled': True,
        'owner': 'cluster_admin',
        'restart': 'default',
        'tries': '7'}

    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify_with_rest():
    ''' modifying snapmirror policy without rules via REST.  Idempotency was tested in create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async']),
        ('PATCH', 'snapmirror/policies/abcdef12-3456-7890-abcd-ef1234567890', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        'comment': 'old comment',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify_with_rules():
    ''' modifying snapmirror policy with rules.  Idempotency was tested in create '''
    register_responses([
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['snapmirror-policy-info']),
        ('ZAPI', 'snapmirror-policy-add-rule', ZRR['success']),
        ('ZAPI', 'snapmirror-policy-add-rule', ZRR['success']),
        ('ZAPI', 'snapmirror-policy-add-rule', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'snapmirror_label': ['daily', 'weekly', 'monthly'],
        'keep': [7, 5, 12],
        'schedule': ['', 'weekly', 'monthly'],
        'prefix': ['', 'weekly', 'monthly']
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify_with_rules_via_rest():
    ''' modifying snapmirror policy with rules via rest.  Idempotency was tested in create '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async']),
        ('PATCH', 'snapmirror/policies/abcdef12-3456-7890-abcd-ef1234567890', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        'snapmirror_label': ['daily', 'weekly', 'monthly'],
        'keep': [7, 5, 12],
        'schedule': ['', 'weekly', 'monthly'],
        'prefix': ['', 'weekly', 'monthly']
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('ZAPI', 'snapmirror-policy-get-iter', ZRR['error']),
        ('ZAPI', 'snapmirror-policy-create', ZRR['error']),
        ('ZAPI', 'snapmirror-policy-delete', ZRR['error']),
        ('ZAPI', 'snapmirror-policy-modify', ZRR['error']),
        ('ZAPI', 'snapmirror-policy-remove-rule', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
        'common_snapshot_schedule': 'sched',
        'policy_type': 'sync_mirror',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = zapi_error_message('Error getting snapmirror policy ansible')
    assert error in expect_and_capture_ansible_exception(my_obj.get_snapmirror_policy, 'fail')['msg']
    error = zapi_error_message('Error creating snapmirror policy ansible')
    assert error in expect_and_capture_ansible_exception(my_obj.create_snapmirror_policy, 'fail')['msg']
    error = zapi_error_message('Error deleting snapmirror policy ansible')
    assert error in expect_and_capture_ansible_exception(my_obj.delete_snapmirror_policy, 'fail')['msg']
    error = zapi_error_message('Error modifying snapmirror policy ansible')
    assert error in expect_and_capture_ansible_exception(my_obj.modify_snapmirror_policy, 'fail')['msg']
    module_args = {
        'use_rest': 'never',
        'common_snapshot_schedule': 'sched',
        'policy_type': 'sync_mirror',
        'snapmirror_label': ['lbl1'],
        'keep': [24],
    }
    current = {
        'snapmirror_label': ['lbl2'],
        'keep': [24],
        'prefix': [''],
        'schedule': ['weekly'],
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = zapi_error_message('Error modifying snapmirror policy rule ansible')
    assert error in expect_and_capture_ansible_exception(my_obj.modify_snapmirror_policy_rules, 'fail', current)['msg']


def test_if_all_methods_catch_exception_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['generic_error']),
        ('POST', 'snapmirror/policies', SRR['generic_error']),
        ('DELETE', 'snapmirror/policies/uuid', SRR['generic_error']),
        ('PATCH', 'snapmirror/policies/uuid', SRR['generic_error']),
        # modifying rules
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('PATCH', 'snapmirror/policies/uuid', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
        'policy_type': 'sync_mirror',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = rest_error_message('Error getting snapmirror policy', 'snapmirror/policies')
    assert error in expect_and_capture_ansible_exception(my_obj.get_snapmirror_policy_rest, 'fail')['msg']
    error = rest_error_message('Error creating snapmirror policy', 'snapmirror/policies')
    assert error in expect_and_capture_ansible_exception(my_obj.create_snapmirror_policy, 'fail')['msg']
    error = rest_error_message('Error deleting snapmirror policy', 'snapmirror/policies/uuid')
    assert error in expect_and_capture_ansible_exception(my_obj.delete_snapmirror_policy, 'fail', 'uuid')['msg']
    error = rest_error_message('Error modifying snapmirror policy', 'snapmirror/policies/uuid')
    assert error in expect_and_capture_ansible_exception(my_obj.modify_snapmirror_policy, 'fail', 'uuid', {'key': 'value'})['msg']
    module_args = {
        'use_rest': 'always',
        'policy_type': 'sync_mirror',
        'snapmirror_label': ['lbl1'],
        'keep': [24],
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = rest_error_message('Error modifying snapmirror policy rules', 'snapmirror/policies/uuid')
    assert error in expect_and_capture_ansible_exception(my_obj.modify_snapmirror_policy_rules, 'fail', None, 'uuid')['msg']


def test_create_snapmirror_policy_retention_obj_for_rest():
    ''' test create_snapmirror_policy_retention_obj_for_rest '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    # Test no rules
    assert my_obj.create_snapmirror_policy_retention_obj_for_rest() == []

    # Test one rule
    rules = [{'snapmirror_label': 'daily', 'keep': 7}]
    retention_obj = [{'label': 'daily', 'count': '7'}]
    assert my_obj.create_snapmirror_policy_retention_obj_for_rest(rules) == retention_obj

    # Test two rules, with a prefix
    rules = [{'snapmirror_label': 'daily', 'keep': 7},
             {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly'}]
    retention_obj = [{'label': 'daily', 'count': '7'},
                     {'label': 'weekly', 'count': '5', 'prefix': 'weekly'}]
    assert my_obj.create_snapmirror_policy_retention_obj_for_rest(rules) == retention_obj

    # Test three rules, with a prefix & schedule
    rules = [{'snapmirror_label': 'daily', 'keep': 7},
             {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly_sv'},
             {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly_sv', 'schedule': 'monthly'}]
    retention_obj = [{'label': 'daily', 'count': '7'},
                     {'label': 'weekly', 'count': '5', 'prefix': 'weekly_sv'},
                     {'label': 'monthly', 'count': '12', 'prefix': 'monthly_sv', 'creation_schedule': {'name': 'monthly'}}]
    assert my_obj.create_snapmirror_policy_retention_obj_for_rest(rules) == retention_obj


def test_identify_snapmirror_policy_rules_with_schedule():
    ''' test identify_snapmirror_policy_rules_with_schedule '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    # Test no rules
    assert my_obj.identify_snapmirror_policy_rules_with_schedule() == ([], [])

    # Test one non-schedule rule identified
    rules = [{'snapmirror_label': 'daily', 'keep': 7}]
    schedule_rules = []
    non_schedule_rules = [{'snapmirror_label': 'daily', 'keep': 7}]
    assert my_obj.identify_snapmirror_policy_rules_with_schedule(rules) == (schedule_rules, non_schedule_rules)

    # Test one schedule and two non-schedule rules identified
    rules = [{'snapmirror_label': 'daily', 'keep': 7},
             {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly_sv'},
             {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly_sv', 'schedule': 'monthly'}]
    schedule_rules = [{'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly_sv', 'schedule': 'monthly'}]
    non_schedule_rules = [{'snapmirror_label': 'daily', 'keep': 7},
                          {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly_sv'}]
    assert my_obj.identify_snapmirror_policy_rules_with_schedule(rules) == (schedule_rules, non_schedule_rules)

    # Test three schedule & zero non-schedule rules identified
    rules = [{'snapmirror_label': 'daily', 'keep': 7, 'schedule': 'daily'},
             {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly_sv', 'schedule': 'weekly'},
             {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly_sv', 'schedule': 'monthly'}]
    schedule_rules = [{'snapmirror_label': 'daily', 'keep': 7, 'schedule': 'daily'},
                      {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly_sv', 'schedule': 'weekly'},
                      {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly_sv', 'schedule': 'monthly'}]
    non_schedule_rules = []
    assert my_obj.identify_snapmirror_policy_rules_with_schedule(rules) == (schedule_rules, non_schedule_rules)


def test_identify_new_snapmirror_policy_rules():
    ''' test identify_new_snapmirror_policy_rules '''
    register_responses([
    ])

    # Test with no rules in parameters. new_rules should always be [].
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    current = None
    new_rules = []
    assert my_obj.identify_new_snapmirror_policy_rules(current) == new_rules

    current = {'snapmirror_label': ['daily'], 'keep': [7], 'prefix': [''], 'schedule': ['']}
    new_rules = []
    assert my_obj.identify_new_snapmirror_policy_rules(current) == new_rules

    # Test with rules in parameters.
    module_args = {
        'use_rest': 'never',
        'snapmirror_label': ['daily', 'weekly', 'monthly'],
        'keep': [7, 5, 12],
        'schedule': ['', 'weekly', 'monthly'],
        'prefix': ['', 'weekly', 'monthly']
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    # Test three new rules identified when no rules currently exist
    current = None
    new_rules = [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''},
                 {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'},
                 {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'}]
    assert my_obj.identify_new_snapmirror_policy_rules(current) == new_rules

    # Test two new rules identified and one rule already exists
    current = {'snapmirror_label': ['daily'], 'keep': [7], 'prefix': [''], 'schedule': ['']}
    new_rules = [{'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'},
                 {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'}]
    assert my_obj.identify_new_snapmirror_policy_rules(current) == new_rules

    # Test one new rule identified and two rules already exist
    current = {'snapmirror_label': ['daily', 'monthly'],
               'keep': [7, 12],
               'prefix': ['', 'monthly'],
               'schedule': ['', 'monthly']}
    new_rules = [{'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'}]
    assert my_obj.identify_new_snapmirror_policy_rules(current) == new_rules

    # Test no new rules identified as all rules already exist
    current = {'snapmirror_label': ['daily', 'monthly', 'weekly'],
               'keep': [7, 12, 5],
               'prefix': ['', 'monthly', 'weekly'],
               'schedule': ['', 'monthly', 'weekly']}
    new_rules = []
    assert my_obj.identify_new_snapmirror_policy_rules(current) == new_rules


def test_identify_obsolete_snapmirror_policy_rules():
    ''' test identify_obsolete_snapmirror_policy_rules '''
    register_responses([
    ])

    # Test with no rules in parameters. obsolete_rules should always be [].
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    current = None
    obsolete_rules = []
    assert my_obj.identify_obsolete_snapmirror_policy_rules(current) == obsolete_rules

    current = {'snapmirror_label': ['daily'], 'keep': [7], 'prefix': [''], 'schedule': ['']}
    obsolete_rules = []
    assert my_obj.identify_obsolete_snapmirror_policy_rules(current) == obsolete_rules

    # Test removing all rules. obsolete_rules should equal current.
    module_args = {
        'use_rest': 'never',
        'snapmirror_label': []
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    current = {'snapmirror_label': ['monthly', 'weekly', 'hourly', 'daily', 'yearly'],
               'keep': [12, 5, 24, 7, 7],
               'prefix': ['monthly', 'weekly', '', '', 'yearly'],
               'schedule': ['monthly', 'weekly', '', '', 'yearly']}
    obsolete_rules = [{'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'},
                      {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'},
                      {'snapmirror_label': 'hourly', 'keep': 24, 'prefix': '', 'schedule': ''},
                      {'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''},
                      {'snapmirror_label': 'yearly', 'keep': 7, 'prefix': 'yearly', 'schedule': 'yearly'}]
    assert my_obj.identify_obsolete_snapmirror_policy_rules(current) == obsolete_rules

    # Test with rules in parameters.
    module_args = {
        'use_rest': 'never',
        'snapmirror_label': ['daily', 'weekly', 'monthly'],
        'keep': [7, 5, 12],
        'schedule': ['', 'weekly', 'monthly'],
        'prefix': ['', 'weekly', 'monthly']
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    # Test no rules exist, thus no obsolete rules
    current = None
    obsolete_rules = []
    assert my_obj.identify_obsolete_snapmirror_policy_rules(current) == obsolete_rules

    # Test new rules and one obsolete rule identified
    current = {'snapmirror_label': ['hourly'], 'keep': [24], 'prefix': [''], 'schedule': ['']}
    obsolete_rules = [{'snapmirror_label': 'hourly', 'keep': 24, 'prefix': '', 'schedule': ''}]
    assert my_obj.identify_obsolete_snapmirror_policy_rules(current) == obsolete_rules

    # Test new rules, with one retained and one obsolete rule identified
    current = {'snapmirror_label': ['hourly', 'daily'],
               'keep': [24, 7],
               'prefix': ['', ''],
               'schedule': ['', '']}
    obsolete_rules = [{'snapmirror_label': 'hourly', 'keep': 24, 'prefix': '', 'schedule': ''}]
    assert my_obj.identify_obsolete_snapmirror_policy_rules(current) == obsolete_rules

    # Test new rules and two obsolete rules identified
    current = {'snapmirror_label': ['monthly', 'weekly', 'hourly', 'daily', 'yearly'],
               'keep': [12, 5, 24, 7, 7],
               'prefix': ['monthly', 'weekly', '', '', 'yearly'],
               'schedule': ['monthly', 'weekly', '', '', 'yearly']}
    obsolete_rules = [{'snapmirror_label': 'hourly', 'keep': 24, 'prefix': '', 'schedule': ''},
                      {'snapmirror_label': 'yearly', 'keep': 7, 'prefix': 'yearly', 'schedule': 'yearly'}]
    assert my_obj.identify_obsolete_snapmirror_policy_rules(current) == obsolete_rules


def test_identify_modified_snapmirror_policy_rules():
    ''' test identify_modified_snapmirror_policy_rules '''
    register_responses([

    ])

    # Test with no rules in parameters. modified_rules & unmodified_rules should always be [].
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    current = None
    modified_rules, unmodified_rules = [], []
    assert my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules == unmodified_rules)

    current = {'snapmirror_label': ['daily'], 'keep': [14], 'prefix': ['daily'], 'schedule': ['daily']}
    modified_rules, unmodified_rules = [], []
    assert my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules == unmodified_rules)

    # Test removing all rules. modified_rules & unmodified_rules should be [].
    module_args = {
        'use_rest': 'never',
        'snapmirror_label': []
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    current = {'snapmirror_label': ['monthly', 'weekly', 'hourly', 'daily', 'yearly'],
               'keep': [12, 5, 24, 7, 7],
               'prefix': ['monthly', 'weekly', '', '', 'yearly'],
               'schedule': ['monthly', 'weekly', '', '', 'yearly']}
    modified_rules, unmodified_rules = [], []
    assert my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules == unmodified_rules)

    # Test with rules in parameters.
    module_args = {
        'use_rest': 'never',
        'snapmirror_label': ['daily', 'weekly', 'monthly'],
        'keep': [7, 5, 12],
        'schedule': ['', 'weekly', 'monthly'],
        'prefix': ['', 'weekly', 'monthly']
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)

    # Test no rules exist, thus no modified & unmodified rules
    current = None
    modified_rules, unmodified_rules = [], []
    assert my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules == unmodified_rules)

    # Test new rules don't exist, thus no modified & unmodified rules
    current = {'snapmirror_label': ['hourly'], 'keep': [24], 'prefix': [''], 'schedule': ['']}
    modified_rules, unmodified_rules = [], []
    assert my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules == unmodified_rules)

    # Test daily & monthly modified, weekly unmodified
    current = {'snapmirror_label': ['hourly', 'daily', 'weekly', 'monthly'],
               'keep': [24, 14, 5, 6],
               'prefix': ['', 'daily', 'weekly', 'monthly'],
               'schedule': ['', 'daily', 'weekly', 'monthly']}
    modified_rules = [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''},
                      {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'}]
    unmodified_rules = [{'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'}]
    assert my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules == unmodified_rules)

    # Test all rules modified
    current = {'snapmirror_label': ['daily', 'weekly', 'monthly'],
               'keep': [14, 10, 6],
               'prefix': ['', '', ''],
               'schedule': ['daily', 'weekly', 'monthly']}
    modified_rules = [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''},
                      {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'},
                      {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'}]
    unmodified_rules = []
    assert my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules == unmodified_rules)

    # Test all rules unmodified
    current = {'snapmirror_label': ['daily', 'weekly', 'monthly'],
               'keep': [7, 5, 12],
               'prefix': ['', 'weekly', 'monthly'],
               'schedule': ['', 'weekly', 'monthly']}
    modified_rules = []
    unmodified_rules = [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''},
                        {'snapmirror_label': 'weekly', 'keep': 5, 'prefix': 'weekly', 'schedule': 'weekly'},
                        {'snapmirror_label': 'monthly', 'keep': 12, 'prefix': 'monthly', 'schedule': 'monthly'}]
    assert my_obj.identify_modified_snapmirror_policy_rules(current), (modified_rules == unmodified_rules)


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.HAS_NETAPP_LIB', False)
def test_module_fail_when_netapp_lib_missing():
    ''' required lib missing '''
    module_args = {
        'use_rest': 'never',
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_validate_parameters():
    ''' test test_validate_parameters '''
    register_responses([
    ])

    args = dict(DEFAULT_ARGS)
    args.pop('vserver')
    module_args = {
        'use_rest': 'never',
    }
    error = 'Error: vserver is a required parameter when using ZAPI.'
    assert error in create_module(my_module, args, module_args, fail=True)['msg']

    module_args = {
        'use_rest': 'never',
        'snapmirror_label': list(range(11)),
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = 'Error: A SnapMirror Policy can have up to a maximum of'
    assert error in expect_and_capture_ansible_exception(my_obj.validate_parameters, 'fail')['msg']

    module_args = {
        'use_rest': 'never',
        'snapmirror_label': list(range(10)),
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = "Error: Missing 'keep' parameter. When specifying the 'snapmirror_label' parameter, the 'keep' parameter must also be supplied"
    assert error in expect_and_capture_ansible_exception(my_obj.validate_parameters, 'fail')['msg']

    module_args = {
        'use_rest': 'never',
        'snapmirror_label': list(range(10)),
        'keep': list(range(9)),
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = "Error: Each 'snapmirror_label' value must have an accompanying 'keep' value"
    assert error in expect_and_capture_ansible_exception(my_obj.validate_parameters, 'fail')['msg']

    module_args = {
        'use_rest': 'never',
        'snapmirror_label': list(range(10)),
        'keep': list(range(11)),
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = "Error: Each 'keep' value must have an accompanying 'snapmirror_label' value"
    assert error in expect_and_capture_ansible_exception(my_obj.validate_parameters, 'fail')['msg']

    module_args = {
        'use_rest': 'never',
        'keep': list(range(11)),
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = "Error: Missing 'snapmirror_label' parameter. When specifying the 'keep' parameter, the 'snapmirror_label' parameter must also be supplied"
    assert error in expect_and_capture_ansible_exception(my_obj.validate_parameters, 'fail')['msg']

    module_args = {
        'use_rest': 'never',
        'snapmirror_label': list(range(10)),
        'keep': list(range(10)),
        'prefix': list(range(10)),
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = "Error: Missing 'schedule' parameter. When specifying the 'prefix' parameter, the 'schedule' parameter must also be supplied"
    assert error in expect_and_capture_ansible_exception(my_obj.validate_parameters, 'fail')['msg']

    module_args = {
        'use_rest': 'never',
        'identity_preservation': 'full',
    }
    error = 'Error: identity_preservation option is not supported with ZAPI.  It can only be used with REST.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']

    module_args = {
        'use_rest': 'never',
        'copy_all_source_snapshots': True,
    }
    error = 'Error: copy_all_source_snapshots option is not supported with ZAPI.  It can only be used with REST.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_validate_parameters_rest():
    ''' test test_validate_parameters '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['zero_records']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['zero_records']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['zero_records']),
        ('POST', 'snapmirror/policies', SRR['success']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async']),
        # copy_all_source_snapshots
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        # copy_latest_source_snapshot
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
        # create_snapshot_on_source
        ('GET', 'cluster', SRR['is_rest_9_11_1']),
    ])

    module_args = {
        'use_rest': 'always',
        'policy_type': 'sync_mirror',
        'is_network_compression_enabled': True
    }
    error = 'Error: input parameter network_compression_enabled is not valid for SnapMirror policy type sync'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']

    module_args = {
        'use_rest': 'always',
        'policy_type': 'sync_mirror',
        'identity_preservation': 'full'
    }
    error = 'Error: identity_preservation is only supported with async (async) policy_type, got: sync'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']

    module_args = {
        'use_rest': 'always',
        'policy_type': 'async_mirror',
        'is_network_compression_enabled': True,
        'identity_preservation': 'full'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']

    module_args = {
        'use_rest': 'always',
        'policy_type': 'async_mirror',
        'copy_all_source_snapshots': False,
    }
    error = 'Error: the property copy_all_source_snapshots can only be set to true when present'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']

    module_args = {
        'use_rest': 'always',
        'policy_type': 'async_mirror',
        'copy_latest_source_snapshot': False,
    }
    error = 'Error: the property copy_latest_source_snapshot can only be set to true when present'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']

    module_args = {
        'use_rest': 'always',
        'policy_type': 'vault',
        'create_snapshot_on_source': True,
    }
    error = 'Error: the property create_snapshot_on_source can only be set to false when present'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_errors_in_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['zero_records']),
        ('POST', 'snapmirror/policies', SRR['success']),
        ('GET', 'snapmirror/policies', SRR['zero_records']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_sync']),
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    error = 'Error: policy ansible not present after create.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']

    # change in policy type
    module_args = {
        'use_rest': 'always',
        'policy_type': 'async_mirror',
    }
    error = 'Error: The policy property policy_type cannot be modified from sync to async'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args = {
        'use_rest': 'always',
        'policy_type': 'sync_mirror',
    }
    error = 'Error: The policy property policy_type cannot be modified from async to sync'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_errors_in_create_with_copy_snapshots():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    module_args = {
        'use_rest': 'always',
        'copy_all_source_snapshots': True,
        'policy_type': 'sync_mirror'
    }
    msg = 'Error: option copy_all_source_snapshots is not supported with policy type sync_mirror.'
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert msg in error


def test_errors_in_create_with_copy_latest_snapshots():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
    ])
    module_args = {
        'use_rest': 'always',
        'copy_latest_source_snapshot': True,
        'policy_type': 'async',
        'snapmirror_label': ["daily", "weekly"],
    }
    msg = 'Error: Retention properties cannot be specified along with copy_all_source_snapshots or copy_latest_source_snapshot properties'
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert msg in error


def test_errors_in_create_snapshot_on_source():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
    ])
    module_args = {
        'use_rest': 'always',
        'create_snapshot_on_source': False,
        'policy_type': 'sync_mirror',
        'snapmirror_label': ["daily", "weekly"],
        'keep': ["7", "2"],
    }
    msg = 'Error: option create_snapshot_on_source is not supported with policy type sync_mirror.'
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert msg in error

    module_args = {
        'use_rest': 'always',
        'create_snapshot_on_source': False,
        'policy_type': 'async',
        'snapmirror_label': ["daily", "weekly"],
    }
    msg = 'Error: The properties snapmirror_label and keep must be specified with'
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert msg in error


def test_async_create_snapshot_on_source():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_12_1']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['empty_records']),
        ('POST', 'snapmirror/policies', SRR['success']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_async_with_create_snapshot_on_source']),
    ])
    module_args = {
        'use_rest': 'always',
        'create_snapshot_on_source': False,
        'policy_type': 'vault',
        'snapmirror_label': ["daily", "weekly"],
        'keep': ["7", "2"],
        'prefix': ["p1", "p2"],
        'schedule': ["daily", "weekly"],
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_get_snapmirror_policy_sync_with_sync_type():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'snapmirror/policies', SRR['empty_records']),
        ('POST', 'snapmirror/policies', SRR['success']),
        ('GET', 'snapmirror/policies', SRR['get_snapmirror_policy_sync_with_sync_type']),
    ])
    module_args = {
        'use_rest': 'always',
        'policy_type': 'sync_mirror',
        'sync_type': 'automated_failover'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_set_scope():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['zero_records']),
        # first test
        ('GET', 'svm/svms', SRR['zero_records']),
        ('GET', 'svm/svms', SRR['one_vserver_record']),
        ('GET', 'svm/svms', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    # vserver not found
    assert my_obj.set_scope() == 'cluster'
    # vserver found
    assert my_obj.set_scope() == 'svm'
    # API error
    error = rest_error_message('Error getting vserver ansible info', 'svm/svms')
    assert error in expect_and_capture_ansible_exception(my_obj.set_scope, 'fail')['msg']
    # no vserver
    my_obj.parameters.pop('vserver')
    assert my_obj.set_scope() == 'cluster'


def check_mapping(my_obj, policy_type, expected_policy_type, copy_latest_source_snapshot, copy_all_source_snapshots, create_snapshot_on_source, retention):
    my_obj.parameters['policy_type'] = policy_type
    if copy_latest_source_snapshot is None:
        my_obj.parameters.pop('copy_latest_source_snapshot', None)
    else:
        my_obj.parameters['copy_latest_source_snapshot'] = copy_latest_source_snapshot
    if copy_all_source_snapshots is None:
        my_obj.parameters.pop('copy_all_source_snapshots', None)
    else:
        my_obj.parameters['copy_all_source_snapshots'] = copy_all_source_snapshots
    if create_snapshot_on_source is None:
        my_obj.parameters.pop('create_snapshot_on_source', None)
    else:
        my_obj.parameters['create_snapshot_on_source'] = create_snapshot_on_source
    if retention is None:
        my_obj.parameters.pop('snapmirror_label', None)
        my_obj.parameters.pop('keep', None)
        my_obj.parameters.pop('prefix', None)
        my_obj.parameters.pop('schedule', None)
    else:
        for key, value in retention.items():
            my_obj.parameters[key] = value
    my_obj.validate_policy_type()
    assert my_obj.parameters['policy_type'] == expected_policy_type


def check_options(my_obj, copy_latest_source_snapshot, copy_all_source_snapshots, create_snapshot_on_source):
    if copy_latest_source_snapshot is None:
        assert 'copy_latest_source_snapshot' not in my_obj.parameters
    else:
        assert my_obj.parameters['copy_latest_source_snapshot'] == copy_latest_source_snapshot
    if copy_all_source_snapshots is None:
        assert 'copy_all_source_snapshots' not in my_obj.parameters
    else:
        assert my_obj.parameters['copy_all_source_snapshots'] == copy_all_source_snapshots
    if create_snapshot_on_source is None:
        assert 'create_snapshot_on_source' not in my_obj.parameters
    else:
        assert my_obj.parameters['create_snapshot_on_source'] == create_snapshot_on_source


def test_validate_policy_type():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'svm/svms', SRR['zero_records']),
        # first test
    ])
    module_args = {
        'use_rest': 'always',
    }
    retention = {
        'snapmirror_label': ["daily", "weekly"],
        'keep': ["7", "2"]
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    check_mapping(my_obj, 'async', 'async', None, None, None, None)
    check_options(my_obj, None, None, None)
    check_mapping(my_obj, 'mirror_vault', 'async', None, None, None, None)
    check_options(my_obj, None, None, None)
    check_mapping(my_obj, 'vault', 'async', None, None, None, retention)
    check_options(my_obj, None, None, False)
    check_mapping(my_obj, 'async_mirror', 'async', None, None, None, None)
    check_options(my_obj, True, None, None)
    check_mapping(my_obj, 'sync', 'sync', None, None, None, None)
    check_options(my_obj, None, None, None)
    check_mapping(my_obj, 'sync_mirror', 'sync', None, None, None, None)
    check_options(my_obj, None, None, None)
    check_mapping(my_obj, 'strict_sync_mirror', 'sync', None, None, None, None)
    check_options(my_obj, None, None, None)

    my_obj.parameters['policy_type'] = 'async'
    my_obj.parameters['sync_type'] = 'strict_sync'
    error = "Error: 'sync_type' is only applicable for sync policy_type"
    assert error in expect_and_capture_ansible_exception(my_obj.validate_policy_type, 'fail')['msg']

    module_args = {
        'use_rest': 'never',
        'policy_type': 'sync'
    }
    error = 'Error: The policy types async and sync are not supported in ZAPI.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_build_body_for_create():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['zero_records']),
        # first test
    ])
    module_args = {
        'use_rest': 'always',
        'snapmirror_label': ["daily", "weekly"],
        'keep': ["7", "2"],
        'copy_all_source_snapshots': True
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    body = my_obj.build_body_for_create()
    assert 'copy_all_source_snapshots' in body


def test_modify_snapmirror_policy_rules_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'svm/svms', SRR['zero_records']),
        # first test
    ])
    module_args = {
        'use_rest': 'always',
        'snapmirror_label': ["daily", "weekly"],
        'keep': ["7", "2"],
        'copy_all_source_snapshots': True
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.modify_snapmirror_policy_rules_rest('uuid', [], ['umod'], [], []) is None
