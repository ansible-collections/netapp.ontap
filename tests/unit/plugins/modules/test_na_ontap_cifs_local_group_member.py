''' unit tests ONTAP Ansible module: na_ontap_cifs_local_group_member '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_group_member \
    import NetAppOntapCifsLocalGroupMember as group_member_module  # module under test


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
    'group_member_record': (200, {
        "records": [{
            'vserver': 'ansible',
            'group_name': 'BUILTIN\\Guests',
            'member': 'test'
        }]
    }, None)
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
        if self.type == 'group_member':
            xml = self.build_group_member_info()
        elif self.type == 'group_member_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_group_member_info():
        ''' build xml data for cifs-local-group-members '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'attributes-list': {'cifs-local-group-members': {'group-name': 'BUILTIN\\GUESTS', 'member': 'test', 'vserver': 'ansible'}}}
        xml.translate_struct(data)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.server = MockONTAPConnection()
        self.onbox = False

    def set_default_args(self, use_rest=None):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'ansible'
            group = 'BUILTIN\\Guests'
            member = 'test'

        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'ansible'
            group = 'BUILTIN\\Guests'
            member = 'test'

        args = dict({
            'state': 'present',
            'hostname': hostname,
            'username': username,
            'password': password,
            'vserver': vserver,
            'group': group,
            'member': member
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_group_member_mock_object(cx_type='zapi', kind=None):
        group_member_obj = group_member_module()
        if cx_type == 'zapi':
            if kind is None:
                group_member_obj.server = MockONTAPConnection()
            else:
                group_member_obj.server = MockONTAPConnection(kind=kind)
        return group_member_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            group_member_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called(self):
        ''' test get_cifs_local_group_member for non-existent config'''
        set_module_args(self.set_default_args(use_rest='Never'))
        print('starting')
        my_obj = group_member_module()
        print('use_rest:', my_obj.use_rest)
        my_obj.server = self.server
        assert my_obj.get_cifs_local_group_member is not None

    def test_ensure_get_called_existing(self):
        ''' test get_cifs_local_group_member for existing config'''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = group_member_module()
        my_obj.server = MockONTAPConnection(kind='group_member')
        assert my_obj.get_cifs_local_group_member()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_group_member.NetAppOntapCifsLocalGroupMember.add_cifs_local_group_member')
    def test_successful_create(self, add_cifs_local_group_member):
        ''' adding member to local-group and testing idempotency '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = group_member_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        add_cifs_local_group_member.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = group_member_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('group_member')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_group_member.NetAppOntapCifsLocalGroupMember.remove_cifs_local_group_member')
    def test_successful_delete(self, remove_cifs_local_group_member):
        ''' removing member from local-group and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = group_member_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('group_member')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # remove_cifs_local_group_member.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = group_member_module()
        if not self.onbox:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = group_member_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('group_member_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.add_cifs_local_group_member()
        assert 'Error adding member ' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.remove_cifs_local_group_member()
        assert 'Error removing member ' in exc.value.args[0]['msg']

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
            self.get_group_member_mock_object(cx_type='rest').apply()
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
            self.get_group_member_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_create_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['group_member_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_group_member_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_delete_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['group_member_record'],  # get
            SRR['empty_good'],  # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_group_member_mock_object(cx_type='rest').apply()
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
            self.get_group_member_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']
