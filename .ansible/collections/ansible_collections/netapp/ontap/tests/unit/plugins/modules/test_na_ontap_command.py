# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP Command Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_error_message, zapi_responses
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    call_main, create_module, expect_and_capture_ansible_exception, patch_ansible


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_command import NetAppONTAPCommand as my_module, main as my_main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'use_rest': 'use_rest',
}


def cli_output(priv, result, translate=True):
    prefix = 'NetApp Release'
    print('HERE', 'start')
    if priv == 'advanced':
        prefix = '\n' + prefix
    if result == "u'77'":
        result = u'77'
    elif result == "b'77'":
        print('HERE', b'77')
        result = b'77'
    elif result is None:
        result = b'7'
    return {
        'cli-output': prefix,
        'cli-result-value': result
    }


def build_zapi_response_raw(contents):
    """ when testing special encodings, we cannot use build_zapi_response as translate_struct converts to text
    """
    if netapp_utils.has_netapp_lib():
        xml = netapp_utils.zapi.NaElement('results')
        xml.add_attr('status', 'status_ok')
        xml.add_new_child('cli-output', contents['cli-output'])
        xml.add_new_child('cli-result-value', contents['cli-result-value'])
        # print('XML ut:', xml.to_string())
        xml.add_attr('status', 'passed')
        return (xml, 'valid')
    return ('netapp-lib is required', 'invalid')


ZRR = zapi_responses({
    'cli_version': build_zapi_response_raw(cli_output(None, None)),
    'cli_version_advanced': build_zapi_response_raw(cli_output('advanced', None)),
    'cli_version_77': build_zapi_response(cli_output(None, '77')),
    'cli_version_b77': build_zapi_response_raw(cli_output(None, "b'77'")),
    'cli_version_u77': build_zapi_response_raw(cli_output(None, "u'77'")),
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    register_responses([
    ])
    module_args = {
    }
    error = 'missing required arguments: command'
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_default_priv():
    ''' make sure privilege is not required '''
    register_responses([
        ('ZAPI', 'system-cli', ZRR['cli_version']),
    ])
    module_args = {
        'command': 'version',
    }
    msg = call_main(my_main, DEFAULT_ARGS, module_args)['msg']
    needle = b'<cli-output>NetApp Release'
    assert needle in msg
    print('Version (raw): %s' % msg)


def test_admin_priv():
    ''' make sure admin is accepted '''
    register_responses([
        ('ZAPI', 'system-cli', ZRR['cli_version']),
    ])
    module_args = {
        'command': 'version',
        'privilege': 'admin',
    }
    msg = call_main(my_main, DEFAULT_ARGS, module_args)['msg']
    needle = b'<cli-output>NetApp Release'
    assert needle in msg
    print('Version (raw): %s' % msg)


def test_advanced_priv():
    ''' make sure advanced is not required '''
    register_responses([
        ('ZAPI', 'system-cli', ZRR['cli_version_advanced']),
    ])
    module_args = {
        'command': 'version',
        'privilege': 'advanced',
    }
    msg = call_main(my_main, DEFAULT_ARGS, module_args)['msg']
    # Interestingly, the ZAPI returns a slightly different response
    needle = b'<cli-output>\nNetApp Release'
    assert needle in msg
    print('Version (raw): %s' % msg)


def get_dict_output(extra_args=None):
    ''' get result value after calling command module  '''
    module_args = {
        'command': 'version',
        'return_dict': 'true',
    }
    if extra_args:
        module_args.update(extra_args)
    dict_output = call_main(my_main, DEFAULT_ARGS, module_args)['msg']
    print('dict_output: %s' % repr(dict_output))
    return dict_output


def test_dict_output_77():
    ''' make sure correct value is returned '''
    register_responses([
        ('ZAPI', 'system-cli', ZRR['cli_version_77']),
    ])
    result = '77'
    assert get_dict_output()['result_value'] == int(result)


def test_dict_output_b77():
    ''' make sure correct value is returned '''
    register_responses([
        ('ZAPI', 'system-cli', ZRR['cli_version_b77']),
    ])
    result = b'77'
    assert get_dict_output()['result_value'] == int(result)


def test_dict_output_u77():
    ''' make sure correct value is returned '''
    register_responses([
        ('ZAPI', 'system-cli', ZRR['cli_version_u77']),
    ])
    result = "u'77'"
    assert get_dict_output()['result_value'] == int(eval(result))


def test_dict_output_exclude():
    ''' make sure correct value is returned '''
    register_responses([
        ('ZAPI', 'system-cli', ZRR['cli_version']),
        ('ZAPI', 'system-cli', ZRR['cli_version']),
    ])
    dict_output = get_dict_output({'exclude_lines': 'NetApp Release'})
    assert len(dict_output['stdout_lines']) == 1
    assert len(dict_output['stdout_lines_filter']) == 0
    dict_output = get_dict_output({'exclude_lines': 'whatever'})
    assert len(dict_output['stdout_lines']) == 1
    assert len(dict_output['stdout_lines_filter']) == 1


def test_dict_output_include():
    ''' make sure correct value is returned '''
    register_responses([
        ('ZAPI', 'system-cli', ZRR['cli_version']),
        ('ZAPI', 'system-cli', ZRR['cli_version']),
    ])
    dict_output = get_dict_output({'include_lines': 'NetApp Release'})
    assert len(dict_output['stdout_lines']) == 1
    assert len(dict_output['stdout_lines_filter']) == 1
    dict_output = get_dict_output({'include_lines': 'whatever'})
    assert len(dict_output['stdout_lines']) == 1
    assert len(dict_output['stdout_lines_filter']) == 0


def test_check_mode():
    ''' make sure nothing is done '''
    register_responses([
    ])
    module_args = {
        'command': 'version',
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    my_obj.module.check_mode = True
    msg = expect_and_capture_ansible_exception(my_obj.apply, 'exit')['msg']
    needle = "Would run command: '['version']'"
    assert needle in msg
    print('Version (raw): %s' % msg)


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_missing_netapp_lib(mock_has_netapp_lib):
    module_args = {
        'command': 'version',
    }
    mock_has_netapp_lib.return_value = False
    msg = 'Error: the python NetApp-Lib module is required.  Import error: None'
    assert msg == call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_zapi_errors():
    ''' make sure nothing is done '''
    register_responses([
        ('ZAPI', 'system-cli', ZRR['error']),
        ('ZAPI', 'system-cli', ZRR['cli_version']),
        ('ZAPI', 'system-cli', ZRR['cli_version']),
        ('ZAPI', 'system-cli', ZRR['cli_version']),

    ])
    module_args = {
        'command': 'version',
    }
    error = zapi_error_message("Error running command ['version']")
    assert error in call_main(my_main, DEFAULT_ARGS, module_args, fail=True)['msg']
    # EMS error is ignored
    assert b'NetApp Release' in call_main(my_main, DEFAULT_ARGS, module_args, fail=False)['msg']
    # EMS cserver error is ignored
    assert b'NetApp Release' in call_main(my_main, DEFAULT_ARGS, module_args, fail=False)['msg']
    # EMS vserver error is ignored
    module_args = {
        'command': 'version',
        'vserver': 'svm'
    }
    assert b'NetApp Release' in call_main(my_main, DEFAULT_ARGS, module_args, fail=False)['msg']
