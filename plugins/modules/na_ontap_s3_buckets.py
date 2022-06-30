#!/usr/bin/python

# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
module: na_ontap_s3_buckets
short_description: NetApp ONTAP S3 Buckets
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 21.19.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Create, delete, or modify S3 buckets on NetApp ONTAP.

options:
  state:
    description:
    - Whether the specified S3 bucket should exist or not.
    choices: ['present', 'absent']
    type: str
    default: 'present'

  name:
    description:
    - The name of the S3 bucket.
    type: str
    required: true

  vserver:
    description:
    - Name of the vserver to use.
    type: str
    required: true

  aggregates:
    description:
    - List of aggregates names to use for the S3 bucket.
    type: list
    elements: str

  constituents_per_aggregate:
    description:
    - Number of constituents per aggregate.
    type: int

  size:
    description:
    - Size of the S3 bucket in bytes.
    type: int

  comment:
    description:
    - Comment for the S3 bucket.
    type: str

  policy:
    description:
      - Access policy uses the Amazon Web Services (AWS) policy language syntax to allow S3 tenants to create access policies to their data
    type: dict
    suboptions:
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
          resources:
            description:
              - The bucket and any object it contains.
              - The wildcard characters * and ? can be used to form a regular expression for specifying a resource.
            type: list
            elements: str
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
          effect:
            description: The statement may allow or deny access
            type: str
            choices:
              - allow
              - deny
          principals:
            description: A list of one or more S3 users or groups.
            type: list
            elements: str
          conditions:
            description: Conditions for when a policy is in effect.
            type: list
            elements: dict
            suboptions:
              operator:
                description:
                  - The operator to use for the condition.
                type: str
                choices:
                  - ip_address
                  - not_ip_address
                  - string_equals
                  - string_not_equals
                  - string_equals_ignore_case
                  - string_not_equals_ignore_case
                  - string_like
                  - string_not_like
                  - numeric_equals
                  - numeric_not_equals
                  - numeric_greater_than
                  - numeric_greater_than_equals
                  - numeric_less_than
                  - numeric_less_than_equals
              max_keys:
                description:
                  - The maximum number of keys that can be returned in a request.
                type: list
                elements: str
              delimiters:
                description:
                 - The delimiter used to identify a prefix in a list of objects.
                type: list
                elements: str
              source_ips:
                description:
                  - The source IP address of the request.
                type: list
                elements: str
              prefixes:
                description:
                  - The prefixes of the objects that you want to list.
                type: list
                elements: str
              usernames:
                description:
                  - The user names that you want to allow to access the bucket.
                type: list
                elements: str

  qos_policy:
    description:
    - A policy group defines measurable service level objectives (SLOs) that apply to the storage objects with which the policy group is associated.
    - If you do not assign a policy group to a bucket, the system wil not monitor and control the traffic to it.
    type: dict
    suboptions:
      max_throughput_iops:
        description: The maximum throughput in IOPS.
        type: int
      max_throughput_mbps:
        description: The maximum throughput in MBPS.
        type: int
      min_throughput_iops:
        description: The minimum throughput in IOPS.
        type: int
      min_throughput_mbps:
        description: The minimum throughput in MBPS.
        type: int
      name:
        description: The QoS policy group name. This is mutually exclusive with other QoS attributes.
        type: str

  audit_event_selector:
    description: Audit event selector allows you to specify access and permission types to audit.
    type: dict
    suboptions:
      access:
        description:
          - specifies the type of event access to be audited, read-only, write-only or all (default is all).
        type: str
        choices:
          - read-only
          - write-only
          - all
      permission:
        description:
          - specifies the type of event permission to be audited, allow-only, deny-only or all (default is all).
        type: str
        choices:
          - allow-only
          - deny-only
          - all
'''

EXAMPLES = """
    - name: Create S3 bucket
      netapp.ontap.na_ontap_s3_buckets:
        state: present
        name: carchi-test-bucket
        comment: carchi8py was here
        size: 838860800
        vserver: ansibleSVM
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: true
        validate_certs: false
        use_rest: always

    - name: Create S3 bucket with a policy
      netapp.ontap.na_ontap_s3_buckets:
        state: present
        name: carchi-test-bucket
        comment: carchi8py was here
        size: 838860800
        policy:
          statements:
            - sid: FullAccessToUser1
              resources:
                - bucket1
                - bucket1/*
              actions:
                - GetObject
                - PutObject
                - DeleteObject
                - ListBucket
              effect: allow
              conditions:
                - operator: ip_address
                  max_keys:
                    - 1000
                  delimiters:
                    - "/"
                  source_ips:
                    - 1.1.1.1
                    - 1.2.2.0/24
                  prefixes:
                    - prex
                  usernames:
                    - user1
              principals:
                - user1
                - group/grp1
        vserver: ansibleSVM
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: true
        validate_certs: false
        use_rest: always

    - name: Delete S3 bucket
      netapp.ontap.na_ontap_s3_buckets:
        state: absent
        name: carchi-test-bucket
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


class NetAppOntapS3Buckets():
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str'),
            vserver=dict(required=True, type='str'),
            aggregates=dict(required=False, type='list', elements='str'),
            constituents_per_aggregate=dict(required=False, type='int'),
            size=dict(required=False, type='int'),
            comment=dict(required=False, type='str'),
            policy=dict(type='dict', options=dict(
                statements=dict(type='list', elements='dict', options=dict(
                    sid=dict(required=False, type='str'),
                    resources=dict(required=False, type='list', elements='str'),
                    actions=dict(required=False, type='list', elements='str'),
                    effect=dict(required=False, type='str', choices=['allow', 'deny']),
                    conditions=dict(type='list', elements='dict', options=dict(
                        operator=dict(required=False, type='str', choices=['ip_address',
                                                                           'not_ip_address',
                                                                           'string_equals',
                                                                           'string_not_equals',
                                                                           'string_equals_ignore_case',
                                                                           'string_not_equals_ignore_case',
                                                                           'string_like',
                                                                           'string_not_like',
                                                                           'numeric_equals',
                                                                           'numeric_not_equals',
                                                                           'numeric_greater_than',
                                                                           'numeric_greater_than_equals',
                                                                           'numeric_less_than',
                                                                           'numeric_less_than_equals']),
                        max_keys=dict(required=False, type='list', elements='str', no_log=False),
                        delimiters=dict(required=False, type='list', elements='str'),
                        source_ips=dict(required=False, type='list', elements='str'),
                        prefixes=dict(required=False, type='list', elements='str'),
                        usernames=dict(required=False, type='list', elements='str'))),
                    principals=dict(type='list', elements='str')
                )))),
            qos_policy=dict(type='dict', options=dict(
                max_throughput_iops=dict(type='int'),
                max_throughput_mbps=dict(type='int'),
                name=dict(type='str'),
                min_throughput_iops=dict(type='int'),
                min_throughput_mbps=dict(type='int'),
            )),
            audit_event_selector=dict(type='dict', options=dict(
                access=dict(type='str', choices=['read-only', 'write-only', 'all']),
                permission=dict(type='str', choices=['allow-only', 'deny-only', 'all']))),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.svm_uuid = None
        self.uuid = None
        self.volume_uuid = None
        self.na_helper = NetAppModule(self.module)
        self.parameters = self.na_helper.check_and_set_parameters(self.module)

        self.rest_api = OntapRestAPI(self.module)
        partially_supported_rest_properties = [['audit_event_selector', (9, 10, 1)]]
        self.use_rest = self.rest_api.is_rest(partially_supported_rest_properties=partially_supported_rest_properties,
                                              parameters=self.parameters)
        self.rest_api.fail_if_not_rest_minimum_version('na_ontap_s3_bucket', 9, 8)

    def get_s3_bucket(self):
        api = 'protocols/s3/buckets'
        if self.rest_api.meets_rest_minimum_version(self.use_rest, 9, 10, 1):
            fields = 'name,svm.name,size,comment,volume.uuid,policy,qos_policy,audit_event_selector'
        else:
            fields = 'name,svm.name,size,comment,volume.uuid,policy,qos_policy'
        params = {'name': self.parameters['name'],
                  'svm.name': self.parameters['vserver'],
                  'fields': fields}
        record, error = rest_generic.get_one_record(self.rest_api, api, params)
        if error:
            self.module.fail_json(msg='Error fetching S3 bucket %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        if record:
            record = self.fix_sid(record)
            return self.set_uuids(record)
        return None

    def fix_sid(self, record):
        # So we treat SID as a String as it can accept Words, or Numbers. ONTAP will return it as a String, unless it is just
        # numbers then it is returned as an INT.
        if self.na_helper.safe_get(record, ['policy', 'statements']):
            for each in self.na_helper.safe_get(record, ['policy', 'statements']):
                each['sid'] = str(each['sid'])
        return record

    def create_s3_bucket(self):
        api = 'protocols/s3/buckets'
        body = {'svm.name': self.parameters['vserver'], 'name': self.parameters['name']}
        if self.parameters.get('aggregates'):
            body['aggregates'] = self.parameters['aggregates']
        if self.parameters.get('constituents_per_aggregate'):
            body['constituents_per_aggregate'] = self.parameters['constituents_per_aggregate']
        if self.parameters.get('size'):
            body['size'] = self.parameters['size']
        if self.parameters.get('comment'):
            body['comment'] = self.parameters['comment']
        if self.parameters.get('policy'):
            body['policy'] = self.na_helper.filter_out_none_entries(self.parameters['policy'])
            if self.na_helper.safe_get(body, ['policy', 'statements']):
                for statement in self.na_helper.safe_get(body, ['policy', 'statements']):
                    for condition in self.na_helper.safe_get(statement, ['conditions']):
                        if self.na_helper.safe_get(condition, ['source_ips']):
                            condition['source-ips'] = condition.pop('source_ips')
        if self.parameters.get('qos_policy'):
            body['qos_policy'] = self.na_helper.filter_out_none_entries(self.parameters['qos_policy'])
        if self.parameters.get('audit_event_selector'):
            body['audit_event_selector'] = self.na_helper.filter_out_none_entries(self.parameters['audit_event_selector'])
        dummy, error = rest_generic.post_async(self.rest_api, api, body, job_timeout=120)
        if error:
            self.module.fail_json(msg='Error creating S3 bucket %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def delete_s3_bucket(self):
        api = 'protocols/s3/buckets'
        uuids = '%s/%s' % (self.svm_uuid, self.uuid)
        dummy, error = rest_generic.delete_async(self.rest_api, api, uuids, job_timeout=120)
        if error:
            self.module.fail_json(msg='Error deleting S3 bucket %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_s3_bucket(self, modify):
        api = 'protocols/s3/buckets'
        uuids = '%s/%s' % (self.svm_uuid, self.uuid)
        body = {}
        if modify.get('size'):
            body['size'] = modify['size']
        if modify.get('comment'):
            body['comment'] = modify['comment']
        if modify.get('policy'):
            body['policy'] = modify['policy']
        if modify.get('qos_policy'):
            body['qos_policy'] = modify['qos_policy']
        if modify.get('audit_event_selector'):
            body['audit_event_selector'] = modify['audit_event_selector']
        dummy, error = rest_generic.patch_async(self.rest_api, api, uuids, body, job_timeout=120)
        if error:
            self.module.fail_json(msg='Error modifying S3 bucket %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def check_volume_aggr(self):
        api = 'storage/volumes/%s' % self.volume_uuid
        params = {'fields': 'aggregates.name'}
        record, error = rest_generic.get_one_record(self.rest_api, api, params)
        if error:
            self.module.fail_json(msg=error)
        aggr_names = [aggr['name'] for aggr in record['aggregates']]
        if self.parameters.get('aggregates'):
            if sorted(aggr_names) != sorted(self.parameters['aggregates']):
                return True
        return False

    def set_uuids(self, record):
        self.uuid = record['uuid']
        self.svm_uuid = record['svm']['uuid']
        self.volume_uuid = record['volume']['uuid']
        return record

    def apply(self):
        current = self.get_s3_bucket()
        cd_action, modify = None, None
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action is None:
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
            if current and self.check_volume_aggr():
                self.module.fail_json(msg='Aggregates can not be modified for S3 bucket %s' % self.parameters['name'])
        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.create_s3_bucket()
            if cd_action == 'delete':
                self.delete_s3_bucket()
            if modify:
                self.modify_s3_bucket(modify)

        self.module.exit_json(changed=self.na_helper.changed)


def main():
    '''Apply volume operations from playbook'''
    obj = NetAppOntapS3Buckets()
    obj.apply()


if __name__ == '__main__':
    main()
