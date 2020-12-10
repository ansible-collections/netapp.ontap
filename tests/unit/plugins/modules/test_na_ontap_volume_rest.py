# (c) 2020, NetApp, Inc
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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume \
    import NetAppOntapVolume as volume_module  # module under test

# needed for get and modify/delete as they still use ZAPI
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
    'svm_record': (200,
                   {'records': [{"uuid": "09e9fd5e-8ebd-11e9-b162-005056b39fe7",
                                 "name": "test_svm",
                                 "subtype": "default",
                                 "language": "c.utf_8",
                                 "aggregates": [{"name": "aggr_1",
                                                 "uuid": "850dd65b-8811-4611-ac8c-6f6240475ff9"},
                                                {"name": "aggr_2",
                                                 "uuid": "850dd65b-8811-4611-ac8c-6f6240475ff9"}],
                                 "comment": "new comment",
                                 "ipspace": {"name": "ansible_ipspace",
                                             "uuid": "2b760d31-8dfd-11e9-b162-005056b39fe7"},
                                 "snapshot_policy": {"uuid": "3b611707-8dfd-11e9-b162-005056b39fe7",
                                                     "name": "old_snapshot_policy"},
                                 "nfs": {"enabled": True},
                                 "cifs": {"enabled": False},
                                 "iscsi": {"enabled": False},
                                 "fcp": {"enabled": False},
                                 "nvme": {"enabled": False}}]}, None)
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

    def __init__(self, kind=None, data=None, get_volume=None):
        ''' save arguments '''
        self.type = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None
        self.get_volume = get_volume
        self.zapis = list()

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        zapi = xml.get_name()
        self.zapis.append(zapi)
        request = xml.to_string().decode('utf-8')
        if self.type == 'error':
            raise OSError('unexpected call to %s' % self.params)
        print('request:', request)
        if request.startswith('<volume-get-iter>'):
            what = None
            if self.get_volume:
                what = self.get_volume.pop(0)
            if what is None:
                xml = self.build_empty_response()
            else:
                xml = self.build_get_response(what)
        self.xml_out = xml
        print('response:', xml.to_string())
        return xml

    @staticmethod
    def build_response(data):
        ''' build xml data for vserser-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        xml.translate_struct(data)
        return xml

    def build_empty_response(self):
        data = {'num-records': '0'}
        return self.build_response(data)

    def build_get_response(self, name):
        ''' build xml data for vserser-info '''
        if name is None:
            return self.build_empty_response()
        data = {'num-records': 1,
                'attributes-list': [{
                    'volume-attributes': {
                        'volume-id-attributes': {
                            'name': name,
                            'instance-uuid': '123',
                            'style-extended': 'flexvol'
                        },
                        'volume-performance-attributes': {
                            'is-atime-update-enabled': 'true'
                        },
                        'volume-security-attributes': {
                            'volume-security-unix-attributes': {
                                'permissions': 777
                            }
                        },
                        'volume-snapshot-attributes': {
                            'snapshot-policy': 'default'
                        },
                        'volume-snapshot-autodelete-attributes': {
                            'is-autodelete-enabled': 'true'
                        },
                        'volume-space-attributes': {
                            'size': 10737418240     # 10 GB
                        },
                        'volume-state-attributes': {
                            'state': 'online'
                        },
                    }
                }]}
        return self.build_response(data)


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        # self.server = MockONTAPConnection()
        self.mock_vserver = {
            'name': 'test_svm',
            'root_volume': 'ansible_vol',
            'root_volume_aggregate': 'ansible_aggr',
            'aggr_list': 'aggr_1,aggr_2',
            'ipspace': 'ansible_ipspace',
            'subtype': 'default',
            'language': 'c.utf_8',
            'snapshot_policy': 'old_snapshot_policy',
            'comment': 'new comment'
        }

    @staticmethod
    def mock_args():
        return {'name': 'test_volume',
                'vserver': 'ansibleSVM',
                'nas_application_template': dict(
                    tiering=None
                ),
                # 'aggregate_name': 'whatever',       # not used for create when using REST application/applications
                'size': 10,
                'size_unit': 'gb',
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!'}

    def get_volume_mock_object(self, **kwargs):
        volume_obj = volume_module()
        netapp_utils.ems_log_event = Mock(return_value=None)
        volume_obj.server = MockONTAPConnection(**kwargs)
        volume_obj.cluster = MockONTAPConnection(kind='error', data='cluster ZAPI.')
        return volume_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            volume_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_fail_if_aggr_is_set(self, mock_request):
        data = dict(self.mock_args())
        data['aggregate_name'] = 'should_fail'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        error = 'Conflict: aggregate_name is not supported when application template is enabled.  Found: aggregate_name: should_fail'
        assert exc.value.args[0]['msg'] == error

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_missing_size(self, mock_request):
        data = dict(self.mock_args())
        data.pop('size')
        set_module_args(data)
        mock_request.side_effect = [
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        error = 'Error: "size" is required to create nas application.'
        assert exc.value.args[0]['msg'] == error

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_mismatched_tiering_policies(self, mock_request):
        data = dict(self.mock_args())
        data['tiering_policy'] = 'none'
        data['nas_application_template'] = dict(
            tiering=dict(policy='auto')
        )
        set_module_args(data)
        mock_request.side_effect = [
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        error = 'Conflict: if tiering_policy and nas_application_template tiering policy are both set, they must match.'
        error += '  Found "none" and "auto".'
        assert exc.value.args[0]['msg'] == error

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        data = dict(self.mock_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],       # POST application/applications
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['msg'] == 'Error: calling: /application/applications: got %s' % SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_created(self, mock_request):
        data = dict(self.mock_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],       # POST application/applications
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_create_idempotency(self, mock_request):
        data = dict(self.mock_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object(get_volume=['test']).apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_created_with_modify(self, mock_request):
        ''' since language is not supported in application, the module is expected to:
            1. create the volume using application REST API
            2. immediately modify the volume to update options which not available in the nas template.
        '''
        data = dict(self.mock_args())
        data['language'] = 'fr'     # TODO: apparently language is not supported for modify
        data['unix_permissions'] = '---rw-rx-r--'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],       # POST application/applications
            SRR['end_of_sequence']
        ]
        my_volume = self.get_volume_mock_object(get_volume=[None, 'test'])
        with pytest.raises(AnsibleExitJson) as exc:
            my_volume.apply()
        assert exc.value.args[0]['changed']
        print(exc.value.args[0])
        assert 'unix_permissions' in exc.value.args[0]['modify_after_create']
        assert 'language' not in exc.value.args[0]['modify_after_create']        # eh!
        assert 'volume-modify-iter' in my_volume.server.zapis

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_resized(self, mock_request):
        ''' make sure resize if using RESP API if sizing_method is present
        '''
        data = dict(self.mock_args())
        data['sizing_method'] = 'add_new_resources'
        data['size'] = 20737418240
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],       # PATCH application/applications
            SRR['end_of_sequence']
        ]
        my_volume = self.get_volume_mock_object(get_volume=['test'])
        with pytest.raises(AnsibleExitJson) as exc:
            my_volume.apply()
        assert exc.value.args[0]['changed']
        print(exc.value.args[0])
        assert 'volume-size' not in my_volume.server.zapis
        print(mock_request.call_args)
        mock_request.assert_called_with('PATCH', '/storage/volumes/123', {'sizing_method': 'add_new_resources'}, json={'size': 22266633286068469760})
