# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP Command Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_command \
    import NetAppONTAPCommand as my_module  # module under test

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

    def __init__(self, kind=None, parm1=None):
        ''' save arguments '''
        self.type = kind
        self.parm1 = parm1
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        # print(xml.to_string())

        if self.type == 'version':
            priv = xml.get_child_content('priv')
            xml = self.build_version(priv, self.parm1)

        self.xml_out = xml
        return xml

    @staticmethod
    def build_version(priv, result):
        ''' build xml data for version '''
        prefix = 'NetApp Release'
        if priv == 'advanced':
            prefix = '\n' + prefix
        xml = netapp_utils.zapi.NaElement('results')
        xml.add_attr('status', 'status_ok')
        xml.add_new_child('cli-output', prefix)
        if result == "u'77'":
            xml.add_new_child('cli-result-value', u'77')
        elif result == "b'77'":
            xml.add_new_child('cli-result-value', b'77')
        else:
            xml.add_new_child('cli-result-value', b'7' if result is None else result)
        # print('XML ut:', xml.to_string())
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.server = MockONTAPConnection(kind='version')
        # whether to use a mock or a simulator
        self.use_vsim = False

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    @staticmethod
    def set_default_args(vsim=False):
        ''' populate hostname/username/password '''
        if vsim:
            hostname = '10.10.10.10'
            username = 'admin'
            password = 'admin'
        else:
            hostname = 'hostname'
            username = 'username'
            password = 'password'
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'https': True,
            'validate_certs': False
        })

    def call_command(self, module_args, vsim=False):
        ''' utility function to call apply '''
        module_args.update(self.set_default_args(vsim=vsim))
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        if not vsim:
            # mock the connection
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        msg = exc.value.args[0]['msg']
        return msg

    def test_default_priv(self):
        ''' make sure privilege is not required '''
        module_args = {
            'command': 'version',
        }
        msg = self.call_command(module_args, vsim=self.use_vsim)
        needle = b'<cli-output>NetApp Release'
        assert needle in msg
        print('Version (raw): %s' % msg)

    def test_admin_priv(self):
        ''' make sure admin is accepted '''
        module_args = {
            'command': 'version',
            'privilege': 'admin',
        }
        msg = self.call_command(module_args, vsim=self.use_vsim)
        needle = b'<cli-output>NetApp Release'
        assert needle in msg
        print('Version (raw): %s' % msg)

    def test_advanced_priv(self):
        ''' make sure advanced is not required '''
        module_args = {
            'command': 'version',
            'privilege': 'advanced',
        }
        msg = self.call_command(module_args, vsim=self.use_vsim)
        # Interestingly, the ZAPI returns a slightly different response
        needle = b'<cli-output>\nNetApp Release'
        assert needle in msg
        print('Version (raw): %s' % msg)

    def get_dict_output(self, result):
        ''' get result value after calling command module  '''
        print('In:', result)
        module_args = {
            'command': 'version',
            'return_dict': 'true',
        }
        self.server = MockONTAPConnection(kind='version', parm1=result)
        dict_output = self.call_command(module_args, vsim=self.use_vsim)
        print('dict_output: %s' % repr(dict_output))
        return dict_output['result_value']

    def test_dict_output_77(self):
        ''' make sure correct value is returned '''
        result = '77'
        assert self.get_dict_output(result) == int(result)

    def test_dict_output_b77(self):
        ''' make sure correct value is returned '''
        result = b'77'
        assert self.get_dict_output(result) == int(result)

    def test_dict_output_u77(self):
        ''' make sure correct value is returned '''
        result = "u'77'"
        assert self.get_dict_output(result) == int(eval(result))
