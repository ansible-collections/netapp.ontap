#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
module: na_ontap_cg
short_description: NetApp ONTAP module to manage operations related to consistency groups.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap_rest
version_added: 23.4.0
author: NetApp Ansible Team (@carchi8py) <ng-ansible-team@netapp.com>
description:
  - Create a consistency group with one or more consistency groups having new or existing volumes.
  - Modify or delete an existing consistency group.
options:
  state:
    description:
      - Specifies whether to create, modify, or delete a consistency group.
    type: str
    choices: ['present', 'absent']
    default: present

  name:
    description:
      - Specifies the name of the consistency group. The consistency group name must be unique within an SVM.
    type: str
    required: true

  vserver:
    description:
      - Specifies the SVM in which the consistency group is located.
    type: str
    required: true

  volumes:
    description:
      - List of volumes to be included in the consistency group.
      - The volumes array can be used to create new volumes in the consistency group, add existing volumes to the consistency group.
      - A volume can only be associated with one direct parent consistency group.
      - Removing all volumes from a consistency group will automatically delete the consistency group.
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - Specifies the name of the volume.
        type: str
        required: true

      size:
        description:
          - Specifies the provisioned size of the volume in C(size_unit).
        type: int

      size_unit:
        description:
          - The unit used to interpret the size parameter.
        type: str
        choices: ['bytes', 'b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb', 'zb', 'yb']

      provisioning_options:
        description:
          - Options that are applied to the operation.
          - Module is not idempotent when 'count' option is set as the name is considered a prefix,
            and a suffix of the form _<N> is generated
            where N is the next available numeric index, starting with 1.
        type: dict
        suboptions:
          action:
            description: Operation to perform on the volume.
            type: str
            choices: ['create', 'add', 'remove']
          count:
            description: Number of elements to perform the operation on.
            type: int

      qos_policy:
        description:
          - The QoS policy for this volume.
          - Only supported when provisioning new objects.
        type: str

      snapshot_policy:
        description:
          - The snapshot policy for this volume.
        type: str

  luns:
    description:
      - The LUNs array can be used to create or modify LUNs in a consistency group on a new or existing volume that is a member of the consistency group.
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - The fully qualified path name of the LUN composed of the "/vol" prefix, the volume name, the qtree name (optional), and the base name of the LUN.
          - Example, /vol/volume1/lun1 or /vol/volume1/qtree1/lun1.
        type: str
        required: true

      size:
        description:
          - Specifies the provisioned size in C(size_unit).
        type: int

      size_unit:
        description:
          - The unit used to interpret the size parameter.
        type: str
        choices: ['bytes', 'b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb', 'zb', 'yb']

      provisioning_options:
        description:
          - Options that are applied to the operation.
          - Module is not idempotent when 'count' option is set as the name is considered a prefix,
            and a suffix of the form _<N> is generated
            where N is the next available numeric index, starting with 1.
        type: dict
        suboptions:
          action:
            description: Operation to perform.
            type: str
            choices: ['create']
          count:
            description: Number of elements to perform the operation on.
            type: int

      os_type:
        description:
          - The os type for the LUN.
        type: str

      lun_maps:
        description: An array of LUN maps.
        type: list
        elements: dict
        suboptions:
          igroup_name:
            description: The name of the initiator group.
            type: str
          igroup_initiators:
            description: Lists of the initiators that are members of the group.
            type: list
            elements: str
          os_type:
            description: The os type for the initiator groups.
            type: str

  namespaces:
    description:
      - The namespaces array can be used to create or modify namespaces in a consistency group.
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - The name of the NVMe namespace, of the form "/vol/<volume>[/<qtree>]/<namespace>" where the qtree name is optional.
          - Example, /vol/volume1/namespace1 or /vol/volume1/qtree1/namespace1.
        type: str
        required: true

      size:
        description:
          - Specifies the provisioned size in C(size_unit).
        type: int

      size_unit:
        description:
          - The unit used to interpret the size parameter.
        type: str
        choices: ['bytes', 'b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb', 'zb', 'yb']

      os_type:
        description:
          - The os type for the namespace.
        type: str

      provisioning_options:
        description:
          - Options that are applied to the operation.
          - Module is not idempotent when 'count' option is set as the name is considered a prefix,
            and a suffix of the form _<N> is generated
            where N is the next available numeric index, starting with 1.
        type: dict
        suboptions:
          action:
            description: Operation to perform.
            type: str
            choices: ['create']
          count:
            description: Number of elements to perform the operation on.
            type: int

  consistency_groups:
    description:
      - List of consistency groups to be included in the consistency group.
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - Specifies the name of the consistency group.
        type: str
        required: true

      provisioning_options:
        description:
          - Options that are applied to the operation.
        type: dict
        suboptions:
          action:
            description: Operation to perform.
            type: str
            choices: ['create', 'add', 'remove']
          name:
            description:
              - New name for consistency group. Required to resolve naming collisions.
              - Requires ONTAP 9.13.1 or later.
            type: str

      volumes:
        description:
          - List of volumes to be included in the consistency group.
          - The volumes array can be used to create new volumes in the consistency group, add existing volumes to the consistency group.
          - A volume can only be associated with one direct parent consistency group.
        type: list
        elements: dict
        suboptions:
          name:
            description:
              - Specifies the name of the volume.
            type: str
            required: true

          size:
            description:
              - Specifies the provisioned size of the volume in C(size_unit).
            type: int

          size_unit:
            description:
              - The unit used to interpret the size parameter.
            type: str
            choices: ['bytes', 'b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb', 'zb', 'yb']

          provisioning_options:
            description:
              - Options that are applied to the operation.
              - Module is not idempotent when 'count' option is set as the name is considered a prefix,
                and a suffix of the form _<N> is generated
                where N is the next available numeric index, starting with 1.
            type: dict
            suboptions:
              action:
                description: Operation to perform on the volume.
                type: str
                choices: ['create', 'add', 'remove']
              count:
                description: Number of elements to perform the operation on.
                type: int

          qos_policy:
            description:
              - The QoS policy for this volume.
              - Only supported when provisioning new objects.
            type: str

          snapshot_policy:
            description:
              - The snapshot policy for this volume.
            type: str

      luns:
        description:
          - The LUNs array can be used to create or modify LUNs in a consistency group on a new or existing volume that is a member of the consistency group.
        type: list
        elements: dict
        suboptions:
          name:
            description:
              - The fully qualified path name of the LUN composed of the "/vol" prefix,
                the volume name, the qtree name (optional), and the base name of the LUN.
              - Example, /vol/volume1/lun1 or /vol/volume1/qtree1/lun1.
            type: str
            required: true

          size:
            description:
              - Specifies the provisioned size in C(size_unit).
            type: int

          size_unit:
            description:
              - The unit used to interpret the size parameter.
            type: str
            choices: ['bytes', 'b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb', 'zb', 'yb']

          provisioning_options:
            description:
              - Options that are applied to the operation.
              - Module is not idempotent when 'count' option is set as the name is considered a prefix,
                and a suffix of the form _<N> is generated
                where N is the next available numeric index, starting with 1.
            type: dict
            suboptions:
              action:
                description: Operation to perform.
                type: str
                choices: ['create']
              count:
                description: Number of elements to perform the operation on.
                type: int

          os_type:
            description:
            - The os type for the LUN.
            type: str

          lun_maps:
            description: An array of LUN maps.
            type: list
            elements: dict
            suboptions:
              igroup_name:
                description: The name of the initiator group.
                type: str
              igroup_initiators:
                description: Lists of the initiators that are members of the group.
                type: list
                elements: str
              os_type:
                description: The os type for the initiator groups.
                type: str

      namespaces:
        description:
          - The namespaces array can be used to create or modify namespaces in a consistency group.
        type: list
        elements: dict
        suboptions:
          name:
            description:
              - The name of the NVMe namespace, of the form "/vol/<volume>[/<qtree>]/<namespace>" where the qtree name is optional.
              - Example, /vol/volume1/namespace1 or /vol/volume1/qtree1/namespace1.
            type: str
            required: true

          size:
            description:
              - Specifies the provisioned size in C(size_unit).
            type: int

          size_unit:
            description:
              - The unit used to interpret the size parameter.
            type: str
            choices: ['bytes', 'b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb', 'zb', 'yb']

          os_type:
            description:
              - The os type for the namespace.
            type: str

          provisioning_options:
            description:
              - Options that are applied to the operation.
              - Module is not idempotent when 'count' option is set as the name is considered a prefix,
                and a suffix of the form _<N> is generated
                where N is the next available numeric index, starting with 1.
            type: dict
            suboptions:
              action:
                description: Operation to perform.
                type: str
                choices: ['create']
              count:
                description: Number of elements to perform the operation on.
                type: int
      qos_policy:
        description:
        - Specifies the QoS policy for the consistency group.
        - Only supported when provisioning new objects.
        type: str

      snapshot_policy:
        description:
        - Specifies the snapshot policy for the consistency group.
        type: str

  qos_policy:
    description:
      - Specifies the QoS policy for the consistency group.
      - Only supported when provisioning new objects.
    type: str

  snapshot_policy:
    description:
      - Specifies the snapshot policy for the consistency group.
    type: str

notes:
  - Only supported with REST and requires ONTAP 9.10.1 or later.
  - Update operation will never delete storage elements.
    Mapping or unmapping a consistency group from igroups or subsystems is not supported.
  - Delete operation will not delete any associated volumes or LUNs.
    To delete those elements, use the appropriate object associated modules.
"""

EXAMPLES = """
- name: Creating a single consistency group with a new SAN volume
  netapp.ontap.na_ontap_cg:
    state: present
    vserver: svm1
    name: test_cg1
    volumes:
      - name: test_vol1
        size: 50
        size_unit: mb
        provisioning_options:
          action: create
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"

- name: Adding an existing volume to an existing consistency group
  netapp.ontap.na_ontap_cg:
    state: present
    vserver: svm1
    name: test_cg1
    volumes:
      - name: test_vol2
        provisioning_options:
          action: add
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"

- name: Adding LUNs to an existing volume in an existing consistency group
  netapp.ontap.na_ontap_cg:
    state: present
    vserver: svm1
    name: test_cg1
    luns:
      - name: "/vol/test_vol2/new_lun"
        size: 5
        size_unit: mb
        os_type: linux
        provisioning_options:
          action: create
        lun_maps:
          - igroup_name: new_igroup1
            igroup_initiators:
              - iqn.1995-08.com.example:new-initiator1
            os_type: linux
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"

- name: Adding namespaces to an existing volume in an existing consistency group
  netapp.ontap.na_ontap_cg:
    state: present
    vserver: svm1
    name: test_cg1
    namespaces:
      - name: "/vol/test_vol2/new_namespace"
        size: 5
        size_unit: mb
        os_type: linux
        provisioning_options:
          action: create
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"

- name: Deleting a CG (consistency group)
  netapp.ontap.na_ontap_cg:
    state: absent
    vserver: svm1
    name: test_cg1
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"

- name: Creating a parent CG with two child consistency groups with existing SAN volumes
  netapp.ontap.na_ontap_cg:
    state: present
    vserver: svm1
    name: parent_cg
    consistency_groups:
      - name: child_1
        volumes:
          - name: test_vol1
            provisioning_options:
              action: add
      - name: child_2
        volumes:
          - name: test_vol2
            provisioning_options:
              action: add
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"

- name: Removing a child consistency group from nested CG
  netapp.ontap.na_ontap_cg:
    state: present
    vserver: svm1
    name: parent_cg
    consistency_groups:
      - name: child_2
        provisioning_options:
          action: remove
          name: new_single_cg
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"

- name: Creating a parent CG with a new child CG with existing volumes
  netapp.ontap.na_ontap_cg:
    state: present
    vserver: svm1
    name: parent_cg
    consistency_groups:
      - name: child_1
        provisioning_options:
          action: create
        volumes:
          - name: test_vol1
            provisioning_options:
              action: add
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"
"""

RETURN = """
"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic

import copy


class NetAppOntapConsistencyGroup:
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_rest_only_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str'),
            vserver=dict(required=True, type='str'),
            volumes=dict(type='list', elements='dict', options=dict(
                name=dict(required=True, type='str'),
                size=dict(type='int'),
                size_unit=dict(type='str', choices=['bytes', 'b', 'kb', 'mb', 'gb', 'tb',
                                                    'pb', 'eb', 'zb', 'yb']),
                provisioning_options=dict(type='dict', options=dict(
                    action=dict(type='str', choices=['create', 'add', 'remove']),
                    count=dict(type='int')
                )),
                qos_policy=dict(type='str'),
                snapshot_policy=dict(type='str')
            )),
            luns=dict(type='list', elements='dict', options=dict(
                name=dict(required=True, type='str'),
                size=dict(type='int'),
                size_unit=dict(type='str', choices=['bytes', 'b', 'kb', 'mb', 'gb', 'tb',
                                                    'pb', 'eb', 'zb', 'yb']),
                provisioning_options=dict(type='dict', options=dict(
                    action=dict(type='str', choices=['create']),
                    count=dict(type='int')
                )),
                os_type=dict(type='str'),
                lun_maps=dict(type='list', elements='dict', options=dict(
                    igroup_name=dict(type='str'),
                    igroup_initiators=dict(type='list', elements='str'),
                    os_type=dict(type='str'),
                )),
            )),
            namespaces=dict(type='list', elements='dict', options=dict(
                name=dict(required=True, type='str'),
                size=dict(type='int'),
                size_unit=dict(type='str', choices=['bytes', 'b', 'kb', 'mb', 'gb', 'tb',
                                                    'pb', 'eb', 'zb', 'yb']),
                os_type=dict(type='str'),
                provisioning_options=dict(type='dict', options=dict(
                    action=dict(type='str', choices=['create']),
                    count=dict(type='int')
                )),
            )),
            consistency_groups=dict(type='list', elements='dict', options=dict(
                name=dict(required=True, type='str'),
                provisioning_options=dict(type='dict', options=dict(
                    action=dict(type='str', choices=['create', 'add', 'remove']),
                    name=dict(type='str')
                )),
                volumes=dict(type='list', elements='dict', options=dict(
                    name=dict(required=True, type='str'),
                    size=dict(type='int'),
                    size_unit=dict(type='str', choices=['bytes', 'b', 'kb', 'mb', 'gb', 'tb',
                                                        'pb', 'eb', 'zb', 'yb']),
                    provisioning_options=dict(type='dict', options=dict(
                        action=dict(type='str', choices=['create', 'add', 'remove']),
                        count=dict(type='int')
                    )),
                    qos_policy=dict(type='str'),
                    snapshot_policy=dict(type='str'),
                )),
                luns=dict(type='list', elements='dict', options=dict(
                    name=dict(required=True, type='str'),
                    size=dict(type='int'),
                    size_unit=dict(type='str', choices=['bytes', 'b', 'kb', 'mb', 'gb', 'tb',
                                                        'pb', 'eb', 'zb', 'yb']),
                    provisioning_options=dict(type='dict', options=dict(
                        action=dict(type='str', choices=['create']),
                        count=dict(type='int')
                    )),
                    os_type=dict(type='str'),
                    lun_maps=dict(type='list', elements='dict', options=dict(
                        igroup_name=dict(type='str'),
                        igroup_initiators=dict(type='list', elements='str'),
                        os_type=dict(type='str'),
                    )),
                )),
                namespaces=dict(type='list', elements='dict', options=dict(
                    name=dict(required=True, type='str'),
                    size=dict(type='int'),
                    size_unit=dict(type='str', choices=['bytes', 'b', 'kb', 'mb', 'gb', 'tb',
                                                        'pb', 'eb', 'zb', 'yb']),
                    os_type=dict(type='str'),
                    provisioning_options=dict(type='dict', options=dict(
                        action=dict(type='str', choices=['create']),
                        count=dict(type='int')
                    )),
                )),
                qos_policy=dict(type='str'),
                snapshot_policy=dict(type='str'),
            )),
            qos_policy=dict(type='str'),
            snapshot_policy=dict(type='str'),
        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
        self.uuid = None
        self.na_helper = NetAppModule(self.module)
        self.parameters = self.na_helper.check_and_set_parameters(self.module)
        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        self.rest_api.fail_if_not_rest_minimum_version('na_ontap_cg:', 9, 10, 1)
        self.validate_options()
        self.validate_size_parameters()

    def validate_size_parameters(self):
        def convert_size_parameters(source_params):
            if 'volumes' in source_params and source_params.get('volumes'):
                for volume in source_params['volumes']:
                    if volume.get('size') is not None:
                        volume['size'] *= netapp_utils.POW2_BYTE_MAP[volume.get('size_unit')]
                        volume.pop('size_unit')
            if 'luns' in source_params and source_params.get('luns'):
                for lun in source_params['luns']:
                    if lun.get('size') is not None:
                        lun['size'] *= netapp_utils.POW2_BYTE_MAP[lun.get('size_unit')]
                        lun.pop('size_unit')
            if 'namespaces' in source_params and source_params.get('namespaces'):
                for namespace in source_params['namespaces']:
                    if namespace.get('size') is not None:
                        namespace['size'] *= netapp_utils.POW2_BYTE_MAP[namespace.get('size_unit')]
                        namespace.pop('size_unit')

        convert_size_parameters(self.parameters)
        if 'consistency_groups' in self.parameters and self.parameters['consistency_groups']:
            for cg in self.parameters['consistency_groups']:
                convert_size_parameters(cg)

    def validate_options(self):
        """ validate ONTAP version supports the options provided in the parameters """
        if 'consistency_groups' in self.parameters and self.parameters['consistency_groups']:
            for cg in self.parameters['consistency_groups']:
                if self.na_helper.safe_get(cg, ['provisioning_options', 'name']) and not self.rest_api.meets_rest_minimum_version(True, 9, 13, 1):
                    self.module.fail_json(msg="The 'name' option under 'provisioning_options' for consistency groups requires ONTAP 9.13.1 or later.")

    def get_consistency_group_rest(self):
        """ Retrieve details of a specific consistency group """
        api = "application/consistency-groups"
        params = {'name': self.parameters['name'],
                  'svm.name': self.parameters['vserver'],
                  'fields': 'name,'
                            'uuid,'}
        if 'volumes' in self.parameters and self.parameters['volumes']:
            params['fields'] += 'volumes,'
        if 'luns' in self.parameters and self.parameters['luns']:
            params['fields'] += 'luns,'
        if 'namespaces' in self.parameters and self.parameters['namespaces']:
            params['fields'] += 'namespaces,'
        if 'consistency_groups' in self.parameters and self.parameters['consistency_groups']:
            params['fields'] += 'consistency_groups,'
        if 'qos_policy' in self.parameters:
            params['fields'] += 'qos.policy.name,'
        if 'snapshot_policy' in self.parameters:
            params['fields'] += 'snapshot_policy.name,'
        record, error = rest_generic.get_one_record(self.rest_api, api, params)
        if error:
            self.module.fail_json(msg="Error retrieving consistency group %s: %s" % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        if record:
            self.uuid = record['uuid']
            volumes = self.format_volmues_info(record.get('volumes', []))
            luns = self.format_luns_info(record.get('luns', []))
            namespaces = self.format_namespaces_info(record.get('namespaces', []))
            consistency_groups = self.format_consistency_groups_info(record.get('consistency_groups', []))
            return {
                'name': record.get('name'),
                'qos_policy': self.na_helper.safe_get(record, ['qos', 'policy', 'name']),
                'snapshot_policy': self.na_helper.safe_get(record, ['snapshot_policy', 'name']),
                'volumes': volumes,
                'luns': luns,
                'namespaces': namespaces,
                'consistency_groups': consistency_groups
            }
        return None

    def format_volmues_info(self, volumes):
        """ Formats the volumes information from the parent list provided """
        volumes_info = []
        for volume in volumes:
            volume_info = {
                'name': volume.get('name'),
                'size': self.na_helper.safe_get(volume, ['space', 'size']),
                'qos_policy': self.na_helper.safe_get(volume, ['qos', 'policy', 'name']),
                'snapshot_policy': self.na_helper.safe_get(volume, ['snapshot_policy', 'name']),
            }
            volumes_info.append(volume_info)
        return volumes_info

    def format_luns_info(self, luns):
        """ Formats the luns information from the parent list provided """
        luns_info = []
        for lun in luns:
            lun_info = {
                'name': lun.get('name'),
                'size': self.na_helper.safe_get(lun, ['space', 'size']),
                'os_type': lun.get('os_type'),
            }
            if self.na_helper.safe_get(lun, ['lun_maps']):
                lun_info['lun_maps'] = []
                for lun_map in lun['lun_maps']:
                    lun_map_info = {
                        'igroup_name': self.na_helper.safe_get(lun_map, ['igroup', 'name']),
                        'igroup_initiators': [initiator['name'] for initiator in self.na_helper.safe_get(lun_map, ['igroup', 'initiators'], [])],
                        'os_type': lun.get('os_type'),
                    }
                    lun_info['lun_maps'].append(lun_map_info)
            luns_info.append(lun_info)
        return luns_info

    def format_namespaces_info(self, namespaces):
        """ Formats the namespaces information from the parent list provided """
        namespaces_info = []
        for namespace in namespaces:
            namespace_info = {
                'name': namespace.get('name'),
                'size': self.na_helper.safe_get(namespace, ['space', 'size']),
                'os_type': namespace.get('os_type'),
            }
            namespaces_info.append(namespace_info)
        return namespaces_info

    def format_consistency_groups_info(self, consistency_groups):
        """ Formats the consistency groups information """
        consistency_groups_info = []
        for cg in consistency_groups:
            cg_info = {
                'name': cg.get('name'),
                'qos_policy': self.na_helper.safe_get(cg, ['qos', 'policy', 'name']),
                'snapshot_policy': self.na_helper.safe_get(cg, ['snapshot_policy', 'name']),
            }
            if self.na_helper.safe_get(cg, ['volumes']):
                cg_info['volumes'] = self.format_volmues_info(cg['volumes'])
            if self.na_helper.safe_get(cg, ['luns']):
                cg_info['luns'] = self.format_luns_info(cg['luns'])
            if self.na_helper.safe_get(cg, ['namespaces']):
                cg_info['namespaces'] = self.format_namespaces_info(cg['namespaces'])
            consistency_groups_info.append(cg_info)
        return consistency_groups_info

    def create_consistency_group_rest(self):
        """ Creates a consistency group """
        api = "application/consistency-groups"
        body = {
            'name': self.parameters['name'],
            'svm': {
                'name': self.parameters['vserver']
            }
        }
        if self.parameters.get('qos_policy') is not None:
            body['qos.policy.name'] = self.parameters['qos_policy']
        if self.parameters.get('snapshot_policy') is not None:
            body['snapshot_policy.name'] = self.parameters['snapshot_policy']
        if self.parameters.get('volumes'):
            body['volumes'] = self.format_volumes_body(self.parameters['volumes'])
        if self.parameters.get('luns'):
            body['luns'] = self.format_luns_body(self.parameters['luns'])
        if self.parameters.get('namespaces'):
            body['namespaces'] = self.format_namespaces_body(self.parameters['namespaces'])
        if self.parameters.get('consistency_groups'):
            body['consistency_groups'] = self.format_consistency_groups_body(self.parameters['consistency_groups'])

        dummy, error = rest_generic.post_async(self.rest_api, api, body=body)
        if error:
            self.module.fail_json(msg='Error creating consistency group %s: %s.' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def format_volumes_body(self, volumes):
        """ Formats the volumes body for create/modify operation """
        volumes_body = []
        for volume in volumes:
            volume_body = {
                'name': volume.get('name'),
            }
            if volume.get('size') is not None:
                volume_body['space.size'] = volume['size']
            if volume.get('qos_policy') is not None:
                volume_body['qos.policy.name'] = volume.get('qos_policy')
            if volume.get('snapshot_policy') is not None:
                volume_body['snapshot_policy.name'] = volume.get('snapshot_policy')
            if volume.get('provisioning_options'):
                if volume['provisioning_options'].get('action') is not None:
                    volume_body['provisioning_options'] = {
                        'action': volume['provisioning_options']['action']
                    }
                if volume['provisioning_options'].get('count') is not None:
                    volume_body['provisioning_options']['count'] = volume['provisioning_options']['count']
            volumes_body.append(volume_body)
        return volumes_body

    def format_luns_body(self, luns):
        """ Formats the luns body for create/modify operation """
        luns_body = []
        for lun in luns:
            lun_body = {
                'name': lun.get('name'),
            }
            if lun.get('size') is not None:
                lun_body['space.size'] = lun['size']
            if lun.get('provisioning_options'):
                if lun['provisioning_options'].get('action') is not None:
                    lun_body['provisioning_options'] = {
                        'action': lun['provisioning_options']['action']
                    }
                if lun['provisioning_options'].get('count') is not None:
                    lun_body['provisioning_options']['count'] = lun['provisioning_options']['count']
            if lun.get('os_type') is not None:
                lun_body['os_type'] = lun.get('os_type')
            if lun.get('lun_maps') and lun.get('lun_maps') != []:
                lun_body['lun_maps'] = []
                for lun_map in lun['lun_maps']:
                    lun_map_body = {'igroup': {}}
                    if 'igroup_name' in lun_map:
                        lun_map_body['igroup']['name'] = lun_map['igroup_name']
                    if 'igroup_initiators' in lun_map:
                        lun_map_body['igroup']['initiators'] = lun_map['igroup_initiators']
                    if 'os_type' in lun_map:
                        lun_map_body['igroup']['os_type'] = lun_map['os_type']
                    lun_body['lun_maps'].append(lun_map_body)
            luns_body.append(lun_body)
        return luns_body

    def format_namespaces_body(self, namespaces):
        """ Formats the namespaces body for create/modify operation """
        namespaces_body = []
        for namespace in namespaces:
            namespace_body = {
                'name': namespace.get('name'),
            }
            if namespace.get('size') is not None:
                namespace_body['space.size'] = namespace['size']
            if namespace.get('os_type') is not None:
                namespace_body['os_type'] = namespace.get('os_type')
            if namespace.get('provisioning_options'):
                if namespace['provisioning_options'].get('action') is not None:
                    namespace_body['provisioning_options'] = {
                        'action': namespace['provisioning_options']['action']
                    }
                if namespace['provisioning_options'].get('count') is not None:
                    namespace_body['provisioning_options']['count'] = namespace['provisioning_options']['count']
            namespaces_body.append(namespace_body)
        return namespaces_body

    def format_consistency_groups_body(self, consistency_groups):
        """ Formats the consistency groups body for create/modify operation """
        consistency_groups_body = []
        for cg in consistency_groups:
            cg_body = {
                'name': cg.get('name'),
            }
            if cg.get('qos_policy') is not None:
                cg_body['qos.policy.name'] = cg.get('qos_policy')
            if cg.get('snapshot_policy') is not None:
                cg_body['snapshot_policy.name'] = cg.get('snapshot_policy')
            if cg.get('provisioning_options'):
                if cg['provisioning_options'].get('action') is not None:
                    cg_body['provisioning_options'] = {
                        'action': cg['provisioning_options']['action']
                    }
                if cg['provisioning_options'].get('name') is not None:
                    cg_body['provisioning_options']['name'] = cg['provisioning_options']['name']
            if cg.get('volumes'):
                cg_body['volumes'] = self.format_volumes_body(cg['volumes'])
            if cg.get('luns'):
                cg_body['luns'] = self.format_luns_body(cg['luns'])
            if cg.get('namespaces'):
                cg_body['namespaces'] = self.format_namespaces_body(cg['namespaces'])
            consistency_groups_body.append(cg_body)
        return consistency_groups_body

    def modify_consistency_group_rest(self, modify):
        """ Modifies a consistency group """
        api = "application/consistency-groups"
        dummy, error = rest_generic.patch_async(self.rest_api, api, uuid_or_name=self.uuid, body=modify)
        if error:
            self.module.fail_json(msg='Error modifying consistency group %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        return

    def set_modify_dict(self, current, modify):
        """ Sets the modify dict for update operation """
        modify_dict = {}
        if 'snapshot_policy' in modify:
            modify_dict['snapshot_policy.name'] = modify['snapshot_policy']

        # volumes
        if self.parameters.get('volumes') and self.parameters.get('volumes') != []:
            modify_volumes = self.set_volumes_modify_list(current.get('volumes', []),
                                                          self.na_helper.filter_out_none_entries(self.parameters.get('volumes', [])))
            if modify_volumes and modify_volumes != []:
                modify_dict['volumes'] = self.format_volumes_body(modify_volumes)
        # luns
        if self.parameters.get('luns') and self.parameters.get('luns') != []:
            modify_luns = self.set_luns_modify_list(current.get('luns', []),
                                                    self.na_helper.filter_out_none_entries(self.parameters.get('luns', [])))
            if modify_luns and modify_luns != []:
                modify_dict['luns'] = self.format_luns_body(modify_luns)
        # namespaces
        if self.parameters.get('namespaces') and self.parameters.get('namespaces') != []:
            modify_namespaces = self.set_namespaces_modify_list(current.get('namespaces', []),
                                                                self.na_helper.filter_out_none_entries(self.parameters.get('namespaces', [])))
            if modify_namespaces and modify_namespaces != []:
                modify_dict['namespaces'] = self.format_namespaces_body(modify_namespaces)
        # consistyency groups
        if self.parameters.get('consistency_groups') and self.parameters.get('consistency_groups') != []:
            modify_cgs = []
            current_cgs_dict = {cg['name']: cg for cg in current.get('consistency_groups', [])}
            for cg in self.parameters['consistency_groups']:
                if cg.get('provisioning_options'):
                    if cg['provisioning_options'].get('action') in ('create', 'add'):
                        if cg.get('name') in current_cgs_dict:
                            cg.pop('provisioning_options')
                            cg_modify = self.set_cgs_modify_list(cg, current_cgs_dict)
                            if cg_modify:
                                cg_modify['name'] = cg['name']
                                modify_cgs.append(cg_modify)
                        else:
                            modify_cgs.append(self.na_helper.filter_out_none_entries(cg))
                    elif cg['provisioning_options'].get('action') == 'remove':
                        if cg.get('name') in current_cgs_dict.keys():
                            modify_cg = {'name': cg['name'], 'provisioning_options': {'action': 'remove'}}
                            if self.na_helper.safe_get(cg, ['provisioning_options', 'name']) is not None:
                                modify_cg['provisioning_options']['name'] = cg['provisioning_options']['name']
                            modify_cgs.append(modify_cg)

            if modify_cgs and modify_cgs != []:
                cgs_to_be_modified = [cg['name'] for cg in modify_cgs]
                # add existing elements to the patch body
                for current_cg in current_cgs_dict.values():
                    if current_cg['name'] not in cgs_to_be_modified:
                        modify_cgs.append({'name': current_cg['name']})
                modify_dict['consistency_groups'] = self.format_consistency_groups_body(modify_cgs)

        return modify_dict if modify_dict else None

    def set_cgs_modify_list(self, cg, current_cgs_dict):
        """ Formats the modify dict for given consistency groups list
            "consistency-groups" does not support removing elements via PATCH.
            All existing elements with any changes must be included in the list during PATCH. """
        cg_modify_dict = {}
        if cg.get('snapshot_policy') and cg.get('snapshot_policy') != current_cgs_dict[cg['name']].get('snapshot_policy'):
            cg_modify_dict['snapshot_policy'] = cg.get('snapshot_policy')
        if cg.get('volumes') and cg.get('volumes') != []:
            cg_modify_volumes = self.set_volumes_modify_list(
                current_cgs_dict[cg['name']].get('volumes', []), self.na_helper.filter_out_none_entries(cg.get('volumes', [])))
            if cg_modify_volumes and cg_modify_volumes != []:
                cg_modify_dict['volumes'] = cg_modify_volumes
        if cg.get('luns') and cg.get('luns') != []:
            cg_modify_luns = self.set_luns_modify_list(
                current_cgs_dict[cg['name']].get('luns', []), self.na_helper.filter_out_none_entries(cg.get('luns', [])))
            if cg_modify_luns and cg_modify_luns != []:
                cg_modify_dict['luns'] = cg_modify_luns
        if cg.get('namespaces') and cg.get('namespaces') != []:
            cg_modify_namespaces = self.set_namespaces_modify_list(
                current_cgs_dict[cg['name']].get('namespaces', []), self.na_helper.filter_out_none_entries(cg.get('namespaces', [])))
            if cg_modify_namespaces and cg_modify_namespaces != []:
                cg_modify_dict['namespaces'] = cg_modify_namespaces
        return cg_modify_dict if cg_modify_dict else None

    def set_volumes_modify_list(self, current_volumes, source_volumes):
        """ Formats the modify dict for given volumes list
            "volumes" does not support removing elements via PATCH.
            All existing elements with any changes must be included in the list during PATCH. """
        current_volumes_dict = {volume['name']: volume for volume in current_volumes}
        filtered_source_volumes = copy.deepcopy(source_volumes)
        volumes_modify = []
        for volume in source_volumes:
            if volume.get('provisioning_options'):
                if volume['provisioning_options'].get('action') in ('create', 'add'):
                    if volume.get('name') in current_volumes_dict:
                        volume.pop('provisioning_options')
                        volume_modify = self.na_helper.get_modified_attributes(current_volumes_dict[volume['name']], volume)
                        if volume_modify:
                            volume_modify['name'] = volume['name']
                            volumes_modify.append(volume_modify)
                    else:
                        volumes_modify.append(volume)
                elif volume['provisioning_options'].get('action') == 'remove':
                    if volume.get('name') not in current_volumes_dict:
                        filtered_source_volumes.remove(volume)
                    else:
                        volumes_modify.append(volume)
        if volumes_modify:
            volumes_to_be_modified = [volume['name'] for volume in volumes_modify]
            # add existing elements to the patch body
            for current_vol in current_volumes:
                if current_vol['name'] not in volumes_to_be_modified:
                    volumes_modify.append({'name': current_vol['name']})
        return volumes_modify if volumes_modify else None

    def set_luns_modify_list(self, current_luns, source_luns):
        """ Formats the modify dict for given luns list
            "luns" does not support removing elements via PATCH.
            All existing elements with any changes must be included in the list during PATCH. """
        current_luns_dict = {lun['name']: lun for lun in current_luns}
        luns_modify = []
        for lun in source_luns:
            if lun.get('provisioning_options'):
                if lun['provisioning_options'].get('action') == 'create':
                    if lun.get('name') in current_luns_dict:
                        lun.pop('provisioning_options')
                        lun_modify = self.na_helper.get_modified_attributes(current_luns_dict[lun['name']], lun)
                        if lun_modify:
                            lun_modify['name'] = lun['name']
                            luns_modify.append(lun_modify)
                    else:
                        luns_modify.append(lun)
        if luns_modify:
            luns_to_be_modified = [lun['name'] for lun in luns_modify]
            # add existing elements to the patch body
            for current_lun in current_luns:
                if current_lun['name'] not in luns_to_be_modified:
                    luns_modify.append({'name': current_lun['name']})
        return luns_modify if luns_modify else None

    def set_namespaces_modify_list(self, current_namespaces, source_namespaces):
        """ Formats the modify dict for given namespaces list
            "namespaces" does not support removing elements via PATCH.
            All existing elements with any changes must be included in the list during PATCH. """
        current_namespaces_dict = {namespace['name']: namespace for namespace in current_namespaces}
        namespaces_modify = []
        for namespace in source_namespaces:
            if namespace.get('provisioning_options'):
                if namespace['provisioning_options'].get('action') == 'create':
                    if namespace.get('name') in current_namespaces_dict:
                        namespace.pop('provisioning_options')
                        namespace_modify = self.na_helper.get_modified_attributes(current_namespaces_dict[namespace['name']], namespace)
                        if namespace_modify:
                            namespace_modify['name'] = namespace['name']
                            namespaces_modify.append(namespace_modify)
                    else:
                        namespaces_modify.append(namespace)
        if namespaces_modify:
            namespaces_to_be_modified = [namespace['name'] for namespace in namespaces_modify]
            # add existing elements to the patch body
            for current_namespace in current_namespaces:
                if current_namespace['name'] not in namespaces_to_be_modified:
                    namespaces_modify.append({'name': current_namespace['name']})
        return namespaces_modify if namespaces_modify else None

    def delete_consistency_group_rest(self):
        api = "application/consistency-groups"
        dummy, error = rest_generic.delete_async(self.rest_api, api, self.uuid)
        if error:
            self.module.fail_json(msg='Error deleting consistency group %s: %s' % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def apply(self):
        cd_action, modify, validated_modify = None, None, None
        current = self.get_consistency_group_rest()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if cd_action is None:
            modify = self.na_helper.get_modified_attributes(current, self.parameters)

        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.create_consistency_group_rest()
            if cd_action == 'delete':
                self.delete_consistency_group_rest()
            if modify:
                validated_modify = self.set_modify_dict(current, modify)
                if not validated_modify:
                    self.na_helper.changed = False
                else:
                    self.modify_consistency_group_rest(validated_modify)
        result = netapp_utils.generate_result(self.na_helper.changed, cd_action, validated_modify)
        self.module.exit_json(**result)


def main():
    consistency_group = NetAppOntapConsistencyGroup()
    consistency_group.apply()


if __name__ == '__main__':
    main()
