#!/usr/bin/python

# (c) 2018-2026, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = '''
module: na_ontap_service_processor_network
short_description: NetApp ONTAP service processor network
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansible-team@netapp.com>
description:
  - Modify a ONTAP service processor network
options:
  state:
    description:
      - Whether the specified service processor network should exist or not.
    choices: ['present']
    type: str
    default: present
  address_type:
    description:
      - Specify address class.
    required: true
    type: str
    choices: ['ipv4', 'ipv6']
  is_enabled:
    description:
      - Specify whether to enable or disable the service processor network.
      - Setting C(ip_address), C(netmask) or C(prefix_length), C(gateway_ip_address) will enable sp network in REST.
    type: bool
  node:
    description:
      - The node where the service processor network should be enabled
    required: true
    type: str
  dhcp:
    description:
      - Specify dhcp type.
      - Setting C(dhcp=none) requires all of C(ip_address), C(netmask), C(gateway_ip_address) and at least one of its value different from current.
    type: str
    choices: ['v4', 'none']
  gateway_ip_address:
    description:
      - Specify the gateway ip.
    type: str
  ip_address:
    description:
      - Specify the service processor ip address.
    type: str
  netmask:
    description:
      - Specify the service processor netmask.
    type: str
  prefix_length:
    description:
      - Specify the service processor prefix_length.
    type: int
  wait_for_completion:
    description:
      - Set this parameter to 'true' for synchronous execution (wait until SP status is successfully updated)
      - Set this parameter to 'false' for asynchronous execution
      - For asynchronous, execution exits as soon as the request is sent, without checking SP status
    type: bool
    default: false
    version_added: 2.8.0
'''

EXAMPLES = """
- name: Modify Service Processor Network, enable dhcp - ipv4.
  netapp.ontap.na_ontap_service_processor_network:
    state: present
    address_type: ipv4
    is_enabled: true
    dhcp: v4
    node: "{{ netapp_node }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    hostname: "{{ netapp_hostname }}"

- name: Enable Service Processor Network configuration - ipv4.
  netapp.ontap.na_ontap_service_processor_network:
    state: present
    address_type: ipv4
    is_enabled: true
    dhcp: None
    ip_address: 10.10.10.1
    netmask: 0.0.0.0
    gateway_ip_address: 10.10.1.1
    wait_for_completion: true
    node: "{{ netapp_node }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    hostname: "{{ netapp_hostname }}"

- name: Disable Service Processor Network configuration - ipv4.
  netapp.ontap.na_ontap_service_processor_network:
    state: present
    address_type: ipv4
    is_enabled: false
    wait_for_completion: true
    node: "{{ netapp_node }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    hostname: "{{ netapp_hostname }}"

- name: Enable Service Processor Network configuration - ipv6.
  netapp.ontap.na_ontap_service_processor_network:
    state: present
    address_type: ipv6
    is_enabled: true
    ip_address: FD20:8B1E:B058:2014:25BE:67F9:0748:6D6B
    prefix_length: 64
    gateway_ip_address: FD20:8B1E:B058:2014:0000:0000:0000:0001
    wait_for_completion: true
    node: "{{ netapp_node }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    hostname: "{{ netapp_hostname }}"

- name: Disable Service Processor Network configuration - ipv6.
  netapp.ontap.na_ontap_service_processor_network:
    state: present
    address_type: ipv6
    is_enabled: false
    wait_for_completion: true
    node: "{{ netapp_node }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    hostname: "{{ netapp_hostname }}"
"""

RETURN = """
"""
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic
from ansible_collections.netapp.ontap.plugins.module_utils import netapp_ipaddress
import time


class NetAppOntapServiceProcessorNetwork:
    """
        Modify a Service Processor Network
    """

    def __init__(self):
        """
            Initialize the NetAppOntapServiceProcessorNetwork class
        """
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present'], default='present'),
            address_type=dict(required=True, type='str', choices=['ipv4', 'ipv6']),
            is_enabled=dict(required=False, type='bool'),
            node=dict(required=True, type='str'),
            dhcp=dict(required=False, type='str', choices=['v4', 'none']),
            gateway_ip_address=dict(required=False, type='str'),
            ip_address=dict(required=False, type='str'),
            netmask=dict(required=False, type='str'),
            prefix_length=dict(required=False, type='int'),
            wait_for_completion=dict(required=False, type='bool', default=False)
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True,
            mutually_exclusive=[('netmask', 'prefix_length')]
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        # Set up Rest API
        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        partially_supported_rest_properties = [['is_enabled', (9, 14, 1)]]
        self.use_rest = self.rest_api.is_rest_supported_properties(self.parameters, partially_supported_rest_properties=partially_supported_rest_properties)
        self.uuid, self.ipv4_or_ipv6 = None, None
        dhcp_mutual_options = ['ip_address', 'gateway_ip_address', 'netmask']
        if self.parameters.get('dhcp') == 'v4':
            # error if dhcp is set to v4 and address_type is ipv6.
            if self.parameters['address_type'] == 'ipv6':
                self.module.fail_json(msg="Error: dhcp cannot be set for address_type: ipv6.")
            # error if dhcp is set to v4 and manual interface options are present.
            if self.parameters['is_enabled'] is True:
                if any(x in self.parameters for x in dhcp_mutual_options):
                    self.module.fail_json(msg="Error: set dhcp v4 or all of 'ip_address, gateway_ip_address, netmask'.")
        if not self.use_rest:
            if not netapp_utils.has_netapp_lib():
                self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
            if 'is_enabled' not in self.parameters:
                self.module.fail_json(msg='missing required arguments: is_enabled in ZAPI')
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=None)
            self.set_playbook_zapi_key_map()

    def normalize_ipv6_address(self, ip_addr):
        """Normalize IPv6 address to a consistent format for comparison"""
        if not ip_addr:
            return ip_addr
        try:
            return netapp_ipaddress.validate_and_compress_ip_address(ip_addr, self.module)
        except Exception:
            # If it's not a valid IPv6 address, return as is
            return ip_addr

    def set_playbook_zapi_key_map(self):
        self.na_helper.zapi_string_keys = {
            'address_type': 'address-type',
            'node': 'node',
            'dhcp': 'dhcp',
            'gateway_ip_address': 'gateway-ip-address',
            'ip_address': 'ip-address',
            'netmask': 'netmask'
        }
        self.na_helper.zapi_int_keys = {
            'prefix_length': 'prefix-length'
        }
        self.na_helper.zapi_bool_keys = {
            'is_enabled': 'is-enabled',
        }
        self.na_helper.zapi_required = {
            'address_type': 'address-type',
            'node': 'node',
            'is_enabled': 'is-enabled'
        }

    def get_sp_network_status(self):
        """
        Return status of service processor network
        :param:
            name : name of the node
        :return: Status of the service processor network
        :rtype: dict
        """
        spn_get_iter = netapp_utils.zapi.NaElement('service-processor-network-get-iter')
        query_info = {
            'query': {
                'service-processor-network-info': {
                    'node': self.parameters['node'],
                    'address-type': self.parameters['address_type']
                }
            }
        }
        spn_get_iter.translate_struct(query_info)
        try:
            result = self.server.invoke_successfully(spn_get_iter, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching service processor network status for %s: %s' %
                                  (self.parameters['node'], to_native(error)), exception=traceback.format_exc())
        if int(result['num-records']) >= 1:
            sp_attr_info = result['attributes-list']['service-processor-network-info']
            status = sp_attr_info.get_child_content('setup-status')
            return status
        return None

    def get_service_processor_network(self):
        """
        Return details about service processor network
        :param:
            name : name of the node
        :return: Details about service processor network. None if not found.
        :rtype: dict
        """
        if self.use_rest:
            return self.get_service_processor_network_rest()
        spn_get_iter = netapp_utils.zapi.NaElement('service-processor-network-get-iter')
        query_info = {
            'query': {
                'service-processor-network-info': {
                    'node': self.parameters['node'],
                    'address-type': self.parameters['address_type']
                }
            }
        }
        spn_get_iter.translate_struct(query_info)
        try:
            result = self.server.invoke_successfully(spn_get_iter, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching service processor network info for %s: %s' %
                                  (self.parameters['node'], to_native(error)), exception=traceback.format_exc())
        sp_details = None
        # check if job exists
        if int(result['num-records']) >= 1:
            sp_details = dict()
            sp_attr_info = result['attributes-list']['service-processor-network-info']
            for item_key, zapi_key in self.na_helper.zapi_string_keys.items():
                sp_details[item_key] = sp_attr_info.get_child_content(zapi_key)
                # set dhcp: 'none' if current dhcp set as None to avoid idempotent issue.
                if item_key == 'dhcp' and sp_details[item_key] is None:
                    sp_details[item_key] = 'none'
                # Normalize IPv6 addresses for consistent comparison
                if item_key in ['ip_address', 'gateway_ip_address']:
                    original_value = sp_details[item_key]
                    sp_details[item_key] = self.normalize_ipv6_address(sp_details[item_key])
            for item_key, zapi_key in self.na_helper.zapi_bool_keys.items():
                sp_details[item_key] = self.na_helper.get_value_for_bool(from_zapi=True,
                                                                         value=sp_attr_info.get_child_content(zapi_key))
            for item_key, zapi_key in self.na_helper.zapi_int_keys.items():
                sp_details[item_key] = self.na_helper.get_value_for_int(from_zapi=True,
                                                                        value=sp_attr_info.get_child_content(zapi_key))
        return sp_details

    def modify_service_processor_network(self, modify):
        """
        Modify a service processor network.
        When dhcp is not set to v4, ip_address, netmask, and gateway_ip_address must be specified even if remains the same.
        """
        if self.use_rest:
            return self.modify_service_processor_network_rest(modify)

        sp_modify = netapp_utils.zapi.NaElement('service-processor-network-modify')
        sp_attributes = dict()
        # Determine which parameters to process: essential only when disabling, all when enabling
        params = (['node', 'address_type', 'is_enabled'] if self.parameters.get('is_enabled') is False else self.parameters.keys())

        # Process parameters
        for item_key in params:
            if item_key in self.na_helper.zapi_string_keys:
                zapi_key = self.na_helper.zapi_string_keys.get(item_key)
                sp_attributes[zapi_key] = self.parameters[item_key]
            elif item_key in self.na_helper.zapi_bool_keys:
                zapi_key = self.na_helper.zapi_bool_keys.get(item_key)
                sp_attributes[zapi_key] = self.na_helper.get_value_for_bool(from_zapi=False, value=self.parameters[item_key])
            elif item_key in self.na_helper.zapi_int_keys:
                zapi_key = self.na_helper.zapi_int_keys.get(item_key)
                sp_attributes[zapi_key] = self.na_helper.get_value_for_int(from_zapi=False, value=self.parameters[item_key])

        sp_modify.translate_struct(sp_attributes)
        try:
            self.server.invoke_successfully(sp_modify, enable_tunneling=True)

            if self.parameters.get('wait_for_completion'):
                if self.parameters.get('is_enabled') is False:
                    retries = 40
                    while retries > 0:
                        current_config = self.get_service_processor_network()
                        if current_config.get('is_enabled') is False:
                            break
                        time.sleep(15)
                        retries -= 1
                else:
                    retries = 25
                    status_key = 'not_setup'
                    while self.get_sp_network_status() == status_key and retries > 0:
                        time.sleep(15)
                        retries -= 1
                    # In ZAPI, once the status is 'succeeded', it takes few more seconds for ip details take effect.
                    time.sleep(10)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying service processor network: %s' % (to_native(error)),
                                  exception=traceback.format_exc())

    def get_service_processor_network_rest(self):
        """
        Retrieves a service processor network configuration.
        """
        api = 'cluster/nodes'
        fields = 'uuid,service_processor.ipv4_interface,service_processor.ipv6_interface,service_processor.dhcp_enabled'
        query = {'name': self.parameters['node']}
        record, error = rest_generic.get_one_record(self.rest_api, api, query, fields)
        if error:
            self.module.fail_json(msg='Error fetching service processor network info for %s: %s' %
                                  (self.parameters['node'], error))

        if not record:
            return None

        self.uuid = record['uuid']
        self.ipv4_or_ipv6 = 'ipv4_interface' if self.parameters['address_type'] == 'ipv4' else 'ipv6_interface'
        interface_data = self.na_helper.safe_get(record, ['service_processor', self.ipv4_or_ipv6])

        current = {
            'gateway_ip_address': self.normalize_ipv6_address(self.na_helper.safe_get(interface_data, ['gateway'])) if interface_data else None,
            'ip_address': self.normalize_ipv6_address(self.na_helper.safe_get(interface_data, ['address'])) if interface_data else None,
            'is_enabled': self.na_helper.safe_get(interface_data, ['enabled']) if interface_data else False
        }

        if self.parameters['address_type'] == 'ipv4':
            current['dhcp'] = 'v4' if self.na_helper.safe_get(record, ['service_processor', 'dhcp_enabled']) else 'none'
            current['netmask'] = self.na_helper.safe_get(interface_data, ['netmask']) if interface_data else None
        else:  # ipv6
            current['dhcp'] = 'none'
            current['prefix_length'] = self.na_helper.safe_get(interface_data, ['netmask']) if interface_data else None

        return current

    def get_interface_config(self, enabled=None):
        """Build interface configuration for REST API"""
        config = {}
        if enabled is not None:
            config['enabled'] = enabled
            # Only add IP config when enabling
            if enabled:
                for param, key in [('ip_address', 'address'), ('gateway_ip_address', 'gateway')]:
                    if self.parameters.get(param):
                        config[key] = self.parameters[param]
                # Handling netmask/prefix_length properly for IPv4/IPv6
                if self.parameters['address_type'] == 'ipv4':
                    if self.parameters.get('netmask'):
                        config['netmask'] = self.parameters['netmask']
                    elif self.parameters.get('prefix_length'):
                        error_msg = ("Error: For IPv4 address_type, use 'netmask' parameter instead of 'prefix_length'.")
                        self.module.fail_json(msg=error_msg)
                else:  # IPv6
                    if self.parameters.get('prefix_length'):
                        config['netmask'] = self.parameters['prefix_length']
                    elif self.parameters.get('netmask'):
                        config['netmask'] = self.parameters['netmask']
        return config

    def get_other_interface_config(self, other_config, disabling_current):
        """Get configuration for the other interface (IPv4/IPv6)"""
        if disabling_current:
            # Must have valid other interface when disabling current
            if not (other_config and other_config.get('ip_address') and other_config.get('gateway_ip_address')):
                other_type = 'ipv6' if self.parameters['address_type'] == 'ipv4' else 'ipv4'
                self.module.fail_json(msg='Cannot disable %s - %s interface not configured' % (self.parameters['address_type'], other_type))
            netmask_value = other_config.get('netmask') or other_config.get('prefix_length')
            return {'enabled': True, 'address': other_config['ip_address'], 'gateway': other_config['gateway_ip_address'],
                    'netmask': netmask_value}

        # Preserve other interface state when enabling/modifying current
        if not other_config:
            return {'enabled': False}

        valid_config = (other_config.get('ip_address') and other_config.get('gateway_ip_address')
                        and (other_config.get('netmask') or other_config.get('prefix_length')))

        if other_config.get('is_enabled') and valid_config:
            netmask_value = other_config.get('netmask') or other_config.get('prefix_length')
            return {'enabled': True, 'address': other_config['ip_address'], 'gateway': other_config['gateway_ip_address'],
                    'netmask': netmask_value}
        return {'enabled': False}

    def modify_service_processor_network_rest(self, modify):
        """Modify interface configuration service processor using REST API"""
        target_enabled = self.parameters.get('is_enabled')
        address_type = self.parameters['address_type']

        body = {'service_processor': {
            self.ipv4_or_ipv6: self.get_interface_config(target_enabled)
        }}

        # Handling other interface
        other_type = 'ipv6' if address_type == 'ipv4' else 'ipv4'
        other_interface = other_type + '_interface'
        original_type = self.parameters['address_type']
        self.parameters['address_type'] = other_type
        other_config = self.get_service_processor_network_rest()
        self.parameters['address_type'] = original_type

        other_interface_config = self.get_other_interface_config(other_config, target_enabled is False)
        body['service_processor'][other_interface] = {k: v for k, v in other_interface_config.items() if v is not None}

        # Set DHCP
        if 'dhcp' in self.parameters:
            body['service_processor']['dhcp_enabled'] = True if self.parameters['dhcp'] == 'v4' else False
        # if dhcp is enabled in REST, setting ip_address details manually requires dhcp: 'none' in params.
        # if dhcp: 'none' is not in params set it False to disable dhcp and assign manual ip address.
        elif (body['service_processor'][self.ipv4_or_ipv6].get('gateway') and
              body['service_processor'][self.ipv4_or_ipv6].get('address') and
              body['service_processor'][self.ipv4_or_ipv6].get('netmask')):
            body['service_processor']['dhcp_enabled'] = False

        dummy, error = rest_generic.patch_async(self.rest_api, 'cluster/nodes', self.uuid, body)
        if error:
            self.module.fail_json(msg='Error modifying service processor network: %s' % error)

        if self.parameters.get('wait_for_completion'):
            for retry in range(25):
                if self.is_sp_modified_rest(modify):
                    break
                time.sleep(15)

    def is_sp_modified_rest(self, modify):
        current = self.get_service_processor_network_rest()
        if current is None:
            return False
        for sp_option in modify:
            if modify[sp_option] != current[sp_option]:
                return False
        return True

    def filter_params_for_disabled_interface(self, current, params):
        """Filter out IP configuration parameters when disabling interface for idempotency"""
        ignored_fields = ['gateway_ip_address', 'ip_address', 'netmask', 'prefix_length', 'dhcp']

        # Check if any ignored fields are present in parameters
        ignored_present = [field for field in ignored_fields if field in params]

        if ignored_present:
            self.module.warn("Ignoring %s parameters when disabling interface for idempotency. Only is_enabled will be processed." % ', '.join(ignored_present))

        # Remove IP fields from both current and parameters for comparison
        current_for_compare = {k: v for k, v in current.items() if k not in ignored_fields}
        compare_params = {k: v for k, v in params.items() if k not in ignored_fields}
        return current_for_compare, compare_params

    def validate_rest(self, current):
        # If we're disabling the interface, exclude IP configuration from comparison for idempotency
        if self.parameters.get('is_enabled') is False:
            return self.filter_params_for_disabled_interface(current, self.parameters)

        # Use already normalized parameters from apply() method
        normalized_params = self.parameters.copy()
        if self.parameters['address_type'] == 'ipv6':
            if 'ip_address' in normalized_params:
                normalized_params['ip_address'] = self.normalize_ipv6_address(normalized_params['ip_address'])
            if 'gateway_ip_address' in normalized_params:
                normalized_params['gateway_ip_address'] = self.normalize_ipv6_address(normalized_params['gateway_ip_address'])

        return current, normalized_params

    def apply(self):
        """
        Run Module based on play book
        """
        current = self.get_service_processor_network()
        if not current:
            self.module.fail_json(msg='Error No Service Processor for node: %s' % self.parameters['node'])

        # Normalize IPv6 addresses in parameters for consistent comparison
        normalized_params = self.parameters.copy()
        if self.parameters['address_type'] == 'ipv6':
            for field in ['ip_address', 'gateway_ip_address']:
                if field in normalized_params:
                    normalized_params[field] = self.normalize_ipv6_address(normalized_params[field])

        if self.use_rest:
            current_for_compare, compare_params = self.validate_rest(current)
        else:
            if self.parameters.get('is_enabled') is False:
                current_for_compare, compare_params = self.filter_params_for_disabled_interface(current, normalized_params)
            else:
                current_for_compare, compare_params = current, normalized_params

        modify = self.na_helper.get_modified_attributes(current_for_compare, compare_params)
        if modify:
            if modify.get('dhcp') == 'none' and not any(x in modify for x in ['ip_address', 'gateway_ip_address', 'netmask']):
                error = "Error: To disable dhcp, configure ip-address, netmask and gateway details manually."
                self.module.fail_json(msg=error)
            if self.use_rest:
                self.validate_rest(modify)
            self.na_helper.changed = True
        if self.na_helper.changed and not self.module.check_mode:
            self.modify_service_processor_network(modify)
        result = netapp_utils.generate_result(self.na_helper.changed, modify=modify)
        self.module.exit_json(**result)


def main():
    """
    Create the NetApp Ontap Service Processor Network Object and modify it
    """

    obj = NetAppOntapServiceProcessorNetwork()
    obj.apply()


if __name__ == '__main__':
    main()
