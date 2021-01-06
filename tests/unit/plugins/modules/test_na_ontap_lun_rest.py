# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_lun \
    import NetAppOntapLUN as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


def exit_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'get_apps_empty': (200,
                       {'records': [],
                        'num_records': 0
                        },
                       None
                       ),
    'get_apps_found': (200,
                       {'records': [dict(name='san_appli', uuid='1234')],
                        'num_records': 1
                        },
                       None
                       ),
    'get_app_components': (200,
                           {'records': [dict(name='san_appli', uuid='1234')],
                            'num_records': 1
                            },
                           None
                           ),
    'get_app_details': (200,
                        dict(name='san_appli', uuid='1234', san=dict(
                            application_components=[dict(name='lun_name', lun_count=3, total_size=1000)]
                        )),
                        None
                        ),
    'get_app_component_details': (200,
                                  {'backing_storage': dict(luns=[]),
                                   },
                                  None
                                  ),
}


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None, parm1=None):
        ''' save arguments '''
        self.type = kind
        self.parm1 = parm1
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'lun':
            xml = self.build_lun_info(self.parm1)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_lun_info(lun_name):
        ''' build xml data for lun-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        lun = dict(
            lun_info=dict(
                path="/what/ever/%s" % lun_name,
                size=10
            )
        )
        attributes = {
            'num-records': 1,
            'attributes-list': [lun]
        }
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_lun_args = {
            'vserver': 'ansible',
            'name': 'lun_name',
            'flexvol_name': 'vol_name',
            'state': 'present'
        }

    def mock_args(self):
        return {
            'vserver': self.mock_lun_args['vserver'],
            'name': self.mock_lun_args['name'],
            'flexvol_name': self.mock_lun_args['flexvol_name'],
            'state': self.mock_lun_args['state'],
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
        }
        # self.server = MockONTAPConnection()

    def get_lun_mock_object(self, kind=None, parm1=None):
        """
        Helper method to return an na_ontap_lun object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_interface object
        """
        lun_obj = my_module()
        lun_obj.autosupport_log = Mock(return_value=None)
        lun_obj.server = MockONTAPConnection(kind=kind, parm1=parm1)
        return lun_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_create_error_missing_param(self):
        ''' Test if create throws an error if required param 'destination_vserver' is not specified'''
        data = self.mock_args()
        set_module_args(data)
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli')
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_mock_object().apply()
        msg = 'size is a required parameter for create.'
        assert msg == exc.value.args[0]['msg']

    def test_create_error_missing_param2(self):
        ''' Test if create throws an error if required param 'destination_vserver' is not specified'''
        data = self.mock_args()
        data.pop('flexvol_name')
        data['size'] = 5
        data['san_application_template'] = dict(lun_count=6)
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_mock_object().apply()
        msg = 'missing required arguments: name found in san_application_template'
        assert msg == exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_create_appli(self, mock_request):
        ''' Test successful create '''
        mock_request.side_effect = [
            SRR['get_apps_empty'],      # GET application/applications
            SRR['empty_good'],          # POST application/applications
            SRR['end_of_sequence']
        ]
        data = dict(self.mock_args())
        data['size'] = 5
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli')
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_create_appli_idem(self, mock_request):
        ''' Test successful create idempotent '''
        mock_request.side_effect = copy.deepcopy([
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data['size'] = 5
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli')
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object().apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_create_appli_idem_no_comp(self, mock_request):
        ''' Test successful create idempotent '''
        mock_request.side_effect = copy.deepcopy([
            SRR['get_apps_found'],      # GET application/applications
            SRR['get_app_details'],     # GET application/applications/<uuid>
            SRR['get_apps_empty'],      # GET application/applications/<uuid>/components
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data['size'] = 5
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli')
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_mock_object().apply()
        # print(mock_request.call_args_list)
        msg = 'Error: no component for application san_appli'
        assert msg == exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_delete_appli(self, mock_request):
        ''' Test successful create '''
        mock_request.side_effect = [
            SRR['get_apps_found'],      # GET application/applications
            SRR['empty_good'],          # POST application/applications
            SRR['end_of_sequence']
        ]
        data = dict(self.mock_args())
        data['size'] = 5
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli')
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_delete_appli_idem(self, mock_request):
        ''' Test successful delete idempotent '''
        mock_request.side_effect = [
            SRR['get_apps_empty'],      # GET application/applications
            SRR['end_of_sequence']
        ]
        data = dict(self.mock_args())
        data['size'] = 5
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli')
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object().apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_appli(self, mock_request):
        ''' Test successful modify application '''
        mock_request.side_effect = copy.deepcopy([
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            # SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            # SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['empty_good'],                      # PATCH application/applications/<uuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data['os_type'] = 'xyz'
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli', lun_count=5, total_size=1000, igroup_name='abc')
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object().apply()
        print(exc.value.args[0])
        # print(mock_request.call_args_list)
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_error_modify_appli_missing_igroup(self, mock_request):
        ''' Test successful modify application '''
        mock_request.side_effect = copy.deepcopy([
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            # SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            # SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data['size'] = 5
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli', lun_count=5)
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_mock_object().apply()
        msg = 'Error: igroup_name is a required parameter when increasing lun_count.'
        assert msg in exc.value.args[0]['msg']
        msg = 'Error: total_size is a required parameter when increasing lun_count.'
        assert msg in exc.value.args[0]['msg']
        msg = 'Error: os_type is a required parameter when increasing lun_count.'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_no_action(self, mock_request):
        ''' Test successful modify application '''
        mock_request.side_effect = copy.deepcopy([
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data['name'] = 'unknown'
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli', lun_count=5)
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object().apply()
        print(exc.value.args[0])
        assert not exc.value.args[0]['changed']
