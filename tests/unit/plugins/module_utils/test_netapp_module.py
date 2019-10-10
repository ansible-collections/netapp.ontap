# Copyright (c) 2018 NetApp
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for module_utils netapp_module.py '''
from __future__ import (absolute_import, division, print_function)

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule as na_helper


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
