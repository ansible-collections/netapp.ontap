#!/usr/bin/python

# (c) 2018-2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_export_policy_rule
'''

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
module: na_ontap_interface
short_description: NetApp ONTAP LIF configuration
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
    - Creating / deleting and modifying the LIF.

options:
  state:
    description:
    - Whether the specified interface should exist or not.
    choices: ['present', 'absent']
    default: 'present'
    type: str

  interface_name:
    description:
    - Specifies the logical interface (LIF) name.
    required: true
    type: str

  home_node:
    description:
    - Specifies the LIF's home node.
    - By default, the first node from the cluster is considered as home node
    type: str

  current_node:
    description:
    - Specifies the LIF's current node.
    - By default, this is home_node
    type: str

  home_port:
    description:
    - Specifies the LIF's home port.
    - Required when C(state=present)
    type: str

  current_port:
    description:
    - Specifies the LIF's current port.
    type: str

  role:
    description:
    - Specifies the role of the LIF.
    - When setting role as "intercluster" or "cluster", setting protocol is not supported.
    - When creating a "cluster" role, the node name will appear as the prefix in the name of LIF.
    - For example, if the specified name is clif and node name is node1, the LIF name appears in the ONTAP as node1_clif.
    - Possible values are 'undef', 'cluster', 'data', 'node-mgmt', 'intercluster', 'cluster-mgmt'.
    - Required when C(state=present) unless service_policy is present and ONTAP version is 9.8 or better.
    type: str

  address:
    description:
    - Specifies the LIF's IP address.
    - Required when C(state=present) and is_ipv4_link_local if false and subnet_name is not set.
    type: str

  netmask:
    description:
    - Specifies the LIF's netmask.
    - Required when C(state=present) and is_ipv4_link_local if false and subnet_name is not set.
    type: str

  is_ipv4_link_local:
    description:
    - Specifies the LIF's are to acquire a ipv4 link local address.
    - Use case for this is when creating Cluster LIFs to allow for auto assignment of ipv4 link local address.
    version_added: '20.1.0'
    type: bool

  vserver:
    description:
    - The name of the vserver to use.
    required: true
    type: str

  firewall_policy:
    description:
    - Specifies the firewall policy for the LIF.
    type: str

  failover_policy:
    description:
    - Specifies the failover policy for the LIF.
    choices: ['disabled', 'system-defined', 'local-only', 'sfo-partner-only', 'broadcast-domain-wide']
    type: str

  failover_group:
    description:
    - Specifies the failover group for the LIF.
    version_added: '20.1.0'
    type: str

  subnet_name:
    description:
    - Subnet where the interface address is allocated from.
    - If the option is not used, the IP address will need to be provided by the administrator during configuration.
    version_added: 2.8.0
    type: str

  admin_status:
    choices: ['up', 'down']
    description:
    - Specifies the administrative status of the LIF.
    type: str

  is_auto_revert:
    description:
    - If true, data LIF will revert to its home node under certain circumstances such as startup,
    - and load balancing migration capability is disabled automatically
    type: bool

  force_subnet_association:
    description:
    - Set this to true to acquire the address from the named subnet and assign the subnet to the LIF.
    version_added: 2.9.0
    type: bool

  protocols:
    description:
    - Specifies the list of data protocols configured on the LIF. By default, the values in this element are nfs, cifs and fcache.
    - Other supported protocols are iscsi and fcp. A LIF can be configured to not support any data protocols by specifying 'none'.
    - Protocol values of none, iscsi, fc-nvme or fcp can't be combined with any other data protocol(s).
    - address, netmask and firewall_policy parameters are not supported for 'fc-nvme' option.
    type: list
    elements: str

  dns_domain_name:
    description:
    - Specifies the unique, fully qualified domain name of the DNS zone of this LIF.
    version_added: 2.9.0
    type: str

  listen_for_dns_query:
    description:
    - If True, this IP address will listen for DNS queries for the dnszone specified.
    version_added: 2.9.0
    type: bool

  is_dns_update_enabled:
    description:
    - Specifies if DNS update is enabled for this LIF. Dynamic updates will be sent for this LIF if updates are enabled at Vserver level.
    version_added: 2.9.0
    type: bool

  service_policy:
    description:
    - Starting with ONTAP 9.5, you can configure LIF service policies to identify a single service or a list of services that will use a LIF.
    - In ONTAP 9.5, you can assign service policies only for LIFs in the admin SVM.
    - In ONTAP 9.6, you can additionally assign service policies for LIFs in the data SVMs.
    - When you specify a service policy for a LIF, you need not specify the data protocol and role for the LIF.
    - NOTE that role is still required because of a ZAPI issue.  This limitation is removed in ONTAP 9.8.
    - Creating LIFs by specifying the role and data protocols is also supported.
    version_added: '20.4.0'
    type: str

  from_name:
    description: name of the interface to be renamed
    type: str
    version_added: 21.11.0
'''

EXAMPLES = '''
    - name: Create interface
      netapp.ontap.na_ontap_interface:
        state: present
        interface_name: data2
        home_port: e0d
        home_node: laurentn-vsim1
        role: data
        protocols:
          - nfs
          - cifs
        admin_status: up
        failover_policy: local-only
        firewall_policy: mgmt
        is_auto_revert: true
        address: 10.10.10.10
        netmask: 255.255.255.0
        force_subnet_association: false
        dns_domain_name: test.com
        listen_for_dns_query: true
        is_dns_update_enabled: true
        vserver: svm1
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Create cluster interface
      netapp.ontap.na_ontap_interface:
        state: present
        interface_name: cluster_lif
        home_port: e0a
        home_node: cluster1-01
        role: cluster
        admin_status: up
        is_auto_revert: true
        is_ipv4_link_local: true
        vserver: Cluster
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Rename interface
      netapp.ontap.na_ontap_interface:
        state: present
        from_name: ansibleSVM_lif
        interface_name: ansibleSVM_lif01
        vserver: ansibleSVM
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Migrate an interface
      na_ontap_interface:
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        vserver: ansible
        https: true
        validate_certs: false
        state: present
        interface_name: carchi_interface3
        home_port: e0d
        home_node: ansdev-stor-1
        current_node: ansdev-stor-2
        role: data
        failover_policy: local-only
        firewall_policy: mgmt
        is_auto_revert: true
        address: 10.10.10.12
        netmask: 255.255.255.0
        force_subnet_association: false
        admin_status: up

    - name: Delete interface
      na_ontap_interface:
        state: absent
        interface_name: data2
        vserver: svm1
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

'''

RETURN = """

"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapInterface():
    ''' object to describe  interface info '''

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=[
                'present', 'absent'], default='present'),
            interface_name=dict(required=True, type='str'),
            home_node=dict(required=False, type='str', default=None),
            current_node=dict(required=False, type='str'),
            home_port=dict(required=False, type='str'),
            current_port=dict(required=False, type='str'),
            role=dict(required=False, type='str'),
            is_ipv4_link_local=dict(required=False, type='bool', default=None),
            address=dict(required=False, type='str'),
            netmask=dict(required=False, type='str'),
            vserver=dict(required=True, type='str'),
            firewall_policy=dict(required=False, type='str', default=None),
            failover_policy=dict(required=False, type='str', default=None,
                                 choices=['disabled', 'system-defined',
                                          'local-only', 'sfo-partner-only', 'broadcast-domain-wide']),
            failover_group=dict(required=False, type='str'),
            admin_status=dict(required=False, choices=['up', 'down']),
            subnet_name=dict(required=False, type='str'),
            is_auto_revert=dict(required=False, type='bool', default=None),
            protocols=dict(required=False, type='list', elements='str'),
            force_subnet_association=dict(required=False, type='bool', default=None),
            dns_domain_name=dict(required=False, type='str'),
            listen_for_dns_query=dict(required=False, type='bool'),
            is_dns_update_enabled=dict(required=False, type='bool'),
            service_policy=dict(required=False, type='str', default=None),
            from_name=dict(required=False, type='str')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            mutually_exclusive=[
                ['subnet_name', 'address'],
                ['subnet_name', 'netmask'],
                ['is_ipv4_link_local', 'address'],
                ['is_ipv4_link_local', 'netmask'],
                ['is_ipv4_link_local', 'subnet_name']
            ],
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        if HAS_NETAPP_LIB is False:
            self.module.fail_json(
                msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def get_interface(self, name=None):
        """
        Return details about the interface
        :param:
            name : Name of the interface

        :return: Details about the interface. None if not found.
        :rtype: dict
        """
        if name is None:
            name = self.parameters['interface_name']
        interface_info = netapp_utils.zapi.NaElement('net-interface-get-iter')
        interface_attributes = netapp_utils.zapi.NaElement('net-interface-info')
        interface_attributes.add_new_child('interface-name', name)
        interface_attributes.add_new_child('vserver', self.parameters['vserver'])
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(interface_attributes)
        interface_info.add_child_elem(query)
        try:
            result = self.server.invoke_successfully(interface_info, True)
        except netapp_utils.zapi.NaApiError as exc:
            self.module.fail_json(msg='Error fetching interface details for %s: %s' %
                                  (name, to_native(exc)),
                                  exception=traceback.format_exc())
        return_value = None
        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) >= 1:

            interface_attributes = result.get_child_by_name('attributes-list'). \
                get_child_by_name('net-interface-info')
            return_value = {
                'interface_name': name,
                'admin_status': interface_attributes['administrative-status'],
                'home_port': interface_attributes['home-port'],
                'home_node': interface_attributes['home-node'],
                'failover_policy': interface_attributes['failover-policy'].replace('_', '-'),
            }
            if interface_attributes.get_child_by_name('is-auto-revert'):
                return_value['is_auto_revert'] = (interface_attributes['is-auto-revert'] == 'true')
            if interface_attributes.get_child_by_name('failover-group'):
                return_value['failover_group'] = interface_attributes['failover-group']
            if interface_attributes.get_child_by_name('address'):
                return_value['address'] = interface_attributes['address']
            if interface_attributes.get_child_by_name('netmask'):
                return_value['netmask'] = interface_attributes['netmask']
            if interface_attributes.get_child_by_name('firewall-policy'):
                return_value['firewall_policy'] = interface_attributes['firewall-policy']
            if interface_attributes.get_child_by_name('dns-domain-name') != 'none':
                return_value['dns_domain_name'] = interface_attributes['dns-domain-name']
            else:
                return_value['dns_domain_name'] = None
            if interface_attributes.get_child_by_name('listen-for-dns-query'):
                return_value['listen_for_dns_query'] = self.na_helper.get_value_for_bool(True, interface_attributes[
                    'listen-for-dns-query'])
            if interface_attributes.get_child_by_name('is-dns-update-enabled'):
                return_value['is_dns_update_enabled'] = self.na_helper.get_value_for_bool(True, interface_attributes[
                    'is-dns-update-enabled'])
            if interface_attributes.get_child_by_name('service-policy'):
                return_value['service_policy'] = interface_attributes['service-policy']
            if interface_attributes.get_child_by_name('current-node'):
                return_value['current_node'] = interface_attributes['current-node']
            if interface_attributes.get_child_by_name('current-port'):
                return_value['current_port'] = interface_attributes['current-port']
        return return_value

    @staticmethod
    def set_options(options, parameters):
        """ set attributes for create or modify """
        if parameters.get('role') is not None:
            options['role'] = parameters['role']
        if parameters.get('home_node') is not None:
            options['home-node'] = parameters['home_node']
        if parameters.get('home_port') is not None:
            options['home-port'] = parameters['home_port']
        if parameters.get('subnet_name') is not None:
            options['subnet-name'] = parameters['subnet_name']
        if parameters.get('address') is not None:
            options['address'] = parameters['address']
        if parameters.get('netmask') is not None:
            options['netmask'] = parameters['netmask']
        if parameters.get('failover_policy') is not None:
            options['failover-policy'] = parameters['failover_policy']
        if parameters.get('failover_group') is not None:
            options['failover-group'] = parameters['failover_group']
        if parameters.get('firewall_policy') is not None:
            options['firewall-policy'] = parameters['firewall_policy']
        if parameters.get('is_auto_revert') is not None:
            options['is-auto-revert'] = 'true' if parameters['is_auto_revert'] is True else 'false'
        if parameters.get('admin_status') is not None:
            options['administrative-status'] = parameters['admin_status']
        if parameters.get('force_subnet_association') is not None:
            options['force-subnet-association'] = 'true' if parameters['force_subnet_association'] else 'false'
        if parameters.get('dns_domain_name') is not None:
            options['dns-domain-name'] = parameters['dns_domain_name']
        if parameters.get('listen_for_dns_query') is not None:
            options['listen-for-dns-query'] = str(parameters['listen_for_dns_query'])
        if parameters.get('is_dns_update_enabled') is not None:
            options['is-dns-update-enabled'] = str(parameters['is_dns_update_enabled'])
        if parameters.get('is_ipv4_link_local') is not None:
            options['is-ipv4-link-local'] = 'true' if parameters['is_ipv4_link_local'] else 'false'
        if parameters.get('service_policy') is not None:
            options['service-policy'] = parameters['service_policy']

    def set_protocol_option(self, required_keys):
        """ set protocols for create """
        if self.parameters.get('protocols') is None:
            return None
        data_protocols_obj = netapp_utils.zapi.NaElement('data-protocols')
        for protocol in self.parameters.get('protocols'):
            if protocol.lower() in ['fc-nvme', 'fcp']:
                if 'address' in required_keys:
                    required_keys.remove('address')
                if 'home_port' in required_keys:
                    required_keys.remove('home_port')
                if 'netmask' in required_keys:
                    required_keys.remove('netmask')
                not_required_params = set(['address', 'netmask', 'firewall_policy'])
                if not not_required_params.isdisjoint(set(self.parameters.keys())):
                    self.module.fail_json(msg='Error: Following parameters for creating interface are not supported'
                                              ' for data-protocol fc-nvme: %s' % ', '.join(not_required_params))
            data_protocols_obj.add_new_child('data-protocol', protocol)
        return data_protocols_obj

    def get_home_node_for_cluster(self):
        ''' get the first node name from this cluster '''
        get_node = netapp_utils.zapi.NaElement('cluster-node-get-iter')
        attributes = {
            'query': {
                'cluster-node-info': {}
            }
        }
        get_node.translate_struct(attributes)
        try:
            result = self.server.invoke_successfully(get_node, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            if str(exc.code) == '13003' or exc.message == 'ZAPI is not enabled in pre-cluster mode.':
                return None
            self.module.fail_json(msg='Error fetching node for interface %s: %s' %
                                  (self.parameters['interface_name'], to_native(exc)),
                                  exception=traceback.format_exc())
        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) >= 1:
            attributes = result.get_child_by_name('attributes-list')
            return attributes.get_child_by_name('cluster-node-info').get_child_content('node-name')
        return None

    def validate_create_parameters(self, keys):
        '''
            Validate if required parameters for create are present.
            Parameter requirement might vary based on given data-protocol.
            :return: None
        '''
        if self.parameters.get('home_node') is None:
            node = self.get_home_node_for_cluster()
            if node is not None:
                self.parameters['home_node'] = node
        # validate if mandatory parameters are present for create
        if not keys.issubset(set(self.parameters.keys())) and self.parameters.get('subnet_name') is None:
            self.module.fail_json(msg='Error: Missing one or more required parameters for creating interface: %s'
                                  % ', '.join(keys))
        # if role is intercluster, protocol cannot be specified
        if self.parameters.get('role') == "intercluster" and self.parameters.get('protocols') is not None:
            self.module.fail_json(msg='Error: Protocol cannot be specified for intercluster role,'
                                      'failed to create interface')

    def create_interface(self):
        ''' calling zapi to create interface '''
        required_keys = set(['role', 'home_port'])
        data_protocols_obj = None
        if (
            self.parameters.get('subnet_name') is None
            and self.parameters.get('is_ipv4_link_local') is not None
            and not self.parameters.get('is_ipv4_link_local')
        ):
            required_keys.add('address')
            required_keys.add('netmask')
        if self.parameters.get('service_policy') is not None:
            required_keys.remove('role')
        data_protocols_obj = self.set_protocol_option(required_keys)
        self.validate_create_parameters(required_keys)

        options = {'interface-name': self.parameters['interface_name'],
                   'vserver': self.parameters['vserver']}
        NetAppOntapInterface.set_options(options, self.parameters)
        interface_create = netapp_utils.zapi.NaElement.create_node_with_children('net-interface-create', **options)
        if data_protocols_obj is not None:
            interface_create.add_child_elem(data_protocols_obj)
        try:
            self.server.invoke_successfully(interface_create, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            # msg: "Error Creating interface ansible_interface: NetApp API failed. Reason - 17:A LIF with the same name already exists"
            if to_native(exc.code) == "17":
                self.na_helper.changed = False
            else:
                self.module.fail_json(msg='Error Creating interface %s: %s' %
                                      (self.parameters['interface_name'], to_native(exc)),
                                      exception=traceback.format_exc())

    def delete_interface(self, current_status):
        ''' calling zapi to delete interface '''
        if current_status == 'up':
            self.parameters['admin_status'] = 'down'
            self.modify_interface({'admin_status': 'down'})

        interface_delete = netapp_utils.zapi.NaElement.create_node_with_children(
            'net-interface-delete', **{'interface-name': self.parameters['interface_name'],
                                       'vserver': self.parameters['vserver']})
        try:
            self.server.invoke_successfully(interface_delete, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            self.module.fail_json(msg='Error deleting interface %s: %s' %
                                  (self.parameters['interface_name'], to_native(exc)),
                                  exception=traceback.format_exc())

    def modify_interface(self, modify):
        """
        Modify the interface.
        """
        # Current_node and current_port don't exist in modify only migrate, so we need to remove them from the list
        migrate = {}
        if modify.get('current_node') is not None:
            migrate['current_node'] = modify.pop('current_node')
        if modify.get('current_port') is not None:
            migrate['current_port'] = modify.pop('current_port')
        if modify:
            options = {'interface-name': self.parameters['interface_name'],
                       'vserver': self.parameters['vserver']
                       }
            NetAppOntapInterface.set_options(options, modify)
            interface_modify = netapp_utils.zapi.NaElement.create_node_with_children('net-interface-modify', **options)
            try:
                self.server.invoke_successfully(interface_modify, enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as err:
                self.module.fail_json(msg='Error modifying interface %s: %s' %
                                      (self.parameters['interface_name'], to_native(err)),
                                      exception=traceback.format_exc())
        # if home node has been changed we need to migrate the interface
        if migrate:
            self.migrate_interface()

    def migrate_interface(self):
        interface_migrate = netapp_utils.zapi.NaElement('net-interface-migrate')
        if self.parameters.get('current_node') is None:
            self.module.fail_json(msg='current_node must be set to migrate')
        interface_migrate.add_new_child('destination-node', self.parameters['current_node'])
        if self.parameters.get('current_port') is not None:
            interface_migrate.add_new_child('destination-port', self.parameters['current_port'])
        interface_migrate.add_new_child('lif', self.parameters['interface_name'])
        interface_migrate.add_new_child('vserver', self.parameters['vserver'])
        try:
            self.server.invoke_successfully(interface_migrate, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error migrating %s: %s'
                                  % (self.parameters['current_node'], to_native(error)),
                                  exception=traceback.format_exc())

    def rename_interface(self):
        options = {
            'interface-name': self.parameters['from_name'],
            'new-name': self.parameters['interface_name'],
            'vserver': self.parameters['vserver']
        }
        interface_rename = netapp_utils.zapi.NaElement.create_node_with_children('net-interface-rename', **options)
        try:
            self.server.invoke_successfully(interface_rename, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error renaming %s to %s: %s'
                                  % (self.parameters['from_name'], self.parameters['interface_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def autosupport_log(self):
        try:
            # Checking to see if autosupport_log() can be ran as this is a post cluster setup request.
            results = netapp_utils.get_cserver(self.server)
            cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
            netapp_utils.ems_log_event("na_ontap_interface", cserver)
        except netapp_utils.zapi.NaApiError as error:
            # Error 13003 denotes cluster does not exist. It happens when running operations on a node not in cluster.
            if to_native(error.code) != '13003':
                self.module.fail_json(
                    msg='Error calling autosupport_log(): %s' % to_native(error),
                    exception=traceback.format_exc())

    def apply(self):
        ''' calling all interface features '''
        self.autosupport_log()
        rename = None
        current = self.get_interface()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action == 'create' and self.parameters.get('from_name'):
            # create by renaming existing interface
            old_interface = self.get_interface(self.parameters['from_name'])
            rename = self.na_helper.is_rename_action(old_interface, current)
            if rename is None:
                self.module.fail_json(msg='Error renaming interface %s: no interface with from_name %s.'
                                      % (self.parameters['interface_name'], self.parameters['from_name']))
            if rename:
                current = old_interface
                cd_action = None
        modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed and not self.module.check_mode:
            if rename:
                self.rename_interface()
                modify.pop('interface_name')
            if cd_action == 'create':
                self.create_interface()
            elif cd_action == 'delete':
                self.delete_interface(current['admin_status'])
            elif modify:
                self.modify_interface(modify)
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    interface = NetAppOntapInterface()
    interface.apply()


if __name__ == '__main__':
    main()
