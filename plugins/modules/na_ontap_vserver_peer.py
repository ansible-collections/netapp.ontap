#!/usr/bin/python

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - Create/Delete vserver peer
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
  - netapp.ontap.netapp.na_ontap_peer
module: na_ontap_vserver_peer
options:
  state:
    choices: ['present', 'absent']
    type: str
    description:
    - Whether the specified vserver peer should exist or not.
    default: present
  vserver:
    description:
    - Specifies name of the source Vserver in the relationship.
    required: true
    type: str
  applications:
    type: list
    elements: str
    description:
    - List of applications which can make use of the peering relationship.
    - FlexCache supported from ONTAP 9.5 onwards.
  peer_vserver:
    description:
    - Specifies name of the peer Vserver in the relationship.
    required: true
    type: str
  peer_cluster:
    description:
    - Specifies name of the peer Cluster.
    - Required for creating the vserver peer relationship with a remote cluster
    type: str
  local_name_for_peer:
    description:
    - Specifies local name of the peer Vserver in the relationship.
    - Use this if you see "Error creating vserver peer ... Vserver name conflicts with one of the following".
    type: str
  local_name_for_source:
    description:
    - Specifies local name of the source Vserver in the relationship.
    - Use this if you see "Error accepting vserver peer ... System generated a name for the peer Vserver because of a naming conflict".
    type: str
  dest_hostname:
    description:
    - DEPRECATED - please use C(peer_options).
    - Destination hostname or IP address.
    - Required for creating the vserver peer relationship with a remote cluster.
    type: str
  dest_username:
    description:
    - DEPRECATED - please use C(peer_options).
    - Destination username.
    - Optional if this is same as source username.
    type: str
  dest_password:
    description:
    - DEPRECATED - please use C(peer_options).
    - Destination password.
    - Optional if this is same as source password.
    type: str
short_description: NetApp ONTAP Vserver peering
version_added: 2.7.0
'''

EXAMPLES = """

    - name: Source vserver peer create
      netapp.ontap.na_ontap_vserver_peer:
        state: present
        peer_vserver: ansible2
        peer_cluster: ansibleCluster
        local_name_for_peer: peername
        local_name_for_source: sourcename
        vserver: ansible
        applications: ['snapmirror']
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        peer_options:
          hostname: "{{ netapp_dest_hostname }}"

    - name: vserver peer delete
      netapp.ontap.na_ontap_vserver_peer:
        state: absent
        peer_vserver: ansible2
        vserver: ansible
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Source vserver peer create - different credentials
      netapp.ontap.na_ontap_vserver_peer:
        state: present
        peer_vserver: ansible2
        peer_cluster: ansibleCluster
        local_name_for_peer: peername
        local_name_for_source: sourcename
        vserver: ansible
        applications: ['snapmirror']
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        peer_options:
          hostname: "{{ netapp_dest_hostname }}"
          cert_filepath: "{{ cert_filepath }}"
          key_filepath: "{{ key_filepath }}"
"""

RETURN = """
"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppONTAPVserverPeer():
    """
    Class with vserver peer methods
    """

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            vserver=dict(required=True, type='str'),
            peer_vserver=dict(required=True, type='str'),
            peer_cluster=dict(required=False, type='str'),
            local_name_for_peer=dict(required=False, type='str'),
            local_name_for_source=dict(required=False, type='str'),
            applications=dict(required=False, type='list', elements='str'),
            peer_options=dict(type='dict', options=netapp_utils.na_ontap_host_argument_spec_peer()),
            dest_hostname=dict(required=False, type='str'),
            dest_username=dict(required=False, type='str'),
            dest_password=dict(required=False, type='str', no_log=True)
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            mutually_exclusive=[
                ['peer_options', 'dest_hostname'],
                ['peer_options', 'dest_username'],
                ['peer_options', 'dest_password']
            ],
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)
            if self.parameters.get('dest_hostname') is None and self.parameters.get('peer_options') is None:
                return
            if self.parameters.get('dest_hostname') is not None:
                # if dest_hostname is present, peer_options is absent
                self.parameters['peer_options'] = dict(
                    hostname=self.parameters.get('dest_hostname'),
                    username=self.parameters.get('dest_username'),
                    password=self.parameters.get('dest_password'),
                )
            else:
                self.parameters['dest_hostname'] = self.parameters['peer_options']['hostname']
            netapp_utils.setup_host_options_from_module_params(
                self.parameters['peer_options'], self.module,
                netapp_utils.na_ontap_host_argument_spec_peer().keys())
            self.dest_server = netapp_utils.setup_na_ontap_zapi(module=self.module, host_options=self.parameters['peer_options'])

    def vserver_peer_get_iter(self, target):
        """
        Compose NaElement object to query current vserver using remote-vserver-name and vserver parameters
        :return: NaElement object for vserver-get-iter with query
        """
        vserver_peer_get = netapp_utils.zapi.NaElement('vserver-peer-get-iter')
        query = netapp_utils.zapi.NaElement('query')
        vserver_peer_info = netapp_utils.zapi.NaElement('vserver-peer-info')
        if target == 'source':
            vserver_peer_info.add_new_child('remote-vserver-name', self.parameters['peer_vserver'])
            vserver_peer_info.add_new_child('vserver', self.parameters['vserver'])
        elif target == 'peer':
            vserver_peer_info.add_new_child('remote-vserver-name', self.parameters['vserver'])
            vserver_peer_info.add_new_child('vserver', self.parameters['peer_vserver'])
        query.add_child_elem(vserver_peer_info)
        vserver_peer_get.add_child_elem(query)
        return vserver_peer_get

    def vserver_peer_get(self, target='source'):
        """
        Get current vserver peer info
        :return: Dictionary of current vserver peer details if query successful, else return None
        """
        vserver_peer_get_iter = self.vserver_peer_get_iter(target)
        vserver_info = dict()
        try:
            if target == 'source':
                result = self.server.invoke_successfully(vserver_peer_get_iter, enable_tunneling=True)
            elif target == 'peer':
                result = self.dest_server.invoke_successfully(vserver_peer_get_iter, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching vserver peer %s: %s'
                                      % (self.parameters['vserver'], to_native(error)),
                                  exception=traceback.format_exc())
        # return vserver peer details
        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) > 0:
            vserver_peer_info = result.get_child_by_name('attributes-list').get_child_by_name('vserver-peer-info')
            vserver_info['peer_vserver'] = vserver_peer_info.get_child_content('remote-vserver-name')
            vserver_info['vserver'] = vserver_peer_info.get_child_content('vserver')
            vserver_info['local_peer_vserver'] = vserver_peer_info.get_child_content('peer-vserver')       # required for delete and accept
            vserver_info['peer_state'] = vserver_peer_info.get_child_content('peer-state')
            return vserver_info
        return None

    def vserver_peer_delete(self, current):
        """
        Delete a vserver peer
        """
        vserver_peer_delete = netapp_utils.zapi.NaElement.create_node_with_children(
            'vserver-peer-delete', **{'peer-vserver': current['local_peer_vserver'],
                                      'vserver': self.parameters['vserver']})
        try:
            self.server.invoke_successfully(vserver_peer_delete,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting vserver peer %s: %s'
                                      % (self.parameters['vserver'], to_native(error)),
                                  exception=traceback.format_exc())

    def get_peer_cluster_name(self):
        """
        Get local cluster name
        :return: cluster name
        """
        cluster_info = netapp_utils.zapi.NaElement('cluster-identity-get')
        try:
            result = self.server.invoke_successfully(cluster_info, enable_tunneling=True)
            return result.get_child_by_name('attributes').get_child_by_name(
                'cluster-identity-info').get_child_content('cluster-name')
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching peer cluster name for peer vserver %s: %s'
                                      % (self.parameters['peer_vserver'], to_native(error)),
                                  exception=traceback.format_exc())

    def vserver_peer_create(self):
        """
        Create a vserver peer
        """
        if self.parameters.get('applications') is None:
            self.module.fail_json(msg='applications parameter is missing')
        if self.parameters.get('peer_cluster') is not None and self.parameters.get('dest_hostname') is None:
            self.module.fail_json(msg='dest_hostname is required for peering a vserver in remote cluster')
        if self.parameters.get('peer_cluster') is None:
            self.parameters['peer_cluster'] = self.get_peer_cluster_name()
        vserver_peer_create = netapp_utils.zapi.NaElement.create_node_with_children(
            'vserver-peer-create', **{'peer-vserver': self.parameters['peer_vserver'],
                                      'vserver': self.parameters['vserver'],
                                      'peer-cluster': self.parameters['peer_cluster']})
        if 'local_name_for_peer' in self.parameters:
            vserver_peer_create.add_new_child('local-name', self.parameters['local_name_for_peer'])
        applications = netapp_utils.zapi.NaElement('applications')
        for application in self.parameters['applications']:
            applications.add_new_child('vserver-peer-application', application)
        vserver_peer_create.add_child_elem(applications)
        try:
            self.server.invoke_successfully(vserver_peer_create,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating vserver peer %s: %s'
                                      % (self.parameters['vserver'], to_native(error)),
                                  exception=traceback.format_exc())

    def is_remote_peer(self):
        if self.parameters.get('dest_hostname') is None or \
                (self.parameters['dest_hostname'] == self.parameters['hostname']):
            return False
        return True

    def vserver_peer_accept(self):
        """
        Accept a vserver peer at destination
        """
        # peer-vserver -> remote (source vserver is provided)
        # vserver -> local (destination vserver is provided)
        vserver_peer_info = self.vserver_peer_get('peer')
        if vserver_peer_info is None:
            self.module.fail_json(msg='Error retrieving vserver peer information while accepting')
        vserver_peer_accept = netapp_utils.zapi.NaElement.create_node_with_children(
            'vserver-peer-accept', **{'peer-vserver': vserver_peer_info['local_peer_vserver'],
                                      'vserver': self.parameters['peer_vserver']})
        if 'local_name_for_source' in self.parameters:
            vserver_peer_accept.add_new_child('local-name', self.parameters['local_name_for_source'])
        try:
            self.dest_server.invoke_successfully(vserver_peer_accept, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error accepting vserver peer %s: %s'
                                      % (self.parameters['peer_vserver'], to_native(error)),
                                  exception=traceback.format_exc())

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

    def apply(self):
        """
        Apply action to create/delete or accept vserver peer
        """
        self.asup_log_for_cserver("na_ontap_vserver_peer")
        current = self.vserver_peer_get()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if self.na_helper.changed:
            if not self.module.check_mode:
                if cd_action == 'create':
                    self.vserver_peer_create()
                    # accept only if the peer relationship is on a remote cluster
                    if self.is_remote_peer():
                        self.vserver_peer_accept()
                elif cd_action == 'delete':
                    self.vserver_peer_delete(current)

        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """Execute action"""
    community_obj = NetAppONTAPVserverPeer()
    community_obj.apply()


if __name__ == '__main__':
    main()
