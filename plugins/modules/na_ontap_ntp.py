#!/usr/bin/python

# (c) 2018-2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = """
module: na_ontap_ntp
short_description: NetApp ONTAP NTP server
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Create or delete or modify NTP server in ONTAP
options:
  state:
    description:
    - Whether the specified NTP server should exist or not.
    choices: ['present', 'absent']
    type: str
    default: 'present'
  server_name:
    description:
    - The name of the NTP server to manage.
    required: True
    type: str
  version:
    description:
    - give version for NTP server
    choices: ['auto', '3', '4']
    default: 'auto'
    type: str
"""

EXAMPLES = """
    - name: Create NTP server
      na_ontap_ntp:
        state: present
        version: auto
        server_name: "{{ server_name }}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Delete NTP server
      na_ontap_ntp:
        state: absent
        server_name: "{{ server_name }}"
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


class NetAppOntapNTPServer(object):
    """ object initialize and class methods """
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            server_name=dict(required=True, type='str'),
            version=dict(required=False, type='str', default='auto',
                         choices=['auto', '3', '4']),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(
                msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def get_ntp_server(self):
        """
        Return details about the ntp server
        :param:
            name : Name of the server_name
        :return: Details about the ntp server. None if not found.
        :rtype: dict
        """
        ntp_iter = netapp_utils.zapi.NaElement('ntp-server-get-iter')
        ntp_info = netapp_utils.zapi.NaElement('ntp-server-info')
        ntp_info.add_new_child('server-name', self.parameters['server_name'])

        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(ntp_info)

        ntp_iter.add_child_elem(query)
        result = self.server.invoke_successfully(ntp_iter, True)
        return_value = None

        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) == 1:

            ntp_server_name = result.get_child_by_name('attributes-list').\
                get_child_by_name('ntp-server-info').\
                get_child_content('server-name')
            server_version = result.get_child_by_name('attributes-list').\
                get_child_by_name('ntp-server-info').\
                get_child_content('version')
            return_value = {
                'server-name': ntp_server_name,
                'version': server_version
            }

        return return_value

    def create_ntp_server(self):
        """
        create ntp server.
        """
        ntp_server_create = netapp_utils.zapi.NaElement.create_node_with_children(
            'ntp-server-create', **{'server-name': self.parameters['server_name'],
                                    'version': self.parameters['version']
                                    })

        try:
            self.server.invoke_successfully(ntp_server_create,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating ntp server %s: %s'
                                  % (self.parameters['server_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def delete_ntp_server(self):
        """
        delete ntp server.
        """
        ntp_server_delete = netapp_utils.zapi.NaElement.create_node_with_children(
            'ntp-server-delete', **{'server-name': self.parameters['server_name']})

        try:
            self.server.invoke_successfully(ntp_server_delete,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting ntp server %s: %s'
                                  % (self.parameters['server_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_version(self):
        """
        modify the version.
        """
        ntp_modify_versoin = netapp_utils.zapi.NaElement.create_node_with_children(
            'ntp-server-modify',
            **{'server-name': self.parameters['server_name'], 'version': self.parameters['version']})
        try:
            self.server.invoke_successfully(ntp_modify_versoin,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying version for ntp server %s: %s'
                                  % (self.parameters['server_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def apply(self):
        """Apply action to ntp-server"""

        modify = None
        netapp_utils.ems_log_event_cserver("na_ontap_ntp", self.server, self.module)
        current = self.get_ntp_server()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action is None and self.parameters['state'] == 'present':
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.create_ntp_server()
            elif cd_action == 'delete':
                self.delete_ntp_server()
            elif modify:
                self.modify_version()
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """ Create object and call apply """
    ntp_obj = NetAppOntapNTPServer()
    ntp_obj.apply()


if __name__ == '__main__':
    main()
