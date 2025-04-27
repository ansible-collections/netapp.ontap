#!/usr/bin/python

# (c) 2025, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
module: na_ontap_support_config_backup
short_description: NetApp ONTAP support configuration backup
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap_rest
version_added: 22.14.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - Retrieves and modify the cluster configuration backup information.

options:
  state:
    description:
      - This module supports only system backup configuration modify, hence only present state is supported.
    choices: ['present']
    type: str
    default: present

  url:
    description:
      - An external backup location for the cluster configuration.
      - This is mostly required for single node clusters where node and cluster configuration backups cannot be copied to other nodes in the cluster.
    type: str
    required: true

  validate_certificate:
    description:
      - Use this parameter with the value "true" to validate the digital certificate of the remote server.
      - Digital certificate validation is available only when the HTTPS protocol is used in the URL; it is disabled by default.
    type: bool
    required: true

  name:
    description:
      - Use this parameter to specify the user name to use to log in to the destination system and perform the upload.
      - The option "name" should be used in parameter instead of "username".
    type: str
    required: true

notes:
  - Only supported with REST and requires ONTAP 9.6 or later.
  - The option 'validate_certificate' requires ONTAP 9.7 or later.

"""

EXAMPLES = """
- name: Get support config backup
  netapp.ontap.na_ontap_support_config_backup:
    state: present
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: false
    validate_certificate: false
    url: "{{ backup_url }}"
    name: Netappuser

- name: Modify the support config_backup
  netapp.ontap.na_ontap_support_config_backup:
    state: present
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: false
    validate_certificate: true
    url: "{{ backup_url }}"
    name: ftpuser
    feature_flags:
      trace_apis: true
"""

RETURN = """
"""


import traceback
from ansible.module_utils.basic import AnsibleModule
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic


class NetAppOntapSupportConfigBackup:
    """Retriveing and updating the configuration backup settings"""
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_rest_only_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present'], default='present'),
            url=dict(required=True, type='str'),
            # destination username should be passed as name
            name=dict(required=True, type='str'),
            validate_certificate=dict(required=True, type='bool')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        self.use_rest = self.rest_api.is_rest()
        partially_supported_rest_properties = [['validate_certificate', (9, 7, 0)]]
        self.use_rest = self.rest_api.is_rest_supported_properties(self.parameters, None, partially_supported_rest_properties)
        if not self.use_rest:
            self.module.fail_json(msg='Error: na_ontap_support_config_backup is only supported with REST API')

    def get_support_config_backup(self):
        # Retrieves the cluster configuration backup information
        api = 'support/configuration-backup'
        record, error = rest_generic.get_one_record(self.rest_api, api)
        fields = 'url,username,'
        if self.rest_api.meets_rest_minimum_version(self.use_rest, 9, 7, 0):
            fields += 'validate_certificate,'
        if error:
            self.module.fail_json(msg='Error fetching configuration backup settings',
                                  exception=traceback.format_exc())
        if record:
            return {
                'url': record['url'],
                'name': record['username'],
                'validate_certificate': record['validate_certificate']
            }
        return None

    def modify_support_config_backup(self, modify):
        # Updates the cluster configuration backup information.
        api = 'support/configuration-backup'
        body = {}
        if 'url' in modify:
            body['url'] = modify['url']
        if 'name' in modify:
            body['username'] = modify['name']
        if 'validate_certificate' in modify:
            body['validate_certificate'] = modify['validate_certificate']
        dummy, error = rest_generic.patch_async(self.rest_api, api, None, body)
        if error:
            self.module.fail_json(msg='Error updating the configuration backup settings',
                                  exception=traceback.format_exc())

    def apply(self):
        current = self.get_support_config_backup()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        modify = self.na_helper.get_modified_attributes(current, self.parameters) if cd_action is None else None
        if self.na_helper.changed and not self.module.check_mode:
            if modify:
                self.modify_support_config_backup(modify)
        result = netapp_utils.generate_result(self.na_helper.changed, cd_action, modify)
        self.module.exit_json(**result)


def main():
    config_bkp = NetAppOntapSupportConfigBackup()
    config_bkp.apply()


if __name__ == '__main__':
    main()
