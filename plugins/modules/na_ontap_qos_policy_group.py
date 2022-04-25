#!/usr/bin/python

# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_qos_policy_group
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
module: na_ontap_qos_policy_group
short_description: NetApp ONTAP manage policy group in Quality of Service.
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
version_added: 2.8.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
  - Create, destroy, modify, or rename QoS policy group on NetApp ONTAP.

options:
  state:
    choices: ['present', 'absent']
    description:
      - Whether the specified policy group should exist or not.
    default: 'present'
    type: str

  name:
    description:
      - The name of the policy group to manage.
    required: true
    type: str

  vserver:
    description:
      - Name of the vserver to use.
    required: true
    type: str

  from_name:
    description:
      - Name of the existing policy group to be renamed to name.
    type: str

  max_throughput:
    description:
      - Maximum throughput defined by this policy.
      - Not supported with REST, use C(fixed_qos_options).
    type: str

  min_throughput:
    description:
      - Minimum throughput defined by this policy.
      - Not supported with REST, use C(fixed_qos_options).
    type: str

  is_shared:
    description:
      - Whether the SLOs of the policy group are shared between the workloads or if the SLOs are applied separately to each workload.
      - With REST, default value is False if not used in creating qos policy.
    type: bool
    version_added: 20.12.0

  force:
    type: bool
    description:
      - Setting to 'true' forces the deletion of the workloads associated with the policy group along with the policy group.
      - Not supported with REST.

  fixed_qos_options:
    version_added: 21.19.0
    type: dict
    description:
      - Set Minimum and Maximum throughput defined by this policy.
      - Only supported with REST and is ignored with ZAPI.
      - Required one of throughtput options when creating qos_policy.
    suboptions:
      max_throughput_iops:
        description:
          - Maximum throughput defined by this policy. It is specified in terms of IOPS.
          - 0 means no maximum throughput is enforced.
        type: int
        required: False
      max_throughput_mbps:
        description:
          - Maximum throughput defined by this policy. It is specified in terms of Mbps.
          - 0 means no maximum throughput is enforced.
        type: int
        required: False
      min_throughput_iops:
        description:
          - Minimum throughput defined by this policy. It is specified in terms of IOPS.
          - 0 means no minimum throughput is enforced.
          - These floors are not guaranteed on non-AFF platforms or when FabricPool tiering policies are set.
        type: int
        required: False
      min_throughput_mbps:
        description:
          - Minimum throughput defined by this policy. It is specified in terms of Mbps.
          - 0 means no minimum throughput is enforced.
          - Requires ONTAP 9.8 or later, and REST support.
        type: int
        required: False
'''

EXAMPLES = """
    - name: create qos policy group in ZAPI.
      netapp.ontap.na_ontap_qos_policy_group:
        state: present
        name: policy_1
        vserver: policy_vserver
        max_throughput: 800KB/s,800iops
        min_throughput: 100iops
        hostname: 10.193.78.30
        username: admin
        password: netapp1!
        use_rest: never

    - name: modify qos policy group max throughput in ZAPI.
      netapp.ontap.na_ontap_qos_policy_group:
        state: present
        name: policy_1
        vserver: policy_vserver
        max_throughput: 900KB/s,800iops
        min_throughput: 100iops
        hostname: 10.193.78.30
        username: admin
        password: netapp1!
        use_rest: never

    - name: delete qos policy group
      netapp.ontap.na_ontap_qos_policy_group:
        state: absent
        name: policy_1
        vserver: policy_vserver
        hostname: 10.193.78.30
        username: admin
        password: netapp1!

    - name: create qos policy group in REST.
      netapp.ontap.na_ontap_qos_policy_group:
        state: present
        name: policy_1
        vserver: policy_vserver
        hostname: 10.193.78.30
        username: admin
        password: netapp1!
        use_rest: always
        fixed_qos_options:
          max_throughput_iops: 800
          max_throughput_mbps: 200
          min_throughput_iops: 500
          min_throughput_mbps: 100

    - name: modify qos policy max_throughput in REST.
      netapp.ontap.na_ontap_qos_policy_group:
        state: present
        name: policy_1
        vserver: policy_vserver
        hostname: 10.193.78.30
        username: admin
        password: netapp1!
        use_rest: always
        fixed_qos_options:
          max_throughput_iops: 1000
          max_throughput_mbps: 300

"""

RETURN = """
"""

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic


class NetAppOntapQosPolicyGroup:
    """
    Create, delete, modify and rename a policy group.
    """
    def __init__(self):
        """
        Initialize the Ontap qos policy group class.
        """
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str'),
            from_name=dict(required=False, type='str'),
            vserver=dict(required=True, type='str'),
            max_throughput=dict(required=False, type='str'),
            min_throughput=dict(required=False, type='str'),
            is_shared=dict(required=False, type='bool'),
            force=dict(required=False, type='bool'),
            fixed_qos_options=dict(required=False, type='dict', options=dict(
                max_throughput_iops=dict(required=False, type='int'),
                max_throughput_mbps=dict(required=False, type='int'),
                min_throughput_iops=dict(required=False, type='int'),
                min_throughput_mbps=dict(required=False, type='int')
            ))
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True,
            mutually_exclusive=[
                ['max_throughput', 'fixed_qos_options'], ['min_throughput', 'fixed_qos_options']
            ]
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        # Set up Rest API
        self.rest_api = OntapRestAPI(self.module)
        unsupported_rest_properties = ['max_throughput', 'min_throughput', 'force']
        self.use_rest = self.rest_api.is_rest_supported_properties(self.parameters, unsupported_rest_properties)
        min_ontap_98 = self.rest_api.meets_rest_minimum_version(self.use_rest, 9, 8)
        if self.use_rest and not min_ontap_98 and self.na_helper.safe_get(self.parameters, ['fixed_qos_options', 'min_throughput_mbps']):
            self.module.fail_json("Minimum version of ONTAP for 'fixed_qos_options.min_throughput_mbps' is (9, 8, 0)")
        self.uuid = None

        if not self.use_rest:
            if not netapp_utils.has_netapp_lib():
                self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)
            if 'fixed_qos_options' in self.parameters:
                self.module.fail_json(msg="Error: 'fixed_qos_options' not supported with ZAPI, use 'max_throughput' and 'min_throughput'")
            # default value for force is false in ZAPI.
            self.parameters['force'] = False

    def get_policy_group(self, policy_group_name=None):
        """
        Return details of a policy group.
        :param policy_group_name: policy group name
        :return: policy group details.
        :rtype: dict.
        """
        if policy_group_name is None:
            policy_group_name = self.parameters['name']
        if self.use_rest:
            return self.get_policy_group_rest(policy_group_name)
        policy_group_get_iter = netapp_utils.zapi.NaElement('qos-policy-group-get-iter')
        policy_group_info = netapp_utils.zapi.NaElement('qos-policy-group-info')
        policy_group_info.add_new_child('policy-group', policy_group_name)
        policy_group_info.add_new_child('vserver', self.parameters['vserver'])
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(policy_group_info)
        policy_group_get_iter.add_child_elem(query)
        try:
            result = self.server.invoke_successfully(policy_group_get_iter, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching qos policy group %s: %s' %
                                  (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        policy_group_detail = None

        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) == 1:
            policy_info = result.get_child_by_name('attributes-list').get_child_by_name('qos-policy-group-info')

            policy_group_detail = {
                'name': policy_info.get_child_content('policy-group'),
                'vserver': policy_info.get_child_content('vserver'),
                'max_throughput': policy_info.get_child_content('max-throughput'),
                'min_throughput': policy_info.get_child_content('min-throughput'),
                'is_shared': self.na_helper.get_value_for_bool(True, policy_info.get_child_content('is-shared'))
            }
        return policy_group_detail

    def get_policy_group_rest(self, policy_group_name):
        api = 'storage/qos/policies'
        query = {
            'name': policy_group_name,
            'svm.name': self.parameters['vserver']
        }
        fields = 'name,svm,fixed'
        record, error = rest_generic.get_one_record(self.rest_api, api, query, fields)
        if error:
            self.module.fail_json(msg='Error fetching qos policy group %s: %s' %
                                  (self.parameters['name'], error))
        current = None
        if record:
            is_shared = record['fixed']['capacity_shared']
            self.uuid = record['uuid']
            current = {
                'name': record['name'],
                'vserver': record['svm']['name'],
                'fixed_qos_options': {},
                'is_shared': is_shared
            }
            for fixed_qos_options in ['max_throughput_iops', 'max_throughput_mbps', 'min_throughput_iops']:
                current['fixed_qos_options'][fixed_qos_options] = record['fixed'].get(fixed_qos_options)
            if self.na_helper.safe_get(self.parameters, ['fixed_qos_options', 'min_throughput_mbps']):
                current['fixed_qos_options']['min_throughput_mbps'] = record['fixed'].get('min_throughput_mbps')
        return current

    def create_policy_group(self):
        """
        create a policy group name.
        """
        if self.use_rest:
            return self.create_policy_group_rest()
        policy_group = netapp_utils.zapi.NaElement('qos-policy-group-create')
        policy_group.add_new_child('policy-group', self.parameters['name'])
        policy_group.add_new_child('vserver', self.parameters['vserver'])
        if self.parameters.get('max_throughput'):
            policy_group.add_new_child('max-throughput', self.parameters['max_throughput'])
        if self.parameters.get('min_throughput'):
            policy_group.add_new_child('min-throughput', self.parameters['min_throughput'])
        if self.parameters.get('is_shared') is not None:
            policy_group.add_new_child('is-shared', self.na_helper.get_value_for_bool(False, self.parameters['is_shared']))
        try:
            self.server.invoke_successfully(policy_group, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating qos policy group %s: %s' %
                                  (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def create_policy_group_rest(self):
        api = 'storage/qos/policies'
        body = {
            'name': self.parameters['name'],
            'svm.name': self.parameters['vserver']
        }
        body['fixed'] = self.na_helper.filter_out_none_entries(self.parameters['fixed_qos_options'])
        # default value for capacity shared is False in REST.
        body['fixed']['capacity_shared'] = self.parameters.get('is_shared', False)
        dummy, error = rest_generic.post_async(self.rest_api, api, body)
        if error:
            self.module.fail_json(msg='Error creating qos policy group %s: %s' %
                                  (self.parameters['name'], error))

    def delete_policy_group(self, policy_group=None):
        """
        delete an existing policy group.
        :param policy_group: policy group name.
        """
        if self.use_rest:
            return self.delete_policy_group_rest()
        if policy_group is None:
            policy_group = self.parameters['name']
        policy_group_obj = netapp_utils.zapi.NaElement('qos-policy-group-delete')
        policy_group_obj.add_new_child('policy-group', policy_group)
        if self.parameters.get('force'):
            policy_group_obj.add_new_child('force', str(self.parameters['force']))
        try:
            self.server.invoke_successfully(policy_group_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting qos policy group %s: %s' %
                                  (policy_group, to_native(error)),
                                  exception=traceback.format_exc())

    def delete_policy_group_rest(self):
        api = 'storage/qos/policies'
        dummy, error = rest_generic.delete_async(self.rest_api, api, self.uuid)
        if error:
            self.module.fail_json(msg='Error deleting qos policy group %s: %s' %
                                  (self.parameters['name'], error))

    def modify_policy_group(self):
        """
        Modify policy group.
        """
        if self.use_rest:
            return self.modify_policy_group_rest()
        policy_group_obj = netapp_utils.zapi.NaElement('qos-policy-group-modify')
        policy_group_obj.add_new_child('policy-group', self.parameters['name'])
        if self.parameters.get('max_throughput'):
            policy_group_obj.add_new_child('max-throughput', self.parameters['max_throughput'])
        if self.parameters.get('min_throughput'):
            policy_group_obj.add_new_child('min-throughput', self.parameters['min_throughput'])
        try:
            self.server.invoke_successfully(policy_group_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying qos policy group %s: %s' %
                                  (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_policy_group_rest(self):
        api = 'storage/qos/policies'
        body = {'fixed': self.na_helper.filter_out_none_entries(self.parameters['fixed_qos_options'])}
        dummy, error = rest_generic.patch_async(self.rest_api, api, self.uuid, body)
        if error:
            self.module.fail_json(msg='Error modifying qos policy group %s: %s' %
                                  (self.parameters['name'], error))

    def rename_policy_group(self):
        """
        Rename policy group name.
        """
        if self.use_rest:
            return self.rename_policy_group_rest()
        rename_obj = netapp_utils.zapi.NaElement('qos-policy-group-rename')
        rename_obj.add_new_child('new-name', self.parameters['name'])
        rename_obj.add_new_child('policy-group-name', self.parameters['from_name'])
        try:
            self.server.invoke_successfully(rename_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error renaming qos policy group %s: %s' %
                                  (self.parameters['from_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def rename_policy_group_rest(self):
        api = 'storage/qos/policies'
        body = {'name': self.parameters['name']}
        dummy, error = rest_generic.patch_async(self.rest_api, api, self.uuid, body)
        if error:
            self.module.fail_json(msg='Error renaming qos policy group %s: %s' %
                                  (self.parameters['from_name'], error))

    def modify_helper(self, modify):
        """
        helper method to modify policy group.
        :param modify: modified attributes.
        """
        if 'is_shared' in modify:
            self.module.fail_json(msg='Error cannot modify is_shared attribute.')
        if any(
            attribute in modify
            for attribute in ['max_throughput', 'min_throughput', 'fixed_qos_options']
        ):
            self.modify_policy_group()

    def apply(self):
        """
        Run module based on playbook
        """
        if not self.use_rest:
            self.asup_log_for_cserver("na_ontap_qos_policy_group")
        current = self.get_policy_group()
        rename, cd_action = None, None
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action == 'create' and self.parameters.get('from_name'):
            # create policy by renaming an existing one
            old_policy = self.get_policy_group(self.parameters['from_name'])
            rename = self.na_helper.is_rename_action(old_policy, current)
            if rename:
                current = old_policy
                cd_action = None
            if rename is None:
                self.module.fail_json(msg='Error renaming qos policy group: cannot find %s' %
                                      self.parameters['from_name'])
        modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.use_rest and cd_action == 'create' and self.parameters.get('fixed_qos_options') is None:
            self.module.fail_json(msg="Error: atleast one 'fixed_qos_options' required in creating qos_policy in REST")
        if self.na_helper.changed and not self.module.check_mode:
            if rename:
                self.rename_policy_group()
            if cd_action == 'create':
                self.create_policy_group()
            elif cd_action == 'delete':
                self.delete_policy_group()
            elif modify:
                self.modify_helper(modify)
        self.module.exit_json(changed=self.na_helper.changed)

    def asup_log_for_cserver(self, event_name):
        """
        Fetch admin vserver for the given cluster
        Create and Autosupport log event with the given module name
        :param event_name: Name of the event log
        :return: None
        """
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event(event_name, cserver)


def main():
    '''Apply vserver operations from playbook'''
    qos_policy_group = NetAppOntapQosPolicyGroup()
    qos_policy_group.apply()


if __name__ == '__main__':
    main()
