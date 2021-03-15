#!/usr/bin/python

# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
module: na_ontap_efficiency_policy
short_description: NetApp ONTAP manage efficiency policies (sis policies)
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.9.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Create/Modify/Delete efficiency policies (sis policies)
options:
  state:
    description:
    - Whether the specified efficiency policy should exist or not.
    choices: ['present', 'absent']
    default: 'present'
    type: str

  policy_name:
    description:
    - the name of the efficiency policy
    required: true
    type: str

  comment:
    description:
    - A brief description of the policy.
    type: str

  duration:
    description:
    - The duration in hours for which the scheduled efficiency operation should run.
      After this time expires, the efficiency operation will be stopped even if the operation is incomplete.
      If '-' is specified as the duration, the efficiency operation will run till it completes. Otherwise, the duration has to be an integer greater than 0.
      By default, the operation runs till it completes.
    type: str

  enabled:
    description:
    - If the value is true, the efficiency policy is active in this cluster.
      If the value is false this policy will not be activated by the schedulers and hence will be inactive.
    type: bool

  policy_type:
    description:
    - The policy type reflects the reason a volume using this policy will start processing a changelog.
    - (Changelog processing is identifying and eliminating duplicate blocks which were written since the changelog was last processed.)
    - threshold Changelog processing occurs once the changelog reaches a certain percent full.
    - scheduled Changelog processing will be triggered by time.
    choices: ['threshold', 'scheduled']
    type: str

  qos_policy:
    description:
    - QoS policy for the efficiency operation.
    - background efficiency operation will run in background with minimal or no impact on data serving client operations,
    - best-effort efficiency operations may have some impact on data serving client operations.
    choices: ['background', 'best_effort']
    type: str

  schedule:
    description:
    - Cron type job schedule name. When the associated policy is set on a volume, the efficiency operation will be triggered for the volume on this schedule.
    - These schedules can be created using the na_ontap_job_schedule module
    type: str

  vserver:
    description:
    - Name of the vserver to use.
    required: true
    type: str

  changelog_threshold_percent:
    description:
    - Specifies the percentage at which the changelog will be processed for a threshold type of policy, tested once each hour.
    type: int
    version_added: '19.11.0'
'''

EXAMPLES = """
    - name: Create threshold efficiency policy
      na_ontap_efficiency_policy:
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        vserver: ansible
        state: present
        policy_name: test
        comment: This policy is for x and y
        enabled: true
        policy_type: threshold
        qos_policy: background
        changelog_threshold_percent: 20

    - name: Create Scheduled efficiency Policy
      na_ontap_efficiency_policy:
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        vserver: ansible
        state: present
        policy_name: test2
        comment: This policy is for x and y
        enabled: true
        schedule: new_job_schedule
        duration: 1
        policy_type: scheduled
        qos_policy: background
"""

RETURN = """
"""

import traceback
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapEfficiencyPolicy(object):
    """
    Create, delete and modify efficiency policy
    """
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            policy_name=dict(required=True, type='str'),
            comment=dict(required=False, type='str'),
            duration=dict(required=False, type='str'),
            enabled=dict(required=False, type='bool'),
            policy_type=dict(required=False, choices=['threshold', 'scheduled']),
            qos_policy=dict(required=False, choices=['background', 'best_effort']),
            schedule=dict(required=False, type='str'),
            vserver=dict(required=True, type='str'),
            changelog_threshold_percent=dict(required=False, type='int')
        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True,
            mutually_exclusive=[('changelog_threshold_percent', 'duration'), ('changelog_threshold_percent', 'schedule')]
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.set_playbook_zapi_key_map()
        if self.parameters.get('policy_type'):
            if self.parameters['policy_type'] == 'threshold':
                if self.parameters.get('duration'):
                    self.module.fail_json(msg="duration cannot be set if policy_type is threshold")
                if self.parameters.get('schedule'):
                    self.module.fail_json(msg='schedule cannot be set if policy_type is threshold')
            # if policy_type is 'scheduled'
            else:
                if self.parameters.get('changelog_threshold_percent'):
                    self.module.fail_json(msg='changelog_threshold_percent cannot be set if policy_type is scheduled')
        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def set_playbook_zapi_key_map(self):

        self.na_helper.zapi_int_keys = {
            'changelog_threshold_percent': 'changelog-threshold-percent'
        }
        self.na_helper.zapi_str_keys = {
            'policy_name': 'policy-name',
            'comment': 'comment',
            'policy_type': 'policy-type',
            'qos_policy': 'qos-policy',
            'schedule': 'schedule',
            'duration': 'duration'
        }
        self.na_helper.zapi_bool_keys = {
            'enabled': 'enabled'
        }

    def get_efficiency_policy(self):
        """
        Get a efficiency policy
        :return: a efficiency-policy info
        """
        sis_policy_obj = netapp_utils.zapi.NaElement("sis-policy-get-iter")
        query = netapp_utils.zapi.NaElement("query")
        sis_policy_info = netapp_utils.zapi.NaElement("sis-policy-info")
        sis_policy_info.add_new_child("policy-name", self.parameters['policy_name'])
        sis_policy_info.add_new_child("vserver", self.parameters['vserver'])
        query.add_child_elem(sis_policy_info)
        sis_policy_obj.add_child_elem(query)
        try:
            results = self.server.invoke_successfully(sis_policy_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error searching for efficiency policy %s: %s" % (self.parameters['policy_name'], to_native(error)),
                                  exception=traceback.format_exc())
        return_value = {}
        if results.get_child_by_name('num-records') and int(results.get_child_content('num-records')) == 1:
            attributes_list = results.get_child_by_name('attributes-list')
            sis_info = attributes_list.get_child_by_name('sis-policy-info')
            for option, zapi_key in self.na_helper.zapi_int_keys.items():
                return_value[option] = self.na_helper.get_value_for_int(from_zapi=True, value=sis_info.get_child_content(zapi_key))
            for option, zapi_key in self.na_helper.zapi_bool_keys.items():
                return_value[option] = self.na_helper.get_value_for_bool(from_zapi=True, value=sis_info.get_child_content(zapi_key))
            for option, zapi_key in self.na_helper.zapi_str_keys.items():
                return_value[option] = sis_info.get_child_content(zapi_key)
            return return_value
        return None

    def create_efficiency_policy(self):
        """
        Creates a efficiency policy
        :return: None
        """
        sis_policy_obj = netapp_utils.zapi.NaElement("sis-policy-create")
        for option, zapi_key in self.na_helper.zapi_int_keys.items():
            if self.parameters.get(option):
                sis_policy_obj.add_new_child(zapi_key,
                                             self.na_helper.get_value_for_int(from_zapi=False,
                                                                              value=self.parameters[option]))
        for option, zapi_key in self.na_helper.zapi_bool_keys.items():
            if self.parameters.get(option):
                sis_policy_obj.add_new_child(zapi_key,
                                             self.na_helper.get_value_for_bool(from_zapi=False,
                                                                               value=self.parameters[option]))
        for option, zapi_key in self.na_helper.zapi_str_keys.items():
            if self.parameters.get(option):
                sis_policy_obj.add_new_child(zapi_key, str(self.parameters[option]))
        try:
            self.server.invoke_successfully(sis_policy_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error creating efficiency policy %s: %s" % (self.parameters["policy_name"], to_native(error)),
                                  exception=traceback.format_exc())

    def delete_efficiency_policy(self):
        """
        Delete a efficiency Policy
        :return: None
        """
        sis_policy_obj = netapp_utils.zapi.NaElement("sis-policy-delete")
        sis_policy_obj.add_new_child("policy-name", self.parameters['policy_name'])
        try:
            self.server.invoke_successfully(sis_policy_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error deleting efficiency policy %s: %s" % (self.parameters["policy_name"], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_efficiency_policy(self, current, modify):
        """
        Modify a efficiency policy
        :return: None
        """
        sis_policy_obj = netapp_utils.zapi.NaElement("sis-policy-modify")
        sis_policy_obj.add_new_child("policy-name", self.parameters['policy_name'])
        # sis-policy-create zapi pre-checks the options and fails if it's not supported.
        # sis-policy-modify pre-checks one of the options, but tries to modify the others even it's not supported. And it will mess up the vsim.
        # Do the checks before sending to the zapi.
        if current['policy_type'] == 'scheduled' and self.parameters.get('policy_type') != 'threshold':
            if modify.get('changelog_threshold_percent'):
                self.module.fail_json(msg="changelog_threshold_percent cannot be set if policy_type is scheduled")
        elif current['policy_type'] == 'threshold' and self.parameters.get('policy_type') != 'scheduled':
            if modify.get('duration'):
                self.module.fail_json(msg="duration cannot be set if policy_type is threshold")
            elif modify.get('schedule'):
                self.module.fail_json(msg="schedule cannot be set if policy_type is threshold")
        for attribute in modify:
            sis_policy_obj.add_new_child(self.attribute_to_name(attribute), str(self.parameters[attribute]))
        try:
            self.server.invoke_successfully(sis_policy_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error modifying efficiency policy %s: %s" % (self.parameters["policy_name"], to_native(error)),
                                  exception=traceback.format_exc())

    @staticmethod
    def attribute_to_name(attribute):
        return str.replace(attribute, '_', '-')

    def apply(self):
        netapp_utils.ems_log_event("na_ontap_efficiency_policy", self.server)
        current = self.get_efficiency_policy()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action is None and self.parameters['state'] == 'present':
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if cd_action == 'create':
                    self.create_efficiency_policy()
                elif cd_action == 'delete':
                    self.delete_efficiency_policy()
                elif modify:
                    self.modify_efficiency_policy(current, modify)
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    obj = NetAppOntapEfficiencyPolicy()
    obj.apply()


if __name__ == '__main__':
    main()
