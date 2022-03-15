# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_cifs '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs \
    import NetAppONTAPCifsShare as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'cifs_record': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansibleSVM"
                    },
                    "name": 'cifssharename',
                    "path": '/',
                    "comment": 'CIFS share comment',
                    "unix_symlink": 'widelink',
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    }
                }
            ],
            "num_records": 1
        }, None
    ),
    "no_record": (
        200,
        {"num_records": 0},
        None)
}


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'cifs':
            xml = self.build_cifs_info()
        elif self.type == 'cifs_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_cifs_info():
        ''' build xml data for cifs-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1, 'attributes-list': {'cifs-share': {
            'share-name': 'test',
            'path': '/test',
            'vscan-fileop-profile': 'standard',
            'share-properties': [{'cifs-share-properties': 'browsable'},
                                 {'cifs-share-properties': 'oplocks'}],
            'symlink-properties': [{'cifs-share-symlink-properties': 'enable'},
                                   {'cifs-share-symlink-properties': 'read_only'}],
        }}}
        xml.translate_struct(data)
        print(xml.to_string())
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.server = MockONTAPConnection()
        self.onbox = False

    def set_default_args(self):
        if self.onbox:
            share_properties = 'browsable,oplocks'
            vscan_fileop_profile = 'standard'
        else:
            share_properties = 'show_previous_versions'
            vscan_fileop_profile = 'no_scan'
        password = 'netapp1!'
        hostname = '10.193.77.37'
        vserver = 'abc'
        path = '/test'
        username = 'admin'
        symlink_properties = 'disable'
        name = 'test'
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'name': name,
            'path': path,
            'share_properties': share_properties,
            'symlink_properties': symlink_properties,
            'vscan_fileop_profile': vscan_fileop_profile,
            'vserver': vserver,
            'use_rest': 'never'
        })

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_cifs_get_called(self):
        ''' fetching details of cifs '''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = self.server
        cifs_get = my_obj.get_cifs_share()
        print('Info: test_cifs_share_get: %s' % repr(cifs_get))
        assert not bool(cifs_get)

    def test_ensure_apply_for_cifs_called(self):
        ''' creating cifs share and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cifs_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        if not self.onbox:
            my_obj.server = MockONTAPConnection('cifs')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cifs_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs.NetAppONTAPCifsShare.create_cifs_share')
    def test_cifs_create_called(self, create_cifs_share):
        ''' creating cifs'''
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection()
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cifs_apply: %s' % repr(exc.value))
        create_cifs_share.assert_called_with()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs.NetAppONTAPCifsShare.delete_cifs_share')
    def test_cifs_delete_called(self, delete_cifs_share):
        ''' deleting cifs'''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['state'] = 'absent'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('cifs')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cifs_apply: %s' % repr(exc.value))
        delete_cifs_share.assert_called_with()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs.NetAppONTAPCifsShare.modify_cifs_share')
    def test_cifs_modify_called(self, modify_cifs_share):
        ''' modifying cifs'''
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('cifs')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cifs_apply: %s' % repr(exc.value))
        modify_cifs_share.assert_called_with()

    def test_if_all_methods_catch_exception(self):
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('cifs_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_cifs_share()
        assert 'Error creating cifs-share' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.delete_cifs_share()
        assert 'Error deleting cifs-share' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_cifs_share()
        assert 'Error modifying cifs-share' in exc.value.args[0]['msg']

    def mock_args(self, rest=False):
        if rest:
            return {
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'use_rest': 'always',
                'vserver': 'test_vserver',
                'name': 'cifs_share_name'
            }

    def get_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_cifs_server object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_cifs_share object
        """
        return my_module()

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['path'] = "\\"
        data['comment'] = "CIFS comment"
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],
            SRR['empty_good']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_delete(self, mock_request):
        '''Test successful rest delete'''
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            copy.deepcopy(SRR['cifs_record']),  # deepcopy as the code changes the record in place
            SRR['empty_good'],
            SRR['empty_good']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_get(self, mock_request):
        '''Test error rest create'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on fetching cifs shares: calling: protocols/cifs/shares: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_delete(self, mock_request):
        '''Test error rest delete'''
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            copy.deepcopy(SRR['cifs_record']),
            SRR['generic_error']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on deleting cifs shares: calling: ' + \
               'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_create(self, mock_request):
        '''Test error rest create'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],
            SRR['generic_error']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on creating cifs shares: calling: protocols/cifs/shares: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_modify_cifs_share_path(self, mock_request):
        ''' test modify CIFS share path '''
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['path'] = "\\"
        data['symlink_properties'] = "local"
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],                # get version
            copy.deepcopy(SRR['cifs_record']),    # get
            SRR['empty_good'],                 # modify
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_modify_path(self, mock_request):
        ''' negative test for modifying cifs share path'''
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        data['path'] = "\\vol1"
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],                # get version
            copy.deepcopy(SRR['cifs_record']),    # get
            SRR['generic_error'],                 # modify
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on modifying cifs shares: calling: ' + \
               'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/cifssharename: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_modify_cifs_share_comment(self, mock_request):
        ''' test modify CIFS share comment '''
        data = self.mock_args(rest=True)
        data['comment'] = "CIFs share comment"
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],                # get version
            copy.deepcopy(SRR['cifs_record']),    # get
            SRR['empty_good'],                 # modify
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_error_modify_cifs_share_comment(self, mock_request):
        ''' negative test for modifying CIFS share comment '''
        data = self.mock_args(rest=True)
        data['comment'] = "CIFs share negative test"
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],                # get version
            copy.deepcopy(SRR['cifs_record']),    # get
            SRR['generic_error'],                 # modify
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on modifying cifs shares: calling: ' + \
               'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/cifssharename: got Expected error.' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_modify_cifs_share_symlink(self, mock_request):
        ''' test modify CIFS share symlink '''
        data = self.mock_args(rest=True)
        data['symlink_properties'] = "widelink"
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],                # get version
            copy.deepcopy(SRR['cifs_record']),    # get
            SRR['empty_good'],                 # modify
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_error_modify_cifs_share_symlink(self, mock_request):
        ''' negative test for modifying CIFS share symlink '''
        data = self.mock_args(rest=True)
        data['symlink_properties'] = 'test'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],                # get version
            copy.deepcopy(SRR['cifs_record']),    # get
            SRR['generic_error'],                 # modify
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on modifying cifs shares: calling: ' + \
               'protocols/cifs/shares/671aa46e-11ad-11ec-a267-005056b30cfa/cifssharename: got Expected error.' in exc.value.args[0]['msg']
