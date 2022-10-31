#!/usr/bin/python

# (c) 2019-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_snapmirror_policy
'''

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = """
module: na_ontap_snapmirror_policy
short_description: NetApp ONTAP create, delete or modify SnapMirror policies
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '20.3.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - NetApp ONTAP create, modify, or destroy the SnapMirror policy
  - Add, modify and remove SnapMirror policy rules
  - Following parameters are not supported in REST; 'owner', 'restart', 'transfer_priority', 'tries', 'ignore_atime', 'common_snapshot_schedule'
options:
  state:
    description:
      - Whether the specified SnapMirror policy should exist or not.
    choices: ['present', 'absent']
    default: present
    type: str
  vserver:
    description:
      - Specifies the vserver for the SnapMirror policy.
    required: true
    type: str
  policy_name:
    description:
      - Specifies the SnapMirror policy name.
      - C(name) added as an alias in 22.0.0.
    required: true
    type: str
    aliases: ['name']
    version_added: '22.0.0'
  policy_type:
    description:
      - Specifies the SnapMirror policy type. Modifying the type of an existing SnapMirror policy is not supported
    choices: ['vault', 'async_mirror', 'mirror_vault', 'strict_sync_mirror', 'sync_mirror']
    type: str
  comment:
    description:
      - Specifies the SnapMirror policy comment.
    type: str
  tries:
    description:
      - Specifies the number of tries.
    type: str
  transfer_priority:
    description:
      - Specifies the priority at which a SnapMirror transfer runs.
    choices: ['low', 'normal']
    type: str
  common_snapshot_schedule:
    description:
      - Specifies the common Snapshot copy schedule associated with the policy, only required for strict_sync_mirror and sync_mirror.
    type: str
  owner:
    description:
      - Specifies the owner of the SnapMirror policy.
    choices: ['cluster_admin', 'vserver_admin']
    type: str
  is_network_compression_enabled:
    description:
      - Specifies whether network compression is enabled for transfers.
    type: bool
  ignore_atime:
    description:
      - Specifies whether incremental transfers will ignore files which have only their access time changed. Applies to SnapMirror vault relationships only.
    type: bool
  restart:
    description:
      - Defines the behavior of SnapMirror if an interrupted transfer exists, applies to data protection only.
    choices: ['always', 'never', 'default']
    type: str
  snapmirror_label:
    description:
      - SnapMirror policy rule label.
      - Required when defining policy rules.
      - Use an empty list to remove all user-defined rules.
    type: list
    elements: str
    version_added: '20.7.0'
  keep:
    description:
      - SnapMirror policy rule retention count for snapshots created.
      - Required when defining policy rules.
    type: list
    elements: int
    version_added: '20.7.0'
  prefix:
    description:
      - SnapMirror policy rule prefix.
      - Optional when defining policy rules.
      - Set to '' to not set or remove an existing custom prefix.
      - Prefix name should be unique within the policy.
      - When specifying a custom prefix, schedule must also be specified.
    type: list
    elements: str
    version_added: '20.7.0'
  schedule:
    description:
      - SnapMirror policy rule schedule.
      - Optional when defining policy rules.
      - Set to '' to not set or remove a schedule.
      - When specifying a schedule a custom prefix can be set otherwise the prefix will be set to snapmirror_label.
    type: list
    elements: str
    version_added: '20.7.0'
  identity_preservation:
    description:
      - Specifies which configuration of the source SVM is replicated to the destination SVM.
      - This property is applicable only for SVM data protection with "async" policy type.
      - Only supported with REST.
    type: str
    choices: ['full', 'exclude_network_config', 'exclude_network_and_protocol_config']
    version_added: '22.0.0'

"""

EXAMPLES = """
    - name: Create SnapMirror policy
      na_ontap_snapmirror_policy:
        state: present
        vserver: "SVM1"
        policy_name: "ansible_policy"
        policy_type: "mirror_vault"
        comment: "created by ansible"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Modify SnapMirror policy
      na_ontap_snapmirror_policy:
        state: present
        vserver: "SVM1"
        policy_name: "ansible_policy"
        policy_type: "async_mirror"
        transfer_priority: "low"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Create SnapMirror policy with basic rules
      na_ontap_snapmirror_policy:
        state: present
        vserver: "SVM1"
        policy_name: "ansible_policy"
        policy_type: "async_mirror"
        snapmirror_label: ['daily', 'weekly', 'monthly']
        keep: [7, 5, 12]
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Create SnapMirror policy with rules and schedules (no schedule for daily rule)
      na_ontap_snapmirror_policy:
        state: present
        vserver: "SVM1"
        policy_name: "ansible_policy"
        policy_type: "mirror_vault"
        snapmirror_label: ['daily', 'weekly', 'monthly']
        keep: [7, 5, 12]
        schedule: ['','weekly','monthly']
        prefix: ['','','monthly_mv']
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Modify SnapMirror policy with rules, remove existing schedules and prefixes
      na_ontap_snapmirror_policy:
        state: present
        vserver: "SVM1"
        policy_name: "ansible_policy"
        policy_type: "mirror_vault"
        snapmirror_label: ['daily', 'weekly', 'monthly']
        keep: [7, 5, 12]
        schedule: ['','','']
        prefix: ['','','']
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Modify SnapMirror policy, delete all rules (excludes builtin rules)
      na_ontap_snapmirror_policy:
        state: present
        vserver: "SVM1"
        policy_name: "ansible_policy"
        policy_type: "mirror_vault"
        snapmirror_label: []
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Delete SnapMirror policy
      na_ontap_snapmirror_policy:
        state: absent
        vserver: "SVM1"
        policy_type: "async_mirror"
        policy_name: "ansible_policy"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false
"""

RETURN = """

"""

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapSnapMirrorPolicy:
    """
        Create, Modifies and Destroys a SnapMirror policy
    """
    def __init__(self):
        """
            Initialize the Ontap SnapMirror policy class
        """

        self.use_rest = False
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            vserver=dict(required=True, type='str'),
            policy_name=dict(required=True, type='str', aliases=['name']),
            comment=dict(required=False, type='str'),
            policy_type=dict(required=False, type='str',
                             choices=['vault', 'async_mirror', 'mirror_vault', 'strict_sync_mirror', 'sync_mirror']),
            tries=dict(required=False, type='str'),
            transfer_priority=dict(required=False, type='str', choices=['low', 'normal']),
            common_snapshot_schedule=dict(required=False, type='str'),
            ignore_atime=dict(required=False, type='bool'),
            is_network_compression_enabled=dict(required=False, type='bool'),
            owner=dict(required=False, type='str', choices=['cluster_admin', 'vserver_admin']),
            restart=dict(required=False, type='str', choices=['always', 'never', 'default']),
            snapmirror_label=dict(required=False, type="list", elements="str"),
            keep=dict(required=False, type="list", elements="int"),
            prefix=dict(required=False, type="list", elements="str"),
            schedule=dict(required=False, type="list", elements="str"),
            identity_preservation=dict(required=False, type="str", choices=['full', 'exclude_network_config', 'exclude_network_and_protocol_config']),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        # set up variables
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        # API should be used for ONTAP 9.6 or higher, Zapi for lower version
        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        # some attributes are not supported in earlier REST implementation
        unsupported_rest_properties = ['owner', 'restart', 'transfer_priority', 'tries', 'ignore_atime',
                                       'common_snapshot_schedule']
        self.use_rest = self.rest_api.is_rest_supported_properties(self.parameters, unsupported_rest_properties)
        if not self.use_rest:
            if not netapp_utils.has_netapp_lib():
                self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def get_snapmirror_policy(self):

        if self.use_rest:
            return self.get_snapmirror_policy_rest()

        return_value = None

        snapmirror_policy_get_iter = netapp_utils.zapi.NaElement('snapmirror-policy-get-iter')
        snapmirror_policy_info = netapp_utils.zapi.NaElement('snapmirror-policy-info')
        snapmirror_policy_info.add_new_child('policy-name', self.parameters['policy_name'])
        snapmirror_policy_info.add_new_child('vserver', self.parameters['vserver'])
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(snapmirror_policy_info)
        snapmirror_policy_get_iter.add_child_elem(query)

        try:
            result = self.server.invoke_successfully(snapmirror_policy_get_iter, True)
        except netapp_utils.zapi.NaApiError as error:
            if 'NetApp API failed. Reason - 13001:' in to_native(error):
                # policy does not exist
                return None
            self.module.fail_json(msg='Error getting snapmirror policy %s: %s' % (self.parameters['policy_name'], to_native(error)),
                                  exception=traceback.format_exc())

        if result and result.get_child_by_name('attributes-list'):
            snapmirror_policy_attributes = result['attributes-list']['snapmirror-policy-info']

            return_value = {
                'policy_name': snapmirror_policy_attributes['policy-name'],
                'tries': snapmirror_policy_attributes['tries'],
                'transfer_priority': snapmirror_policy_attributes['transfer-priority'],
                'is_network_compression_enabled': self.na_helper.get_value_for_bool(True,
                                                                                    snapmirror_policy_attributes['is-network-compression-enabled']),
                'restart': snapmirror_policy_attributes['restart'],
                'ignore_atime': self.na_helper.get_value_for_bool(True, snapmirror_policy_attributes['ignore-atime']),
                'vserver': snapmirror_policy_attributes['vserver-name'],
                'comment': '',
                'snapmirror_label': [],
                'keep': [],
                'prefix': [],
                'schedule': [],
            }
            if snapmirror_policy_attributes.get_child_content('comment') is not None:
                return_value['comment'] = snapmirror_policy_attributes['comment']

            if snapmirror_policy_attributes.get_child_content('type') is not None:
                return_value['policy_type'] = snapmirror_policy_attributes['type']

            if snapmirror_policy_attributes.get_child_by_name('snapmirror-policy-rules'):
                for rule in snapmirror_policy_attributes['snapmirror-policy-rules'].get_children():
                    # Ignore builtin rules
                    if rule.get_child_content('snapmirror-label') in ["sm_created", "all_source_snapshots"]:
                        continue

                    return_value['snapmirror_label'].append(rule.get_child_content('snapmirror-label'))
                    return_value['keep'].append(int(rule.get_child_content('keep')))

                    prefix = rule.get_child_content('prefix')
                    if prefix is None or prefix == '-':
                        prefix = ''
                    return_value['prefix'].append(prefix)

                    schedule = rule.get_child_content('schedule')
                    if schedule is None or schedule == '-':
                        schedule = ''
                    return_value['schedule'].append(schedule)

        return return_value

    def get_snapmirror_policy_rest(self):

        query = {'fields': 'uuid,name,svm.name,comment,network_compression_enabled,type,retention',
                 'name': self.parameters['policy_name'],
                 'svm.name': self.parameters['vserver']}
        api = "snapmirror/policies"
        record, error = rest_generic.get_one_record(self.rest_api, api, query)
        if error:
            self.module.fail_json(msg='Error getting snapmirror policy: %s' % error)
        if record:
            return_value = {
                'uuid': record['uuid'],
                'vserver': record['svm']['name'],
                'policy_name': record['name'],
                'comment': '',
                'is_network_compression_enabled': record['network_compression_enabled'],
                'snapmirror_label': [],
                'keep': [],
                'prefix': [],
                'schedule': [],
                'identity_preservation': '',
            }
            if 'type' in record:
                policy_type = record['type']
                if policy_type == 'async':
                    policy_type = 'async_mirror'
                elif policy_type == 'sync':
                    policy_type = 'sync_mirror'
                return_value['policy_type'] = policy_type
            if 'comment' in record:
                return_value['comment'] = record['comment']
            if 'retention' in record:
                for rule in record['retention']:
                    return_value['snapmirror_label'].append(rule['label'])
                    return_value['keep'].append(int(rule['count']))
                    if rule['prefix'] == '-':
                        return_value['prefix'].append('')
                    else:
                        return_value['prefix'].append(rule['prefix'])
                    if rule['creation_schedule']['name'] == '-':
                        return_value['schedule'].append('')
                    else:
                        return_value['schedule'].append(rule['creation_schedule']['name'])
            if 'identity_preservation' in record:
                return_value['identity_preservation'] = record['identity_preservation']
            return return_value
        return None

    def validate_parameters(self):
        """
        Validate snapmirror policy rules
        :return: None
        """

        # For snapmirror policy rules, 'snapmirror_label' is required.
        if 'snapmirror_label' in self.parameters:

            # Check size of 'snapmirror_label' list is 0-10. Can have zero rules.
            # Take builtin 'sm_created' rule into account for 'mirror_vault'.
            if (('policy_type' in self.parameters and self.parameters['policy_type'] == 'mirror_vault' and len(self.parameters['snapmirror_label']) > 9)
                    or len(self.parameters['snapmirror_label']) > 10):
                self.module.fail_json(msg="Error: A SnapMirror Policy can have up to a maximum of "
                                          "10 rules (including builtin rules), with a 'keep' value "
                                          "representing the maximum number of Snapshot copies for each rule")

            # 'keep' must be supplied as long as there is at least one snapmirror_label
            if len(self.parameters['snapmirror_label']) > 0 and 'keep' not in self.parameters:
                self.module.fail_json(msg="Error: Missing 'keep' parameter. When specifying the "
                                          "'snapmirror_label' parameter, the 'keep' parameter must "
                                          "also be supplied")

            # Make sure other rule values match same number of 'snapmirror_label' values.
            for rule_parameter in ['keep', 'prefix', 'schedule']:
                if rule_parameter in self.parameters:
                    if len(self.parameters['snapmirror_label']) > len(self.parameters[rule_parameter]):
                        self.module.fail_json(msg="Error: Each 'snapmirror_label' value must have "
                                                  "an accompanying '%s' value" % rule_parameter)
                    if len(self.parameters[rule_parameter]) > len(self.parameters['snapmirror_label']):
                        self.module.fail_json(msg="Error: Each '%s' value must have an accompanying "
                                                  "'snapmirror_label' value" % rule_parameter)
        else:
            # 'snapmirror_label' not supplied.
            # Bail out if other rule parameters have been supplied.
            for rule_parameter in ['keep', 'prefix', 'schedule']:
                if rule_parameter in self.parameters:
                    self.module.fail_json(msg="Error: Missing 'snapmirror_label' parameter. When "
                                              "specifying the '%s' parameter, the 'snapmirror_label' "
                                              "parameter must also be supplied" % rule_parameter)

        # Schedule must be supplied if prefix is supplied.
        if 'prefix' in self.parameters and 'schedule' not in self.parameters:
            self.module.fail_json(msg="Error: Missing 'schedule' parameter. When "
                                      "specifying the 'prefix' parameter, the 'schedule' "
                                      "parameter must also be supplied")

    def create_snapmirror_policy(self, body=None):
        """
        Creates a new storage efficiency policy
        """
        if self.use_rest:
            api = "snapmirror/policies"
            dummy, error = rest_generic.post_async(self.rest_api, api, body)
            if error:
                self.module.fail_json(msg='Error creating snapmirror policy: %s' % error)
        else:
            snapmirror_policy_obj = netapp_utils.zapi.NaElement("snapmirror-policy-create")
            snapmirror_policy_obj.add_new_child("policy-name", self.parameters['policy_name'])
            if 'policy_type' in self.parameters.keys():
                snapmirror_policy_obj.add_new_child("type", self.parameters['policy_type'])
            snapmirror_policy_obj = self.create_snapmirror_policy_obj(snapmirror_policy_obj)

            try:
                self.server.invoke_successfully(snapmirror_policy_obj, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error creating snapmirror policy %s: %s' % (self.parameters['policy_name'], to_native(error)),
                                      exception=traceback.format_exc())

    def create_snapmirror_policy_obj(self, snapmirror_policy_obj):
        if 'comment' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("comment", self.parameters['comment'])
        if 'common_snapshot_schedule' in self.parameters.keys() and self.parameters['policy_type'] in ('sync_mirror', 'strict_sync_mirror'):
            snapmirror_policy_obj.add_new_child("common-snapshot-schedule", self.parameters['common_snapshot_schedule'])
        if 'ignore_atime' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("ignore-atime", self.na_helper.get_value_for_bool(False, self.parameters['ignore_atime']))
        if 'is_network_compression_enabled' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("is-network-compression-enabled",
                                                self.na_helper.get_value_for_bool(False, self.parameters['is_network_compression_enabled']))
        if 'owner' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("owner", self.parameters['owner'])
        if 'restart' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("restart", self.parameters['restart'])
        if 'transfer_priority' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("transfer-priority", self.parameters['transfer_priority'])
        if 'tries' in self.parameters.keys():
            snapmirror_policy_obj.add_new_child("tries", self.parameters['tries'])
        return snapmirror_policy_obj

    def build_body_for_create(self):

        body = {'name': self.parameters['policy_name'],
                'svm': {'name': self.parameters['vserver']}}
        # if policy type is omitted, REST assumes async
        policy_type = 'async'
        if 'policy_type' in self.parameters:
            if 'async_mirror' in self.parameters['policy_type']:
                policy_type = 'async'
            elif 'sync_mirror' in self.parameters['policy_type']:
                policy_type = 'sync'
                body['sync_type'] = 'sync'
            else:
                self.module.fail_json(msg='Error: policy type in REST only supports options async_mirror or sync_mirror, given %s'
                                      % (self.parameters['policy_type']))
            body['type'] = policy_type

        return self.build_body_for_create_or_modify(policy_type, body)

    def build_body_for_create_or_modify(self, policy_type, body=None):

        if body is None:
            body = {}
        if 'comment' in self.parameters.keys():
            body["comment"] = self.parameters['comment']
        if 'is_network_compression_enabled' in self.parameters:
            if policy_type == 'sync':
                self.module.fail_json(msg="Error: input parameter network_compression_enabled is not valid for SnapMirror policy type sync")
            body["network_compression_enabled"] = self.parameters['is_network_compression_enabled']
        if 'identity_preservation' in self.parameters:
            if policy_type == 'sync':
                self.module.fail_json(msg='Error: identity_preservation is only supported with async (async_mirror) policy_type, got: %s'
                                      % (self.parameters['policy_type']))
            body['identity_preservation'] = self.parameters['identity_preservation']
        return body

    def create_snapmirror_policy_retention_obj_for_rest(self, rules=None):
        """
        Create SnapMirror policy retention REST object.
        :param list rules: e.g. [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': 'daily', 'schedule': 'daily'}, ... ]
        :return: List of retention REST objects.
                 e.g. [{'label': 'daily', 'count': 7, 'prefix': 'daily', 'creation_schedule': {'name': 'daily'}}, ... ]
        """
        snapmirror_policy_retention_objs = []
        if rules is not None:
            for rule in rules:
                retention = {'label': rule['snapmirror_label'], 'count': str(rule['keep'])}
                if 'prefix' in rule and rule['prefix'] != '':
                    retention['prefix'] = rule['prefix']
                if 'schedule' in rule and rule['schedule'] != '':
                    retention['creation_schedule'] = {'name': rule['schedule']}
                snapmirror_policy_retention_objs.append(retention)
        return snapmirror_policy_retention_objs

    def delete_snapmirror_policy(self, uuid=None):
        """
        Deletes a snapmirror policy
        """
        if self.use_rest:
            api = "snapmirror/policies"
            dummy, error = rest_generic.delete_async(self.rest_api, api, uuid)
            if error:
                self.module.fail_json(msg='Error deleting snapmirror policy: %s' % error)
        else:
            snapmirror_policy_obj = netapp_utils.zapi.NaElement("snapmirror-policy-delete")
            snapmirror_policy_obj.add_new_child("policy-name", self.parameters['policy_name'])

            try:
                self.server.invoke_successfully(snapmirror_policy_obj, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error deleting snapmirror policy %s: %s' % (self.parameters['policy_name'], to_native(error)),
                                      exception=traceback.format_exc())

    def modify_snapmirror_policy(self, uuid=None, body=None):
        """
        Modifies a snapmirror policy
        """
        if self.use_rest:
            if not body:
                return
            api = "snapmirror/policies"
            dummy, error = rest_generic.patch_async(self.rest_api, api, uuid, body)
            if error:
                self.module.fail_json(msg='Error modifying snapmirror policy: %s' % error)
        else:
            snapmirror_policy_obj = netapp_utils.zapi.NaElement("snapmirror-policy-modify")
            snapmirror_policy_obj = self.create_snapmirror_policy_obj(snapmirror_policy_obj)
            # Only modify snapmirror policy if a specific snapmirror policy attribute needs
            # modifying. It may be that only snapmirror policy rules are being modified.
            if snapmirror_policy_obj.get_children():
                snapmirror_policy_obj.add_new_child("policy-name", self.parameters['policy_name'])

                try:
                    self.server.invoke_successfully(snapmirror_policy_obj, True)
                except netapp_utils.zapi.NaApiError as error:
                    self.module.fail_json(msg='Error modifying snapmirror policy %s: %s' % (self.parameters['policy_name'], to_native(error)),
                                          exception=traceback.format_exc())

    def identify_new_snapmirror_policy_rules(self, current=None):
        """
        Identify new rules that should be added.
        :return: List of new rules to be added
                 e.g. [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''}, ... ]
        """
        new_rules = []
        if 'snapmirror_label' in self.parameters:
            for snapmirror_label in self.parameters['snapmirror_label']:
                snapmirror_label = snapmirror_label.strip()

                # Construct new rule. prefix and schedule are optional.
                snapmirror_label_index = self.parameters['snapmirror_label'].index(snapmirror_label)
                rule = dict({
                    'snapmirror_label': snapmirror_label,
                    'keep': self.parameters['keep'][snapmirror_label_index]
                })
                if 'prefix' in self.parameters:
                    rule['prefix'] = self.parameters['prefix'][snapmirror_label_index]
                else:
                    rule['prefix'] = ''
                if 'schedule' in self.parameters:
                    rule['schedule'] = self.parameters['schedule'][snapmirror_label_index]
                else:
                    rule['schedule'] = ''

                if current is None or 'snapmirror_label' not in current or snapmirror_label not in current['snapmirror_label']:
                    # Rule doesn't exist. Add new rule.
                    new_rules.append(rule)
        return new_rules

    def identify_obsolete_snapmirror_policy_rules(self, current=None):
        """
        Identify existing rules that should be deleted
        :return: List of rules to be deleted
                 e.g. [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''}, ... ]
        """
        obsolete_rules = []
        if 'snapmirror_label' in self.parameters and current is not None and 'snapmirror_label' in current:
            # Iterate existing rules.
            for snapmirror_label in current['snapmirror_label']:
                snapmirror_label = snapmirror_label.strip()
                if snapmirror_label not in [item.strip() for item in self.parameters['snapmirror_label']]:
                    # Existing rule isn't in parameters. Delete existing rule.
                    current_snapmirror_label_index = current['snapmirror_label'].index(snapmirror_label)
                    rule = dict({
                        'snapmirror_label': snapmirror_label,
                        'keep': current['keep'][current_snapmirror_label_index],
                        'prefix': current['prefix'][current_snapmirror_label_index],
                        'schedule': current['schedule'][current_snapmirror_label_index]
                    })
                    obsolete_rules.append(rule)
        return obsolete_rules

    def set_rule(self, rule, key, current, snapmirror_label_index, current_snapmirror_label_index):
        if key not in self.parameters or self.parameters[key][snapmirror_label_index] == current[key][current_snapmirror_label_index]:
            modified = False
            rule[key] = current[key][current_snapmirror_label_index]
        else:
            modified = True
            rule[key] = self.parameters[key][snapmirror_label_index]
        return modified

    def identify_modified_snapmirror_policy_rules(self, current=None):
        """
        Identify self.parameters rules that will be modified or not.
        :return: List of 'modified' rules and a list of 'unmodified' rules
                 e.g. [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': '', 'schedule': ''}, ... ]
        """
        modified_rules = []
        unmodified_rules = []
        if 'snapmirror_label' in self.parameters:
            for snapmirror_label in self.parameters['snapmirror_label']:
                snapmirror_label = snapmirror_label.strip()
                if current is not None and 'snapmirror_label' in current and snapmirror_label in current['snapmirror_label']:
                    # Rule exists. Identify whether it requires modification or not.
                    modified = False
                    rule = {'snapmirror_label': snapmirror_label}
                    # Get indexes of current and supplied rule.
                    current_snapmirror_label_index = current['snapmirror_label'].index(snapmirror_label)
                    snapmirror_label_index = self.parameters['snapmirror_label'].index(snapmirror_label)

                    # Check if keep modified
                    if self.set_rule(rule, 'keep', current, snapmirror_label_index, current_snapmirror_label_index):
                        modified = True

                    # Check if prefix modified
                    if self.set_rule(rule, 'prefix', current, snapmirror_label_index, current_snapmirror_label_index):
                        modified = True

                    # Check if schedule modified
                    if self.set_rule(rule, 'schedule', current, snapmirror_label_index, current_snapmirror_label_index):
                        modified = True

                    if modified:
                        modified_rules.append(rule)
                    else:
                        unmodified_rules.append(rule)
        return modified_rules, unmodified_rules

    def identify_snapmirror_policy_rules_with_schedule(self, rules=None):
        """
        Identify rules that are using a schedule or not. At least one
        non-schedule rule must be added to a policy before schedule rules
        are added.
        :return: List of rules with schedules and a list of rules without schedules
                 e.g. [{'snapmirror_label': 'daily', 'keep': 7, 'prefix': 'daily', 'schedule': 'daily'}, ... ],
                      [{'snapmirror_label': 'weekly', 'keep': 5, 'prefix': '', 'schedule': ''}, ... ]
        """
        schedule_rules = []
        non_schedule_rules = []
        if rules is not None:
            for rule in rules:
                if 'schedule' in rule:
                    schedule_rules.append(rule)
                else:
                    non_schedule_rules.append(rule)
        return schedule_rules, non_schedule_rules

    def modify_snapmirror_policy_rules(self, current=None, uuid=None):
        """
        Modify existing rules in snapmirror policy
        :return: None
        """
        # Need 'snapmirror_label' to add/modify/delete rules
        if 'snapmirror_label' not in self.parameters:
            return

        obsolete_rules = self.identify_obsolete_snapmirror_policy_rules(current)
        new_rules = self.identify_new_snapmirror_policy_rules(current)
        modified_rules, unmodified_rules = self.identify_modified_snapmirror_policy_rules(current)

        if self.use_rest:
            api = "snapmirror/policies"
            body = {'retention': []}

            # As rule 'prefix' can't be unset, have to delete existing rules first.
            # Builtin rules remain.
            dummy, error = rest_generic.patch_async(self.rest_api, api, uuid, body)
            if error:
                self.module.fail_json(msg='Error deleting snapmirror policy rules: %s' % error)

            # Re-add desired rules.
            rules = unmodified_rules + modified_rules + new_rules
            body['retention'] = self.create_snapmirror_policy_retention_obj_for_rest(rules)

            if len(body['retention']) > 0:
                dummy, error = rest_generic.patch_async(self.rest_api, api, uuid, body)
                if error:
                    self.module.fail_json(msg='Error adding snapmirror policy rules: %s' % error)
        else:
            delete_rules = obsolete_rules + modified_rules
            add_schedule_rules, add_non_schedule_rules = self.identify_snapmirror_policy_rules_with_schedule(new_rules + modified_rules)
            # Delete rules no longer required or modified rules that will be re-added.
            for rule in delete_rules:
                options = {'policy-name': self.parameters['policy_name'],
                           'snapmirror-label': rule['snapmirror_label']}
                self.modify_snapmirror_policy_rule(options, 'snapmirror-policy-remove-rule')

            # Add rules. At least one non-schedule rule must exist before
            # a rule with a schedule can be added, otherwise zapi will complain.
            for rule in add_non_schedule_rules + add_schedule_rules:
                options = {'policy-name': self.parameters['policy_name'],
                           'snapmirror-label': rule['snapmirror_label'],
                           'keep': str(rule['keep'])}
                if 'prefix' in rule and rule['prefix'] != '':
                    options['prefix'] = rule['prefix']
                if 'schedule' in rule and rule['schedule'] != '':
                    options['schedule'] = rule['schedule']
                self.modify_snapmirror_policy_rule(options, 'snapmirror-policy-add-rule')

    def modify_snapmirror_policy_rule(self, options, zapi):
        """
        Add, modify or remove a rule to/from a snapmirror policy
        """
        snapmirror_obj = netapp_utils.zapi.NaElement.create_node_with_children(zapi, **options)
        try:
            self.server.invoke_successfully(snapmirror_obj, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying snapmirror policy rule %s: %s' %
                                  (self.parameters['policy_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def asup_log_for_cserver(self):
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("na_ontap_snapmirror_policy", cserver)

    def get_actions(self):
        current, modify = self.get_snapmirror_policy(), None
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if current and cd_action is None and self.parameters['state'] == 'present':
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
            if 'policy_type' in modify:
                self.module.fail_json(msg='Error: policy type cannot be changed: current=%s, expected=%s' %
                                      (current.get('policy_type'), modify['policy_type']))

        body = None
        modify_body = any(key not in ('keep', 'prefix', 'schedule', 'snapmirror_label') for key in modify) if modify else False
        if self.na_helper.changed and (cd_action == 'create' or modify):
            # report any error even in check_mode
            self.validate_parameters()
            if self.use_rest and (cd_action == 'create' or modify_body):
                body = self.build_body_for_create_or_modify(current.get('policy_type')) if modify_body else self.build_body_for_create()
        return cd_action, modify, current, body

    def apply(self):
        if not self.use_rest:
            self.asup_log_for_cserver()
        cd_action, modify, current, body = self.get_actions()

        if self.na_helper.changed and not self.module.check_mode:
            uuid = None
            if cd_action == 'create':
                self.create_snapmirror_policy(body)
                if self.use_rest:
                    current = self.get_snapmirror_policy()
                    if not current:
                        self.module.fail_json(msg="Error: policy %s not present after create." % self.parameters['policy_name'])
                    uuid = current['uuid']
                self.modify_snapmirror_policy_rules(current, uuid)
            elif cd_action == 'delete':
                if self.use_rest:
                    uuid = current['uuid']
                self.delete_snapmirror_policy(uuid)
            elif modify:
                if self.use_rest:
                    uuid = current['uuid']
                self.modify_snapmirror_policy(uuid, body)
                self.modify_snapmirror_policy_rules(current, uuid)

        result = netapp_utils.generate_result(self.na_helper.changed, cd_action, modify)
        self.module.exit_json(**result)


def main():
    """
    Creates the NetApp Ontap SnapMirror policy object and runs the correct play task
    """
    obj = NetAppOntapSnapMirrorPolicy()
    obj.apply()


if __name__ == '__main__':
    main()
