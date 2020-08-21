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
short_description: NetApp ONTAP cluster - create a cluster and add/remove nodes.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Create ONTAP cluster.
- Add or remove cluster nodes using cluster_ip_address.
- Adding a node requires ONTAP 9.3 or better.
- Removing a node requires ONTAP 9.4 or better.
options:
  state:
    description:
    - Whether the specified cluster should exist (deleting a cluster is not supported).
    - Whether the node identified by its cluster_ip_address should be in the cluster or not.
    choices: ['present', 'absent']
    type: str
    default: present
  cluster_name:
    description:
    - The name of the cluster to manage.
    type: str
  cluster_ip_address:
    description:
    - intra cluster IP address of the node to be added or removed.
    type: str
  single_node_cluster:
    description:
    - Whether the cluster is a single node cluster.  Ignored for 9.3 or older versions.
    default: False
    version_added: 19.11.0
    type: bool
  cluster_location:
    description:
    - Cluster location, only relevant if performing a modify action.
    version_added: 19.11.0
    type: str
  cluster_contact:
    description:
    - Cluster contact, only relevant if performing a modify action.
    version_added: 19.11.0
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
    - name: Add node to cluster (Join cluster)
      na_ontap_cluster:
        state: present
        cluster_ip_address: 10.10.10.10
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Create a 2 node cluster in one call
      na_ontap_cluster:
        state: present
        cluster_name: new_cluster
        cluster_ip_address: 10.10.10.10
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Remove node from cluster
      na_ontap_cluster:
        state: absent
        cluster_ip_address: 10.10.10.10
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: modify cluster
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

import time
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppONTAPCluster(object):
    """
    object initialize and class methods
    """
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
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

    def get_cluster_ip_addresses(self, cluster_ip_address, ignore_error=True):
        ''' get list of IP addresses for this cluster
            return:
                a list of dictionaries
        '''
        if_infos = list()
        zapi = netapp_utils.zapi.NaElement('net-interface-get-iter')
        if cluster_ip_address is not None:
            query = netapp_utils.zapi.NaElement('query')
            net_info = netapp_utils.zapi.NaElement('net-interface-info')
            net_info.add_new_child('address', cluster_ip_address)
            query.add_child_elem(net_info)
            zapi.add_child_elem(query)

        try:
            result = self.server.invoke_successfully(zapi, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            if ignore_error:
                return if_infos
            self.module.fail_json(msg='Error getting IP addresses: %s' % to_native(error),
                                  exception=traceback.format_exc())

        if result.get_child_by_name('attributes-list'):
            for net_info in result.get_child_by_name('attributes-list').get_children():
                if net_info:
                    if_info = dict()
                    if_info['address'] = net_info.get_child_content('address')
                    if_info['home_node'] = net_info.get_child_content('home-node')
                if_infos.append(if_info)
        return if_infos

    def get_cluster_ip_address(self, cluster_ip_address, ignore_error=True):
        ''' get node information if it is discoverable
            return:
                None if the cluster cannot be reached
                a dictionary of attributes
        '''
        if cluster_ip_address is None:
            return None
        nodes = self.get_cluster_ip_addresses(cluster_ip_address, ignore_error=ignore_error)
        return nodes if len(nodes) > 0 else None

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
            self.module.fail_json(msg='Error creating cluster %s: %s'
                                  % (self.parameters['cluster_name'], to_native(error)),
                                  exception=traceback.format_exc())
        return True

    def add_node(self, older_api=False):
        """
        Add a node to an existing cluster
        9.2 and 9.3 do not support cluster-ips so fallback to node-ip
        """
        if self.parameters.get('cluster_ip_address') is not None:
            cluster_add_node = netapp_utils.zapi.NaElement('cluster-add-node')
            if older_api:
                cluster_add_node.add_new_child('node-ip', self.parameters.get('cluster_ip_address'))
            else:
                cluster_ips = netapp_utils.zapi.NaElement('cluster-ips')
                cluster_ips.add_new_child('ip-address', self.parameters.get('cluster_ip_address'))
                cluster_add_node.add_child_elem(cluster_ips)
        else:
            return False
        try:
            self.server.invoke_successfully(cluster_add_node, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            if error.message == "Extra input: cluster-ips":
                return self.add_node(older_api=True)
            # skip if error says no failed operations to retry.
            if to_native(error) == "NetApp API failed. Reason - 13001:There are no failed \"cluster create\" or \"cluster add-node\" operations to retry.":
                return False
            self.module.fail_json(msg='Error adding node with ip %s: %s'
                                  % (self.parameters.get('cluster_ip_address'), to_native(error)),
                                  exception=traceback.format_exc())
        return True

    def remove_node(self):
        """
        Remove a node from an existing cluster
        """
        if self.parameters.get('cluster_ip_address') is not None:
            cluster_remove_node = netapp_utils.zapi.NaElement('cluster-remove-node')
            cluster_remove_node.add_new_child('cluster-ip', self.parameters.get('cluster_ip_address'))
        else:
            raise KeyError('TODO: DEVOPS-2336 support other ways to remove a node')
        try:
            self.server.invoke_successfully(cluster_remove_node, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            if error.message == "Unable to find API: cluster-remove-node":
                msg = 'Error: ZAPI is not available.  Removing a node requires ONTAP 9.4 or newer.'
                self.module.fail_json(msg=msg)
            self.module.fail_json(msg='Error removing node with ip %s: %s'
                                  % (self.parameters.get('cluster_ip_address'), to_native(error)),
                                  exception=traceback.format_exc())

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
                if error.message == "Unable to find API: cluster-add-node-status-get-iter":
                    # This API is not supported for 9.3 or earlier releases, just wait a bit
                    time.sleep(60)
                    return
                self.module.fail_json(msg='Error adding node with ip address %s: %s'
                                      % (self.parameters.get('cluster_ip_address'), to_native(error)),
                                      exception=traceback.format_exc())

            attributes_list = result.get_child_by_name('attributes-list')
            join_progress = attributes_list.get_child_by_name('cluster-create-add-node-status-info')
            is_complete = join_progress.get_child_content('status')
            failure_msg = join_progress.get_child_content('failure-msg')

        if is_complete != 'success':
            if 'Node is already in a cluster' in failure_msg:
                return
            else:
                self.module.fail_json(
                    msg='Error adding node with ip address %s' % (self.parameters.get('cluster_ip_address')))

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
        cluster_action = None
        node_action = None
        # TODO: DEVOPS-2336 remove debug
        debug = list()

        cluster_identity = self.get_cluster_identity(ignore_error=True)
        if self.parameters.get('cluster_name') is not None:
            cluster_action = self.na_helper.get_cd_action(cluster_identity, self.parameters)
        if self.parameters.get('cluster_ip_address') is not None:
            existing_interfaces = self.get_cluster_ip_address(self.parameters.get('cluster_ip_address'))
            if self.parameters.get('state') == 'present':
                node_action = 'add_node' if existing_interfaces is None else None
            else:
                node_action = 'remove_node' if existing_interfaces is not None else None
            debug.append('existing_interfaces %s' % repr(existing_interfaces))
        modify = self.na_helper.get_modified_attributes(cluster_identity, self.parameters)
        debug.append('cluster_action %s' % cluster_action)
        debug.append('node_action %s' % node_action)

        if node_action is not None:
            self.na_helper.changed = True

        if not self.module.check_mode:
            if cluster_action == 'create':
                if self.create_cluster():
                    self.cluster_create_wait()
            if node_action == 'add_node':
                if self.add_node():
                    self.node_add_wait()
            elif node_action == 'remove_node':
                self.remove_node()
                # TODO: DEVOPS-2336 wait for interface to disappear
                # leave a bit of time for things to settle in teh meantime
                time.sleep(60)
            if modify:
                self.modify_cluster_identity(modify)
        self.autosupport_log()
        self.module.exit_json(changed=self.na_helper.changed, debug=debug)


def main():
    """
    Create object and call apply
    """
    cluster_obj = NetAppONTAPCluster()
    cluster_obj.apply()


if __name__ == '__main__':
    main()
