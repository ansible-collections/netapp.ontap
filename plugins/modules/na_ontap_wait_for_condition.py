#!/usr/bin/python
'''
# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = '''
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - Loop over an ONTAP get status request until a condition is satisfied.
  - Report a timeout error if C(timeout) is exceeded while waiting for the condition.
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
module: na_ontap_wait_for_condition
short_description: NetApp ONTAP wait_for_condition.  Loop over a get status request until a condition is met.
version_added: 20.8.0
options:
    name:
        description:
          - The name of the event to check for.
        choices: ['sp_upgrade', 'sp_version']
        type: str
        required: true
    state:
        description:
          - whether the conditions should be present or absent.
          - if C(present), the module exits when any of the conditions is observed.
          - if C(absent), the module exits with success when None of the conditions is observed.
        choices: ['present', 'absent']
        default: present
        type: str
    conditions:
        description:
          - one or more conditions to match
          - for instance C(is_in_progress) for C(sp_upgrade), C(firmware_version) for C(sp_version).
        type: list
        elements: str
        required: true
    polling_interval:
        description:
          - how ofen to check for the conditions, in seconds.
        default: 5
        type: int
    timeout:
        description:
          - how long to wait for the conditions, in seconds.
        default: 180
        type: int
    attributes:
        description:
          - a dictionary of custom attributes for the event.
          - for instance, C(sp_upgrade), C(sp_version) require C(node).
          - C(sp_version) requires C(expectd_version).
        type: dict
'''

EXAMPLES = """
    - name: wait for sp_upgrade in progress
      na_ontap_wait_for_condition:
        hostname: "{{ ontap_admin_ip }}"
        username: "{{ ontap_admin_username }}"
        password: "{{ ontap_admin_password }}"
        https: true
        validate_certs: no
        name: sp_upgrade
        conditions: is_in_progress
        attributes:
          node: "{{ node }}"
        polling_interval: 30
        timeout: 1800

    - name: wait for sp_upgrade not in progress
      na_ontap_wait_for_condition:
        hostname: "{{ ontap_admin_ip }}"
        username: "{{ ontap_admin_username }}"
        password: "{{ ontap_admin_password }}"
        https: true
        validate_certs: no
        name: sp_upgrade
        conditions: is_in_progress
        state: absent
        attributes:
          node: "{{ ontap_admin_ip }}"
        polling_interval: 30
        timeout: 1800

    - name: wait for sp_version to match 3.9
      na_ontap_wait_for_condition:
        hostname: "{{ ontap_admin_ip }}"
        username: "{{ ontap_admin_username }}"
        password: "{{ ontap_admin_password }}"
        https: true
        validate_certs: no
        name: sp_version
        conditions: firmware_version
        state: present
        attributes:
          node: "{{ ontap_admin_ip }}"
          expected_version: 3.9
        polling_interval: 30
        timeout: 1800
"""

RETURN = """
states:
  description:
    - summarized list of observed states while waiting for completion
    - reported for success or timeout error
  returned: always
  type: str
last_state:
  description: last observed state for event
  returned: always
  type: str
"""

import time
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppONTAPWFC(object):
    ''' wait for a resource to match a condition or not '''

    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str', choices=['sp_upgrade', 'sp_version']),
            conditions=dict(required=True, type='list', elements='str'),
            polling_interval=dict(required=False, type='int', default=5),
            timeout=dict(required=False, type='int', default=180),
            attributes=dict(required=False, type='dict')
        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            required_if=[
                ('name', 'sp_upgrade', ['attributes']),
                ('name', 'sp_version', ['attributes']),
            ],
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.states = list()

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, wrap_zapi=True)

        self.resource_configuration = dict(
            sp_upgrade=dict(
                required_attributes=['node'],
                conditions=dict(
                    is_in_progress=('is-in-progress', "true")
                )
            ),
            sp_version=dict(
                required_attributes=['node', 'expected_version'],
                conditions=dict(
                    firmware_version=('firmware-version', self.parameters['attributes'].get('expected_version'))
                )
            )
        )

    def asup_log_for_cserver(self, event_name):
        """
        Fetch admin vserver for the given cluster
        Create and Autosupport log event with the given module name
        :param event_name: Name of the event log
        :return: None
        """
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        try:
            netapp_utils.ems_log_event(event_name, cserver)
        except netapp_utils.zapi.NaApiError:
            pass

    def get_key_value(self, xml, key):
        for child in xml.get_children():
            value = xml.get_child_content(key)
            if value is not None:
                return value
            value = self.get_key_value(child, key)
            if value is not None:
                return value
        return None

    def build_zapi(self, name):
        ''' build ZAPI request based on resource  name '''
        if name == 'sp_upgrade':
            zapi_obj = netapp_utils.zapi.NaElement("service-processor-image-update-progress-get")
            zapi_obj.add_new_child('node', self.parameters['attributes']['node'])
            return zapi_obj
        if name == 'sp_version':
            zapi_obj = netapp_utils.zapi.NaElement("service-processor-get")
            zapi_obj.add_new_child('node', self.parameters['attributes']['node'])
            return zapi_obj
        raise KeyError(name)

    def extract_condition(self, name, results):
        ''' check if any of the conditions is present
            return:
                None, error if key is not found
                condition, None if a key is found with expected value
                None, None if every key does not match the expected values
        '''
        error = None
        for condition, (key, value) in self.resource_configuration[name]['conditions'].items():
            status = self.get_key_value(results, key)
            self.states.append(str(status))
            if status == str(value):
                return condition, error
            if status is None:
                error = 'Cannot find element with name: %s in results: %s' % (key, results.to_string())
                return None, error
        # not found, or no match
        return None, None

    def get_condition(self, name, zapi_obj):
        ''' calls the ZAPI and extract condition value'''
        try:
            results = self.server.invoke_successfully(zapi_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            error = 'Error running command %s: %s' % (self.parameters['name'], to_native(error))
            return None, error

        condition, error = self.extract_condition(name, results)
        if error is not None:
            self.module.fail_json(msg='Error: %s' % error)
        if self.parameters['state'] == 'present':
            if condition in self.parameters['conditions']:
                return 'matched condition: %s' % condition, None
        else:
            if condition is None:
                return 'conditions not matched', None
            if condition not in self.parameters['conditions']:
                return 'conditions not matched: found other condition: %s' % condition, None
        return None, None

    def summarize_states(self):
        ''' replaces a long list of states with multipliers
            eg 'false'*5
            return:
                state_list as str
                last_state
        '''
        previous_state = None
        count = 0
        summary = ''
        for state in self.states:
            if state == previous_state:
                count += 1
            else:
                if previous_state is not None:
                    summary += '%s%s' % (previous_state, '' if count == 1 else '*%d' % count)
                count = 1
                previous_state = state
        if previous_state is not None:
            summary += '%s%s' % (previous_state, '' if count == 1 else '*%d' % count)
        last_state = self.states[-1] if self.states else ''
        return summary, last_state

    def wait_for_condition(self, name):
        ''' calls the ZAPI and extract condition value - loop until found '''
        time_left = self.parameters['timeout']
        max_consecutive_error_count = 3
        error_count = 0
        zapi_obj = self.build_zapi(name)

        while time_left > 0:
            condition, error = self.get_condition(name, zapi_obj)
            if error is not None:
                error_count += 1
                if error_count >= max_consecutive_error_count:
                    self.module.fail_json(msg='Error: %s - count: %d' % (error, error_count))
            elif condition is not None:
                return condition
            time.sleep(self.parameters['polling_interval'])
            time_left -= self.parameters['polling_interval']

        error = 'Error: timeout waiting for condition%s: %s.' %\
                ('s' if len(self.parameters['conditions']) > 1 else '',
                 ', '.join(self.parameters['conditions']))
        states, last_state = self.summarize_states()
        self.module.fail_json(msg=error, states=states, last_state=last_state)

    def validate_resource(self, name):
        if name not in self.resource_configuration:
            raise KeyError('%s - configuration entry missing for resource' % name)

    def validate_attributes(self, name):
        required = self.resource_configuration[name].get('required_attributes', list())
        msgs = list()
        for attribute in required:
            if attribute not in self.parameters['attributes']:
                msgs.append('attributes: %s is required for resource name: %s' % (attribute, name))
        if msgs:
            self.module.fail_json(msg='Error: %s' % ', '.join(msgs))

    def validate_conditions(self, name):
        conditions = self.resource_configuration[name].get('conditions')
        msgs = list()
        for condition in self.parameters['conditions']:
            if condition not in conditions:
                msgs.append('condition: %s is not valid for resource name: %s' % (condition, name))
        if msgs:
            msgs.append('valid condition%s: %s' %
                        ('s are' if len(conditions) > 1 else ' is', ', '.join(conditions.keys())))
            self.module.fail_json(msg='Error: %s' % ', '.join(msgs))

    def apply(self):
        ''' calls the ZAPI and check conditions '''
        changed = False
        self.asup_log_for_cserver("na_ontap_wait_for_condition: %s " % self.parameters['name'])
        name = self.parameters['name']
        self.validate_resource(name)
        self.validate_attributes(name)
        self.validate_conditions(name)
        output = self.wait_for_condition(name)
        states, last_state = self.summarize_states()
        self.module.exit_json(changed=changed, msg=output, states=states, last_state=last_state)


def main():
    """
    Execute action from playbook
    """
    command = NetAppONTAPWFC()
    command.apply()


if __name__ == '__main__':
    main()
