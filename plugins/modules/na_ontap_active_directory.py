#!/usr/bin/python

# (c) 2020, NetApp Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = '''
module: na_ontap_active_directory
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
short_description: NetApp ONTAP configure active directory
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 20.9.0
description:
    - Configure Active Directory

options:
  state:
    description:
    - Whether the Active Directory should exist or not
    choices: ['present', 'absent']
    default: present
    type: str

  vserver:
    description:
    - The name of the vserver to use.
    required: true
    type: str

  account_name:
    description:
    - Active Directory account NetBIOS name.
    required: true
    type: str

  admin_password:
    description:
    - Administrator password required for Active Directory account creation.
    required: true
    type: str

  admin_username:
    description:
    - Administrator username required for Active Directory account creation.
    required: true
    type: str

  domain:
    description:
    - Fully qualified domain name.
    type: str

  force_account_overwrite:
    description:
    - If true and a machine account with the same name as specified in 'account-name' exists in Active Directory, it will be overwritten and reused.
    type: bool

  organizational_unit:
    description:
    - Organizational unit under which the Active Directory account will be created.
    type: str
'''
EXAMPLES = """
-
  name: Ontap test
  hosts: localhost
  collections:
    - netapp.ontap
  tasks:
    - name: run ontap active directory
      na_ontap_active_directory:
        hostname: 10.193.78.219
        username: admin
        password: netapp1!
        https: True
        validate_certs: False
        vserver: laurentncluster-1
        state: present
        account_name: carchi
        admin_password: password
        admin_username: carchi
        domain: 12
"""
RETURN = """

"""

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapActiveDirectory(object):
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            vserver=dict(required=True, type='str'),
            state=dict(choices=['present', 'absent'], default='present'),
            account_name=dict(required=True, type='str'),
            admin_password=dict(required=True, type='str', no_log=True),
            admin_username=dict(required=True, type='str'),
            domain=dict(type="str", default=None),
            force_account_overwrite=dict(type="bool", default=None),
            organizational_unit=dict(type="str", default=None)
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
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def get_active_directory(self):
        active_directory_iter = netapp_utils.zapi.NaElement('active-directory-account-get-iter')
        acitve_directory_info = netapp_utils.zapi.NaElement('active-directory-account-config')
        acitve_directory_info.add_new_child('account-name', self.parameters['account_name'])
        acitve_directory_info.add_new_child('vserver', self.parameters['vserver'])
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(acitve_directory_info)
        active_directory_iter.add_child_elem(query)
        try:
            result = self.server.invoke_successfully(active_directory_iter, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error searching for Active Directory %s: %s' %
                                      (self.parameters['account-name'], to_native(error)),
                                  exception=traceback.format_exc())
        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) >= 1:
            return result.get_child_by_name('attributes-list').get_child_by_name('active-directory-account-config')
        return None

    def create_active_directory(self):
        active_directory_obj = netapp_utils.zapi.NaElement('active-directory-account-create')
        active_directory_obj.add_new_child('account-name', self.parameters['account_name'])
        active_directory_obj.add_new_child('admin-password', self.parameters['admin_password'])
        active_directory_obj.add_new_child('admin-username', self.parameters['admin_username'])
        if self.parameters.get('domain'):
            active_directory_obj.add_new_child('domain', self.parameters['domain'])
        if self.parameters.get('force_account_overwrite'):
            active_directory_obj.add_new_child('force-account-overwrite', str(self.parameters['force_account_overwrite']))
        if self.parameters.get('organizational_unit'):
            active_directory_obj.add_new_child('organizational-unit', self.parameters['organizational_unit'])
        try:
            result = self.server.invoke_successfully(active_directory_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating on Active Directory %s: %s' %
                                      (self.parameters['account_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def delete_active_directory(self):
        active_directory_obj = netapp_utils.zapi.NaElement('active-directory-account-delete')
        active_directory_obj.add_new_child('admin-password', self.parameters['admin_password'])
        active_directory_obj.add_new_child('admin-username', self.parameters['admin_username'])
        try:
            result = self.server.invoke_successfully(active_directory_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting on Active Directory %s: %s' %
                                      (self.parameters['account_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_active_directory(self):
        active_directory_obj = netapp_utils.zapi.NaElement('active-directory-account-modify')
        active_directory_obj.add_new_child('admin-password', self.parameters['admin_password'])
        active_directory_obj.add_new_child('admin-username', self.parameters['admin_username'])
        if self.parameters.get('domain'):
            active_directory_obj.add_new_child('domain', self.parameters['domain'])
        if self.parameters.get('force_account_overwrite'):
            active_directory_obj.add_new_child('force-account-overwrite', str(self.parameters['force_account_overwrite']))
        try:
            result = self.server.invoke_successfully(active_directory_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting on Active Directory %s: %s' %
                                      (self.parameters['account_name'], to_native(error)),
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
        self.asup_log_for_cserver("na_ontap_active_directory")
        current = self.get_active_directory()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        modify = None
        if cd_action is None and self.parameters['state'] == 'present':
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed:
            # TODO add Modify
            if self.module.check_mode:
                pass
            else:
                if cd_action == 'create':
                    self.create_active_directory()
                elif cd_action == 'delete':
                    self.delete_active_directory()
                elif modify:
                    self.modify_active_directory()
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """
    Execute action from playbook
    """
    command = NetAppOntapActiveDirectory()
    command.apply()


if __name__ == '__main__':
    main()
