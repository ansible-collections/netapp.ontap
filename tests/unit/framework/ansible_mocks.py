# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# Author: Laurent Nicolas, laurentn@netapp.com

''' set up Ansible mocking context

By importing patch_ansible or path_ansible_warn, the fixture is automatically
applied by every testcase (autouse=True).

Use as:

from ansible_collections.netapp.ontap.tests.unit.framework.ansible_mocks import \
    set_module_args, AnsibleExitJson, AnsibleFailJson, patch_ansible

or:

from ansible_collections.netapp.ontap.tests.unit.framework.ansible_mocks import \
    set_module_args, AnsibleExitJson, AnsibleFailJson, patch_ansible_warn

Optionally, add one or more warning features:

from ansible_collections.netapp.ontap.tests.unit.framework.ansible_mocks import \
    get_warnings, print_warnings, assert_no_warnings, assert_warning_was_raised

'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch


# set this to True to enable print statements
DEBUG = False


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


# mock key Ansible features, including warn
@pytest.fixture(autouse=True)
def patch_ansible_warn():
    if DEBUG:
        print('DEBUG:', 'fixture: patch_ansible_warn')
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json,
                        warn=warn) as mocks:
        global WARNINGS
        WARNINGS = []
        yield mocks


# mock key Ansible features, excluding warn
@pytest.fixture(autouse=True)
def patch_ansible():
    if DEBUG:
        print('DEBUG:', 'fixture: patch_ansible')
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json) as mocks:
        yield mocks
