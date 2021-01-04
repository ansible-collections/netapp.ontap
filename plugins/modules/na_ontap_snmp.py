#!/usr/bin/python
"""
create SNMP module to add/delete/modify SNMP user
"""

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - "Create/Delete SNMP community"
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
module: na_ontap_snmp
options:
  access_control:
    choices: ['ro']
    description:
      - "Access control for the community. The only supported value is 'ro' (read-only)"
    default: 'ro'
    type: str
  community_name:
    description:
      - "The name of the SNMP community to manage."
    required: true
    type: str
  state:
    choices: ['present', 'absent']
    description:
      - "Whether the specified SNMP community should exist or not."
    default: 'present'
    type: str
short_description: NetApp ONTAP SNMP community
version_added: 2.6.0
'''

EXAMPLES = """
    - name: Create SNMP community
      na_ontap_snmp:
        state: present
        community_name: communityName
        access_control: 'ro'
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Delete SNMP community
      na_ontap_snmp:
        state: absent
        community_name: communityName
        access_control: 'ro'
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
"""

RETURN = """
"""
import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppONTAPSnmp(object):
    '''Class with SNMP methods, doesn't support check mode'''

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            community_name=dict(required=True, type='str'),
            access_control=dict(required=False, type='str', choices=['ro'], default='ro'),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()

        # set up state variables
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def invoke_snmp_community(self, zapi):
        """
        Invoke zapi - add/delete take the same NaElement structure
        @return: SUCCESS / FAILURE with an error_message
        """
        snmp_community = netapp_utils.zapi.NaElement.create_node_with_children(
            zapi, **{'community': self.parameters['community_name'],
                     'access-control': self.parameters['access_control']})
        try:
            self.server.invoke_successfully(snmp_community, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            if zapi == 'snmp-community-add':
                action = 'adding'
            elif zapi == 'snmp-community-delete':
                action = 'deleting'
            else:
                action = 'unexpected'
            self.module.fail_json(msg='Error %s community %s: %s' % (action, self.parameters['community_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def get_snmp(self):
        """
        Check if SNMP community exists
        """
        snmp_obj = netapp_utils.zapi.NaElement('snmp-status')
        try:
            result = self.server.invoke_successfully(snmp_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg=to_native(error), exception=traceback.format_exc())
        if result.get_child_by_name('communities') is not None:
            for snmp_entry in result.get_child_by_name('communities').get_children():
                community_name = snmp_entry.get_child_content('community')
                if community_name == self.parameters['community_name']:
                    return_values = {'community_name': snmp_entry.get_child_content('community'),
                                     'access_control': snmp_entry.get_child_content('access-control')}
                    return return_values
        return None

    def add_snmp_community(self):
        """
        Adds a SNMP community
        """
        return self.invoke_snmp_community('snmp-community-add')

    def delete_snmp_community(self):
        """
        Delete a SNMP community
        """
        return self.invoke_snmp_community('snmp-community-delete')

    def apply(self):
        """
        Apply action to SNMP community
        This module is not idempotent:
        Add doesn't fail the playbook if user is trying
        to add an already existing snmp community
        """
        changed = False
        current = self.get_snmp()
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("na_ontap_snmp", cserver)
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.add_snmp_community()
            elif cd_action == 'delete':
                self.delete_snmp_community()

        self.module.exit_json(changed=self.na_helper.changed)


def main():
    '''Execute action'''
    community_obj = NetAppONTAPSnmp()
    community_obj.apply()


if __name__ == '__main__':
    main()
