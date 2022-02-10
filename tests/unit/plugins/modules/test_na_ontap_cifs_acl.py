# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_cifs_acl """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleExitJson, AnsibleFailJson, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses, get_mock_record
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_acl \
    import NetAppONTAPCifsAcl as my_module, main as my_main     # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


SHARE_NAME = 'share_name'

acl_info = {'num-records': 1,
            'attributes-list':
                {'cifs-share-access-control':
                    {'share': SHARE_NAME,
                     'user-or-group': 'user123',
                     'permission': 'full_control',
                     'user-group-type': 'windows'
                     }
                 },
            }

ZRR = zapi_responses({
    'acl_info': build_zapi_response(acl_info),
})


def set_default_args():
    return {
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'permission': 'full_control',
        'share_name': 'share_name',
        'user_or_group': 'user_or_group',
        'vserver': 'vserver',
        'use_rest': 'never',
    }


VERBOSE = True


def expect_and_capture_ansible_exception(function, exception, *args, **kwargs):
    ''' wraps a call to a funtion in a pytest.raises context and return the exception data as a dict

        function: the function to call -- without ()
        mode: 'exit' or 'fail' to trap Ansible exceptions raised by exit_json or fail_json
              can also take an exception to test soem corner cases (eg KeyError)
        *args, **kwargs  to capture any function arguments
    '''
    if exception in ('fail', 'exit'):
        exception = AnsibleFailJson if exception == 'fail' else AnsibleExitJson
    if not (isinstance(exception, type) and issubclass(exception, Exception)):
        raise KeyError('Error: got: %s, expecting fail, exit, or some exception' % exception)
    with pytest.raises(exception) as exc:
        function(*args, **kwargs)
    if VERBOSE:
        print('EXC:', exception, exc.value.args[0])
    return exc.value.args[0]


def create_module(module_args=None, use_default_args=True):
    ''' utility function to create a module object '''
    args = dict(set_default_args()) if use_default_args else {}
    if module_args:
        args.update(module_args)
    set_module_args(args)
    return my_module()


def create_and_apply(module_args, fail=False):
    ''' utility function to create a module and call apply '''
    my_obj = create_module(module_args)
    return expect_and_capture_ansible_exception(my_obj.apply, 'fail' if fail else 'exit')


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    msg = 'missing required arguments: hostname, share_name, user_or_group, vserver'
    assert expect_and_capture_ansible_exception(create_module, 'fail', use_default_args=False)['msg'] == msg


def test_create():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['empty']),
        ('cifs-share-access-control-create', ZRR['success']),
    ])
    module_args = {
    }
    assert create_and_apply(module_args)['changed']


def test_create_with_type():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['empty']),
        ('cifs-share-access-control-create', ZRR['success']),
    ])
    module_args = {
        'type': 'unix_group'
    }
    assert create_and_apply(module_args)['changed']


def test_delete():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['acl_info']),
        ('cifs-share-access-control-delete', ZRR['success']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(module_args)['changed']


def test_delete_idempotent():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['empty']),
    ])
    module_args = {
        'state': 'absent'
    }
    assert not create_and_apply(module_args)['changed']


def test_modify():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['acl_info']),
        ('cifs-share-access-control-modify', ZRR['success']),
    ])
    module_args = {
        'permission': 'no_access',
        'type': 'windows'
    }
    assert create_and_apply(module_args)['changed']


def test_create_modify_idempotent():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['acl_info']),
    ])
    module_args = {
        'permission': 'full_control',
        'type': 'windows'
    }
    assert not create_and_apply(module_args)['changed']


def test_negative_modify_with_type():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['acl_info']),
    ])
    module_args = {
        'type': 'unix_group'
    }
    msg = create_and_apply(module_args, fail=True)['msg']
    assert msg == 'Error: changing the type is not supported by ONTAP - current: windows, desired: unix_group'


def test_negative_modify_with_extra_stuff():
    register_responses([
    ])
    my_module = create_module()
    current = {'share_name': 'extra'}
    msg = "Error: only permission can be changed - modify: {'share_name': 'share_name'}"
    assert msg in expect_and_capture_ansible_exception(my_module.get_modify, 'fail', current)['msg']

    current = {'share_name': 'extra', 'permission': 'permission'}
    # don't check dict contents as order may differ
    msg = "Error: only permission can be changed - modify:"
    assert msg in expect_and_capture_ansible_exception(my_module.get_modify, 'fail', current)['msg']


def test_if_all_methods_catch_exception():
    register_responses([
        ('cifs-share-access-control-get-iter', ZRR['error']),
        ('cifs-share-access-control-create', ZRR['error']),
        ('cifs-share-access-control-modify', ZRR['error']),
        ('cifs-share-access-control-delete', ZRR['error']),
    ])
    my_module = create_module()

    msg = 'Error getting cifs-share-access-control share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg in expect_and_capture_ansible_exception(my_module.get_cifs_acl, 'fail')['msg']

    msg = 'Error creating cifs-share-access-control share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg in expect_and_capture_ansible_exception(my_module.create_cifs_acl, 'fail')['msg']

    msg = 'Error modifying cifs-share-access-control permission share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg in expect_and_capture_ansible_exception(my_module.modify_cifs_acl_permission, 'fail')['msg']

    msg = 'Error deleting cifs-share-access-control share_name: NetApp API failed. Reason - 12345:synthetic error for UT purpose'
    assert msg in expect_and_capture_ansible_exception(my_module.delete_cifs_acl, 'fail')['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_missing_netapp_lib(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    with pytest.raises(AnsibleFailJson) as exc:
        create_module({})
    msg = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert msg == exc.value.args[0]['msg']


def test_main():
    register_responses([
        ('ems-autosupport-log', ZRR['success']),
        ('cifs-share-access-control-get-iter', ZRR['empty']),
        ('cifs-share-access-control-create', ZRR['success']),
    ])
    set_module_args(set_default_args())
    assert expect_and_capture_ansible_exception(my_main, 'exit')['changed']
