# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c) 2018, Laurent Nicolas <laurentn@netapp.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

''' Support class for NetApp ansible modules '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from copy import deepcopy
import re
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils


def cmp(obj1, obj2):
    """
    Python 3 does not have a cmp function, this will do the cmp.
    :param obj1: first object to check
    :param obj2: second object to check
    :return:
    """
    # convert to lower case for string comparison.
    if obj1 is None:
        return -1
    if isinstance(obj1, str) and isinstance(obj2, str):
        obj1 = obj1.lower()
        obj2 = obj2.lower()
    # if list has string element, convert string to lower case.
    if isinstance(obj1, list) and isinstance(obj2, list):
        obj1 = [x.lower() if isinstance(x, str) else x for x in obj1]
        obj2 = [x.lower() if isinstance(x, str) else x for x in obj2]
        obj1.sort()
        obj2.sort()
    return (obj1 > obj2) - (obj1 < obj2)


class NetAppModule(object):
    '''
    Common class for NetApp modules
    set of support functions to derive actions based
    on the current state of the system, and a desired state
    '''

    def __init__(self):
        self.log = list()
        self.changed = False
        self.parameters = {'name': 'not initialized'}
        self.zapi_string_keys = dict()
        self.zapi_bool_keys = dict()
        self.zapi_list_keys = dict()
        self.zapi_int_keys = dict()
        self.zapi_required = dict()

    def set_parameters(self, ansible_params):
        self.parameters = dict()
        for param in ansible_params:
            if ansible_params[param] is not None:
                self.parameters[param] = ansible_params[param]
        return self.parameters

    def check_and_set_parameters(self, module):
        self.parameters = dict()
        check_for_none = netapp_utils.has_feature(module, 'check_required_params_for_none')
        if check_for_none:
            required_keys = [key for key, value in module.argument_spec.items() if value.get('required')]
        for param in module.params:
            if module.params[param] is not None:
                self.parameters[param] = module.params[param]
            elif check_for_none and param in required_keys:
                module.fail_json(msg="%s requires a value, got: None" % param)
        return self.parameters

    @staticmethod
    def type_error_message(type_str, key, value):
        return "expecting '%s' type for %s: %s, got: %s" % (type_str, repr(key), repr(value), type(value))

    def get_value_for_bool(self, from_zapi, value, key=None):
        """
        Convert boolean values to string or vice-versa
        If from_zapi = True, value is converted from string (as it appears in ZAPI) to boolean
        If from_zapi = False, value is converted from boolean to string
        For get() method, from_zapi = True
        For modify(), create(), from_zapi = False
        :param from_zapi: convert the value from ZAPI or to ZAPI acceptable type
        :param value: value of the boolean attribute
        :param key: if present, force error checking to validate type, and accepted values
        :return: string or boolean
        """
        if value is None:
            return None
        if from_zapi:
            if key is not None and not isinstance(value, str):
                raise TypeError(self.type_error_message('str', key, value))
            if key is not None and value not in ('true', 'false'):
                raise ValueError('Unexpected value: %s received from ZAPI for boolean attribute: %s' % (repr(value), repr(key)))
            return value == 'true'
        if key is not None and not isinstance(value, bool):
            raise TypeError(self.type_error_message('bool', key, value))
        return 'true' if value else 'false'

    def get_value_for_int(self, from_zapi, value, key=None):
        """
        Convert integer values to string or vice-versa
        If from_zapi = True, value is converted from string (as it appears in ZAPI) to integer
        If from_zapi = False, value is converted from integer to string
        For get() method, from_zapi = True
        For modify(), create(), from_zapi = False
        :param from_zapi: convert the value from ZAPI or to ZAPI acceptable type
        :param value: value of the integer attribute
        :param key: if present, force error checking to validate type
        :return: string or integer
        """
        if value is None:
            return None
        if from_zapi:
            if key is not None and not isinstance(value, str):
                raise TypeError(self.type_error_message('str', key, value))
            return int(value)
        if key is not None and not isinstance(value, int):
            raise TypeError(self.type_error_message('int', key, value))
        return str(value)

    def get_value_for_list(self, from_zapi, zapi_parent, zapi_child=None, data=None):
        """
        Convert a python list() to NaElement or vice-versa
        If from_zapi = True, value is converted from NaElement (parent-children structure) to list()
        If from_zapi = False, value is converted from list() to NaElement
        :param zapi_parent: ZAPI parent key or the ZAPI parent NaElement
        :param zapi_child: ZAPI child key
        :param data: list() to be converted to NaElement parent-children object
        :param from_zapi: convert the value from ZAPI or to ZAPI acceptable type
        :return: list() or NaElement
        """
        if from_zapi:
            if zapi_parent is None:
                return []
            return [zapi_child.get_content() for zapi_child in zapi_parent.get_children()]

        zapi_parent = netapp_utils.zapi.NaElement(zapi_parent)
        for item in data:
            zapi_parent.add_new_child(zapi_child, item)
        return zapi_parent

    def get_cd_action(self, current, desired):
        ''' takes a desired state and a current state, and return an action:
            create, delete, None
            eg:
            is_present = 'absent'
            some_object = self.get_object(source)
            if some_object is not None:
                is_present = 'present'
            action = cd_action(current=is_present, desired = self.desired.state())
        '''
        if 'state' in desired:
            desired_state = desired['state']
        else:
            desired_state = 'present'

        if current is None and desired_state == 'absent':
            return None
        if current is not None and desired_state == 'present':
            return None
        # change in state
        self.changed = True
        if current is not None:
            return 'delete'
        return 'create'

    def compare_and_update_values(self, current, desired, keys_to_compare):
        updated_values = dict()
        is_changed = False
        for key in keys_to_compare:
            if key in current:
                if key in desired and desired[key] is not None:
                    if current[key] != desired[key]:
                        updated_values[key] = desired[key]
                        is_changed = True
                    else:
                        updated_values[key] = current[key]
                else:
                    updated_values[key] = current[key]

        return updated_values, is_changed

    @staticmethod
    def check_keys(current, desired):
        ''' TODO: raise an error if keys do not match
            with the exception of:
            new_name, state in desired
        '''

    @staticmethod
    def compare_lists(current, desired, get_list_diff):
        ''' compares two lists and return a list of elements that are either the desired elements or elements that are
            modified from the current state depending on the get_list_diff flag
            :param: current: current item attribute in ONTAP
            :param: desired: attributes from playbook
            :param: get_list_diff: specifies whether to have a diff of desired list w.r.t current list for an attribute
            :return: list of attributes to be modified
            :rtype: list
        '''
        current_copy = deepcopy(current)
        desired_copy = deepcopy(desired)

        # get what in desired and not in current
        desired_diff_list = list()
        for item in desired:
            if item in current_copy:
                current_copy.remove(item)
            else:
                desired_diff_list.append(item)

        # get what in current but not in desired
        current_diff_list = list()
        for item in current:
            if item in desired_copy:
                desired_copy.remove(item)
            else:
                current_diff_list.append(item)

        if desired_diff_list or current_diff_list:
            # there are changes
            if get_list_diff:
                return desired_diff_list
            else:
                return desired
        else:
            return None

    def get_modified_attributes(self, current, desired, get_list_diff=False):
        ''' takes two dicts of attributes and return a dict of attributes that are
            not in the current state
            It is expected that all attributes of interest are listed in current and
            desired.
            :param: current: current attributes in ONTAP
            :param: desired: attributes from playbook
            :param: get_list_diff: specifies whether to have a diff of desired list w.r.t current list for an attribute
            :return: dict of attributes to be modified
            :rtype: dict

            NOTE: depending on the attribute, the caller may need to do a modify or a
            different operation (eg move volume if the modified attribute is an
            aggregate name)
        '''
        # if the object does not exist,  we can't modify it
        modified = dict()
        if current is None:
            return modified

        # error out if keys do not match
        self.check_keys(current, desired)

        # collect changed attributes
        for key, value in current.items():
            if key in desired and desired[key] is not None:
                if isinstance(value, list):
                    modified_list = self.compare_lists(value, desired[key], get_list_diff)  # get modified list from current and desired
                    if modified_list is not None:
                        modified[key] = modified_list
                elif isinstance(value, dict):
                    modified_dict = self.get_modified_attributes(value, desired[key])
                    if modified_dict:
                        modified[key] = modified_dict
                else:
                    try:
                        result = cmp(value, desired[key])
                    except TypeError as exc:
                        raise TypeError("%s, key: %s, value: %s, desired: %s" % (repr(exc), key, repr(value), repr(desired[key])))
                    else:
                        if result != 0:
                            modified[key] = desired[key]
        if modified:
            self.changed = True
        return modified

    def is_rename_action(self, source, target):
        ''' takes a source and target object, and returns True
            if a rename is required
            eg:
            source = self.get_object(source_name)
            target = self.get_object(target_name)
            action = is_rename_action(source, target)
            :return: None for error, True for rename action, False otherwise
        '''
        if source is None and target is None:
            # error, do nothing
            # cannot rename an non existent resource
            # alternatively we could create B
            return None
        if source is not None and target is not None:
            # error, do nothing
            # idempotency (or) new_name_is_already_in_use
            # alternatively we could delete B and rename A to B
            return False
        if source is None and target is not None:
            # do nothing, maybe the rename was already done
            return False
        # source is not None and target is None:
        # rename is in order
        self.changed = True
        return True

    @staticmethod
    def sanitize_wwn(initiator):
        ''' igroup initiator may or may not be using WWN format: eg 20:00:00:25:B5:00:20:01
            if format is matched, convert initiator to lowercase, as this is what ONTAP is using '''
        wwn_format = r'[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){7}'
        initiator = initiator.strip()
        if re.match(wwn_format, initiator):
            initiator = initiator.lower()
        return initiator

    def safe_get(self, an_object, key_list, allow_sparse_dict=True):
        ''' recursively traverse a dictionary or a any object supporting get_item
            (in our case, python dicts and NAElement responses)
            It is expected that some keys can be missing, this is controlled with allow_sparse_dict

            return value if the key chain is exhausted
            return None if a key is not found and allow_sparse_dict is True
            raise KeyError is a key is not found and allow_sparse_dict is False (looking for exact match)
            raise TypeError if an intermediate element cannot be indexed,
              unless the element is None and allow_sparse_dict is True
        '''
        if not key_list:
            # we've exhausted the keys, good!
            return an_object
        key = key_list.pop(0)
        try:
            return self.safe_get(an_object[key], key_list, allow_sparse_dict=allow_sparse_dict)
        except KeyError as exc:
            # error, key not found
            if allow_sparse_dict:
                return None
            raise exc
        except TypeError as exc:
            # error, we were expecting a dict or NAElement
            if allow_sparse_dict and an_object is None:
                return None
            raise exc

    def filter_out_none_entries(self, list_or_dict):
        """take a dict or list as input and return a dict/list without keys/elements whose values are None
           skip empty dicts or lists.
        """

        if isinstance(list_or_dict, dict):
            result = dict()
            for key, value in list_or_dict.items():
                if isinstance(value, (list, dict)):
                    sub = self.filter_out_none_entries(value)
                    if sub:
                        # skip empty dict or list
                        result[key] = sub
                elif value is not None:
                    # skip None value
                    result[key] = value
            return result

        if isinstance(list_or_dict, list):
            alist = list()
            for item in list_or_dict:
                if isinstance(item, (list, dict)):
                    sub = self.filter_out_none_entries(item)
                    if sub:
                        # skip empty dict or list
                        alist.append(sub)
                elif item is not None:
                    # skip None value
                    alist.append(item)
            return alist

        raise TypeError('unexpected type %s' % type(list_or_dict))
