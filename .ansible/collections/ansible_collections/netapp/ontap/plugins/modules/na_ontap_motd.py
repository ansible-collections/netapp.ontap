#!/usr/bin/python

# (c) 2018-2025, NetApp, Inc
# (c) 2018 Piotr Olczak <piotr.olczak@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
module: na_ontap_motd
author:
  - Piotr Olczak (@dprts) <polczak@redhat.com>
  - NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap_zapi
short_description: Setup motd
description:
  - This module allows you to manipulate motd for a vserver
  - It also allows to manipulate motd at the cluster level by using the cluster vserver (cserver)
version_added: 2.7.0
options:
    state:
        description:
          - If C(state=present) sets MOTD given in I(message) C(state=absent) removes it.
        choices: ['present', 'absent']
        type: str
        default: present
    motd_message:
        description:
          - MOTD Text message.
          - message is deprecated and will be removed to avoid a conflict with an Ansible internal variable.
        type: str
        default: ''
        aliases:
          - message
    vserver:
        description:
          - The name of the SVM motd should be set for.
        required: true
        type: str
    show_cluster_motd:
        description:
          - Set to I(false) if Cluster-level Message of the Day should not be shown
        type: bool
        default: True

notes:
  - This module is deprecated and only supports ZAPI.
  - Please use netapp.ontap.na_ontap_login_messages both for ZAPI and REST.

'''

EXAMPLES = '''
- name: Set Cluster-Level MOTD
  netapp.ontap.na_ontap_motd:
    vserver: my_ontap_cluster
    motd_message: "Cluster wide MOTD"
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    state: present
    https: true

- name: Set MOTD for I(rhev_nfs_krb) SVM, do not show Cluster-Level MOTD
  netapp.ontap.na_ontap_motd:
    vserver: rhev_nfs_krb
    motd_message: "Access to rhev_nfs_krb is also restricted"
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    state: present
    show_cluster_motd: false
    https: true

- name: Remove Cluster-Level MOTD
  netapp.ontap.na_ontap_motd:
    vserver: my_ontap_cluster
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    state: absent
    https: true
'''

RETURN = '''

'''

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule


class NetAppONTAPMotd:

    def __init__(self):
        argument_spec = netapp_utils.na_ontap_zapi_only_spec()
        argument_spec.update(dict(
            state=dict(required=False, type='str', default='present', choices=['present', 'absent']),
            vserver=dict(required=True, type='str'),
            motd_message=dict(default='', type='str', aliases=['message']),
            show_cluster_motd=dict(default=True, type='bool')
        ))

        self.module = AnsibleModule(
            argument_spec=argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.na_helper.module_replaces('na_ontap_login_messages', self.module)

        msg = 'netapp.ontap.na_ontap_motd is deprecated and only supports ZAPI.  Please use netapp.ontap.na_ontap_login_messages.'
        if self.parameters['use_rest'].lower() == 'never':
            self.module.warn(msg)
        else:
            self.na_helper.fall_back_to_zapi(self.module, msg, self.parameters)
        if 'message' in self.parameters:
            self.module.warn('Error: "message" option conflicts with Ansible internal variable - please use "motd_message".')

        if not netapp_utils.has_netapp_lib():
            self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())

        self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def motd_get_iter(self):
        """
        Compose NaElement object to query current motd
        :return: NaElement object for vserver-motd-get-iter
        """
        motd_get_iter = netapp_utils.zapi.NaElement('vserver-motd-get-iter')
        query = netapp_utils.zapi.NaElement('query')
        motd_info = netapp_utils.zapi.NaElement('vserver-motd-info')
        motd_info.add_new_child('is-cluster-message-enabled', str(self.parameters['show_cluster_motd']))
        motd_info.add_new_child('vserver', self.parameters['vserver'])
        query.add_child_elem(motd_info)
        motd_get_iter.add_child_elem(query)
        return motd_get_iter

    def motd_get(self):
        """
        Get current motd
        :return: Dictionary of current motd details if query successful, else None
        """
        motd_get_iter = self.motd_get_iter()
        motd_result = {}
        try:
            result = self.server.invoke_successfully(motd_get_iter, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching motd info: %s' % to_native(error),
                                  exception=traceback.format_exc())
        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) > 0:
            motd_info = result.get_child_by_name('attributes-list').get_child_by_name(
                'vserver-motd-info')
            motd_result['motd_message'] = motd_info.get_child_content('message')
            motd_result['motd_message'] = str(motd_result['motd_message']).rstrip()
            motd_result['show_cluster_motd'] = motd_info.get_child_content('is-cluster-message-enabled') == 'true'
            motd_result['vserver'] = motd_info.get_child_content('vserver')
            return motd_result
        return None

    def modify_motd(self):
        motd_create = netapp_utils.zapi.NaElement('vserver-motd-modify-iter')
        motd_create.add_new_child('message', self.parameters['motd_message'])
        motd_create.add_new_child(
            'is-cluster-message-enabled', 'true' if self.parameters['show_cluster_motd'] is True else 'false')
        query = netapp_utils.zapi.NaElement('query')
        motd_info = netapp_utils.zapi.NaElement('vserver-motd-info')
        motd_info.add_new_child('vserver', self.parameters['vserver'])
        query.add_child_elem(motd_info)
        motd_create.add_child_elem(query)
        try:
            self.server.invoke_successfully(motd_create, enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as err:
            self.module.fail_json(msg="Error creating motd: %s" % (to_native(err)), exception=traceback.format_exc())
        return motd_create

    def apply(self):
        """
        Applies action from playbook
        """
        current = self.motd_get()
        if self.parameters['state'] == 'absent':
            # Just make sure it is empty
            self.parameters['motd_message'] = ''
            if current and current['motd_message'] == 'None':
                current = None
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action is None and self.parameters['state'] == 'present':
            self.na_helper.get_modified_attributes(current, self.parameters)

        if self.na_helper.changed and not self.module.check_mode:
            self.modify_motd()
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    motd_obj = NetAppONTAPMotd()
    motd_obj.apply()


if __name__ == '__main__':
    main()
