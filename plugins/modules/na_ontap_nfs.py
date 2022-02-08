#!/usr/bin/python

# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = """
module: na_ontap_nfs
short_description: NetApp ONTAP NFS status
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Enable or disable NFS on ONTAP
options:
  state:
    description:
    - Whether NFS should exist or not.
    choices: ['present', 'absent']
    type: str
    default: present
  service_state:
    description:
    - Whether the specified NFS should be enabled or disabled. Creates NFS service if doesnt exist.
    choices: ['started', 'stopped']
    type: str
  vserver:
    description:
    - Name of the vserver to use.
    required: true
    type: str
  nfsv3:
    description:
    - status of NFSv3.
    choices: ['enabled', 'disabled']
    type: str
  nfsv3_fsid_change:
    description:
    - status of if NFSv3 clients see change in FSID as they traverse filesystems.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.7.0
  nfsv4_fsid_change:
    description:
    - status of if NFSv4 clients see change in FSID as they traverse filesystems.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.9.0
  nfsv4:
    description:
    - status of NFSv4.
    choices: ['enabled', 'disabled']
    type: str
  nfsv41:
    description:
    - status of NFSv41.
    aliases: ['nfsv4.1']
    choices: ['enabled', 'disabled']
    type: str
  nfsv41_pnfs:
    description:
    - status of NFSv41 pNFS.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.9.0
  nfsv4_numeric_ids:
    description:
    - status of NFSv4 numeric ID's.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.9.0
  vstorage_state:
    description:
    - status of vstorage_state.
    choices: ['enabled', 'disabled']
    type: str
  nfsv4_id_domain:
    description:
    - Name of the nfsv4_id_domain to use.
    type: str
  nfsv40_acl:
    description:
    - status of NFS v4.0 ACL feature
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.7.0
  nfsv40_read_delegation:
    description:
    - status for NFS v4.0 read delegation feature.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.7.0
  nfsv40_write_delegation:
    description:
    - status for NFS v4.0 write delegation feature.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.7.0
  nfsv41_acl:
    description:
    - status of NFS v4.1 ACL feature
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.7.0
  nfsv41_read_delegation:
    description:
    - status for NFS v4.1 read delegation feature.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.7.0
  nfsv41_write_delegation:
    description:
    - status for NFS v4.1 write delegation feature.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.7.0
  nfsv40_referrals:
    description:
    - status for NFS v4.0 referrals.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.9.0
  nfsv41_referrals:
    description:
    - status for NFS v4.1 referrals.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.9.0
  tcp:
    description:
    - Enable TCP (support from ONTAP 9.3 onward).
    choices: ['enabled', 'disabled']
    type: str
  udp:
    description:
    - Enable UDP (support from ONTAP 9.3 onward).
    choices: ['enabled', 'disabled']
    type: str
  showmount:
    description:
    - Whether SVM allows showmount
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.7.0
  tcp_max_xfer_size:
    description:
    - TCP Maximum Transfer Size (bytes). The default value is 65536.
    version_added: 2.8.0
    type: int

"""

EXAMPLES = """
    - name: change nfs status
      na_ontap_nfs:
        state: present
        service_state: stopped
        vserver: vs_hack
        nfsv3: disabled
        nfsv4: disabled
        nfsv41: enabled
        tcp: disabled
        udp: disabled
        vstorage_state: disabled
        nfsv4_id_domain: example.com
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


class NetAppONTAPNFS:
    """ object initialize and class methods """

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            service_state=dict(required=False, type='str', choices=['started', 'stopped']),
            vserver=dict(required=True, type='str'),
            nfsv3=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv3_fsid_change=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv4_fsid_change=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv4=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv41=dict(required=False, type='str', default=None, choices=['enabled', 'disabled'], aliases=['nfsv4.1']),
            nfsv41_pnfs=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv4_numeric_ids=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            vstorage_state=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            tcp=dict(required=False, default=None, type='str', choices=['enabled', 'disabled']),
            udp=dict(required=False, default=None, type='str', choices=['enabled', 'disabled']),
            nfsv4_id_domain=dict(required=False, type='str', default=None),
            nfsv40_acl=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv40_read_delegation=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv40_referrals=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv40_write_delegation=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv41_acl=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv41_read_delegation=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv41_referrals=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            nfsv41_write_delegation=dict(required=False, type='str', default=None, choices=['enabled', 'disabled']),
            showmount=dict(required=False, default=None, type='str', choices=['enabled', 'disabled']),
            tcp_max_xfer_size=dict(required=False, default=None, type='int')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.zapi_names = {
            'nfsv3': 'is-nfsv3-enabled',
            'nfsv3_fsid_change': 'is-nfsv3-fsid-change-enabled',
            'nfsv4_fsid_change': 'is-nfsv4-fsid-change-enabled',
            'nfsv4': 'is-nfsv4-enabled',
            'nfsv41': 'is-nfsv41-enabled',
            'nfsv41_pnfs': 'is-nfsv41-pnfs-enabled',
            'nfsv4_numeric_ids': 'is-nfsv4-numeric-ids-enabled',
            'vstorage_state': 'is-vstorage-enabled',
            'nfsv4_id_domain': 'nfsv4-id-domain',
            'tcp': 'is-tcp-enabled',
            'udp': 'is-udp-enabled',
            'nfsv40_acl': 'is-nfsv40-acl-enabled',
            'nfsv40_read_delegation': 'is-nfsv40-read-delegation-enabled',
            'nfsv40_referrals': 'is-nfsv40-referrals-enabled',
            'nfsv40_write_delegation': 'is-nfsv40-write-delegation-enabled',
            'nfsv41_acl': 'is-nfsv41-acl-enabled',
            'nfsv41_read_delegation': 'is-nfsv41-read-delegation-enabled',
            'nfsv41_referrals': 'is-nfsv41-referrals-enabled',
            'nfsv41_write_delegation': 'is-nfsv41-write-delegation-enabled',
            'showmount': 'showmount',
            'tcp_max_xfer_size': 'tcp-max-xfer-size'
        }

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def get_nfs_service(self):
        nfs_get_iter = netapp_utils.zapi.NaElement('nfs-service-get-iter')
        nfs_info = netapp_utils.zapi.NaElement('nfs-info')
        nfs_info.add_new_child('vserver', self.parameters['vserver'])
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(nfs_info)
        nfs_get_iter.add_child_elem(query)
        result = self.server.invoke_successfully(nfs_get_iter, True)
        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) >= 1:
            return self.format_return(result)
        return None

    def format_return(self, result):
        attributes_list = result.get_child_by_name('attributes-list').get_child_by_name('nfs-info')
        return {
            'nfsv3': self.convert_from_bool(attributes_list.get_child_content('is-nfsv3-enabled')),
            'nfsv3_fsid_change': self.convert_from_bool(attributes_list.get_child_content('is-nfsv3-fsid-change-enabled')),
            'nfsv4_fsid_change': self.convert_from_bool(attributes_list.get_child_content('is-nfsv4-fsid-change-enabled')),
            'nfsv4': self.convert_from_bool(attributes_list.get_child_content('is-nfsv40-enabled')),
            'nfsv41': self.convert_from_bool(attributes_list.get_child_content('is-nfsv41-enabled')),
            'nfsv41_pnfs': self.convert_from_bool(attributes_list.get_child_content('is-nfsv41-pnfs-enabled')),
            'nfsv4_numeric_ids': self.convert_from_bool(attributes_list.get_child_content('is-nfsv4-numeric-ids-enabled')),
            'vstorage_state': self.convert_from_bool(attributes_list.get_child_content('is-vstorage-enabled')),
            'nfsv4_id_domain': attributes_list.get_child_content('nfsv4-id-domain'),
            'tcp': self.convert_from_bool(attributes_list.get_child_content('is-tcp-enabled')),
            'udp': self.convert_from_bool(attributes_list.get_child_content('is-udp-enabled')),
            'nfsv40_acl': self.convert_from_bool(attributes_list.get_child_content('is-nfsv40-acl-enabled')),
            'nfsv40_read_delegation': self.convert_from_bool(attributes_list.get_child_content('is-nfsv40-read-delegation-enabled')),
            'nfsv40_referrals': self.convert_from_bool(attributes_list.get_child_content('is-nfsv40-referrals-enabled')),
            'nfsv40_write_delegation': self.convert_from_bool(attributes_list.get_child_content('is-nfsv40-write-delegation-enabled')),
            'nfsv41_acl': self.convert_from_bool(attributes_list.get_child_content('is-nfsv41-acl-enabled')),
            'nfsv41_read_delegation': self.convert_from_bool(attributes_list.get_child_content('is-nfsv41-read-delegation-enabled')),
            'nfsv41_referrals': self.convert_from_bool(attributes_list.get_child_content('is-nfsv41-referrals-enabled')),
            'nfsv41_write_delegation': self.convert_from_bool(attributes_list.get_child_content('is-nfsv41-write-delegation-enabled')),
            'showmount': self.convert_from_bool(attributes_list.get_child_content('showmount')),
            'tcp_max_xfer_size': int(attributes_list.get_child_content('tcp-max-xfer-size'))
        }

    def get_nfs_status(self):
        nfs_status = netapp_utils.zapi.NaElement('nfs-status')
        result = self.server.invoke_successfully(nfs_status, True)
        return result.get_child_content('is-enabled')

    def enable_nfs(self):
        """
        enable nfs (online). If the NFS service was not explicitly created,
        this API will create one with default options.
        """
        nfs_enable = netapp_utils.zapi.NaElement.create_node_with_children('nfs-enable')
        try:
            self.server.invoke_successfully(nfs_enable, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error changing the service_state of nfs %s to %s: %s' %
                                      (self.parameters['vserver'], self.parameters['service_state'], to_native(error)),
                                  exception=traceback.format_exc())

    def disable_nfs(self):
        """
        disable nfs (offline).
        """
        nfs_disable = netapp_utils.zapi.NaElement.create_node_with_children('nfs-disable')
        try:
            self.server.invoke_successfully(nfs_disable, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error changing the service_state of nfs %s to %s: %s' %
                                      (self.parameters['vserver'], self.parameters['service_state'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_nfs_service(self, modify):
        nfs_modify = netapp_utils.zapi.NaElement('nfs-service-modify')
        service_state = modify.pop('service_state', None)
        self.modify_service_state(service_state)
        for each in modify:
            if each in ['nfsv4_id_domain', 'tcp_max_xfer_size']:
                nfs_modify.add_new_child(self.zapi_names[each], str(modify[each]))
            else:
                nfs_modify.add_new_child(self.zapi_names[each], self.convert_to_bool(modify[each]))
        try:
            self.server.invoke_successfully(nfs_modify, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying nfs: %s' % (to_native(error)),
                                  exception=traceback.format_exc())

    def modify_service_state(self, service_state):
        nfs_enabled = self.get_nfs_status()
        if service_state == 'started' and nfs_enabled == 'false':
            self.enable_nfs()
        elif service_state == 'stopped' and nfs_enabled == 'true':
            self.disable_nfs()

    def delete_nfs_service(self):
        """
        delete nfs service.
        """
        nfs_delete = netapp_utils.zapi.NaElement.create_node_with_children('nfs-service-destroy')
        try:
            self.server.invoke_successfully(nfs_delete, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting nfs: %s' % (to_native(error)),
                                  exception=traceback.format_exc())

    def convert_to_bool(self, value):
        return 'true' if value == 'enabled' else 'false'

    def convert_from_bool(self, value):
        return 'enabled' if value == 'true' else 'disabled'

    def apply(self):
        netapp_utils.ems_log_event("na_ontap_nfs", self.server)
        current = self.get_nfs_service()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        modify = None
        if cd_action is None and self.parameters['state'] == 'present':
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                # This is what the old module did, not sure what happens if nfs dosn't exist.
                self.enable_nfs()
            elif cd_action == 'delete':
                self.delete_nfs_service()
            elif modify:
                self.modify_nfs_service(modify)
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """ Create object and call apply """
    obj = NetAppONTAPNFS()
    obj.apply()


if __name__ == '__main__':
    main()
