# (c) 2018, NTT Europe Ltd.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit test for Ansible module: na_ontap_ipspace """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ipspace \
    import NetAppOntapIpspace as my_module  # module under test

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
    'ipspace_record': (200, {'records': [{"name": "test_ipspace",
                                          "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"}]}, None)
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
        if self.type == 'ipspace':
            xml = self.build_ipspace_info(self.parm1)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_ipspace_info(ipspace):
        '''  build xml data for ipspace '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1,
                'attributes-list': {'net-ipspaces-info': {'ipspace': ipspace}}}
        xml.translate_struct(data)
        print(xml.to_string())
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.server = MockONTAPConnection()

    def set_default_args(self):
        return dict({
            'name': 'test_ipspace',
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password'
        })

    @staticmethod
    def get_ipspace_mock_object(cx_type='zapi', kind=None, status=None):
        ipspace_obj = my_module()
        if cx_type == 'zapi':
            if kind is None:
                ipspace_obj.server = MockONTAPConnection()
            else:
                ipspace_obj.server = MockONTAPConnection(kind=kind, parm1=status)
        return ipspace_obj

    def test_fail_requiredargs_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_get_ipspace_iscalled(self, mock_request):
        ''' test if get_ipspace() is called '''
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        set_module_args(self.set_default_args())
        my_obj = my_module()
        my_obj.server = self.server
        ipspace = my_obj.get_ipspace()
        print('Info: test_get_ipspace: %s' % repr(ipspace))
        assert ipspace is None

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_ipspace_apply_iscalled(self, mock_request):
        ''' test if apply() is called '''
        mock_request.side_effect = [
            SRR['is_zapi'],
            SRR['end_of_sequence']
        ]
        module_args = {'name': 'test_apply_ips'}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.server = self.server
        ipspace = my_obj.get_ipspace()
        print('Info: test_get_ipspace: %s' % repr(ipspace))
        assert ipspace is None
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_ipspace_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        my_obj.server = MockONTAPConnection('ipspace', 'test_apply_ips')
        ipspace = my_obj.get_ipspace()
        print('Info: test_get_ipspace: %s' % repr(ipspace))
        assert ipspace is not None
        assert ipspace['name'] == 'test_apply_ips'
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_ipspace_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        ipspace = my_obj.get_ipspace()
        assert ipspace['name'] == 'test_apply_ips'

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
            self.get_ipspace_mock_object(cx_type='rest').apply()
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
            self.get_ipspace_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_create_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['ipspace_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ipspace_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_delete_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['ipspace_record'],  # get
            SRR['empty_good'],  # delete
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ipspace_mock_object(cx_type='rest').apply()
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
            self.get_ipspace_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ipspace_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['ipspace_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ipspace_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']
