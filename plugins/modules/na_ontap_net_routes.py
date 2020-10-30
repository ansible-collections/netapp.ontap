#!/usr/bin/python

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_net_routes
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = '''
module: na_ontap_net_routes
short_description: NetApp ONTAP network routes
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Modify ONTAP network routes.
options:
  state:
    description:
    - Whether you want to create or delete a network route.
    choices: ['present', 'absent']
    type: str
    default: present
  vserver:
    description:
    - The name of the vserver.
    required: true
    type: str
  destination:
    description:
    - Specify the route destination.
    - Example 10.7.125.5/20, fd20:13::/64.
    required: true
    type: str
  gateway:
    description:
    - Specify the route gateway.
    - Example 10.7.125.1, fd20:13::1.
    required: true
    type: str
  metric:
    description:
    - Specify the route metric.
    - If this field is not provided the default will be set to 20.
    type: int
  from_destination:
    description:
    - Specify the route destination that should be changed.
    - new_destination was removed to fix idempotency issues. To rename destination the original goes to from_destination and the new goes to destination.
    version_added: 2.8.0
    type: str
  from_gateway:
    description:
    - Specify the route gateway that should be changed.
    version_added: 2.8.0
    type: str
  from_metric:
    description:
    - Specify the route metric that should be changed.
    version_added: 2.8.0
    type: int
'''

EXAMPLES = """
    - name: create route
      na_ontap_net_routes:
        state: present
        vserver: "{{ Vserver name }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        hostname: "{{ netapp_hostname }}"
        destination: 10.7.125.5/20
        gateway: 10.7.125.1
        metric: 30
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


class NetAppOntapNetRoutes(object):
    """
    Create, Modifies and Destroys a Net Route
    """

    def __init__(self):
        """
        Initialize the Ontap Net Route class
        """
        self.use_rest = False
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            vserver=dict(required=True, type='str'),
            destination=dict(required=True, type='str'),
            gateway=dict(required=True, type='str'),
            metric=dict(required=False, type='int'),
            from_destination=dict(required=False, type='str', default=None),
            from_gateway=dict(required=False, type='str', default=None),
            from_metric=dict(required=False, type='int', default=None),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        self.rest_api = OntapRestAPI(self.module)
        # some attributes are not supported in earlier REST implementation
        unsupported_rest_properties = ['metric', 'from_metric']
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

    def create_net_route(self, current_metric=None):
        """
        Creates a new Route
        """
        if self.use_rest:
            api = "network/ip/routes"
            params = {'gateway': self.parameters['gateway'],
                      'svm': self.parameters['vserver']}
            if self.parameters.get('destination') is not None:
                dest = self.parameters['destination'].split('/')
                params['destination'] = {'address': dest[0], 'netmask': dest[1]}
            __, error = self.rest_api.post(api, params)
            if error:
                self.module.fail_json(msg=error)
        else:
            route_obj = netapp_utils.zapi.NaElement('net-routes-create')
            route_obj.add_new_child("destination", self.parameters['destination'])
            route_obj.add_new_child("gateway", self.parameters['gateway'])
            if current_metric is None and self.parameters.get('metric') is not None:
                metric = self.parameters['metric']
            else:
                metric = current_metric
            # Metric can be None, Can't set metric to none
            if metric is not None:
                route_obj.add_new_child("metric", str(metric))
            try:
                self.server.invoke_successfully(route_obj, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error creating net route: %s' % (to_native(error)),
                                      exception=traceback.format_exc())

    def delete_net_route(self, params):
        """
        Deletes a given Route
        """
        if self.use_rest:
            uuid = params['uuid']
            api = "network/ip/routes/" + uuid
            dummy, error = self.rest_api.delete(api)
            if error:
                self.module.fail_json(msg=error)
        else:
            route_obj = netapp_utils.zapi.NaElement('net-routes-destroy')
            if params is None:
                params = self.parameters
            route_obj.add_new_child("destination", params['destination'])
            route_obj.add_new_child("gateway", params['gateway'])
            try:
                self.server.invoke_successfully(route_obj, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error deleting net route: %s'
                                      % (to_native(error)),
                                      exception=traceback.format_exc())

    def modify_net_route(self, current, desired):
        """
        Modify a net route
        Since we cannot modify a route, we are deleting the existing route, and creating a new one.
        """
        if self.use_rest:
            if desired.get('destination') is not None:
                dest = desired['destination'].split('/')
                if dest[0] != current['destination']['address'] or dest[1] != current['destination']['netmask']:
                    self.na_helper.changed = True
                self.parameters['destination'] = desired['destination']
            else:
                self.parameters['destination'] = '%s/%s' % (current['destination']['address'],
                                                            current['destination']['netmask'])
            if desired.get('gateway') is not None:
                if desired['gateway'] != current['gateway']:
                    self.na_helper.changed = True
                self.parameters['gateway'] = desired['gateway']
            else:
                self.parameters['gateway'] = current['gateway']
            if not self.na_helper.changed or self.module.check_mode:
                return
            params = {'destination': '%s/%s' % (current['destination']['address'], current['destination']['netmask']),
                      'gateway': current['gateway']}
            target = self.get_net_route(params)
            self.delete_net_route(target)
            self.create_net_route()
            return

        else:
            # return if there is nothing to change
            for key, val in desired.items():
                if val != current[key]:
                    self.na_helper.changed = True
                    break
            if not self.na_helper.changed or self.module.check_mode:
                return
            # delete and re-create with new params
            self.delete_net_route(current)
            route_obj = netapp_utils.zapi.NaElement('net-routes-create')
            for attribute in ['metric', 'destination', 'gateway']:
                if desired.get(attribute) is not None:
                    value = desired[attribute]
                else:
                    value = current[attribute]
                route_obj.add_new_child(attribute, str(value))
            try:
                self.server.invoke_successfully(route_obj, True)
            except netapp_utils.zapi.NaApiError as error:
                # restore the old route, create the route with the existing metric
                self.create_net_route(current['metric'])
                # return if desired route already exists
                if to_native(error.code) == '13001':
                    return
                # Invalid value specified for any of the attributes
                self.module.fail_json(msg='Error modifying net route: %s'
                                      % (to_native(error)),
                                      exception=traceback.format_exc())

    def get_net_route(self, params=None):
        """
        Checks to see if a route exist or not
        :return: NaElement object if a route exists, None otherwise
        """
        if params is not None:
            # we need either destination or gateway to fetch desired route
            if params.get('destination') is None and params.get('gateway') is None:
                return None
        if self.use_rest:
            api = "network/ip/routes"
            data = {'fields': 'destination,gateway,svm'}
            message, error = self.rest_api.get(api, data)
            if error:
                self.module.fail_json(msg=error)
            if len(message.keys()) == 0:
                return None
            elif 'records' in message and len(message['records']) == 0:
                return None
            elif 'records' not in message:
                error = "Unexpected response in get_net_route from %s: %s" % (api, repr(message))
                self.module.fail_json(msg=error)
            if params is None:
                params = self.parameters
            else:
                if params.get('destination') is None:
                    params['destination'] = self.parameters['destination']
                if params.get('gateway') is None:
                    params['gateway'] = self.parameters['gateway']
                params['vserver'] = self.parameters['vserver']
            for record in message['records']:
                if record['gateway'] == params['gateway'] and \
                        record['destination']['address'] == params['destination'].split('/')[0] and \
                        record.get('svm') and record['svm']['name'] == params['vserver']:
                    return record
            return None
        else:
            current = None
            route_obj = netapp_utils.zapi.NaElement('net-routes-get')
            for attr in ['destination', 'gateway']:
                if params and params.get(attr) is not None:
                    value = params[attr]
                else:
                    value = self.parameters[attr]
                route_obj.add_new_child(attr, value)
            try:
                result = self.server.invoke_successfully(route_obj, True)
                if result.get_child_by_name('attributes') is not None:
                    route_info = result.get_child_by_name('attributes').get_child_by_name('net-vs-routes-info')
                    current = {
                        'destination': route_info.get_child_content('destination'),
                        'gateway': route_info.get_child_content('gateway'),
                        'metric': int(route_info.get_child_content('metric'))
                    }

            except netapp_utils.zapi.NaApiError as error:
                # Error 13040 denotes a route doesn't exist.
                if to_native(error.code) == "15661":
                    return None
                self.module.fail_json(msg='Error fetching net route: %s'
                                      % (to_native(error)),
                                      exception=traceback.format_exc())
            return current

    @staticmethod
    def is_modify_action(current, desired):
        """
        Get desired action to be applied for net routes
        Destination and gateway are unique params for a route and cannot be duplicated
        So if a route with desired destination or gateway exists already, we don't try to modify
        :param current: current details
        :param desired: desired details
        :return: create / delete / modify / None
        """
        if current is None and desired is None:
            # this is invalid
            # cannot modify a non existent resource
            return None
        if current is None and desired is not None:
            # idempotency or duplication
            # we need not create
            return False
        if current is not None and desired is not None:
            # we can't modify an ambiguous route (idempotency/duplication)
            return False
        return True

    def get_params_to_be_modified(self, current):
        """
        Get parameters and values that need to be modified
        :param current: current details
        :return: dict(), None
        """
        if current is None:
            return None
        desired = dict()
        if self.parameters.get('new_destination') is not None and \
                self.parameters['new_destination'] != current['destination']:
            desired['destination'] = self.parameters['new_destination']
        if self.parameters.get('new_gateway') is not None and \
                self.parameters['new_gateway'] != current['gateway']:
            desired['gateway'] = self.parameters['new_gateway']
        if self.parameters.get('new_metric') is not None and \
                self.parameters['new_metric'] != current['metric']:
            desired['metric'] = self.parameters['new_metric']
        return desired

    def apply(self):
        """
        Run Module based on play book
        """
        if not self.use_rest:
            netapp_utils.ems_log_event("na_ontap_net_routes", self.server)
        current = self.get_net_route()
        modify, cd_action = None, None
        if self.use_rest:
            modify_params = {'gateway': self.parameters.get('from_gateway'),
                             'destination': self.parameters.get('from_destination')}
            if any(modify_params.values()):
                # destination and gateway combination is unique, and is considered like a id. so modify destination
                # or gateway is considered a rename action.
                old_params = self.get_net_route(modify_params)
                modify = self.na_helper.is_rename_action(old_params, current)
                if modify is None:
                    self.module.fail_json(msg="Error modifying: route %s does not exist" % self.parameters['from_destination'])
            else:
                cd_action = self.na_helper.get_cd_action(current, self.parameters)
        else:
            modify_params = {'destination': self.parameters.get('from_destination'),
                             'gateway': self.parameters.get('from_gateway'),
                             'metric': self.parameters.get('from_metric')}
            # if any from_* param is present in playbook, check for modify action
            if any(modify_params.values()):
                # destination and gateway combination is unique, and is considered like a id. so modify destination
                # or gateway is considered a rename action. metric is considered an attribute of the route so it is
                # considered as modify.
                if modify_params.get('metric') is not None:
                    modify = True
                    old_params = current
                else:
                    # get parameters that are eligible for modify
                    old_params = self.get_net_route(modify_params)
                    modify = self.na_helper.is_rename_action(old_params, current)
                if modify is None:
                    self.module.fail_json(msg="Error modifying: route %s does not exist" % self.parameters['from_destination'])
            else:
                cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action == 'create':
            if not self.module.check_mode:
                self.create_net_route()
        elif cd_action == 'delete':
            if not self.module.check_mode:
                self.delete_net_route(current)
        elif modify:
            desired = {}
            for key, value in old_params.items():
                desired[key] = value
            for key, value in modify_params.items():
                if value is not None:
                    desired[key] = self.parameters.get(key)
            self.modify_net_route(old_params, desired)
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """
    Creates the NetApp Ontap Net Route object and runs the correct play task
    """
    obj = NetAppOntapNetRoutes()
    obj.apply()


if __name__ == '__main__':
    main()
