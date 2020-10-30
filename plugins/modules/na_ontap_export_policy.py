#!/usr/bin/python

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_export_policy
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
module: na_ontap_export_policy
short_description: NetApp ONTAP manage export-policy
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Create or destroy or rename export-policies on ONTAP
options:
  state:
    description:
    - Whether the specified export policy should exist or not.
    choices: ['present', 'absent']
    type: str
    default: present
  name:
    description:
    - The name of the export-policy to manage.
    type: str
    required: true
  from_name:
    description:
    - The name of the export-policy to be renamed.
    type: str
    version_added: 2.7.0
  vserver:
    required: true
    type: str
    description:
    - Name of the vserver to use.
'''

EXAMPLES = """
    - name: Create Export Policy
      na_ontap_export_policy:
        state: present
        name: ansiblePolicyName
        vserver: vs_hack
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Rename Export Policy
      na_ontap_export_policy:
        action: present
        from_name: ansiblePolicyName
        vserver: vs_hack
        name: newPolicyName
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
    - name: Delete Export Policy
      na_ontap_export_policy:
        state: absent
        name: ansiblePolicyName
        vserver: vs_hack
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
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppONTAPExportPolicy(object):
    """
    Class with export policy methods
    """

    def __init__(self):
        self.use_rest = False
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str'),
            from_name=dict(required=False, type='str', default=None),
            vserver=dict(required=True, type='str')
        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        self.rest_api = OntapRestAPI(self.module)
        if self.rest_api.is_rest():
            self.use_rest = True
        else:
            if HAS_NETAPP_LIB is False:
                self.module.fail_json(msg="the python NetApp-Lib module is required")
            else:
                self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def get_export_policy(self, name=None, uuid=None):
        """
        Return details about the export-policy
        :param:
            name : Name of the export-policy
        :return: Details about the export-policy. None if not found.
        :rtype: dict
        """
        if name is None:
            name = self.parameters['name']
        if self.use_rest:
            params = {'fields': 'name',
                      'name': name,
                      'svm.uuid': uuid}
            api = 'protocols/nfs/export-policies/'
            message, error = self.rest_api.get(api, params)
            if error is not None:
                self.module.fail_json(msg="Error on fetching export policy: %s" % error)
            if message['num_records'] > 0:
                return {'policy-name': message['records'][0]['name']}
            else:
                return None

        else:
            export_policy_iter = netapp_utils.zapi.NaElement('export-policy-get-iter')
            export_policy_info = netapp_utils.zapi.NaElement('export-policy-info')
            export_policy_info.add_new_child('policy-name', name)
            export_policy_info.add_new_child('vserver', self.parameters['vserver'])
            query = netapp_utils.zapi.NaElement('query')
            query.add_child_elem(export_policy_info)
            export_policy_iter.add_child_elem(query)
            result = self.server.invoke_successfully(export_policy_iter, True)
            return_value = None
            # check if query returns the expected export-policy
            if result.get_child_by_name('num-records') and \
                    int(result.get_child_content('num-records')) == 1:

                export_policy = result.get_child_by_name('attributes-list').get_child_by_name('export-policy-info').get_child_by_name('policy-name')
                return_value = {
                    'policy-name': export_policy
                }
            return return_value

    def create_export_policy(self, uuid=None):
        """
        Creates an export policy
        """
        if self.use_rest:
            params = {'name': self.parameters['name'],
                      'svm.uuid': uuid}
            api = 'protocols/nfs/export-policies'
            dummy, error = self.rest_api.post(api, params)
            if error is not None:
                self.module.fail_json(msg="Error on creating export policy: %s" % error)
        else:
            export_policy_create = netapp_utils.zapi.NaElement.create_node_with_children(
                'export-policy-create', **{'policy-name': self.parameters['name']})
            try:
                self.server.invoke_successfully(export_policy_create,
                                                enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error on creating export-policy %s: %s'
                                      % (self.parameters['name'], to_native(error)),
                                      exception=traceback.format_exc())

    def delete_export_policy(self, policy_id=None):
        """
        Delete export-policy
        """
        if self.use_rest:
            api = 'protocols/nfs/export-policies/' + str(policy_id)
            dummy, error = self.rest_api.delete(api)
            if error is not None:
                self.module.fail_json(msg=" Error on deleting export policy: %s" % error)
        else:
            export_policy_delete = netapp_utils.zapi.NaElement.create_node_with_children(
                'export-policy-destroy', **{'policy-name': self.parameters['name'], })
            try:
                self.server.invoke_successfully(export_policy_delete,
                                                enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error on deleting export-policy %s: %s'
                                      % (self.parameters['name'],
                                         to_native(error)), exception=traceback.format_exc())

    def rename_export_policy(self, policy_id=None):
        """
        Rename the export-policy.
        """
        if self.use_rest:
            params = {'name': self.parameters['name']}
            api = 'protocols/nfs/export-policies/' + str(policy_id)
            dummy, error = self.rest_api.patch(api, params)
            if error is not None:
                self.module.fail_json(msg="Error on renaming export policy: %s" % error)
        else:
            export_policy_rename = netapp_utils.zapi.NaElement.create_node_with_children(
                'export-policy-rename', **{'policy-name': self.parameters['from_name'],
                                           'new-policy-name': self.parameters['name']})
            try:
                self.server.invoke_successfully(export_policy_rename,
                                                enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error on renaming export-policy %s:%s'
                                      % (self.parameters['name'], to_native(error)),
                                      exception=traceback.format_exc())

    def get_export_policy_id(self, name=None):
        """
        Get a export policy's id
        :return: id of the export policy
        """
        if name is None:
            name = self.parameters['name']

        params = {'fields': 'id',
                  'svm.name': self.parameters['vserver'],
                  'name': name
                  }
        api = 'protocols/nfs/export-policies'
        message, error = self.rest_api.get(api, params)
        if error is not None:
            self.module.fail_json(msg="%s" % error)
        if message['num_records'] == 0:
            return None
        else:
            return message['records'][0]['id']

    def get_export_policy_svm_uuid(self):
        """
        Get a svm's uuid
        :return: uuid of the svm
        """
        params = {'svm.name': self.parameters['vserver']}
        api = 'protocols/nfs/export-policies'
        message, error = self.rest_api.get(api, params)
        if error is not None:
            self.module.fail_json(msg="%s" % error)
        return message['records'][0]['svm']['uuid']

    def apply(self):
        """
        Apply action to export-policy
        """
        policy_id, uuid = None, None
        cd_action, rename = None, None

        if not self.use_rest:
            netapp_utils.ems_log_event("na_ontap_export_policy", self.server)
        if self.use_rest:
            uuid = self.get_export_policy_svm_uuid()
            if self.parameters.get('from_name'):
                policy_id = self.get_export_policy_id(self.parameters['from_name'])
            else:
                policy_id = self.get_export_policy_id()

        current = self.get_export_policy(uuid=uuid)

        if self.parameters.get('from_name'):
            rename = self.na_helper.is_rename_action(self.get_export_policy(self.parameters['from_name']), current)
            if rename is None:
                self.module.fail_json(msg="Error renaming: export policy %s does not exist" % self.parameters['from_name'])
        else:
            cd_action = self.na_helper.get_cd_action(current, self.parameters)

        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if rename:
                    self.rename_export_policy(policy_id=policy_id)
                elif cd_action == 'create':
                    self.create_export_policy(uuid=uuid)
                elif cd_action == 'delete':
                    self.delete_export_policy(policy_id=policy_id)
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """
    Execute action
    """
    export_policy = NetAppONTAPExportPolicy()
    export_policy.apply()


if __name__ == '__main__':
    main()
