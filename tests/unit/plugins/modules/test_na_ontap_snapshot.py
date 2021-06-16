# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_nvme_snapshot'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapshot \
    import NetAppOntapSnapshot as my_module

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'volume_uuid': (200,
                    {'records': [{"uuid": "test_uuid"}], 'num_records': 1}, None,
                    ),
    'snapshot_record': (200,
                        {'records': [{"volume": {"uuid": "d9cd4ec5-c96d-11eb-9271-005056b3ef5a",
                                                 "name": "ansible_vol"},
                                      "uuid": "343b5227-8c6b-4e79-a133-304bbf7537ce",
                                      "svm": {"uuid": "b663d6f0-c96d-11eb-9271-005056b3ef5a",
                                              "name": "ansible"},
                                      "name": "ss1",
                                      "create_time": "2021-06-10T17:24:41-04:00",
                                      "comment": "123",
                                      "expiry_time": "2022-02-04T14:00:00-05:00",
                                      "snapmirror_label": "321", }], 'num_records': 1}, None),
    'create_response': (200, {'job': {'uuid': 'd0b3eefe-cd59-11eb-a170-005056b338cd',
                                      '_links': {
                                          'self': {'href': '/api/cluster/jobs/d0b3eefe-cd59-11eb-a170-005056b338cd'}}}},
                        None),
    'job_response': (200, {'uuid': 'e43a40db-cd61-11eb-a170-005056b338cd',
                           'description': 'PATCH /api/storage/volumes/d9cd4ec5-c96d-11eb-9271-005056b3ef5a/'
                           'snapshots/da995362-cd61-11eb-a170-005056b338cd',
                           'state': 'success',
                           'message': 'success',
                           'code': 0,
                           'start_time': '2021-06-14T18:43:08-04:00',
                           'end_time': '2021-06-14T18:43:08-04:00',
                           'svm': {'name': 'ansible', 'uuid': 'b663d6f0-c96d-11eb-9271-005056b3ef5a',
                                   '_links': {'self': {'href': '/api/svm/svms/b663d6f0-c96d-11eb-9271-005056b3ef5a'}}},
                           '_links': {'self': {'href': '/api/cluster/jobs/e43a40db-cd61-11eb-a170-005056b338cd'}}},
                     None)
}


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""
    pass


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""
    pass


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

    def __init__(self, kind=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'snapshot':
            xml = self.build_snapshot_info()
        elif self.type == 'snapshot_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_snapshot_info():
        ''' build xml data for snapshot-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1,
                'attributes-list': {'snapshot-info': {'comment': 'new comment',
                                                      'name': 'ansible',
                                                      'snapmirror-label': 'label12'}}}
        xml.translate_struct(data)
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
        self.onbox = False

    def set_default_args(self):
        if self.onbox:
            hostname = '10.193.75.3'
            username = 'admin'
            password = 'netapp1!'
            vserver = 'ansible'
            volume = 'ansible'
            snapshot = 'ansible'
            comment = 'new comment'
            snapmirror_label = 'label12'
        else:
            hostname = 'hostname'
            username = 'username'
            password = 'password'
            vserver = 'vserver'
            volume = 'ansible'
            snapshot = 'ansible'
            comment = 'new comment'
            snapmirror_label = 'label12'
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'vserver': vserver,
            'volume': volume,
            'snapshot': snapshot,
            'comment': comment,
            'snapmirror_label': snapmirror_label
        })

    def set_rest_args(self):
        return dict(
            {
                'state': 'present',
                'hostname': 'hostname',
                'username': 'username',
                'password': 'password',
                'vserver': 'vserver',
                'comment': 'test comment',
                'snapshot': 'test_snapshot',
                'snapmirror_label': 'test_label',
                'volume': 'test_vol'
            }
        )

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_snapshot()  for non-existent snapshot'''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = self.server
        assert my_obj.get_snapshot() is None

    def test_ensure_get_called_existing(self):
        ''' test get_snapshot()  for existing snapshot'''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = MockONTAPConnection(kind='snapshot')
        assert my_obj.get_snapshot()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapshot.NetAppOntapSnapshot.create_snapshot')
    def test_successful_create(self, create_snapshot):
        ''' creating snapshot and testing idempotency '''
        set_module_args(self.set_default_args())
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        create_snapshot.assert_called_with(volume_id=None)
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapshot')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapshot.NetAppOntapSnapshot.modify_snapshot')
    def test_successful_modify(self, modify_snapshot):
        ''' modifying snapshot and testing idempotency '''
        data = self.set_default_args()
        data['comment'] = 'adding comment'
        data['snapmirror_label'] = 'label22'
        set_module_args(data)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapshot')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        modify_snapshot.assert_called_with(uuid=None, volume_id=None)
        # to reset na_helper from remembering the previous 'changed' value
        data['comment'] = 'new comment'
        data['snapmirror_label'] = 'label12'
        set_module_args(data)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapshot')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snapshot.NetAppOntapSnapshot.delete_snapshot')
    def test_successful_delete(self, delete_snapshot):
        ''' deleting snapshot and testing idempotency '''
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapshot')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        delete_snapshot.assert_called_with(uuid=None, volume_id=None)
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('snapshot_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_snapshot()
        assert 'Error creating snapshot ansible:' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.delete_snapshot()
        assert 'Error deleting snapshot ansible:' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_snapshot()
        assert 'Error modifying snapshot ansible:' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_create(self, mock_request):
        data = self.set_rest_args()
        data['state'] = 'present'
        data['use_rest'] = 'Always'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['empty_good'],
            SRR['volume_uuid'],
            SRR['empty_good'],  # get
            SRR['create_response'],
            SRR['job_response'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            my_module().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_successfully_modify(self, mock_request):
        data = self.set_rest_args()
        data['state'] = 'present'
        data['use_rest'] = 'Always'
        data['comment'] = 'new comment'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['empty_good'],
            SRR['volume_uuid'],
            SRR['snapshot_record'],  # get
            SRR['create_response'],  # modify
            SRR['job_response'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            my_module().apply()
        assert exc.value.args[0]['changed']
