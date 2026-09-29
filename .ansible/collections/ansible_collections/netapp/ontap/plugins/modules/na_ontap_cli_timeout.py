#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
module: na_ontap_cli_timeout
short_description: NetApp ONTAP module to set the CLI inactivity timeout value.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap_rest
version_added: '22.9.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansible-team@netapp.com>
description:
  -  Modify the timeout value for CLI sessions.
options:
  state:
    description:
      - Modify timeout value, only present is supported.
    choices: ['present']
    type: str
    default: present
  timeout:
    description:
      - Specifies the timeout value, in minutes.
      - To prevent CLI sessions from timing out, specify a value of 0 (zero).
    type: int
    required: true
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
  - Only supported with REST and requires ONTAP 9.6 or later.
  - Supports AWS Lambda proxy functionality. See README for example usage.
"""

EXAMPLES = """
- name: Modify the timeout value for CLI sessions to be 15 minutes
  netapp.ontap.na_ontap_cli_timeout:
    state: present
    timeout: 15
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"

- name: Prevent CLI sessions from timing out
  netapp.ontap.na_ontap_cli_timeout:
    state: present
    timeout: 0
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"
"""

RETURN = """
"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic


class NetAppOntapCliTimeout:
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_rest_only_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present'], default='present'),
            timeout=dict(required=True, type='int')
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
        self.rest_api.fail_if_not_rest_minimum_version('na_ontap_cli_timeout:', 9, 6)

    def get_timeout_value_rest(self):
        """ Get CLI inactivity timeout value """
        fields = 'timeout'
        api = 'private/cli/system/timeout'
        record, error = rest_generic.get_one_record(self.rest_api, api, query=None, fields=fields)
        if error:
            self.module.fail_json(msg="Error fetching CLI sessions timeout value: %s" % to_native(error),
                                  exception=traceback.format_exc())
        if record:
            return {
                'timeout': record.get('timeout')
            }
        return None

    def modify_timeout_value_rest(self, modify):
        """ Modify CLI inactivity timeout value """
        api = 'private/cli/system/timeout'
        dummy, error = rest_generic.patch_async(self.rest_api, api, uuid_or_name=None, body=modify)
        if error:
            self.module.fail_json(msg='Error modifying CLI sessions timeout value: %s.' % to_native(error),
                                  exception=traceback.format_exc())

    def apply(self):
        current = self.get_timeout_value_rest()
        modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed and not self.module.check_mode:
            self.modify_timeout_value_rest(modify)
        result = netapp_utils.generate_result(self.na_helper.changed, modify=modify)
        self.module.exit_json(**result)


def main():
    cli_timeout = NetAppOntapCliTimeout()
    cli_timeout.apply()


if __name__ == '__main__':
    main()
