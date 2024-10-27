# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock, call
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible, assert_warning_was_raised, print_warnings
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_lun \
    import NetAppOntapLUN as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest_96': (200, dict(version=dict(generation=9, major=6, minor=0, full='dummy')), None),
    'is_rest_97': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy')), None),
    'is_rest_98': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {'records': []}, None),
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
                        dict(name='san_appli', uuid='1234',
                             san=dict(application_components=[dict(name='lun_name', lun_count=3, total_size=1000)]),
                             statistics=dict(space=dict(provisioned=1100))
                             ),
                        None
                        ),
    'get_app_component_details': (200,
                                  {'backing_storage': dict(luns=[]),
                                   },
                                  None
                                  ),
    'get_volumes_found': (200,
                          {'records': [dict(name='san_appli', uuid='1234')],
                           'num_records': 1
                           },
                          None
                          ),
    'get_lun_path': (200,
                     {'records': [{'uuid': '1234', 'path': '/vol/lun_name/lun_name'}],
                      'num_records': 1
                      },
                     None
                     ),
    'one_lun': (200,
                {'records': [{
                 'uuid': "1234",
                 'name': '/vol/lun_name/lun_name',
                 'path': '/vol/lun_name/lun_name',
                 'size': 9871360,
                 'comment': None,
                 'flexvol_name': None,
                 'os_type': 'xyz',
                 'qos_policy_group': None,
                 'space_reserve': False,
                 'space_allocation': False
                 }],
                 }, None),
    'get_storage': (200,
                    {'backing_storage': dict(luns=[{'path': '/vol/lun_name/lun_name',
                                                    'uuid': '1234',
                                                    'size': 15728640,
                                                    'creation_timestamp': '2022-07-26T20:35:50+00:00'
                                                    }]),
                     }, None),

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
            SRR['is_rest_98'],
            SRR['get_apps_empty'],      # GET application/applications
            SRR['get_apps_empty'],      # GET volumes
            SRR['empty_good'],          # POST application/applications
            SRR['end_of_sequence']
        ]
        data = dict(self.mock_args())
        data['size'] = 5
        data.pop('flexvol_name')
        tiering = dict(control='required')
        data['san_application_template'] = dict(name='san_appli', tiering=tiering)
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object().apply()
        assert exc.value.args[0]['changed']
        expected_json = {'name': 'san_appli', 'svm': {'name': 'ansible'}, 'smart_container': True,
                         'san': {'application_components':
                                 [{'name': 'lun_name', 'lun_count': 1, 'total_size': 5368709120, 'tiering': {'control': 'required'}}]}}
        expected_call = call(
            'POST', 'application/applications', {'return_timeout': 30, 'return_records': 'true'}, json=expected_json, headers=None, files=None)
        assert expected_call in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_create_appli_idem(self, mock_request):
        ''' Test successful create idempotent '''
        mock_request.side_effect = copy.deepcopy([
            SRR['is_rest_98'],
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
            SRR['is_rest_98'],
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
            SRR['is_rest_98'],
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
            SRR['is_rest_98'],
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
            SRR['is_rest_98'],
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['empty_good'],
            SRR['get_lun_path'],
            SRR['get_storage'],
            SRR['one_lun'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data['os_type'] = 'xyz'
        data['space_reserve'] = True
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
            SRR['is_rest_98'],
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
            SRR['is_rest_98'],
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

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_no_96(self, mock_request):
        ''' Test SAN application not supported on 9.6 '''
        mock_request.side_effect = copy.deepcopy([
            SRR['is_rest_96'],
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data['name'] = 'unknown'
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli', lun_count=5)
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_mock_object().apply()
        print(exc.value.args[0]['msg'])
        msg = 'Error: using san_application_template requires ONTAP 9.7 or later and REST must be enabled.'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_no_modify_on97(self, mock_request):
        ''' Test modify SAN application not supported on 9.7 '''
        mock_request.side_effect = copy.deepcopy([
            SRR['is_rest_97'],
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data.pop('flexvol_name')
        data['os_type'] = 'xyz'
        data['san_application_template'] = dict(name='san_appli', lun_count=5, total_size=1000, igroup_name='abc')
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_mock_object().apply()
        print(exc.value.args[0])
        msg = 'Error: modifying lun_count, total_size is not supported on ONTAP 9.7'
        # in python 2.6, keys() is not sorted!
        msg2 = 'Error: modifying total_size, lun_count is not supported on ONTAP 9.7'
        assert msg in exc.value.args[0]['msg'] or msg2 in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_no_modify_on97_2(self, mock_request):
        ''' Test modify SAN application not supported on 9.7 '''
        mock_request.side_effect = copy.deepcopy([
            SRR['is_rest_97'],
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli', total_size=1000)
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_mock_object().apply()
        print(exc.value.args[0])
        msg = 'Error: modifying total_size is not supported on ONTAP 9.7'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_app_changes_reduction_not_allowed(self, mock_request):
        ''' Test modify SAN application - can't decrease size '''
        mock_request.side_effect = copy.deepcopy([
            SRR['is_rest_98'],
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            # SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            # SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli', total_size=899, total_size_unit='b')
        set_module_args(data)
        lun_object = self.get_lun_mock_object()
        with pytest.raises(AnsibleFailJson) as exc:
            lun_object.app_changes('scope')
        msg = "Error: can't reduce size: total_size=1000, provisioned=1100, requested=899"
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_app_changes_reduction_small_enough_10(self, mock_request):
        ''' Test modify SAN application - a 10% reduction is ignored '''
        mock_request.side_effect = copy.deepcopy([
            SRR['is_rest_98'],
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            # SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            # SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli', total_size=900, total_size_unit='b')
        set_module_args(data)
        lun_object = self.get_lun_mock_object()
        results = lun_object.app_changes('scope')
        print(results)
        print(lun_object.debug)
        msg = "Ignoring small reduction (10.0 %) in total size: total_size=1000, provisioned=1100, requested=900"
        assert_warning_was_raised(msg)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_app_changes_reduction_small_enough_17(self, mock_request):
        ''' Test modify SAN application - a 1.7% reduction is ignored '''
        mock_request.side_effect = copy.deepcopy([
            SRR['is_rest_98'],
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            # SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            # SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli', total_size=983, total_size_unit='b')
        set_module_args(data)
        lun_object = self.get_lun_mock_object()
        results = lun_object.app_changes('scope')
        print(results)
        print(lun_object.debug)
        print_warnings()
        msg = "Ignoring small reduction (1.7 %) in total size: total_size=1000, provisioned=1100, requested=983"
        assert_warning_was_raised(msg)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_app_changes_increase_small_enough(self, mock_request):
        ''' Test modify SAN application - a 1.7% reduction is ignored '''
        mock_request.side_effect = copy.deepcopy([
            SRR['is_rest_98'],
            SRR['get_apps_found'],                  # GET application/applications
            SRR['get_app_details'],                 # GET application/applications/<uuid>
            # SRR['get_apps_found'],                  # GET application/applications/<uuid>/components
            # SRR['get_app_component_details'],       # GET application/applications/<uuid>/components/<cuuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data.pop('flexvol_name')
        data['san_application_template'] = dict(name='san_appli', total_size=1050, total_size_unit='b')
        set_module_args(data)
        lun_object = self.get_lun_mock_object()
        results = lun_object.app_changes('scope')
        print(results)
        print(lun_object.debug)
        msg = "Ignoring increase: requested size is too small: total_size=1000, provisioned=1100, requested=1050"
        assert_warning_was_raised(msg)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_convert_to_appli(self, mock_request):
        ''' Test successful convert to application
            Appli does not exist, but the volume does.
        '''
        mock_request.side_effect = copy.deepcopy([
            SRR['is_rest_98'],
            SRR['get_apps_empty'],      # GET application/applications
            SRR['get_volumes_found'],   # GET volumes
            SRR['empty_good'],          # POST application/applications
            SRR['get_apps_found'],      # GET application/applications
            SRR['get_app_details'],     # GET application/applications/<uuid>
            SRR['end_of_sequence']
        ])
        data = dict(self.mock_args())
        data['size'] = 5
        data.pop('flexvol_name')
        tiering = dict(control='required')
        data['san_application_template'] = dict(name='san_appli', tiering=tiering, scope='application')
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object().apply()
        # assert exc.value.args[0]['changed']
        print(mock_request.mock_calls)
        print(exc.value.args[0])
        expected_json = {'name': 'san_appli', 'svm': {'name': 'ansible'}, 'smart_container': True,
                         'san': {'application_components':
                                 [{'name': 'lun_name'}]}}
        expected_call = call(
            'POST', 'application/applications', {'return_timeout': 30, 'return_records': 'true'}, json=expected_json, headers=None, files=None)
        assert expected_call in mock_request.mock_calls

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_convert_to_appli(self, mock_request):
        ''' Test successful convert to application
            Appli does not exist, but the volume does.
        '''
        mock_request.side_effect = [
            SRR['is_rest_97'],
            SRR['get_apps_empty'],      # GET application/applications
            SRR['get_volumes_found'],   # GET volumes
            SRR['end_of_sequence']
        ]
        data = dict(self.mock_args())
        data['size'] = 5
        data.pop('flexvol_name')
        tiering = dict(control='required')
        data['san_application_template'] = dict(name='san_appli', tiering=tiering, scope='application')
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_mock_object().apply()
        msg = "Error: converting a LUN volume to a SAN application container requires ONTAP 9.8 or better."
        assert msg in exc.value.args[0]['msg']
