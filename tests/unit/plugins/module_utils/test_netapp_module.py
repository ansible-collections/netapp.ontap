# Copyright (c) 2018-2022 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for module_utils netapp_module.py """
from __future__ import (absolute_import, division, print_function)
import copy
__metaclass__ = type

import pytest
import sys

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule as na_helper, cmp as na_cmp
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_no_warnings, assert_warning_was_raised, clear_warnings, patch_ansible, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response
from ansible_collections.netapp.ontap.tests.unit.framework import ut_utilities

if sys.version_info < (3, 11):
    pytestmark = pytest.mark.skip("Skipping Unit Tests on 3.11")


class MockONTAPModule(object):
    def __init__(self):
        self.module = basic.AnsibleModule(netapp_utils.na_ontap_host_argument_spec())
        self.na_helper = na_helper(self.module)
        self.na_helper.set_parameters(self.module.params)


class MockONTAPModuleV2(object):
    def __init__(self):
        self.module = basic.AnsibleModule(netapp_utils.na_ontap_host_argument_spec())
        self.na_helper = na_helper(self)
        self.na_helper.set_parameters(self.module.params)


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


def create_ontap_module(args=None, version=1):
    if version == 2:
        return create_module(MockONTAPModuleV2, args)
    return create_module(MockONTAPModule, args)


def test_get_cd_action_create():
    """ validate cd_action for create """
    current = None
    desired = {'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_cd_action(current, desired)
    assert result == 'create'


def test_get_cd_action_delete():
    """ validate cd_action for delete """
    current = {'state': 'absent'}
    desired = {'state': 'absent'}
    my_obj = na_helper()
    result = my_obj.get_cd_action(current, desired)
    assert result == 'delete'


def test_get_cd_action_already_exist():
    """ validate cd_action for returning None """
    current = {'state': 'whatever'}
    desired = {'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_cd_action(current, desired)
    assert result is None


def test_get_cd_action_already_absent():
    """ validate cd_action for returning None """
    current = None
    desired = {'state': 'absent'}
    my_obj = na_helper()
    result = my_obj.get_cd_action(current, desired)
    assert result is None


def test_get_modified_attributes_for_no_data():
    """ validate modified attributes when current is None """
    current = None
    desired = {'name': 'test'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == {}


def test_get_modified_attributes():
    """ validate modified attributes """
    current = {'name': ['test', 'abcd', 'xyz', 'pqr'], 'state': 'present'}
    desired = {'name': ['abcd', 'abc', 'xyz', 'pqr'], 'state': 'absent'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == desired


def test_get_modified_attributes_for_intersecting_mixed_list():
    """ validate modified attributes for list diff """
    current = {'name': [2, 'four', 'six', 8]}
    desired = {'name': ['a', 8, 'ab', 'four', 'abcd']}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'name': ['a', 'ab', 'abcd']}


def test_get_modified_attributes_for_intersecting_list():
    """ validate modified attributes for list diff """
    current = {'name': ['two', 'four', 'six', 'eight']}
    desired = {'name': ['a', 'six', 'ab', 'four', 'abc']}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'name': ['a', 'ab', 'abc']}


def test_get_modified_attributes_for_nonintersecting_list():
    """ validate modified attributes for list diff """
    current = {'name': ['two', 'four', 'six', 'eight']}
    desired = {'name': ['a', 'ab', 'abd']}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'name': ['a', 'ab', 'abd']}


def test_get_modified_attributes_for_list_of_dicts_no_data():
    """ validate modified attributes for list diff """
    current = None
    desired = {'address_blocks': [{'start': '10.20.10.40', 'size': 5}]}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {}


def test_get_modified_attributes_for_intersecting_list_of_dicts():
    """ validate modified attributes for list diff """
    current = {'address_blocks': [{'start': '10.10.10.23', 'size': 5}, {'start': '10.10.10.30', 'size': 5}]}
    desired = {'address_blocks': [{'start': '10.10.10.23', 'size': 5}, {'start': '10.10.10.30', 'size': 5}, {'start': '10.20.10.40', 'size': 5}]}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'address_blocks': [{'start': '10.20.10.40', 'size': 5}]}


def test_get_modified_attributes_for_nonintersecting_list_of_dicts():
    """ validate modified attributes for list diff """
    current = {'address_blocks': [{'start': '10.10.10.23', 'size': 5}, {'start': '10.10.10.30', 'size': 5}]}
    desired = {'address_blocks': [{'start': '10.20.10.23', 'size': 5}, {'start': '10.20.10.30', 'size': 5}, {'start': '10.20.10.40', 'size': 5}]}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'address_blocks': [{'start': '10.20.10.23', 'size': 5}, {'start': '10.20.10.30', 'size': 5}, {'start': '10.20.10.40', 'size': 5}]}


def test_get_modified_attributes_for_list_diff():
    """ validate modified attributes for list diff """
    current = {'name': ['test', 'abcd'], 'state': 'present'}
    desired = {'name': ['abcd', 'abc'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'name': ['abc']}


def test_get_modified_attributes_for_no_change():
    """ validate modified attributes for same data in current and desired """
    current = {'name': 'test'}
    desired = {'name': 'test'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == {}


def test_get_modified_attributes_for_an_empty_desired_list():
    """ validate modified attributes for an empty desired list """
    current = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    desired = {'snapmirror_label': [], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == {'snapmirror_label': []}


def test_get_modified_attributes_for_an_empty_desired_list_diff():
    """ validate modified attributes for an empty desired list with diff"""
    current = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    desired = {'snapmirror_label': [], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'snapmirror_label': []}


def test_get_modified_attributes_for_an_empty_current_list():
    """ validate modified attributes for an empty current list """
    current = {'snapmirror_label': [], 'state': 'present'}
    desired = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == {'snapmirror_label': ['daily', 'weekly', 'monthly']}


def test_get_modified_attributes_for_an_empty_current_list_diff():
    """ validate modified attributes for an empty current list with diff"""
    current = {'snapmirror_label': [], 'state': 'present'}
    desired = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'snapmirror_label': ['daily', 'weekly', 'monthly']}


def test_get_modified_attributes_for_empty_lists():
    """ validate modified attributes for empty lists """
    current = {'snapmirror_label': [], 'state': 'present'}
    desired = {'snapmirror_label': [], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == {}


def test_get_modified_attributes_for_empty_lists_diff():
    """ validate modified attributes for empty lists with diff """
    current = {'snapmirror_label': [], 'state': 'present'}
    desired = {'snapmirror_label': [], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {}


def test_get_modified_attributes_equal_lists_with_duplicates():
    """ validate modified attributes for equal lists with duplicates """
    current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, False)
    assert result == {}


def test_get_modified_attributes_equal_lists_with_duplicates_diff():
    """ validate modified attributes for equal lists with duplicates with diff """
    current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {}


def test_get_modified_attributes_for_current_list_with_duplicates():
    """ validate modified attributes for current list with duplicates """
    current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    desired = {'schedule': ['daily', 'daily', 'weekly', 'monthly'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, False)
    assert result == {'schedule': ['daily', 'daily', 'weekly', 'monthly']}


def test_get_modified_attributes_for_current_list_with_duplicates_diff():
    """ validate modified attributes for current list with duplicates with diff """
    current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    desired = {'schedule': ['daily', 'daily', 'weekly', 'monthly'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'schedule': []}


def test_get_modified_attributes_for_desired_list_with_duplicates():
    """ validate modified attributes for desired list with duplicates """
    current = {'schedule': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, False)
    assert result == {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily']}


def test_get_modified_attributes_for_desired_list_with_duplicates_diff():
    """ validate modified attributes for desired list with duplicates with diff """
    current = {'schedule': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'schedule': ['hourly', 'daily', 'daily']}


def test_get_modified_attributes_exceptions():
    """ validate exceptions """
    current = {'schedule': {'name': 'weekly'}, 'state': 'present'}
    desired = {'schedule': 'weekly', 'state': 'present'}
    my_obj = create_ontap_module({'hostname': ''})
    # mismatch in structure
    error = expect_and_capture_ansible_exception(my_obj.na_helper.get_modified_attributes, TypeError, current, desired)
    assert "Expecting dict, got: weekly with current: {'name': 'weekly'}" in error
    # mismatch in types
    if sys.version_info[:2] > (3, 0):
        # our cmp function reports an exception.  But python 2.x has it's own version.
        desired = {'schedule': {'name': 12345}, 'state': 'present'}
        error = expect_and_capture_ansible_exception(my_obj.na_helper.get_modified_attributes, TypeError, current, desired)
        assert ("unorderable types:" in error                                           # 3.5
                or "'>' not supported between instances of 'str' and 'int'" in error)   # 3.9


def test_get_modified_attributes_for_dicts():
    """ validate modified attributes for dict of dicts """
    current = {'schedule': {'name': 'weekly'}, 'state': 'present'}
    desired = {'schedule': {'name': 'daily'}, 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'schedule': {'name': 'daily'}}


def test_is_rename_action_for_empty_input():
    """ validate rename action for input None """
    source = None
    target = None
    my_obj = na_helper()
    result = my_obj.is_rename_action(source, target)
    assert result == source


def test_is_rename_action_for_no_source():
    """ validate rename action when source is None """
    source = None
    target = 'test2'
    my_obj = na_helper()
    result = my_obj.is_rename_action(source, target)
    assert result is False


def test_is_rename_action_for_no_target():
    """ validate rename action when target is None """
    source = 'test2'
    target = None
    my_obj = na_helper()
    result = my_obj.is_rename_action(source, target)
    assert result is True


def test_is_rename_action():
    """ validate rename action """
    source = 'test'
    target = 'test2'
    my_obj = na_helper()
    result = my_obj.is_rename_action(source, target)
    assert result is False


# def test_required_is_not_set_to_none():
#     """ if a key is present, without a value, Ansible sets it to None """
#     args = {}
#     args['hostname'] = None
#     # my_obj = create_ontap_module(args)
#     # msg = 'hostname requires a value, got: None'
#     # assert msg == expect_and_capture_ansible_exception(my_obj.na_helper.check_and_set_parameters, 'fail', my_obj.module)['msg']
#     # Expect the AnsibleFailJson exception
#     with pytest.raises(AnsibleFailJson) as excinfo:
#         my_obj = create_ontap_module(args)

#     # Check the exception message
#     assert "argument 'hostname' is of type <class 'NoneType'>" in str(excinfo.value)
#     # force a value different than None
#     my_obj.module.params['hostname'] = 1
#     my_params = my_obj.na_helper.check_and_set_parameters(my_obj.module)
#     assert set(my_params.keys()) == set(['hostname', 'https', 'validate_certs', 'use_rest'])


def test_sanitize_wwn_no_action():
    """ no change """
    initiator = 'tEsT'
    expected = initiator
    my_obj = na_helper()
    result = my_obj.sanitize_wwn(initiator)
    assert result == expected


def test_sanitize_wwn_no_action_valid_iscsi():
    """ no change """
    initiator = 'iqn.1995-08.com.eXaMpLe:StRiNg'
    expected = initiator
    my_obj = na_helper()
    result = my_obj.sanitize_wwn(initiator)
    assert result == expected


def test_sanitize_wwn_no_action_valid_wwn():
    """ no change """
    initiator = '01:02:03:04:0A:0b:0C:0d'
    expected = initiator.lower()
    my_obj = na_helper()
    result = my_obj.sanitize_wwn(initiator)
    assert result == expected


def test_filter_empty_dict():
    """ empty dict return empty dict """
    my_obj = na_helper()
    arg = {}
    result = my_obj.filter_out_none_entries(arg)
    assert arg == result


def test_filter_empty_list():
    """ empty list return empty list """
    my_obj = na_helper()
    arg = []
    result = my_obj.filter_out_none_entries(arg)
    assert arg == result


def test_filter_typeerror_on_none():
    """ empty list return empty list """
    my_obj = na_helper()
    arg = None
    with pytest.raises(TypeError) as exc:
        my_obj.filter_out_none_entries(arg)
    if sys.version_info[:2] < (3, 0):
        # the assert fails on 2.x
        return
    msg = "unexpected type <class 'NoneType'>"
    assert exc.value.args[0] == msg


def test_filter_typeerror_on_str():
    """ empty list return empty list """
    my_obj = na_helper()
    arg = ""
    with pytest.raises(TypeError) as exc:
        my_obj.filter_out_none_entries(arg)
    if sys.version_info[:2] < (3, 0):
        # the assert fails on 2.x
        return
    msg = "unexpected type <class 'str'>"
    assert exc.value.args[0] == msg


def test_filter_simple_dict():
    """ simple dict return simple dict """
    my_obj = na_helper()
    arg = dict(a=None, b=1, c=None, d=2, e=3)
    expected = dict(b=1, d=2, e=3)
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_filter_simple_list():
    """ simple list return simple list """
    my_obj = na_helper()
    arg = [None, 2, 3, None, 5]
    expected = [2, 3, 5]
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_filter_dict_dict():
    """ simple dict return simple dict """
    my_obj = na_helper()
    arg = dict(a=None, b=dict(u=1, v=None, w=2), c={}, d=2, e=3)
    expected = dict(b=dict(u=1, w=2), d=2, e=3)
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_filter_list_list():
    """ simple list return simple list """
    my_obj = na_helper()
    arg = [None, [1, None, 3], 3, None, 5]
    expected = [[1, 3], 3, 5]
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_filter_dict_list_dict():
    """ simple dict return simple dict """
    my_obj = na_helper()
    arg = dict(a=None, b=[dict(u=1, v=None, w=2), 5, None, dict(x=6, y=None)], c={}, d=2, e=3)
    expected = dict(b=[dict(u=1, w=2), 5, dict(x=6)], d=2, e=3)
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_filter_list_dict_list():
    """ simple list return simple list """
    my_obj = na_helper()
    arg = [None, [1, None, 3], dict(a=None, b=[7, None, 9], c=None, d=dict(u=None, v=10)), None, 5]
    expected = [[1, 3], dict(b=[7, 9], d=dict(v=10)), 5]
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_convert_value():
    """ positive tests """
    my_obj = na_helper()
    for value, convert_to, expected in [
        ('any', None, 'any'),
        (12345, None, 12345),
        ('12345', int, 12345),
        ('any', str, 'any'),
        ('true', bool, True),
        ('false', bool, False),
        ('online', 'bool_online', True),
        ('any', 'bool_online', False),
    ]:
        result, error = my_obj.convert_value(value, convert_to)
        assert error is None
        assert expected == result


def test_convert_value_with_error():
    """ negative tests """
    my_obj = na_helper()
    for value, convert_to, expected in [
        (12345, 'any', "Unexpected type:"),
        ('any', int, "Unexpected value for int: any"),
        ('any', bool, "Unexpected value: any received from ZAPI for boolean attribute"),
    ]:
        result, error = my_obj.convert_value(value, convert_to)
        print(value, convert_to, result, '"%s"' % expected, '"%s"' % error)
        assert result is None
        assert expected in error


def test_convert_value_with_exception():
    """ negative tests """
    my_obj = create_ontap_module({'hostname': ''})
    expect_and_capture_ansible_exception(my_obj.na_helper.convert_value, 'fail', 'any', 'any')


def get_zapi_info():
    return {
        'a': {'b': '12345', 'bad_stuff': ['a', 'b'], 'none_stuff': None}
    }


def get_zapi_na_element(zapi_info):
    na_element, valid = build_zapi_response(zapi_info)
    if valid != 'valid' and sys.version_info[:2] < (2, 7):
        pytest.skip('Skipping Unit Tests on 2.6 as netapp-lib is not available')
    assert valid == 'valid'
    return na_element


def test_zapi_get_value():
    na_element = get_zapi_na_element(get_zapi_info())
    my_obj = na_helper()
    assert my_obj.zapi_get_value(na_element, ['a', 'b'], convert_to=int) == 12345
    # missing key returns None if sparse dict is allowed (default)
    assert my_obj.zapi_get_value(na_element, ['a', 'c'], convert_to=int) is None
    # missing key returns 'default' - note, no conversion - if sparse dict is allowed (default)
    assert my_obj.zapi_get_value(na_element, ['a', 'c'], convert_to=int, default='default') == 'default'


def test_zapi_get_value_with_exception():
    na_element = get_zapi_na_element(get_zapi_info())
    my_obj = create_ontap_module({'hostname': ''})
    # KeyError
    error = expect_and_capture_ansible_exception(my_obj.na_helper.zapi_get_value, 'fail', na_element, ['a', 'c'], required=True)['msg']
    assert 'No element by given name c.' in error


def test_safe_get():
    na_element = get_zapi_na_element(get_zapi_info())
    my_obj = na_helper()
    assert my_obj.safe_get(na_element, ['a', 'b']) == '12345'
    assert my_obj.safe_get(na_element, ['a', 'c']) is None
    assert my_obj.safe_get(get_zapi_info(), ['a', 'b']) == '12345'
    assert my_obj.safe_get(get_zapi_info(), ['a', 'c']) is None
    assert my_obj.safe_get(get_zapi_info(), ['a', 'none_stuff', 'extra']) is None       # TypeError on None


def test_safe_get_dict_of_list():
    my_obj = na_helper()
    my_dict = {'a': ['b', 'c', {'d': ['e']}]}
    assert my_obj.safe_get(my_dict, ['a', 0]) == 'b'
    assert my_obj.safe_get(my_dict, ['a', 2, 'd', 0]) == 'e'
    assert my_obj.safe_get(my_dict, ['a', 3]) is None


def test_safe_get_with_exception():
    na_element = get_zapi_na_element(get_zapi_info())
    my_obj = create_ontap_module({'hostname': ''})
    # KeyError
    error = expect_and_capture_ansible_exception(my_obj.na_helper.safe_get, KeyError, na_element, ['a', 'c'], allow_sparse_dict=False)
    assert 'No element by given name c.' in error
    error = expect_and_capture_ansible_exception(my_obj.na_helper.safe_get, KeyError, get_zapi_info(), ['a', 'c'], allow_sparse_dict=False)
    assert 'c' == error
    # IndexError
    error = expect_and_capture_ansible_exception(my_obj.na_helper.safe_get, IndexError, get_zapi_info(), ['a', 'bad_stuff', 4], allow_sparse_dict=False)
    print('EXC', error)
    if ut_utilities.is_indexerror_exception_formatted():
        assert 'list index out of range' in str(error)
    error = expect_and_capture_ansible_exception(my_obj.na_helper.safe_get, IndexError, get_zapi_info(), ['a', 'bad_stuff', -4], allow_sparse_dict=False)
    print('EXC', error)
    if ut_utilities.is_indexerror_exception_formatted():
        assert 'list index out of range' in str(error)
    # TypeError - not sure I can build a valid ZAPI NaElement that can give a type error, but using a dict worked.
    error = expect_and_capture_ansible_exception(my_obj.na_helper.safe_get, TypeError, get_zapi_info(), ['a', 'bad_stuff', 'extra'], allow_sparse_dict=False)
    # 'list indices must be integers, not str' with 2.7
    # 'list indices must be integers or slices, not str' with 3.x
    assert 'list indices must be integers' in error
    error = expect_and_capture_ansible_exception(my_obj.na_helper.safe_get, TypeError, get_zapi_info(), ['a', 'none_stuff', 'extra'], allow_sparse_dict=False)
    # 'NoneType' object has no attribute '__getitem__' with 2.7
    # 'NoneType' object is not subscriptable with 3.x
    assert "'NoneType' object " in error


def test_get_value_for_bool():
    my_obj = na_helper()
    for value, from_zapi, expected in [
        (None, 'any', None),
        ('true', True, True),
        ('false', True, False),
        ('any', True, False),           # no error checking if key is not present
        (True, False, 'true'),
        (False, False, 'false'),
        ('any', False, 'true'),         # no error checking if key is not present
    ]:
        result = my_obj.get_value_for_bool(from_zapi, value)
        print(value, from_zapi, result)
        assert result == expected


def test_get_value_for_bool_with_exception():
    na_element = get_zapi_na_element(get_zapi_info())
    my_obj = create_ontap_module({'hostname': ''})
    # Error with from_zapi=True if key is present
    error = expect_and_capture_ansible_exception(my_obj.na_helper.get_value_for_bool, TypeError, True, 1234, 'key')
    assert "expecting 'str' type for 'key': 1234" in error
    error = expect_and_capture_ansible_exception(my_obj.na_helper.get_value_for_bool, ValueError, True, 'any', 'key')
    assert "Unexpected value: 'any' received from ZAPI for boolean attribute: 'key'" == error
    # TypeError - expecting a bool
    error = expect_and_capture_ansible_exception(my_obj.na_helper.get_value_for_bool, TypeError, False, 'any', 'key')
    assert "expecting 'bool' type for 'key': 'any'" in error


def test_get_value_for_int():
    my_obj = na_helper()
    for value, from_zapi, expected in [
        (None, 'any', None),
        ('12345', True, 12345),
        (12345, True, 12345),           # no error checking if key is not present
        (12345, False, '12345'),
    ]:
        result = my_obj.get_value_for_int(from_zapi, value)
        print(value, from_zapi, result)
        assert result == expected


def test_get_value_for_int_with_exception():
    na_element = get_zapi_na_element(get_zapi_info())
    my_obj = create_ontap_module({'hostname': ''})
    # Error with from_zapi=True if key is present
    error = expect_and_capture_ansible_exception(my_obj.na_helper.get_value_for_int, TypeError, True, 1234, 'key')
    assert "expecting 'str' type for 'key': 1234" in error
    error = expect_and_capture_ansible_exception(my_obj.na_helper.get_value_for_int, ValueError, True, 'any', 'key')
    assert "invalid literal for int() with base 10: 'any'" == error
    # TypeError - expecting a int
    error = expect_and_capture_ansible_exception(my_obj.na_helper.get_value_for_int, TypeError, False, 'any', 'key')
    assert "expecting 'int' type for 'key': 'any'" in error


def test_get_value_for_list():
    my_obj = na_helper()
    zapi_info = {
        'a': [{'b': 'a1'}, {'b': 'a2'}, {'b': 'a3'}]
    }
    for from_zapi, zapi_parent, zapi_child, data, expected in [
        (True, None, None, None, []),
        (True, get_zapi_na_element(zapi_info), None, None, [None]),
        (True, get_zapi_na_element(get_zapi_info()).get_child_by_name('a'), None, None, ['12345', None, None]),
        (True, get_zapi_na_element(zapi_info).get_child_by_name('a'), None, None, ['a1', 'a2', 'a3']),
        (False, 'parent', 'child', [], b'<parent/>'),
        (False, 'parent', 'child', ['1', '1'], b'<parent><child>1</child><child>1</child></parent>'),
    ]:
        result = my_obj.get_value_for_list(from_zapi, zapi_parent, zapi_child, data)
        print(from_zapi, expected, result)
        if from_zapi:
            if zapi_parent:
                print(zapi_parent.to_string())
            # ordering maybe different with 3.5 compared to 3.9 or 2.7
            assert set(result) == set(expected)
        else:
            print(result.to_string())
            assert result.to_string() == expected


def test_zapi_get_attrs():
    my_obj = na_helper()
    zapi_info = {
        'a': {'b': 'a1', 'c': 'a2', 'd': 'a3', 'int': '123'}
    }
    naelement = get_zapi_na_element(zapi_info)
    attr_dict = {
        'first': {'key_list': ['a', 'b']}
    }
    result = {}
    my_obj.zapi_get_attrs(naelement, attr_dict, result)
    assert result == {'first': 'a1'}

    # if element not found return None, unless omitnone is True
    attr_dict = {
        'none': {'key_list': ['a', 'z'], 'omitnone': True}
    }
    my_obj.zapi_get_attrs(naelement, attr_dict, result)
    assert result == {'first': 'a1'}

    # if element not found return None when required and omitnone are False
    attr_dict = {
        'none': {'key_list': ['a', 'z']}
    }
    my_obj.zapi_get_attrs(naelement, attr_dict, result)
    assert result == {'first': 'a1', 'none': None}

    # if element not found return default
    result = {}
    attr_dict = {
        'none': {'key_list': ['a', 'z'], 'default': 'some_default'}
    }
    my_obj.zapi_get_attrs(naelement, attr_dict, result)
    assert result == {'none': 'some_default'}

    # convert to int
    result = {}
    attr_dict = {
        'int': {'key_list': ['a', 'int'], 'convert_to': int}
    }
    my_obj.zapi_get_attrs(naelement, attr_dict, result)
    assert result == {'int': 123}

    # if element not found return None, unless required is True
    my_obj = create_ontap_module({'hostname': 'abc'})
    attr_dict = {
        'none': {'key_list': ['a', 'z'], 'required': True}
    }
    # the contents of to_string() may be in a different sequence depending on the pytohn version
    assert expect_and_capture_ansible_exception(my_obj.na_helper.zapi_get_attrs, 'fail', naelement, attr_dict, result)['msg'].startswith((
        "Error reading ['a', 'z'] from b'<results status=\"passed\"><a>",   # python 3.x
        "Error reading ['a', 'z'] from <results status=\"passed\"><a>"      # python 2.7
    ))


def test_set_parameters():
    my_obj = na_helper()
    adict = dict((x, x * x) for x in range(10))
    assert my_obj.set_parameters(adict) == adict
    assert my_obj.parameters == adict
    assert len(my_obj.parameters) == 10

    # None values are copied
    adict[3] = None
    assert my_obj.set_parameters(adict) != adict
    assert my_obj.parameters != adict
    assert len(my_obj.parameters) == 9


def test_get_caller():
    assert na_helper.get_caller(0) == 'get_caller'
    assert na_helper.get_caller(1) == 'test_get_caller'

    def one(depth):
        return na_helper.get_caller(depth)
    assert one(1) == 'one'

    def two():
        return one(2)
    assert two() == 'two'

    def three():
        return two(), one(3)
    assert three() == ('two', 'test_get_caller')


@patch('traceback.extract_stack')
def test_get_caller_2_7(mock_frame):
    frame = ('first', 'second', 'function_name')
    mock_frame.return_value = [frame]
    assert na_helper.get_caller(0) == 'function_name'


@patch('traceback.extract_stack')
def test_get_caller_bad_format(mock_frame):
    frame = ('first', 'second')
    mock_frame.return_value = [frame]
    assert na_helper.get_caller(0) == "Error retrieving function name: tuple index out of range - [('first', 'second')]"


def test_fail_on_error():
    my_obj = create_ontap_module({'hostname': 'abc'})
    assert my_obj.na_helper.fail_on_error(None) is None
    assert expect_and_capture_ansible_exception(my_obj.na_helper.fail_on_error, 'fail', 'error_msg')['msg'] ==\
        'Error in expect_and_capture_ansible_exception: error_msg'
    assert expect_and_capture_ansible_exception(my_obj.na_helper.fail_on_error, 'fail', 'error_msg', 'api')['msg'] ==\
        'Error in expect_and_capture_ansible_exception: calling api: api: error_msg'
    previous_errors = ['some_errror']
    exc = expect_and_capture_ansible_exception(my_obj.na_helper.fail_on_error, 'fail', 'error_msg', 'api', previous_errors=previous_errors)
    assert exc['msg'] == 'Error in expect_and_capture_ansible_exception: calling api: api: error_msg'
    assert exc['previous_errors'] == previous_errors[0]
    exc = expect_and_capture_ansible_exception(my_obj.na_helper.fail_on_error, 'fail', 'error_msg', 'api', True)
    assert exc['msg'] == 'Error in expect_and_capture_ansible_exception: calling api: api: error_msg'
    assert exc['stack']
    delattr(my_obj.na_helper, 'ansible_module')
    assert expect_and_capture_ansible_exception(my_obj.na_helper.fail_on_error, AttributeError, 'error_message') ==\
        "Expecting self.ansible_module to be set when reporting {'msg': 'Error in expect_and_capture_ansible_exception: error_message'}"


def test_cmp():
    assert na_cmp(None, 'any') == -1
    # string comparison ignores case
    assert na_cmp('ABC', 'abc') == 0
    assert na_cmp('abcd', 'abc') == 1
    assert na_cmp('abd', 'abc') == 1
    assert na_cmp(['abd', 'abc'], ['abc', 'abd']) == 0
    # list comparison ignores case
    assert na_cmp(['ABD', 'abc'], ['abc', 'abd']) == 0
    # but not duplicates
    assert na_cmp(['ABD', 'ABD', 'abc'], ['abc', 'abd']) == 1


def test_fall_back_to_zapi():
    my_obj = create_ontap_module({'hostname': 'abc'}, version=2)
    parameters = {'use_rest': 'never'}
    assert my_obj.na_helper.fall_back_to_zapi(my_obj.na_helper.ansible_module, 'some message', parameters) is None
    assert_no_warnings()

    parameters = {'use_rest': 'auto'}
    assert my_obj.na_helper.fall_back_to_zapi(my_obj.na_helper.ansible_module, 'some message', parameters) is False
    assert_warning_was_raised('Falling back to ZAPI: some message')

    parameters = {'use_rest': 'always'}
    clear_warnings()
    assert 'Error: some message' in expect_and_capture_ansible_exception(
        my_obj.na_helper.fall_back_to_zapi, 'fail', my_obj.na_helper.ansible_module, 'some message', parameters)['msg']
    assert_no_warnings()


def test_module_deprecated():
    my_obj = create_ontap_module({'hostname': 'abc'})
    assert my_obj.na_helper.module_deprecated(my_obj.na_helper.ansible_module) is None
    assert_warning_was_raised('This module only supports ZAPI and is deprecated.   It will no longer work with newer versions of ONTAP.  '
                              'The final ONTAP version to support ZAPI is ONTAP 9.12.1.')


def test_module_replaces():
    my_obj = create_ontap_module({'hostname': 'abc'})
    new_module = 'na_ontap_new_modules'
    assert my_obj.na_helper.module_replaces(new_module, my_obj.na_helper.ansible_module) is None
    assert_warning_was_raised('netapp.ontap.%s should be used instead.' % new_module)


def test_compare_chmod_value():
    myobj = na_helper()
    assert myobj.compare_chmod_value("0777", "---rwxrwxrwx") is True
    assert myobj.compare_chmod_value("777", "---rwxrwxrwx") is True
    assert myobj.compare_chmod_value("7777", "sstrwxrwxrwx") is True
    assert myobj.compare_chmod_value("4555", "s--r-xr-xr-x") is True
    assert myobj.compare_chmod_value(None, "---rwxrwxrwx") is False
    assert myobj.compare_chmod_value("755", "rwxrwxrwxrwxr") is False
    assert myobj.compare_chmod_value("777", "---ssxrwxrwx") is False
    assert myobj.compare_chmod_value("7777", "rwxrwxrwxrwx") is False
    assert myobj.compare_chmod_value("7777", "7777") is True


def test_ignore_missing_vserver_on_delete():
    my_obj = create_ontap_module({'hostname': 'abc'})
    assert not my_obj.na_helper.ignore_missing_vserver_on_delete('error')
    my_obj.na_helper.parameters['state'] = 'absent'
    error = 'Internal error, vserver name is required, when processing error: error_msg'
    assert error in expect_and_capture_ansible_exception(my_obj.na_helper.ignore_missing_vserver_on_delete, 'fail', 'error_msg')['msg']
    my_obj.na_helper.parameters['vserver'] = 'svm'
    error = 'Internal error, error should contain "message" key, found:'
    assert error in expect_and_capture_ansible_exception(my_obj.na_helper.ignore_missing_vserver_on_delete, 'fail', {'error_msg': 'error'})['msg']
    error = 'Internal error, error should be str or dict, found:'
    assert error in expect_and_capture_ansible_exception(my_obj.na_helper.ignore_missing_vserver_on_delete, 'fail', ['error_msg'])['msg']
    assert not my_obj.na_helper.ignore_missing_vserver_on_delete('error')
    assert my_obj.na_helper.ignore_missing_vserver_on_delete({'message': 'SVM "svm" does not exist.'})


def test_remove_hal_links():
    my_obj = create_ontap_module({'hostname': 'abc'})
    assert my_obj.na_helper.remove_hal_links(None) is None
    assert my_obj.na_helper.remove_hal_links('string') is None
    adict = {
        '_links': 'whatever',
        'other': 'other'
    }
    # dict
    test_object = copy.deepcopy(adict)
    assert my_obj.na_helper.remove_hal_links(test_object) is None
    assert '_links' not in test_object
    # list of dicts
    test_object = [copy.deepcopy(adict)] * 5
    assert my_obj.na_helper.remove_hal_links(test_object) is None
    assert all('_links' not in elem for elem in test_object)
    # dict of dicts
    test_object = {'a': copy.deepcopy(adict), 'b': copy.deepcopy(adict)}
    assert my_obj.na_helper.remove_hal_links(test_object) is None
    assert all('_links' not in value for value in test_object.values())
    # list of list of dicts
    items = [copy.deepcopy(adict)] * 5
    test_object = [items, items]
    assert my_obj.na_helper.remove_hal_links(test_object) is None
    assert all('_links' not in elem for elems in test_object for elem in elems)
