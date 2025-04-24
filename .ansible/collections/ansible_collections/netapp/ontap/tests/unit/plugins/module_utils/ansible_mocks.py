# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import json
import pytest
import sys
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import ZAPI_DEPRECATION_MESSAGE

VERBOSE = True

if sys.version_info < (3, 11):
    pytestmark = pytest.mark.skip("Skipping Unit Tests on 3.11")


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


WARNINGS = []


def warn(dummy, msg):
    print('WARNING:', msg)
    WARNINGS.append(msg)


def expect_and_capture_ansible_exception(function, exception, *args, **kwargs):
    ''' wraps a call to a funtion in a pytest.raises context and return the exception data as a dict

        function:  the function to call -- without ()
        exception: 'exit' or 'fail' to trap Ansible exceptions raised by exit_json or fail_json
                   can also take an exception to test some corner cases (eg KeyError)
        *args, **kwargs  to capture any function arguments
    '''
    if exception in ('fail', 'exit'):
        exception = AnsibleFailJson if exception == 'fail' else AnsibleExitJson
    if not (isinstance(exception, type) and issubclass(exception, Exception)):
        raise KeyError('Error: got: %s, expecting fail, exit, or some exception' % exception)
    with pytest.raises(exception) as exc:
        function(*args, **kwargs)
    if VERBOSE:
        print('EXC:', exception, exc.value)
    if exception in (AnsibleExitJson, AnsibleFailJson, Exception, AttributeError, KeyError, TypeError, ValueError):
        return exc.value.args[0]
    return exc


def call_main(my_main, default_args=None, module_args=None, fail=False):
    ''' utility function to call a module main() entry point
        my_main: main function for a module
        default_args: a dict for the Ansible options - in general, what is accepted by all tests
        module_args: additional options - in general what is specific to a test

        call main and should raise AnsibleExitJson or AnsibleFailJson
    '''
    args = copy.deepcopy(default_args) if default_args else {}
    if module_args:
        args.update(module_args)
    set_module_args(args)
    return expect_and_capture_ansible_exception(my_main, 'fail' if fail else 'exit')


def create_module(my_module, default_args=None, module_args=None, check_mode=None, fail=False):
    ''' utility function to create a module object
        my_module: a class that represent an ONTAP Ansible module
        default_args: a dict for the Ansible options - in general, what is accepted by all tests
        module_args: additional options - in general what is specific to a test
        check_mode: True/False - if not None, check_mode is set accordingly

        returns an instance of the module
    '''
    args = copy.deepcopy(default_args) if default_args else {}
    if module_args:
        args.update(module_args)
    set_module_args(args)
    if fail:
        return expect_and_capture_ansible_exception(my_module, 'fail')
    my_module_object = my_module()
    if check_mode is not None:
        my_module_object.module.check_mode = check_mode
    return my_module_object


def create_and_apply(my_module, default_args=None, module_args=None, fail=False, check_mode=None):
    ''' utility function to create a module and call apply

        calls create_module, then calls the apply function and checks for:
             AnsibleExitJson exception if fail is False or not present.
             AnsibleFailJson exception if fail is True.

        see create_module for a description of the other arguments.
    '''
    try:
        my_obj = create_module(my_module, default_args, module_args, check_mode)
    except Exception as exc:
        print('Unexpected exception returned in create_module: %s' % exc)
        print('If expected, use create_module with fail=True.')
        raise
    return expect_and_capture_ansible_exception(my_obj.apply, 'fail' if fail else 'exit')


# using pytest natively, without unittest.TestCase
@pytest.fixture(autouse=True)
def patch_ansible():
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json,
                        warn=warn) as mocks:
        clear_warnings()
        # so that we get a SystemExit: 1 error (no able to read from stdin in ansible-test !)
        # if set_module_args() was not called
        basic._ANSIBLE_ARGS = None
        yield mocks


def get_warnings():
    return WARNINGS


def print_warnings(framed=True):
    if framed:
        sep = '-' * 7
        title = ' WARNINGS '
        print(sep, title, sep)
    for warning in WARNINGS:
        print(warning)
    if framed:
        sep = '-' * (7 * 2 + len(title))
        print(sep)


def assert_no_warnings():
    assert not WARNINGS


def assert_no_warnings_except_zapi():
    # Deprecation message can appear more than once. Remove will only remove the first instance.
    local_warning = list(set(WARNINGS))
    tmp_warnings = local_warning[:]
    for warning in tmp_warnings:
        if warning in ZAPI_DEPRECATION_MESSAGE:
            local_warning.remove(ZAPI_DEPRECATION_MESSAGE)
    assert not local_warning


def assert_warning_was_raised(warning, partial_match=False):
    if partial_match:
        assert any(warning in msg for msg in WARNINGS)
    else:
        assert warning in WARNINGS


def clear_warnings():
    global WARNINGS
    WARNINGS = []
