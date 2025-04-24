# (c) 2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP license Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import sys
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_no_warnings, assert_warning_was_raised, call_main, create_module, expect_and_capture_ansible_exception, patch_ansible, print_warnings
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_error_message, rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_license import NetAppOntapLicense as my_module, main as my_main, HAS_DEEPDIFF


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
}

NLF = """
{"statusResp":{"statusCode":"SUCCESS","message":"Information sent successfully","filter":"SOA","serialNumber":"12345678","cmatID":"0000000",
"product":"%s","version":"2","licenses":{"legacyKey":"Generate NetApp License File (NLF)","HostID":"12345678","type":"capacity",
"package":["CIFS","NFS","S3","FCP","iSCSI","NVMe_oF","FlexClone","SnapRestore","SnapMirror","SnapMirror_Sync","SnapManagerSuite","SnapVault","S3_SnapMirror","VE","TPM"],
"capacity":"1","evaluation":"false","entitlementLastUpdated":"2023-01-04T07:58:16.000-07:00","licenseScope":"node","licenseProtocol":"ENT_ENCRYPT_ED_CAP_3",
"enforcementAttributes":[{"name":"DO-Capacity-Warn","metric":"5:1",
"msg":"You've exceeded your capacity limit. Add capacity to your license to ensure your product use is unaffected.","operatingPolicy":"na"},
{"name":"DO-Capacity-Enforce","metric":"6:1",
"msg":"You've exceeded your capacity limit. Add capacity to your license to ensure your product use is unaffected.","operatingPolicy":"ndo"}]}},
"Signature":"xxxx"}
""".replace('\n', '')

NLF_EE = NLF % "Enterprise Edition"
NLF_CB = NLF % "Core Bundle"

NLF_MULTIPLE = "%s\n%s" % (NLF_EE, NLF_CB)

NLF_DICT_NO_PRODUCT = {"statusResp": {"serialNumber": "12345678"}}
NLF_DICT_NO_SERIAL = {"statusResp": {"product": "Enterprise Edition"}}
NLF_DICT_PRODUCT_SN = {"statusResp": {"product": "Enterprise Edition", "serialNumber": "12345678"}}
NLF_DICT_PRODUCT_SN_STAR = {"statusResp": {"product": "Enterprise Edition", "serialNumber": "*"}}


def test_module_error_zapi_not_supported():
    ''' Test add license '''
    register_responses([
    ])
    module_args = {
        'use_rest': 'never',
        'license_codes': [NLF_EE],
    }
    error = 'Error: NLF license format is not supported with ZAPI.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    module_args = {
        'use_rest': 'never',
        'license_codes': [NLF_EE],
        'state': 'absent'
    }
    error = 'Error: NLF license format is not supported with ZAPI.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


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
                "state": "compliant",
                "licenses": [
                    {
                        "installed_license": "Enterprise Edition",
                        "serial_number": "12345678",
                        "maximum_size": 1099511627776
                    }

                ]
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
    }, None),
    'conflict_error': (409, None, 'license with conflicts error message'),
    'failed_to_install_error': (400, None,
                                'Failed to install the license at index 0.  The system received a licensing request with an invalid digital signature.'),
}, False)


def test_module_add_nlf_license_rest():
    ''' test add license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_1']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),       # get license information
        ('POST', 'cluster/licensing/licenses', SRR['empty_good']),          # Apply license
        ('GET', 'cluster/licensing/licenses', SRR['license_record_nfs']),   # get updated license information
    ])
    module_args = {
        'license_codes': [NLF_EE],
        'use_rest': 'always'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is True
    if HAS_DEEPDIFF:
        assert_no_warnings()


def test_module_error_add_nlf_license_rest():
    ''' test add license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),
        ('POST', 'cluster/licensing/licenses', SRR['conflict_error']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_nfs']),   # get updated license information
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),
        ('POST', 'cluster/licensing/licenses', SRR['failed_to_install_error']),
    ])
    module_args = {
        'license_codes': [NLF_EE],
        'use_rest': 'always'
    }
    error = rest_error_message('Error: some licenses were updated, but others were in conflict', 'cluster/licensing/licenses',
                               got='got license with conflicts error message')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    if HAS_DEEPDIFF:
        assert_no_warnings()
    error = rest_error_message('Error adding license', 'cluster/licensing/licenses',
                               got='got Failed to install the license at index 0')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    if HAS_DEEPDIFF:
        assert_no_warnings()


def test_module_remove_nlf_license():
    ''' test remove license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_nfs']),
        ('DELETE', 'cluster/licensing/licenses', SRR['empty_good']),
    ])
    module_args = {
        'license_codes': [NLF_EE],
        'state': 'absent',
        'use_rest': 'always'
    }
    print_warnings()
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is True
    assert_no_warnings()


def test_module_remove_nlf_license_by_name():
    ''' test remove license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_nfs']),
        ('DELETE', 'cluster/licensing/licenses', SRR['empty_good']),
    ])
    module_args = {
        'license_names': "Enterprise Edition",
        'state': 'absent',
        'use_rest': 'always',
        'serial_number': '12345678'
    }
    print_warnings()
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed'] is True
    assert_no_warnings()


def test_module_error_remove_nlf_license_rest():
    ''' test remove license error'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_nfs']),
        ('DELETE', 'cluster/licensing/licenses', SRR['generic_error']),
    ])
    module_args = {
        'license_codes': [NLF_EE],
        'state': 'absent',
        'use_rest': 'always'
    }
    error = rest_error_message('Error removing license for serial number 12345678 and Enterprise Edition', 'cluster/licensing/licenses')
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    assert_no_warnings()


def test_module_try_to_remove_nlf_license_not_present_rest():
    ''' test remove license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_nfs']),
    ])
    module_args = {
        'license_codes': [NLF_CB],
        'state': 'absent',
        'use_rest': 'always'
    }
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert not call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    assert_no_warnings()


@patch('time.sleep')
def test_compare_license_status(dont_sleep):
    ''' test remove license'''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),
        # 2nd test
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),
        # deepdiff 1
        ('GET', 'cluster/licensing/licenses', SRR['license_record_nfs']),
        # deepdiff 2
        ('GET', 'cluster/licensing/licenses', SRR['license_record_nfs']),
        # retries
        ('GET', 'cluster/licensing/licenses', SRR['license_record_no_nfs']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record_no_nfs']),
        ('GET', 'cluster/licensing/licenses', SRR['license_record']),
        # Error, no records
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
    previous_license_status = {'base': 'compliant', 'nfs': 'compliant', 'cifs': 'compliant'}
    assert my_obj.compare_license_status(previous_license_status) == ['nfs']
    previous_license_status = {'base': 'compliant', 'nfs': 'unlicensed', 'cifs': 'compliant'}
    # deepdiffs
    my_obj.previous_records = [{'name': 'base', 'scope': 'cluster', 'state': 'compliant'}]
    assert my_obj.compare_license_status(previous_license_status) == (['nfs', 'cifs'] if HAS_DEEPDIFF else ['nfs'])
    if HAS_DEEPDIFF:
        assert_no_warnings()
    with patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.HAS_DEEPDIFF', False):
        assert my_obj.compare_license_status(previous_license_status) == ['nfs']
        print_warnings()
        assert_warning_was_raised('deepdiff is required to identify detailed changes')
    # retries, success
    previous_license_status = {'base': 'compliant', 'nfs': 'unlicensed', 'cifs': 'unlicensed'}
    assert my_obj.compare_license_status(previous_license_status) == (['cifs', 'nfs'] if HAS_DEEPDIFF else ['cifs'])
    # retries, error
    error = "Error: mismatch in license package names: 'nfs'.  Expected:"
    assert error in expect_and_capture_ansible_exception(my_obj.compare_license_status, 'fail', previous_license_status)['msg']


def test_format_post_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'use_rest': 'always',
        'state': 'absent',
        'license_codes': []
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.format_post_error('some_error', {}) == 'some_error'
    rest_error = 'The system received a licensing request with an invalid digital signature.'
    error = my_obj.format_post_error(rest_error, {})
    assert error == rest_error
    rest_error += '  Failed to install the license at index 0'
    error = my_obj.format_post_error(rest_error, {'keys': ["'statusResp'"]})
    assert 'Original NLF contents were modified by Ansible.' in error
    error = my_obj.format_post_error(rest_error, {'keys': ["'whatever'"]})
    assert 'Original NLF contents were modified by Ansible.' not in error


def test_nlf_is_installed():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'use_rest': 'always',
        'state': 'absent',
        'license_codes': []
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert not my_obj.nlf_is_installed(NLF_DICT_NO_PRODUCT)
    assert not my_obj.nlf_is_installed(NLF_DICT_NO_SERIAL)
    my_obj.license_status = {}
    assert not my_obj.nlf_is_installed(NLF_DICT_PRODUCT_SN)
    my_obj.license_status['installed_licenses'] = []
    assert my_obj.nlf_is_installed(NLF_DICT_PRODUCT_SN_STAR)


def test_validate_delete_action():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'use_rest': 'always'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = 'Error: product not found in NLF file'
    assert error in expect_and_capture_ansible_exception(my_obj.validate_delete_action, 'fail', NLF_DICT_NO_PRODUCT)['msg']
    error = 'Error: serialNumber not found in NLF file'
    assert error in expect_and_capture_ansible_exception(my_obj.validate_delete_action, 'fail', NLF_DICT_NO_SERIAL)['msg']
    my_obj.parameters['serial_number'] = 'otherSN'
    error = 'Error: mismatch is serial numbers otherSN vs 12345678'
    assert error in expect_and_capture_ansible_exception(my_obj.validate_delete_action, 'fail', NLF_DICT_PRODUCT_SN)['msg']


def test_scan_license_codes_for_nlf():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'use_rest': 'always'
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    nlf = NLF_EE.replace("'", "\\'")
    nlf = nlf.replace('"', "'")
    license_code, nlf_dict, is_nlf = my_obj.scan_license_codes_for_nlf(nlf)
    assert len(nlf_dict) == 2
    assert len(nlf_dict['statusResp']) == 8

    with patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.HAS_AST', False):
        error = 'Error: ast and json packages are required to install NLF license files.'
        assert error in expect_and_capture_ansible_exception(my_obj.scan_license_codes_for_nlf, 'fail', nlf)['msg']

    with patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.HAS_JSON', False):
        error = 'Error: ast and json packages are required to install NLF license files.'
        assert error in expect_and_capture_ansible_exception(my_obj.scan_license_codes_for_nlf, 'fail', nlf)['msg']

    with patch('json.dumps') as json_dumps:
        json_dumps.side_effect = Exception('exception for test')
        error = 'Error: unable to encode input:'
        assert error in expect_and_capture_ansible_exception(my_obj.scan_license_codes_for_nlf, 'fail', nlf)['msg']

    with patch('json.loads') as json_loads:
        json_loads.side_effect = Exception('exception for test')
        error = 'Error: the license contents cannot be read.  Unable to decode input:'
        assert error in expect_and_capture_ansible_exception(my_obj.scan_license_codes_for_nlf, 'fail', nlf)['msg']

    nlf = "'statusResp':"
    # older versions of python report unexpected EOF while parsing
    # but python 3.10.2 reports exception: invalid syntax (<unknown>, line 1)
    error = "Error: malformed input: 'statusResp':, exception:"
    assert error in expect_and_capture_ansible_exception(my_obj.scan_license_codes_for_nlf, 'fail', nlf)['msg']

    nlf = '"statusResp":' * 2
    error = "Error: NLF license files with multiple licenses are not supported, found 2 in"
    assert error in expect_and_capture_ansible_exception(my_obj.scan_license_codes_for_nlf, 'fail', nlf)['msg']
    nlf = '"statusResp":' + ('"serialNumber":' * 2)
    error = "Error: NLF license files with multiple serial numbers are not supported, found 2 in"
    assert error in expect_and_capture_ansible_exception(my_obj.scan_license_codes_for_nlf, 'fail', nlf)['msg']
    nlf = '"statusResp":'
    my_obj.scan_license_codes_for_nlf(nlf)
    print_warnings()
    assert_warning_was_raised('The license will be installed without checking for idempotency.', partial_match=True)
    assert_warning_was_raised('Unable to decode input', partial_match=True)
    with patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.HAS_JSON', False):
        my_obj.scan_license_codes_for_nlf(nlf)
        print_warnings()
        assert_warning_was_raised('The license will be installed without checking for idempotency.', partial_match=True)
        assert_warning_was_raised('the json package is required to process NLF license files', partial_match=True)


def test_error_nlf_and_legacy():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'use_rest': 'always',
        'license_codes': [NLF, 'xxxxxxxxxxxxxxxx']
    }
    error = 'Error: cannot mix legacy licenses and NLF licenses; found 1 NLF licenses out of 2 license_codes.'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_split_nlfs():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'use_rest': 'always',
        'license_codes': [NLF_MULTIPLE]
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert len(my_obj.parameters['license_codes']) == 2
    # force error:
    error = 'Error: unexpected format found 2 entries and 3 lines'
    assert error in expect_and_capture_ansible_exception(my_obj.split_nlf, 'fail', '%s\nyyyyy' % NLF_MULTIPLE)['msg']


def test_remove_licenses_rest():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
    ])
    module_args = {
        'use_rest': 'always',
        'license_codes': [NLF_MULTIPLE]
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    error = 'Error: serial_number is required to delete a license.'
    assert error in expect_and_capture_ansible_exception(my_obj.remove_licenses_rest, 'fail', 'bundle name', {})['msg']
