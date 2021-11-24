# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_routes \
    import NetAppOntapNetRoutes as net_route_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'net_routes_record': (200,
                          {'records': [{"destination": {"address": "176.0.0.0",
                                                        "netmask": "24",
                                                        "family": "ipv4"},
                                        "gateway": '10.193.72.1',
                                        "uuid": '1cd8a442-86d1-11e0-ae1c-123478563412',
                                        "svm": {"name": "test_vserver"}}]}, None),
    'net_routes_cluster': (200,
                           {'records': [{"destination": {"address": "176.0.0.0",
                                                         "netmask": "24",
                                                         "family": "ipv4"},
                                         "gateway": '10.193.72.1',
                                         "uuid": '1cd8a442-86d1-11e0-ae1c-123478563412',
                                         "scope": "cluster"}]}, None),
    'modified_record': (200,
                        {'records': [{"destination": {"address": "0.0.0.0",
                                                      "netmask": "0",
                                                      "family": "ipv4"},
                                      "gateway": "10.193.72.1",
                                      "uuid": '1cd8a442-86d1-11e0-ae1c-123478563412',
                                      "svm": {"name": "test_vserver"}}]}, None)
}


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


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None, data=None, sequence=None):
        ''' save arguments '''
        self.kind = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None
        self.sequence = sequence
        self.zapis = []

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        print('IN:', xml.to_string())
        zapi = xml.get_name()
        self.zapis.append(zapi)
        if self.sequence:
            kind, params = self.sequence.pop(0)
        else:
            kind, params = self.kind, self.params
        print(kind, params)
        if kind == 'net_route':
            xml = self.build_net_route_info(params)
        elif kind == 'naapierror':
            print('raising exception')
            raise netapp_utils.zapi.NaApiError(code=params[0], message=params[1])
        self.xml_out = xml
        return xml

    @staticmethod
    def build_net_route_info(net_route_details):
        ''' build xml data for net_route-attributes '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'attributes': {
                'net-vs-routes-info': {
                    'address-family': 'ipv4',
                    'destination': net_route_details['destination'],
                    'gateway': net_route_details['gateway'],
                    'metric': net_route_details['metric'],
                    'vserver': net_route_details['vserver']
                }
            }
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
        self.server = MockONTAPConnection()
        self.mock_net_route = {
            'destination': '176.0.0.0/24',
            'gateway': '10.193.72.1',
            'vserver': 'test_vserver',
            'metric': 70
        }

    def mock_args(self, rest=False, modify=False):
        if rest:
            return {
                'vserver': self.mock_net_route['vserver'],
                'destination': self.mock_net_route['destination'],
                'gateway': self.mock_net_route['gateway'],
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!'
            }
        elif modify:
            return {
                'vserver': self.mock_net_route['vserver'],
                'destination': '0.0.0.0/0',
                'gateway': '10.193.72.1',
                'from_destination': self.mock_net_route['destination'],
                'from_gateway': self.mock_net_route['gateway'],
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'use_rest': 'never'
            }
        else:
            return {
                'vserver': self.mock_net_route['vserver'],
                'destination': self.mock_net_route['destination'],
                'gateway': self.mock_net_route['gateway'],
                'metric': self.mock_net_route['metric'],
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'use_rest': 'never'
            }

    def get_net_route_mock_object(self, kind=None, data=None, cx_type='zapi', sequence=None):
        """
        Helper method to return an na_ontap_net_route object
        :param kind: passes this param to MockONTAPConnection()
        :param data: passes this data to  MockONTAPConnection()
        :param type: differentiates zapi and rest procedure
        :return: na_ontap_net_route object
        """
        net_route_obj = net_route_module()
        if cx_type == 'zapi':
            net_route_obj.ems_log_event = Mock(return_value=None)
            net_route_obj.cluster = Mock()
            net_route_obj.cluster.invoke_successfully = Mock()
            if sequence is not None:
                net_route_obj.server = MockONTAPConnection(sequence=sequence)
            elif kind is None:
                net_route_obj.server = MockONTAPConnection()
            elif data is None:
                net_route_obj.server = MockONTAPConnection(kind='net_route', data=self.mock_net_route)
            else:
                net_route_obj.server = MockONTAPConnection(kind=kind, data=data)
        return net_route_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            net_route_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_nonexistent_net_route(self):
        ''' Test if get_net_route returns None for non-existent net_route '''
        set_module_args(self.mock_args())
        result = self.get_net_route_mock_object().get_net_route()
        assert result is None

    def test_get_nonexistent_net_route_15661(self):
        ''' Test if get_net_route returns None for non-existent net_route
            when ZAPI returns an exception for a route not found
        '''
        set_module_args(self.mock_args())
        result = self.get_net_route_mock_object('naapierror', (15661, 'not_exists_error')).get_net_route()
        assert result is None

    def test_get_existing_route(self):
        ''' Test if get_net_route returns details for existing net_route '''
        set_module_args(self.mock_args())
        result = self.get_net_route_mock_object('net_route').get_net_route()
        assert result['destination'] == self.mock_net_route['destination']
        assert result['gateway'] == self.mock_net_route['gateway']

    def test_negative_get_route(self):
        ''' Test NaApiError on get '''
        data = dict(self.mock_args())
        set_module_args(data)
        sequence = [
            (None, None),                           # EMS
            ('naapierror', (12345, 'error'))        # get
        ]
        my_obj = self.get_net_route_mock_object(sequence=sequence)
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = 'Error fetching net route: NetApp API failed. Reason - 12345:error'
        assert msg in exc.value.args[0]['msg']
        assert 'net-routes-get' in my_obj.server.zapis

    def test_create_error_missing_param(self):
        ''' Test if create throws an error if destination is not specified'''
        data = self.mock_args()
        del data['destination']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object('net_route').create_net_route()
        msg = 'missing required arguments: destination'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_routes.NetAppOntapNetRoutes.create_net_route')
    def test_successful_create(self, create_net_route):
        ''' Test successful create '''
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object().apply()
        assert exc.value.args[0]['changed']
        create_net_route.assert_called_with()

    def test_successful_create_zapi(self):
        ''' Test successful create '''
        data = dict(self.mock_args())
        set_module_args(data)
        my_obj = self.get_net_route_mock_object()
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        assert 'net-routes-create' in my_obj.server.zapis

    def test_negative_create_zapi(self):
        ''' Test NaApiError on create '''
        data = dict(self.mock_args())
        set_module_args(data)
        sequence = [
            (None, None),                           # EMS
            (None, None),                           # get
            ('naapierror', (13001, 'error'))       # create
        ]
        my_obj = self.get_net_route_mock_object(sequence=sequence)
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = 'Error creating net route: NetApp API failed. Reason - 13001:error'
        assert msg in exc.value.args[0]['msg']
        assert 'net-routes-create' in my_obj.server.zapis

    def test_create_zapi_ignore_route_exist(self):
        ''' Test NaApiError on create '''
        data = dict(self.mock_args())
        set_module_args(data)
        sequence = [
            (None, None),                               # EMS
            (None, None),                               # get
            ('naapierror', (13001, 'already exists'))   # create
        ]
        my_obj = self.get_net_route_mock_object(sequence=sequence)
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        assert 'net-routes-create' in my_obj.server.zapis

    def test_successful_create_zapi_no_metric(self):
        ''' Test successful create '''
        data = dict(self.mock_args())
        data.pop('metric')
        set_module_args(data)
        my_obj = self.get_net_route_mock_object()
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        assert 'net-routes-create' in my_obj.server.zapis

    def test_create_idempotency(self):
        ''' Test create idempotency '''
        set_module_args(self.mock_args())
        obj = self.get_net_route_mock_object('net_route')
        with pytest.raises(AnsibleExitJson) as exc:
            obj.apply()
        assert not exc.value.args[0]['changed']

    def test_successful_delete(self):
        ''' Test successful delete '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object('net_route').apply()
        assert exc.value.args[0]['changed']

    def test_delete_idempotency(self):
        ''' Test delete idempotency '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object().apply()
        assert not exc.value.args[0]['changed']

    def test_negative_delete_zapi(self):
        ''' Test NaApiError on delete '''
        data = dict(self.mock_args())
        data['state'] = 'absent'
        set_module_args(data)
        sequence = [
            (None, None),                           # EMS
            ('net_route', self.mock_net_route),     # get
            ('naapierror', (12345, 'error'))        # delete
        ]
        my_obj = self.get_net_route_mock_object(sequence=sequence)
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = 'Error deleting net route: NetApp API failed. Reason - 12345:error'
        assert msg in exc.value.args[0]['msg']
        assert 'net-routes-destroy' in my_obj.server.zapis

    def test_successful_modify_metric(self):
        ''' Test successful modify metric '''
        data = dict(self.mock_args())
        del data['metric']
        data['from_metric'] = 70
        data['metric'] = 40
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object('net_route').apply()
        assert exc.value.args[0]['changed']

    def test_modify_metric_idempotency(self):
        ''' Test modify metric idempotency'''
        data = self.mock_args()
        data['metric'] = 70
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object('net_route').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_routes.NetAppOntapNetRoutes.get_net_route')
    def test_successful_modify_gateway(self, get_net_route):
        ''' Test successful modify gateway '''
        data = self.mock_args()
        del data['gateway']
        data['from_gateway'] = '10.193.72.1'
        data['gateway'] = '10.193.0.1'
        data.pop('metric')  # to use current metric
        set_module_args(data)
        current = {
            'destination': '176.0.0.0/24',
            'gateway': '10.193.72.1',
            'metric': 70,
            'vserver': 'test_server'
        }
        get_net_route.side_effect = [
            None,
            current
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_routes.NetAppOntapNetRoutes.get_net_route')
    def test_modify_gateway_idempotency(self, get_net_route):
        ''' Test modify gateway idempotency '''
        data = self.mock_args()
        del data['gateway']
        data['from_gateway'] = '10.193.72.1'
        data['gateway'] = '10.193.0.1'
        set_module_args(data)
        current = {
            'destination': '178.0.0.1/24',
            'gateway': '10.193.72.1',
            'metric': 70,
            'vserver': 'test_server'
        }
        get_net_route.side_effect = [
            current,
            None
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object('net_route', current).apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_routes.NetAppOntapNetRoutes.get_net_route')
    def test_successful_modify_destination(self, get_net_route):
        ''' Test successful modify destination '''
        data = self.mock_args()
        del data['destination']
        data['from_destination'] = '176.0.0.0/24'
        data['destination'] = '178.0.0.1/24'
        set_module_args(data)
        current = {
            'destination': '176.0.0.0/24',
            'gateway': '10.193.72.1',
            'metric': 70,
            'vserver': 'test_server'
        }
        get_net_route.side_effect = [
            None,
            current
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_routes.NetAppOntapNetRoutes.get_net_route')
    def test_modify_destination_idempotency(self, get_net_route):
        ''' Test modify destination idempotency'''
        data = self.mock_args()
        del data['destination']
        data['from_destination'] = '176.0.0.0/24'
        data['destination'] = '178.0.0.1/24'
        set_module_args(data)
        current = {
            'destination': '178.0.0.1/24',
            'gateway': '10.193.72.1',
            'metric': 70,
            'vserver': 'test_server'
        }
        get_net_route.side_effect = [
            current,
            None
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object('net_route', current).apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_net_routes.NetAppOntapNetRoutes.get_net_route')
    def test_negative_modify_destination(self, get_net_route):
        ''' Test successful modify destination '''
        data = self.mock_args()
        del data['destination']
        data['from_destination'] = '176.0.0.0/24'
        data['destination'] = '178.0.0.1/24'
        set_module_args(data)
        current = {
            'destination': '176.0.0.0/24',
            'gateway': '10.193.72.1',
            'metric': 70,
            'vserver': 'test_server'
        }
        get_net_route.side_effect = [
            None,
            current
        ]

        sequence = [
            (None, None),                           # EMS
            # ('net_route', self.mock_net_route),   - get is already mocked
            (None, None),                           # delete
            ('naapierror', (12345, 'error')),       # create
            (None, None),                           # create to undo the delete
        ]

        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(sequence=sequence).apply()
        msg = 'Error modifying net route: Error creating net route:'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == 'calling: network/ip/routes: got %s.' % SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],     # get
            SRR['empty_good'],      # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            my_main()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_cluster_scope(self, mock_request):
        data = dict(self.mock_args(rest=True))
        data['state'] = 'present'
        data.pop('vserver')
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],     # get
            SRR['empty_good'],      # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_idempotent_create_dns(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['net_routes_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_idempotent_create_cluster(self, mock_request):
        data = dict(self.mock_args(rest=True))
        data['state'] = 'present'
        data.pop('vserver')
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['net_routes_cluster'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_create(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],     # get
            SRR['generic_error'],   # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        msg = SRR['generic_error'][2]
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_destroy(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['net_routes_record'],   # get
            SRR['empty_good'],          # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_idempotently_destroy(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],     # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_destroy(self, mock_request):
        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['net_routes_record'],   # get
            SRR['generic_error'],       # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        msg = 'Error deleting net route'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_modify(self, mock_request):
        data = self.mock_args(modify=True)
        data['state'] = 'present'
        data['use_rest'] = 'auto'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],         # get - not found
            SRR['net_routes_record'],   # get - from
            SRR['empty_good'],          # delete
            SRR['empty_good'],          # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']
        print(mock_request.mock_calls)
        assert len(mock_request.mock_calls) == 5

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_idempotently_modify(self, mock_request):
        data = self.mock_args(modify=True)
        data['state'] = 'present'
        data['use_rest'] = 'auto'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['modified_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']
        assert len(mock_request.mock_calls) == 2

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_modify(self, mock_request):
        data = self.mock_args(modify=True)
        data['state'] = 'present'
        data['use_rest'] = 'auto'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],     # get
            SRR['zero_record'],     # get from
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        msg = 'Error modifying: route 176.0.0.0/24 does not exist'
        assert msg in exc.value.args[0]['msg']
        assert len(mock_request.mock_calls) == 3

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_negative_rename_fallback(self, mock_request):
        data = self.mock_args(modify=True)
        data['state'] = 'present'
        data['use_rest'] = 'auto'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['zero_record'],         # get
            SRR['net_routes_record'],   # get from
            SRR['empty_good'],          # delete
            SRR['generic_error'],       # create fail
            SRR['empty_good'],          # recreate original
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        msg = 'Error modifying net route: Error creating net route'
        assert msg in exc.value.args[0]['msg']
        print(mock_request.mock_calls)
        assert len(mock_request.mock_calls) == 6

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_zapi_no_netapp_lib(self, mock_request, mock_has_lib):
        data = self.mock_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        mock_has_lib.return_value = False
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        msg = 'Error: the python NetApp-Lib module is required.'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_non_supported_option(self, mock_request):
        data = self.mock_args()
        data['metric'] = 8
        data['use_rest'] = 'always'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        msg = "REST API currently does not support 'metric'"
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_zapi_requires_vserver(self, mock_request):
        data = dict(self.mock_args())
        data.pop('vserver')
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        msg = "Error: vserver is a required parameter when using ZAPI"
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_dest_format(self, mock_request):
        data = dict(self.mock_args())
        data['destination'] = '1.2.3.4'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        msg = "Error: Expecting '/' in '1.2.3.4'."
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_from_dest_format(self, mock_request):
        data = dict(self.mock_args())
        data['use_rest'] = 'auto'
        data['destination'] = '1.2.3.4'
        data['from_destination'] = '5.6.7.8'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_net_route_mock_object(cx_type='rest').apply()
        msg = "Error: Expecting '/' in '1.2.3.4'."
        assert msg in exc.value.args[0]['msg']
        msg = "Expecting '/' in '5.6.7.8'."
        assert msg in exc.value.args[0]['msg']
