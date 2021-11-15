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
    'is_rest': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'no_record': (200, {'num_records': 0, 'records': []}, None),
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
                                 "nvme": {"enabled": False}}]}, None),
    # Volume
    'get_volume': (200,
                   {'records': [{
                       "uuid": "7882901a-1aef-11ec-a267-005056b30cfa",
                       "comment": "carchi8py",
                       "name": "test_svm",
                       "state": "online",
                       "style": "flexvol",
                       "tiering": {
                           "policy": "backup"
                       },
                       "type": "rw",
                       "aggregates": [
                           {
                               "name": "aggr1"
                           }
                       ],
                       "encryption": {
                           "enabled": True
                       },
                       "efficiency": {
                           "compression": "none",
                           "policy": {
                               "name": "-"
                           }
                       },
                       "nas": {
                           "gid": 0,
                           "security_style": "unix",
                           "uid": 0,
                           "unix_permissions": 654,
                           "path": '/this/path',
                           "export_policy": {
                               "name": "default"
                           }
                       },
                       "snapshot_policy": {
                           "name": "default",
                           "uuid": "0a42a3d9-0c29-11ec-a267-005056b30cfa"
                       },
                       "space": {
                           "size": 10737418240,
                           "snapshot": {
                               "reserve_percent": 5
                           }
                       },
                       "guarantee": {
                           "type": "volume"
                       }
                   }]}, None),
    'get_volume_mount': (200,
                         {'records': [{
                             "uuid": "7882901a-1aef-11ec-a267-005056b30cfa",
                             "comment": "carchi8py",
                             "name": "test_svm",
                             "state": "online",
                             "style": "flexvol",
                             "tiering": {
                                 "policy": "none"
                             },
                             "type": "rw",
                             "aggregates": [
                                 {
                                     "name": "aggr1"
                                 }
                             ],
                             "encryption": {
                                 "enabled": True
                             },
                             "efficiency": {
                                 "compression": "none",
                                 "policy": {
                                     "name": "-"
                                 }
                             },
                             "nas": {
                                 "gid": 0,
                                 "security_style": "unix",
                                 "uid": 0,
                                 "unix_permissions": 654,
                                 "path": '',
                                 "export_policy": {
                                     "name": "default"
                                 }
                             },
                             "snapshot_policy": {
                                 "name": "default",
                                 "uuid": "0a42a3d9-0c29-11ec-a267-005056b30cfa"
                             },
                             "space": {
                                 "size": 10737418240,
                                 "snapshot": {
                                     "reserve_percent": 5
                                 }
                             },
                             "guarantee": {
                                 "type": "volume"
                             }
                         }]}, None),
    'get_volume_encrypt_off': (200,
                               {'records': [{
                                   "uuid": "7882901a-1aef-11ec-a267-005056b30cfa",
                                   "comment": "carchi8py",
                                   "name": "test_svm",
                                   "state": "online",
                                   "style": "flexvol",
                                   "tiering": {
                                       "policy": "backup"
                                   },
                                   "type": "rw",
                                   "aggregates": [
                                       {
                                           "name": "aggr1"
                                       }
                                   ],
                                   "encryption": {
                                       "enabled": False
                                   },
                                   "efficiency": {
                                       "compression": "none",
                                       "policy": {
                                           "name": "-"
                                       }
                                   },
                                   "nas": {
                                       "gid": 0,
                                       "security_style": "unix",
                                       "uid": 0,
                                       "unix_permissions": 654,
                                       "path": '/this/path',
                                       "export_policy": {
                                           "name": "default"
                                       }
                                   },
                                   "snapshot_policy": {
                                       "name": "default",
                                       "uuid": "0a42a3d9-0c29-11ec-a267-005056b30cfa"
                                   },
                                   "space": {
                                       "size": 10737418240,
                                       "snapshot": {
                                           "reserve_percent": 5
                                       }
                                   },
                                   "guarantee": {
                                       "type": "volume"
                                   }
                               }]}, None),
    # module specific responses
    'nas_app_record': (200,
                       {'records': [{"uuid": "09e9fd5e-8ebd-11e9-b162-005056b39fe7",
                                     "name": "test_app",
                                     "nas": {
                                         "application_components": [{'xxx': 1}]}
                                     }]}, None)
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
            'comment': 'new comment',
            'use_rest': 'always'
        }

    @staticmethod
    def mock_args():
        return {'name': 'test_svm',
                'vserver': 'ansibleSVM',
                'nas_application_template': dict(
                    tiering=None
                ),
                # 'aggregate_name': 'whatever',       # not used for create when using REST application/applications
                'size': 10,
                'size_unit': 'gb',
                'hostname': 'test',
                'username': 'test_user',
                'password': 'test_pass!',
                'use_rest': 'always'}

    @staticmethod
    def mock_args_volume():
        return {
            'name': 'test_svm',
            'vserver': 'ansibleSVM',
            'aggregate_name': 'aggr1',
            'size': 10,
            'size_unit': 'gb',
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!',
            'use_rest': 'always'
        }

    def get_volume_mock_object(self):
        return volume_module()

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
            SRR['is_rest'],
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
            SRR['is_rest'],
            SRR['no_record'],  # GET volume
            SRR['no_record'],  # GET application/applications
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
            SRR['is_rest'],
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
            SRR['no_record'],  # GET volume
            SRR['no_record'],  # GET application/applications
            SRR['generic_error'],  # POST application/applications
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = 'Error in create_nas_application: calling: application/applications: got %s.' % SRR['generic_error'][2]
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_created(self, mock_request):
        data = dict(self.mock_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # GET application/applications
            SRR['empty_good'],  # POST application/applications
            SRR['get_volume'],
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
            SRR['get_volume'],  # Get Volume
            SRR['no_record'],  # GET application/applications
            SRR['end_of_sequence']

        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_created_with_modify(self, mock_request):
        ''' since language is not supported in application, the module is expected to:
            1. create the volume using application REST API
            2. immediately modify the volume to update options which not available in the nas template.
        '''
        data = dict(self.mock_args())
        data['language'] = 'fr'  # TODO: apparently language is not supported for modify
        data['unix_permissions'] = '---rw-rx-r--'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['no_record'],  # GET application/applications
            SRR['empty_good'],  # POST application/applications
            SRR['end_of_sequence']
        ]
        my_volume = self.get_volume_mock_object()
        with pytest.raises(AnsibleExitJson) as exc:
            my_volume.apply()
        assert exc.value.args[0]['changed']
        print(exc.value.args[0])
        assert 'unix_permissions' in exc.value.args[0]['modify']
        assert 'language' not in exc.value.args[0]['modify']  # eh!

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
            SRR['get_volume'],  # Get Volume
            SRR['no_record'],  # GET application/applications
            SRR['empty_good'],  # PATCH storage/volumes
        ]
        my_volume = self.get_volume_mock_object()
        with pytest.raises(AnsibleExitJson) as exc:
            my_volume.apply()
        assert exc.value.args[0]['changed']
        print(exc.value.args[0])
        print(mock_request.call_args)
        query = {'return_timeout': 30, 'sizing_method': 'add_new_resources'}
        mock_request.assert_called_with('PATCH',
                                        'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa',
                                        query,
                                        json={'size': 22266633286068469760},
                                        headers=None
                                        )

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_deleted(self, mock_request):
        ''' delete volume using REST - no app
        '''
        data = dict(self.mock_args())
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['no_record'],  # GET application/applications
            SRR['empty_good'],  # PATCH storage/volumes - unmount
            SRR['empty_good'],  # DELETE storage/volumes
            SRR['end_of_sequence']
        ]
        my_volume = self.get_volume_mock_object()
        with pytest.raises(AnsibleExitJson) as exc:
            my_volume.apply()
        assert exc.value.args[0]['changed']
        print(exc.value.args[0])
        print(mock_request.call_args)
        print(mock_request.mock_calls)
        query = {'return_timeout': 30}
        mock_request.assert_called_with('DELETE',
                                        'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa',
                                        query,
                                        json=None,
                                        headers=None
                                        )

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_deleted_with_app(self, mock_request):
        ''' delete app
        '''
        data = dict(self.mock_args())
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['nas_app_record'],  # GET application/applications
            SRR['nas_app_record'],  # GET application/applications/uuid
            SRR['empty_good'],  # PATCH storage/volumes - unmount
            SRR['empty_good'],  # DELETE storage/volumes
            SRR['end_of_sequence']
        ]
        my_volume = self.get_volume_mock_object()
        with pytest.raises(AnsibleExitJson) as exc:
            my_volume.apply()
        assert exc.value.args[0]['changed']
        print(exc.value.args[0])
        print(mock_request.call_args)
        print(mock_request.mock_calls)
        query = {'return_timeout': 30}
        mock_request.assert_called_with('DELETE',
                                        'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa',
                                        query,
                                        json=None,
                                        headers=None)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_move_volume(self, mock_request):
        data = dict(self.mock_args_volume())
        data['aggregate_name'] = 'aggr2'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['no_record'],  # Move volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_move_volume(self, mock_request):
        data = dict(self.mock_args_volume())
        data['aggregate_name'] = 'aggr2'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['generic_error'],  # Move volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error moving volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_volume_unmount_rest(self, mock_request):
        data = dict(self.mock_args_volume())
        data['junction_path'] = ''
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['no_record'],  # Mount Volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_volume_unmount_rest(self, mock_request):
        data = dict(self.mock_args_volume())
        data['junction_path'] = ''
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['generic_error'],  # Mount Volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error unmounting volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_volume_mount_rest(self, mock_request):
        data = dict(self.mock_args_volume())
        data['junction_path'] = '/this/path'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume_mount'],  # Get Volume
            SRR['no_record'],  # Mount Volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_volume_mount_rest(self, mock_request):
        data = dict(self.mock_args_volume())
        data['junction_path'] = '/this/path'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume_mount'],  # Get Volume
            SRR['generic_error'],  # Mount Volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error mounting volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_change_volume_state(self, mock_request):
        data = dict(self.mock_args_volume())
        data['is_online'] = False
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['no_record'],  # Move volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_change_volume_state(self, mock_request):
        data = dict(self.mock_args_volume())
        data['is_online'] = False
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['generic_error'],  # Move volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error changing state of volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_modify_attributes(self, mock_request):
        data = dict(self.mock_args_volume())
        data['space_guarantee'] = 'volume'
        data['percent_snapshot_space'] = 10
        data['snapshot_policy'] = 'default2'
        data['export_policy'] = 'default2'
        data['group_id'] = 5
        data['user_id'] = 5
        data['volume_security_style'] = 'mixed'
        data['comment'] = 'carchi8py was here'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['no_record'],  # Modify
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_modify_attributes(self, mock_request):
        data = dict(self.mock_args_volume())
        data['space_guarantee'] = 'volume'
        data['percent_snapshot_space'] = 10
        data['snapshot_policy'] = 'default2'
        data['export_policy'] = 'default2'
        data['group_id'] = 5
        data['user_id'] = 5
        data['volume_security_style'] = 'mixed'
        data['comment'] = 'carchi8py was here'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['generic_error'],  # Modify
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error modifying volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_volume(self, mock_request):
        data = dict(self.mock_args_volume())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['get_volume'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_get_volume(self, mock_request):
        data = dict(self.mock_args_volume())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],  # Get Volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "calling: storage/volumes: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_create_volume(self, mock_request):
        data = dict(self.mock_args_volume())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['generic_error'],  # Create Volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error creating volume test_svm: calling: storage/volumes: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_volume_with_options(self, mock_request):
        data = dict(self.mock_args_volume())
        data['space_guarantee'] = 'volume'
        data['percent_snapshot_space'] = 5
        data['snapshot_policy'] = 'default'
        data['export_policy'] = 'default'
        data['group_id'] = 0
        data['user_id'] = 0
        data['volume_security_style'] = 'unix'
        data['comment'] = 'carchi8py'
        data['type'] = 'RW'
        data['language'] = 'en'
        data['encrypt'] = True
        data['junction_path'] = '/this/path'
        data['tiering_policy'] = 'backup'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['get_volume'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_snapshot_restore_volume(self, mock_request):
        data = dict(self.mock_args_volume())
        data['snapshot_restore'] = 'snapshot_copy'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['get_volume'],  # Get Volume
            SRR['no_record'],  # Modify Snapshot restore
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_snapshot_restore_volume(self, mock_request):
        data = dict(self.mock_args_volume())
        data['snapshot_restore'] = 'snapshot_copy'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume
            SRR['get_volume'],  # Get Volume
            SRR['generic_error'],  # Modify Snapshot restore
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error restoring snapshot snapshot_copy in volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_rename_volume(self, mock_request):
        data = dict(self.mock_args_volume())
        data['from_name'] = 'test_svm'
        data['name'] = 'new_name'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume name
            SRR['get_volume'],  # Get Volume from
            SRR['get_volume'],  # Get Volume from
            SRR['no_record'],  # Patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_rename_volume(self, mock_request):
        data = dict(self.mock_args_volume())
        data['from_name'] = 'test_svm'
        data['name'] = 'new_name'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume name
            SRR['get_volume'],  # Get Volume from
            SRR['get_volume'],  # Get Volume from
            SRR['generic_error'],  # Patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error changing name of volume new_name: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_resizing_volume(self, mock_request):
        data = dict(self.mock_args_volume())
        data['sizing_method'] = 'add_new_resources'
        data['size'] = 20737418240
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume'],  # Get Volume name
            SRR['generic_error'],  # Resize volume
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error resizing volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_volume_with_unix_permissions(self, mock_request):
        data = dict(self.mock_args_volume())
        data['unix_permissions'] = '---rw-r-xr-x'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['get_volume'],
            SRR['no_record'],  # add unix permissions
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_volume_with_qos_policy(self, mock_request):
        data = dict(self.mock_args_volume())
        data['qos_policy_group'] = 'policy-name'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['get_volume'],
            SRR['no_record'],  # Set policy name
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_volume_with_qos_adaptive_policy_group(self, mock_request):
        data = dict(self.mock_args_volume())
        data['qos_adaptive_policy_group'] = 'policy-name'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['get_volume'],
            SRR['no_record'],  # Set policy name
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_volume_with_qos_adaptive_policy_error(self, mock_request):
        data = dict(self.mock_args_volume())
        data['qos_adaptive_policy_group'] = 'policy-name'
        data['qos_policy_group'] = 'policy-name'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['get_volume'],
            SRR['generic_error'],  # Set policy name
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error: With Rest API qos_policy_group and qos_adaptive_policy_group are now the same thing, and cannot be set at the same time"
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_volume_with_tiring_policy(self, mock_request):
        data = dict(self.mock_args_volume())
        data['tiering_policy'] = 'all'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['get_volume'],
            SRR['no_record'],  # Set Tiering_policy
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create_volume_encrypt(self, mock_request):
        data = dict(self.mock_args_volume())
        data['encrypt'] = False
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['no_record'],  # Get Volume
            SRR['no_record'],  # Create Volume
            SRR['get_volume'],
            SRR['no_record'],  # Set Encryption
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_modify_volume_encrypt(self, mock_request):
        data = dict(self.mock_args_volume())
        data['encrypt'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume_encrypt_off'],  # Get Volume
            SRR['no_record'],  # Set Encryption
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_modify_volume_encrypt(self, mock_request):
        data = dict(self.mock_args_volume())
        data['encrypt'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume_encrypt_off'],  # Get Volume
            SRR['generic_error'],  # Set Encryption
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error enabling encryption for volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_modify_volume_compression(self, mock_request):
        data = dict(self.mock_args_volume())
        data['efficiency_policy'] = 'test'
        data['compression'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume_encrypt_off'],  # Get Volume
            SRR['no_record'],  # compression
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_modify_volume_inline_compression(self, mock_request):
        data = dict(self.mock_args_volume())
        data['efficiency_policy'] = 'test'
        data['inline_compression'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume_encrypt_off'],  # Get Volume
            SRR['no_record'],  # compression
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_modify_volume_efficiency_policy(self, mock_request):
        data = dict(self.mock_args_volume())
        data['efficiency_policy'] = 'test'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume_encrypt_off'],  # Get Volume
            SRR['generic_error'],  # Set Encryption
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error set efficiency for volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error_volume_compression_both(self, mock_request):
        data = dict(self.mock_args_volume())
        data['compression'] = True
        data['inline_compression'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['get_volume_encrypt_off'],  # Get Volume
            SRR['generic_error'],  # Set Encryption
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_mock_object().apply()
        msg = "Error set efficiency for volume test_svm: calling: storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa: got Expected error."
        assert exc.value.args[0]['msg'] == msg
