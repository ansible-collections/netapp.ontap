# Copyright (c) 2018 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils netapp_module.py '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible.module_utils import basic
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule as na_helper
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response


class MockONTAPModule(object):
    def __init__(self):
        self.module = basic.AnsibleModule(netapp_utils.na_ontap_host_argument_spec())
        self.na_helper = na_helper(self.module)


def create_ontap_module(args=None):
    return create_module(MockONTAPModule, args)


def test_get_cd_action_create():
    ''' validate cd_action for create '''
    current = None
    desired = {'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_cd_action(current, desired)
    assert result == 'create'


def test_get_cd_action_delete():
    ''' validate cd_action for delete '''
    current = {'state': 'absent'}
    desired = {'state': 'absent'}
    my_obj = na_helper()
    result = my_obj.get_cd_action(current, desired)
    assert result == 'delete'


def test_get_cd_action():
    ''' validate cd_action for returning None '''
    current = None
    desired = {'state': 'absent'}
    my_obj = na_helper()
    result = my_obj.get_cd_action(current, desired)
    assert result is None


def test_get_modified_attributes_for_no_data():
    ''' validate modified attributes when current is None '''
    current = None
    desired = {'name': 'test'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == {}


def test_get_modified_attributes():
    ''' validate modified attributes '''
    current = {'name': ['test', 'abcd', 'xyz', 'pqr'], 'state': 'present'}
    desired = {'name': ['abcd', 'abc', 'xyz', 'pqr'], 'state': 'absent'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == desired


def test_get_modified_attributes_for_intersecting_mixed_list():
    ''' validate modified attributes for list diff '''
    current = {'name': [2, 'four', 'six', 8]}
    desired = {'name': ['a', 8, 'ab', 'four', 'abcd']}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'name': ['a', 'ab', 'abcd']}


def test_get_modified_attributes_for_intersecting_list():
    ''' validate modified attributes for list diff '''
    current = {'name': ['two', 'four', 'six', 'eight']}
    desired = {'name': ['a', 'six', 'ab', 'four', 'abc']}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'name': ['a', 'ab', 'abc']}


def test_get_modified_attributes_for_nonintersecting_list():
    ''' validate modified attributes for list diff '''
    current = {'name': ['two', 'four', 'six', 'eight']}
    desired = {'name': ['a', 'ab', 'abd']}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'name': ['a', 'ab', 'abd']}


def test_get_modified_attributes_for_list_of_dicts_no_data():
    ''' validate modified attributes for list diff '''
    current = None
    desired = {'address_blocks': [{'start': '10.20.10.40', 'size': 5}]}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {}


def test_get_modified_attributes_for_intersecting_list_of_dicts():
    ''' validate modified attributes for list diff '''
    current = {'address_blocks': [{'start': '10.10.10.23', 'size': 5}, {'start': '10.10.10.30', 'size': 5}]}
    desired = {'address_blocks': [{'start': '10.10.10.23', 'size': 5}, {'start': '10.10.10.30', 'size': 5}, {'start': '10.20.10.40', 'size': 5}]}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'address_blocks': [{'start': '10.20.10.40', 'size': 5}]}


def test_get_modified_attributes_for_nonintersecting_list_of_dicts():
    ''' validate modified attributes for list diff '''
    current = {'address_blocks': [{'start': '10.10.10.23', 'size': 5}, {'start': '10.10.10.30', 'size': 5}]}
    desired = {'address_blocks': [{'start': '10.20.10.23', 'size': 5}, {'start': '10.20.10.30', 'size': 5}, {'start': '10.20.10.40', 'size': 5}]}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'address_blocks': [{'start': '10.20.10.23', 'size': 5}, {'start': '10.20.10.30', 'size': 5}, {'start': '10.20.10.40', 'size': 5}]}


def test_get_modified_attributes_for_list_diff():
    ''' validate modified attributes for list diff '''
    current = {'name': ['test', 'abcd'], 'state': 'present'}
    desired = {'name': ['abcd', 'abc'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'name': ['abc']}


def test_get_modified_attributes_for_no_change():
    ''' validate modified attributes for same data in current and desired '''
    current = {'name': 'test'}
    desired = {'name': 'test'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == {}


def test_get_modified_attributes_for_an_empty_desired_list():
    ''' validate modified attributes for an empty desired list '''
    current = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    desired = {'snapmirror_label': [], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == {'snapmirror_label': []}


def test_get_modified_attributes_for_an_empty_desired_list_diff():
    ''' validate modified attributes for an empty desired list with diff'''
    current = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    desired = {'snapmirror_label': [], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'snapmirror_label': []}


def test_get_modified_attributes_for_an_empty_current_list():
    ''' validate modified attributes for an empty current list '''
    current = {'snapmirror_label': [], 'state': 'present'}
    desired = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == {'snapmirror_label': ['daily', 'weekly', 'monthly']}


def test_get_modified_attributes_for_an_empty_current_list_diff():
    ''' validate modified attributes for an empty current list with diff'''
    current = {'snapmirror_label': [], 'state': 'present'}
    desired = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'snapmirror_label': ['daily', 'weekly', 'monthly']}


def test_get_modified_attributes_for_empty_lists():
    ''' validate modified attributes for empty lists '''
    current = {'snapmirror_label': [], 'state': 'present'}
    desired = {'snapmirror_label': [], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired)
    assert result == {}


def test_get_modified_attributes_for_empty_lists_diff():
    ''' validate modified attributes for empty lists with diff '''
    current = {'snapmirror_label': [], 'state': 'present'}
    desired = {'snapmirror_label': [], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {}


def test_get_modified_attributes_equal_lists_with_duplicates():
    ''' validate modified attributes for equal lists with duplicates '''
    current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, False)
    assert result == {}


def test_get_modified_attributes_equal_lists_with_duplicates_diff():
    ''' validate modified attributes for equal lists with duplicates with diff '''
    current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {}


def test_get_modified_attributes_for_current_list_with_duplicates():
    ''' validate modified attributes for current list with duplicates '''
    current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    desired = {'schedule': ['daily', 'daily', 'weekly', 'monthly'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, False)
    assert result == {'schedule': ['daily', 'daily', 'weekly', 'monthly']}


def test_get_modified_attributes_for_current_list_with_duplicates_diff():
    ''' validate modified attributes for current list with duplicates with diff '''
    current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    desired = {'schedule': ['daily', 'daily', 'weekly', 'monthly'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'schedule': []}


def test_get_modified_attributes_for_desired_list_with_duplicates():
    ''' validate modified attributes for desired list with duplicates '''
    current = {'schedule': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, False)
    assert result == {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily']}


def test_get_modified_attributes_for_desired_list_with_duplicates_diff():
    ''' validate modified attributes for desired list with duplicates with diff '''
    current = {'schedule': ['daily', 'weekly', 'monthly'], 'state': 'present'}
    desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'schedule': ['hourly', 'daily', 'daily']}


def test_get_modified_attributes_exceptions():
    ''' validate exceptions '''
    current = {'schedule': {'name': 'weekly'}, 'state': 'present'}
    desired = {'schedule': 'weekly', 'state': 'present'}
    my_obj = create_ontap_module({'hostname': None})
    # mismatch in structure
    error = expect_and_capture_ansible_exception(my_obj.na_helper.get_modified_attributes, TypeError, current, desired)
    assert "Expecting dict, got: weekly with current: {'name': 'weekly'}" in error
    # mismatch in types
    if sys.version_info > (3, 0):
        # our cmp function reports an exception.  But python 2.x has it's own version.
        desired = {'schedule': {'name': 12345}, 'state': 'present'}
        error = expect_and_capture_ansible_exception(my_obj.na_helper.get_modified_attributes, TypeError, current, desired)
        assert ("unorderable types:" in error                                           # 3.5
                or "'>' not supported between instances of 'str' and 'int'" in error)   # 3.9


def test_get_modified_attributes_for_dicts():
    ''' validate modified attributes for dict of dicts '''
    current = {'schedule': {'name': 'weekly'}, 'state': 'present'}
    desired = {'schedule': {'name': 'daily'}, 'state': 'present'}
    my_obj = na_helper()
    result = my_obj.get_modified_attributes(current, desired, True)
    assert result == {'schedule': {'name': 'daily'}}


def test_is_rename_action_for_empty_input():
    ''' validate rename action for input None '''
    source = None
    target = None
    my_obj = na_helper()
    result = my_obj.is_rename_action(source, target)
    assert result == source


def test_is_rename_action_for_no_source():
    ''' validate rename action when source is None '''
    source = None
    target = 'test2'
    my_obj = na_helper()
    result = my_obj.is_rename_action(source, target)
    assert result is False


def test_is_rename_action_for_no_target():
    ''' validate rename action when target is None '''
    source = 'test2'
    target = None
    my_obj = na_helper()
    result = my_obj.is_rename_action(source, target)
    assert result is True


def test_is_rename_action():
    ''' validate rename action '''
    source = 'test'
    target = 'test2'
    my_obj = na_helper()
    result = my_obj.is_rename_action(source, target)
    assert result is False


def test_required_is_not_set_to_none():
    ''' if a key is present, without a value, Ansible sets it to None '''
    my_obj = create_ontap_module({'hostname': None})
    msg = 'hostname requires a value, got: None'
    assert msg == expect_and_capture_ansible_exception(my_obj.na_helper.check_and_set_parameters, 'fail', my_obj.module)['msg']

    # force a value different than None
    my_obj.module.params['hostname'] = 1
    my_params = my_obj.na_helper.check_and_set_parameters(my_obj.module)
    assert set(my_params.keys()) == set(['hostname', 'feature_flags', 'https', 'validate_certs', 'use_rest'])


def test_sanitize_wwn_no_action():
    ''' no change '''
    initiator = 'tEsT'
    expected = initiator
    my_obj = na_helper()
    result = my_obj.sanitize_wwn(initiator)
    assert result == expected


def test_sanitize_wwn_no_action_valid_iscsi():
    ''' no change '''
    initiator = 'iqn.1995-08.com.eXaMpLe:StRiNg'
    expected = initiator
    my_obj = na_helper()
    result = my_obj.sanitize_wwn(initiator)
    assert result == expected


def test_sanitize_wwn_no_action_valid_wwn():
    ''' no change '''
    initiator = '01:02:03:04:0A:0b:0C:0d'
    expected = initiator.lower()
    my_obj = na_helper()
    result = my_obj.sanitize_wwn(initiator)
    assert result == expected


def test_filter_empty_dict():
    ''' empty dict return empty dict '''
    my_obj = na_helper()
    arg = {}
    result = my_obj.filter_out_none_entries(arg)
    assert arg == result


def test_filter_empty_list():
    ''' empty list return empty list '''
    my_obj = na_helper()
    arg = []
    result = my_obj.filter_out_none_entries(arg)
    assert arg == result


def test_filter_typeerror_on_none():
    ''' empty list return empty list '''
    my_obj = na_helper()
    arg = None
    with pytest.raises(TypeError) as exc:
        my_obj.filter_out_none_entries(arg)
    msg = "unexpected type <class 'NoneType'>"
    if sys.version_info < (3, 0):
        # the assert fails on 2.x
        return
    assert exc.value.args[0] == msg


def test_filter_typeerror_on_str():
    ''' empty list return empty list '''
    my_obj = na_helper()
    arg = ""
    with pytest.raises(TypeError) as exc:
        my_obj.filter_out_none_entries(arg)
    msg = "unexpected type <class 'str'>"
    if sys.version_info < (3, 0):
        # the assert fails on 2.x
        return
    assert exc.value.args[0] == msg


def test_filter_simple_dict():
    ''' simple dict return simple dict '''
    my_obj = na_helper()
    arg = dict(a=None, b=1, c=None, d=2, e=3)
    expected = dict(b=1, d=2, e=3)
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_filter_simple_list():
    ''' simple list return simple list '''
    my_obj = na_helper()
    arg = [None, 2, 3, None, 5]
    expected = [2, 3, 5]
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_filter_dict_dict():
    ''' simple dict return simple dict '''
    my_obj = na_helper()
    arg = dict(a=None, b=dict(u=1, v=None, w=2), c=dict(), d=2, e=3)
    expected = dict(b=dict(u=1, w=2), d=2, e=3)
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_filter_list_list():
    ''' simple list return simple list '''
    my_obj = na_helper()
    arg = [None, [1, None, 3], 3, None, 5]
    expected = [[1, 3], 3, 5]
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_filter_dict_list_dict():
    ''' simple dict return simple dict '''
    my_obj = na_helper()
    arg = dict(a=None, b=[dict(u=1, v=None, w=2), 5, None, dict(x=6, y=None)], c=dict(), d=2, e=3)
    expected = dict(b=[dict(u=1, w=2), 5, dict(x=6)], d=2, e=3)
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_filter_list_dict_list():
    ''' simple list return simple list '''
    my_obj = na_helper()
    arg = [None, [1, None, 3], dict(a=None, b=[7, None, 9], c=None, d=dict(u=None, v=10)), None, 5]
    expected = [[1, 3], dict(b=[7, 9], d=dict(v=10)), 5]
    result = my_obj.filter_out_none_entries(arg)
    assert expected == result


def test_get_caller():
    my_obj = na_helper()
    fname = my_obj.get_caller(1)
    assert fname == 'test_get_caller'

    def one(depth):
        return my_obj.get_caller(depth)
    assert one(1) == 'one'

    def two():
        return one(2)
    assert two() == 'two'

    def three():
        return two(), one(3)
    assert three() == ('two', 'test_get_caller')


def test_convert_value():
    ''' positive tests '''
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
    ''' negative tests '''
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
    ''' negative tests '''
    my_obj = create_ontap_module({'hostname': None})
    expect_and_capture_ansible_exception(my_obj.na_helper.convert_value, 'fail', 'any', 'any')


def get_zapi_info():
    return {
        'a': {'b': '12345', 'bad_stuff': ['a', 'b'], 'none_stuff': None}
    }


def get_zapi_na_element(zapi_info):
    na_element, valid = build_zapi_response(zapi_info)
    if valid != 'valid' and sys.version_info < (2, 7):
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
    my_obj = create_ontap_module({'hostname': None})
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


def test_safe_get_with_exception():
    na_element = get_zapi_na_element(get_zapi_info())
    my_obj = create_ontap_module({'hostname': None})
    # KeyError
    error = expect_and_capture_ansible_exception(my_obj.na_helper.safe_get, KeyError, na_element, ['a', 'c'], allow_sparse_dict=False)
    assert 'No element by given name c.' in error
    error = expect_and_capture_ansible_exception(my_obj.na_helper.safe_get, KeyError, get_zapi_info(), ['a', 'c'], allow_sparse_dict=False)
    assert 'c' == error
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
    my_obj = create_ontap_module({'hostname': None})
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
    my_obj = create_ontap_module({'hostname': None})
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
