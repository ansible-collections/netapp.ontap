# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import json
import pytest
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch

VERBOSE = True


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
    WARNINGS.append(msg)


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


def create_module(my_module, default_args=None, module_args=None):
    ''' utility function to create a module object '''
    args = copy.deepcopy(default_args) if default_args else {}
    if module_args:
        args.update(module_args)
    set_module_args(args)
    return my_module()


def create_and_apply(my_module, default_args=None, module_args=None, fail=False):
    ''' utility function to create a module and call apply '''
    my_obj = create_module(my_module, default_args, module_args)
    return expect_and_capture_ansible_exception(my_obj.apply, 'fail' if fail else 'exit')


# using pytest natively, without unittest.TestCase
@pytest.fixture(autouse=True)
def patch_ansible():
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json,
                        warn=warn) as mocks:
        global WARNINGS
        WARNINGS = []
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


def assert_warning_was_raised(warning, partial_match=False):
    if partial_match:
        assert any(warning in msg for msg in WARNINGS)
    else:
        assert warning in WARNINGS
