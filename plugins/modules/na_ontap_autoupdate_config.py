#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
module: na_ontap_autoupdate_config
short_description: NetApp ONTAP module to manage configurations for automatic updates.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap_rest
version_added: 23.4.0
author: NetApp Ansible Team (@carchi8py) <ng-ansible-team@netapp.com>
description:
  - Modify the configuration for a specified automatic update.
options:
  state:
    description:
      - Update the configuration, only present is supported.
    type: str
    choices: ['present']
    default: present
  category:
    description:
      - Specifies the category for the configuration row.
      - Examples - firmware, sp_fw, system, security.
    type: str
    required: true
  action:
    description:
      - Specifies the action to be taken by the alert source as specified by the user.
    type: str
    choices: ['confirm', 'dismiss', 'automatic']
    default: 'confirm'
    required: false

notes:
  - Only supported with REST and requires ONTAP 9.10.1 or later.
"""

EXAMPLES = """
- name: Modify the automatic update setting for security category
  netapp.ontap.na_ontap_autoupdate_config:
    state: present
    category: security
    action: automatic
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
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic


class NetAppOntapAutoUpdateConfig:
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_rest_only_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present'], default='present'),
            category=dict(required=True, type='str'),
            action=dict(required=False, type='str', choices=['confirm', 'dismiss', 'automatic'], default='confirm'),
        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.uuid = None
        self.na_helper = NetAppModule(self.module)
        self.parameters = self.na_helper.check_and_set_parameters(self.module)
        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        self.rest_api.fail_if_not_rest_minimum_version('na_ontap_autoupdate_config:', 9, 10, 1)

    def get_autoupdate_config_rest(self):
        """ Retrieves the configuration for the specified automatic update """
        api = "support/auto-update/configurations"
        fields = 'category,action'
        records, error = rest_generic.get_0_or_more_records(self.rest_api, api, query=None, fields=fields)
        if error:
            self.module.fail_json(msg="Error retrieving auto-update settings for %s: %s" % (self.parameters['category'], to_native(error)),
                                  exception=traceback.format_exc())
        if records:
            for record in records:
                if record.get('category') == self.parameters['category']:
                    self.uuid = record.get('uuid')
                    return {
                        'category': record.get('category'),
                        'action': record.get('action')
                    }
        return None

    def modify_autoupdate_config_rest(self, modify):
        """ Updates the configuration for the specified automatic update """
        api = "support/auto-update/configurations"
        body = {'action': modify['action']}
        dummy, error = rest_generic.patch_async(self.rest_api, api, uuid_or_name=self.uuid, body=body)
        if error:
            self.module.fail_json(msg='Error modifying auto-update settings for %s: %s.' % (self.parameters['category'], to_native(error)),
                                  exception=traceback.format_exc())

    def apply(self):
        current = self.get_autoupdate_config_rest()
        modify = self.na_helper.get_modified_attributes(current, self.parameters)

        if self.na_helper.changed and not self.module.check_mode:
            self.modify_autoupdate_config_rest(modify)
        result = netapp_utils.generate_result(changed=self.na_helper.changed, modify=modify)
        self.module.exit_json(**result)


def main():
    autoupdate_config = NetAppOntapAutoUpdateConfig()
    autoupdate_config.apply()


if __name__ == '__main__':
    main()
