#!/usr/bin/python

# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_rest_cli
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = '''
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - "Run system-cli commands on ONTAP"
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
module: na_ontap_rest_cli
short_description: NetApp ONTAP Run any cli command, the username provided needs to have console login permission.
version_added: 2.9.0
options:
    command:
        description:
        - a string command.
        required: true
        type: str
    verb:
        description:
        - a string indicating which api call to run
        - OPTIONS is useful to know which verbs are supported by the REST API
        choices: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS']
        required: true
        type: str
    params:
        description:
        - a dictionary of parameters to pass into the api call
        type: dict
    body:
        description:
        - a dictionary for info specification
        type: dict
'''

EXAMPLES = """
    - name: run ontap rest cli command
      na_ontap_rest_cli:
        hostname: "{{ hostname }}"
        username: "{{ admin username }}"
        password: "{{ admin password }}"
        command: 'version'
        verb: 'GET'

    - name: run ontap rest cli command
      na_ontap_rest_cli:
        hostname: "{{ hostname }}"
        username: "{{ admin username }}"
        password: "{{ admin password }}"
        command: 'security/login/motd'
        verb: 'PATCH'
        params: {'vserver': 'ansibleSVM'}
        body: {'message': 'test'}
"""

RETURN = """
"""

import traceback
from ansible.module_utils.basic import AnsibleModule
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI


class NetAppONTAPCommandREST(object):
    ''' calls a CLI command '''

    def __init__(self):
        self.use_rest = False
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            command=dict(required=True, type='str'),
            verb=dict(required=True, type='str', choices=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS']),
            params=dict(required=False, type='dict', default={}),
            body=dict(required=False, type='dict', default={})
        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.rest_api = OntapRestAPI(self.module)
        parameters = self.module.params
        # set up state variables
        self.command = parameters['command']
        self.verb = parameters['verb']
        self.params = parameters['params']
        self.body = parameters['body']

        if self.rest_api.is_rest():
            self.use_rest = True
        else:
            self.module.fail_json(msg="use na_ontap_command for non-rest cli")

    def run_command(self):
        api = "private/cli/" + self.command

        if self.verb == 'POST':
            message, error = self.rest_api.post(api, self.body, self.params)
        elif self.verb == 'GET':
            message, error = self.rest_api.get(api, self.params)
        elif self.verb == 'PATCH':
            message, error = self.rest_api.patch(api, self.body, self.params)
        elif self.verb == 'DELETE':
            message, error = self.rest_api.delete(api, self.body, self.params)
        elif self.verb == 'OPTIONS':
            message, error = self.rest_api.options(api, self.params)
        else:
            self.module.fail_json(msg='Error running command %s:' % self.command,
                                  exception=traceback.format_exc())

        if error:
            self.module.fail_json(msg=error)
        return message

    def apply(self):
        ''' calls the command and returns raw output '''
        changed = True
        output = self.run_command()
        self.module.exit_json(changed=changed, msg=output)


def main():
    """
    Execute action from playbook
    """
    command = NetAppONTAPCommandREST()
    command.apply()


if __name__ == '__main__':
    main()
