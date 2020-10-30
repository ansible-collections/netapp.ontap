#!/usr/bin/python
"""
create SNMP module to add/delete/modify SNMP user
"""

# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
module: na_ontap_snmp_traphosts
short_description: NetApp ONTAP SNMP traphosts.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '20.3.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Whether the specified SNMP traphost should exist or not. Requires REST with 9.7 or higher
options:
  ip_address:
    description:
      - "The IP address of the SNMP traphost to manage."
    required: true
    type: str
  state:
    choices: ['present', 'absent']
    description:
      - "Whether the specified SNMP traphost should exist or not."
    default: 'present'
    type: str
'''

EXAMPLES = """
    - name: Create SNMP traphost
      na_ontap_snmp:
        state: present
        ip_address: '10.10.10.10'
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
    - name: Delete SNMP traphost
      na_ontap_snmp:
        state: absent
        ip_address: '10.10.10.10'
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
"""

RETURN = """
"""
from ansible.module_utils.basic import AnsibleModule
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI


class NetAppONTAPSnmpTraphosts(object):
    """Class with SNMP methods"""

    def __init__(self):
        self.use_rest = False
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            ip_address=dict(required=True, type='str'),
        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.rest_api = OntapRestAPI(self.module)
        if not self.rest_api.is_rest():
            self.module.fail_json(msg="na_ontap_snmp_traphosts only support Rest and ONTAP 9.6+")

    def get_snmp_traphosts(self):
        params = {'ip_address': self.parameters['ip_address']}
        api = 'support/snmp/traphosts'
        message, error = self.rest_api.get(api, params)
        if error:
            self.module.fail_json(msg=error)
        if not message['records']:
            return None
        return message['records']

    def create_snmp_traphost(self):
        api = '/support/snmp/traphosts'
        params = {'host': self.parameters['ip_address']}
        dummy, error = self.rest_api.post(api, params)
        if error:
            self.module.fail_json(msg=error)

    def delete_snmp_traphost(self):
        api = '/support/snmp/traphosts/' + self.parameters['ip_address']
        dummy, error = self.rest_api.delete(api)
        if error is not None:
            self.module.fail_json(msg="Error deleting traphost: %s" % error)

    def apply(self):
        """
        Apply action to SNMP traphost
        """
        current = self.get_snmp_traphosts()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if cd_action == 'create':
                    self.create_snmp_traphost()
                elif cd_action == 'delete':
                    self.delete_snmp_traphost()

        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """Execute action"""
    community_obj = NetAppONTAPSnmpTraphosts()
    community_obj.apply()


if __name__ == '__main__':
    main()
