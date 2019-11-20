#!/usr/bin/python

# (c) 2017-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
module: na_ontap_cluster
short_description: NetApp ONTAP cluster - create and join.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '2.6'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Create or join to ONTAP clusters
- Cluster join can be performed using only one of the parameters, either cluster_name or cluster_ip_address
options:
  state:
    description:
    - Whether the specified cluster should exist or not.
    choices: ['present']
    default: present
  cluster_name:
    description:
    - The name of the cluster to manage.
  cluster_ip_address:
    description:
    - IP address of cluster to be joined

'''

EXAMPLES = """
    - name: Create cluster
      na_ontap_cluster:
        state: present
        cluster_name: new_cluster
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Join cluster
      na_ontap_cluster:
        state: present
        cluster_ip_address: 10.10.10.10
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Join cluster
      na_ontap_cluster:
        state: present
        cluster_name: "{{ netapp_cluster}}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
"""

RETURN = """
"""

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


def local_cmp(a, b):
    """
    compares with only values and not keys, keys should be the same for both dicts
    :param a: dict 1
    :param b: dict 2
    :return: difference of values in both dicts
    """
    diff = [key for key in a if a[key] != b[key]]
    return len(diff)


class NetAppONTAPCluster(object):
    """
    object initialize and class methods
    """
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=['present'], default='present'),
            cluster_name=dict(required=False, type='str'),
            cluster_ip_address=dict(required=False, type='str')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def create_cluster(self):
        """
        Create a cluster
        """
        cluster_create = netapp_utils.zapi.NaElement.create_node_with_children(
            'cluster-create', **{'cluster-name': self.parameters['cluster_name']})

        try:
            self.server.invoke_successfully(cluster_create,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            # Error 36503 denotes node already being used.
            if to_native(error.code) == "36503":
                return False
            else:
                self.module.fail_json(msg='Error creating cluster %s: %s'
                                      % (self.parameters['cluster_name'], to_native(error)),
                                      exception=traceback.format_exc())
        return True

    def cluster_join(self):
        """
        Add a node to an existing cluster
        """
        if self.parameters.get('cluster_ip_address') is not None:
            cluster_add_node = netapp_utils.zapi.NaElement.create_node_with_children(
                'cluster-join', **{'cluster-ip-address': self.parameters['cluster_ip_address']})
            for_fail_attribute = self.parameters.get('cluster_ip_address')
        elif self.parameters.get('cluster_name') is not None:
            cluster_add_node = netapp_utils.zapi.NaElement.create_node_with_children(
                'cluster-join', **{'cluster-name': self.parameters['cluster_name']})
            for_fail_attribute = self.parameters.get('cluster_name')
        else:
            return False
        try:
            self.server.invoke_successfully(cluster_add_node, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            # Error 36503 denotes node already being used.
            if to_native(error.code) == "36503":
                return False
            else:
                self.module.fail_json(msg='Error adding node to cluster %s: %s'
                                      % (for_fail_attribute, to_native(error)),
                                      exception=traceback.format_exc())
        return True

    def autosupport_log(self):
        """
        Autosupport log for cluster
        :return:
        """
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("na_ontap_cluster", cserver)

    def apply(self):
        """
        Apply action to cluster
        """
        create_flag = False
        join_flag = False

        if self.module.check_mode:
            pass
        else:
            if self.parameters.get('state') == 'present':
                if self.parameters.get('cluster_name') is not None:
                    create_flag = self.create_cluster()
                if not create_flag:
                    join_flag = self.cluster_join()
        self.autosupport_log()
        changed = create_flag or join_flag
        self.module.exit_json(changed=changed)


def main():
    """
    Create object and call apply
    """
    cluster_obj = NetAppONTAPCluster()
    cluster_obj.apply()


if __name__ == '__main__':
    main()
