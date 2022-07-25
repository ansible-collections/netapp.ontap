"""
create Network Interface Service Policy module to add/delete/modify service policies
"""

# (c) 2018-2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
module: na_ontap_show_network_service_policy
short_description: NetApp ONTAP Get a Network Service Policy
version_added: 2.9.0
author: OVH Cloud <gheorghe.luca.ext@ovhcloud.com>
description:
  - Get secure network  service policy 
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
options:
  policy:
    description:
      - A policy name for the service policy
    type: str
  vserver:
    description:
      - The vserver name
    type: str
  service:
    description:
      - the service name 
    type: str
'''

EXAMPLES = """
    - name: Get Network Service Policy using policy field
      na_ontap_show_network_service_policy:
        policy: "secure_mgmt"
        hostname: "{{ netapp hostname }}"
        username: "{{ netapp username }}"
        password: "{{ netapp password }}"

    - name: Get Network Service Policy using service filed
      na_ontap_show_network_service_policy:
        service: "management-https"
        hostname: "{{ netapp hostname }}"
        username: "{{ netapp username }}"
        password: "{{ netapp password }}"
        

"""
RETURN = """

ok: [localhost] => {
    "msg": {
        "changed": false,
        "failed": false,
        "msg": {
            "num_records": 1,
            "records": [
                {
                    "policy": "default-cluster",
                    "service_allowed_addresses": [
                        "cluster-core: 0.0.0.0/0"
                    ],
                    "vserver": "Cluster"
                }
            ]
        }
    }
}


"""
import json
import traceback
from ansible.module_utils.basic import AnsibleModule
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
import ansible_collections.netapp.ontap.plugins.module_utils.rest_response_helpers as rrh

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()

import urllib3
urllib3.disable_warnings()
class NetAppONTAPNetworkServicePolicy(object):
    '''Class with Network Interface Serice Policies capabilities'''

    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            policy=dict(required=False, type='str'),
            service=dict(required=False, type='str'),
            vserver=dict(required=False, type="str"),
            fields=dict(required=False,type='list', elements="str")
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        # set up state variables
        self.parameters = self.na_helper.set_parameters(self.module.params)

        # Set up Rest API
        self.rest_api = OntapRestAPI(self.module)
        self.use_rest = self.rest_api.is_rest()
        self.api = 'private/cli/network/interface/service-policy'

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        elif not self.use_rest:
            self.module.fail_json(msg="Always use REST, this module support only ontap REST API")

    def get_service_policy(self):
        """
        Get a Network Service Policy
        :return: returns a network service policy object, or returns False if there is none
        """
        attr = self.network_service_policy_attributes()
        message, error = self.rest_api.get(
            self.api,attr
        )
        if len(message['records'])<1:
            self.module.fail_json(msg="Error, pease check your params")
        else:
            return message
        return None

    def obj(self, result):
        s = []
        res = result['records'][0]
        for element in res['service_allowed_addresses']:
            e = element.split(": ")
            r = {
                'policy': res['policy'],
                'vserver': res['vserver'],
                'allow_list' : e[1],
                'service': e[0]
            }
            s.append(r)
        return s

    def network_service_policy_attributes(self):
        """
        return attribute used to get service policy
        """
        attributes = {'fields': 'service-allowed-addresses'}
        if self.parameters.get('policy'):
          attributes['policy'] = self.parameters['policy']
        if self.parameters.get('vserver'):
          attributes['policy'] = self.parameters['vserver']
        if self.parameters.get('service'):
            attributes['service'] = self.parameters['service']
        return attributes

    def apply(self):
        """
        Apply action to Network Interface Service Policy
        """
        current = self.get_service_policy()
        if current is None:
            current = "No result"
        else:
            current = self.obj(current)
        self.module.exit_json(changed=False, msg=current)



def main():
    """
    Execute action from playbook
    :return: nothing
    """
    cfg_obj = NetAppONTAPNetworkServicePolicy()
    cfg_obj.apply()


if __name__ == '__main__':
    main()
