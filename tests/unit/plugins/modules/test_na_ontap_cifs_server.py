# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_cifs_server '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible
# from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_server \
    import NetAppOntapcifsServer as my_module  # module under test

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
                    "enabled": True,
                    "target": {
                        "name": "20:05:00:50:56:b3:0c:fa"
                    }
                }
            ],
            "num_records": 1
        }, None
    ),
    'cifs_record_disabled': (
        200,
        {
            "records": [
                {
                    "svm": {
                        "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                        "name": "ansibleSVM"
                    },
                    "enabled": False,
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

    def __init__(self, kind=None, parm1=None, parm2=None):
        ''' save arguments '''
        self.type = kind
        self.parm1 = parm1
        self.parm2 = parm2
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'cifs_server':
            xml = self.build_vserver_info(self.parm1, self.parm2)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_vserver_info(cifs_server, admin_status):
        ''' build xml data for cifs-server-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1,
                'attributes-list': {'cifs-server-config': {'cifs-server': cifs_server,
                                                           'administrative-status': admin_status}}}
        xml.translate_struct(data)
        print(xml.to_string())
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.server = MockONTAPConnection()
        self.use_vsim = False

    def set_default_args(self):
        if self.use_vsim:
            hostname = '10.193.77.154'
            username = 'admin'
            password = 'netapp1!'
            cifs_server = 'test'
            vserver = 'ansible_test'
        else:
            hostname = 'hostname'
            username = 'username'
            password = 'password'
            cifs_server = 'name'
            vserver = 'vserver'
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'cifs_server_name': cifs_server,
            'vserver': vserver,
            'use_rest': 'never',
            'feature_flags': {'no_cserver_ems': True}
        })

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_cifs_server_get_called(self):
        ''' a more interesting test '''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = self.server
        cifs_server = my_obj.get_cifs_server()
        print('Info: test_cifs_server_get: %s' % repr(cifs_server))
        assert cifs_server is None

    def test_ensure_cifs_server_apply_for_create_called(self):
        ''' creating cifs server and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['cifs_server_name'] = 'create'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cifs_server_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cifs_server', 'create', 'up')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cifs_server_apply_for_create: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']

    def test_ensure_cifs_server_apply_for_delete_called(self):
        ''' deleting cifs server and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['cifs_server_name'] = 'delete'
        module_args['admin_password'] = 'pw1'
        module_args['force'] = 'false'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cifs_server', 'delete', 'up')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cifs_server_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        module_args['state'] = 'absent'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cifs_server', 'delete', 'up')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_cifs_server_delete: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_ensure_start_cifs_server_called(self):
        ''' starting cifs server and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['cifs_server_name'] = 'delete'
        module_args['service_state'] = 'started'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cifs_server', 'test', 'up')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_ensure_start_cifs_server: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        module_args['service_state'] = 'stopped'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cifs_server', 'test', 'up')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_ensure_start_cifs_server: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def test_ensure_stop_cifs_server_called(self):
        ''' stopping cifs server and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['cifs_server_name'] = 'delete'
        module_args['service_state'] = 'stopped'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cifs_server', 'test', 'down')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_ensure_stop_cifs_server: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        module_args['service_state'] = 'started'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('cifs_server', 'test', 'down')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_ensure_stop_cifs_server: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']

    def mock_args(self, rest=False):
        if rest:
            return {
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'use_rest': 'always',
                'vserver': 'test_vserver',
                'name': 'cifs_server_name'
            }

    def get_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_cifs_server object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_cifs_server object
        """
        obj = my_module()
        return obj

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_args(rest=True)
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
    def test_rest_successful_create_with_user(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_args(rest=True)
        data['admin_user_name'] = 'test_user'
        data['admin_password'] = 'pwd'
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
    def test_rest_successful_create_with_ou(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_args(rest=True)
        data['ou'] = 'ou'
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
    def test_rest_successful_create_with_domain(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_args(rest=True)
        data['domain'] = 'domain'
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
    def test_rest_successful_disable(self, mock_request):
        '''Test successful rest disable'''
        data = self.mock_args(rest=True)
        data['service_state'] = 'stopped'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            copy.deepcopy(SRR['cifs_record']),
            SRR['empty_good'],

        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_enable(self, mock_request):
        '''Test successful rest enable'''
        data = self.mock_args(rest=True)
        data['service_state'] = 'started'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            copy.deepcopy(SRR['cifs_record_disabled']),
            SRR['empty_good'],

        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_enabled_change(self, mock_request):
        '''Test error rest change'''
        data = self.mock_args(rest=True)
        data['service_state'] = 'stopped'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            copy.deepcopy(SRR['cifs_record']),
            SRR['generic_error'],
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_mock_object().apply()
        assert 'Error on modifying cifs server: calling: ' + \
               'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa: ' + \
               'got Expected error.' in exc.value.args[0]['msg']

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
        assert 'Error on fetching cifs: calling: protocols/cifs/services: got Expected error.' in exc.value.args[0]['msg']

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
        assert 'Error on deleting cifs server: calling: ' + \
               'protocols/cifs/services/671aa46e-11ad-11ec-a267-005056b30cfa: got Expected error.' in exc.value.args[0]['msg']

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
        assert 'Error on creating cifs: calling: protocols/cifs/services: got Expected error.' in exc.value.args[0]['msg']
