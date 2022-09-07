# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP license Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import sys
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_no_warnings, call_main, create_module, expect_and_capture_ansible_exception, patch_ansible
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, build_zapi_error, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_license import NetAppOntapLicense as my_module, main as my_main      # module under test


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


def license_status(fcp_method):
    return {
        'license-v2-status': [
            {'license-v2-status-info':
                {
                    'package': 'base',
                    'method': 'site'
                }},
            {'license-v2-status-info':
                {
                    'package': 'capacitypool',
                    'method': 'none'
                }},
            {'license-v2-status-info':
                {
                    'package': 'cifs',
                    'method': 'site'
                }},
            {'license-v2-status-info':
                {
                    'package': 'fcp',
                    'method': fcp_method
                }},
        ]
    }


ZRR = zapi_responses({
    'license_status_fcp_none': build_zapi_response(license_status('none')),
    'license_status_fcp_site': build_zapi_response(license_status('site')),
    'error_object_not_found': build_zapi_error('15661', 'license is not active')
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
}


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_netapp_lib_error(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    module_args = {
        "use_rest": "never"
    }
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_module_add_license_zapi():
    ''' Test add license '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'license-v2-status-list-info', ZRR['license_status_fcp_none']),
        ('ZAPI', 'license-v2-add', ZRR['success']),
        ('ZAPI', 'license-v2-status-list-info', ZRR['license_status_fcp_site']),
    ])
    module_args = {
        'use_rest': 'never',
        'license_codes': 'LICENSECODE',
    }
    print('ZRR', build_zapi_response(license_status('site'))[0].to_string())
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_module_add_license_idempotent_zapi():
    ''' Test add license idempotent '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'license-v2-status-list-info', ZRR['license_status_fcp_site']),
        ('ZAPI', 'license-v2-add', ZRR['success']),
        ('ZAPI', 'license-v2-status-list-info', ZRR['license_status_fcp_site']),
    ])
    module_args = {
        'use_rest': 'never',
        'license_codes': 'LICENSECODE',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_module_remove_license_zapi():
    ''' Test remove license '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'license-v2-status-list-info', ZRR['license_status_fcp_site']),
        ('ZAPI', 'license-v2-delete', ZRR['success']),
        ('ZAPI', 'license-v2-delete', ZRR['success']),
    ])
    module_args = {
        'use_rest': 'never',
        'serial_number': '1-8-000000',
        'license_names': 'cifs,fcp',
        'state': 'absent',
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_module_remove_license_idempotent_zapi():
    ''' Test remove license idempotent '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'license-v2-status-list-info', ZRR['license_status_fcp_site']),
        ('ZAPI', 'license-v2-delete', ZRR['error_object_not_found']),
        ('ZAPI', 'license-v2-delete', ZRR['error_object_not_found']),
    ])
    module_args = {
        'use_rest': 'never',
        'serial_number': '1-8-000000',
        'license_names': 'cifs,fcp',
        'state': 'absent',
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_module_remove_unused_expired_zapi():
    ''' Test remove unused expired license '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['no_records']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'license-v2-status-list-info', ZRR['license_status_fcp_site']),
        ('ZAPI', 'license-v2-delete-unused', ZRR['success']),
        ('ZAPI', 'license-v2-delete-expired', ZRR['success']),
        ('ZAPI', 'license-v2-status-list-info', ZRR['license_status_fcp_none']),
    ])
    module_args = {
        'use_rest': 'never',
        'remove_unused': True,
        'remove_expired': True,
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']


def test_module_try_to_remove_non_existent_package_license_zapi():
    ''' Try to remove non existent license '''
    register_responses([
        ('ZAPI', 'license-v2-delete', ZRR['error_object_not_found']),
    ])
    module_args = {
        'use_rest': 'never',
        'serial_number': '1-8-000000',
        'license_names': 'cifs',
        'state': 'absent',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    license_exist = my_obj.remove_licenses('cifs')
    assert not license_exist


def test_module_error_add_license_zapi():
    ''' Test error add license '''
    register_responses([
        ('ZAPI', 'license-v2-add', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
        'license_codes': 'random',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert 'Error adding licenses' in expect_and_capture_ansible_exception(my_obj.add_licenses, 'fail')['msg']


def test_module_error_remove_license_zapi():
    ''' Test error remove license '''
    register_responses([
        ('ZAPI', 'license-v2-delete', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
        'serial_number': '1-8-000000',
        'license_names': 'random',
        'state': 'absent',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert 'Error removing license' in expect_and_capture_ansible_exception(my_obj.remove_licenses, 'fail', 'random')['msg']


def test_module_error_get_and_remove_unused_expired_license_zapi():
    ''' Test error get and remove unused/expired license '''
    register_responses([
        ('ZAPI', 'license-v2-status-list-info', ZRR['error']),
        ('ZAPI', 'license-v2-delete-unused', ZRR['error']),
        ('ZAPI', 'license-v2-delete-expired', ZRR['error']),
    ])
    module_args = {
        'use_rest': 'never',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert 'Error checking license status' in expect_and_capture_ansible_exception(my_obj.get_licensing_status, 'fail')['msg']
    assert 'Error removing unused licenses' in expect_and_capture_ansible_exception(my_obj.remove_unused_licenses, 'fail')['msg']
    assert 'Error removing expired licenses' in expect_and_capture_ansible_exception(my_obj.remove_expired_licenses, 'fail')['msg']


# REST API canned responses when mocking send_request
SRR = rest_responses({
    'error_entry_does_not_exist': (404, None, "entry doesn't exist"),
    'license_record': (200, {
        "num_records": 3,
        "records": [
            {
                "name": "base",
                "scope": "cluster",
                "state": "compliant"
            },
            {
                "name": "nfs",
                "scope": "not_available",
                "state": "unlicensed"
            },
            {
                "name": "cifs",
                "scope": "site",
                "state": "compliant"
            }]
    }, None),
    'license_record_nfs': (200, {
        "num_records": 3,
        "records": [
            {
                "name": "base",
                "scope": "cluster",
                "state": "compliant"
            },
            {
                "name": "nfs",
                "scope": "site",
                "state": "compliant"
            },
            {
                "name": "cifs",
                "scope": "site",
                "state": "compliant"
            }]
    }, None),
    'license_record_no_nfs': (200, {
        "num_records": 3,
        "records": [
            {
                "name": "base",
                "scope": "cluster",
                "state": "compliant"
            },
            {
                "name": "cifs",
                "scope": "site",
                "state": "compliant"
            }]
    }, None)
}, False)


def test_module_fail_when_unsupported_rest_present():
    ''' error if unsupported rest properties present '''
    register_responses([
    ])
    module_args = {
        'remove_unused': True,
        'remove_expired': True,
        'use_rest': 'always'
    }
    error = 'REST API currently does not support'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_ensure_get_license_status_called_rest():
    ''' test get'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),
    ])
    module_args = {
        'use_rest': 'always'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert_no_warnings()


def test_module_error_get_license_rest():
    ''' test add license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['generic_error']),
    ])
    module_args = {
        'use_rest': 'always'
    }
    error = rest_error_message('', 'cluster/licensing/licenses')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_module_add_license_rest():
    ''' test add license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),       # get license information
        ('POST', 'cluster/licensing/licenses', SRR['empty_good']),          # Apply license
        ('GET', 'cluster/licensing/licenses', SRR['license_record_nfs']),   # get updated license information
    ])
    module_args = {
        'license_codes': 'LICENCECODE',
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is True
    assert_no_warnings()


def test_module_error_add_license_rest():
    ''' test add license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),       # get license information
        ('POST', 'cluster/licensing/licenses', SRR['generic_error']),       # Error in adding license
    ])
    module_args = {
        'license_codes': 'INVALIDLICENCECODE',
        'use_rest': 'always'
    }
    error = 'calling: cluster/licensing/licenses: got Expected error.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_module_remove_license():
    ''' test remove license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_nfs']),
        ('DELETE', 'cluster/licensing/licenses/nfs', SRR['empty_good']),        # remove license
    ])
    module_args = {
        'license_names': 'nfs',
        'serial_number': '1-23-45678',
        'state': 'absent',
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is True
    assert_no_warnings()


def test_module_error_remove_license_rest():
    ''' test remove license error'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),                           # get license information
        ('DELETE', 'cluster/licensing/licenses/non-existent-package', SRR['generic_error']),    # Error in removing license
    ])
    module_args = {
        'license_names': 'non-existent-package',
        'serial_number': '1-23-45678',
        'state': 'absent',
        'use_rest': 'always'
    }
    error = 'calling: cluster/licensing/licenses/non-existent-package: got Expected error.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_module_try_to_remove_license_not_present_rest():
    ''' test remove license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),
        ('DELETE', 'cluster/licensing/licenses/non-existent-package', SRR['error_entry_does_not_exist']),   # license not active.
    ])
    module_args = {
        'license_names': 'non-existent-package',
        'serial_number': '1-23-45678',
        'state': 'absent',
        'use_rest': 'always'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert_no_warnings()


@patch('time.sleep')
def test_error_mismatch_in_package_list_rest(dont_sleep):
    ''' test remove license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),
        # 2nd test
        ('GET', 'cluster/licensing/licenses', SRR['license_record_no_nfs']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_no_nfs']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),
        # 3rd test
        ('GET', 'cluster/licensing/licenses', SRR['license_record_no_nfs']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_no_nfs']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_no_nfs']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_no_nfs']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_no_nfs']),
    ])
    module_args = {
        'license_names': 'non-existent-package',
        'serial_number': '1-23-45678',
        'use_rest': 'always'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    previous_license_status = {'base': 'compliant', 'nfs': 'unlicensed', 'cifs': 'compliant'}
    assert my_obj.compare_license_status(previous_license_status) == []
    previous_license_status = {'base': 'compliant', 'nfs': 'unlicensed', 'cifs': 'unlicensed'}
    assert my_obj.compare_license_status(previous_license_status) == ['cifs']
    error = "Error: mismatch in license package names: 'nfs'.  Expected:"
    assert error in expect_and_capture_ansible_exception(my_obj.compare_license_status, 'fail', previous_license_status)['msg']
