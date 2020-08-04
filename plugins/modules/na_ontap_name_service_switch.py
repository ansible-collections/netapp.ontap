#!/usr/bin/python

# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - Create/Delete/Modify Name Service Switch
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
module: na_ontap_name_service_switch
options:
  state:
    choices: ['present', 'absent']
    description:
      - Whether the specified ns-switch should exist or not.
    default: present
    type: str
  vserver:
    description:
      - Name of the vserver to use.
    required: true
    type: str
  database_type:
    description:
      - Name services switch database.
    choices: ['hosts','group', 'passwd', 'netgroup', 'namemap']
    required: true
    type: str
  sources:
    description:
      - Type of sources.
      - Possible values include files,dns,ldap,nis.
    type: list
    elements: str

short_description: "NetApp ONTAP Manage name service switch"
'''

EXAMPLES = """
    - name: create name service database
      na_ontap_name_service_switch:
        state: present
        database_type: namemap
        sources: files,ldap
        vserver: "{{ Vserver name }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        hostname: "{{ netapp_hostname }}"

    - name: modify name service database sources
      na_ontap_name_service_switch:
        state: present
        database_type: namemap
        sources: files
        vserver: "{{ Vserver name }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        hostname: "{{ netapp_hostname }}"
"""

RETURN = """
"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppONTAPNsswitch(object):
    """
    Class with NVMe service methods
    """

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            vserver=dict(required=True, type='str'),
            database_type=dict(required=True, type='str', choices=['hosts', 'group', 'passwd', 'netgroup', 'namemap']),
            sources=dict(required=False, type='list', elements='str')
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

    def get_name_service_switch(self):
        """
        get current name service switch config
        :return: dict of current name service switch
        """
        nss_iter = netapp_utils.zapi.NaElement('nameservice-nsswitch-get-iter')
        nss_info = netapp_utils.zapi.NaElement('namservice-nsswitch-config-info')
        db_type = netapp_utils.zapi.NaElement('nameservice-database')
        db_type.set_content(self.parameters['database_type'])
        query = netapp_utils.zapi.NaElement('query')
        nss_info.add_child_elem(db_type)
        query.add_child_elem(nss_info)
        nss_iter.add_child_elem(query)
        result = self.server.invoke_successfully(nss_iter, True)
        return_value = None
        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) == 1:
            nss_sources = result.get_child_by_name('attributes-list').get_child_by_name(
                'namservice-nsswitch-config-info').get_child_by_name('nameservice-sources')
            sources = [sources.get_content() for sources in nss_sources.get_children()]
            return_value = {
                'sources': sources
            }
        return return_value

    def create_name_service_switch(self):
        """
        create name service switch config
        :return: None
        """
        nss_create = netapp_utils.zapi.NaElement('nameservice-nsswitch-create')
        nss_create.add_new_child('nameservice-database', self.parameters['database_type'])
        nss_sources = netapp_utils.zapi.NaElement('nameservice-sources')
        nss_create.add_child_elem(nss_sources)
        for source in self.parameters['sources']:
            nss_sources.add_new_child('nss-source-type', source.strip())
        try:
            self.server.invoke_successfully(nss_create,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error on creating name service switch config on vserver %s: %s'
                                      % (self.parameters['vserver'], to_native(error)),
                                  exception=traceback.format_exc())

    def delete_name_service_switch(self):
        """
        delete name service switch
        :return: None
        """
        nss_delete = netapp_utils.zapi.NaElement.create_node_with_children(
            'nameservice-nsswitch-destroy', **{'nameservice-database': self.parameters['database_type']})
        try:
            self.server.invoke_successfully(nss_delete,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error on deleting name service switch config on vserver %s: %s'
                                      % (self.parameters['vserver'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_name_service_switch(self, modify):
        """
        modify name service switch
        :param modify: dict of modify attributes
        :return: None
        """
        nss_modify = netapp_utils.zapi.NaElement('nameservice-nsswitch-modify')
        nss_modify.add_new_child('nameservice-database', self.parameters['database_type'])
        nss_sources = netapp_utils.zapi.NaElement('nameservice-sources')
        nss_modify.add_child_elem(nss_sources)
        if 'sources' in modify:
            for source in self.parameters['sources']:
                nss_sources.add_new_child('nss-source-type', source.strip())
        try:
            self.server.invoke_successfully(nss_modify, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error on modifying name service switch config on vserver %s: %s'
                                  % (self.parameters['vserver'], to_native(error)),
                                  exception=traceback.format_exc())

    def apply(self):
        netapp_utils.ems_log_event("na_ontap_name_service_switch", self.server)
        current = self.get_name_service_switch()
        cd_action, modify = None, None
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        modify = self.na_helper.get_modified_attributes(current, self.parameters)

        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if cd_action == 'create':
                    self.create_name_service_switch()
                elif cd_action == 'delete':
                    self.delete_name_service_switch()
                elif modify:
                    self.modify_name_service_switch(modify)
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    '''Applyoperations from playbook'''
    nss = NetAppONTAPNsswitch()
    nss.apply()


if __name__ == '__main__':
    main()
