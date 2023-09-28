# (c) 2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_ems_filter module '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception, call_main
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ems_filter \
    import NetAppOntapEMSFilters as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    'default_ems_filter': (200, {
        "name": "snmp-traphost",
        "rules": [{
            "index": "1",
            "type": "exclude",
            "message_criteria": {
                "severities": "*",
                "name_pattern": "*",
                "snmp_trap_types": "*",
            }
        }]
    }, None),
    'ems_filter': (200, {
        "name": "snmp-traphost",
        "rules": [{
            "index": "1",
            "type": "include",
            "message_criteria": {
                "severities": "error,informational",
                "name_pattern": "callhome.*",
            }
        }, {
            "index": "2",
            "type": "exclude",
            "message_criteria": {
                "severities": "*",
                "name_pattern": "*",
                "snmp_trap_types": "*",
            }
        }]
    }, None),
    'post_empty_good': (201, {}, None),
    'ems_filter_2_rules': (200, {
        "name": "snmp-traphost",
        "rules": [{
            "index": "1",
            "type": "include",
            "message_criteria": {
                "severities": "error,informational",
                "name_pattern": "callhome.*",
            }
        }, {
            "index": "2",
            "type": "include",
            "message_criteria": {
                "severities": "alert",
                "name_pattern": "callhome.*",
            }
        }, {
            "index": "3",
            "type": "exclude",
            "message_criteria": {
                "severities": "*",
                "name_pattern": "*",
                "snmp_trap_types": "*",
            }
        }]
    }, None),
    'ems_filter_3_rules': (200, {
        "name": "snmp-traphost",
        "rules": [{
            "index": "1",
            "type": "include",
            "message_criteria": {
                "severities": "error",
                "name_pattern": "*",
            }
        }, {
            "index": "2",
            "type": "include",
            "message_criteria": {
                "severities": "alert",
                "name_pattern": "callhome.*",
            }
        }, {
            "index": "3",
            "type": "include",
            "message_criteria": {
                "severities": "emergency",
                "name_pattern": "callhome.*",
            }
        }, {
            "index": "4",
            "type": "exclude",
            "message_criteria": {
                "severities": "*",
                "name_pattern": "*",
                "snmp_trap_types": "*",
            }
        }]
    }, None),
    'ems_filter_no_rules': (200, {
        "name": "snmp-traphost",
    }, None)
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': "snmp-traphost"
}

DEFAULT_RULE = [{
    "index": "1",
    "type": "include",
    "message_criteria": {
        "severities": "error,informational",
        "name_pattern": "callhome.*",
    }
}]


DEFAULT_RULE_2_RULES = [{
    "index": "1",
    "type": "exclude",
    "message_criteria": {
        "severities": "error,informational",
        "name_pattern": "callhome.*",
    }
}, {
    "index": "2",
    "type": "exclude",
    "message_criteria": {
        "severities": "*",
        "name_pattern": "*",
    }
}]

DEFAULT_RULE_MODIFY_TYPE_2_RULES = [{
    "index": "1",
    "type": "include",
    "message_criteria": {
        "severities": "error,informational",
        "name_pattern": "callhome.*",
    }
}, {
    "index": "2",
    "type": "exclude",
    "message_criteria": {
        "severities": "alert",
        "name_pattern": "callhome.*",
    }
}]

DEFAULT_RULE_MODIFY_SEVERITIES_2_RULES = [{
    "index": "1",
    "type": "include",
    "message_criteria": {
        "severities": "notice",
        "name_pattern": "callhome.*",
    }
}, {
    "index": "2",
    "type": "include",
    "message_criteria": {
        "severities": "alert",
        "name_pattern": "callhome.*",
    }
}]

DEFAULT_RULE_MODIFY_NAME_PATTERN_2_RULES = [{
    "index": "1",
    "type": "include",
    "message_criteria": {
        "severities": "error,informational",
        "name_pattern": "*",
    }
}, {
    "index": "2",
    "type": "include",
    "message_criteria": {
        "severities": "alert",
        "name_pattern": "*",
    }
}]

DEFAULT_RULE_MODIFY_SEVERITIES_3_RULES = [{
    "index": "1",
    "type": "include",
    "message_criteria": {
        "severities": "error, informational",
        "name_pattern": "*",
    }
}, {
    "index": "2",
    "type": "include",
    "message_criteria": {
        "severities": "alert",
        "name_pattern": "callhome.*",
    }
}, {
    "index": "3",
    "type": "include",
    "message_criteria": {
        "severities": "emergency",
        "name_pattern": "callhome.*",
    }
}]

DEFAULT_RULE_STARS = [{
    "index": "1",
    "type": "include",
    "message_criteria": {
        "severities": "*",
        "name_pattern": "*",
    }
}]


def test_get_ems_filter_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_ems_filter() is None


def test_get_ems_filter_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching ems filter snmp-traphost: calling: support/ems/filters: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_ems_filter, 'fail')['msg']


def test_get_ems_filter_get():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['ems_filter'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_ems_filter() is not None


def test_create_ems_filter():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['empty_records']),
        ('POST', 'support/ems/filters', SRR['empty_good'])
    ])
    module_args = {'rules': DEFAULT_RULE}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_ems_filter_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('POST', 'support/ems/filters', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['rules'] = DEFAULT_RULE
    error = expect_and_capture_ansible_exception(my_obj.create_ems_filter, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error creating EMS filter snmp-traphost: calling: support/ems/filters: got Expected error.' == error


def test_delete_ems_filter():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['ems_filter']),
        ('DELETE', 'support/ems/filters/snmp-traphost', SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_ems_filter_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('DELETE', 'support/ems/filters/snmp-traphost', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['rules'] = DEFAULT_RULE
    error = expect_and_capture_ansible_exception(my_obj.delete_ems_filter, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error deleting EMS filter snmp-traphost: calling: support/ems/filters/snmp-traphost: got Expected error.' == error


def test_modify_ems_filter_add_rule():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['default_ems_filter']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good']),
    ])
    module_args = {'rules': DEFAULT_RULE}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ems_filter_change_type():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['ems_filter']),
        ('PATCH', 'support/ems/filters/snmp-traphost', SRR['empty_good']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good'])
    ])
    module_args = {'rules': DEFAULT_RULE_2_RULES}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ems_filter_change_severities():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['ems_filter_2_rules']),
        ('PATCH', 'support/ems/filters/snmp-traphost', SRR['empty_good']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good'])
    ])
    module_args = {'rules': DEFAULT_RULE_MODIFY_SEVERITIES_2_RULES}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ems_filter_change_name_pattern():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['ems_filter_2_rules']),
        ('PATCH', 'support/ems/filters/snmp-traphost', SRR['empty_good']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good'])
    ])
    module_args = {'rules': DEFAULT_RULE_MODIFY_NAME_PATTERN_2_RULES}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ems_filter_add_rule_and_change_severities():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['ems_filter_2_rules']),
        ('PATCH', 'support/ems/filters/snmp-traphost', SRR['empty_good']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good'])
    ])
    module_args = {'rules': DEFAULT_RULE_MODIFY_SEVERITIES_3_RULES}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_ems_filter_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('PATCH', 'support/ems/filters/snmp-traphost', SRR['generic_error']),
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    patch_rules = [{'index': 1, 'type': 'include', 'message_criteria': {'severities': 'error', 'name_pattern': '*'}}]
    post_rules = [{'index': 2, 'type': 'include', 'message_criteria': {'severities': 'notice', 'name_pattern': '*'}}]
    desired_rules = {'patch_rules': patch_rules, 'post_rules': post_rules}
    error = expect_and_capture_ansible_exception(my_obj.modify_ems_filter, 'fail', desired_rules)['msg']
    print('Info: %s' % error)
    assert 'Error modifying EMS filter snmp-traphost: calling: support/ems/filters/snmp-traphost: got Expected error.' == error


def test_modify_ems_filter_no_rules():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['default_ems_filter']),
    ])
    assert not create_and_apply(my_module, DEFAULT_ARGS, {})['changed']


def test_modify_star_test():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'support/ems/filters', SRR['ems_filter']),
        ('PATCH', 'support/ems/filters/snmp-traphost', SRR['empty_good']),
        ('POST', 'support/ems/filters/snmp-traphost/rules', SRR['post_empty_good'])
    ])
    module_args = {'rules': DEFAULT_RULE_STARS}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
