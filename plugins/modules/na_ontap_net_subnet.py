#!/usr/bin/python
# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
module: na_ontap_net_subnet
short_description: NetApp ONTAP Create, delete, modify network subnets.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.8.0
author:  Storage Engineering (@Albinpopote) <ansible@black-perl.fr>
description:
  - Create, modify, destroy the network subnet
options:
  state:
    description:
      - Whether the specified network interface group should exist or not.
    choices: ['present', 'absent']
    default: present
    type: str

  broadcast_domain:
    description:
      - Specify the required broadcast_domain name for the subnet.
      - A broadcast domain can not be modified after the subnet has been created
    type: str

  name:
    description:
      - Specify the subnet name.
    required: true
    type: str

  from_name:
    description:
      - Name of the subnet to be renamed
    type: str

  gateway:
    description:
      - Specify the gateway for the default route of the subnet.
    type: str

  ipspace:
    description:
      - Specify the ipspace for the subnet.
      - The default value for this parameter is the default IPspace, named 'Default'.
    type: str

  ip_ranges:
    description:
      - Specify the list of IP address ranges associated with the subnet.
    type: list
    elements: str

  subnet:
    description:
      - Specify the subnet (ip and mask).
    type: str
"""

EXAMPLES = """
    - name: create subnet
      netapp.ontap.na_ontap_net_subnet:
        state: present
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        hostname: "{{ netapp_hostname }}"
        subnet: 10.10.10.0/24
        name: subnet-adm
        ip_ranges: [ '10.10.10.30-10.10.10.40', '10.10.10.51' ]
        gateway: 10.10.10.254
        ipspace: Default
        broadcast_domain: Default
    - name: delete subnet
      netapp.ontap.na_ontap_net_subnet:
        state: absent
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        hostname: "{{ netapp_hostname }}"
        name: subnet-adm
        ipspace: Default
    - name: rename subnet
      netapp.ontap.na_ontap_net_subnet:
        state: present
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        hostname: "{{ netapp_hostname }}"
        name: subnet-adm-new
        from_name: subnet-adm
        ipspace: Default
"""

RETURN = """

"""

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule


class NetAppOntapSubnet:
    """
    Create, Modifies and Destroys a subnet
    """
    def __init__(self):
        """
        Initialize the ONTAP Subnet class
        """
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str'),
            from_name=dict(required=False, type='str'),
            broadcast_domain=dict(required=False, type='str'),
            gateway=dict(required=False, type='str'),
            ip_ranges=dict(required=False, type='list', elements='str'),
            ipspace=dict(required=False, type='str'),
            subnet=dict(required=False, type='str')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.na_helper.module_deprecated(self.module)

        if not netapp_utils.has_netapp_lib():
            self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
        self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def get_subnet(self, name=None):
        """
        Return details about the subnet
        :param:
            name : Name of the subnet
        :return: Details about the subnet. None if not found.
        :rtype: dict
        """
        if name is None:
            name = self.parameters.get('name')

        subnet_iter = netapp_utils.zapi.NaElement('net-subnet-get-iter')
        subnet_info = netapp_utils.zapi.NaElement('net-subnet-info')
        subnet_info.add_new_child('subnet-name', name)
        if self.parameters.get('ipspace'):
            subnet_info.add_new_child('ipspace', self.parameters['ipspace'])
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(subnet_info)

        subnet_iter.add_child_elem(query)

        result = self.server.invoke_successfully(subnet_iter, True)
        return_value = None
        # check if query returns the expected subnet
        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) == 1:

            subnet_attributes = result.get_child_by_name('attributes-list').get_child_by_name('net-subnet-info')
            broadcast_domain = subnet_attributes.get_child_content('broadcast-domain')
            gateway = subnet_attributes.get_child_content('gateway')
            ipspace = subnet_attributes.get_child_content('ipspace')
            subnet = subnet_attributes.get_child_content('subnet')
            name = subnet_attributes.get_child_content('subnet-name')

            ip_ranges = []
            if subnet_attributes.get_child_by_name('ip-ranges'):
                range_obj = subnet_attributes.get_child_by_name('ip-ranges').get_children()
                ip_ranges = [elem.get_content() for elem in range_obj]

            return_value = {
                'name': name,
                'broadcast_domain': broadcast_domain,
                'gateway': gateway,
                'ip_ranges': ip_ranges,
                'ipspace': ipspace,
                'subnet': subnet
            }

        return return_value

    def create_subnet(self):
        """
        Creates a new subnet
        """
        subnet_create = self.build_zapi_request_for_create_or_modify('net-subnet-create')
        try:
            self.server.invoke_successfully(subnet_create, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating subnet %s: %s' % (self.parameters.get('name'), to_native(error)),
                                  exception=traceback.format_exc())

    def delete_subnet(self):
        """
        Deletes a subnet
        """
        subnet_delete = netapp_utils.zapi.NaElement.create_node_with_children(
            'net-subnet-destroy', **{'subnet-name': self.parameters.get('name')})
        if self.parameters.get('ipspace'):
            subnet_delete.add_new_child('ipspace', self.parameters.get('ipspace'))

        try:
            self.server.invoke_successfully(subnet_delete, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting subnet %s: %s' % (self.parameters.get('name'), to_native(error)),
                                  exception=traceback.format_exc())

    def modify_subnet(self):
        """
        Modifies a subnet
        """
        subnet_modify = self.build_zapi_request_for_create_or_modify('net-subnet-modify')
        try:
            self.server.invoke_successfully(subnet_modify, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying subnet %s: %s' % (self.parameters.get('name'), to_native(error)),
                                  exception=traceback.format_exc())

    def build_zapi_request_for_create_or_modify(self, zapi):
        simple_keys = ['gateway', 'ipspace', 'subnet']

        # required parameters
        options = {'subnet-name': self.parameters.get('name')}
        if zapi == 'net-subnet-create':
            options['broadcast-domain'] = self.parameters.get('broadcast_domain')
            options['subnet'] = self.parameters.get('subnet')
            simple_keys.remove('subnet')

        # optional parameters
        for key in simple_keys:
            value = self.parameters.get(key)
            if value is not None:
                options[key] = value

        result = netapp_utils.zapi.NaElement.create_node_with_children(zapi, **options)
        if self.parameters.get('ip_ranges'):
            subnet_ips = netapp_utils.zapi.NaElement('ip-ranges')
            for ip_range in self.parameters.get('ip_ranges'):
                subnet_ips.add_new_child('ip-range', ip_range)
            result.add_child_elem(subnet_ips)

        return result

    def rename_subnet(self):
        """
        TODO
        """
        options = {'subnet-name': self.parameters.get('from_name'),
                   'new-name': self.parameters.get('name')}

        subnet_rename = netapp_utils.zapi.NaElement.create_node_with_children(
            'net-subnet-rename', **options)

        if self.parameters.get('ipspace'):
            subnet_rename.add_new_child('ipspace', self.parameters.get('ipspace'))

        try:
            self.server.invoke_successfully(subnet_rename, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error renaming subnet %s: %s' % (self.parameters.get('name'), to_native(error)),
                                  exception=traceback.format_exc())

    def apply(self):
        '''Apply action to subnet'''
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("na_ontap_net_subnet", cserver)
        current = self.get_subnet()
        rename, modify = None, None

        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action == 'create' and self.parameters.get('from_name'):
            # creating new subnet by renaming
            current = self.get_subnet(self.parameters.get('from_name'))
            if current is None:
                self.module.fail_json(msg="Error renaming: subnet %s does not exist" %
                                      self.parameters.get('from_name'))
            rename = True
            cd_action = None

        if self.parameters['state'] == 'present' and current:
            current.pop('name', None)       # handled in rename
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
            if 'broadcast_domain' in modify:
                self.module.fail_json(msg='Error modifying subnet %s: cannot modify broadcast_domain parameter, desired "%s", currrent "%s"'
                                      % (self.parameters.get('name'), self.parameters.get('broadcast_domain'), current.get('broadcast_domain')))

        if cd_action == 'create':
            for attribute in ['subnet', 'broadcast_domain']:
                if not self.parameters.get(attribute):
                    self.module.fail_json(msg='Error - missing required arguments: %s.' % attribute)

        if self.na_helper.changed and not self.module.check_mode:
            if rename:
                self.rename_subnet()
            # If rename is True, cd_action is None but modify could be true
            if cd_action == 'create':
                self.create_subnet()
            elif cd_action == 'delete':
                self.delete_subnet()
            elif modify:
                self.modify_subnet()
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """
    Creates the NetApp ONTAP Net Route object and runs the correct play task
    """
    subnet_obj = NetAppOntapSubnet()
    subnet_obj.apply()


if __name__ == '__main__':
    main()
