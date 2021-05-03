#!/usr/bin/python

# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = """
module: na_ontap_security_config
short_description: NetApp ONTAP modify security config for SSL.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '21.3.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Modifies the security configuration for SSL.
options:
  name:
    description:
    - The type of FIPS compliant interface.
    type: str
    default: ssl

  is_fips_enabled:
    description:
    - Enables or disables FIPS-compliant mode for the cluster.
    type: bool

  supported_ciphers:
    description:
    - Selects the supported cipher suites for the selected interface.
    type: str

  supported_protocols:
    description:
    - Selects the supported protocols for the selected interface. Supported_ciphers should not be specified if operating in FIPS-compliant mode.
    choices: ['TLSv1.2', 'TLSv1.1', 'TLSv1']
    type: list
    elements: str
"""

EXAMPLES = """
    - name: Modify SSL Security Config
      na_ontap_security_config:
        name: ssl
        is_fips_enabled: false
        supported_ciphers:  'ALL:!LOW:!aNULL:!EXP:!eNULL:!3DES:!RC4:!SHA1'
        supported_protocols: ['TLSv1.2', 'TLSv1.1', 'TLSv1']
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        ontapi: "{{ ontap_info.ontap_info.ontap_version }}"
        https: true
        validate_certs: false
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


class NetAppOntapSecurityConfig(object):
    """
        Modifies SSL Security Config
    """
    def __init__(self):
        """
            Initialize the ONTAP Security Config class
        """
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            name=dict(required=False, type='str', default='ssl'),
            is_fips_enabled=dict(required=False, type='bool'),
            supported_ciphers=dict(required=False, type='str'),
            supported_protocols=dict(required=False, type='list', elements='str', choices=['TLSv1.2', 'TLSv1.1', 'TLSv1'])
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if 'is_fips_enabled' in self.parameters and 'supported_ciphers' in self.parameters:
            #  if fips is enabled, supported ciphers should not be specified.
            if self.parameters['is_fips_enabled']:
                self.module.fail_json(
                    msg='is_fips_enabled was specified as true and supported_ciphers was specified. \
                    If fips is enabled then supported ciphers should not be specified')

        if 'is_fips_enabled' in self.parameters and 'supported_protocols' in self.parameters:
            #  if fips is enabled, TLSv1 is not a supported protocol.
            if self.parameters['is_fips_enabled'] and 'TLSv1' in self.parameters['supported_protocols']:
                self.module.fail_json(
                    msg='is_fips_enabled was specified as true and TLSv1 was specified as a supported protocol. \
                    If fips is enabled then TLSv1 is not a supported protocol')

        if 'supported_ciphers' in self.parameters:
            self.parameters['supported_ciphers'] = self.parameters['supported_ciphers'].replace('\\', '')

        self.rest_api = OntapRestAPI(self.module)
        self.use_rest = self.rest_api.is_rest()

        if not self.use_rest:
            if HAS_NETAPP_LIB is False:
                self.module.fail_json(msg='The python NetApp-Lib module is required')
            else:
                self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def get_security_config(self):
        """
            Get the current security configuration
        """
        if self.use_rest:
            api = "private/cli/security/config"
            query = {
                'fields': 'interface,is-fips-enabled,supported-protocols,supported-ciphers'
            }
            message, error = self.rest_api.get(api, query)
            if error:
                self.module.fail_json(msg=error)
            if not message:
                self.module.fail_json(msg="get_security_config expected a message")

            return_value = {
                'name': message['records'][0]['interface'],
                'is_fips_enabled': message['records'][0]['is_fips_enabled'],
                'supported_ciphers': message['records'][0]['supported_ciphers'],
                'supported_protocols': message['records'][0]['supported_protocols']
            }
        else:
            return_value = None

            security_config_get_iter = netapp_utils.zapi.NaElement('security-config-get')
            security_config_info = netapp_utils.zapi.NaElement('desired-attributes')

            if 'is_fips_enabled' in self.parameters:
                security_config_info.add_new_child(
                    'is-fips-enabled', self.na_helper.get_value_for_bool(from_zapi=False, value=self.parameters['is_fips_enabled'])
                )
            if 'supported_ciphers' in self.parameters:
                security_config_info.add_new_child('supported-ciphers', self.parameters['supported_ciphers'])
            if 'supported_protocols' in self.parameters:
                security_config_info.add_new_child('supported-protocols', ','.join(self.parameters['supported_protocols']))

            security_config_get_iter.add_child_elem(security_config_info)
            security_config_get_iter.add_new_child('interface', self.parameters['name'])

            try:
                result = self.server.invoke_successfully(security_config_get_iter, True)
                security_supported_protocols = []

                if result.get_child_by_name('attributes'):
                    attributes = result.get_child_by_name('attributes')
                    security_config_attributes = attributes.get_child_by_name('security-config-info')
                    supported_protocols = security_config_attributes.get_child_by_name('supported-protocols')
                    for supported_protocol in supported_protocols.get_children():
                        security_supported_protocols.append(supported_protocol.get_content())

                    return_value = {
                        'name': security_config_attributes['interface'],
                        'is_fips_enabled': self.na_helper.get_value_for_bool(from_zapi=True, value=security_config_attributes['is-fips-enabled']),
                        'supported_ciphers': security_config_attributes['supported-ciphers'],
                        'supported_protocols': security_supported_protocols,
                    }

            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(
                    msg='Error getting security config for interface %s: %s' % (self.parameters['name'], to_native(error)),
                    exception=traceback.format_exc())

        return return_value

    def modify_security_config(self):
        """
        Modifies the security configuration.
        """
        if self.use_rest:
            #  url contains the value for 'name' due to the interface not being supported through body using the api.
            api = "private/cli/security/config?interface=%s" % (self.parameters['name'])
            body = {}
            if 'is_fips_enabled' in self.parameters:
                body['is_fips_enabled'] = self.parameters['is_fips_enabled']
            if 'supported_ciphers' in self.parameters:
                body['supported_ciphers'] = self.parameters['supported_ciphers']
            if 'supported_protocols' in self.parameters:
                body['supported_protocols'] = self.parameters['supported_protocols']

            dummy, error = self.rest_api.patch(api, body)

            if error:
                self.module.fail_json(msg=error)
        else:
            security_config_obj = netapp_utils.zapi.NaElement("security-config-modify")
            security_config_obj.add_new_child("interface", self.parameters['name'])
            if 'is_fips_enabled' in self.parameters:
                self.parameters['is_fips_enabled'] = self.na_helper.get_value_for_bool(from_zapi=False, value=self.parameters['is_fips_enabled'])
                security_config_obj.add_new_child('is-fips-enabled', self.parameters['is_fips_enabled'])
            if 'supported_ciphers' in self.parameters:
                security_config_obj.add_new_child('supported-ciphers', self.parameters['supported_ciphers'])
            if 'supported_protocols' in self.parameters:
                supported_protocol_obj = netapp_utils.zapi.NaElement("supported-protocols")
                for protocol in self.parameters['supported_protocols']:
                    supported_protocol_obj.add_new_child('string', protocol)
                security_config_obj.add_child_elem(supported_protocol_obj)
            try:
                self.server.invoke_successfully(security_config_obj, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(
                    msg='Error modifying security config for interface %s: %s' % (self.parameters['name'], to_native(error)),
                    exception=traceback.format_exc()
                )

    def ems_log_event(self):
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("na_ontap_security_config", cserver)

    def apply(self):
        if not self.use_rest:
            self.ems_log_event()
        current = self.get_security_config()
        self.na_helper.get_modified_attributes(current, self.parameters)

        if self.na_helper.changed:
            if not self.module.check_mode:
                self.modify_security_config()

        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """
    Creates the NetApp ONTAP security config object and runs the correct play task
    """
    obj = NetAppOntapSecurityConfig()
    obj.apply()


if __name__ == '__main__':
    main()
