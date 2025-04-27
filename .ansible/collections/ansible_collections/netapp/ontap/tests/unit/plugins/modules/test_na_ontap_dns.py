# (c) 2018-2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_dns'''

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
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import call_main, create_module, expect_and_capture_ansible_exception, \
    patch_ansible, assert_warning_was_raised, print_warnings


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_dns import main as my_main, NetAppOntapDns as my_module      # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


# REST API canned responses when mocking send_request
SRR = rest_responses({
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'dns_record': (200, {"records": [{"domains": ['test.com'],
                                      "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7",
                                      "servers": ['0.0.0.0'],
                                      "svm": {"name": "svm1", "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"}}]}, None),
    'cluster_data': (200, {"dns_domains": ['test.com'],
                           "name_servers": ['0.0.0.0'],
                           "name": "cserver",
                           "uuid": "C2c9e252-41be-11e9-81d5-00a0986138f7"}, None),
    'cluster_name': (200, {"name": "cserver",
                           "uuid": "C2c9e252-41be-11e9-81d5-00a0986138f7"}, None),
})

dns_info = {
    'attributes': {
        'net-dns-info': {
            'name-servers': [{'ip-address': '0.0.0.0'}],
            'domains': [{'string': 'test.com'}],
            'skip-config-validation': 'true'
        }
    }
}


ZRR = zapi_responses({
    'dns_info': build_zapi_response(dns_info),
    'error_15661': build_zapi_error(15661, 'not_found'),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'nameservers': ['0.0.0.0'],
    'domains': ['test.com'],
}


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never',
    }
    error = 'Error: vserver is a required parameter with ZAPI.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_zapi_get_error():
    register_responses([
        ('ZAPI', 'net-dns-get', ZRR['error']),
        ('ZAPI', 'net-dns-get', ZRR['error_15661']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'svm_abc',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    # get
    error = zapi_error_message('Error getting DNS info')
    assert error in expect_and_capture_ansible_exception(my_obj.get_dns, 'fail')['msg']
    assert my_obj.get_dns() is None


def test_idempotent_modify_dns():
    register_responses([
        ('ZAPI', 'net-dns-get', ZRR['dns_info']),
    ])
    module_args = {
        'use_rest': 'never',
        'vserver': 'svm_abc',
    }

    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_zapi_modify_dns():
    register_responses([
        ('ZAPI', 'net-dns-get', ZRR['dns_info']),
        ('ZAPI', 'net-dns-modify', ZRR['success']),
        # idempotency
        ('ZAPI', 'net-dns-get', ZRR['dns_info']),
        # error
        ('ZAPI', 'net-dns-get', ZRR['dns_info']),
        ('ZAPI', 'net-dns-modify', ZRR['error']),
    ])
    module_args = {
        'domains': ['new_test.com'],
        'nameservers': ['1.2.3.4'],
        'skip_validation': True,
        'use_rest': 'never',
        'vserver': 'svm_abc',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        'domains': ['test.com'],
        'skip_validation': True,
        'use_rest': 'never',
        'vserver': 'svm_abc',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        'domains': ['new_test.com'],
        'nameservers': ['1.2.3.4'],
        'skip_validation': True,
        'use_rest': 'never',
        'vserver': 'svm_abc',
    }
    error = zapi_error_message('Error modifying dns')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_zapi_create_dns():
    register_responses([
        ('ZAPI', 'net-dns-get', ZRR['empty']),
        ('ZAPI', 'net-dns-create', ZRR['success']),
        # idempotency
        ('ZAPI', 'net-dns-get', ZRR['dns_info']),
        # error
        ('ZAPI', 'net-dns-get', ZRR['empty']),
        ('ZAPI', 'net-dns-create', ZRR['error']),
    ])
    module_args = {
        'domains': ['test.com'],
        'skip_validation': True,
        'use_rest': 'never',
        'vserver': 'svm_abc',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    error = zapi_error_message('Error creating dns')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_zapi_delete_dns():
    register_responses([
        ('ZAPI', 'net-dns-get', ZRR['dns_info']),
        ('ZAPI', 'net-dns-destroy', ZRR['success']),
        # idempotency
        ('ZAPI', 'net-dns-get', ZRR['empty']),
        # error
        ('ZAPI', 'net-dns-get', ZRR['dns_info']),
        ('ZAPI', 'net-dns-destroy', ZRR['error']),
    ])
    module_args = {
        'domains': ['new_test.com'],
        'state': 'absent',
        'use_rest': 'never',
        'vserver': 'svm_abc',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    error = zapi_error_message('Error destroying dns')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_rest_error():
    module_args = {
        'use_rest': 'always',
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'cluster', SRR['generic_error']),
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        # create
        ('PATCH', 'cluster', SRR['generic_error']),
        ('PATCH', 'cluster', SRR['generic_error']),
        ('POST', 'name-services/dns', SRR['generic_error']),
        # delete
        ('DELETE', 'name-services/dns/uuid', SRR['generic_error']),
        # read
        ('GET', 'name-services/dns', SRR['generic_error']),
        # modify
        ('PATCH', 'cluster', SRR['generic_error']),
        ('PATCH', 'name-services/dns/uuid', SRR['generic_error']),
    ])
    error = rest_error_message('Error getting cluster info', 'cluster')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    # create
    my_obj.is_cluster = True
    error = rest_error_message('Error updating cluster DNS options', 'cluster')
    assert error in expect_and_capture_ansible_exception(my_obj.create_dns_rest, 'fail')['msg']
    my_obj.is_cluster = False
    # still cluster scope, as verserver is not set
    assert error in expect_and_capture_ansible_exception(my_obj.create_dns_rest, 'fail')['msg']
    my_obj.parameters['vserver'] = 'vserver'
    error = rest_error_message('Error creating DNS service', 'name-services/dns')
    assert error in expect_and_capture_ansible_exception(my_obj.create_dns_rest, 'fail')['msg']
    # delete
    my_obj.is_cluster = True
    error = 'Error: cluster scope when deleting DNS with REST requires ONTAP 9.9.1 or later.'
    assert error in expect_and_capture_ansible_exception(my_obj.destroy_dns_rest, 'fail', {})['msg']
    my_obj.is_cluster = False
    error = rest_error_message('Error deleting DNS service', 'name-services/dns/uuid')
    assert error in expect_and_capture_ansible_exception(my_obj.destroy_dns_rest, 'fail', {'uuid': 'uuid'})['msg']
    # read, cluster scope
    del my_obj.parameters['vserver']
    error = rest_error_message('Error getting DNS service', 'name-services/dns')
    assert error in expect_and_capture_ansible_exception(my_obj.get_dns_rest, 'fail')['msg']
    # modify
    dns_attrs = {
        'domains': [],
        'nameservers': [],
        'uuid': 'uuid',
    }
    my_obj.is_cluster = True
    error = rest_error_message('Error updating cluster DNS options', 'cluster')
    assert error in expect_and_capture_ansible_exception(my_obj.modify_dns_rest, 'fail', dns_attrs)['msg']
    my_obj.is_cluster = False
    error = rest_error_message('Error modifying DNS configuration', 'name-services/dns/uuid')
    assert error in expect_and_capture_ansible_exception(my_obj.modify_dns_rest, 'fail', dns_attrs)['msg']


def test_rest_successfully_create():
    module_args = {
        'use_rest': 'always',
        'vserver': 'svm_abc',
        'skip_validation': True
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/dns', SRR['zero_records']),
        ('POST', 'name-services/dns', SRR['success']),
    ])
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_create_is_cluster_vserver():
    module_args = {
        'use_rest': 'always',
        'vserver': 'cserver'
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'name-services/dns', SRR['zero_records']),
        ('GET', 'cluster', SRR['cluster_name']),
        ('PATCH', 'cluster', SRR['empty_good']),
    ])
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_idempotent_create_dns():
    module_args = {
        'use_rest': 'always',
        'vserver': 'svm_abc',
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'name-services/dns', SRR['dns_record']),
    ])
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_destroy():
    module_args = {
        'state': 'absent',
        'use_rest': 'always',
        'vserver': 'svm_abc',
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'name-services/dns', SRR['dns_record']),
        ('DELETE', 'name-services/dns/02c9e252-41be-11e9-81d5-00a0986138f7', SRR['success']),
    ])
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_idempotently_destroy():
    module_args = {
        'state': 'absent',
        'use_rest': 'always',
        'vserver': 'svm_abc',
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'name-services/dns', SRR['zero_records']),
        ('GET', 'cluster', SRR['cluster_data']),
    ])
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_modify():
    module_args = {
        'domains': 'new_test.com',
        'state': 'present',
        'use_rest': 'always',
        'vserver': 'svm_abc'
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'name-services/dns', SRR['dns_record']),
        ('PATCH', 'name-services/dns/02c9e252-41be-11e9-81d5-00a0986138f7', SRR['success']),
    ])
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_modify_is_cluster_vserver():
    module_args = {
        'domains': 'new_test.com',
        'state': 'present',
        'use_rest': 'always',
        'vserver': 'cserver'
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'name-services/dns', SRR['zero_records']),
        ('GET', 'cluster', SRR['cluster_data']),
        ('PATCH', 'cluster', SRR['empty_good']),
    ])
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_idempotently_modify():
    module_args = {
        'state': 'present',
        'use_rest': 'always',
        'vserver': 'svm_abc',
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'name-services/dns', SRR['dns_record']),
    ])
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_rest_successfully_modify_is_cluster_skip_validation():
    module_args = {
        'domains': 'new_test.com',
        'state': 'present',
        'use_rest': 'always',
        'skip_validation': True
    }
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'name-services/dns', SRR['zero_records']),
        ('PATCH', 'cluster', SRR['empty_good']),
        # error if used skip_validation on earlier versions.
        ('GET', 'cluster', SRR['is_rest']),
    ])
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert_warning_was_raised("skip_validation is ignored for cluster DNS operations in REST.")
    assert 'Error: Minimum version of ONTAP for skip_validation is (9, 9, 1)' in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_has_netapp_lib(has_netapp_lib):
    module_args = {
        'state': 'present',
        'use_rest': 'never',
        'vserver': 'svm_abc',
    }
    has_netapp_lib.return_value = False
    assert call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg'] == 'Error: the python NetApp-Lib module is required.  Import error: None'
