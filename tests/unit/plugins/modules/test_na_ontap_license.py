# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP license Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import sys
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_license \
    import NetAppOntapLicense as my_module      # module under test


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None, data=None):
        ''' save arguments '''
        self.type = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'generic-error':
            raise netapp_utils.zapi.NaApiError(code='15000', message="generic error")
        if self.type == 'entry-not-exist':
            raise netapp_utils.zapi.NaApiError(code='15661', message="License missing")
        self.xml_out = xml
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.server = MockONTAPConnection()

    def mock_args(self):
        return {
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!',
            'use_rest': 'never',
            'state': 'present',
            'feature_flags': {'no_cserver_ems': True}
        }

    def get_license_mock_object(self, kind=None, data=None):
        """
        Helper method to return an na_ontap_license object
        :param kind: passes this param to MockONTAPConnection()
        :param data: passes this param to MockONTAPConnection()
        :return: na_ontap_license object
        """
        license_obj = my_module()
        license_obj.asup_log_for_cserver = Mock(return_value=None)
        license_obj.cluster = Mock()
        license_obj.cluster.invoke_successfully = Mock()
        license_obj.server = MockONTAPConnection(kind=kind)
        return license_obj

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.NetAppOntapLicense.get_licensing_status')
    def test_module_add_license_zapi(self, get_licensing_status):
        ''' Test add license '''
        data = self.mock_args()
        data['license_codes'] = 'LICENSECODE'
        set_module_args(data)
        current = {
            'base': 'site',
            'capacitypool': 'none',
            'cifs': 'site',
            'fcp': 'none'
        }
        updated_current = {
            'base': 'site',
            'capacitypool': 'none',
            'cifs': 'site',
            'fcp': 'site'
        }
        get_licensing_status.side_effect = [
            current,
            updated_current
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_license_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.NetAppOntapLicense.get_licensing_status')
    def test_module_add_license_idempotent_zapi(self, get_licensing_status):
        ''' Test add license idempotent '''
        data = self.mock_args()
        data['license_codes'] = 'LICENSECODE'
        set_module_args(data)
        current = {
            'base': 'site',
            'capacitypool': 'none',
            'cifs': 'site',
            'fcp': 'none'
        }
        updated_current = {
            'base': 'site',
            'capacitypool': 'none',
            'cifs': 'site',
            'fcp': 'none'
        }
        get_licensing_status.side_effect = [
            current,
            updated_current
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_license_mock_object().apply()
        assert exc.value.args[0]['changed'] is False

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.NetAppOntapLicense.remove_licenses')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.NetAppOntapLicense.get_licensing_status')
    def test_module_remove_license_zapi(self, get_licensing_status, remove_licenses):
        ''' Test remove license '''
        data = self.mock_args()
        data['serial_number'] = '1-8-000000'
        data['license_names'] = 'cifs,fcp'
        data['state'] = 'absent'
        set_module_args(data)
        current = {
            'base': 'site',
            'capacitypool': 'none',
            'cifs': 'site',
            'fcp': 'site'
        }
        get_licensing_status.side_effect = [current]
        remove_licenses.side_effect = [True, True]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_license_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.NetAppOntapLicense.remove_licenses')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.NetAppOntapLicense.get_licensing_status')
    def test_module_remove_license_idempotent_zapi(self, get_licensing_status, remove_licenses):
        ''' Test remove license idempotent '''
        data = self.mock_args()
        data['serial_number'] = '1-8-000000'
        data['license_names'] = 'cifs,fcp'
        data['state'] = 'absent'
        set_module_args(data)
        current = {
            'base': 'site',
            'capacitypool': 'none',
            'cifs': 'none',
            'fcp': 'none'
        }
        get_licensing_status.side_effect = [current]
        remove_licenses.side_effect = [False, False]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_license_mock_object().apply()
        assert exc.value.args[0]['changed'] is False

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_license.NetAppOntapLicense.get_licensing_status')
    def test_module_remove_unused_expired_zapi(self, get_licensing_status):
        ''' Test remove unused expired license '''
        data = self.mock_args()
        data['remove_unused'] = True
        data['remove_expired'] = True
        set_module_args(data)
        current = {
            'base': 'site',
            'capacitypool': 'none',
            'cifs': 'site',
            'fcp': 'site'
        }
        updated_current = {
            'base': 'site',
            'capacitypool': 'none',
            'cifs': 'none',
            'fcp': 'none'
        }
        get_licensing_status.side_effect = [current, updated_current]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_license_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_module_try_to_remove_non_existent_package_license_zapi(self):
        ''' Try to remove non existent license '''
        data = self.mock_args()
        data['serial_number'] = '1-8-000000'
        data['license_names'] = 'cifs'
        data['state'] = 'absent'
        set_module_args(data)
        license_exist = self.get_license_mock_object("entry-not-exist").remove_licenses('cifs')
        assert license_exist is False

    def test_module_error_add_license_zapi(self):
        ''' Test error add license '''
        data = self.mock_args()
        data['license_codes'] = 'random'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_license_mock_object("generic-error").add_licenses()
        print('Info: %s' % exc.value.args[0]['msg'])
        assert 'Error adding licenses' in exc.value.args[0]['msg']

    def test_module_error_remove_license_zapi(self):
        ''' Test error remove license '''
        data = self.mock_args()
        data['serial_number'] = '1-8-000000'
        data['license_names'] = 'random'
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_license_mock_object("generic-error").remove_licenses(data['license_names'])
        print('Info: %s' % exc.value.args[0]['msg'])
        assert 'Error removing license' in exc.value.args[0]['msg']

    def test_module_error_get_and_remove_unused_expired_license_zapi(self):
        ''' Test error get and remove unused/expired license '''
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_license_mock_object("generic-error").get_licensing_status()
        assert 'Error checking license status' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_license_mock_object("generic-error").remove_unused_licenses()
        assert 'Error removing unused licenses' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_license_mock_object("generic-error").remove_expired_licenses()
        assert 'Error removing expired licenses' in exc.value.args[0]['msg']


WARNINGS = list()


def warn(dummy, msg):
    WARNINGS.append(msg)


def default_args():
    args = {
        'state': 'present',
        'hostname': '10.10.10.10',
        'username': 'admin',
        'https': 'true',
        'validate_certs': 'false',
        'password': 'password',
        'use_rest': 'always'
    }
    return args


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_6': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy')), None),
    'is_rest_9_7': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (404, None, "entry doesn't exist"),
    'expected_error': (400, None, "Expected error"),
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
    }, None)
}


def test_module_fail_when_unsupported_rest_present(patch_ansible):
    ''' error if unsupported rest properties present '''
    args = dict(default_args())
    args['remove_unused'] = True
    args['remove_expired'] = True
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj = my_module()
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = 'REST API currently does not support'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_ensure_get_license_status_called_rest(mock_request, patch_ansible):
    ''' test get'''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],         # get version
        SRR['license_record'],         # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_get_license_rest(mock_request, patch_ansible):
    ''' test add license'''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],             # get versioN
        SRR['expected_error'],          # Error in getting license
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'calling: cluster/licensing/licenses: got Expected error.'
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_add_license_rest(mock_request, patch_ansible):
    ''' test add license'''
    args = dict(default_args())
    args['license_codes'] = "LICENCECODE"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],             # get version
        SRR['license_record'],          # get license information
        SRR['empty_good'],              # Apply license
        SRR['license_record_nfs'],      # get updated license information
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_add_license_rest(mock_request, patch_ansible):
    ''' test add license'''
    args = dict(default_args())
    args['license_codes'] = "INVALIDLICENCECODE"
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],             # get version
        SRR['license_record'],          # get license information
        SRR['expected_error'],          # Error in adding license
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'calling: cluster/licensing/licenses: got Expected error.'
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_remove_license(mock_request, patch_ansible):
    ''' test remove license'''
    args = dict(default_args())
    args['license_names'] = 'nfs'
    args['serial_number'] = '1-23-45678'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],           # get version
        SRR['license_record_nfs'],    # get
        SRR['empty_good'],            # remove license
        SRR['license_record'],        # get updated license.
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is True
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_error_remove_license_rest(mock_request, patch_ansible):
    ''' test remove license error'''
    args = dict(default_args())
    args['license_names'] = 'non-existent-package'
    args['serial_number'] = '1-23-45678'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],             # get version
        SRR['license_record'],          # get license information
        SRR['expected_error'],          # Error in removing license
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    msg = 'calling: cluster/licensing/licenses/non-existent-package: got Expected error.'
    assert msg in exc.value.args[0]['msg']
    assert not WARNINGS


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_module_try_to_remove_license_not_present_rest(mock_request, patch_ansible):
    ''' test remove license'''
    args = dict(default_args())
    args['license_names'] = 'nfs'
    args['serial_number'] = '1-23-45678'
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest_9_8'],           # get version
        SRR['license_record'],        # get
        SRR['generic_error'],         # license not exist, so error returns.
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Info: %s' % exc.value.args[0])
    assert exc.value.args[0]['changed'] is False
    assert not WARNINGS
