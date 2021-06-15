#!/usr/bin/python

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - Create/Delete cluster peer relations on ONTAP
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
  - netapp.ontap.netapp.na_ontap_peer
module: na_ontap_cluster_peer
options:
  state:
    choices: ['present', 'absent']
    type: str
    description:
      - Whether the specified cluster peer should exist or not.
    default: present
  source_intercluster_lifs:
    description:
      - List of intercluster addresses of the source cluster.
      - Used as peer-addresses in destination cluster.
      - All these intercluster lifs should belong to the source cluster.
    version_added: 2.8.0
    type: list
    elements: str
    aliases:
    - source_intercluster_lif
  dest_intercluster_lifs:
    description:
      - List of intercluster addresses of the destination cluster.
      - Used as peer-addresses in source cluster.
      - All these intercluster lifs should belong to the destination cluster.
    version_added: 2.8.0
    type: list
    elements: str
    aliases:
    - dest_intercluster_lif
  passphrase:
    description:
      - The arbitrary passphrase that matches the one given to the peer cluster.
    type: str
  source_cluster_name:
    description:
      - The name of the source cluster name in the peer relation to be deleted.
    type: str
  dest_cluster_name:
    description:
      - The name of the destination cluster name in the peer relation to be deleted.
      - Required for delete
    type: str
  dest_hostname:
    description:
      - DEPRECATED - please use C(peer_options).
      - Destination cluster IP or hostname which needs to be peered.
      - Required to complete the peering process at destination cluster.
    type: str
  dest_username:
    description:
      - DEPRECATED - please use C(peer_options).
      - Destination username.
      - Optional if this is same as source username or if a certificate is used.
    type: str
  dest_password:
    description:
      - DEPRECATED - please use C(peer_options).
      - Destination password.
      - Optional if this is same as source password or if a certificate is used..
    type: str
  ipspace:
    description:
    - IPspace of the local intercluster LIFs.
    - Assumes Default IPspace if not provided.
    type: str
    version_added: '20.11.0'
  encryption_protocol_proposed:
    description:
     - Encryption protocol to be used for inter-cluster communication.
     - Only available on ONTAP 9.5 or later.
    choices: ['tls_psk', 'none']
    type: str
    version_added: '20.5.0'
short_description: NetApp ONTAP Manage Cluster peering
version_added: 2.7.0
'''

EXAMPLES = """

    - name: Create cluster peer
      netapp.ontap.na_ontap_cluster_peer:
        state: present
        source_intercluster_lifs: 1.2.3.4,1.2.3.5
        dest_intercluster_lifs: 1.2.3.6,1.2.3.7
        passphrase: XXXX
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        peer_options:
          hostname: "{{ dest_netapp_hostname }}"
        encryption_protocol_proposed: tls_psk

    - name: Delete cluster peer
      netapp.ontap.na_ontap_cluster_peer:
        state: absent
        source_cluster_name: test-source-cluster
        dest_cluster_name: test-dest-cluster
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        peer_options:
          hostname: "{{ dest_netapp_hostname }}"

    - name: Create cluster peer - different credentials
      netapp.ontap.na_ontap_cluster_peer:
        state: present
        source_intercluster_lifs: 1.2.3.4,1.2.3.5
        dest_intercluster_lifs: 1.2.3.6,1.2.3.7
        passphrase: XXXX
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        peer_options:
          hostname: "{{ dest_netapp_hostname }}"
          cert_filepath: "{{ cert_filepath }}"
          key_filepath: "{{ key_filepath }}"
        encryption_protocol_proposed: tls_psk

"""

RETURN = """
"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppONTAPClusterPeer():
    """
    Class with cluster peer methods
    """

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            source_intercluster_lifs=dict(required=False, type='list', elements='str', aliases=['source_intercluster_lif']),
            dest_intercluster_lifs=dict(required=False, type='list', elements='str', aliases=['dest_intercluster_lif']),
            passphrase=dict(required=False, type='str', no_log=True),
            peer_options=dict(type='dict', options=netapp_utils.na_ontap_host_argument_spec_peer()),
            dest_hostname=dict(required=False, type='str'),
            dest_username=dict(required=False, type='str'),
            dest_password=dict(required=False, type='str', no_log=True),
            source_cluster_name=dict(required=False, type='str'),
            dest_cluster_name=dict(required=False, type='str'),
            ipspace=dict(required=False, type='str'),
            encryption_protocol_proposed=dict(required=False, type='str', choices=['tls_psk', 'none'])
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            mutually_exclusive=[
                ['peer_options', 'dest_hostname'],
                ['peer_options', 'dest_username'],
                ['peer_options', 'dest_password']
            ],
            required_one_of=[['peer_options', 'dest_hostname']],
            required_together=[['source_intercluster_lifs', 'dest_intercluster_lifs']],
            required_if=[('state', 'absent', ['source_cluster_name', 'dest_cluster_name'])],
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)
            # set peer server connection
            if self.parameters.get('dest_hostname') is not None:
                # if dest_hostname is present, peer_options is absent
                self.parameters['peer_options'] = dict(
                    hostname=self.parameters.get('dest_hostname'),
                    username=self.parameters.get('dest_username'),
                    password=self.parameters.get('dest_password'),
                )
            netapp_utils.setup_host_options_from_module_params(
                self.parameters['peer_options'], self.module,
                netapp_utils.na_ontap_host_argument_spec_peer().keys())
            self.dest_server = netapp_utils.setup_na_ontap_zapi(module=self.module, host_options=self.parameters['peer_options'])

    def cluster_peer_get_iter(self, cluster):
        """
        Compose NaElement object to query current source cluster using peer-cluster-name and peer-addresses parameters
        :param cluster: type of cluster (source or destination)
        :return: NaElement object for cluster-get-iter with query
        """
        cluster_peer_get = netapp_utils.zapi.NaElement('cluster-peer-get-iter')
        query = netapp_utils.zapi.NaElement('query')
        cluster_peer_info = netapp_utils.zapi.NaElement('cluster-peer-info')
        if cluster == 'source':
            peer_lifs, peer_cluster = 'dest_intercluster_lifs', 'dest_cluster_name'
        else:
            peer_lifs, peer_cluster = 'source_intercluster_lifs', 'source_cluster_name'
        if self.parameters.get(peer_lifs):
            peer_addresses = netapp_utils.zapi.NaElement('peer-addresses')
            for peer in self.parameters.get(peer_lifs):
                peer_addresses.add_new_child('remote-inet-address', peer)
            cluster_peer_info.add_child_elem(peer_addresses)
        if self.parameters.get(peer_cluster):
            cluster_peer_info.add_new_child('cluster-name', self.parameters[peer_cluster])
        query.add_child_elem(cluster_peer_info)
        cluster_peer_get.add_child_elem(query)
        return cluster_peer_get

    def cluster_peer_get(self, cluster):
        """
        Get current cluster peer info
        :param cluster: type of cluster (source or destination)
        :return: Dictionary of current cluster peer details if query successful, else return None
        """
        cluster_peer_get_iter = self.cluster_peer_get_iter(cluster)
        result, cluster_info = None, dict()
        if cluster == 'source':
            server = self.server
        else:
            server = self.dest_server
        try:
            result = server.invoke_successfully(cluster_peer_get_iter, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching cluster peer %s: %s'
                                  % (cluster, to_native(error)),
                                  exception=traceback.format_exc())
        # return cluster peer details
        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) >= 1:
            cluster_peer_info = result.get_child_by_name('attributes-list').get_child_by_name('cluster-peer-info')
            cluster_info['cluster_name'] = cluster_peer_info.get_child_content('cluster-name')
            peers = cluster_peer_info.get_child_by_name('peer-addresses')
            cluster_info['peer-addresses'] = [peer.get_content() for peer in peers.get_children()]
            return cluster_info
        return None

    def cluster_peer_delete(self, cluster):
        """
        Delete a cluster peer on source or destination
        For source cluster, peer cluster-name = destination cluster name and vice-versa
        :param cluster: type of cluster (source or destination)
        :return:
        """
        if cluster == 'source':
            server, peer_cluster_name = self.server, self.parameters['dest_cluster_name']
        else:
            server, peer_cluster_name = self.dest_server, self.parameters['source_cluster_name']
        cluster_peer_delete = netapp_utils.zapi.NaElement.create_node_with_children(
            'cluster-peer-delete', **{'cluster-name': peer_cluster_name})
        try:
            server.invoke_successfully(cluster_peer_delete, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting cluster peer %s: %s'
                                      % (peer_cluster_name, to_native(error)),
                                  exception=traceback.format_exc())

    def cluster_peer_create(self, cluster):
        """
        Create a cluster peer on source or destination
        For source cluster, peer addresses = destination inter-cluster LIFs and vice-versa
        :param cluster: type of cluster (source or destination)
        :return: None
        """
        cluster_peer_create = netapp_utils.zapi.NaElement.create_node_with_children('cluster-peer-create')
        if self.parameters.get('passphrase') is not None:
            cluster_peer_create.add_new_child('passphrase', self.parameters['passphrase'])
        peer_addresses = netapp_utils.zapi.NaElement('peer-addresses')
        if cluster == 'source':
            server, peer_address = self.server, self.parameters['dest_intercluster_lifs']
        else:
            server, peer_address = self.dest_server, self.parameters['source_intercluster_lifs']
        for each in peer_address:
            peer_addresses.add_new_child('remote-inet-address', each)
        cluster_peer_create.add_child_elem(peer_addresses)
        if self.parameters.get('encryption_protocol_proposed') is not None:
            cluster_peer_create.add_new_child('encryption-protocol-proposed', self.parameters['encryption_protocol_proposed'])
        if self.parameters.get('ipspace') is not None:
            cluster_peer_create.add_new_child('ipspace-name', self.parameters['ipspace'])

        try:
            server.invoke_successfully(cluster_peer_create, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating cluster peer %s: %s'
                                  % (peer_address, to_native(error)),
                                  exception=traceback.format_exc())

    def apply(self):
        """
        Apply action to cluster peer
        :return: None
        """
        self.asup_log_for_cserver("na_ontap_cluster_peer")
        source = self.cluster_peer_get('source')
        destination = self.cluster_peer_get('destination')
        source_action = self.na_helper.get_cd_action(source, self.parameters)
        destination_action = self.na_helper.get_cd_action(destination, self.parameters)
        self.na_helper.changed = False
        # create only if expected cluster peer relation is not present on both source and destination clusters
        if source_action == 'create' and destination_action == 'create':
            if not self.module.check_mode:
                self.cluster_peer_create('source')
                self.cluster_peer_create('destination')
            self.na_helper.changed = True
        # delete peer relation in cluster where relation is present
        else:
            if source_action == 'delete':
                if not self.module.check_mode:
                    self.cluster_peer_delete('source')
                self.na_helper.changed = True
            if destination_action == 'delete':
                if not self.module.check_mode:
                    self.cluster_peer_delete('destination')
                self.na_helper.changed = True

        self.module.exit_json(changed=self.na_helper.changed)

    def asup_log_for_cserver(self, event_name):
        """
        Fetch admin vserver for the given cluster
        Create and Autosupport log event with the given module name
        :param event_name: Name of the event log
        :return: None
        """
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event(event_name, cserver)


def main():
    """
    Execute action
    :return: None
    """
    community_obj = NetAppONTAPClusterPeer()
    community_obj.apply()


if __name__ == '__main__':
    main()
