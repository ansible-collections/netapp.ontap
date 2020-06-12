# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_ucadapter '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_ucadapter \
    import NetAppOntapadapter as ucadapter_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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

    def __init__(self, kind=None, data=None):
        ''' save arguments '''
        self.type = kind
        self.parm1 = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'ucadapter':
            xml = self.build_ucadapter_info(self.parm1)
        self.xml_out = xml
        return xml

    def autosupport_log(self):
        ''' mock autosupport log'''
        return None

    @staticmethod
    def build_ucadapter_info(params):
        ''' build xml data for ucadapter_info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'attributes': {'uc-adapter-info': {
            'mode': 'fc',
            'pending-mode': 'abc',
            'type': 'target',
            'pending-type': 'intitiator',
            'status': params['status'],
        }}}
        xml.translate_struct(data)
        print(xml.to_string())
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
        self.use_vsim = False
        self.mock_ucadapter = {
            'mode': 'fc',
            'pending-mode': 'fc',
            'type': 'target',
            'pending-type': 'intitiator',
            'status': 'up',
        }

    def set_default_args(self):
        args = (dict({
            'hostname': '10.0.0.0',
            'username': 'user',
            'password': 'pass',
            'node_name': 'node1',
            'adapter_name': '0f',
            'mode': self.mock_ucadapter['mode'],
            'type': self.mock_ucadapter['type']
        }))
        return args

    def get_ucadapter_mock_object(self, kind=None, data=None):
        """
        Helper method to return an na_ontap_unix_user object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_unix_user object
        """
        obj = ucadapter_module()
        obj.autosupport_log = Mock(return_value=None)
        params = self.mock_ucadapter
        if data is not None:
            for k, v in data.items():
                params[k] = v
        obj.server = MockONTAPConnection(kind=kind, data=params)
        return obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            ucadapter_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_ucadapter_get_called(self):
        ''' fetching ucadapter details '''
        set_module_args(self.set_default_args())
        get_adapter = self.get_ucadapter_mock_object().get_adapter()
        print('Info: test_ucadapter_get: %s' % repr(get_adapter))
        assert get_adapter is None

    def test_change_mode_from_cna_to_fc(self):
        ''' configuring ucadaptor and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ucadapter_mock_object().apply()
        assert not exc.value.args[0]['changed']
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ucadapter_mock_object('ucadapter', {'mode': 'cna', 'pending-mode': 'cna'}).apply()
        assert exc.value.args[0]['changed']

        module_args['type'] = 'intitiator'
        set_module_args(module_args)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ucadapter_mock_object('ucadapter', {'mode': 'cna', 'pending-mode': 'cna'}).apply()
        assert exc.value.args[0]['changed']

    def test_change_mode_from_fc_to_cna(self):
        module_args = self.set_default_args()
        module_args['mode'] = 'cna'
        del module_args['type']
        set_module_args(module_args)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_ucadapter_mock_object('ucadapter').apply()
        assert exc.value.args[0]['changed']
