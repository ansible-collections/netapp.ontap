#!/usr/bin/python

# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_export_policy_rule
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''

module: na_ontap_export_policy_rule

short_description: NetApp ONTAP manage export policy rules
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
  - Create or delete or modify export rules in ONTAP

options:
  state:
    description:
      - Whether the specified export policy rule should exist or not.
    required: false
    choices: ['present', 'absent']
    type: str
    default: present

  name:
    description:
      - The name of the export policy this rule will be added to (or modified, or removed from).
    required: True
    type: str
    aliases:
      - policy_name

  client_match:
    description:
      - List of Client Match host names, IP Addresses, Netgroups, or Domains
      - If rule_index is not provided, client_match is used as a key to fetch current rule to determine create,delete,modify actions.
        If a rule with provided client_match exists, a new rule will not be created, but the existing rule will be modified or deleted.
        If a rule with provided client_match doesn't exist, a new rule will be created if state is present.
    type: list
    elements: str

  anonymous_user_id:
    description:
      - User name or ID to which anonymous users are mapped. Default value is '65534'.
    type: str

  ro_rule:
    description:
      - List of Read only access specifications for the rule
    choices: ['any','none','never','krb5','krb5i','krb5p','ntlm','sys']
    type: list
    elements: str

  rw_rule:
    description:
      - List of Read Write access specifications for the rule
    choices: ['any','none','never','krb5','krb5i','krb5p','ntlm','sys']
    type: list
    elements: str

  super_user_security:
    description:
      - List of Read Write access specifications for the rule
    choices: ['any','none','never','krb5','krb5i','krb5p','ntlm','sys']
    type: list
    elements: str

  allow_suid:
    description:
      - If 'true', NFS server will honor SetUID bits in SETATTR operation. Default value on creation is 'true'
    type: bool

  protocol:
    description:
      - List of Client access protocols.
      - Default value is set to 'any' during create.
    choices: [any,nfs,nfs3,nfs4,cifs,flexcache]
    type: list
    elements: str
    aliases:
      - protocols

  rule_index:
    description:
      - index of the export policy rule
    type: int

  vserver:
    description:
      - Name of the vserver to use.
    required: true
    type: str

  ntfs_unix_security:
    description:
      - NTFS export UNIX security options.
      - With REST, supported from ONTAP 9.9.1 version.
    type: str
    choices: ['fail', 'ignore']
    version_added: 21.18.0
'''

EXAMPLES = """
    - name: Create ExportPolicyRule
      netapp.ontap.na_ontap_export_policy_rule:
        state: present
        name: default123
        vserver: ci_dev
        client_match: 0.0.0.0/0,1.1.1.0/24
        ro_rule: krb5,krb5i
        rw_rule: any
        protocol: nfs,nfs3
        super_user_security: any
        anonymous_user_id: 65534
        allow_suid: true
        ntfs_unix_security: ignore
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Modify ExportPolicyRule
      netapp.ontap.na_ontap_export_policy_rule:
        state: present
        name: default123
        rule_index: 100
        client_match: 0.0.0.0/0
        anonymous_user_id: 65521
        ro_rule: ntlm
        rw_rule: any
        protocol: any
        allow_suid: false
        ntfs_unix_security: fail
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Delete ExportPolicyRule
      netapp.ontap.na_ontap_export_policy_rule:
        state: absent
        name: default123
        rule_index: 100
        vserver: ci_dev
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
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule


class NetAppontapExportRule:
    ''' object initialize and class methods '''

    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str', aliases=['policy_name']),
            protocol=dict(required=False,
                          type='list', elements='str', default=None,
                          choices=['any', 'nfs', 'nfs3', 'nfs4', 'cifs', 'flexcache'],
                          aliases=['protocols']),
            client_match=dict(required=False, type='list', elements='str'),
            ro_rule=dict(required=False,
                         type='list', elements='str', default=None,
                         choices=['any', 'none', 'never', 'krb5', 'krb5i', 'krb5p', 'ntlm', 'sys']),
            rw_rule=dict(required=False,
                         type='list', elements='str', default=None,
                         choices=['any', 'none', 'never', 'krb5', 'krb5i', 'krb5p', 'ntlm', 'sys']),
            super_user_security=dict(required=False,
                                     type='list', elements='str', default=None,
                                     choices=['any', 'none', 'never', 'krb5', 'krb5i', 'krb5p', 'ntlm', 'sys']),
            allow_suid=dict(required=False, type='bool'),
            rule_index=dict(required=False, type='int'),
            anonymous_user_id=dict(required=False, type='str'),
            vserver=dict(required=True, type='str'),
            ntfs_unix_security=dict(required=False, type='str', choices=['fail', 'ignore'])
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.set_playbook_zapi_key_map()

        unsupported_rest_properties = ['allow_suid']
        self.rest_api = OntapRestAPI(self.module)
        partially_supported_rest_properties = [['ntfs_unix_security', (9, 9, 1)]]
        self.use_rest = self.rest_api.is_rest_supported_properties(self.parameters, unsupported_rest_properties, partially_supported_rest_properties)
        if not self.use_rest:
            if not netapp_utils.has_netapp_lib():
                self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def set_playbook_zapi_key_map(self):
        self.na_helper.zapi_string_keys = {
            'anonymous_user_id': 'anonymous-user-id',
            'client_match': 'client-match',
            'name': 'policy-name',
            'ntfs_unix_security': 'export-ntfs-unix-security-ops'
        }
        self.na_helper.zapi_list_keys = {
            'protocol': ('protocol', 'access-protocol'),
            'ro_rule': ('ro-rule', 'security-flavor'),
            'rw_rule': ('rw-rule', 'security-flavor'),
            'super_user_security': ('super-user-security', 'security-flavor'),
        }
        self.na_helper.zapi_bool_keys = {
            'allow_suid': 'is-allow-set-uid-enabled'
        }
        self.na_helper.zapi_int_keys = {
            'rule_index': 'rule-index'
        }

    def set_query_parameters(self):
        """
        Return dictionary of query parameters and
        :return:
        """
        query = {
            'policy-name': self.parameters['name'],
            'vserver': self.parameters['vserver']
        }

        if self.parameters.get('rule_index'):
            query['rule-index'] = self.parameters['rule_index']
        elif self.parameters.get('client_match'):
            query['client-match'] = self.parameters['client_match']
        else:
            self.module.fail_json(
                msg="Need to specify at least one of the rule_index and client_match option.")

        return {
            'query': {
                'export-rule-info': query
            }
        }

    def get_export_policy_rule(self):
        """
        Return details about the export policy rule
        :param:
            name : Name of the export_policy
        :return: Details about the export_policy. None if not found.
        :rtype: dict
        """
        if self.use_rest:
            return self.get_export_policy_rule_rest()
        current, result = None, None
        rule_iter = netapp_utils.zapi.NaElement('export-rule-get-iter')
        rule_iter.translate_struct(self.set_query_parameters())
        try:
            result = self.server.invoke_successfully(rule_iter, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error getting export policy rule %s: %s'
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        if result is not None and \
                result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) >= 1:
            current = dict()
            rule_info = result.get_child_by_name('attributes-list').get_child_by_name('export-rule-info')
            for item_key, zapi_key in self.na_helper.zapi_string_keys.items():
                current[item_key] = rule_info.get_child_content(zapi_key)
            for item_key, zapi_key in self.na_helper.zapi_bool_keys.items():
                current[item_key] = self.na_helper.get_value_for_bool(from_zapi=True,
                                                                      value=rule_info[zapi_key])
            for item_key, zapi_key in self.na_helper.zapi_int_keys.items():
                current[item_key] = self.na_helper.get_value_for_int(from_zapi=True,
                                                                     value=rule_info[zapi_key])
            for item_key, zapi_key in self.na_helper.zapi_list_keys.items():
                parent, dummy = zapi_key
                current[item_key] = self.na_helper.get_value_for_list(from_zapi=True,
                                                                      zapi_parent=rule_info.get_child_by_name(parent))
            current['num_records'] = int(result.get_child_content('num-records'))
            if not self.parameters.get('rule_index'):
                self.parameters['rule_index'] = current['rule_index']
        return current

    def get_export_policy(self):
        """
        Return details about the export-policy
        :param:
            name : Name of the export-policy

        :return: Details about the export-policy. None if not found.
        :rtype: dict
        """
        if self.use_rest:
            return self.get_export_policy_rest()
        export_policy_iter = netapp_utils.zapi.NaElement('export-policy-get-iter')
        attributes = {
            'query': {
                'export-policy-info': {
                    'policy-name': self.parameters['name'],
                    'vserver': self.parameters['vserver']
                }
            }
        }

        export_policy_iter.translate_struct(attributes)
        try:
            result = self.server.invoke_successfully(export_policy_iter, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error getting export policy %s: %s'
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) == 1:
            return result

        return None

    def add_parameters_for_create_or_modify(self, na_element_object, values):
        """
            Add children node for create or modify NaElement object
            :param na_element_object: modify or create NaElement object
            :param values: dictionary of cron values to be added
            :return: None
        """
        for key in values:
            if key in self.na_helper.zapi_string_keys:
                zapi_key = self.na_helper.zapi_string_keys.get(key)
                na_element_object[zapi_key] = values[key]
            elif key in self.na_helper.zapi_list_keys:
                parent_key, child_key = self.na_helper.zapi_list_keys.get(key)
                na_element_object.add_child_elem(self.na_helper.get_value_for_list(from_zapi=False,
                                                                                   zapi_parent=parent_key,
                                                                                   zapi_child=child_key,
                                                                                   data=values[key]))
            elif key in self.na_helper.zapi_int_keys:
                zapi_key = self.na_helper.zapi_int_keys.get(key)
                na_element_object[zapi_key] = self.na_helper.get_value_for_int(from_zapi=False,
                                                                               value=values[key])
            elif key in self.na_helper.zapi_bool_keys:
                zapi_key = self.na_helper.zapi_bool_keys.get(key)
                na_element_object[zapi_key] = self.na_helper.get_value_for_bool(from_zapi=False,
                                                                                value=values[key])

    def create_export_policy_rule(self, policy_id=None):
        """
        create rule for the export policy.
        """
        for key in ['client_match', 'ro_rule', 'rw_rule']:
            if self.parameters.get(key) is None:
                self.module.fail_json(msg='Error: Missing required param for creating export policy rule %s' % key)
        if self.use_rest:
            return self.create_export_policy_rule_rest(policy_id['id'])
        export_rule_create = netapp_utils.zapi.NaElement('export-rule-create')
        self.add_parameters_for_create_or_modify(export_rule_create, self.parameters)
        try:
            self.server.invoke_successfully(export_rule_create, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating export policy rule %s: %s'
                                  % (self.parameters['name'], to_native(error)), exception=traceback.format_exc())

    def create_export_policy(self):
        """
        Creates an export policy
        """
        if self.use_rest:
            return self.create_export_policy_rest()
        export_policy_create = netapp_utils.zapi.NaElement.create_node_with_children(
            'export-policy-create', **{'policy-name': self.parameters['name']})
        try:
            self.server.invoke_successfully(export_policy_create,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating export-policy %s: %s'
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def delete_export_policy_rule(self, rule_index, policy_id=None):
        """
        delete rule for the export policy.
        """
        if self.use_rest:
            return self.delete_export_policy_rule_rest(rule_index, policy_id['id'])
        export_rule_delete = netapp_utils.zapi.NaElement.create_node_with_children(
            'export-rule-destroy', **{'policy-name': self.parameters['name'],
                                      'rule-index': str(rule_index)})

        try:
            self.server.invoke_successfully(export_rule_delete,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting export policy rule %s: %s'
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_export_policy_rule(self, params, policy_id=None, rule_index=None):
        '''
        Modify an existing export policy rule
        :param params: dict() of attributes with desired values
        :return: None
        '''
        if self.use_rest:
            return self.modify_export_policy_rule_rest(params, policy_id['id'], rule_index)
        export_rule_modify = netapp_utils.zapi.NaElement.create_node_with_children(
            'export-rule-modify', **{'policy-name': self.parameters['name'],
                                     'rule-index': str(self.parameters['rule_index'])})
        self.add_parameters_for_create_or_modify(export_rule_modify, params)
        try:
            self.server.invoke_successfully(export_rule_modify, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying allow_suid %s: %s'
                                  % (self.parameters['allow_suid'], to_native(error)),
                                  exception=traceback.format_exc())

    def autosupport_log(self):
        netapp_utils.ems_log_event("na_ontap_export_policy_rules", self.server)

    def get_export_policy_rest(self):
        options = {'fields': 'name,id',
                   'svm.name': self.parameters['vserver'],
                   'name': self.parameters['name']}
        api = 'protocols/nfs/export-policies'
        record, error = rest_generic.get_one_record(self.rest_api, api, options)
        if error:
            self.module.fail_json(msg="Error on fetching export policy: %s" % error)
        return record

    def get_export_policy_rule_rest(self):
        policy = self.get_export_policy_rest()
        if not policy:
            return None
        if self.parameters.get('rule_index') is None:
            return self.get_export_policy_rule_without_index(policy)
        options = {'fields': 'anonymous_user,clients,index,protocols,ro_rule,rw_rule,superuser'}
        if 'ntfs_unix_security' in self.parameters:
            options['fields'] += ',ntfs_unix_security'
        api = 'protocols/nfs/export-policies/%s/rules/%s' % (policy['id'], self.parameters['rule_index'])
        record, error = rest_generic.get_one_record(self.rest_api, api, options)
        if error:
            # If rule index passed in doesn't exist, return None
            if "entry doesn't exist" in error:
                return None
            self.module.fail_json(msg="Error on fetching export policy rule: %s" % error)
        if not record:
            return None
        return self.filter_get_results(record)

    def get_export_policy_rule_without_index(self, policy):
        options = {'fields': 'anonymous_user,clients,index,protocols,ro_rule,rw_rule,superuser'}
        if 'ntfs_unix_security' in self.parameters:
            options['fields'] += ',ntfs_unix_security'
        api = 'protocols/nfs/export-policies/%s/rules' % policy['id']
        records, error = rest_generic.get_0_or_more_records(self.rest_api, api, options)
        if error:
            self.module.fail_json(msg="Error on fetching export policy rule: %s" % error)
        if not records:
            return None
        return_records = {}
        for record in records:
            for match in record.get('clients', []):
                if match['match'] in self.parameters['client_match']:
                    return_records[record['index']] = record
        if not return_records:
            return None
        if len(return_records) > 1:
            self.module.fail_json(msg="More than one export policy rule match client match: %s found the following %s" %
                                      (self.parameters['client_match'],
                                       str(return_records)))
        record = self.filter_get_results(list(return_records.values())[0])
        return record

    def filter_get_results(self, record):
        record['rule_index'] = record.pop('index')
        record['anonymous_user_id'] = record.pop('anonymous_user')
        record['protocol'] = record.pop('protocols')
        record['super_user_security'] = record.pop('superuser')
        record['client_match'] = ','.join(each['match'] for each in record['clients'])
        record.pop('clients')
        return record

    def create_export_policy_rest(self):
        body = {'name': self.parameters['name'], 'svm.name': self.parameters['vserver']}
        api = 'protocols/nfs/export-policies'
        dummy, error = rest_generic.post_async(self.rest_api, api, body)
        if error is not None:
            self.module.fail_json(msg="Error on creating export policy: %s" % error)

    def create_export_policy_rule_rest(self, policy_id):
        body = {'clients': self.client_match_format(self.parameters['client_match']),
                'ro_rule': self.parameters['ro_rule'],
                'rw_rule': self.parameters['rw_rule']}
        if self.parameters.get('anonymous_user_id'):
            body['anonymous_user'] = self.parameters['anonymous_user_id']
        if self.parameters.get('protocol'):
            body['protocols'] = self.parameters['protocol']
        if self.parameters.get('super_user_security'):
            body['superuser'] = self.parameters['super_user_security']
        if self.parameters.get('ntfs_unix_security'):
            body['ntfs_unix_security'] = self.parameters['ntfs_unix_security']
        api = 'protocols/nfs/export-policies/%s/rules' % str(policy_id)
        dummy, error = rest_generic.post_async(self.rest_api, api, body)
        if error:
            self.module.fail_json(msg="Error on creating export policy Rule: %s" % error)

    def client_match_format(self, client_match):
        client_match = client_match.split(',')
        return [{'match': each} for each in client_match]

    def delete_export_policy_rule_rest(self, rule_index, policy_id):
        api = 'protocols/nfs/export-policies/%s/rules' % str(policy_id)
        dummy, error = rest_generic. delete_async(self.rest_api, api, rule_index)
        if error:
            self.module.fail_json(msg="Error on deleting export policy Rule: %s" % error)

    def modify_export_policy_rule_rest(self, params, policy_id, rule_index):
        body = {}
        if params.get('anonymous_user_id'):
            body['anonymous_user'] = self.parameters['anonymous_user_id']
        if params.get('protocol'):
            body['protocols'] = self.parameters['protocol']
        if params.get('super_user_security'):
            body['superuser'] = self.parameters['super_user_security']
        if params.get('client_match'):
            body['clients'] = self.client_match_format(self.parameters['client_match'])
        if params.get('ro_rule'):
            body['ro_rule'] = self.parameters['ro_rule']
        if params.get('rw_rule'):
            body['rw_rule'] = self.parameters['rw_rule']
        if params.get('ntfs_unix_security'):
            body['ntfs_unix_security'] = self.parameters['ntfs_unix_security']
        api = 'protocols/nfs/export-policies/%s/rules' % str(policy_id)
        dummy, error = rest_generic. patch_async(self.rest_api, api, rule_index, body)
        if error:
            self.module.fail_json(msg="Error on modifying export policy Rule: %s" % error)

    def apply(self):
        ''' Apply required action from the play'''
        if not self.use_rest:
            self.autosupport_log()
            # convert client_match list to comma-separated string
        if self.parameters.get('client_match') is not None:
            self.parameters['client_match'] = ','.join(self.parameters['client_match'])
            self.parameters['client_match'] = self.parameters['client_match'].replace(' ', '')
        current, modify = self.get_export_policy_rule(), None
        current_policy = self.get_export_policy()
        # rule_index can be modified in Zapi, but can't be modified in REST
        if current and self.use_rest:
            current_filters = current.copy()
            current_filters.pop('rule_index')
        else:
            current_filters = current
        action = self.na_helper.get_cd_action(current_filters, self.parameters)
        if action is None and self.parameters['state'] == 'present':
            modify = self.na_helper.get_modified_attributes(current, self.parameters)

        if self.na_helper.changed and not self.module.check_mode:
            # create export policy (if policy doesn't exist) only when changed=True
            if action == 'create':
                if not current_policy:
                    self.create_export_policy()
                    current_policy = self.get_export_policy()
                self.create_export_policy_rule(current_policy)
            elif action == 'delete':
                if self.use_rest:
                    self.delete_export_policy_rule(current['rule_index'], current_policy)
                elif current['num_records'] > 1:
                    self.module.fail_json(msg='Multiple export policy rules exist.'
                                              'Please specify a rule_index to delete')
                else:
                    self.delete_export_policy_rule(current['rule_index'])
            elif modify:
                self.modify_export_policy_rule(modify, current_policy, current['rule_index'])

        self.module.exit_json(changed=self.na_helper.changed)


def main():
    ''' Create object and call apply '''
    rule_obj = NetAppontapExportRule()
    rule_obj.apply()


if __name__ == '__main__':
    main()
