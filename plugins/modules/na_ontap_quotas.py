#!/usr/bin/python

# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

'''
na_ontap_quotas
'''


DOCUMENTATION = '''
module: na_ontap_quotas
short_description: NetApp ONTAP Quotas
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.8.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - Set/Modify/Delete quota on ONTAP
options:
  state:
    description:
      - Whether the specified quota should exist or not.
    choices: ['present', 'absent']
    default: present
    type: str
  vserver:
    required: true
    description:
      - Name of the vserver to use.
    type: str
  volume:
    description:
      - The name of the volume that the quota resides on.
    required: true
    type: str
  quota_target:
    description:
      - The quota target of the type specified.
      - Required to create or modify a rule.
    type: str
  qtree:
    description:
      - Name of the qtree for the quota.
      - For user or group rules, it can be the qtree name or "" if no qtree.
      - For tree type rules, this field must be "".
    default: ""
    type: str
  type:
    description:
      - The type of quota rule
      - Required to create or modify a rule.
    choices: ['user', 'group', 'tree']
    type: str
  policy:
    description:
      - Name of the quota policy from which the quota rule should be obtained.
    type: str
  set_quota_status:
    description:
      - Whether the specified volume should have quota status on or off.
    type: bool
  perform_user_mapping:
    description:
      - Whether quota management will perform user mapping for the user specified in quota-target.
      - User mapping can be specified only for a user quota rule.
    type: bool
    version_added: 20.12.0
  file_limit:
    description:
      - The number of files that the target can have.
    type: str
  disk_limit:
    description:
      - The amount of disk space that is reserved for the target.
      - Expects a number followed with KB, MB, GB, TB.
      - If the unit is not present KB is assumed.
      - Examples - 10MB, 20GB, 1TB
    type: str
  soft_file_limit:
    description:
    - The number of files the target would have to exceed before a message is logged and an SNMP trap is generated.
    type: str
  soft_disk_limit:
    description:
      - The amount of disk space the target would have to exceed before a message is logged and an SNMP trap is generated.
      - See C(disk_limit) for format description.
    type: str
  threshold:
    description:
      - The amount of disk space the target would have to exceed before a message is logged.
      - See C(disk_limit) for format description.
    type: str
  activate_quota_on_change:
    description:
      - Method to use to activate quota on a change.
    choices: ['resize', 'reinitialize', 'none']
    default: resize
    type: str
    version_added: 20.12.0
'''

EXAMPLES = """
    - name: Add/Set quota
      na_ontap_quotas:
        state: present
        vserver: ansible
        volume: ansible
        quota_target: /vol/ansible
        type: user
        policy: ansible
        file_limit: 2
        disk_limit: 3
        set_quota_status: True
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Resize quota
      na_ontap_quotas:
        state: present
        vserver: ansible
        volume: ansible
        quota_target: /vol/ansible
        type: user
        policy: ansible
        file_limit: 2
        disk_limit: 3
        set_quota_status: True
        activate_quota_on_change: resize
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Reinitialize quota
      na_ontap_quotas:
        state: present
        vserver: ansible
        volume: ansible
        quota_target: /vol/ansible
        type: user
        policy: ansible
        file_limit: 2
        disk_limit: 3
        set_quota_status: True
        activate_quota_on_change: reinitialize
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: modify quota
      na_ontap_quotas:
        state: present
        vserver: ansible
        volume: ansible
        quota_target: /vol/ansible
        type: user
        policy: ansible
        file_limit: 2
        disk_limit: 3
        threshold: 3
        set_quota_status: False
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Delete quota
      na_ontap_quotas:
        state: absent
        vserver: ansible
        volume: ansible
        quota_target: /vol/ansible
        type: user
        policy: ansible
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
"""

RETURN = """

"""

import time
import traceback
import re
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule


class NetAppONTAPQuotas:
    '''Class with quotas methods'''

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            vserver=dict(required=True, type='str'),
            volume=dict(required=True, type='str'),
            quota_target=dict(required=False, type='str'),
            qtree=dict(required=False, type='str', default=""),
            type=dict(required=False, type='str', choices=['user', 'group', 'tree']),
            policy=dict(required=False, type='str'),
            set_quota_status=dict(required=False, type='bool'),
            perform_user_mapping=dict(required=False, type='bool'),
            file_limit=dict(required=False, type='str'),
            disk_limit=dict(required=False, type='str'),
            soft_file_limit=dict(required=False, type='str'),
            soft_disk_limit=dict(required=False, type='str'),
            threshold=dict(required=False, type='str'),
            activate_quota_on_change=dict(required=False, type='str', choices=['resize', 'reinitialize', 'none'], default='resize')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            required_by={
                'policy': ['quota_target', 'type'],
                'perform_user_mapping': ['quota_target', 'type'],
                'file_limit': ['quota_target', 'type'],
                'disk_limit': ['quota_target', 'type'],
                'soft_file_limit': ['quota_target', 'type'],
                'soft_disk_limit': ['quota_target', 'type'],
                'threshold': ['quota_target', 'type'],
            },
            required_together=[['quota_target', 'type']],
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        # converted blank parameter to * as shown in vsim
        if self.parameters.get('quota_target') == "":
            self.parameters['quota_target'] = '*'
        size_format_error_message = "input string is not a valid size format. A valid size format is constructed as" \
                                    "<integer><size unit>. For example, '10MB', '10KB'.  Only numeric input is also valid." \
                                    "The default unit size is KB."
        if self.parameters.get('disk_limit') and self.parameters['disk_limit'] != '-' and not self.convert_to_kb('disk_limit'):
            self.module.fail_json(msg='disk_limit %s' % size_format_error_message)
        if self.parameters.get('soft_disk_limit') and self.parameters['soft_disk_limit'] != '-' and not self.convert_to_kb('soft_disk_limit'):
            self.module.fail_json(msg='soft_disk_limit %s' % size_format_error_message)
        if self.parameters.get('threshold') and self.parameters['threshold'] != '-' and not self.convert_to_kb('threshold'):
            self.module.fail_json(msg='threshold %s' % size_format_error_message)

        if not netapp_utils.has_netapp_lib():
            self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
        self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def get_quota_status(self):
        """
        Return details about the quota status
        :param:
            name : volume name
        :return: status of the quota. None if not found.
        :rtype: dict
        """
        quota_status_get = netapp_utils.zapi.NaElement('quota-status')
        quota_status_get.translate_struct({
            'volume': self.parameters['volume']
        })
        try:
            result = self.server.invoke_successfully(quota_status_get, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching quotas status info: %s' % to_native(error),
                                  exception=traceback.format_exc())
        return result['status']

    def get_quotas_with_retry(self, get_request, policy):
        return_values = None
        if policy is not None:
            get_request['query']['quota-entry'].add_new_child('policy', policy)
        try:
            result = self.server.invoke_successfully(get_request, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            # Bypass a potential issue in ZAPI when policy is not set in the query
            # https://github.com/ansible-collections/netapp.ontap/issues/4
            # BURT1076601 Loop detected in next() for table quota_rules_zapi
            if policy is None and 'Reason - 13001:success' in to_native(error):
                result = None
                return_values = self.debug_quota_get_error(error)
            else:
                self.module.fail_json(msg='Error fetching quotas info for policy %s: %s'
                                      % (policy, to_native(error)),
                                      exception=traceback.format_exc())
        return result, return_values

    def get_quotas(self, policy=None):
        """
        Get quota details
        :return: name of volume if quota exists, None otherwise
        """
        if self.parameters.get('type') is None:
            return None
        if policy is None:
            policy = self.parameters.get('policy')
        quota_get = netapp_utils.zapi.NaElement('quota-list-entries-iter')
        query = {
            'query': {
                'quota-entry': {
                    'volume': self.parameters['volume'],
                    'quota-target': self.parameters['quota_target'],
                    'quota-type': self.parameters['type'],
                    'vserver': self.parameters['vserver']
                }
            }
        }
        quota_get.translate_struct(query)
        result, return_values = self.get_quotas_with_retry(quota_get, policy)
        if result is None:
            return return_values
        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) >= 1:
            # if quota-target is '*', the query treats it as a wildcard. But a blank entry is represented as '*'.
            # Hence the need to loop through all records to find a match.
            for quota_entry in result.get_child_by_name('attributes-list').get_children():
                quota_target = quota_entry.get_child_content('quota-target')
                if quota_target == self.parameters['quota_target']:
                    return_values = {'volume': quota_entry.get_child_content('volume'),
                                     'file_limit': quota_entry.get_child_content('file-limit'),
                                     'disk_limit': quota_entry.get_child_content('disk-limit'),
                                     'soft_file_limit': quota_entry.get_child_content('soft-file-limit'),
                                     'soft_disk_limit': quota_entry.get_child_content('soft-disk-limit'),
                                     'threshold': quota_entry.get_child_content('threshold')}
                    value = self.na_helper.safe_get(quota_entry, ['perform-user-mapping'])
                    if value is not None:
                        return_values['perform_user_mapping'] = self.na_helper.get_value_for_bool(True, value)
                    return return_values
        return None

    def get_quota_policies(self):
        """
        Get list of quota policies
        :return: list of quota policies (empty list if None found)
        """
        quota_policy_get = netapp_utils.zapi.NaElement('quota-policy-get-iter')
        query = {
            'query': {
                'quota-policy-info': {
                    'vserver': self.parameters['vserver']
                }
            }
        }
        quota_policy_get.translate_struct(query)
        try:
            result = self.server.invoke_successfully(quota_policy_get, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching quota policies: %s' % to_native(error),
                                  exception=traceback.format_exc())
        return ([policy['policy-name'] for policy in result['attributes-list'].get_children()]
                if result.get_child_by_name('attributes-list')
                else [])

    def debug_quota_get_error(self, error):
        policies = self.get_quota_policies()
        entries = {}
        for policy in policies:
            entries[policy] = self.get_quotas(policy)
        if len(policies) == 1:
            self.module.warn('retried with success using policy="%s" on "13001:success" ZAPI error.' % policy)
            return entries[policies[0]]
        self.module.fail_json(msg='Error fetching quotas info: %s - current vserver policies: %s, details: %s'
                              % (to_native(error), policies, entries))

    def quota_entry_set(self):
        """
        Adds a quota entry
        """
        options = {'volume': self.parameters['volume'],
                   'quota-target': self.parameters['quota_target'],
                   'quota-type': self.parameters['type'],
                   'qtree': self.parameters['qtree']}

        self.set_zapi_options(options)
        if self.parameters.get('policy'):
            options['policy'] = self.parameters['policy']
        set_entry = netapp_utils.zapi.NaElement.create_node_with_children(
            'quota-set-entry', **options)
        try:
            self.server.invoke_successfully(set_entry, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error adding/modifying quota entry %s: %s'
                                  % (self.parameters['volume'], to_native(error)),
                                  exception=traceback.format_exc())

    def quota_entry_delete(self):
        """
        Deletes a quota entry
        """
        options = {'volume': self.parameters['volume'],
                   'quota-target': self.parameters['quota_target'],
                   'quota-type': self.parameters['type'],
                   'qtree': self.parameters['qtree']}
        set_entry = netapp_utils.zapi.NaElement.create_node_with_children(
            'quota-delete-entry', **options)
        if self.parameters.get('policy'):
            set_entry.add_new_child('policy', self.parameters['policy'])
        try:
            self.server.invoke_successfully(set_entry, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting quota entry %s: %s'
                                  % (self.parameters['volume'], to_native(error)),
                                  exception=traceback.format_exc())

    def quota_entry_modify(self, modify_attrs):
        """
        Modifies a quota entry
        """
        options = {'volume': self.parameters['volume'],
                   'quota-target': self.parameters['quota_target'],
                   'quota-type': self.parameters['type'],
                   'qtree': self.parameters['qtree']}
        options.update(modify_attrs)
        self.set_zapi_options(options)
        if self.parameters.get('policy'):
            options['policy'] = str(self.parameters['policy'])
        modify_entry = netapp_utils.zapi.NaElement.create_node_with_children(
            'quota-modify-entry', **options)
        try:
            self.server.invoke_successfully(modify_entry, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying quota entry %s: %s'
                                  % (self.parameters['volume'], to_native(error)),
                                  exception=traceback.format_exc())

    def set_zapi_options(self, options):
        if self.parameters.get('file_limit'):
            options['file-limit'] = self.parameters['file_limit']
        if self.parameters.get('disk_limit'):
            options['disk-limit'] = self.parameters['disk_limit']
        if self.parameters.get('perform_user_mapping') is not None:
            options['perform-user-mapping'] = str(self.parameters['perform_user_mapping'])
        if self.parameters.get('soft_file_limit'):
            options['soft-file-limit'] = self.parameters['soft_file_limit']
        if self.parameters.get('soft_disk_limit'):
            options['soft-disk-limit'] = self.parameters['soft_disk_limit']
        if self.parameters.get('threshold'):
            options['threshold'] = self.parameters['threshold']

    def on_or_off_quota(self, status, cd_action=None):
        """
        on or off quota
        """
        quota = netapp_utils.zapi.NaElement.create_node_with_children(
            status, **{'volume': self.parameters['volume']})
        try:
            self.server.invoke_successfully(quota,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            if cd_action == 'delete' and status == 'quota-on' and '14958:No valid quota rules found' in to_native(error):
                # ignore error on quota-on, as all rules have been deleted
                self.module.warn('Last rule deleted, quota is off.')
                return
            self.module.fail_json(msg='Error setting %s for %s: %s'
                                  % (status, self.parameters['volume'], to_native(error)),
                                  exception=traceback.format_exc())

    def resize_quota(self, cd_action=None):
        """
        resize quota
        """
        quota = netapp_utils.zapi.NaElement.create_node_with_children(
            'quota-resize', **{'volume': self.parameters['volume']})
        try:
            self.server.invoke_successfully(quota,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            if cd_action == 'delete' and '14958:No valid quota rules found' in to_native(error):
                # ignore error on quota-on, as all rules have been deleted
                self.module.warn('Last rule deleted, but quota is on as resize is not allowed.')
                return
            self.module.fail_json(msg='Error setting %s for %s: %s'
                                  % ('quota-resize', self.parameters['volume'], to_native(error)),
                                  exception=traceback.format_exc())

    def apply(self):
        """
        Apply action to quotas
        """
        netapp_utils.ems_log_event("na_ontap_quotas", self.server)
        cd_action = None
        modify_quota_status = None
        modify_quota = None
        current = self.get_quotas()
        if self.parameters.get('type') is not None:
            cd_action = self.na_helper.get_cd_action(current, self.parameters)
            if cd_action is None:
                modify_quota = self.na_helper.get_modified_attributes(current, self.parameters)
        quota_status = self.get_quota_status()
        if 'set_quota_status' in self.parameters and quota_status is not None:
            # if 'set_quota_status' == True in create, sometimes there is delay in status update from 'initializing' -> 'on'.
            # if quota_status == 'on' and options(set_quota_status == True and activate_quota_on_change == 'resize'),
            # sometimes there is delay in status update from 'resizing' -> 'on'
            set_quota_status = True if quota_status in ('on', 'resizing', 'initializing') else False
            quota_status_action = self.na_helper.get_modified_attributes({'set_quota_status': set_quota_status}, self.parameters)
            if quota_status_action:
                modify_quota_status = 'quota-on' if quota_status_action['set_quota_status'] else 'quota-off'
        if (self.parameters['activate_quota_on_change'] in ['resize', 'reinitialize']
                and (cd_action is not None or modify_quota is not None)
                and modify_quota_status is None
                and quota_status in ('on', None)):
            modify_quota_status = self.parameters['activate_quota_on_change']
        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.quota_entry_set()
            elif cd_action == 'delete':
                self.quota_entry_delete()
            elif modify_quota:
                for key in list(modify_quota):
                    modify_quota[key.replace("_", "-")] = modify_quota.pop(key)
                self.quota_entry_modify(modify_quota)
            if modify_quota_status in ['quota-off', 'quota-on']:
                self.on_or_off_quota(modify_quota_status)
            elif modify_quota_status == 'resize':
                self.resize_quota(cd_action)
            elif modify_quota_status == 'reinitialize':
                self.on_or_off_quota('quota-off')
                time.sleep(10)  # status switch interval
                self.on_or_off_quota('quota-on', cd_action)

        self.module.exit_json(changed=self.na_helper.changed)

    def convert_to_kb(self, option):
        """
        convert input to kb, and set to self.parameters.
        :param option: disk_limit or soft_disk_limit.
        :return: boolean if it can be converted.
        """
        self.parameters[option].replace(' ', '')
        slices = re.findall(r"\d+|\D+", self.parameters[option])
        if len(slices) < 1 or len(slices) > 2:
            return False
        if not slices[0].isdigit():
            return False
        if len(slices) > 1 and slices[1].lower() not in ['kb', 'mb', 'gb', 'tb']:
            return False
        if len(slices) > 1:
            self.parameters[option] = str(int(slices[0]) * netapp_utils.POW2_BYTE_MAP[slices[1].lower()] // 1024)
        return True


def main():
    '''Execute action'''
    quota_obj = NetAppONTAPQuotas()
    quota_obj.apply()


if __name__ == '__main__':
    main()
