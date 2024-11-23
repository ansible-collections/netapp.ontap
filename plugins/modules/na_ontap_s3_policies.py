#!/usr/bin/python

# (c) 2022-2024, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
module: na_ontap_s3_policies
short_description: NetApp ONTAP S3 Policies
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap_rest
version_added: 21.21.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Create, delete, or modify S3 Policies on NetApp ONTAP.

options:
  state:
    description:
    - Whether the specified S3 policy should exist or not.
    choices: ['present', 'absent']
    type: str
    default: 'present'

  name:
    description:
    - The name of the S3 policy.
    type: str
    required: true

  vserver:
    description:
    - Name of the vserver to use.
    type: str
    required: true

  comment:
    description:
    - comment about the policy
    type: str

  statements:
    description:
      - Policy statements are built using this structure to specify permissions
      - Grant <Effect> to allow/deny <Principal> to perform <Action> on <Resource> when <Condition> applies
    type: list
    elements: dict
    suboptions:
      sid:
        description: Statement ID
        type: str
        required: true
      resources:
        description:
          - The bucket and any object it contains.
          - The wildcard characters * and ? can be used to form a regular expression for specifying a resource.
        type: list
        elements: str
        required: true
      actions:
        description:
          - You can specify * to mean all actions, or a list of one or more of the following
          - GetObject
          - PutObject
          - DeleteObject
          - ListBucket
          - GetBucketAcl
          - GetObjectAcl
          - ListBucketMultipartUploads
          - ListMultipartUploadParts
        type: list
        elements: str
        required: true
      effect:
        description: The statement may allow or deny access
        type: str
        choices:
          - allow
          - deny
        required: true
'''
EXAMPLES = """
    - name: Create and modify a S3 policy
      netapp.ontap.na_ontap_s3_policies:
        state: present
        name: carchi-s3-policy
        comment: carchi8py was here
        vserver: ansibleSVM
        statements:
          - sid: 1
            resources:
            - "bucket1"
            - "bucket1/*"
            actions:
              - "*"
            effect:
              allow
          - sid: 2
            resources:
            - "bucket2"
            - "bucket2/*"
            actions:
              - "*"
            effect:
              allow
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: true
        validate_certs: false
        use_rest: always

    - name: delete S3 policy
      netapp.ontap.na_ontap_s3_policies:
        state: absent
        name: carchi-s3-policy
        vserver: ansibleSVM
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: true
        validate_certs: false
        use_rest: always
"""
RETURN = """
"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic
from ansible_collections.netapp.ontap.plugins.module_utils import rest_vserver


class NetAppOntapS3Policies:
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_rest_only_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            vserver=dict(required=True, type='str'),
            name=dict(required=True, type='str'),
            comment=dict(required=False, type='str'),
            statements=dict(type='list', elements='dict', options=dict(
                sid=dict(required=True, type='str'),
                resources=dict(required=True, type='list', elements='str'),
                actions=dict(required=True, type='list', elements='str'),
                effect=dict(required=True, type='str', choices=['allow', 'deny']),
            ))))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.svm_uuid = None
        self.uuid = None
        self.na_helper = NetAppModule(self.module)
        self.parameters = self.na_helper.check_and_set_parameters(self.module)
        self.rest_api = OntapRestAPI(self.module)
        self.use_rest = self.rest_api.is_rest()
        self.rest_api.fail_if_not_rest_minimum_version('na_ontap_s3_policies', 9, 8)

    def get_s3_policies(self):
        self.get_svm_uuid()
        api = 'protocols/s3/services/%s/policies' % self.svm_uuid
        fields = ','.join(('name',
                           'comment',
                           'statements'))
        params = {'name': self.parameters['name'],
                  'fields': fields}
        record, error = rest_generic.get_one_record(self.rest_api, api, params)
        if error:
            self.module.fail_json(msg='Error fetching S3 policy %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        # sid is an Str or a number, it will return a string back unless you pass a number then it returns a int
        if record:
            for each in record['statements']:
                each['sid'] = str(each['sid'])
        return record

    def get_svm_uuid(self):
        uuid, dummy = rest_vserver.get_vserver_uuid(self.rest_api, self.parameters['vserver'], self.module, True)
        self.svm_uuid = uuid

    def create_s3_policies(self):
        api = 'protocols/s3/services/%s/policies' % self.svm_uuid
        body = {'name': self.parameters['name']}
        if self.parameters.get('comment'):
            body['comment'] = self.parameters['comment']
        if self.parameters.get('statements'):
            body['statements'] = self.parameters['statements']
        dummy, error = rest_generic.post_async(self.rest_api, api, body)
        if error:
            self.module.fail_json(msg='Error creating S3 policy %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def delete_s3_policies(self):
        api = 'protocols/s3/services/%s/policies' % self.svm_uuid
        dummy, error = rest_generic.delete_async(self.rest_api, api, self.parameters['name'])
        if error:
            self.module.fail_json(msg='Error deleting S3 policy %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_s3_policies(self, modify):
        api = 'protocols/s3/services/%s/policies' % self.svm_uuid
        body = {}
        if modify.get('comment'):
            body['comment'] = self.parameters['comment']
        if self.parameters.get('statements'):
            body['statements'] = self.parameters['statements']
        dummy, error = rest_generic.patch_async(self.rest_api, api, self.parameters['name'], body)
        if error:
            self.module.fail_json(msg='Error modifying S3 policy %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def apply(self):
        current = self.get_s3_policies()
        modify = None
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action is None:
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.create_s3_policies()
            if cd_action == 'delete':
                self.delete_s3_policies()
            if modify:
                self.modify_s3_policies(modify)
        result = netapp_utils.generate_result(self.na_helper.changed, cd_action, modify)
        self.module.exit_json(**result)


def main():
    '''Apply volume operations from playbook'''
    obj = NetAppOntapS3Policies()
    obj.apply()


if __name__ == '__main__':
    main()
