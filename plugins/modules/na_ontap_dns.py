#!/usr/bin/python

# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_dns
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = '''
module: na_ontap_dns
short_description: NetApp ONTAP Create, delete, modify DNS servers.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.7.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Create, delete, modify DNS servers.
- With REST, the module is currently limited to data vservers for delete or modify operations.
options:
  state:
    description:
    - Whether the DNS servers should be enabled for the given vserver.
    choices: ['present', 'absent']
    type: str
    default: present

  vserver:
    description:
    - The name of the vserver to use.
    required: true
    type: str

  domains:
    description:
    - List of DNS domains such as 'sales.bar.com'. The first domain is the one that the Vserver belongs to.
    type: list
    elements: str

  nameservers:
    description:
    - List of IPv4 addresses of name servers such as '123.123.123.123'.
    type: list
    elements: str

  skip_validation:
    type: bool
    description:
    - By default, all nameservers are checked to validate they are available to resolve.
    - If you DNS servers are not yet installed or momentarily not available, you can set this option to 'true'
    - to bypass the check for all servers specified in nameservers field.
    version_added: 2.8.0
'''

EXAMPLES = """
    - name: create DNS
      na_ontap_dns:
        state: present
        hostname: "{{hostname}}"
        username: "{{username}}"
        password: "{{password}}"
        vserver:  "{{vservername}}"
        domains: sales.bar.com
        nameservers: 10.193.0.250,10.192.0.250
        skip_validation: true
"""

RETURN = """

"""
import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapDns(object):
    """
    Enable and Disable dns
    """

    def __init__(self):
        self.use_rest = False
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            vserver=dict(required=True, type='str'),
            domains=dict(required=False, type='list', elements='str'),
            nameservers=dict(required=False, type='list', elements='str'),
            skip_validation=dict(required=False, type='bool')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            required_if=[('state', 'present', ['domains', 'nameservers'])],
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        # Cluster vserver and data vserver use different REST API.
        self.is_cluster = False

        # REST API should be used for ONTAP 9.6 or higher, ZAPI for lower version
        self.rest_api = OntapRestAPI(self.module)
        # some attributes are not supported in earlier REST implementation
        unsupported_rest_properties = ['skip_validation']
        used_unsupported_rest_properties = [x for x in unsupported_rest_properties if x in self.parameters]
        self.use_rest, error = self.rest_api.is_rest(used_unsupported_rest_properties)

        if error is not None:
            self.module.fail_json(msg=error)

        if not self.use_rest:
            if HAS_NETAPP_LIB is False:
                self.module.fail_json(msg="the python NetApp-Lib module is required")
            else:
                self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])
        return

    def create_dns(self):
        """
        Create DNS server
        :return: none
        """
        if self.use_rest:
            if self.is_cluster:
                api = 'cluster'
                params = {
                    'dns_domains': self.parameters['domains'],
                    'name_servers': self.parameters['nameservers']
                }
                dummy, error = self.rest_api.patch(api, params)
                if error:
                    self.module.fail_json(msg=error)
            else:
                api = 'name-services/dns'
                params = {
                    'domains': self.parameters['domains'],
                    'servers': self.parameters['nameservers'],
                    'svm': {
                        'name': self.parameters['vserver']
                    }
                }
                dummy, error = self.rest_api.post(api, params)
                if error:
                    self.module.fail_json(msg=error)
        else:
            dns = netapp_utils.zapi.NaElement('net-dns-create')
            nameservers = netapp_utils.zapi.NaElement('name-servers')
            domains = netapp_utils.zapi.NaElement('domains')
            for each in self.parameters['nameservers']:
                ip_address = netapp_utils.zapi.NaElement('ip-address')
                ip_address.set_content(each)
                nameservers.add_child_elem(ip_address)
            dns.add_child_elem(nameservers)
            for each in self.parameters['domains']:
                domain = netapp_utils.zapi.NaElement('string')
                domain.set_content(each)
                domains.add_child_elem(domain)
            dns.add_child_elem(domains)
            if self.parameters.get('skip_validation'):
                validation = netapp_utils.zapi.NaElement('skip-config-validation')
                validation.set_content(str(self.parameters['skip_validation']))
                dns.add_child_elem(validation)
            try:
                self.server.invoke_successfully(dns, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error creating dns: %s' %
                                      (to_native(error)),
                                      exception=traceback.format_exc())

    def destroy_dns(self, dns_attrs):
        """
        Destroys an already created dns
        :return:
        """
        if self.use_rest:
            if self.is_cluster:
                error = 'cluster operation for deleting DNS is not supported with REST.'
                self.module.fail_json(msg=error)
            api = 'name-services/dns/' + dns_attrs['uuid']
            dummy, error = self.rest_api.delete(api)
            if error:
                self.module.fail_json(msg=error)
        else:
            try:
                self.server.invoke_successfully(netapp_utils.zapi.NaElement('net-dns-destroy'), True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error destroying dns %s' %
                                      (to_native(error)),
                                      exception=traceback.format_exc())

    def get_cluster(self):
        api = "cluster"
        message, error = self.rest_api.get(api, None)
        if error:
            self.module.fail_json(msg=error)
        if len(message.keys()) == 0:
            self.module.fail_json(msg="no data from cluster %s" % str(message))
        return message

    def get_cluster_dns(self):
        cluster_attrs = self.get_cluster()
        dns_attrs = None
        if self.parameters['vserver'] == cluster_attrs['name']:
            dns_attrs = {
                'domains': cluster_attrs.get('dns_domains'),
                'nameservers': cluster_attrs.get('name_servers'),
                'uuid': cluster_attrs['uuid'],
            }
            self.is_cluster = True
            if dns_attrs['domains'] is None and dns_attrs['nameservers'] is None:
                dns_attrs = None
        return dns_attrs

    def get_dns(self):
        if self.use_rest:
            api = "name-services/dns"
            params = {'fields': 'domains,servers,svm',
                      "svm.name": self.parameters['vserver']}
            message, error = self.rest_api.get(api, params)
            if error:
                self.module.fail_json(msg=error)
            if len(message.keys()) == 0:
                message = None
            elif 'records' in message and len(message['records']) == 0:
                message = None
            elif 'records' not in message or len(message['records']) != 1:
                error = "Unexpected response from %s: %s" % (api, repr(message))
                self.module.fail_json(msg=error)
            if message is not None:
                record = message['records'][0]
                attrs = {
                    'domains': record['domains'],
                    'nameservers': record['servers'],
                    'uuid': record['svm']['uuid']
                }
                return attrs
            return None
        else:
            dns_obj = netapp_utils.zapi.NaElement('net-dns-get')
            try:
                result = self.server.invoke_successfully(dns_obj, True)
            except netapp_utils.zapi.NaApiError as error:
                if to_native(error.code) == "15661":
                    # 15661 is object not found
                    return None
                else:
                    self.module.fail_json(msg=to_native(
                        error), exception=traceback.format_exc())

            # read data for modify
            attrs = dict()
            attributes = result.get_child_by_name('attributes')
            dns_info = attributes.get_child_by_name('net-dns-info')
            nameservers = dns_info.get_child_by_name('name-servers')
            attrs['nameservers'] = [each.get_content() for each in nameservers.get_children()]
            domains = dns_info.get_child_by_name('domains')
            attrs['domains'] = [each.get_content() for each in domains.get_children()]
            attrs['skip_validation'] = dns_info.get_child_by_name('skip-config-validation')
            return attrs

    def modify_dns(self, dns_attrs):
        if self.use_rest:
            changed = False
            params = {}
            if dns_attrs['nameservers'] != self.parameters['nameservers']:
                changed = True
                params['servers'] = self.parameters['nameservers']
            if dns_attrs['domains'] != self.parameters['domains']:
                changed = True
                params['domains'] = self.parameters['domains']
            if changed and not self.module.check_mode:
                uuid = dns_attrs['uuid']
                api = "name-services/dns/" + uuid
                if self.is_cluster:
                    api = 'cluster'
                    params = {
                        'dns_domains': self.parameters['domains'],
                        'name_servers': self.parameters['nameservers']
                    }
                dummy, error = self.rest_api.patch(api, params)
                if error:
                    self.module.fail_json(msg=error)

        else:
            changed = False
            dns = netapp_utils.zapi.NaElement('net-dns-modify')
            if dns_attrs['nameservers'] != self.parameters['nameservers']:
                changed = True
                nameservers = netapp_utils.zapi.NaElement('name-servers')
                for each in self.parameters['nameservers']:
                    ip_address = netapp_utils.zapi.NaElement('ip-address')
                    ip_address.set_content(each)
                    nameservers.add_child_elem(ip_address)
                dns.add_child_elem(nameservers)
            if dns_attrs['domains'] != self.parameters['domains']:
                changed = True
                domains = netapp_utils.zapi.NaElement('domains')
                for each in self.parameters['domains']:
                    domain = netapp_utils.zapi.NaElement('string')
                    domain.set_content(each)
                    domains.add_child_elem(domain)
                dns.add_child_elem(domains)
            if changed and not self.module.check_mode:
                if self.parameters.get('skip_validation'):
                    validation = netapp_utils.zapi.NaElement('skip-config-validation')
                    validation.set_content(str(self.parameters['skip_validation']))
                    dns.add_child_elem(validation)
                try:
                    self.server.invoke_successfully(dns, True)
                except netapp_utils.zapi.NaApiError as error:
                    self.module.fail_json(msg='Error modifying dns %s' %
                                          (to_native(error)), exception=traceback.format_exc())
        return changed

    def apply(self):
        # asup logging
        if not self.use_rest:
            netapp_utils.ems_log_event("na_ontap_dns", self.server)
        dns_attrs = self.get_dns()
        if self.use_rest and dns_attrs is None:
            # There is a chance we are working at the cluster level
            dns_attrs = self.get_cluster_dns()
        changed = False
        if self.parameters['state'] == 'present':
            if dns_attrs is not None:
                changed = self.modify_dns(dns_attrs)
            else:
                if not self.module.check_mode:
                    self.create_dns()
                changed = True
        else:
            if dns_attrs is not None:
                if not self.module.check_mode:
                    self.destroy_dns(dns_attrs)
                changed = True
        self.module.exit_json(changed=changed)


def main():
    """
    Create, Delete, Modify DNS servers.
    """
    obj = NetAppOntapDns()
    obj.apply()


if __name__ == '__main__':
    main()
