# Copyright (c) 2018 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils netapp_module.py '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys

import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule as na_helper


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


class MockModule(object):
    ''' rough mock for an Ansible module class '''
    def __init__(self, required_param=None, not_required_param=None, unqualified_param=None):
        self.argument_spec = dict(
            required_param=dict(required=True),
            not_required_param=dict(required=False),
            unqualified_param=dict(),
            feature_flags=dict(type='dict')
        )
        self.params = dict(
            required_param=required_param,
            not_required_param=not_required_param,
            unqualified_param=unqualified_param,
            feature_flags=dict(type='dict')
        )

    def fail_json(self, *args, **kwargs):  # pylint: disable=unused-argument
        """function to simulate fail_json: package return data into an exception"""
        kwargs['failed'] = True
        raise AnsibleFailJson(kwargs)


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def test_get_cd_action_create(self):
        ''' validate cd_action for create '''
        current = None
        desired = {'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_cd_action(current, desired)
        assert result == 'create'

    def test_get_cd_action_delete(self):
        ''' validate cd_action for delete '''
        current = {'state': 'absent'}
        desired = {'state': 'absent'}
        my_obj = na_helper()
        result = my_obj.get_cd_action(current, desired)
        assert result == 'delete'

    def test_get_cd_action(self):
        ''' validate cd_action for returning None '''
        current = None
        desired = {'state': 'absent'}
        my_obj = na_helper()
        result = my_obj.get_cd_action(current, desired)
        assert result is None

    def test_get_modified_attributes_for_no_data(self):
        ''' validate modified attributes when current is None '''
        current = None
        desired = {'name': 'test'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired)
        assert result == {}

    def test_get_modified_attributes(self):
        ''' validate modified attributes '''
        current = {'name': ['test', 'abcd', 'xyz', 'pqr'], 'state': 'present'}
        desired = {'name': ['abcd', 'abc', 'xyz', 'pqr'], 'state': 'absent'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired)
        assert result == desired

    def test_get_modified_attributes_for_intersecting_mixed_list(self):
        ''' validate modified attributes for list diff '''
        current = {'name': [2, 'four', 'six', 8]}
        desired = {'name': ['a', 8, 'ab', 'four', 'abcd']}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {'name': ['a', 'ab', 'abcd']}

    def test_get_modified_attributes_for_intersecting_list(self):
        ''' validate modified attributes for list diff '''
        current = {'name': ['two', 'four', 'six', 'eight']}
        desired = {'name': ['a', 'six', 'ab', 'four', 'abc']}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {'name': ['a', 'ab', 'abc']}

    def test_get_modified_attributes_for_nonintersecting_list(self):
        ''' validate modified attributes for list diff '''
        current = {'name': ['two', 'four', 'six', 'eight']}
        desired = {'name': ['a', 'ab', 'abd']}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {'name': ['a', 'ab', 'abd']}

    def test_get_modified_attributes_for_list_of_dicts_no_data(self):
        ''' validate modified attributes for list diff '''
        current = None
        desired = {'address_blocks': [{'start': '10.20.10.40', 'size': 5}]}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {}

    def test_get_modified_attributes_for_intersecting_list_of_dicts(self):
        ''' validate modified attributes for list diff '''
        current = {'address_blocks': [{'start': '10.10.10.23', 'size': 5}, {'start': '10.10.10.30', 'size': 5}]}
        desired = {'address_blocks': [{'start': '10.10.10.23', 'size': 5}, {'start': '10.10.10.30', 'size': 5}, {'start': '10.20.10.40', 'size': 5}]}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {'address_blocks': [{'start': '10.20.10.40', 'size': 5}]}

    def test_get_modified_attributes_for_nonintersecting_list_of_dicts(self):
        ''' validate modified attributes for list diff '''
        current = {'address_blocks': [{'start': '10.10.10.23', 'size': 5}, {'start': '10.10.10.30', 'size': 5}]}
        desired = {'address_blocks': [{'start': '10.20.10.23', 'size': 5}, {'start': '10.20.10.30', 'size': 5}, {'start': '10.20.10.40', 'size': 5}]}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {'address_blocks': [{'start': '10.20.10.23', 'size': 5}, {'start': '10.20.10.30', 'size': 5}, {'start': '10.20.10.40', 'size': 5}]}

    def test_get_modified_attributes_for_list_diff(self):
        ''' validate modified attributes for list diff '''
        current = {'name': ['test', 'abcd'], 'state': 'present'}
        desired = {'name': ['abcd', 'abc'], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {'name': ['abc']}

    def test_get_modified_attributes_for_no_change(self):
        ''' validate modified attributes for same data in current and desired '''
        current = {'name': 'test'}
        desired = {'name': 'test'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired)
        assert result == {}

    def test_get_modified_attributes_for_an_empty_desired_list(self):
        ''' validate modified attributes for an empty desired list '''
        current = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
        desired = {'snapmirror_label': [], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired)
        assert result == {'snapmirror_label': []}

    def test_get_modified_attributes_for_an_empty_desired_list_diff(self):
        ''' validate modified attributes for an empty desired list with diff'''
        current = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
        desired = {'snapmirror_label': [], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {'snapmirror_label': []}

    def test_get_modified_attributes_for_an_empty_current_list(self):
        ''' validate modified attributes for an empty current list '''
        current = {'snapmirror_label': [], 'state': 'present'}
        desired = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired)
        assert result == {'snapmirror_label': ['daily', 'weekly', 'monthly']}

    def test_get_modified_attributes_for_an_empty_current_list_diff(self):
        ''' validate modified attributes for an empty current list with diff'''
        current = {'snapmirror_label': [], 'state': 'present'}
        desired = {'snapmirror_label': ['daily', 'weekly', 'monthly'], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {'snapmirror_label': ['daily', 'weekly', 'monthly']}

    def test_get_modified_attributes_for_empty_lists(self):
        ''' validate modified attributes for empty lists '''
        current = {'snapmirror_label': [], 'state': 'present'}
        desired = {'snapmirror_label': [], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired)
        assert result == {}

    def test_get_modified_attributes_for_empty_lists_diff(self):
        ''' validate modified attributes for empty lists with diff '''
        current = {'snapmirror_label': [], 'state': 'present'}
        desired = {'snapmirror_label': [], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {}

    def test_get_modified_attributes_equal_lists_with_duplicates(self):
        ''' validate modified attributes for equal lists with duplicates '''
        current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
        desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, False)
        assert result == {}

    def test_get_modified_attributes_equal_lists_with_duplicates_diff(self):
        ''' validate modified attributes for equal lists with duplicates with diff '''
        current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
        desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {}

    def test_get_modified_attributes_for_current_list_with_duplicates(self):
        ''' validate modified attributes for current list with duplicates '''
        current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
        desired = {'schedule': ['daily', 'daily', 'weekly', 'monthly'], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, False)
        assert result == {'schedule': ['daily', 'daily', 'weekly', 'monthly']}

    def test_get_modified_attributes_for_current_list_with_duplicates_diff(self):
        ''' validate modified attributes for current list with duplicates with diff '''
        current = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
        desired = {'schedule': ['daily', 'daily', 'weekly', 'monthly'], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {'schedule': []}

    def test_get_modified_attributes_for_desired_list_with_duplicates(self):
        ''' validate modified attributes for desired list with duplicates '''
        current = {'schedule': ['daily', 'weekly', 'monthly'], 'state': 'present'}
        desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, False)
        assert result == {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily']}

    def test_get_modified_attributes_for_desired_list_with_duplicates_diff(self):
        ''' validate modified attributes for desired list with duplicates with diff '''
        current = {'schedule': ['daily', 'weekly', 'monthly'], 'state': 'present'}
        desired = {'schedule': ['hourly', 'daily', 'daily', 'weekly', 'monthly', 'daily'], 'state': 'present'}
        my_obj = na_helper()
        result = my_obj.get_modified_attributes(current, desired, True)
        assert result == {'schedule': ['hourly', 'daily', 'daily']}

    def test_is_rename_action_for_empty_input(self):
        ''' validate rename action for input None '''
        source = None
        target = None
        my_obj = na_helper()
        result = my_obj.is_rename_action(source, target)
        assert result == source

    def test_is_rename_action_for_no_source(self):
        ''' validate rename action when source is None '''
        source = None
        target = 'test2'
        my_obj = na_helper()
        result = my_obj.is_rename_action(source, target)
        assert result is False

    def test_is_rename_action_for_no_target(self):
        ''' validate rename action when target is None '''
        source = 'test2'
        target = None
        my_obj = na_helper()
        result = my_obj.is_rename_action(source, target)
        assert result is True

    def test_is_rename_action(self):
        ''' validate rename action '''
        source = 'test'
        target = 'test2'
        my_obj = na_helper()
        result = my_obj.is_rename_action(source, target)
        assert result is False

    def test_required_is_not_set_to_none(self):
        ''' if a key is present, without a value, Ansible sets it to None '''
        my_obj = na_helper()
        my_module = MockModule()
        print(my_module.argument_spec)
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.check_and_set_parameters(my_module)
        msg = 'required_param requires a value, got: None'
        assert exc.value.args[0]['msg'] == msg

        # force a value different than None
        my_module.params['required_param'] = 1
        my_params = my_obj.check_and_set_parameters(my_module)
        assert set(my_params.keys()) == set(['required_param', 'feature_flags'])

    def test_sanitize_wwn_no_action(self):
        ''' no change '''
        initiator = 'tEsT'
        expected = initiator
        my_obj = na_helper()
        result = my_obj.sanitize_wwn(initiator)
        assert result == expected

    def test_sanitize_wwn_no_action_valid_iscsi(self):
        ''' no change '''
        initiator = 'iqn.1995-08.com.eXaMpLe:StRiNg'
        expected = initiator
        my_obj = na_helper()
        result = my_obj.sanitize_wwn(initiator)
        assert result == expected

    def test_sanitize_wwn_no_action_valid_wwn(self):
        ''' no change '''
        initiator = '01:02:03:04:0A:0b:0C:0d'
        expected = initiator.lower()
        my_obj = na_helper()
        result = my_obj.sanitize_wwn(initiator)
        assert result == expected

    def test_filter_empty_dict(self):
        ''' empty dict return empty dict '''
        my_obj = na_helper()
        arg = dict()
        result = my_obj.filter_out_none_entries(arg)
        assert arg == result

    def test_filter_empty_list(self):
        ''' empty list return empty list '''
        my_obj = na_helper()
        arg = list()
        result = my_obj.filter_out_none_entries(arg)
        assert arg == result

    def test_filter_typeerror_on_none(self):
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

    def test_filter_typeerror_on_str(self):
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

    def test_filter_simple_dict(self):
        ''' simple dict return simple dict '''
        my_obj = na_helper()
        arg = dict(a=None, b=1, c=None, d=2, e=3)
        expected = dict(b=1, d=2, e=3)
        result = my_obj.filter_out_none_entries(arg)
        assert expected == result

    def test_filter_simple_list(self):
        ''' simple list return simple list '''
        my_obj = na_helper()
        arg = [None, 2, 3, None, 5]
        expected = [2, 3, 5]
        result = my_obj.filter_out_none_entries(arg)
        assert expected == result

    def test_filter_dict_dict(self):
        ''' simple dict return simple dict '''
        my_obj = na_helper()
        arg = dict(a=None, b=dict(u=1, v=None, w=2), c=dict(), d=2, e=3)
        expected = dict(b=dict(u=1, w=2), d=2, e=3)
        result = my_obj.filter_out_none_entries(arg)
        assert expected == result

    def test_filter_list_list(self):
        ''' simple list return simple list '''
        my_obj = na_helper()
        arg = [None, [1, None, 3], 3, None, 5]
        expected = [[1, 3], 3, 5]
        result = my_obj.filter_out_none_entries(arg)
        assert expected == result

    def test_filter_dict_list_dict(self):
        ''' simple dict return simple dict '''
        my_obj = na_helper()
        arg = dict(a=None, b=[dict(u=1, v=None, w=2), 5, None, dict(x=6, y=None)], c=dict(), d=2, e=3)
        expected = dict(b=[dict(u=1, w=2), 5, dict(x=6)], d=2, e=3)
        result = my_obj.filter_out_none_entries(arg)
        assert expected == result

    def test_filter_list_dict_list(self):
        ''' simple list return simple list '''
        my_obj = na_helper()
        arg = [None, [1, None, 3], dict(a=None, b=[7, None, 9], c=None, d=dict(u=None, v=10)), None, 5]
        expected = [[1, 3], dict(b=[7, 9], d=dict(v=10)), 5]
        result = my_obj.filter_out_none_entries(arg)
        assert expected == result

    def test_get_caller(self):
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
