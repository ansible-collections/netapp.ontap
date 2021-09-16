# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_job_schedule '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_job_schedule \
    import NetAppONTAPJob as job_module, main as uut_main   # module under test

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
    'get_schedule': (
        200,
        {
            "records": [
                {
                    "uuid": "010df156-e0a9-11e9-9f70-005056b3df08",
                    "name": "test_job",
                    "cron": {
                        "minutes": [
                            25
                        ],
                        "hours": [
                            0
                        ],
                        "weekdays": [
                            0
                        ],
                        "months": [5, 6]
                    }
                }
            ],
            "num_records": 1
        }, None),
    'get_all_minutes': (
        200,
        {
            "records": [
                {
                    "uuid": "010df156-e0a9-11e9-9f70-005056b3df08",
                    "name": "test_job",
                    "cron": {
                        "minutes": range(60),
                        "hours": [
                            0
                        ],
                        "weekdays": [
                            0
                        ],
                        "months": [5, 6]
                    }
                }
            ],
            "num_records": 1
        }, None),
    "no_record": (
        200,
        {"num_records": 0},
        None)
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

    def __init__(self, kind=None, data=None):
        ''' save arguments '''
        if kind == 'get_all_minutes':
            data = {
                'name': 'test_job',
                'minutes': range(60),
                'job_hours': [0],
                'weekdays': [0]
            }
        self.kind = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None
        self.call_log = []

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        # print('IN:', xml.to_string())
        self.call_log.append(xml.to_string())
        if self.kind == 'job':
            xml = self.build_job_schedule_cron_info(self.params)
        elif self.kind == 'job_multiple':
            xml = self.build_job_schedule_multiple_cron_info(self.params)
        elif self.kind == 'get_all_minutes':
            xml = self.build_job_schedule_multiple_cron_minutes_info(self.params)
        elif self.kind == 'no_job':
            xml = self.build_job_schedule_None_info(self.params)
        elif self.kind == 'error':
            raise netapp_utils.zapi.NaApiError('forced exception')
        elif self.kind == 'error_after_empty_get_job':
            xml = self.build_job_schedule_None_info(self.params)
            self.kind = 'error'
        elif self.kind == 'error_after_get_job':
            xml = self.build_job_schedule_cron_info(self.params)
            self.kind = 'error'
        self.xml_out = xml
        return xml

    @staticmethod
    def build_job_schedule_cron_info(job_details):
        ''' build xml data for vserser-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'job-schedule-cron-info': {
                    'job-schedule-name': job_details['name'],
                    'job-schedule-cron-minute': {
                        'cron-minute': job_details['minutes']
                    }
                }
            }
        }
        xml.translate_struct(attributes)
        return xml

    @staticmethod
    def build_job_schedule_None_info(job_details):
        ''' build xml data for vserser-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': '0'
        }
        xml.translate_struct(attributes)
        return xml

    @staticmethod
    def build_job_schedule_multiple_cron_info(job_details):
        ''' build xml data for vserser-info '''
        print("CALLED MULTIPLE BUILD")
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'job-schedule-cron-info': {
                    'job-schedule-name': job_details['name'],
                    'job-schedule-cron-minute': [
                        {'cron-minute': '25'},
                        {'cron-minute': '35'}
                    ],
                    'job-schedule-cron-month': [
                        {'cron-month': '5'},
                        {'cron-month': '10'}
                    ]
                }
            }
        }
        xml.translate_struct(attributes)
        return xml

    @staticmethod
    def build_job_schedule_multiple_cron_minutes_info(job_details):
        ''' build xml data for vserser-info '''
        print("CALLED MULTIPLE BUILD")
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
            'attributes-list': {
                'job-schedule-cron-info': {
                    'job-schedule-name': job_details['name'],
                    'job-schedule-cron-minute': [{'cron-minute': str(x)} for x in job_details['minutes']],
                    'job-schedule-cron-month': [
                        {'cron-month': '5'},
                        {'cron-month': '10'}
                    ]
                }
            }
        }
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_job_schedule '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_job = {
            'name': 'test_job',
            'minutes': 25,
            'job_hours': [0],
            'weekdays': [0]
        }

    def mock_args(self, rest=False):
        if rest:
            return {
                'name': self.mock_job['name'],
                'job_minutes': [self.mock_job['minutes']],
                'job_hours': self.mock_job['job_hours'],
                'job_days_of_week': self.mock_job['weekdays'],
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!'
            }
        else:
            return {
                'name': self.mock_job['name'],
                'job_minutes': [self.mock_job['minutes']],
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'use_rest': 'never'
            }

    def get_job_mock_object(self, kind=None, call_type='zapi'):
        """
        Helper method to return an na_ontap_job_schedule object
        :param kind: passes this param to MockONTAPConnection()
        :param call_type:
        :return: na_ontap_job_schedule object
        """
        job_obj = job_module()
        if call_type == 'zapi':
            if kind is None:
                job_obj.server = MockONTAPConnection()
            else:
                job_obj.server = MockONTAPConnection(kind=kind, data=self.mock_job)
        return job_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            job_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_get_nonexistent_job(self):
        ''' Test if get_job_schedule returns None for non-existent job '''
        set_module_args(self.mock_args())
        result = self.get_job_mock_object().get_job_schedule()
        assert result is None

    def test_get_existing_job(self):
        ''' Test if get_job_schedule retuns job details for existing job '''
        data = self.mock_args()
        set_module_args(data)
        result = self.get_job_mock_object('job').get_job_schedule()
        assert result['name'] == self.mock_job['name']
        assert result['job_minutes'] == data['job_minutes']

    def test_get_existing_job_multiple_minutes(self):
        # sourcery skip: class-extract-method
        ''' Test if get_job_schedule retuns job details for existing job '''
        set_module_args(self.mock_args())
        result = self.get_job_mock_object('job_multiple').get_job_schedule()
        print(str(result))
        assert result['name'] == self.mock_job['name']
        assert result['job_minutes'] == [25, 35]
        assert result['job_months'] == [5, 10]

    def test_get_existing_job_multiple_minutes_0_offset(self):
        ''' Test if get_job_schedule retuns job details for existing job '''
        data = self.mock_args()
        data['month_offset'] = 0
        set_module_args(data)
        result = self.get_job_mock_object('job_multiple').get_job_schedule()
        print(str(result))
        assert result['name'] == self.mock_job['name']
        assert result['job_minutes'] == [25, 35]
        assert result['job_months'] == [5, 10]

    def test_get_existing_job_multiple_minutes_1_offset(self):
        ''' Test if get_job_schedule retuns job details for existing job '''
        data = self.mock_args()
        data['month_offset'] = 1
        set_module_args(data)
        result = self.get_job_mock_object('job_multiple').get_job_schedule()
        print(str(result))
        assert result['name'] == self.mock_job['name']
        assert result['job_minutes'] == [25, 35]
        assert result['job_months'] == [5 + 1, 10 + 1]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_create_error_missing_param(self, mock_ems_log):
        ''' Test if create throws an error if job_minutes is not specified'''
        data = self.mock_args()
        del data['job_minutes']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_job_mock_object('no_job').apply()
        msg = 'Error: missing required parameter job_minutes for create'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_successful_create(self, mock_ems_log):
        ''' Test successful create '''
        set_module_args(self.mock_args())
        uut = self.get_job_mock_object()
        with pytest.raises(AnsibleExitJson) as exc:
            uut.apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_successful_create_0_offset(self, mock_ems_log):
        ''' Test successful create '''
        data = self.mock_args()
        data['month_offset'] = 0
        data['job_months'] = [0, 8]
        set_module_args(data)
        uut = self.get_job_mock_object()
        with pytest.raises(AnsibleExitJson) as exc:
            uut.apply()
        assert exc.value.args[0]['changed']
        print(uut.server.call_log)
        assert b"<cron-month>0</cron-month>" in uut.server.call_log[1]
        assert b"<cron-month>8</cron-month>" in uut.server.call_log[1]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_successful_create_1_offset(self, mock_ems_log):
        ''' Test successful create '''
        data = self.mock_args()
        data['month_offset'] = 1
        data['job_months'] = [1, 9]
        set_module_args(data)
        uut = self.get_job_mock_object()
        with pytest.raises(AnsibleExitJson) as exc:
            uut.apply()
        assert exc.value.args[0]['changed']
        print(uut.server.call_log)
        assert b"<cron-month>0</cron-month>" in uut.server.call_log[1]
        assert b"<cron-month>8</cron-month>" in uut.server.call_log[1]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_create_idempotency(self, mock_ems_log):
        ''' Test create idempotency '''
        set_module_args(self.mock_args())
        mock_ems_log.return_value = None
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_job_mock_object('job').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_negative_create(self, mock_ems_log):
        ''' Test create error '''
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_job_mock_object('error_after_empty_get_job').apply()
        msg = 'Error creating job schedule test_job:'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_successful_delete(self, mock_ems_log):
        ''' Test delete existing job '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_job_mock_object('job').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_delete_idempotency(self, mock_ems_log):
        ''' Test delete idempotency '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_job_mock_object().apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_negative_delete(self, mock_ems_log):
        ''' Test delete existing job  with error '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_job_mock_object('error_after_get_job').apply()
        msg = 'Error deleting job schedule test_job:'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_successful_modify(self, mock_ems_log):
        ''' Test successful modify job_minutes '''
        data = self.mock_args()
        data['job_minutes'] = ['20']
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_job_mock_object('job').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_modify_idempotency(self, mock_ems_log):
        ''' Test modify idempotency '''
        data = self.mock_args()
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_job_mock_object('job').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_negative_modify(self, mock_ems_log):
        ''' Test modify error '''
        data = self.mock_args()
        data['job_minutes'] = ['20']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_job_mock_object('error_after_get_job').apply()
        msg = 'Error modifying job schedule test_job:'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successful_create(self, mock_request):
        '''Test successful rest create'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_job_mock_object(call_type='rest').apply()
        assert exc.value.args[0]['changed']
        print(mock_request.mock_calls)
        print(mock_request.call_args[1]['json']['cron'])

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_create_idempotency(self, mock_request):
        '''Test rest create idempotency'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_schedule'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_job_mock_object(call_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        '''Test rest create idempotency'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_job_mock_object(call_type='rest').apply()
        assert 'Error on creating job schedule: Expected error' in exc.value.args[0]['msg']

        data = self.mock_args(rest=True)
        data['job_minutes'] = ['20']
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_schedule'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_job_mock_object(call_type='rest').apply()
        assert 'Error on modifying job schedule: Expected error' in exc.value.args[0]['msg']

        data = self.mock_args(rest=True)
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_schedule'],
            SRR['generic_error'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_job_mock_object(call_type='rest').apply()
        assert 'Error on deleting job schedule: Expected error' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_get_0_offset(self, mock_request):
        '''Test rest get using month offset'''
        data = self.mock_args(rest=True)
        data['month_offset'] = 0
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_schedule'],
            SRR['end_of_sequence']
        ]
        record = self.get_job_mock_object(call_type='rest').get_job_schedule()
        print('RECORD', record)
        assert record
        assert record['job_months'] == [x - 1 for x in SRR['get_schedule'][1]['records'][0]['cron']['months']]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_get_1_offset(self, mock_request):
        '''Test rest get using month offset'''
        data = self.mock_args(rest=True)
        data['month_offset'] = 1
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_schedule'],
            SRR['end_of_sequence']
        ]
        record = self.get_job_mock_object(call_type='rest').get_job_schedule()
        print('RECORD', record)
        assert record
        assert record['job_months'] == SRR['get_schedule'][1]['records'][0]['cron']['months']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_create_all_minutes(self, mock_request):
        '''Test rest create using month offset'''
        data = self.mock_args(rest=True)
        data['job_minutes'] = [-1]
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],
            SRR['end_of_sequence']
        ]
        self.get_job_mock_object(call_type='rest').create_job_schedule()
        assert mock_request.call_args
        assert mock_request.call_args[1]['json']['cron']['minutes'] == []

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_create_0_offset(self, mock_request):
        '''Test rest create using month offset'''
        data = self.mock_args(rest=True)
        data['month_offset'] = 0
        data['job_months'] = [0, 8]
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],
            SRR['end_of_sequence']
        ]
        self.get_job_mock_object(call_type='rest').create_job_schedule()
        assert mock_request.call_args
        assert mock_request.call_args[1]['json']['cron']['months'] == [x + 1 for x in data['job_months']]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_create_1_offset(self, mock_request):
        '''Test rest create using month offset'''
        data = self.mock_args(rest=True)
        data['month_offset'] = 1
        data['job_months'] = [1, 9]
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],
            SRR['end_of_sequence']
        ]
        self.get_job_mock_object(call_type='rest').create_job_schedule()
        assert mock_request.call_args
        assert mock_request.call_args[1]['json']['cron']['months'] == data['job_months']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_modify_0_offset(self, mock_request):
        '''Test rest modify using month offset'''
        data = self.mock_args(rest=True)
        data['month_offset'] = 0
        data['job_months'] = [0, 8]
        current, modify = dict(), dict()
        modify['job_months'] = [0, 8]
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_schedule'],
            SRR['end_of_sequence']
        ]
        uut = self.get_job_mock_object(call_type='rest')
        uut.uuid = 'testuuid'
        uut.modify_job_schedule(modify, current)
        assert mock_request.call_args
        assert mock_request.call_args[1]['json']['cron']['months'] == [x + 1 for x in data['job_months']]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_modify_1_offset(self, mock_request):
        '''Test rest modify using month offset'''
        data = self.mock_args(rest=True)
        data['month_offset'] = 1
        data['job_months'] = [1, 9]
        current, modify = dict(), dict()
        modify['job_months'] = [1, 9]
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],
            SRR['end_of_sequence']
        ]
        uut = self.get_job_mock_object(call_type='rest')
        uut.uuid = 'testuuid'
        uut.modify_job_schedule(modify, current)
        assert mock_request.call_args
        assert mock_request.call_args[1]['json']['cron']['months'] == data['job_months']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_month_of_0(self, mock_request):
        '''Test rest modify using month offset'''
        data = self.mock_args(rest=True)
        data['month_offset'] = 1
        data['job_months'] = [0, 9]
        current, modify = dict(), dict()
        modify['job_months'] = [1, 9]
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_job_mock_object(call_type='rest')
        msg = 'Error: 0 is not a valid value in months if month_offset is set to 1'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
    def test_negative_no_netapp_lib(self, mock_has):
        mock_has.return_value = False
        data = self.mock_args(rest=True)
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_job_mock_object()
        msg = 'the python NetApp-Lib module is required'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_negative_zapi_get_error(self, mock_ems_log):
        data = self.mock_args()
        set_module_args(data)
        uut = self.get_job_mock_object(kind='error')
        with pytest.raises(AnsibleFailJson) as exc:
            uut.apply()
        msg = 'Error fetching job schedule test_job:'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_rest_get_error(self, mock_request):
        '''Test rest modify using month offset'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            uut_main()
        msg = 'Error on fetching job schedule:'
        assert msg in exc.value.args[0]['msg']

    def test_zapi_get_all_minutes(self):
        data = self.mock_args()
        set_module_args(data)
        uut = self.get_job_mock_object(kind='get_all_minutes')
        schedule = uut.get_job_schedule()
        print('SCHED', schedule)
        assert schedule
        assert 'job_minutes' in schedule
        assert schedule['job_minutes'] == [-1]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_get_all_minutes(self, mock_request):
        '''Test rest modify using month offset'''
        data = self.mock_args(rest=True)
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_all_minutes'],
            SRR['end_of_sequence']
        ]
        uut = self.get_job_mock_object(call_type='rest')
        schedule = uut.get_job_schedule()
        print('SCHED:', schedule)
        assert schedule
        assert 'job_minutes' in schedule
        assert schedule['job_minutes'] == [-1]
