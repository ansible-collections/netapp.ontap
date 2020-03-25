#!/usr/bin/python

# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'certified'
}

DOCUMENTATION = '''

module: na_ontap_autosupport_invoke
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
short_description: NetApp ONTAP send AutoSupport message
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '20.4.0'
description:
    - Send an AutoSupport message from a node

options:
  name:
    description:
    - The name of the node to send the message to.
    - Not specifying this option invokes AutoSupport on all nodes in the cluster.
    type: str

  message:
    description:
    - Text sent in the subject line of the AutoSupport message.
    type: str

  type:
    description:
    - Type of AutoSupport Collection to Issue.
    choices: ['test', 'performance', 'all']
    default: 'all'
    type: str

  uri:
    description:
    - send the AutoSupport message to the destination you specify instead of the configured destination.
    type: str

'''

EXAMPLES = '''
    - name: Send message
      na_ontap_autosupport_invoke:
        name: node1
        message: invoked test autosupport rest
        uri: http://1.2.3.4/delivery_uri
        type: test
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
'''

RETURN = '''
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils


class NetAppONTAPasupInvoke(object):

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            name=dict(required=False, type='str'),
            message=dict(required=False, type='str'),
            type=dict(required=False, choices=[
                'test', 'performance', 'all'], default='all'),
            uri=dict(required=False, type='str')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        # REST API should be used for ONTAP 9.6 or higher.
        self.restApi = OntapRestAPI(self.module)
        if self.restApi.is_rest():
            self.use_rest = True
        else:
            self.module.fail_json(msg="This module only supports REST API.")

    def send_message(self):
        params = dict()
        if self.parameters.get('name'):
            params['node.name'] = self.parameters['name']
        if self.parameters.get('message'):
            params['message'] = self.parameters['message']
        if self.parameters.get('type'):
            params['type'] = self.parameters['type']
        if self.parameters.get('uri'):
            params['uri'] = self.parameters['uri']
        api = 'support/autosupport/messages'
        message, error = self.restApi.post(api, params)
        if error is not None:
            self.module.fail_json(msg="Error on sending autosupport message: %s." % error)

    def apply(self):
        if self.module.check_mode:
            pass
        else:
            self.send_message()
        self.module.exit_json(changed=True)


def main():
    alias = NetAppONTAPasupInvoke()
    alias.apply()


if __name__ == '__main__':
    main()
