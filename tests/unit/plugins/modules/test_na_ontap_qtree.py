''' unit tests ONTAP Ansible module: na_ontap_quotas '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_qtree \
    import NetAppOntapQTree as qtree_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Ooops, the UT needs one more SRR response"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'qtree_record': (200,
                     {"records": [{"svm": {"uuid": "09e9fd5e-8ebd-11e9-b162-005056b39fe7",
                                           "name": "ansibleSVM"},
                                   "id": 1,
                                   "name": "string",
                                   "security_style": "unix",
                                   "unix_permissions": "abc",
                                   "export_policy": {"name": "ansible"},
                                   "volume": {"name": "volume1",
                                              "uuid": "028baa66-41bd-11e9-81d5-00a0986138f7"}}]}, None)
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

    def __init__(self, kind=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'qtree':
            xml = self.build_quota_info()
        elif self.type == 'qtree_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_quota_info():
        ''' build xml data for quota-entry '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1,
                'attributes-list': {'qtree-info': {'export-policy': 'ansible', 'vserver': 'ansible', 'qtree': 'ansible',
                                                   'oplocks': 'enabled', 'security-style': 'unix', 'mode': 'abc',
                                                   'volume': 'ansible'}}}
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

    def set_default_args(self, use_rest=None):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            name = 'ansible'
            vserver = 'ansible'
            flexvol_name = 'ansible'
            export_policy = 'ansible'
            security_style = 'unix'
            mode = 'abc'
        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            name = 'ansible'
            vserver = 'ansible'
            flexvol_name = 'ansible'
            export_policy = 'ansible'
            security_style = 'unix'
            mode = 'abc'

        args = dict({
            'state': 'present',
            'hostname': hostname,
            'username': username,
            'password': password,
            'name': name,
            'vserver': vserver,
            'flexvol_name': flexvol_name,
            'export_policy': export_policy,
            'security_style': security_style,
            'unix_permissions': mode
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_qtree_mock_object(cx_type='zapi', kind=None):
        qtree_obj = qtree_module()
        if cx_type == 'zapi':
            if kind is None:
                qtree_obj.server = MockONTAPConnection()
            else:
                qtree_obj.server = MockONTAPConnection(kind=kind)
        return qtree_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            qtree_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_qtree for non-existent qtree'''
        set_module_args(self.set_default_args(use_rest='Never'))
        print('starting')
        my_obj = qtree_module()
        print('use_rest:', my_obj.use_rest)
        my_obj.server = self.server
        assert my_obj.get_qtree is not None

    def test_ensure_get_called_existing(self):
        ''' test get_qtree for existing qtree'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = qtree_module()
        my_obj.server = MockONTAPConnection(kind='qtree')
        assert my_obj.get_qtree()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_qtree.NetAppOntapQTree.create_qtree')
    def test_successful_create(self, create_qtree):
        ''' creating qtree and testing idempotency '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = qtree_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        create_qtree.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = qtree_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('qtree')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_qtree.NetAppOntapQTree.delete_qtree')
    def test_successful_delete(self, delete_qtree):
        ''' deleting qtree and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = qtree_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('qtree')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # delete_qtree.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = qtree_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_qtree.NetAppOntapQTree.modify_qtree')
    def test_successful_modify(self, modify_qtree):
        ''' modifying qtree and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['export_policy'] = 'test'
        set_module_args(data)
        my_obj = qtree_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('qtree')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # modify_qtree.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        data['export_policy'] = 'ansible'
        set_module_args(data)
        my_obj = qtree_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('qtree')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_qtree.NetAppOntapQTree.get_qtree')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_qtree.NetAppOntapQTree.rename_qtree')
    def test_failed_rename(self, rename_qtree, get_qtree):
        ''' creating qtree and testing idempotency '''
        get_qtree.side_effect = [None, None]
        data = self.set_default_args(use_rest='Never')
        data['from_name'] = 'ansible_old'
        set_module_args(data)
        my_obj = qtree_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = 'Error renaming: qtree %s does not exist' % data['from_name']
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_qtree.NetAppOntapQTree.get_qtree')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_qtree.NetAppOntapQTree.rename_qtree')
    def test_successful_rename(self, rename_qtree, get_qtree):
        ''' creating qtree and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['from_name'] = 'ansible_old'
        qtree = dict(
            security_style=data['security_style'],
            unix_permissions=data['unix_permissions'],
            export_policy=data['export_policy']
        )
        get_qtree.side_effect = [None, qtree]
        set_module_args(data)
        my_obj = qtree_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        rename_qtree.assert_called_with(qtree)
        # Idempotency
        get_qtree.side_effect = [qtree, 'whatever']
        my_obj = qtree_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('qtree')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        data['from_name'] = 'ansible'
        set_module_args(data)
        my_obj = qtree_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('qtree_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_qtree()
        assert 'Error provisioning qtree ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.delete_qtree(self.get_qtree_mock_object())
        assert 'Error deleting qtree ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_qtree(self.get_qtree_mock_object())
        assert 'Error modifying qtree ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.rename_qtree(self.get_qtree_mock_object())
        assert 'Error renaming qtree ' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_qtree_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['msg'] == SRR['generic_error'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_create_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # get
            SRR['empty_good'],  # post
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_qtree_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_create_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['qtree_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_qtree_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_delete_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['qtree_record'],  # get
            SRR['empty_good'],  # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_qtree_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_delete_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_qtree_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['unix_permissions'] = 'abcde'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['qtree_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_qtree_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['qtree_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_qtree_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_rename_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['from_name'] = 'abcde'
        # data['unix_permissions'] = 'abcde'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],    # get (current)
            SRR['qtree_record'],  # get (from)
            SRR['empty_good'],    # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_qtree_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_rename_rest_idempotent(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['from_name'] = 'abcde'
        # data['unix_permissions'] = 'abcde'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['qtree_record'],  # get (current exists)
            SRR['empty_good'],    # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_qtree_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_rename_and_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['from_name'] = 'abcde'
        data['unix_permissions'] = 'abcde'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],    # get (current)
            SRR['qtree_record'],  # get (from)
            SRR['empty_good'],    # patch (rename)
            SRR['empty_good'],    # patch (modify)
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_qtree_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']
