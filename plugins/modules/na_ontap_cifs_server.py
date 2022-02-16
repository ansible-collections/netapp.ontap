#!/usr/bin/python
""" this is cifs_server module

 (c) 2018-2022, NetApp, Inc
 # GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
---
module: na_ontap_cifs_server
short_description: NetApp ONTAP CIFS server configuration
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
    - Creating / deleting and modifying the CIFS server .

options:

  state:
    description:
    - Whether the specified cifs_server should exist or not.
    default: present
    choices: ['present', 'absent']
    type: str

  service_state:
    description:
    - CIFS Server Administrative Status.
    choices: ['stopped', 'started']
    type: str

  name:
    description:
    - Specifies the cifs_server name.
    required: true
    aliases: ['cifs_server_name']
    type: str

  admin_user_name:
    description:
    - Specifies the cifs server admin username.
    - When used with absent, the account will be deleted if admin_password is also provided.
    type: str

  admin_password:
    description:
    - Specifies the cifs server admin password.
    - When used with absent, the account will be deleted if admin_user_name is also provided.
    type: str

  domain:
    description:
    - The Fully Qualified Domain Name of the Windows Active Directory this CIFS server belongs to.
    type: str

  workgroup:
    description:
    -  The NetBIOS name of the domain or workgroup this CIFS server belongs to.
    type: str

  ou:
    description:
    - The Organizational Unit (OU) within the Windows Active Directory
      this CIFS server belongs to.
    version_added: 2.7.0
    type: str

  force:
    type: bool
    description:
    - When state is present, if this is set and a machine account with the same name as
      specified in 'name' exists in the Active Directory, it
      will be overwritten and reused.
    - When state is absent, if this is set, the local CIFS configuration is deleted regardless of communication errors.
    version_added: 2.7.0

  vserver:
    description:
    - The name of the vserver to use.
    required: true
    type: str

'''

EXAMPLES = '''
    - name: Create cifs_server
      netapp.ontap.na_ontap_cifs_server:
        state: present
        name: data2
        vserver: svm1
        service_state: stopped
        domain: "{{ id_domain }}"
        admin_user_name: "{{ domain_login }}"
        admin_password: "{{ domain_pwd }}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Delete cifs_server
      netapp.ontap.na_ontap_cifs_server:
        state: absent
        name: data2
        vserver: svm1
        admin_user_name: "{{ domain_login }}"
        admin_password: "{{ domain_pwd }}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Start cifs_server
      netapp.ontap.na_ontap_cifs_server:
        state: present
        name: data2
        vserver: svm1
        service_state: started
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Stop cifs_server
      netapp.ontap.na_ontap_cifs_server:
        state: present
        name: data2
        vserver: svm1
        service_state: stopped
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

'''

RETURN = '''
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic
HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapcifsServer:
    """
    object to describe  cifs_server info
    """

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            service_state=dict(required=False, choices=['stopped', 'started']),
            name=dict(required=True, type='str', aliases=['cifs_server_name']),
            workgroup=dict(required=False, type='str', default=None),
            domain=dict(required=False, type='str'),
            admin_user_name=dict(required=False, type='str'),
            admin_password=dict(required=False, type='str', no_log=True),
            ou=dict(required=False, type='str'),
            force=dict(required=False, type='bool'),
            vserver=dict(required=True, type='str'),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        self.parameters['cifs_server_name'] = self.parameters['name']
        # Set up Rest API
        self.rest_api = OntapRestAPI(self.module)
        unsupported_rest_properties = ['force', 'workgroup']
        self.use_rest = self.rest_api.is_rest_supported_properties(self.parameters, unsupported_rest_properties)

        if not self.use_rest:
            if HAS_NETAPP_LIB is False:
                self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def get_cifs_server(self):
        """
        Return details about the CIFS-server
        :param:
            name : Name of the name of the cifs_server

        :return: Details about the cifs_server. None if not found.
        :rtype: dict
        """
        cifs_server_info = netapp_utils.zapi.NaElement('cifs-server-get-iter')
        cifs_server_attributes = netapp_utils.zapi.NaElement('cifs-server-config')
        cifs_server_attributes.add_new_child('cifs-server', self.parameters['cifs_server_name'])
        cifs_server_attributes.add_new_child('vserver', self.parameters['vserver'])
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(cifs_server_attributes)
        cifs_server_info.add_child_elem(query)
        result = self.server.invoke_successfully(cifs_server_info, True)
        return_value = None

        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) >= 1:

            cifs_server_attributes = result.get_child_by_name('attributes-list').\
                get_child_by_name('cifs-server-config')
            return_value = {
                'cifs_server_name': self.parameters['cifs_server_name'],
                'administrative-status': cifs_server_attributes.get_child_content('administrative-status')
            }

        return return_value

    def create_cifs_server(self):
        """
        calling zapi to create cifs_server
        """
        options = {'cifs-server': self.parameters['cifs_server_name'], 'administrative-status': 'up'
                   if self.parameters.get('service_state') == 'started' else 'down'}
        if 'workgroup' in self.parameters:
            options['workgroup'] = self.parameters['workgroup']
        if 'domain' in self.parameters:
            options['domain'] = self.parameters['domain']
        if 'admin_user_name' in self.parameters:
            options['admin-username'] = self.parameters['admin_user_name']
        if 'admin_password' in self.parameters:
            options['admin-password'] = self.parameters['admin_password']
        if 'ou' in self.parameters:
            options['organizational-unit'] = self.parameters['ou']
        if 'force' in self.parameters:
            options['force-account-overwrite'] = str(self.parameters['force']).lower()

        cifs_server_create = netapp_utils.zapi.NaElement.create_node_with_children(
            'cifs-server-create', **options)

        try:
            self.server.invoke_successfully(cifs_server_create,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            self.module.fail_json(msg='Error Creating cifs_server %s: %s' %
                                  (self.parameters['cifs_server_name'], to_native(exc)), exception=traceback.format_exc())

    def delete_cifs_server(self):
        """
        calling zapi to create cifs_server
        """
        options = {}
        if 'admin_user_name' in self.parameters:
            options['admin-username'] = self.parameters['admin_user_name']
        if 'admin_password' in self.parameters:
            options['admin-password'] = self.parameters['admin_password']
        if 'force' in self.parameters:
            options['force-account-delete'] = str(self.parameters['force']).lower()

        if options:
            cifs_server_delete = netapp_utils.zapi.NaElement.create_node_with_children('cifs-server-delete', **options)
        else:
            cifs_server_delete = netapp_utils.zapi.NaElement.create_node_with_children('cifs-server-delete')

        try:
            self.server.invoke_successfully(cifs_server_delete,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            self.module.fail_json(msg='Error deleting cifs_server %s: %s' % (self.parameters['cifs_server_name'], to_native(exc)),
                                  exception=traceback.format_exc())

    def start_cifs_server(self):
        """
        RModify the cifs_server.
        """
        cifs_server_modify = netapp_utils.zapi.NaElement.create_node_with_children(
            'cifs-server-start')
        try:
            self.server.invoke_successfully(cifs_server_modify,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as e:
            self.module.fail_json(msg='Error modifying cifs_server %s: %s' % (self.parameters['cifs_server_name'], to_native(e)),
                                  exception=traceback.format_exc())

    def stop_cifs_server(self):
        """
        RModify the cifs_server.
        """
        cifs_server_modify = netapp_utils.zapi.NaElement.create_node_with_children(
            'cifs-server-stop')
        try:
            self.server.invoke_successfully(cifs_server_modify,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as e:
            self.module.fail_json(msg='Error modifying cifs_server %s: %s' % (self.parameters['cifs_server_name'], to_native(e)),
                                  exception=traceback.format_exc())

    def get_cifs_server_rest(self):
        """
        get details of the cifs_server.
        """
        options = {'svm.name': self.parameters['vserver'],
                   'name': self.parameters['cifs_server_name']}
        api = 'protocols/cifs/services'
        fields = 'svm.uuid,enabled'
        record, error = rest_generic.get_one_record(self.rest_api, api, options, fields)
        if error:
            self.module.fail_json(msg="Error on fetching cifs: %s" % error)
        if record:
            record['service_state'] = 'started' if record.pop('enabled') else 'stopped'
        return record

    def service_state_to_bool(self):
        return self.parameters.get('service_state') == 'started'

    def build_ad_domain(self):
        ad_domain = {}
        if 'admin_user_name' in self.parameters:
            ad_domain['user'] = self.parameters['admin_user_name']
        if 'admin_password' in self.parameters:
            ad_domain['password'] = self.parameters['admin_password']
        if 'ou' in self.parameters:
            ad_domain['organizational_unit'] = self.parameters['ou']
        if 'domain' in self.parameters:
            ad_domain['fqdn'] = self.parameters['domain']
        return ad_domain

    def create_cifs_server_rest(self):
        """
        create the cifs_server.
        """
        body = {'svm.name': self.parameters['vserver'],
                'name': self.parameters['cifs_server_name'],
                'enabled': self.service_state_to_bool()}
        ad_domain = self.build_ad_domain()
        if ad_domain:
            body['ad_domain'] = ad_domain
        api = 'protocols/cifs/services'
        dummy, error = rest_generic.post_async(self.rest_api, api, body)
        if error is not None:
            self.module.fail_json(msg="Error on creating cifs: %s" % error)

    def delete_cifs_server_rest(self, current):
        """
        delete the cifs_server.
        """
        ad_domain = self.build_ad_domain()
        body = {'ad_domain': ad_domain} if ad_domain else None
        api = 'protocols/cifs/services'
        dummy, error = rest_generic.delete_async(self.rest_api, api, current['svm']['uuid'], body=body)
        if error is not None:
            self.module.fail_json(msg="Error on deleting cifs server: %s" % error)

    def modify_cifs_server_rest(self, enabled, current):
        """
        Modify the state of CIFS server.
        """
        body = {'enabled': enabled}
        api = 'protocols/cifs/services'
        dummy, error = rest_generic.patch_async(self.rest_api, api, current['svm']['uuid'], body)
        if error is not None:
            self.module.fail_json(msg="Error on modifying cifs server: %s" % error)

    def zapiapply(self):
        """
        calling all cifs_server features
        """

        changed = False
        cifs_server_exists = False
        netapp_utils.ems_log_event("na_ontap_cifs_server", self.server)
        cifs_server_detail = self.get_cifs_server()

        if cifs_server_detail:
            cifs_server_exists = True

            if self.parameters['state'] == 'present':
                administrative_status = cifs_server_detail['administrative-status']
                if self.parameters.get('service_state') == 'started' and administrative_status == 'down':
                    changed = True
                if self.parameters.get('service_state') == 'stopped' and administrative_status == 'up':
                    changed = True
            else:
                # we will delete the CIFs server
                changed = True
        elif self.parameters['state'] == 'present':
            changed = True

        if changed and not self.module.check_mode:
            if self.parameters['state'] == 'present':
                if not cifs_server_exists:
                    self.create_cifs_server()

                elif self.parameters.get('service_state') == 'stopped':
                    self.stop_cifs_server()

                elif self.parameters.get('service_state') == 'started':
                    self.start_cifs_server()

            elif self.parameters['state'] == 'absent':
                self.delete_cifs_server()

        self.module.exit_json(changed=changed)

    def apply(self):
        if not self.use_rest:
            netapp_utils.ems_log_event_cserver("na_ontap_cifs_server", self.server, self.module)
            self.zapiapply()
        current = self.get_cifs_server_rest()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        modify = self.na_helper.get_modified_attributes(current, self.parameters) if cd_action is None else None
        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.create_cifs_server_rest()
            elif cd_action == 'delete':
                self.delete_cifs_server_rest(current)
            elif modify:
                if modify['service_state'] == 'started':
                    self.modify_cifs_server_rest(True, current)
                elif modify['service_state'] == 'stopped':
                    self.modify_cifs_server_rest(False, current)
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    cifs_server = NetAppOntapcifsServer()
    cifs_server.apply()


if __name__ == '__main__':
    main()
