#!/usr/bin/python

# (c) 2019-2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = """
module: na_ontap_snapmirror_policy
short_description: NetApp ONTAP create, delete or modify SnapMirror policies
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '20.3.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- NetApp ONTAP create, modify, or destroy the SnapMirror policy
options:
  state:
    description:
    - Whether the specified SnapMirror policy should exist or not.
    choices: ['present', 'absent']
    default: present
    type: str
  vserver:
    description:
    - Specifies the vserver for the SnapMirror policy.
    required: true
    type: str
  policy_name:
    description:
    - Specifies the SnapMirror policy name.
    required: true
    type: str
  policy_type:
    description:
    - Specifies the SnapMirror policy type. Modifying the type of an existing SnapMirror policy is not supported
    choices: ['vault', 'async_mirror', 'mirror_vault', 'strict_sync_mirror', 'sync_mirror']
    default: async_mirror
    type: str
  comment:
    description:
    - Specifies the SnapMirror policy comment.
    type: str
  tries:
    description:
    - Specifies the number of tries.
    default: 8
    type: str
  transfer_priority:
    description:
    - Specifies the priority at which a SnapMirror transfer runs.
    choices: ['low', 'normal']
    default: normal
    type: str
  common_snapshot_schedule:
    description:
    - Specifies the common Snapshot copy schedule associated with the policy, only required for strict_sync_mirror and sync_mirror.
    type: str
  owner:
    description:
    - Specifies the owner of the SnapMirror policy.
    choices: ['cluster_admin', 'vserver_admin']
    type: str
  is_network_compression_enabled:
    description:
    - Specifies whether network compression is enabled for transfers.
    type: bool
  ignore_atime:
    description:
    - Specifies whether incremental transfers will ignore files which have only their access time changed. Applies to SnapMirror vault relationships only.
    type: bool
  restart:
    description:
    - Defines the behavior of SnapMirror if an interrupted transfer exists, applies to data protection only.
    choices: ['always', 'never', 'default']
    default: always
    type: str
"""

EXAMPLES = """
    - name: Create SnapMirror policy
      na_ontap_snapmirror_policy:
        state: present
        vserver: "SVM1"
        policy_name: "ansible_policy"
        policy_type: "mirror_vault"
        comment: "created by ansible"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Modify SnapMirror policy
      na_ontap_snapmirror_policy:
        state: present
        vserver: "SVM1"
        policy_name: "ansible_policy"
        policy_type: "async_mirror"
        transfer_priority: "low"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Delete SnapMirror policy
      na_ontap_snapmirror_policy:
        state: absent
        vserver: "SVM1"
        policy_type: "async_mirror"
        policy_name: "ansible_policy"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false
"""

RETURN = """

"""

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapSnapMirrorPolicy(object):
    """
        Create, Modifies and Destroys a SnapMirror policy
    """
    def __init__(self):
        """
            Initialize the Ontap SnapMirror policy class
        """

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            vserver=dict(required=True, type='str'),
            policy_name=dict(required=True, type='str'),
            comment=dict(required=False, type='str'),
            policy_type=dict(required=False, type='str', default='async_mirror',
                             choices=['vault', 'async_mirror', 'mirror_vault', 'strict_sync_mirror', 'sync_mirror']),
            tries=dict(required=False, type='str', default='8'),
            transfer_priority=dict(required=False, type='str', choices=['low', 'normal'], default='normal'),
            common_snapshot_schedule=dict(required=False, type='str'),
            ignore_atime=dict(required=False, type='bool'),
            is_network_compression_enabled=dict(required=False, type='bool'),
            owner=dict(required=False, type='str', choices=['cluster_admin', 'vserver_admin']),
            restart=dict(required=False, type='str', choices=['always', 'never', 'default'], default='always'),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        # set up variables
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg='The python NetApp-Lib module is required')
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])
        return

    def get_snapmirror_policy(self):

        return_value = None

        snapmirror_policy_get_iter = netapp_utils.zapi.NaElement('snapmirror-policy-get-iter')
        snapmirror_policy_info = netapp_utils.zapi.NaElement('snapmirror-policy-info')
        snapmirror_policy_info.add_new_child('policy-name', self.parameters['policy_name'])
        snapmirror_policy_info.add_new_child('vserver', self.parameters['vserver'])
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(snapmirror_policy_info)
        snapmirror_policy_get_iter.add_child_elem(query)

        try:
            result = self.server.invoke_successfully(snapmirror_policy_get_iter, True)
            if result.get_child_by_name('attributes-list'):
                snapmirror_policy_attributes = result['attributes-list']['snapmirror-policy-info']

                return_value = {
                    'policy_name': snapmirror_policy_attributes['policy-name'],
                    'tries': snapmirror_policy_attributes['tries'],
                    'transfer_priority': snapmirror_policy_attributes['transfer-priority'],
                    'is_network_compression_enabled': snapmirror_policy_attributes['is-network-compression-enabled'],
                    'restart': snapmirror_policy_attributes['restart'],
                    'ignore_atime': snapmirror_policy_attributes['ignore-atime'],
                    'vserver': snapmirror_policy_attributes['vserver-name'],
                }
                if snapmirror_policy_attributes.get_child_content('comment') is not None:
                    return_value['comment'] = snapmirror_policy_attributes['comment']

                if snapmirror_policy_attributes.get_child_content('type') is not None:
                    return_value['policy_type'] = snapmirror_policy_attributes['type']

        except netapp_utils.zapi.NaApiError as error:
            if 'NetApp API failed. Reason - 13001:' in to_native(error):
                # Policy does not exist
                pass
            else:
                self.module.fail_json(msg='Error getting snapmirror policy %s: %s' % (self.parameters['policy_name'], to_native(error)),
                                      exception=traceback.format_exc())

        return return_value

    def create_snapmirror_policy(self):
        """
        Creates a new storage efficiency policy
        """
        snapmirror_policy_obj = netapp_utils.zapi.NaElement("snapmirror-policy-create")
        snapmirror_policy_obj.add_new_child("policy-name", self.parameters['policy_name'])
        if 'policy_type' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("type", self.parameters['policy_type'])
        snapmirror_policy_obj = self.create_snapmirror_policy_obj(snapmirror_policy_obj)

        try:
            self.server.invoke_successfully(snapmirror_policy_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating snapmirror policy %s: %s' % (self.parameters['policy_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def create_snapmirror_policy_obj(self, snapmirror_policy_obj):
        if 'comment' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("comment", self.parameters['comment'])
        if 'common_snapshot_schedule' in self.parameters.keys() and 'sync_mirror' in self.parameters['policy_type']:
            snapmirror_policy_obj.add_new_child("common-snapshot-schedule", self.parameters['common_snapshot_schedule'])
        if 'ignore_atime' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("ignore-atime", self.parameters['ignore_atime'])
        if 'is_network_compression_enabled' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("is-network-compression-enabled", self.parameters['is_network_compression_enabled'])
        if 'owner' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("owner", self.parameters['owner'])
        if 'restart' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("restart", self.parameters['restart'])
        if 'transfer_priority' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("transfer-priority", self.parameters['transfer_priority'])
        if 'tries' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("tries", self.parameters['tries'])
        return snapmirror_policy_obj

    def delete_snapmirror_policy(self):
        """
        Deletes a snapmirror policy
        """
        snapmirror_policy_obj = netapp_utils.zapi.NaElement("snapmirror-policy-delete")
        snapmirror_policy_obj.add_new_child("policy-name", self.parameters['policy_name'])

        try:
            self.server.invoke_successfully(snapmirror_policy_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting snapmirror policy %s: %s' % (self.parameters['policy_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_snapmirror_policy(self):
        """
        Modifies a snapmirror policy
        """
        snapmirror_policy_obj = netapp_utils.zapi.NaElement("snapmirror-policy-modify")
        snapmirror_policy_obj.add_new_child("policy-name", self.parameters['policy_name'])
        snapmirror_policy_obj = self.create_snapmirror_policy_obj(snapmirror_policy_obj)

        try:
            self.server.invoke_successfully(snapmirror_policy_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying snapmirror policy %s: %s' % (self.parameters['policy_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def asup_log_for_cserver(self):
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("snapmirror_policy", cserver)

    def apply(self):
        self.asup_log_for_cserver()
        current, modify = self.get_snapmirror_policy(), None
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if current and cd_action is None and self.parameters['state'] == 'present':
            self.parameters['policy_type'] = current['policy_type']
            modify = self.na_helper.get_modified_attributes(current, self.parameters)

        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if cd_action == 'create':
                    self.create_snapmirror_policy()
                elif cd_action == 'delete':
                    self.delete_snapmirror_policy()
                elif modify:
                    self.modify_snapmirror_policy()
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """
    Creates the NetApp Ontap SnapMirror policy object and runs the correct play task
    """
    obj = NetAppOntapSnapMirrorPolicy()
    obj.apply()


if __name__ == '__main__':
    main()
