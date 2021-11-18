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
    - This option is deprecated in REST.
    - With REST, the module tries to derive a service_policy and may error out.
    type: str

  address:
    description:
    - Specifies the LIF's IP address.
    - ZAPI - Required when C(state=present) and is_ipv4_link_local if false and subnet_name is not set.
    - REST - Required when C(state=present) and C(interface_type) is IP.
    type: str

  netmask:
    description:
    - Specifies the LIF's netmask.
    - ZAPI - Required when C(state=present) and is_ipv4_link_local if false and subnet_name is not set.
    - REST - Required when C(state=present) and C(interface_type) is IP.
    type: str

  is_ipv4_link_local:
    description:
    - Specifies the LIF's are to acquire a ipv4 link local address.
    - Use case for this is when creating Cluster LIFs to allow for auto assignment of ipv4 link local address.
    - Not supported in REST
    version_added: '20.1.0'
    type: bool

  vserver:
    description:
    - The name of the vserver to use.
    - Required with ZAPI.
    - Required with REST for SVM-scoped interfaces.
    - Invalid with REST for cluster-scoped interfaces.
    required: false
    type: str

  firewall_policy:
    description:
    - Specifies the firewall policy for the LIF.
    - This option is deprecated in REST.
    - With REST, the module tries to derive a service_policy and may error out.
    type: str

  failover_policy:
    description:
      - Specifies the failover policy for the LIF.
      - When using REST, this values are mapped to 'home_port_only', 'default', 'home_node_only', 'sfo_partners_only', 'broadcast_domain_only'.
    choices: ['disabled', 'system-defined', 'local-only', 'sfo-partner-only', 'broadcast-domain-wide']
    type: str

  failover_scope:
    description:
      - Specifies the failover scope for the LIF.
      - REST only, and only for IP interfaces.  Not supported for FC interfaces.
    choices: ['home_port_only', 'default', 'home_node_only', 'sfo_partners_only', 'broadcast_domain_only']
    type: str
    version_added: '21.13.0'

  failover_group:
    description:
      - Specifies the failover group for the LIF.
      - Not supported with REST.
    version_added: '20.1.0'
    type: str

  subnet_name:
    description:
    - Subnet where the interface address is allocated from.
    - If the option is not used, the IP address will need to be provided by the administrator during configuration.
    - Not supported in REST.
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
    - not supported with REST.
    version_added: 2.9.0
    type: bool

  protocols:
    description:
    - Specifies the list of data protocols configured on the LIF. By default, the values in this element are nfs, cifs and fcache.
    - Other supported protocols are iscsi and fcp. A LIF can be configured to not support any data protocols by specifying 'none'.
    - Protocol values of none, iscsi, fc-nvme or fcp can't be combined with any other data protocol(s).
    - address, netmask and firewall_policy parameters are not supported for 'fc-nvme' option.
    - This option is ignored with REST, though it can be used to derive C(interface_type) or C(data_protocol).
    type: list
    elements: str

  data_protocol:
    description:
    - The data protocol for which the FC interface is configured.
    - Ignored with ZAPI or for IP interfaces.
    - Required for create on for a FC type interface.
    type: str
    choices: ['fcp', 'fc_nvme']

  dns_domain_name:
    description:
    - Specifies the unique, fully qualified domain name of the DNS zone of this LIF.
    - not supported with REST.
    version_added: 2.9.0
    type: str

  listen_for_dns_query:
    description:
    - If True, this IP address will listen for DNS queries for the dnszone specified.
    - Not supported with REST.
    version_added: 2.9.0
    type: bool

  is_dns_update_enabled:
    description:
    - Specifies if DNS update is enabled for this LIF. Dynamic updates will be sent for this LIF if updates are enabled at Vserver level.
    - Not supported with REST.
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

  interface_type:
    description:
      - type of the interface.
      - IP is assumed if address or netmask are present.
      - IP interfaces includes cluster, intercluster, management, and NFS, CIFS, iSCSI interfaces.
      - FC interfaces includes FCP and NVME-FC interfaces.
      - ignored with ZAPI.
    type: str
    choices: ['fc', 'ip']
    version_added: 21.13.0

  ipspace:
    description:
      - IPspace name is required with REST for cluster-scoped interfaces.  It is optional with SVM scope.
      - ignored with ZAPI.
    type: str
    version_added: 21.13.0

  ignore_zapi_options:
    description:
      - ignore unsupported options that should not be relevant.
      - ignored with ZAPI.
    choices: ['dns_domain_name', 'failover_group', 'force_subnet_association', 'is_dns_update_enabled', 'listen_for_dns_query']
    type: list
    elements: str
    default: ['force_subnet_association']
    version_added: 21.13.0
notes:
  - REST support is experimental and requires ONTAP 9.7 or later.
  - ZAPI is selected if C(use_rest) is set to I(never) or I(auto).  We will restore I(auto) to its expected behavior in a few months.
  - REST is only selected if C(use_rest) is set to I(always).
'''

EXAMPLES = '''
    - name: Create interface - ZAPI
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

    - name: Create data interface - REST - NAS
      netapp.ontap.na_ontap_interface:
        state: present
        interface_name: data2
        home_port: e0d
        home_node: laurentn-vsim1
        admin_status: up
        failover_scope: home_node_only
        service_policy: default-data-files
        is_auto_revert: true
        interface_type: ip
        address: 10.10.10.10
        netmask: 255.255.255.0
        vserver: svm1
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Create cluster interface - ZAPI
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

    - name: Create cluster interface - REST
      netapp.ontap.na_ontap_interface:
        state: present
        interface_name: cluster_lif
        home_port: e0a
        home_node: cluster1-01
        service_policy: default-cluster
        admin_status: up
        is_auto_revert: true
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

try:
    import ipaddress
    HAS_IPADDRESS_LIB = True
    IMPORT_ERROR = None
except ImportError as exc:
    HAS_IPADDRESS_LIB = False
    IMPORT_ERROR = str(exc)

import time
import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic

FAILOVER_POLICIES = ['disabled', 'system-defined', 'local-only', 'sfo-partner-only', 'broadcast-domain-wide']
FAILOVER_SCOPES = ['home_port_only', 'default', 'home_node_only', 'sfo_partners_only', 'broadcast_domain_only']
REST_UNSUPPORTED_OPTIONS = ['is_ipv4_link_local', 'subnet_name', ]
REST_IGNORABLE_OPTIONS = ['dns_domain_name', 'failover_group', 'force_subnet_association', 'is_dns_update_enabled', 'listen_for_dns_query']


def get_network(ip, mask):
    # python 2.7 requires the address to be in unicode format (which is the default for 3.x)
    net = u'%s/%s' % (ip, mask)
    return ipaddress.ip_network(net, strict=False)


def netmask_length_to_netmask(ip, length):
    return str(get_network(ip, length).netmask)


def netmask_to_netmask_length(ip, netmask):
    return str(get_network(ip, netmask).prefixlen)


class NetAppOntapInterface():
    ''' object to describe  interface info '''

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=[
                'present', 'absent'], default='present'),
            interface_name=dict(required=True, type='str'),
            interface_type=dict(type='str', choices=['fc', 'ip']),
            ipspace=dict(type='str'),
            home_node=dict(required=False, type='str', default=None),
            current_node=dict(required=False, type='str'),
            home_port=dict(required=False, type='str'),
            current_port=dict(required=False, type='str'),
            role=dict(required=False, type='str'),
            is_ipv4_link_local=dict(required=False, type='bool', default=None),
            address=dict(required=False, type='str'),
            netmask=dict(required=False, type='str'),
            vserver=dict(required=False, type='str'),
            firewall_policy=dict(required=False, type='str', default=None),
            failover_policy=dict(required=False, type='str', default=None,
                                 choices=['disabled', 'system-defined',
                                          'local-only', 'sfo-partner-only', 'broadcast-domain-wide']),
            failover_scope=dict(required=False, type='str', default=None,
                                choices=['home_port_only', 'default',
                                         'home_node_only', 'sfo_partners_only', 'broadcast_domain_only']),
            failover_group=dict(required=False, type='str'),
            admin_status=dict(required=False, choices=['up', 'down']),
            subnet_name=dict(required=False, type='str'),
            is_auto_revert=dict(required=False, type='bool', default=None),
            protocols=dict(required=False, type='list', elements='str'),
            data_protocol=dict(required=False, type='str', choices=['fc_nvme', 'fcp']),
            force_subnet_association=dict(required=False, type='bool', default=None),
            dns_domain_name=dict(required=False, type='str'),
            listen_for_dns_query=dict(required=False, type='bool'),
            is_dns_update_enabled=dict(required=False, type='bool'),
            service_policy=dict(required=False, type='str', default=None),
            from_name=dict(required=False, type='str'),
            ignore_zapi_options=dict(required=False, type='list', elements='str', default=['force_subnet_association'], choices=REST_IGNORABLE_OPTIONS)
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            mutually_exclusive=[
                ['subnet_name', 'address'],
                ['subnet_name', 'netmask'],
                ['is_ipv4_link_local', 'address'],
                ['is_ipv4_link_local', 'netmask'],
                ['is_ipv4_link_local', 'subnet_name'],
                ['failover_policy', 'failover_scope'],
            ],
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.rest_api = OntapRestAPI(self.module)
        unsupported_rest_properties = [key for key in REST_IGNORABLE_OPTIONS if key not in self.parameters['ignore_zapi_options']]
        unsupported_rest_properties.extend(REST_UNSUPPORTED_OPTIONS)
        used_unsupported_rest_properties = [x for x in unsupported_rest_properties if x in self.parameters]
        self.use_rest, error = self.rest_api.is_rest(used_unsupported_rest_properties)
        if error is not None:
            self.module.fail_json(msg=error)
        if self.use_rest and not self.rest_api.meets_rest_minimum_version(self.use_rest, 9, 7, 0):
            msg = 'REST requires ONTAP 9.7 or later for interface APIs.'
            if self.parameters['use_rest'].lower() == 'always':
                self.module.fail_json(msg='Error: %s' % msg)
            self.module.warn('Falling back to ZAPI: %s' % msg)
            self.use_rest = False
        # TODO: revert this after a few months
        if self.use_rest and self.parameters['use_rest'].lower() == 'auto':
            self.module.warn(
                'Falling back to ZAPI as REST support for na_ontap_interface is in beta and use_rest: auto.  Set use_rest: always to force REST.')
            self.use_rest = False
        if self.use_rest:
            if HAS_IPADDRESS_LIB is False:
                self.module.fail_json(msg="the python ipaddress package is required for this module: %s" % IMPORT_ERROR)
            self.cluster_nodes = None       # cached value to limit number of API calls.
            self.map_failover_policy()
            self.validate_input_parameters()
        elif netapp_utils.has_netapp_lib() is False:
            self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
        else:
            if 'vserver' not in self.parameters:
                self.module.fail_json(msg='missing required argument with ZAPI: vserver')
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def map_failover_policy(self):
        if self.use_rest and 'failover_policy' in self.parameters:
            mapping = dict(zip(FAILOVER_POLICIES, FAILOVER_SCOPES))
            self.parameters['failover_scope'] = mapping[self.parameters['failover_policy']]

    def set_interface_type(self, interface_type):
        if 'interface_type' in self.parameters:
            if self.parameters['interface_type'] != interface_type:
                self.module.fail_json(msg="Error: mismatch between configured interface_type: %s and derived interface_type: %s."
                                      % (self.parameters['interface_type'], interface_type))
        else:
            self.parameters['interface_type'] = interface_type

    def derive_fc_data_protocol(self):
        protocols = self.parameters.get('protocols')
        if not protocols:
            return
        if len(protocols) > 1:
            self.module.fail_json(msg="A single protocol entry is expected for FC interface, got %s." % protocols)
        mapping = {'fc-nvme': 'fc_nvme', 'fc_nvme': 'fc_nvme', 'fcp': 'fcp'}
        if protocols[0] not in mapping:
            self.module.fail_json(msg="Unexpected protocol value %s." % protocols[0])
        data_protocol = mapping[protocols[0]]
        if 'data_protocol' in self.parameters and self.parameters['data_protocol'] != data_protocol:
            self.module.fail_json(msg="Error: mismatch between configured data_protocol: %s and data_protocols: %s"
                                  % (self.parameters['data_protocol'], protocols))
        self.parameters['data_protocol'] = data_protocol

    def derive_interface_type(self):
        protocols = self.parameters.get('protocols')
        if protocols is None:
            if self.parameters.get('role') in ('cluster', 'intercluster'):
                self.set_interface_type('ip')
            if 'address' in self.parameters or 'netmask' in self.parameters:
                self.set_interface_type('ip')
            return False, False
        protocol_types = set()
        unknown_protocols = []
        for protocol in protocols:
            if protocol.lower() in ['fc-nvme', 'fcp']:
                protocol_types.add('fc')
            elif protocol.lower() in ['nfs', 'cifs', 'iscsi']:
                protocol_types.add('ip')
            else:
                unknown_protocols.append(protocol)
        errors = []
        if unknown_protocols or not protocol_types:
            errors.append('Unexpected value(s) for protocols: %s' % unknown_protocols)
        if len(protocol_types) > 1:
            errors.append('Incompatible value(s) for protocols: %s' % protocols)
        if errors:
            self.module.fail_json(msg='Error: ' + (' - '.join(errors)))
        self.set_interface_type(protocol_types.pop())
        return None

    def derive_block_file_type(self, protocols):
        block_p, file_p = False, False
        if protocols is None:
            return block_p, file_p
        block_values, file_values = [], []
        for protocol in protocols:
            if protocol.lower() in ['fc-nvme', 'fcp', 'iscsi']:
                block_p = True
                block_values.append(protocol)
            elif protocol.lower() in ['nfs', 'cifs']:
                file_p = True
                file_values.append(protocol)
        if block_p and file_p:
            self.module.fail_json(msg="Cannot use any of %s with %s" % (block_values, file_values))
        return block_p, file_p

    def get_interface_record_rest(self, if_type, query, fields):
        if 'ipspace' in self.parameters:
            query['ipspace.name'] = self.parameters['ipspace']
        if 'vserver' in self.parameters:
            query['svm.name'] = self.parameters['vserver']
        return rest_generic.get_one_record(self.rest_api, self.get_net_int_api(if_type), query, fields)

    def get_interface_records_rest(self, if_type, query, fields):
        if 'ipspace' in self.parameters:
            query['ipspace.name'] = self.parameters['ipspace']
        if 'vserver' in self.parameters:
            query['svm.name'] = self.parameters['vserver']
        records, error = rest_generic.get_0_or_more_records(self.rest_api, self.get_net_int_api(if_type), query, fields)
        if error and 'are available in precluster.' in error:
            # in precluster mode, network APIs are not available!
            self.module.fail_json(msg="This module cannot use REST in precluster mode, ZAPI can be forced with use_rest: never.  Error: %s"
                                  % error)
        return records, error

    def get_net_int_api(self, if_type=None):
        if if_type is None:
            if_type = self.parameters.get('interface_type')
        if if_type is None:
            self.module.fail_json('Error: missing option "interface_type (or could not be derived)')
        return 'network/%s/interfaces' % if_type

    def find_interface_record(self, records, home_node, name):
        full_name = "%s_%s" % (home_node, name) if home_node is not None else name
        full_name_records = [record for record in records if record['name'] == full_name]
        if len(full_name_records) > 1:
            self.module.fail_json(msg='Error: multiple records for: %s - %s' % (full_name, full_name_records))
        return None if not full_name_records else full_name_records[0]

    def find_exact_match(self, records, name):
        """ with vserver, we expect an exact match
            but ONTAP transform cluster interface names by prepending the home_port
        """
        if 'vserver' in self.parameters:
            if len(records) > 1:
                self.module.fail_json(msg='Error: unexpected records for name: %s, vserser: %s - %s'
                                      % (name, self.parameters['vserver'], records))
            return records[0] if records else None
        # since our queries included a '*', we expect multiple records
        # an exact match is <home_node>_<name> or <name>.
        # is there an exact macth on name only?
        record = self.find_interface_record(records, None, name)
        # now matching with home_port as a prefix
        if 'home_node' in self.parameters and self.parameters['home_node'] != 'localhost':
            home_record = self.find_interface_record(records, self.parameters['home_node'], name)
            if record and home_record:
                self.module.warn('Found both %s, selecting %s' % ([record['name'] for record in (record, home_record)], home_record['name']))
        else:
            # look for all known nodes
            home_node_records = []
            for home_node in self.get_cluster_node_names_rest():
                home_record = self.find_interface_record(records, home_node, name)
                if home_record:
                    home_node_records.append(home_record)
            if len(home_node_records) > 1:
                self.module.fail_json(msg='Error: multiple matches for name: %s: %s.  Set home_node parameter.'
                                      % (name, [record['name'] for record in home_node_records]))
            home_record = None if not home_node_records else home_node_records[0]
            if record and home_node_records:
                self.module.fail_json(msg='Error: multiple matches for name: %s: %s.  Set home_node parameter.'
                                      % (name, [record['name'] for record in (record, home_record)]))
        if home_record:
            record = home_record
        if record and self.parameters.get('interface_name') != record['name']:
            # fix name, otherwise we'll attempt a rename :(
            self.parameters['interface_name'] = record['name']
            self.module.warn('adjusting name from %s to %s' % (name, record['name']))
        return record

    def get_interface_rest(self, name):
        """
        Return details about the interface
        :param:
            name : Name of the interface

        :return: Details about the interface. None if not found.
        :rtype: dict
        """
        self.derive_interface_type()
        if_type = self.parameters.get('interface_type')
        # ONTAP renames cluster interfaces, use a * to find them
        qname = '*%s' % name if 'vserver' not in self.parameters else name
        query = {'name': qname}
        fields = 'name,location,uuid,enabled,svm.name'
        fields_fc = fields + ',data_protocol'
        fields_ip = fields + ',ip,service_policy'
        records, error, records2, error2 = None, None, None, None
        if if_type is None or if_type == 'ip':
            records, error = self.get_interface_records_rest('ip', query, fields_ip)
        if if_type is None or if_type == 'fc':
            records2, error2 = self.get_interface_records_rest('fc', query, fields_fc)
        if records and records2:
            msg = 'Error fetching interface %s - found duplicate entries, please indicate interface_type.'
            if error:
                msg += ' - error ip: %s' % error
            if error2:
                msg += ' - error fc: %s' % error2
            self.module.fail_json(msg=msg)
        if error is None and error2 is not None and records:
            # ignore error on fc if ip interface is found
            error2 = None
        if error2 is None and error is not None and records2:
            # ignore error on ip if fc interface is found
            error = None
        if error or error2:
            errors = [to_native(err) for err in (error, error2) if err]
            self.module.fail_json(msg='Error fetching interface details for %s: %s' % (name, ' - '.join(errors)),
                                  exception=traceback.format_exc())
        if records:
            self.set_interface_type('ip')
        if records2:
            self.set_interface_type('fc')
            records = records2

        record = self.find_exact_match(records, name) if records else None
        return self.dict_from_record(record) if record else None

    def dict_from_record(self, record):
        if not record:
            return None
        return_value = {
            'interface_name': record['name'],
            'interface_type': self.parameters['interface_type'],
            'uuid': record['uuid'],
            'admin_status': 'up' if record['enabled'] else 'down',
            'home_port': record['location']['home_port']['name'],
            'home_node': record['location']['home_node']['name'],
        }
        if self.na_helper.safe_get(record, ['svm', 'name']):
            return_value['vserver'] = record['svm']['name']
        if 'data_protocol' in record:
            return_value['data_protocol'] = record['data_protocol']
        if 'auto_revert' in record['location']:
            return_value['is_auto_revert'] = record['location']['auto_revert']
        if 'failover' in record['location']:
            return_value['failover_scope'] = record['location']['failover']
        # if interface_attributes.get_child_by_name('failover-group'):
        #     return_value['failover_group'] = interface_attributes['failover-group']
        if self.na_helper.safe_get(record, ['ip', 'address']):
            return_value['address'] = record['ip']['address']
            if self.na_helper.safe_get(record, ['ip', 'netmask']):
                return_value['netmask'] = netmask_length_to_netmask(record['ip']['address'], record['ip']['netmask'])
        if self.na_helper.safe_get(record, ['service_policy', 'name']):
            return_value['service_policy'] = record['service_policy']['name']
        if self.na_helper.safe_get(record, ['location', 'node', 'name']):
            return_value['current_node'] = record['location']['node']['name']
        if self.na_helper.safe_get(record, ['location', 'port', 'name']):
            return_value['current_port'] = record['location']['port']['name']
        return return_value

    def get_node_port(self, uuid):
        record, error = self.get_interface_record_rest(self.parameters['interface_type'], {'uuid': uuid}, 'location')
        if error or not record:
            return None, None, error
        node = self.na_helper.safe_get(record, ['location', 'node', 'name'])
        port = self.na_helper.safe_get(record, ['location', 'port', 'name'])
        return node, port, None

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
        if self.use_rest:
            return self.get_interface_rest(name)

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

    def fix_errors(self, options, parameters, errors):
        block_p, file_p = self.derive_block_file_type(self.parameters.get('protocols'))
        if 'role' in errors:
            fixed = False
            if errors['role'] == 'data' and errors.get('firewall_policy', 'data') == 'data':
                if file_p and parameters.get('service_policy', 'default-data-files') == 'default-data-files':
                    options['service_policy'] = 'default-data-files'
                    fixed = True
                elif block_p and parameters.get('service_policy', 'default-data-blocks') == 'default-data-blocks':
                    options['service_policy'] = 'default-data-blocks'
                    fixed = True
            if errors['role'] == 'data' and errors.get('firewall_policy') == 'mgmt':
                options['service_policy'] = 'default-management'
                fixed = True
            if errors['role'] == 'intercluster' and errors.get('firewall_policy') in [None, 'intercluster']:
                options['service_policy'] = 'default-intercluster'
                fixed = True
            if errors['role'] == 'cluster' and errors.get('firewall_policy') in [None, 'mgmt']:
                options['service_policy'] = 'default-cluster'
                fixed = True
            if fixed:
                errors.pop('role')
                errors.pop('firewall_policy', None)
        return None

    def set_options_rest(self, parameters):
        """ set attributes for create or modify """

        def add_ip(options, key, value):
            if 'ip' not in options:
                options['ip'] = {}
            options['ip'][key] = value

        def add_location(options, key, value, node=None):
            if 'location' not in options:
                options['location'] = {}
            if key in ['home_node', 'home_port', 'node', 'port']:
                options['location'][key] = {'name': value}
            else:
                options['location'][key] = value
            if key in ['home_port', 'port']:
                if node is None:
                    node = self.parameters['home_node']
                options['location'][key]['node'] = {'name': node}

        def get_node_for_port(parameters, pkey):
            if pkey == 'current_port':
                return parameters.get('current_port', parameters.get('home_node'))
            elif pkey == 'home_port':
                return parameters.get('home_node')
            else:
                return None

        options, migrate_options, errors = {}, {}, {}
        if parameters is None:
            parameters = self.parameters

        mapping_params_to_rest = {
            'data_protocol': 'data_protocol',
            'admin_status': 'enabled',
            'ipspace': 'ipspace.name',
            'interface_name': 'name',
            'vserver': 'svm.name',
            'service_policy': 'service_policy',
            # IP
            'address': 'address',
            'netmask': 'netmask',
            # LOCATION
            'home_port': 'home_port',
            'home_node': 'home_node',
            'current_port': 'port',
            'current_node': 'node',
            'failover_scope': 'failover',
            'is_auto_revert': 'auto_revert',
        }
        ip_keys = ('address', 'netmask')
        location_keys = ('home_port', 'home_node', 'current_port', 'current_node', 'failover_scope', 'is_auto_revert')

        for pkey, rkey in mapping_params_to_rest.items():
            if pkey in parameters:
                if pkey == 'admin_status':
                    options[rkey] = parameters[pkey] == 'up'
                elif pkey in ip_keys:
                    add_ip(options, rkey, parameters[pkey])
                elif pkey in location_keys:
                    dest = migrate_options if rkey in ('node', 'port') else options
                    add_location(dest, rkey, parameters[pkey], get_node_for_port(parameters, pkey))
                else:
                    options[rkey] = parameters[pkey]

        keys_in_error = ('role', 'subnet_name', 'failover_group', 'firewall_policy', 'force_subnet_association',
                         'dns_domain_name', 'listen_for_dns_query', 'is_dns_update_enabled', 'is_ipv4_link_local')
        for pkey in keys_in_error:
            if pkey in parameters:
                errors[pkey] = parameters[pkey]

        return options, migrate_options, errors

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

    def get_cluster_node_names_rest(self):
        ''' get cluster node names, but the cluster may not exist yet
            return:
                empty list if the cluster cannot be reached
                a list of nodes
        '''
        if self.cluster_nodes is None:
            records, error = rest_generic.get_0_or_more_records(self.rest_api, 'cluster/nodes', fields='name,uuid,cluster_interfaces')
            if error:
                self.module.fail_json(msg='Error fetching cluster node info: %s' % to_native(error),
                                      exception=traceback.format_exc())
            self.cluster_nodes = records or []
        return [record['name'] for record in self.cluster_nodes]

    def get_home_node_for_cluster(self):
        ''' get the first node name from this cluster '''
        if self.use_rest:
            nodes = self.get_cluster_node_names_rest()
            if nodes:
                return nodes[0]
            return None

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

    def validate_input_parameters(self, action=None):
        if action == 'create' and 'vserver' not in self.parameters and 'ipspace' not in self.parameters:
            self.module.fail_json(msg='ipspace name must be provided if scope is cluster, or vserver for svm scope.')
        ignored_keys = []
        for key in self.parameters.get('ignore_zapi_options', []):
            if key in self.parameters:
                del self.parameters[key]
                ignored_keys.append(key)
        if ignored_keys:
            self.module.warn("Ignoring %s" % ', '.join(ignored_keys))

    def validate_required_parameters(self, keys):
        '''
            Validate if required parameters for create or modify are present.
            Parameter requirement might vary based on given data-protocol.
            :return: None
        '''
        if self.parameters.get('home_node') is None:
            node = self.get_home_node_for_cluster()
            if node is not None:
                self.parameters['home_node'] = node
        # validate if mandatory parameters are present for create or modify
        error = None
        if self.use_rest and self.parameters.get('home_node') is None and self.parameters.get('home_port') is not None:
            error = 'Cannot guess home_node, home_node is required when home_port is present with REST.'
        if not error and not keys.issubset(set(self.parameters.keys())) and self.parameters.get('subnet_name') is None:
            error = 'Missing one or more required parameters for creating interface: %s.' % ', '.join(keys)
        # if role is intercluster, protocol cannot be specified
        if not error and self.parameters.get('role') == "intercluster" and self.parameters.get('protocols') is not None:
            error = 'Protocol cannot be specified for intercluster role, failed to create interface.'
        if not error and 'interface_type' in keys and self.parameters['interface_type'] not in ['fc', 'ip']:
            error = 'unexpected value for interface_type: %s.' % self.parameters['interface_type']
        if error:
            self.module.fail_json(msg='Error: %s' % error)

    def validate_modify_parameters(self, body):
        """ Only the following keys can be modified:
            enabled, ip, location, name, service_policy
        """
        bad_keys = [key for key in body if key not in ['enabled', 'ip', 'location', 'name', 'service_policy']]
        if bad_keys:
            plural = 's' if len(bad_keys) > 1 else ''
            self.module.fail_json(msg='The following option%s cannot be modified: %s' % (plural, ', '.join(bad_keys)))

    def build_rest_body(self, modify=None):
        # if self.parameters.get('vserver') is not None:
        required_keys = set(['interface_type'])     # python 2.6 syntax
        # running validation twice, as interface_type dictates the second set of requirements
        self.validate_required_parameters(required_keys)
        self.validate_input_parameters(action='modify' if modify else 'create')
        if self.parameters['interface_type'] == 'fc' and not modify:
            self.derive_fc_data_protocol()
            required_keys = set(['interface_name', 'home_port', 'data_protocol'])
        elif self.parameters['interface_type'] == 'ip' and not modify:
            required_keys = set(['interface_name', 'home_port', 'address', 'netmask'])
        self.validate_required_parameters(required_keys)
        body, migrate_body, errors = self.set_options_rest(modify)
        self.fix_errors(body, self.parameters, errors)
        if errors:
            self.module.fail_json(msg='Error %s interface, unsupported options: %s'
                                  % ('modifying' if modify else 'creating', str(errors)))
        if modify:
            self.validate_modify_parameters(body)
        return body, migrate_body

    def create_interface_rest(self, body):
        ''' calling REST to create interface '''
        dummy, error = rest_generic.post_async(self.rest_api, self.get_net_int_api(), body)
        if error:
            self.module.fail_json(msg='Error creating interface %s: %s' % (self.parameters['interface_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def create_interface(self, body):
        ''' calling zapi to create interface '''
        if self.use_rest:
            return self.create_interface_rest(body)

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
        self.validate_required_parameters(required_keys)

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

    def delete_interface_rest(self, current_status, uuid):
        ''' calling zapi to delete interface '''

        dummy, error = rest_generic.delete_async(self.rest_api, self.get_net_int_api(), uuid)
        if error:
            self.module.fail_json(msg='Error Deleting interface %s: %s' % (self.parameters['interface_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def delete_interface(self, current_status, uuid):
        ''' calling zapi to delete interface '''
        if self.use_rest:
            return self.delete_interface_rest(current_status, uuid)

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

    def modify_interface_rest(self, uuid, body):
        ''' calling REST to modify interface '''
        if not body:
            return
        dummy, error = rest_generic.patch_async(self.rest_api, self.get_net_int_api(), uuid, body)
        if error:
            self.module.fail_json(msg='Error modifying interface %s: %s' % (self.parameters['interface_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def migrate_interface_rest(self, uuid, body):
        # curiously, we sometimes need to send the request twice (well, always in my experience)
        errors = []
        desired_node = self.na_helper.safe_get(body, ['location', 'node', 'name'])
        desired_port = self.na_helper.safe_get(body, ['location', 'port', 'name'])
        for __ in range(10):
            self.modify_interface_rest(uuid, body)
            time.sleep(5)
            node, port, error = self.get_node_port(uuid)
            if error is None and desired_node in [None, node] and desired_port in [None, port]:
                return
            if errors or error is not None:
                errors.append(str(error))
        if errors:
            self.module.fail_json(msg='Errors waiting for migration to complete: %s' % ' - '.join(errors))
        else:
            self.module.warn('Failed to confirm interface is migrated after 120 seconds')

    def modify_interface(self, modify, uuid=None, body=None):
        """
        Modify the interface.
        """
        if self.use_rest:
            return self.modify_interface_rest(uuid, body)

        # Current_node and current_port don't exist in modify only migrate, so we need to remove them from the list
        migrate = {}
        modify_options = dict(modify)
        if modify_options.get('current_node') is not None:
            migrate['current_node'] = modify_options.pop('current_node')
        if modify_options.get('current_port') is not None:
            migrate['current_port'] = modify_options.pop('current_port')
        if modify_options:
            options = {'interface-name': self.parameters['interface_name'],
                       'vserver': self.parameters['vserver']
                       }
            NetAppOntapInterface.set_options(options, modify_options)
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
        # ZAPI
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
        # like with REST, the migration may not be completed on the first try!
        # just blindly do it twice.
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
        if self.use_rest:
            return
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

    def get_action(self):
        modify, rename = None, None
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
        if cd_action is None:
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if rename and self.use_rest:
            rename = False
            if 'interface_name' not in modify:
                self.module.fail_json(msg='Error: inconsistency in rename action.')
        if modify and modify.get('home_node') == 'localhost':
            modify.pop('home_node')
            if not modify:
                self.na_helper.changed = False

        return cd_action, modify, rename, current

    def build_rest_payloads(self, cd_action, modify, current):
        body, migrate_body = None, None
        uuid = current.get('uuid') if current else None
        if self.use_rest:
            if cd_action == 'create':
                body, migrate_body = self.build_rest_body()
            elif modify:
                body, migrate_body = self.build_rest_body(modify)
            if (modify or cd_action == 'delete') and uuid is None:
                self.module.fail_json(msg='Error, expecting uuid in existing record')
        return uuid, body, migrate_body

    def apply(self):
        ''' calling all interface features '''
        self.autosupport_log()
        cd_action, modify, rename, current = self.get_action()
        uuid = current.get('uuid') if current else None

        # build the payloads even in check_mode, to perform validations
        uuid, body, migrate_body = self.build_rest_payloads(cd_action, modify, current)

        if self.na_helper.changed and not self.module.check_mode:
            if rename and not self.use_rest:
                self.rename_interface()
                modify.pop('interface_name')
            if cd_action == 'create':
                self.create_interface(body)
            elif cd_action == 'delete':
                self.delete_interface(current['admin_status'], uuid)
            elif modify:
                self.modify_interface(modify, uuid, body)
            if migrate_body:
                self.migrate_interface_rest(uuid, migrate_body)

        results = {'changed': self.na_helper.changed}
        if netapp_utils.has_feature(self.module, 'show_modified'):
            results['modify'] = str(modify)
        self.module.exit_json(**results)


def main():
    interface = NetAppOntapInterface()
    interface.apply()


if __name__ == '__main__':
    main()
