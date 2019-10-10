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
version_added: '2.9'
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
'''

EXAMPLES = """
    - name: Create threshold efficiency policy
      na_ontap_efficiency_policy:
        hostname: 10.193.79.189
        username: admin
        password: netapp1!
        vserver: ansible_vserver
        https: true
        validate_certs: false
        state: present
        policy_name: test
        comment: This policy is for x and y
        enabled: true
        policy_type: threshold
        qos_policy: background
    - name: Create efficiency Scheduled efficiency Policy
      na_ontap_efficiency_policy:
        hostname: 10.193.79.189
        username: admin
        password: netapp1!
        vserver: ansible_vserver
        https: true
        validate_certs: false
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
            schedule=dict(reuired=False, type='str'),
            vserver=dict(required=True, type='str'),
        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True,
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        if self.parameters.get('policy_type'):
            if self.parameters['policy_type'] == 'threshold':
                if self.parameters.get('duration'):
                    self.module.fail_json(msg="duration cannot be set if policy_type is threshold")
                if self.parameters.get('schedule'):
                    self.module.fail_json(msg='schedule cannot be set if policy_type is threshold')
        if self.parameters.get('schedule'):
            if self.parameters.get('policy_type') is None:
                self.module.fail_json(msg="policy_type set to scheduled is required if schedule is given")
        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

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
            if sis_info.get_child_by_name('comment'):
                return_value['comment'] = sis_info.get_child_content('comment')
            if sis_info.get_child_by_name('duration'):
                return_value['duration'] = sis_info.get_child_content('duration')
            if sis_info.get_child_by_name('enabled'):
                if sis_info.get_child_content('enabled') == 'true':
                    return_value['enabled'] = True
                else:
                    return_value['enabled'] = False
            if sis_info.get_child_by_name('policy-type'):
                return_value['policy_type'] = sis_info.get_child_content('policy-type')
            if sis_info.get_child_by_name('qos-policy'):
                return_value['qos_policy'] = sis_info.get_child_content('qos-policy')
            if sis_info.get_child_by_name('schedule'):
                return_value['schedule'] = sis_info.get_child_content('schedule')
        if return_value == {}:
            return_value = None
        return return_value

    def create_efficiency_policy(self):
        """
        Creates a efficiency policy
        :return: None
        """
        sis_policy_obj = netapp_utils.zapi.NaElement("sis-policy-create")
        sis_policy_obj = self._options(sis_policy_obj)
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
            self.module.fail_json(msg="Error Deleting efficiency policy %s: %s" % (self.parameters["policy_name"], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_efficiency_policy(self):
        """
        Modify a efficiency policy
        :return: None
        """
        sis_policy_obj = netapp_utils.zapi.NaElement("sis-policy-modify")
        sis_policy_obj = self._options(sis_policy_obj)
        try:
            self.server.invoke_successfully(sis_policy_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error Modifying efficiency policy %s: %s" % (self.parameters["policy_name"], to_native(error)),
                                  exception=traceback.format_exc())

    def _options(self, sis_policy_obj):
        sis_policy_obj.add_new_child("policy-name", self.parameters['policy_name'])
        if self.parameters.get('comment'):
            sis_policy_obj.add_new_child("comment", self.parameters['comment'])
        if self.parameters.get('duration'):
            sis_policy_obj.add_new_child("duration", self.parameters['duration'])
        if self.parameters.get('enabled') is not None:
            sis_policy_obj.add_new_child("enabled", str(self.parameters['enabled']))
        if self.parameters.get('policy_type'):
            sis_policy_obj.add_new_child("policy-type", self.parameters['policy_type'])
        if self.parameters.get('qos_policy'):
            sis_policy_obj.add_new_child("qos-policy", self.parameters['qos_policy'])
        if self.parameters.get('schedule'):
            sis_policy_obj.add_new_child("schedule", self.parameters['schedule'])
        return sis_policy_obj

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
                    self.modify_efficiency_policy()
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    obj = NetAppOntapEfficiencyPolicy()
    obj.apply()


if __name__ == '__main__':
    main()
