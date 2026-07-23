#!/usr/bin/python

# (c) 2023-2026, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
module: na_ontap_ems_filter
short_description: NetApp ONTAP EMS Filter
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap_rest
version_added: 22.4.0
author: NetApp Ansible Team (@carchi8py) <ng-ansible-team@netapp.com>
description:
  - Create, delete, or modify EMS filters on NetApp ONTAP. This module only supports REST.

options:
  state:
    description:
      - Whether the specified user should exist or not.
    choices: ['present', 'absent']
    type: str
    default: 'present'

  name:
    description:
      - Name of the EMS Filter
    required: True
    type: str

  rules:
    description: List of EMS filter rules
    type: list
    elements: dict
    suboptions:
      index:
        description: Index of rule
        type: int
        required: True
      type:
        description: The type of rule
        type: str
        choices: ['include', 'exclude']
        required: True
      message_criteria:
        description: Message criteria for EMS filter, required one of severities, name_pattern when creating ems filter.
        type: dict
        suboptions:
          severities:
            description: comma separated string of severities this rule applies to
            type: str
          name_pattern:
            description:  Name pattern to apply rule to
            type: str
      parameter_criteria:
        description: Parameter criteria for EMS filter, used to match specific parameters in EMS messages.
        type: list
        elements: dict
        version_added: 23.3.0
        suboptions:
          name_pattern:
            description: Name pattern for parameter matching
            type: str
          value_pattern:
            description: Value pattern for parameter matching
            type: str
  lambda_config:
    description:
      - Configuration parameters for AWS Lambda proxy functionality.
      - These option and suboptions are only supported with REST.
    type: dict
    version_added: 23.6.0
    suboptions:
      function_name:
        description:
          - The name of the AWS Lambda function to invoke.
        type: str
        required: true
      aws_region:
        description:
          - The name of the AWS region.
        type: str
        required: true
      aws_profile:
        description:
          - The name of the AWS profile to use for authentication.
        type: str

notes:
  - This module only supports REST.
  - Supports AWS Lambda proxy functionality. See README for example usage.
'''

EXAMPLES = """
- name: Create EMS filter
  netapp.ontap.na_ontap_ems_filter:
    state: present
    name: carchi_ems
    rules:
      - index: 1
        type: include
        message_criteria:
          severities: "error"
          name_pattern: "callhome.*"
      - index: 2
        type: include
        message_criteria:
          severities: "EMERGENCY"

- name: Modify EMS filter add rule
  netapp.ontap.na_ontap_ems_filter:
    state: present
    name: carchi_ems
    rules:
      - index: 1
        type: include
        message_criteria:
          severities: "error"
          name_pattern: "callhome.*"
      - index: 2
        type: include
        message_criteria:
          severities: "EMERGENCY"
      - index: 3
        type: include
        message_criteria:
          severities: "ALERT"

- name: Create EMS filter with parameter criteria
  netapp.ontap.na_ontap_ems_filter:
    state: present
    name: param_filter
    rules:
      - index: 1
        type: include
        message_criteria:
          severities: "error"
        parameter_criteria:
          - name_pattern: "volume"
            value_pattern: "vol0*"
          - name_pattern: "node"
            value_pattern: "cluster-01"

- name: Delete EMS Filter
  netapp.ontap.na_ontap_ems_filter:
    state: absent
    name: carchi_ems
"""

RETURN = """
"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic


class NetAppOntapEMSFilters:

    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_rest_only_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str'),
            rules=dict(type='list', elements='dict', options=dict(
                index=dict(required=True, type="int"),
                type=dict(required=True, type="str", choices=['include', 'exclude']),
                message_criteria=dict(type="dict", options=dict(
                    severities=dict(required=False, type="str"),
                    name_pattern=dict(required=False, type="str")
                )),
                parameter_criteria=dict(type="list", elements="dict", options=dict(
                    name_pattern=dict(required=False, type="str"),
                    value_pattern=dict(required=False, type="str")
                ))
            ))
        ))
        self.argument_spec.update(netapp_utils.na_ontap_lambda_argument_spec())

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            required_if=[
                ('use_lambda', True, ['lambda_config']),
            ],
            supports_check_mode=True
        )
        self.na_helper = NetAppModule(self.module)
        self.parameters = self.na_helper.check_and_set_parameters(self.module)
        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        self.use_rest = self.rest_api.is_rest()
        if not self.use_rest:
            self.module.fail_json(msg="This module requires REST with ONTAP 9.6 or higher")

    def get_ems_filter(self):
        api = 'support/ems/filters'
        params = {'name': self.parameters['name'],
                  'fields': "rules"}
        record, error = rest_generic.get_one_record(self.rest_api, api, params)
        if error:
            self.module.fail_json(msg="Error fetching ems filter %s: %s" % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        return record

    def create_ems_filter(self):
        api = 'support/ems/filters'
        body = {'name': self.parameters['name']}
        if self.parameters.get('rules'):
            body['rules'] = self.na_helper.filter_out_none_entries(self.parameters['rules'])
        dummy, error = rest_generic.post_async(self.rest_api, api, body)
        if error:
            self.module.fail_json(msg="Error creating EMS filter %s: %s" % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def delete_ems_filter(self):
        api = 'support/ems/filters'
        dummy, error = rest_generic.delete_async(self.rest_api, api, self.parameters['name'])
        if error:
            self.module.fail_json(msg='Error deleting EMS filter %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_ems_filter(self, desired_rules):
        """
        Modify EMS filter rules.

        Note: Unlike ONTAP CLI, the REST API requires sequential rule indexes.
        When deleting rules, the module automatically reindexes remaining rules.
        This is a limitation of the REST API, not the module.
        """
        post_api = 'support/ems/filters/%s/rules' % self.parameters['name']
        delete_api = 'support/ems/filters/%s/rules' % self.parameters['name']
        api = 'support/ems/filters'

        # Delete rules that are no longer needed
        if desired_rules.get('delete_rules'):
            for rule_index in desired_rules['delete_rules']:
                dummy, error = rest_generic.delete_async(self.rest_api, delete_api, rule_index)
                if error:
                    self.module.fail_json(msg='Error deleting rule %s from EMS filter %s: %s' % (rule_index, self.parameters['name'], to_native(error)),
                                          exception=traceback.format_exc())

        # Patch existing rules
        if desired_rules['patch_rules'] != []:
            patch_body = {'rules': desired_rules['patch_rules']}
            dummy, error = rest_generic.patch_async(self.rest_api, api, self.parameters['name'], patch_body)
            if error:
                self.module.fail_json(msg='Error modifying EMS filter %s: %s' % (self.parameters['name'], to_native(error)),
                                      exception=traceback.format_exc())

        # Add new rules
        if desired_rules['post_rules'] != []:
            for rule in desired_rules['post_rules']:
                dummy, error = rest_generic.post_async(self.rest_api, post_api, rule)
                if error:
                    self.module.fail_json(msg='Error adding rule to EMS filter %s: %s' % (self.parameters['name'], to_native(error)),
                                          exception=traceback.format_exc())

    def normalize_severities(self, severities):
        """
        Normalize severity order for consistent comparison.
        Convert comma-separated severity string to a sorted, lowercase string.
        """
        if not severities or severities == '*':
            return '*'

        # Split, strip whitespace, convert to lowercase, sort, and rejoin
        severity_list = [s.strip().lower() for s in severities.split(',')]
        return ','.join(sorted(severity_list))

    def desired_ems_rules(self, current_rules):
        # Modify current filter to remove auto added rule of type exclude, from testing it always appears to be the last element
        current_rules['rules'] = current_rules['rules'][:-1]
        if self.parameters.get('rules'):
            input_rules = self.na_helper.filter_out_none_entries(self.parameters['rules'])
            for i in range(len(input_rules)):
                input_rules[i]['message_criteria']['severities'] = input_rules[i]['message_criteria']['severities'].lower()

            # Declarative approach: manage rules to match exactly what's in configuration
            patch_rules = []
            post_rules = []
            delete_rules = []

            # Get all input rule indices for quick lookup
            input_rule_indices = {str(rule['index']) for rule in input_rules}

            # Find current rules that are no longer in input - these should be deleted
            for current_rule in current_rules['rules']:
                if str(current_rule['index']) not in input_rule_indices:
                    delete_rules.append(current_rule['index'])

            # Process input rules to determine if they need patching or posting
            for input_rule in input_rules:
                rule_matched = False
                for current_rule in current_rules['rules']:
                    if str(input_rule['index']) == str(current_rule['index']):
                        patch_rules.append(input_rule)
                        rule_matched = True
                        break

                # If input rule doesn't match any existing rule, it's a new rule to post
                if not rule_matched:
                    post_rules.append(input_rule)

            desired_rules = {'patch_rules': patch_rules, 'post_rules': post_rules, 'delete_rules': delete_rules}
            return desired_rules
        return None

    def find_modify(self, current, desired_rules):
        """
        Determine if modifications are needed based on the desired rules.
        """
        if not current:
            return False
        # Next check if either one has no rules
        if current.get('rules') is None or desired_rules is None:
            return False

        # If there are rules to delete, we definitely need to modify
        if desired_rules.get('delete_rules') and len(desired_rules['delete_rules']) > 0:
            return True

        # If there are rules to post, we definitely need to modify
        if desired_rules.get('post_rules') and len(desired_rules['post_rules']) > 0:
            return True

        modify = False
        merge_rules = desired_rules['patch_rules']

        # Check if any rules need patching by comparing current vs desired
        for i, patch_rule in enumerate(merge_rules):
            # Find corresponding current rule
            current_rule = None
            for curr_rule in current['rules']:
                if str(curr_rule['index']) == str(patch_rule['index']):
                    current_rule = curr_rule
                    break

            if not current_rule:
                return True  # Rule exists in desired but not in current

            # Compare rule attributes
            if current_rule['type'] != patch_rule['type']:
                return True

            # Adding default values for fields under message_criteria
            if patch_rule.get('message_criteria') is None:
                patch_rule['message_criteria'] = {'severities': '*', 'name_pattern': '*'}
            elif patch_rule['message_criteria'].get('severities') is None:
                patch_rule['message_criteria']['severities'] = '*'
            elif patch_rule['message_criteria'].get('name_pattern') is None:
                patch_rule['message_criteria']['name_pattern'] = '*'

            if current_rule.get('message_criteria').get('name_pattern') != patch_rule.get('message_criteria').get('name_pattern'):
                return True

            # Compare severities using normalized order
            current_severities = self.normalize_severities(current_rule.get('message_criteria', {}).get('severities', '*'))
            desired_severities = self.normalize_severities(patch_rule.get('message_criteria', {}).get('severities', '*'))
            if current_severities != desired_severities:
                return True

            # Handling parameter_criteria comparison
            current_params = current_rule.get('parameter_criteria', [])
            desired_params = patch_rule.get('parameter_criteria')

            # Handling None/null parameter_criteria
            if desired_params is None:
                # If desired is None, check if current is the default wildcard pattern
                default_param = [{'name_pattern': '*', 'value_pattern': '*'}]
                if current_params != [] and current_params != default_param:
                    return True
            else:
                if current_params != desired_params:
                    return True
        return modify

    def apply(self):
        current = self.get_ems_filter()
        cd_action, modify = None, False
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action is None and self.parameters['state'] == 'present':
            desired_rules = self.desired_ems_rules(current)
            modify = self.find_modify(current, desired_rules)
            if modify:
                self.na_helper.changed = True

        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.create_ems_filter()
            if cd_action == 'delete':
                self.delete_ems_filter()
            if modify:
                self.modify_ems_filter(desired_rules)
        result = netapp_utils.generate_result(self.na_helper.changed, cd_action, modify)
        self.module.exit_json(**result)


def main():
    '''Apply volume operations from playbook'''
    obj = NetAppOntapEMSFilters()
    obj.apply()


if __name__ == '__main__':
    main()
