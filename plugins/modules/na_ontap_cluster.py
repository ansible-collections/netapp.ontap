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
    type: str
    default: present
  cluster_name:
    description:
    - The name of the cluster to manage.
    type: str
  cluster_ip_address:
    description:
    - IP address of cluster to be joined
    type: str
  single_node_cluster:
    description:
    - Whether the cluster is a single node cluster.  Ignored for 9.3 or older versions.
    default: False
    version_added: '19.11.0'
    type: bool
  cluster_location:
    description:
    - Cluster location, only relevant if performing a modify action.
    version_added: '19.11.0'
    type: str
  cluster_contact:
    description:
    - Cluster contact, only relevant if performing a modify action.
    version_added: '19.11.0'
    type: str
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
    - name: modify cluster again
      na_ontap_cluster:
        state: present
        cluster_contact: testing
        cluster_location: testing
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
import time

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
            state=dict(required=False, type='str', choices=['present'], default='present'),
            cluster_name=dict(required=False, type='str'),
            cluster_ip_address=dict(required=False, type='str'),
            cluster_location=dict(required=False, type='str'),
            cluster_contact=dict(required=False, type='str'),
            single_node_cluster=dict(required=False, type='bool', default=False)
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

    def get_cluster_identity(self, ignore_error=True):
        ''' get cluster information, but the cluster may not exist yet
            return:
                None if the cluster cannot be reached
                a dictionary of attributes
        '''
        zapi = netapp_utils.zapi.NaElement('cluster-identity-get')
        try:
            result = self.server.invoke_successfully(zapi, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            if ignore_error:
                return None
            self.module.fail_json(msg='Error fetching cluster identity info: %s' % to_native(error),
                                  exception=traceback.format_exc())
        cluster_identity = dict()
        if result.get_child_by_name('attributes'):
            identity_info = result.get_child_by_name('attributes').get_child_by_name('cluster-identity-info')
            if identity_info:
                cluster_identity['cluster_contact'] = identity_info.get_child_content('cluster-contact')
                cluster_identity['cluster_location'] = identity_info.get_child_content('cluster-location')
                cluster_identity['cluster_name'] = identity_info.get_child_content('cluster-name')
            return cluster_identity
        return None

    def create_cluster(self):
        """
        Create a cluster
        """
        dummy, minor = self.server.get_api_version()
        options = {'cluster-name': self.parameters['cluster_name']}
        if minor >= 140:
            options['single-node-cluster'] = str(self.parameters.get('single_node_cluster'))
        cluster_create = netapp_utils.zapi.NaElement.create_node_with_children(
            'cluster-create', **options)
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
            cluster_add_node = netapp_utils.zapi.NaElement('cluster-add-node')
            cluster_ips = netapp_utils.zapi.NaElement('cluster-ips')
            cluster_ips.add_new_child('ip-address', self.parameters.get('cluster_ip_address'))
            cluster_add_node.add_child_elem(cluster_ips)
        else:
            return False
        try:
            self.server.invoke_successfully(cluster_add_node, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            # skip if error says no failed operations to retry.
            if to_native(error) == "NetApp API failed. Reason - 13001:There are no failed \"cluster create\" or \"cluster add-node\" operations to retry.":
                return False
            else:
                self.module.fail_json(msg='Error adding node with ip %s: %s'
                                      % (self.parameters.get('cluster_ip_address'), to_native(error)),
                                      exception=traceback.format_exc())
        return True

    def modify_cluster_identity(self, modify):
        """
        Modifies the cluster identity
        """
        cluster_modify = netapp_utils.zapi.NaElement('cluster-identity-modify')
        if modify.get('cluster_name') is not None:
            cluster_modify.add_new_child("cluster-name", modify.get('cluster_name'))
        if modify.get('cluster_location') is not None:
            cluster_modify.add_new_child("cluster-location", modify.get('cluster_location'))
        if modify.get('cluster_contact') is not None:
            cluster_modify.add_new_child("cluster-contact", modify.get('cluster_contact'))

        try:
            self.server.invoke_successfully(cluster_modify,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying cluster idetity details %s: %s'
                                      % (self.parameters['cluster_name'], to_native(error)),
                                  exception=traceback.format_exc())
        return True

    def cluster_create_wait(self):
        """
        Wait whilst cluster creation completes
        """

        cluster_wait = netapp_utils.zapi.NaElement('cluster-create-join-progress-get')
        is_complete = False
        status = ''
        wait = False    # do not wait on the first call

        while not is_complete and status not in ('failed', 'success'):
            if wait:
                time.sleep(10)
            else:
                wait = True
            try:
                result = self.server.invoke_successfully(cluster_wait, enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:

                self.module.fail_json(msg='Error creating cluster %s: %s'
                                          % (self.parameters.get('cluster_name'), to_native(error)),
                                      exception=traceback.format_exc())

            clus_progress = result.get_child_by_name('attributes')
            result = clus_progress.get_child_by_name('cluster-create-join-progress-info')
            is_complete = self.na_helper.get_value_for_bool(from_zapi=True,
                                                            value=result.get_child_content('is-complete'))
            status = result.get_child_content('status')

        if not is_complete and status != 'success':
            current_status_message = result.get_child_content('current-status-message')

            self.module.fail_json(
                msg='Failed to create cluster %s: %s' % (self.parameters.get('cluster_name'), current_status_message))

        return is_complete

    def node_add_wait(self):
        """
        Wait whilst node is being added to the existing cluster
        """
        cluster_node_status = netapp_utils.zapi.NaElement('cluster-add-node-status-get-iter')
        node_status_info = netapp_utils.zapi.NaElement('cluster-create-add-node-status-info')
        node_status_info.add_new_child('cluster-ip', self.parameters.get('cluster_ip_address'))
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(node_status_info)
        cluster_node_status.add_child_elem(query)
        result = self.server.invoke_successfully(cluster_node_status, True)

        is_complete = None
        failure_msg = None
        wait = False    # do not wait on the first call

        while is_complete != 'success' and is_complete != 'failure':
            if wait:
                time.sleep(10)
            else:
                wait = True
            try:
                result = self.server.invoke_successfully(cluster_node_status, enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:

                self.module.fail_json(msg='Error adding node with ip address %s: %s'
                                          % (self.parameters.get('cluster_ip_address'), to_native(error)),
                                      exception=traceback.format_exc())

            attributes_list = result.get_child_by_name('attributes-list')
            join_progress = attributes_list.get_child_by_name('cluster-create-add-node-status-info')
            is_complete = join_progress.get_child_content('status')
            failure_msg = join_progress.get_child_content('failure-msg')

        if is_complete != 'success':
            if 'Node is already in a cluster' in failure_msg:
                return is_complete
            else:
                self.module.fail_json(
                    msg='Error adding node with ip address %s' % (self.parameters.get('cluster_ip_address')))
        return is_complete

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
        changed = False
        create_flag = False
        cluster_identity = self.get_cluster_identity(ignore_error=True)
        modify = self.na_helper.get_modified_attributes(cluster_identity, self.parameters)
        # temporary hack to fix check_mode for modify
        changed = self.na_helper.changed
        # TODO: JIRA-3048 fix check_mode for create and join

        if not self.module.check_mode:
            if self.parameters.get('state') == 'present':
                if self.parameters.get('cluster_name') is not None:
                    create_flag = self.create_cluster()
                    if create_flag:
                        cluster_wait = self.cluster_create_wait()
                        changed = True if cluster_wait else changed
                if not create_flag:
                    join_flag = self.cluster_join()
                    if join_flag:
                        join_wait_flag = self.node_add_wait()
                        changed = True if join_wait_flag == 'success' else changed
                if modify:
                    self.modify_cluster_identity(modify)
        self.autosupport_log()
        self.module.exit_json(changed=changed)


def main():
    """
    Create object and call apply
    """
    cluster_obj = NetAppONTAPCluster()
    cluster_obj.apply()


if __name__ == '__main__':
    main()
