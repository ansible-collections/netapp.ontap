#!/usr/bin/python

# (c) 2019-2022, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''

module: na_ontap_security_key_manager

short_description: NetApp ONTAP security key manager.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.8.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
- Add or delete or setup key management on NetApp ONTAP.

options:

  state:
    description:
      - Whether the specified key manager should exist or not.
    choices: ['present', 'absent']
    type: str
    default: 'present'

  ip_address:
    description:
      - The IP address of the key management server.
    required: true
    type: str

  tcp_port:
    description:
      - The TCP port on which the key management server listens for incoming connections.
    default: 5696
    type: int

  node:
    description:
      - The node which key management server runs on.
      - Ignored, a warning is raised if present.
      - Deprecated as of 21.22.0, as it was never used.
    type: str

notes:
  - Though C(node) is accepted as a parameter, it is not used in the module.
  - Supports check_mode.
  - Only supported at cluster level.
'''

EXAMPLES = """

    - name: Delete Key Manager
      tags:
      - delete
      netapp.ontap.na_ontap_security_key_manager:
        state: absent
        hostname: "{{ hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: False
        ip_address: 0.0.0.0

    - name: Add Key Manager
      tags:
      - add
      netapp.ontap.na_ontap_security_key_manager:
        state: present
        hostname: "{{ hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: False
        ip_address: 0.0.0.0

"""

RETURN = """
"""

import traceback
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native


class NetAppOntapSecurityKeyManager(object):
    '''class with key manager operations'''

    def __init__(self):
        '''Initialize module parameters'''
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            ip_address=dict(required=True, type='str'),
            node=dict(required=False, type='str'),
            tcp_port=dict(required=False, type='int', default=5696)
        )
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        if 'node' in self.parameters:
            self.module.warn('The option "node" is deprecated and should not be used.')

        if not netapp_utils.has_netapp_lib():
            self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
        self.cluster = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def get_key_manager(self):
        """
        get key manager by ip address.
        :return: a dict of key manager
        """
        key_manager_info = netapp_utils.zapi.NaElement('security-key-manager-get-iter')
        query_details = netapp_utils.zapi.NaElement.create_node_with_children(
            'key-manager-info', **{'key-manager-ip-address': self.parameters['ip_address']})
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(query_details)
        key_manager_info.add_child_elem(query)

        try:
            result = self.cluster.invoke_successfully(key_manager_info, enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching key manager: %s' % to_native(error),
                                  exception=traceback.format_exc())

        return_value = None
        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) > 0:
            key_manager = result.get_child_by_name('attributes-list').get_child_by_name('key-manager-info')
            return_value = {}
            if key_manager.get_child_by_name('key-manager-ip-address'):
                return_value['ip_address'] = key_manager.get_child_content('key-manager-ip-address')
            if key_manager.get_child_by_name('key-manager-server-status'):
                return_value['server_status'] = key_manager.get_child_content('key-manager-server-status')
            if key_manager.get_child_by_name('key-manager-tcp-port'):
                return_value['tcp_port'] = key_manager.get_child_content('key-manager-tcp-port')

        return return_value

    def key_manager_setup(self):
        """
        set up external key manager.
        """
        key_manager_setup = netapp_utils.zapi.NaElement('security-key-manager-setup')
        # if specify on-boarding passphrase, it is on-boarding key management.
        # it not, then it's external key management.
        try:
            self.cluster.invoke_successfully(key_manager_setup, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error setting up key manager: %s' % to_native(error),
                                  exception=traceback.format_exc())

    def create_key_manager(self):
        """
        add key manager.
        """
        key_manager_create = netapp_utils.zapi.NaElement('security-key-manager-add')
        key_manager_create.add_new_child('key-manager-ip-address', self.parameters['ip_address'])
        if self.parameters.get('tcp_port'):
            key_manager_create.add_new_child('key-manager-tcp-port', str(self.parameters['tcp_port']))
        try:
            self.cluster.invoke_successfully(key_manager_create, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating key manager: %s' % to_native(error),
                                  exception=traceback.format_exc())

    def delete_key_manager(self):
        """
        delete key manager.
        """
        key_manager_delete = netapp_utils.zapi.NaElement('security-key-manager-delete')
        key_manager_delete.add_new_child('key-manager-ip-address', self.parameters['ip_address'])
        try:
            self.cluster.invoke_successfully(key_manager_delete, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting key manager: %s' % to_native(error),
                                  exception=traceback.format_exc())

    def apply(self):
        netapp_utils.ems_log_event_cserver("na_ontap_security_key_manager", self.cluster, self.module)
        self.key_manager_setup()
        current = self.get_key_manager()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.create_key_manager()
            elif cd_action == 'delete':
                self.delete_key_manager()
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    '''Apply volume operations from playbook'''
    obj = NetAppOntapSecurityKeyManager()
    obj.apply()


if __name__ == '__main__':
    main()
