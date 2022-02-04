# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP disks Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_user_set_password \
    import NetAppONTAPCifsSetPassword as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


class MockONTAPConnection():
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml


def default_args():
    args = {
        'user_password': 'test',
        'user_name': 'user1',
        'vserver': 'svm1',
        'hostname': '10.10.10.10',
        'username': 'username',
        'password': 'password',
    }
    return args


def test_successful_set_password(patch_ansible):
    ''' successful set '''
    args = dict(default_args())
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection()
    my_obj.ems_log_event = Mock(return_value=None)
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
        print('set: ' + repr(exc.value))
    assert exc.value.args[0]['changed']


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_ensure_get_called(patch_ansible):
    ''' test cifs_local_set_passwd '''
    args = dict(default_args())
    set_module_args(args)
    print('starting')
    my_obj = my_module()
    my_obj.server = MockONTAPConnection()
    my_obj.ems_log_event = Mock(return_value=None)
    assert my_obj.cifs_local_set_passwd is not None


def test_rest_missing_arguments(patch_ansible):     # pylint: disable=redefined-outer-name,unused-argument ##WHAT DOES THIS METHOD DO
    ''' test missing args '''
    args = dict(default_args())
    del args['hostname']
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = 'missing required arguments: hostname'
    assert exc.value.args[0]['msg'] == msg


def test_if_all_methods_catch_exception(patch_ansible):
    args = dict(default_args())
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fail')
    my_obj.ems_log_event = Mock(return_value=None)

    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.cifs_local_set_passwd()
    assert 'Error setting password ' in exc.value.args[0]['msg']
