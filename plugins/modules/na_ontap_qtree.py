#!/usr/bin/python

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_qtree
'''

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''

module: na_ontap_qtree

short_description: NetApp ONTAP manage qtrees
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
- Create or destroy Qtrees.

options:

  state:
    description:
    - Whether the specified qtree should exist or not.
    choices: ['present', 'absent']
    type: str
    default: 'present'

  name:
    description:
    - The name of the qtree to manage.
    required: true
    type: str

  from_name:
    description:
    - Name of the qtree to be renamed.
    version_added: 2.7.0
    type: str

  flexvol_name:
    description:
    - The name of the FlexVol the qtree should exist on.
    required: true
    type: str

  vserver:
    description:
    - The name of the vserver to use.
    required: true
    type: str

  export_policy:
    description:
    - The name of the export policy to apply.
    version_added: 2.9.0
    type: str

  security_style:
    description:
    - The security style for the qtree.
    choices: ['unix', 'ntfs', 'mixed']
    type: str
    version_added: 2.9.0

  oplocks:
    description:
    - Whether the oplocks should be enabled or not for the qtree.
    choices: ['enabled', 'disabled']
    type: str
    version_added: 2.9.0

  unix_permissions:
    description:
    - File permissions bits of the qtree.
    version_added: 2.9.0
    type: str

  force_delete:
    description:
      - Whether the qtree should be deleted even if files still exist.
      - Note that the default of true reflect the REST API behavior.
      - a value of false is not supported with REST.
    type: bool
    default: true
    version_added: 20.8.0

  wait_for_completion:
    description:
      - Only applicable for REST.  When using ZAPI, the deletion is always synchronous.
      - Deleting a qtree may take time if many files need to be deleted.
      - Set this parameter to 'true' for synchronous execution during delete.
      - Set this parameter to 'false' for asynchronous execution.
      - For asynchronous, execution exits as soon as the request is sent, and the qtree is deleted in background.
    type: bool
    default: true
    version_added: 2.9.0

  time_out:
    description:
      - Maximum time to wait for qtree deletion in seconds when wait_for_completion is True.
      - Error out if task is not completed in defined time.
      - Default is set to 3 minutes.
    default: 180
    type: int
    version_added: 2.9.0
'''

EXAMPLES = """
- name: Create Qtrees
  na_ontap_qtree:
    state: present
    name: ansibleQTree
    flexvol_name: ansibleVolume
    export_policy: policyName
    security_style: mixed
    oplocks: disabled
    unix_permissions:
    vserver: ansibleVServer
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"

- name: Rename Qtrees
  na_ontap_qtree:
    state: present
    from_name: ansibleQTree_rename
    name: ansibleQTree
    flexvol_name: ansibleVolume
    vserver: ansibleVServer
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
"""

RETURN = """

"""
import datetime
import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapQTree(object):
    '''Class with qtree operations'''

    def __init__(self):
        self.use_rest = False
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str'),
            from_name=dict(required=False, type='str'),
            flexvol_name=dict(required=True, type='str'),
            vserver=dict(required=True, type='str'),
            export_policy=dict(required=False, type='str'),
            security_style=dict(required=False, type='str', choices=['unix', 'ntfs', 'mixed']),
            oplocks=dict(required=False, type='str', choices=['enabled', 'disabled']),
            unix_permissions=dict(required=False, type='str'),
            force_delete=dict(required=False, type='bool', default=True),
            wait_for_completion=dict(required=False, type='bool', default=True),
            time_out=dict(required=False, type='int', default=180),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            required_if=[
                ('state', 'present', ['flexvol_name'])
            ],
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        self.rest_api = OntapRestAPI(self.module)
        if self.rest_api.is_rest():
            self.use_rest = True
        else:
            if HAS_NETAPP_LIB is False:
                self.module.fail_json(
                    msg="the python NetApp-Lib module is required")
            else:
                self.server = netapp_utils.setup_na_ontap_zapi(
                    module=self.module, vserver=self.parameters['vserver'])

    def get_qtree(self, name=None):
        """
        Checks if the qtree exists.
        :param:
            name : qtree name
        :return:
            Details about the qtree
            False if qtree is not found
        :rtype: bool
        """
        if name is None:
            name = self.parameters['name']
        if self.use_rest:
            api = "storage/qtrees"
            query = {'fields': 'export_policy,unix_permissions,security_style,volume',
                     'svm.name': self.parameters['vserver'],
                     'volume': self.parameters['flexvol_name'],
                     'name': name}
            message, error = self.rest_api.get(api, query)
            if error:
                self.module.fail_json(msg=error)
            if len(message.keys()) == 0:
                return None
            elif 'records' in message and len(message['records']) == 0:
                return None
            elif 'records' not in message:
                error = "Unexpected response in get_qtree from %s: %s" % (api, repr(message))
                self.module.fail_json(msg=error)
            return message['records'][0]
        else:
            qtree_list_iter = netapp_utils.zapi.NaElement('qtree-list-iter')
            query_details = netapp_utils.zapi.NaElement.create_node_with_children(
                'qtree-info', **{'vserver': self.parameters['vserver'],
                                 'volume': self.parameters['flexvol_name'],
                                 'qtree': name})
            query = netapp_utils.zapi.NaElement('query')
            query.add_child_elem(query_details)
            qtree_list_iter.add_child_elem(query)
            result = self.server.invoke_successfully(qtree_list_iter,
                                                     enable_tunneling=True)
            return_q = None
            if (result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) >= 1):
                return_q = {'export_policy': result['attributes-list']['qtree-info']['export-policy'],
                            'oplocks': result['attributes-list']['qtree-info']['oplocks'],
                            'security_style': result['attributes-list']['qtree-info']['security-style']}

                if result['attributes-list']['qtree-info'].get_child_by_name('mode'):
                    return_q['unix_permissions'] = result['attributes-list']['qtree-info']['mode']
                else:
                    return_q['unix_permissions'] = ''

            return return_q

    def create_qtree(self):
        """
        Create a qtree
        """
        if self.use_rest:
            api = "storage/qtrees"
            body = {'name': self.parameters['name'], 'volume': {'name': self.parameters['flexvol_name']},
                    'svm': {'name': self.parameters['vserver']}}
            if self.parameters.get('export_policy'):
                body['export_policy'] = self.parameters['export_policy']
            if self.parameters.get('security_style'):
                body['security_style'] = self.parameters['security_style']
            if self.parameters.get('unix_permissions'):
                body['unix_permissions'] = self.parameters['unix_permissions']
            __, error = self.rest_api.post(api, body)
            if error:
                self.module.fail_json(msg=error)
        else:
            options = {'qtree': self.parameters['name'], 'volume': self.parameters['flexvol_name']}
            if self.parameters.get('export_policy'):
                options['export-policy'] = self.parameters['export_policy']
            if self.parameters.get('security_style'):
                options['security-style'] = self.parameters['security_style']
            if self.parameters.get('oplocks'):
                options['oplocks'] = self.parameters['oplocks']
            if self.parameters.get('unix_permissions'):
                options['mode'] = self.parameters['unix_permissions']
            qtree_create = netapp_utils.zapi.NaElement.create_node_with_children(
                'qtree-create', **options)
            try:
                self.server.invoke_successfully(qtree_create,
                                                enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg="Error provisioning qtree %s: %s"
                                      % (self.parameters['name'], to_native(error)),
                                      exception=traceback.format_exc())

    def delete_qtree(self, current):
        """
        Delete a qtree
        """
        if self.use_rest:
            uuid = current['volume']['uuid']
            qid = str(current['id'])
            api = "storage/qtrees/%s/%s" % (uuid, qid)
            query = {'return_timeout': 3}
            response, error = self.rest_api.delete(api, params=query)
            if error:
                self.module.fail_json(msg=error)
            if 'job' in response and self.parameters['wait_for_completion']:
                message, error = self.rest_api.wait_on_job(response['job'], timeout=self.parameters['time_out'], increment=10)
                if error:
                    self.module.fail_json(msg="%s" % error)

        else:
            path = '/vol/%s/%s' % (self.parameters['flexvol_name'], self.parameters['name'])
            options = {'qtree': path}
            if self.parameters['force_delete']:
                options['force'] = "true"
            qtree_delete = netapp_utils.zapi.NaElement.create_node_with_children(
                'qtree-delete', **options)

            try:
                self.server.invoke_successfully(qtree_delete,
                                                enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg="Error deleting qtree %s: %s" % (path, to_native(error)),
                                      exception=traceback.format_exc())

    def rename_qtree(self, current):
        """
        Rename a qtree
        """
        if self.use_rest:
            body = {'name': self.parameters['name']}
            uuid = current['volume']['uuid']
            qid = str(current['id'])
            api = "storage/qtrees/%s/%s" % (uuid, qid)
            dummy, error = self.rest_api.patch(api, body)
            if error:
                self.module.fail_json(msg=error)
        else:
            path = '/vol/%s/%s' % (self.parameters['flexvol_name'], self.parameters['from_name'])
            new_path = '/vol/%s/%s' % (self.parameters['flexvol_name'], self.parameters['name'])
            qtree_rename = netapp_utils.zapi.NaElement.create_node_with_children(
                'qtree-rename', **{'qtree': path,
                                   'new-qtree-name': new_path})

            try:
                self.server.invoke_successfully(qtree_rename,
                                                enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg="Error renaming qtree %s: %s"
                                      % (self.parameters['from_name'], to_native(error)),
                                      exception=traceback.format_exc())

    def modify_qtree(self, current):
        """
        Modify a qtree
        """
        if self.use_rest:
            now = datetime.datetime.now()
            body = {}
            if self.parameters.get('security_style'):
                body['security_style'] = self.parameters['security_style']
            if self.parameters.get('unix_permissions'):
                body['unix_permissions'] = self.parameters['unix_permissions']
            if self.parameters.get('export_policy'):
                body['export_policy'] = {'name': self.parameters['export_policy']}
            uuid = current['volume']['uuid']
            qid = str(current['id'])
            api = "storage/qtrees/%s/%s" % (uuid, qid)
            timeout = 120
            query = {'return_timeout': timeout}
            dummy, error = self.rest_api.patch(api, body, query)

            later = datetime.datetime.now()
            time_elapsed = later - now
            # modify will not return any error if return_timeout is 0, so we set it to 120 seconds as default
            if time_elapsed.seconds > (timeout - 1):
                self.module.fail_json(msg="Too long to run")
            if error:
                self.module.fail_json(msg=error)
        else:
            options = {'qtree': self.parameters['name'], 'volume': self.parameters['flexvol_name']}
            if self.parameters.get('export_policy'):
                options['export-policy'] = self.parameters['export_policy']
            if self.parameters.get('security_style'):
                options['security-style'] = self.parameters['security_style']
            if self.parameters.get('oplocks'):
                options['oplocks'] = self.parameters['oplocks']
            if self.parameters.get('unix_permissions'):
                options['mode'] = self.parameters['unix_permissions']
            qtree_modify = netapp_utils.zapi.NaElement.create_node_with_children(
                'qtree-modify', **options)
            try:
                self.server.invoke_successfully(qtree_modify, enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error modifying qtree %s: %s'
                                      % (self.parameters['name'], to_native(error)),
                                      exception=traceback.format_exc())

    def apply(self):
        '''Call create/delete/modify/rename operations'''
        if not self.use_rest:
            netapp_utils.ems_log_event("na_ontap_qtree", self.server)
        current = self.get_qtree()
        rename, cd_action, modify = None, None, None
        if self.parameters.get('from_name'):
            from_qtree = self.get_qtree(self.parameters['from_name'])
            rename = self.na_helper.is_rename_action(from_qtree, current)
            if rename is None:
                self.module.fail_json(msg='Error renaming: qtree %s does not exist' % self.parameters['from_name'])
            if rename:
                current = from_qtree
        else:
            cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action is None and self.parameters['state'] == 'present':
            if self.parameters.get('security_style') and self.parameters['security_style'] != current['security_style']:
                modify = True
            if self.parameters.get('unix_permissions') and \
                    self.parameters['unix_permissions'] != str(current['unix_permissions']):
                modify = True
            # rest and zapi handle export policy differently
            if self.use_rest:
                if self.parameters.get('export_policy') and \
                        self.parameters['export_policy'] != current['export_policy']['name']:
                    modify = True
            else:
                if self.parameters.get('export_policy') and \
                        self.parameters['export_policy'] != current['export_policy']:
                    modify = True
        if self.use_rest and cd_action == 'delete' and not self.parameters['force_delete']:
            self.module.fail_json(msg='Error: force_delete option is not supported for REST, unless set to true.')

        if modify:
            self.na_helper.changed = True
        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if cd_action == 'create':
                    self.create_qtree()
                elif cd_action == 'delete':
                    self.delete_qtree(current)
                else:
                    if rename:
                        self.rename_qtree(current)
                    if modify:
                        self.modify_qtree(current)
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    '''Apply qtree operations from playbook'''
    qtree_obj = NetAppOntapQTree()
    qtree_obj.apply()


if __name__ == '__main__':
    main()
