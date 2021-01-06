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

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_lun \
    import NetAppOntapLUN as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
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
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_mock_object().apply()
        msg = 'size is a required parameter for create.'
        assert msg == exc.value.args[0]['msg']

    def test_successful_create(self):
        ''' Test successful create '''
        data = dict(self.mock_args())
        data['size'] = 5
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object().apply()
        assert exc.value.args[0]['changed']

    def test_create_rename_idempotency(self):
        ''' Test create idempotency '''
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object('lun', 'lun_name').apply()
        assert not exc.value.args[0]['changed']

    def test_successful_rename(self):
        ''' Test successful create '''
        data = dict(self.mock_args())
        data['from_name'] = 'lun_from_name'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_lun_mock_object('lun', 'lun_from_name').apply()
        assert exc.value.args[0]['changed']
        assert 'lun_rename' in exc.value.args[0]['actions']

    def test_failed_rename(self):
        ''' Test failed rename '''
        data = dict(self.mock_args())
        data['from_name'] = 'lun_from_name'
        set_module_args(data)
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_lun_mock_object('lun', 'other_lun_name').apply()
        msg = 'Error renaming lun: lun_from_name does not exist'
        assert msg == exc.value.args[0]['msg']
