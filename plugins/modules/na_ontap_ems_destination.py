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

  filters:
    description:
    - List of filters that destination is linked to
    required: true
    type: list
    elements: str

'''

EXAMPLES = """
    - name: Configure REST EMS destination
      na_ontap_ems_destination:
        state: present
        name: rest
        type: rest_api
        filters: ['important_events']
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


class NetAppOntapEmsDestination:
    """Create/ Modify/ Remove EMS destinations"""
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
                state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
                name=dict(required=True, type='str'),
                type=dict(required=True, type='str', choices=['email', 'syslog', 'rest_api']),
                destination=dict(required=True, type='str'),
                filters=dict(required=True, type='list', elements='str')
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
            self.module.fail_json(msg='na_ontap_ems_destination is only supported with REST API')

    def fail_on_error(self, error, stack=False):
        if error is None:
            return
        elements = dict(msg="Error: %s" % error)
        if stack:
            elements['stack'] = traceback.format_stack()
        self.module.fail_json(**elements)

    def generate_filters_list(self, filters):
        filters_list = []
        for filter in filters:
            filters_list.append({'name': filter})

        return filters_list

    def get_ems_destination(self, name):
        api = 'support/ems/destinations'
        fields = 'name,type,destination,filters.name'
        query = dict(name=name, fields=fields)
        record, error = rest_generic.get_one_record(self.rest_api, api, query)
        self.fail_on_error(error)
        if record:
            try:
                current = {
                    'name': record['name'],
                    'type': record['type'],
                    'destination': record['destination'],
                    'filters': [filter['name'] for filter in record['filters']]
                }
            except KeyError as exc:
                self.module.fail_json(msg='Error: unexpected ems destination body: %s, KeyError on %s' % (str(record), str(exc)))
            self.module.fail_json(msg=str(current))
            return current
        return None
    
    def create_ems_destination(self):
        api = 'support/ems/destinations'
        body = {
            'name': self.parameters['name'],
            'type': self.parameters['type'],
            'destination': self.parameters['destination'],
            'filters': self.generate_filters_list(self.parameters['filters'])
        }
        _, error = rest_generic.post_async(self.rest_api, api, body)
        self.fail_on_error(error)

    def delete_ems_destination(self, name):
        api = 'support/ems/destinations'
        _, error = rest_generic.delete_async(self.rest_api, api, name)
        self.fail_on_error(error)
    
    def modify_ems_destination(self, name, modify):
        if 'type' in modify:
            # changing type is not supported
            self.delete_ems_destination(name)
            self.create_ems_destination()
        else:
            api = 'support/ems/destinations'
            body = dict()
            for option in modify:
                if option == 'filters':
                    body[option] = self.generate_filters_list(modify[option])
                else:
                    body[option] = modify[option]
            if body:
                _, error = rest_generic.patch_async(self.rest_api, api, name, body)
                self.fail_on_error(error)

    def apply(self):
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
