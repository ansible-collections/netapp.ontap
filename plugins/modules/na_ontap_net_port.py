#!/usr/bin/python

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

'''
na_ontap_net_port
'''

DOCUMENTATION = """
module: na_ontap_net_port
short_description: NetApp ONTAP network ports.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Modify a ONTAP network port.
options:
  state:
    description:
    - Whether the specified net port should exist or not.
    choices: ['present']
    type: str
    default: present
  node:
    description:
    - Specifies the name of node.
    required: true
    type: str
  ports:
    aliases:
    - port
    description:
    - Specifies the name of port(s).
    required: true
    type: list
    elements: str
  mtu:
    description:
    - Specifies the maximum transmission unit (MTU) reported by the port.
    type: int
  autonegotiate_admin:
    description:
    - Enables or disables Ethernet auto-negotiation of speed,
      duplex and flow control.
    type: bool
  duplex_admin:
    description:
    - Specifies the user preferred duplex setting of the port.
    - Valid values auto, half, full
    type: str
  speed_admin:
    description:
    - Specifies the user preferred speed setting of the port.
    type: str
  flowcontrol_admin:
    description:
    - Specifies the user preferred flow control setting of the port.
    type: str
  ipspace:
    description:
    - Specifies the port's associated IPspace name.
    - The 'Cluster' ipspace is reserved for cluster ports.
    type: str
  up_admin:
    description:
    - Enables or disables the port.
    type: bool
    version_added: 21.8.0
"""

EXAMPLES = """
    - name: Modify Net Port
      netapp.ontap.na_ontap_net_port:
        state: present
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        hostname: "{{ netapp_hostname }}"
        node: "{{ node_name }}"
        ports: e0d,e0c
        autonegotiate_admin: true
        up_admin: true
        mtu: 1500
"""

RETURN = """

"""
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule


class NetAppOntapNetPort():
    """
        Modify a Net port
    """

    def __init__(self):
        """
            Initialize the Ontap Net Port Class
        """
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present'], default='present'),
            node=dict(required=True, type="str"),
            ports=dict(required=True, type='list', elements='str', aliases=['port']),
            mtu=dict(required=False, type="int", default=None),
            autonegotiate_admin=dict(required=False, type="bool", default=None),
            up_admin=dict(required=False, type="bool", default=None),
            duplex_admin=dict(required=False, type="str", default=None),
            speed_admin=dict(required=False, type="str", default=None),
            flowcontrol_admin=dict(required=False, type="str", default=None),
            ipspace=dict(required=False, type="str", default=None),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.set_playbook_zapi_key_map()

        if not netapp_utils.has_netapp_lib():
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)
        return

    def set_playbook_zapi_key_map(self):
        self.na_helper.zapi_string_keys = {
            'duplex_admin': 'administrative-duplex',
            'speed_admin': 'administrative-speed',
            'flowcontrol_admin': 'administrative-flowcontrol',
            'ipspace': 'ipspace'
        }
        self.na_helper.zapi_bool_keys = {
            'up_admin': 'is-administrative-up',
            'autonegotiate_admin': 'is-administrative-auto-negotiate',
        }
        self.na_helper.zapi_int_keys = {
            'mtu': 'mtu',
        }

    def get_net_port(self, port):
        """
        Return details about the net port
        :param: port: Name of the port
        :return: Dictionary with current state of the port. None if not found.
        :rtype: dict
        """
        net_port_get = netapp_utils.zapi.NaElement('net-port-get-iter')
        attributes = {
            'query': {
                'net-port-info': {
                    'node': self.parameters['node'],
                    'port': port
                }
            }
        }
        net_port_get.translate_struct(attributes)

        try:
            result = self.server.invoke_successfully(net_port_get, True)
            if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) >= 1:
                port_info = result['attributes-list']['net-port-info']
                port_details = dict()
            else:
                return None
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error getting net ports for %s: %s' % (self.parameters['node'], to_native(error)),
                                  exception=traceback.format_exc())

        for item_key, zapi_key in self.na_helper.zapi_bool_keys.items():
            port_details[item_key] = self.na_helper.get_value_for_bool(from_zapi=True, value=port_info.get_child_content(zapi_key))
        for item_key, zapi_key in self.na_helper.zapi_int_keys.items():
            port_details[item_key] = self.na_helper.get_value_for_int(from_zapi=True, value=port_info.get_child_content(zapi_key))
        for item_key, zapi_key in self.na_helper.zapi_string_keys.items():
            port_details[item_key] = port_info.get_child_content(zapi_key)
        return port_details

    def modify_net_port(self, port, modify):
        """
        Modify a port

        :param port: Name of the port
        :param modify: dict with attributes to be modified
        :return: None
        """

        def get_zapi_key_and_value(key, value):
            zapi_key = self.na_helper.zapi_string_keys.get(key)
            if zapi_key is not None:
                return zapi_key, value
            zapi_key = self.na_helper.zapi_bool_keys.get(key)
            if zapi_key is not None:
                return zapi_key, self.na_helper.get_value_for_bool(from_zapi=False, value=value)
            zapi_key = self.na_helper.zapi_int_keys.get(key)
            if zapi_key is not None:
                return zapi_key, self.na_helper.get_value_for_int(from_zapi=False, value=value)
            raise KeyError(key)

        port_modify = netapp_utils.zapi.NaElement('net-port-modify')
        port_attributes = {'node': self.parameters['node'],
                           'port': port}
        for key, value in modify.items():
            zapi_key, value = get_zapi_key_and_value(key, value)
            port_attributes[zapi_key] = value
        port_modify.translate_struct(port_attributes)
        try:
            self.server.invoke_successfully(port_modify, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying net ports for %s: %s' % (self.parameters['node'], to_native(error)),
                                  exception=traceback.format_exc())

    def autosupport_log(self):
        """
        AutoSupport log for na_ontap_net_port
        :return: None
        """
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("na_ontap_net_port", cserver)

    def apply(self):
        """
        Run Module based on play book
        """

        self.autosupport_log()
        # Run the task for all ports in the list of 'ports'
        missing_ports = list()
        modified = dict()
        for port in self.parameters['ports']:
            current = self.get_net_port(port)
            if current is None:
                missing_ports.append(port)
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
            modified[port] = modify
            if modify and not self.module.check_mode:
                self.modify_net_port(port, modify)
        if missing_ports:
            plural, suffix = '', '.'
            if len(missing_ports) == len(self.parameters['ports']):
                suffix = ' - check node name.'
            if len(missing_ports) > 1:
                plural = 's'
            self.module.fail_json(changed=self.na_helper.changed, modify=modified,
                                  msg='Error: port%s: %s not found on node: %s%s'
                                  % (plural, ', '.join(missing_ports), self.parameters['node'], suffix))
        self.module.exit_json(changed=self.na_helper.changed, modify=modified)


def main():
    """
    Create the NetApp Ontap Net Port Object and modify it
    """
    obj = NetAppOntapNetPort()
    obj.apply()


if __name__ == '__main__':
    main()
