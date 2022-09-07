# (c) 2021-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP disks Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import call_main, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import zapi_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cifs_local_user_set_password import main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


ZRR = zapi_responses({
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'never',
    'user_password': 'test',
    'user_name': 'user1',
    'vserver': 'svm1',
}


def test_successful_set_password(patch_ansible):
    ''' successful set '''
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cifs-local-user-set-password', ZRR['success']),
    ])
    assert call_main(my_main, DEFAULT_ARGS)['changed']


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    error = 'missing required arguments:'
    assert error in call_main(my_main, {}, fail=True)['msg']


def test_if_all_methods_catch_exception(patch_ansible):
    register_responses([
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cifs-local-user-set-password', ZRR['error']),
    ])
    assert 'Error setting password ' in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_netapp_lib_error(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    error = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert error in call_main(my_main, DEFAULT_ARGS, fail=True)['msg']
