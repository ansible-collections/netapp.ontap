#!/usr/bin/python

# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = """
module: na_ontap_storage_failover
short_description: Enables or disables NetApp Ontap storage failover for a specified node
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
version_added: '21.3.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
  - Enable or disable storage failover

options:

  state:
    description:
    - Whether storage failover should be enabled (present) or disabled (absent).
    choices: ['present', 'absent']
    default: present
    type: str

  node_name:
    description:
    - Specifies the node name to enable or disable storage failover.
    required: true
    type: str

"""

EXAMPLES = """
- name: Enable storage failover
  na_ontap_storage_failover:
    state: present
    node_name: node1
    hostname: "{{ hostname }}"
    username: "{{ username }}"
    password: "{{ password }}"

- name: Disable storage failover
  na_ontap_storage_failover:
    state: absent
    node_name: node1
    hostname: "{{ hostname }}"
    username: "{{ username }}"
    password: "{{ password }}"

"""

RETURN = """

"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
import ansible_collections.netapp.ontap.plugins.module_utils.rest_response_helpers as rrh

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapStorageFailover(object):
    """
        Enable or disable storage failover for a specified node
    """
    def __init__(self):
        """
            Initialize the Ontap Storage failover class
        """

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            node_name=dict(required=True, type='str'),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        # set up variables
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if self.parameters['state'] == 'present':
            self.parameters['is_enabled'] = True
        else:
            self.parameters['is_enabled'] = False

        self.rest_api = OntapRestAPI(self.module)
        self.use_rest = self.rest_api.is_rest()

        if not self.use_rest:
            if HAS_NETAPP_LIB is False:
                self.module.fail_json(msg='The python NetApp-Lib module is required')
            else:
                self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def get_storage_failover(self):
        """
        get the storage failover for a given node
        :return: dict of is-enabled: true if enabled is true None if not
        """

        if self.use_rest:
            return_value = None
            api = "cluster/nodes"
            query = {
                'fields': 'uuid,ha.enabled',
                'name': self.parameters['node_name']
            }
            message, error = self.rest_api.get(api, query)
            records, error = rrh.check_for_0_or_1_records(api, message, error)

            if error is None and records is not None:
                return_value = {
                    'uuid': message['records'][0]['uuid'],
                    'is_enabled': message['records'][0]['ha']['enabled']
                }

            if error:
                self.module.fail_json(msg=error)

            if not records:
                error = "REST API did not return failover details for node %s" % (self.parameters['node_name'])
                self.module.fail_json(msg=error)

            return return_value

        else:
            storage_failover_get_iter = netapp_utils.zapi.NaElement('cf-status')
            storage_failover_get_iter.add_new_child('node', self.parameters['node_name'])

            try:
                result = self.server.invoke_successfully(storage_failover_get_iter, True)
                return_value = {'is_enabled': self.na_helper.get_value_for_bool(True, result.get_child_content('is-enabled'))}

            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error getting storage failover info for node %s: %s' % (
                    self.parameters['node_name'], to_native(error)), exception=traceback.format_exc())

            return return_value

    def modify_storage_failover(self, current):
        """
        Modifies storage failover for a specified node
        """

        if self.use_rest:
            api = "cluster/nodes"
            query = {
                'uuid': current['uuid'],
                'return_timeout': 60  # Timeout added to allow for return messages
            }
            body = {'ha': {'enabled': self.parameters['is_enabled']}}
            message, error = self.rest_api.patch(api, body, query)
            if error:
                self.module.fail_json(msg=error)

        else:

            if self.parameters['state'] == 'present':
                cf_service = 'cf-service-enable'
            else:
                cf_service = 'cf-service-disable'

            storage_failover_modify = netapp_utils.zapi.NaElement(cf_service)
            storage_failover_modify.add_new_child('node', self.parameters['node_name'])

            try:
                self.server.invoke_successfully(storage_failover_modify, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error modifying storage failover for node %s: %s' % (
                    self.parameters['node_name'], to_native(error)), exception=traceback.format_exc())

    def ems_log_event(self):
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        return netapp_utils.ems_log_event("na_ontap_storage_failover", cserver)

    def apply(self):
        if not self.use_rest:
            self.ems_log_event()

        current = self.get_storage_failover()
        self.na_helper.get_modified_attributes(current, self.parameters)

        if self.na_helper.changed:
            if not self.module.check_mode:
                self.modify_storage_failover(current)
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """
    Enables or disables NetApp Ontap storage failover for a specified node
    """

    obj = NetAppOntapStorageFailover()
    obj.apply()


if __name__ == '__main__':
    main()
