# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_lun_copy \
    import NetAppOntapLUNCopy as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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
        if self.type == 'destination_vserver':
            xml = self.build_lun_info()
        self.xml_out = xml
        return xml

    @staticmethod
    def build_lun_info():
        ''' build xml data for lun-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'num-records': 1,
        }
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_lun_copy = {
            'source_vserver': 'ansible',
            'destination_path': '/vol/test/test_copy_dest_dest_new_reviewd_new',
            'source_path': '/vol/test/test_copy_1',
            'destination_vserver': 'ansible',
            'state': 'present'
        }

    def mock_args(self):

        return {
            'source_vserver': self.mock_lun_copy['source_vserver'],
            'destination_path': self.mock_lun_copy['destination_path'],
            'source_path': self.mock_lun_copy['source_path'],
            'destination_vserver': self.mock_lun_copy['destination_vserver'],
            'state': self.mock_lun_copy['state'],
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
        }
        # self.server = MockONTAPConnection()

    def get_lun_copy_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_lun_copy object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_interface object
        """
        lun_copy_obj = my_module()
        lun_copy_obj.autosupport_log = Mock(return_value=None)
        if kind is None:
            lun_copy_obj.server = MockONTAPConnection()
        else:
            lun_copy_obj.server = MockONTAPConnection(kind=kind)
        return lun_copy_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_create_error_missing_param(self):
        ''' Test if create throws an error if required param 'destination_vserver' is not specified'''
        data = self.mock_args()
        del data['destination_vserver']
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_copy_mock_object('lun_copy').copy_lun()
        msg = 'missing required arguments: destination_vserver'
        assert msg == exc.value.args[0]['msg']

    def test_successful_copy(self):
        ''' Test successful create '''
        # data = self.mock_args()
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_copy_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_copy_idempotency(self):
        ''' Test create idempotency '''
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_copy_mock_object('destination_vserver').apply()
        assert not exc.value.args[0]['changed']
