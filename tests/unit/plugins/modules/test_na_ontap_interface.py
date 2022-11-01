# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_warning_was_raised, print_warnings, call_main, create_module, expect_and_capture_ansible_exception, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_error, build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_interface \
    import NetAppOntapInterface as interface_module, main as my_main


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def interface_info(dns=True):
    info = {
        'attributes-list': {
            'net-interface-info': {
                'interface-name': 'abc_if',
                'administrative-status': 'up',
                'failover-group': 'failover_group',
                'failover-policy': 'up',
                'firewall-policy': 'up',
                'is-auto-revert': 'true',
                'home-node': 'node',
                'current-node': 'node',
                'home-port': 'e0c',
                'current-port': 'e0c',
                'address': '2.2.2.2',
                'netmask': '1.1.1.1',
                'role': 'data',
                'listen-for-dns-query': 'true',
                'is-dns-update-enabled': 'true',
                'is-ipv4-link-local': 'false',
                'service-policy': 'service_policy',
            }
        }
    }
    if dns:
        info['attributes-list']['net-interface-info']['dns-domain-name'] = 'test.com'
    return info


node_info = {
    'attributes-list': {
        'cluster-node-info': {
            'node-name': 'node_1',
        }
    }
}


ZRR = zapi_responses({
    'interface_info': build_zapi_response(interface_info(), 1),
    'interface_info_no_dns': build_zapi_response(interface_info(dns=False), 1),
    'node_info': build_zapi_response(node_info, 1),
    'error_17': build_zapi_error(17, 'A LIF with the same name already exists'),
    'error_13003': build_zapi_error(13003, 'ZAPI is not enabled in pre-cluster mode.'),
})


DEFAULT_ARGS = {
    'hostname': '10.10.10.10',
    'username': 'admin',
    'password': 'password',
    'home_port': 'e0c',
    'interface_name': 'abc_if',
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    module_args = {
        'vserver': 'vserver',
        'use_rest': 'never'
    }
    error = create_module(interface_module, module_args, fail=True)['msg']
    assert 'missing required arguments:' in error
    assert 'interface_name' in error


def test_create_error_missing_param():
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'vserver': 'vserver',
        'home_node': 'node',
        'use_rest': 'never'
    }
    msg = 'Error: Missing one or more required parameters for creating interface:'
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert msg in error
    assert 'role' in error


def test_successful_create():
    ''' Test successful create '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
        ('ZAPI', 'net-interface-create', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'vserver',
        'home_node': 'node',
        'role': 'data',
        # 'subnet_name': 'subnet_name',
        'address': '10.10.10.13',
        'netmask': '255.255.255.0',
        'failover_policy': 'system-defined',
        'failover_group': 'failover_group',
        'firewall_policy': 'firewall_policy',
        'is_auto_revert': True,
        'admin_status': 'down',
        'force_subnet_association': True,
        'dns_domain_name': 'dns_domain_name',
        'listen_for_dns_query': True,
        'is_dns_update_enabled': True,
        # 'is_ipv4_link_local': False,
        'service_policy': 'service_policy'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_create_for_NVMe():
    ''' Test successful create for NVMe protocol'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
        ('ZAPI', 'cluster-node-get-iter', ZRR['node_info']),
        ('ZAPI', 'net-interface-create', ZRR['success']),
    ])
    module_args = {
        'vserver': 'vserver',
        # 'home_node': 'node',
        'role': 'data',
        'protocols': ['fc-nvme'],
        'subnet_name': 'subnet_name',
        'use_rest': 'never'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_idempotency_for_NVMe():
    ''' Test successful create for NVMe protocol'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
    ])
    module_args = {
        'vserver': 'vserver',
        'home_node': 'node',
        'role': 'data',
        'protocols': ['fc-nvme'],
        'use_rest': 'never'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_create_error_for_NVMe():
    ''' Test if create throws an error if required param 'protocols' uses NVMe'''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
    ])
    msg = 'Error: Following parameters for creating interface are not supported for data-protocol fc-nvme:'
    module_args = {
        'vserver': 'vserver',
        'protocols': ['fc-nvme'],
        'address': '1.1.1.1',
        'use_rest': 'never'
    }
    error = call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert msg in error
    for option in ('netmask', 'address', 'firewall_policy'):
        assert option in error


def test_create_idempotency():
    ''' Test create idempotency, and ignore EMS logging error '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['error']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
    ])
    module_args = {
        'vserver': 'vserver',
        'use_rest': 'never'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_delete():
    ''' Test delete existing interface, and ignore EMS logging error '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['error']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info_no_dns']),
        ('ZAPI', 'net-interface-modify', ZRR['success']),               # offline
        ('ZAPI', 'net-interface-delete', ZRR['success']),
    ])
    module_args = {
        'state': 'absent',
        'vserver': 'vserver',
        'use_rest': 'never'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_delete_idempotency():
    ''' Test delete idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
    ])
    module_args = {
        'state': 'absent',
        'vserver': 'vserver',
        'use_rest': 'never'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_successful_modify():
    ''' Test successful modify interface_minutes '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
        ('ZAPI', 'net-interface-modify', ZRR['success']),
    ])
    module_args = {
        'vserver': 'vserver',
        'dns_domain_name': 'test2.com',
        'home_port': 'e0d',
        'is_dns_update_enabled': False,
        'is_ipv4_link_local': True,
        'listen_for_dns_query': False,
        'use_rest': 'never'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_modify_idempotency():
    ''' Test modify idempotency '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
    ])
    module_args = {
        'vserver': 'vserver',
        'use_rest': 'never'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_error_message():
    register_responses([
        # create, missing params
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
        ('ZAPI', 'cluster-node-get-iter', ZRR['no_records']),

        # create - get home_node error
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
        ('ZAPI', 'cluster-node-get-iter', ZRR['error']),

        # create error
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
        ('ZAPI', 'cluster-node-get-iter', ZRR['error_13003']),
        ('ZAPI', 'net-interface-create', ZRR['error']),

        # create error
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
        ('ZAPI', 'cluster-node-get-iter', ZRR['no_records']),
        ('ZAPI', 'net-interface-create', ZRR['error_17']),

        # modify error
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
        ('ZAPI', 'net-interface-modify', ZRR['error']),

        # rename error
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
        ('ZAPI', 'net-interface-rename', ZRR['error']),

        # delete error
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
        ('ZAPI', 'net-interface-modify', ZRR['success']),
        ('ZAPI', 'net-interface-delete', ZRR['error']),

        # get error
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['error']),
    ])
    module_args = {
        'vserver': 'vserver',
        'use_rest': 'never',
    }
    msg = 'Error: Missing one or more required parameters for creating interface:'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['home_port'] = 'e0d'
    module_args['role'] = 'data'
    module_args['address'] = '10.11.12.13'
    module_args['netmask'] = '255.192.0.0'
    msg = 'Error fetching node for interface abc_if: NetApp API failed. Reason - 12345:'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = 'Error Creating interface abc_if: NetApp API failed. Reason - 12345:'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    # LIF already exists (error 17)
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args['home_port'] = 'new_port'
    msg = 'Error modifying interface abc_if: NetApp API failed. Reason - 12345:'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['from_name'] = 'old_name'
    msg = 'Error renaming old_name to abc_if: NetApp API failed. Reason - 12345:'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['state'] = 'absent'
    msg = 'Error deleting interface abc_if: NetApp API failed. Reason - 12345:'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = 'Error fetching interface details for abc_if: NetApp API failed. Reason - 12345:'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_successful_rename():
    ''' Test successful '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
        ('ZAPI', 'net-interface-rename', ZRR['success']),
        ('ZAPI', 'net-interface-modify', ZRR['success']),
    ])
    module_args = {
        'vserver': 'vserver',
        'dns_domain_name': 'test2.com',
        'from_name': 'from_interface_name',
        'home_port': 'new_port',
        'is_dns_update_enabled': False,
        'listen_for_dns_query': False,
        'use_rest': 'never'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_negative_rename_not_found():
    ''' Test from interface not found '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
        ('ZAPI', 'net-interface-get-iter', ZRR['no_records']),
    ])
    msg = 'Error renaming interface abc_if: no interface with from_name from_interface_name.'
    module_args = {
        'vserver': 'vserver',
        'dns_domain_name': 'test2.com',
        'from_name': 'from_interface_name',
        'home_port': 'new_port',
        'is_dns_update_enabled': False,
        'listen_for_dns_query': False,
        'use_rest': 'never'
    }
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_successful_migrate():
    ''' Test successful '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
        ('ZAPI', 'net-interface-modify', ZRR['success']),
        ('ZAPI', 'net-interface-migrate', ZRR['success']),
        ('ZAPI', 'net-interface-migrate', ZRR['success']),
    ])
    module_args = {
        'vserver': 'vserver',
        'dns_domain_name': 'test2.com',
        'current_node': 'new_node',
        'is_dns_update_enabled': False,
        'listen_for_dns_query': False,
        'use_rest': 'never'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_negative_migrate():
    ''' Test successful '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
        ('ZAPI', 'net-interface-modify', ZRR['success']),

        # 2nd try
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
        ('ZAPI', 'net-interface-modify', ZRR['success']),
        ('ZAPI', 'net-interface-migrate', ZRR['error']),

        # 3rd try
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'net-interface-get-iter', ZRR['interface_info']),
        ('ZAPI', 'net-interface-modify', ZRR['success']),
        ('ZAPI', 'net-interface-migrate', ZRR['success']),
        ('ZAPI', 'net-interface-migrate', ZRR['error']),
    ])
    module_args = {
        'vserver': 'vserver',
        'dns_domain_name': 'test2.com',
        'current_port': 'new_port',
        'is_dns_update_enabled': False,
        'listen_for_dns_query': False,
        'use_rest': 'never'
    }
    msg = 'current_node must be set to migrate'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args['current_node'] = 'new_node'
    msg = 'Error migrating new_node: NetApp API failed. Reason - 12345'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    msg = 'Error migrating new_node: NetApp API failed. Reason - 12345'
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


SRR = rest_responses({
    'one_record_home_node': (200, {'records': [
        {'name': 'node2_abc_if',
         'uuid': '54321',
         'enabled': True,
         'location': {'home_port': {'name': 'e0c'}, 'home_node': {'name': 'node2'}, 'node': {'name': 'node2'}, 'port': {'name': 'e0c'}}
         }]}, None),
    'one_record_vserver': (200, {'records': [{
        'name': 'abc_if',
        'uuid': '54321',
        'svm': {'name': 'vserver', 'uuid': 'svm_uuid'},
        'dns_zone': 'netapp.com',
        'ddns_enabled': True,
        'data_protocol': ['nfs'],
        'enabled': True,
        'ip': {'address': '10.11.12.13', 'netmask': '255.192.0.0'},
        'location': {
            'home_port': {'name': 'e0c'},
            'home_node': {'name': 'node2'},
            'node': {'name': 'node2'},
            'port': {'name': 'e0c'},
            'auto_revert': True,
            'failover': True
        },
        'service_policy': {'name': 'data-mgmt'}
    }]}, None),
    'two_records': (200, {'records': [{'name': 'node2_abc_if'}, {'name': 'node2_abc_if'}]}, None),
    'error_precluster': (500, None, {'message': 'are available in precluster.'}),
    'cluster_identity': (200, {'location': 'Oz', 'name': 'abc'}, None),
    'nodes': (200, {'records': [
        {'name': 'node2', 'uuid': 'uuid2', 'cluster_interfaces': [{'ip': {'address': '10.10.10.2'}}]}
    ]}, None),
    'nodes_two_records': (200, {'records': [
        {'name': 'node2', 'uuid': 'uuid2', 'cluster_interfaces': [{'ip': {'address': '10.10.10.2'}}]},
        {'name': 'node3', 'uuid': 'uuid2', 'cluster_interfaces': [{'ip': {'address': '10.10.10.2'}}]}
    ]}, None),
}, False)


def test_rest_create_ip_no_svm():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['zero_records']),      # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                     # get nodes
        ('POST', 'network/ip/interfaces', SRR['success']),          # post
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_create_ip_no_svm_idempotent():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),      # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                             # get nodes
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_create_ip_no_svm_idempotent_localhost():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),      # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                             # get nodes
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'home_node': 'localhost',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_create_ip_with_svm():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['zero_records']),      # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                     # get nodes
        ('POST', 'network/ip/interfaces', SRR['success']),          # post
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'vserver': 'vserver',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_create_fc_with_svm():
    ''' create FC interface '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'network/fc/interfaces', SRR['zero_records']),      # get FC
        ('POST', 'network/fc/interfaces', SRR['success']),          # post
    ])
    module_args = {
        'use_rest': 'always',
        'vserver': 'vserver',
        'data_protocol': 'fc_nvme',
        'home_node': 'my_node',
        'protocols': 'fc-nvme'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_create_fc_with_svm_no_home_port():
    ''' create FC interface '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/fc/interfaces', SRR['zero_records']),      # get FC
        ('GET', 'cluster/nodes', SRR['nodes']),                     # get nodes
        ('POST', 'network/fc/interfaces', SRR['success']),          # post
    ])
    args = dict(DEFAULT_ARGS)
    module_args = {
        'use_rest': 'always',
        'vserver': 'vserver',
        'data_protocol': 'fc_nvme',
        'protocols': 'fc-nvme',
        'current_port': args.pop('home_port'),
        'current_node': 'my_node',
    }
    assert call_main(my_main, args, module_args)['changed']


@patch('time.sleep')
def test_rest_create_ip_with_cluster_svm(dont_sleep):
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['zero_records']),                  # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                                 # get nodes
        ('POST', 'network/ip/interfaces', SRR['one_record_vserver']),           # post
        ('PATCH', 'network/ip/interfaces/54321', SRR['one_record_vserver']),    # migrate
        ('GET', 'network/ip/interfaces', SRR['one_record_vserver']),            # get IP
    ])
    module_args = {
        'use_rest': 'always',
        'admin_status': 'up',
        'current_port': 'e0c',
        'failover_scope': 'home_node_only',
        'ipspace': 'cluster',
        'vserver': 'vserver',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
        'role': 'intercluster'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised('Ignoring vserver with REST for non data SVM.')


def test_rest_negative_create_ip():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['zero_records']),       # get IP
        ('GET', 'cluster/nodes', SRR['zero_records']),               # get nodes
    ])
    msg = 'Error: Cannot guess home_node, home_node is required when home_port is present with REST.'
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
    }
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_negative_create_ip_with_svm_no_home_port():
    ''' create FC interface '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['zero_records']),      # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                     # get nodes
        # ('POST', 'network/fc/interfaces', SRR['success']),          # post
    ])
    args = dict(DEFAULT_ARGS)
    args.pop('home_port')
    module_args = {
        'use_rest': 'always',
        'vserver': 'vserver',
        'interface_type': 'ip',
    }
    error = "Error: At least one of 'broadcast_domain', 'home_port', 'home_node' is required to create an IP interface."
    assert error in call_main(my_main, args, module_args, fail=True)['msg']


def test_rest_negative_create_no_ip_address():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['zero_records']),    # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),     # get nodes
    ])
    msg = 'Error: Missing one or more required parameters for creating interface: interface_type.'
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
    }
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_get_fc_no_svm():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster/nodes', SRR['nodes']),     # get nodes
    ])
    module_args = {
        'use_rest': 'always',
        'interface_type': 'fc',
    }
    msg = "A data 'vserver' is required for FC interfaces."
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_negative_get_multiple_ip_if():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['two_records']),       # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                     # get nodes
    ])
    msg = 'Error: multiple records for: node2_abc_if'
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
    }
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_negative_get_multiple_fc_if():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['zero_records']),  # get IP
        ('GET', 'network/fc/interfaces', SRR['two_records']),   # get FC
    ])
    msg = 'Error: unexpected records for name: abc_if, vserver: not_cluster'
    module_args = {
        'use_rest': 'always',
        'vserver': 'not_cluster',
    }
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_negative_get_multiple_ip_fc_if():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_vserver']),        # get IP
        ('GET', 'network/fc/interfaces', SRR['one_record_vserver']),        # get FC
    ])
    msg = 'Error fetching interface abc_if - found duplicate entries, please indicate interface_type.'
    module_args = {
        'use_rest': 'always',
        'vserver': 'not_cluster',
    }
    assert msg in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_modify_idempotent_ip_no_svm():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),  # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                         # get nodes
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_modify_ip_no_svm():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['zero_records']),           # get IP
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),  # get IP
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
        'home_node': 'node2',
        'interface_name': 'new_name',
        'from_name': 'abc_if'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_modify_ip_svm():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_vserver']),    # get IP
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
    ])
    module_args = {
        'use_rest': 'always',
        'vserver': 'vserver',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
        'home_node': 'node1',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_rest_migrate_ip_no_svm(sleep_mock):
    ''' create cluster '''
    modified = copy.deepcopy(SRR['one_record_home_node'])
    modified[1]['records'][0]['location']['node']['name'] = 'node1'
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),      # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                             # get nodes (for get)
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),      # get - no change
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', modified),
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
        'current_node': 'node1',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_rest_migrate_ip_no_svm_port(sleep_mock):
    ''' create cluster '''
    modified = copy.deepcopy(SRR['one_record_home_node'])
    modified[1]['records'][0]['location']['port']['name'] = 'port1'
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),      # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                             # get nodes (for get)
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),      # get - no change
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', modified),
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
        'current_port': 'port1',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_rest_migrate_ip_svm(sleep_mock):
    ''' create cluster '''
    modified = copy.deepcopy(SRR['one_record_home_node'])
    modified[1]['records'][0]['location']['node']['name'] = 'node1'
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),      # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                             # get nodes (for get)
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', modified),
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
        'current_node': 'node1',
        'vserver': 'vserver'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_rest_migrate_ip_error(sleep_mock):
    ''' create cluster '''
    modified = copy.deepcopy(SRR['one_record_home_node'])
    modified[1]['records'][0]['location']['node']['name'] = 'node1'
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),      # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                             # get nodes (for get)
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['generic_error']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
        'current_node': 'node1',
        'vserver': 'vserver'
    }
    error = rest_error_message('Errors waiting for migration to complete', 'network/ip/interfaces')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_rest_migrate_ip_timeout(sleep_mock):
    ''' create cluster '''
    modified = copy.deepcopy(SRR['one_record_home_node'])
    modified[1]['records'][0]['location']['node']['name'] = 'node1'
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),      # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                             # get nodes (for get)
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
        'current_node': 'node1',
        'vserver': 'vserver'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert_warning_was_raised('Failed to confirm interface is migrated after 120 seconds')


def test_rest_delete_ip_no_svm():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['one_record_home_node']),  # get IP
        ('GET', 'cluster/nodes', SRR['nodes']),                         # get nodes (for get)
        ('DELETE', 'network/ip/interfaces/54321', SRR['success']),      # delete
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
        'state': 'absent',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_disable_delete_fc():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/fc/interfaces', SRR['one_record_vserver']),    # get IP
        ('PATCH', 'network/fc/interfaces/54321', SRR['success']),       # disable fc before delete
        ('DELETE', 'network/fc/interfaces/54321', SRR['success']),      # delete
    ])
    module_args = {
        'use_rest': 'always',
        'state': 'absent',
        "admin_status": "up",
        "protocols": "fc-nvme",
        "role": "data",
        "vserver": "svm3",
        "current_port": "1a"
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_delete_idempotent_ip_no_svm():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['zero_records']),         # get IP
    ])
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'address': '10.12.12.13',
        'netmask': '255.255.192.0',
        'state': 'absent',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_derive_fc_protocol_fcp():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'protocols': ['fcp'],
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    my_obj.derive_fc_data_protocol()
    assert my_obj.parameters['data_protocol'] == 'fcp'


def test_derive_fc_protocol_nvme():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'protocols': ['fc-nvme'],
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    my_obj.derive_fc_data_protocol()
    assert my_obj.parameters['data_protocol'] == 'fc_nvme'


def test_derive_fc_protocol_empty():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'protocols': [],
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    assert my_obj.derive_fc_data_protocol() is None


def test_negative_derive_fc_protocol_nvme():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'protocols': ['fc-nvme', 'fcp'],
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    msg = "A single protocol entry is expected for FC interface, got ['fc-nvme', 'fcp']."
    assert msg in expect_and_capture_ansible_exception(my_obj.derive_fc_data_protocol, 'fail')['msg']


def test_negative_derive_fc_protocol_nvme_mismatch():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'protocols': ['fc-nvme'],
        'data_protocol': 'fcp'
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    msg = "Error: mismatch between configured data_protocol: fcp and data_protocols: ['fc-nvme']"
    assert msg in expect_and_capture_ansible_exception(my_obj.derive_fc_data_protocol, 'fail')['msg']


def test_negative_derive_fc_protocol_unexpected():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'protocols': ['fc-unknown'],
        'data_protocol': 'fcp'
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    msg = "Unexpected protocol value fc-unknown."
    assert msg in expect_and_capture_ansible_exception(my_obj.derive_fc_data_protocol, 'fail')['msg']


def test_derive_interface_type_nvme():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'protocols': ['fc-nvme'],
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    my_obj.derive_interface_type()
    assert my_obj.parameters['interface_type'] == 'fc'


def test_derive_interface_type_iscsi():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'protocols': ['iscsi'],
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    my_obj.derive_interface_type()
    assert my_obj.parameters['interface_type'] == 'ip'


def test_derive_interface_type_cluster():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'role': 'cluster',
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    my_obj.derive_interface_type()
    assert my_obj.parameters['interface_type'] == 'ip'


def test_negative_derive_interface_type_nvme_mismatch():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    msg = "Error: mismatch between configured interface_type: ip and derived interface_type: fc."
    module_args = {
        'use_rest': 'always',
        'protocols': ['fc-nvme'],
        'interface_type': 'ip'
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    assert msg in expect_and_capture_ansible_exception(my_obj.derive_interface_type, 'fail')['msg']


def test_negative_derive_interface_type_unknown():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    msg = "Error: unable to determine interface type, please set interface_type: unexpected value(s) for protocols: ['unexpected']"
    module_args = {
        'use_rest': 'always',
        'protocols': ['unexpected'],
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    assert msg in expect_and_capture_ansible_exception(my_obj.derive_interface_type, 'fail')['msg']


def test_negative_derive_interface_type_multiple():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    msg = "Error: unable to determine interface type, please set interface_type: incompatible value(s) for protocols: ['fc-nvme', 'cifs']"
    module_args = {
        'use_rest': 'always',
        'protocols': ['fc-nvme', 'cifs'],
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    assert msg in expect_and_capture_ansible_exception(my_obj.derive_interface_type, 'fail')['msg']


def test_derive_block_file_type_fcp():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    block_p, file_p, fcp = my_obj.derive_block_file_type(['fcp'])
    assert block_p
    assert not file_p
    assert fcp
    module_args['interface_type'] = 'fc'
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    block_p, file_p, fcp = my_obj.derive_block_file_type(None)
    assert block_p
    assert not file_p
    assert fcp


def test_derive_block_file_type_iscsi():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    block_p, file_p, fcp = my_obj.derive_block_file_type(['iscsi'])
    assert block_p
    assert not file_p
    assert not fcp


def test_derive_block_file_type_cifs():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    block_p, file_p, fcp = my_obj.derive_block_file_type(['cifs'])
    assert not block_p
    assert file_p
    assert not fcp


def test_derive_block_file_type_mixed():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    error = "Cannot use any of ['fcp'] with ['cifs']"
    assert expect_and_capture_ansible_exception(my_obj.derive_block_file_type, 'fail', ['cifs', 'fcp'])['msg'] == error


def test_map_failover_policy():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {
        'use_rest': 'always',
        'failover_policy': 'local-only',
    }
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    my_obj.map_failover_policy()
    assert my_obj.parameters['failover_scope'] == 'home_node_only'


def test_rest_negative_unsupported_zapi_option_fail():
    ''' create cluster '''
    register_responses([
    ])
    msg = "REST API currently does not support 'is_ipv4_link_local'"
    module_args = {
        'use_rest': 'always',
        'ipspace': 'cluster',
        'is_ipv4_link_local': True,
    }
    assert msg in create_module(interface_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_negative_unsupported_zapi_option_force_zapi_1():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    msg = "missing required argument with ZAPI: vserver"
    module_args = {
        'use_rest': 'auto',
        'ipspace': 'cluster',
        'is_ipv4_link_local': True,
    }
    assert msg in create_module(interface_module, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_rest_negative_unsupported_zapi_option_force_zapi_2(mock_netapp_lib):
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    mock_netapp_lib.return_value = False
    msg = "the python NetApp-Lib module is required"
    module_args = {
        'use_rest': 'auto',
        'ipspace': 'cluster',
        'is_ipv4_link_local': True,
    }
    assert msg in create_module(interface_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_negative_unsupported_rest_version():
    ''' create cluster '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    msg = "Error: REST requires ONTAP 9.7 or later for interface APIs."
    module_args = {'use_rest': 'always'}
    assert msg == create_module(interface_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_auto_falls_back_to_zapi_if_ip_9_6():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96'])
    ])
    module_args = {'use_rest': 'auto'}
    # vserver is a required parameter with ZAPI
    msg = "missing required argument with ZAPI: vserver"
    assert msg in create_module(interface_module, DEFAULT_ARGS, module_args, fail=True)['msg']
    print_warnings
    assert_warning_was_raised('Falling back to ZAPI: REST requires ONTAP 9.7 or later for interface APIs.')


def test_fix_errors():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97'])
    ])
    module_args = {'use_rest': 'auto'}
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    control = {'xx': 11, 'yy': 22}
    # no role in error
    errors = dict(control)
    assert my_obj.fix_errors(None, errors) is None
    assert errors == control
    # role/firewall_policy/protocols/service_policy -> service_policy
    tests = [
        ('data', 'data', ['nfs'], None, 'default-data-files', True),
        ('data', 'data', ['cifs'], None, 'default-data-files', True),
        ('data', 'data', ['iscsi'], None, 'default-data-blocks', True),
        ('data', '', ['fc-nvme'], None, 'unchanged', True),
        ('data', 'mgmt', ['ignored'], None, 'default-management', True),
        ('data', '', ['nfs'], None, 'default-data-files', True),
        ('data', '', ['cifs'], None, 'default-data-files', True),
        ('data', '', ['iscsi'], None, 'default-data-blocks', True),
        ('data', 'mgmt', ['ignored'], None, 'default-management', True),
        ('intercluster', 'intercluster', ['ignored'], None, 'default-intercluster', True),
        ('intercluster', '', ['ignored'], None, 'default-intercluster', True),
        ('cluster', 'mgmt', ['ignored'], None, 'default-cluster', True),
        ('cluster', '', ['ignored'], None, 'default-cluster', True),
        ('cluster', 'other', ['ignored'], None, 'unchanged', False),
    ]
    for role, firewall_policy, protocols, service_policy, expected_service_policy, fixed in tests:
        my_obj.parameters['protocols'] = protocols
        if service_policy:
            my_obj['service_policy'] = service_policy
        options = {'service_policy': 'unchanged'}
        errors = dict(control)
        errors['role'] = role
        if firewall_policy:
            errors['firewall_policy'] = firewall_policy
        assert my_obj.fix_errors(options, errors) is None
        print('OPTIONS', options)
        assert 'service_policy' in options
        assert options['service_policy'] == expected_service_policy
        assert errors == control or not fixed
        assert fixed or 'role' in errors


def test_error_messages_get_interface_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'network/ip/interfaces', SRR['two_records']),           # get IP
        ('GET', 'cluster/nodes', SRR['generic_error']),                 # get nodes
        # second call
        ('GET', 'network/ip/interfaces', SRR['one_record_vserver']),    # get IP
        ('GET', 'network/fc/interfaces', SRR['generic_error']),         # get FC
        # third call
        ('GET', 'network/ip/interfaces', SRR['generic_error']),    # get IP
        ('GET', 'network/fc/interfaces', SRR['one_record_vserver']),         # get FC
        # fourth call
        ('GET', 'network/ip/interfaces', SRR['generic_error']),         # get IP
        ('GET', 'network/fc/interfaces', SRR['generic_error']),         # get FC
        # fifth call
        ('GET', 'network/ip/interfaces', SRR['error_precluster']),      # get IP
    ])
    module_args = {'use_rest': 'auto'}
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    # first call
    error = 'Error fetching cluster node info'
    assert expect_and_capture_ansible_exception(my_obj.get_interface_rest, 'fail', 'my_lif')['msg'] == rest_error_message(error, 'cluster/nodes')
    # second call
    # reset value, as it was set for ip
    del my_obj.parameters['interface_type']
    my_obj.parameters['vserver'] = 'not_cluster'
    assert my_obj.get_interface_rest('my_lif') is not None
    # third call
    # reset value, as it was set for ip
    del my_obj.parameters['interface_type']
    my_obj.parameters['vserver'] = 'not_cluster'
    assert my_obj.get_interface_rest('my_lif') is not None
    # fourth call
    # reset value, as it was set for fc
    del my_obj.parameters['interface_type']
    error = expect_and_capture_ansible_exception(my_obj.get_interface_rest, 'fail', 'my_lif')['msg']
    assert rest_error_message('Error fetching interface details for my_lif', 'network/ip/interfaces') in error
    assert rest_error_message('', 'network/fc/interfaces') in error
    # fifth call
    error = 'This module cannot use REST in precluster mode, ZAPI can be forced with use_rest: never.'
    assert error in expect_and_capture_ansible_exception(my_obj.get_interface_rest, 'fail', 'my_lif')['msg']


def test_error_messages_rest_find_interface():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster/nodes', SRR['nodes_two_records']),             # get nodes
    ])
    module_args = {'use_rest': 'auto'}
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    # no calls
    # no interface type
    error = 'Error: missing option "interface_type (or could not be derived)'
    assert error in expect_and_capture_ansible_exception(my_obj.get_net_int_api, 'fail')['msg']
    # multiple records for cluster
    records = [
        {'name': 'node_name'},
        {'name': 'node_name'}
    ]
    error = 'Error: multiple records for: node_name - %s' % records
    assert error in expect_and_capture_ansible_exception(my_obj.find_interface_record, 'fail', records, 'node', 'name')['msg']
    # multiple records with vserver
    records = [1, 2]
    my_obj.parameters['vserver'] = 'vserver'
    error = 'Error: unexpected records for name: name, vserver: vserver - [1, 2]'
    assert error in expect_and_capture_ansible_exception(my_obj.find_exact_match, 'fail', records, 'name')['msg']
    # multiple records with ambiguity, home_node set (warn)
    del my_obj.parameters['vserver']
    my_obj.parameters['home_node'] = 'node'
    records = [
        {'name': 'node_name'},
        {'name': 'node_name'}
    ]
    error = 'Error: multiple records for: node_name - %s' % records
    assert error in expect_and_capture_ansible_exception(my_obj.find_exact_match, 'fail', records, 'name')['msg']
    records = [
        {'name': 'node_name'},
        {'name': 'name'}
    ]
    record = my_obj.find_exact_match(records, 'name')
    assert record == {'name': 'node_name'}
    assert_warning_was_raised("Found both ['name', 'node_name'], selecting node_name")
    assert_warning_was_raised("adjusting name from name to node_name")
    # fifth call (get nodes, cached)
    # multiple records with different home nodes
    del my_obj.parameters['home_node']
    records = [
        {'name': 'node2_name'},
        {'name': 'node3_name'}
    ]
    error = "Error: multiple matches for name: name: ['node2_name', 'node3_name'].  Set home_node parameter."
    assert error in expect_and_capture_ansible_exception(my_obj.find_exact_match, 'fail', records, 'name')['msg']
    # multiple records with home node and no home node
    records = [
        {'name': 'node2_name'},
        {'name': 'name'}
    ]
    error = "Error: multiple matches for name: name: ['name', 'node2_name'].  Set home_node parameter."
    assert error in expect_and_capture_ansible_exception(my_obj.find_exact_match, 'fail', records, 'name')['msg']
    # sixth call
    error = "Error: multiple matches for name: name: ['name', 'node2_name'].  Set home_node parameter."
    assert error in expect_and_capture_ansible_exception(my_obj.find_exact_match, 'fail', records, 'name')['msg']


def test_error_messages_rest_misc():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('POST', 'network/type/interfaces', SRR['generic_error']),
        ('PATCH', 'network/type/interfaces/uuid', SRR['generic_error']),
        ('DELETE', 'network/type/interfaces/uuid', SRR['generic_error']),
    ])
    module_args = {'use_rest': 'auto'}
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    # no calls
    # no interface type
    error = 'Error, expecting uuid in existing record'
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_payloads, 'fail', 'delete', {}, {})['msg']
    my_obj.parameters['interface_type'] = 'type'
    error = rest_error_message('Error creating interface abc_if', 'network/type/interfaces')
    assert error in expect_and_capture_ansible_exception(my_obj.create_interface_rest, 'fail', {})['msg']
    error = rest_error_message('Error modifying interface abc_if', 'network/type/interfaces/uuid')
    assert error in expect_and_capture_ansible_exception(my_obj.modify_interface_rest, 'fail', 'uuid', {'xxx': 'yyy'})['msg']
    error = rest_error_message('Error deleting interface abc_if', 'network/type/interfaces/uuid')
    assert error in expect_and_capture_ansible_exception(my_obj.delete_interface_rest, 'fail', 'uuid')['msg']


def test_error_messages_build_rest_body_and_validations():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
    ])
    module_args = {'use_rest': 'always'}
    my_obj = create_module(interface_module, DEFAULT_ARGS, module_args)
    my_obj.parameters['home_node'] = 'node1'
    my_obj.parameters['protocols'] = ['nfs']
    my_obj.parameters['role'] = 'intercluster'
    error = 'Error: Missing one or more required parameters for creating interface: interface_type.'
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail')['msg']
    my_obj.parameters['interface_type'] = 'type'
    error = 'Error: unexpected value for interface_type: type.'
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail')['msg']
    my_obj.parameters['interface_type'] = 'ip'
    my_obj.parameters['ipspace'] = 'ipspace'
    error = 'Error: Protocol cannot be specified for intercluster role, failed to create interface.'
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail')['msg']
    del my_obj.parameters['protocols']
    my_obj.parameters['interface_type'] = 'fc'
    error = "Error: 'home_port' is not supported for FC interfaces with 9.7, use 'current_port', avoid home_node."
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail')['msg']
    print_warnings()
    assert_warning_was_raised("Avoid 'home_node' with FC interfaces with 9.7, use 'current_node'.")
    del my_obj.parameters['home_port']
    error = "Error: A data 'vserver' is required for FC interfaces."
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail')['msg']
    my_obj.parameters['current_port'] = '0a'
    my_obj.parameters['data_protocol'] = 'fc'
    my_obj.parameters['force_subnet_association'] = True
    my_obj.parameters['failover_group'] = 'failover_group'
    my_obj.parameters['vserver'] = 'vserver'
    error = "Error: 'role' is deprecated, and 'data' is the only value supported for FC interfaces: found intercluster."
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail')['msg']
    my_obj.parameters['role'] = 'data'
    error = "Error creating interface, unsupported options: {'failover_group': 'failover_group'}"
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail')['msg']
    del my_obj.parameters['failover_group']
    my_obj.parameters['broadcast_domain'] = 'BDD1'
    error = "Error: broadcast_domain option only supported for IP interfaces: abc_if, interface_type: fc"
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail', None)['msg']
    my_obj.parameters['service_policy'] = 'svc_pol'
    error = "Error: 'service_policy' is not supported for FC interfaces."
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail', None)['msg']
    print_warnings()
    assert_warning_was_raised('Ignoring force_subnet_association')
    my_obj.parameters['interface_type'] = 'ip'
    del my_obj.parameters['vserver']
    del my_obj.parameters['ipspace']
    error = 'Error: ipspace name must be provided if scope is cluster, or vserver for svm scope.'
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail')['msg']
    modify = {'ipspace': 'ipspace'}
    error = "The following option cannot be modified: ipspace.name"
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail', modify)['msg']
    del my_obj.parameters['role']
    my_obj.parameters['current_port'] = 'port1'
    my_obj.parameters['home_port'] = 'port1'
    my_obj.parameters['ipspace'] = 'ipspace'
    error = "Error: home_port and broadcast_domain are mutually exclusive for creating: abc_if"
    assert error in expect_and_capture_ansible_exception(my_obj.build_rest_body, 'fail', None)['msg']


def test_dns_domain_ddns_enabled():
    ''' domain and ddns enabled option test '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'network/ip/interfaces', SRR['zero_records']),
        ('GET', 'cluster/nodes', SRR['nodes']),
        ('POST', 'network/ip/interfaces', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'network/ip/interfaces', SRR['one_record_vserver']),
        ('GET', 'cluster/nodes', SRR['nodes']),
        ('PATCH', 'network/ip/interfaces/54321', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'network/fc/interfaces', SRR['zero_records']),
        ('GET', 'cluster', SRR['is_rest_9_9_0'])
    ])
    module_args = {
        'use_rest': 'always',
        'address': '10.11.12.13',
        'netmask': '255.192.0.0',
        'vserver': 'vserver',
        'dns_domain_name': 'netapp1.com',
        'is_dns_update_enabled': False
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    del module_args['address']
    del module_args['netmask']
    args = {'data_protocol': 'fc_nvme', 'home_node': 'my_node', 'protocols': 'fc-nvme', 'interface_type': 'fc'}
    module_args.update(args)
    assert 'dns_domain_name, is_dns_update_enabled options only supported for IP interfaces' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert 'Error: Minimum version of ONTAP for is_dns_update_enabled is (9, 9, 1).' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
