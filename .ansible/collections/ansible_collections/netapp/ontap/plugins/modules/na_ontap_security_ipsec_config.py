#!/usr/bin/python

# (c) 2022-2026, NetApp, Inc. GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
module: na_ontap_security_ipsec_config
short_description: NetApp ONTAP module to configure IPsec config.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap_rest
version_added: '22.1.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansible-team@netapp.com>
description:
  - Enable or disable IPsec config.
  - Configure replay window.
options:
  state:
    description:
      - modify IPsec configuration, only present is supported.
    choices: ['present']
    type: str
    default: present
  enabled:
    description:
      - Indicates whether or not IPsec is enabled.
    type: bool
    required: false
  replay_window:
    description:
      - Replay window size in packets, where 0 indicates that the relay window is disabled.
    type: str
    required: false
    choices: ['0', '64', '128', '256', '512', '1024']
  lambda_config:
    description:
      - Configuration parameters for AWS Lambda proxy functionality.
      - These option and suboptions are only supported with REST.
    type: dict
    version_added: 24.0.0
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
  - Supports check_mode.
  - Only supported with REST and requires ONTAP 9.10.1 or later.
  - Supports AWS Lambda proxy functionality. See README for example usage.
"""

EXAMPLES = """
- name: Enable IPsec config and set replay_window.
  netapp.ontap.na_ontap_security_ipsec_config:
    enabled: true
    replay_window: 64
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"

- name: Disable IPsec config.
  netapp.ontap.na_ontap_security_ipsec_config:
    enabled: false
    replay_window: 64
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


class NetAppOntapSecurityIPsecConfig:
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_rest_only_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present'], default='present'),
            enabled=dict(required=False, type='bool'),
            replay_window=dict(required=False, type='str', choices=['0', '64', '128', '256', '512', '1024'])
        ))
        self.argument_spec.update(netapp_utils.na_ontap_lambda_argument_spec())
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True,
            required_if=[
                ('use_lambda', True, ['lambda_config']),
            ]
        )
        self.uuid = None
        self.na_helper = NetAppModule(self.module)
        self.parameters = self.na_helper.check_and_set_parameters(self.module)
        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        self.rest_api.fail_if_not_rest_minimum_version('na_ontap_security_ipsec_config:', 9, 8)

    def get_security_ipsec_config(self):
        """Get IPsec config details"""
        record, error = rest_generic.get_one_record(self.rest_api, 'security/ipsec', None, 'enabled,replay_window')
        if error:
            self.module.fail_json(msg="Error fetching security IPsec config: %s" % to_native(error), exception=traceback.format_exc())
        if record:
            return {
                'enabled': record.get('enabled'),
                'replay_window': record.get('replay_window')
            }
        return None

    def modify_security_ipsec_config(self, modify):
        """
        Modify security ipsec config
        """
        dummy, error = rest_generic.patch_async(self.rest_api, 'security/ipsec', None, modify)
        if error:
            self.module.fail_json(msg='Error modifying security IPsec config: %s.' % to_native(error), exception=traceback.format_exc())

    def apply(self):
        modify = self.na_helper.get_modified_attributes(self.get_security_ipsec_config(), self.parameters)
        if self.na_helper.changed and not self.module.check_mode:
            self.modify_security_ipsec_config(modify)
        result = netapp_utils.generate_result(self.na_helper.changed, modify=modify)
        self.module.exit_json(**result)


def main():
    ipsec_config = NetAppOntapSecurityIPsecConfig()
    ipsec_config.apply()


if __name__ == '__main__':
    main()
