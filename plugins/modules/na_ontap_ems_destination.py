#!/usr/bin/python

# (c) 2019-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_ems_destination
'''
from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
module: na_ontap_ems_destination
short_description: NetApp ONTAP configuration for EMS event destinations.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: ?
author: Bartosz Bielawski (@bielawb) <bartek.bielawski@live.com>
description:
- Configure EMS destinations. Currently certificate authentication for REST is not supported.
options:
  state:
    description:
    - Whether the destination should be present or not.
    choices: ['present', 'absent']
    type: str
    default: present

  name:
    description:
    - Name of the EMS destination
    required: true
    type: str

  type:
    description:
    - Type of the EMS destination.
    choices: ['email', 'syslog', 'rest_api']
    required: true
    type: str

  destination:
    description:
    - Destination - content depends on the type
    required: true
    type: str

'''

EXAMPLES = """
    - name: Configure REST EMS destination
      na_ontap_ems_destination:
        state: present
        name: rest
        type: rest_api
        destination: http://my.rest.api/address
        hostname: "{{hostname}}"
        username: "{{username}}"
        password: "{{password}}"
"""

RETURN = """

"""
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()

class NetAppOntapEmsDestination:
    """Create/ Modify/ Remove EMS destinations"""
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
                state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
                name=dict(required=True, type='str'),
                type=dict(required=True, type='str', choices=['email', 'syslog', 'rest_api']),
                destination=dict(required=True, type='str')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.rest_api = OntapRestAPI(self.module)
        self.use_rest = self.rest_api.is_rest()

        if not self.use_rest:
            if not netapp_utils.has_netapp_lib():
                self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)


    def fail_on_error(self, error, stack=False):
        if error is None:
            return
        elements = dict(msg="Error: %s" % error)
        if stack:
            elements['stack'] = traceback.format_stack()
        self.module.fail_json(**elements)

    def get_zapi_destination_property(self, type):
        if type == 'rest_api':
            return 'rest-api-url'
        else:
            return type

    def get_ems_destination_rest(self, name):
        api = 'support/ems/destinations'
        fields = 'name,type,destination'
        query = dict(name=name, fields=fields)
        record, error = rest_generic.get_one_record(self.rest_api, api, query)
        self.fail_on_error(error)
        if record:
            try:
                current = {
                    'name': record['name'],
                    'type': record['type'],
                    'destination': record['destination']
                }
            except KeyError as exc:
                self.module.fail_json(msg='Error: unexpected ems destination body: %s, KeyError on %s' % (str(record), str(exc)))
            
            return current
        return None
    
    def get_ems_destination(self, name):
        if self.use_rest:
            return self.get_ems_destination_rest(name)

        ems_destination_info = netapp_utils.zapi.NaElement('ems-event-notification-destination-get-iter')
        query = netapp_utils.zapi.NaElement('query')
        event_notification_destination_info = netapp_utils.zapi.NaElement('event-notification-destination-info')
        event_notification_destination_info.add_new_child('name', name)
        query.add_child_elem(event_notification_destination_info)
        ems_destination_info.add_child_elem(query)
        current = None

        try:
            result = self.server.invoke_successfully(ems_destination_info, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching ems destination info %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) >= 1:
            ems_destination = result['attributes-list']['event-notification-destination-info']
            if ems_destination.get_child_by_name('destination'):
                destination_value = self.na_helper.get_value_for_list(from_zapi=True, zapi_parent=ems_destination.get_child_by_name('destination'))[0]
            else:
                destination_value = None

            current = {
                'name': ems_destination.get_child_content('name'),
                'type': ems_destination.get_child_content('type'),
                'destination': destination_value
            }   
        return current

    def create_ems_destination_rest(self):
        api = 'support/ems/destinations'
        body = dict(
            name=self.parameters['name'],
            type=self.parameters['type'],
            destination=self.parameters['destination']
        )
        _, error = rest_generic.post_async(self.rest_api, api, body)
        self.fail_on_error(error)

    def create_ems_destination(self):
        if self.use_rest:
            return self.create_ems_destination_rest()

        options = {'name': self.parameters['name']}
        type = self.parameters['type']
        destination = self.parameters['destination']
        option = self.get_zapi_destination_property(type)
        options[option] = destination

        ems_destination_create = netapp_utils.zapi.NaElement.create_node_with_children(
            'ems-event-notification-destination-create', **options
        )
    
        try:
            self.server.invoke_successfully(ems_destination_create, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error provisioning ems destination %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())


    def delete_ems_destination_rest(self, name):
        api = 'support/ems/destinations'
        _, error = rest_generic.delete_async(self.rest_api, api, name)
        self.fail_on_error(error)
    
    def delete_ems_destination(self, name):
        if self.use_rest:
            return self.delete_ems_destination_rest(name)

        ems_destination_delete = netapp_utils.zapi.NaElement('ems-event-notification-destination-destroy-iter')
        query = netapp_utils.zapi.NaElement('query')
        event_notification_destination = netapp_utils.zapi.NaElement('event-notification-destination')
        event_notification_destination.add_new_child('name', name)
        query.add_child_elem(event_notification_destination)
        ems_destination_delete.add_child_elem(query)

        try:
            self.server.invoke_successfully(ems_destination_delete, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting ems destination %s: %s' % (name, to_native(error)),
                                  exception=traceback.format_exc())

    def modify_ems_destination_rest(self, name, modify):
        api = 'support/ems/destinations'
        body = dict()
        for option in modify:
            body[option] = modify[option]
        if body:
            _, error = rest_generic.patch_async(self.rest_api, api, name, body)
            self.fail_on_error(error)

    def modify_ems_destination(self, name, modify):
        if 'type' in modify:
            # changing type is not supported...
            if self.use_rest:
                self.delete_ems_destination_rest(name)
                self.create_ems_destination_rest()
            else:
                self.delete_ems_destination(name)
                self.create_ems_destination()
        else:
            if self.use_rest:
                return self.modify_ems_destination_rest(name, modify)

            ems_destination_modify = netapp_utils.zapi.NaElement('ems-event-notification-destination-modify-iter')
            query = netapp_utils.zapi.NaElement('query')
            event_notification_destination = netapp_utils.zapi.NaElement('event-notification-destination')
            event_notification_destination.add_new_child('name', name)
            query.add_child_elem(event_notification_destination)
            ems_destination_modify.add_child_elem(query)

            attributes = netapp_utils.zapi.NaElement('attributes')
            changed_event_notification_destination = netapp_utils.zapi.NaElement('event-notification-destination')
            for option in modify:
                if option == 'destination':
                    type = self.parameters['type']
                    zapi_option = self.get_zapi_destination_property(type)
                    destination = modify[option]
                    changed_event_notification_destination.add_new_child(zapi_option, destination)
                else:
                    changed_event_notification_destination.add_new_child(option, modify[option])
        
            attributes.add_child_elem(changed_event_notification_destination)
            ems_destination_modify.add_child_elem(attributes)

            try:
                self.server.invoke_successfully(ems_destination_modify, enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error changing ems destination %s: %s' % (name, to_native(error)),
                                    exception=traceback.format_exc())

    def autosupport_log(self):
        if not self.use_rest:
            netapp_utils.ems_log_event_cserver("na_ontap_ems_destination", self.server, self.module)

    def apply(self):
        self.autosupport_log()
        name = None
        modify = None
        current = self.get_ems_destination(self.parameters['name'])
        name = self.parameters['name']
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action is None and self.parameters['state'] == 'present':
            modify = self.na_helper.get_modified_attributes(current, self.parameters)

        saved_modify = str(modify)
        if self.na_helper.changed and not self.module.check_mode:
            if modify:
                self.modify_ems_destination(name, modify)
            elif cd_action == 'create':
                self.create_ems_destination()
            elif cd_action == 'delete':
                self.delete_ems_destination(name)
        self.module.exit_json(changed=self.na_helper.changed, current=current, modify=saved_modify)


def main():
    obj = NetAppOntapEmsDestination()
    obj.apply()


if __name__ == '__main__':
    main()
