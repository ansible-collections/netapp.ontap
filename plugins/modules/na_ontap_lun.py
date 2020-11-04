#!/usr/bin/python

# (c) 2017-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_lun
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''

module: na_ontap_lun

short_description: NetApp ONTAP manage LUNs
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
- Create, destroy, resize LUNs on NetApp ONTAP.

options:

  state:
    description:
    - Whether the specified LUN should exist or not.
    choices: ['present', 'absent']
    type: str
    default: present

  name:
    description:
    - The name of the LUN to manage.
    required: true
    type: str

  flexvol_name:
    description:
    - The name of the FlexVol the LUN should exist on.
    required: true
    type: str

  size:
    description:
    - The size of the LUN in C(size_unit).
    - Required when C(state=present).
    type: int

  size_unit:
    description:
    - The unit used to interpret the size parameter.
    choices: ['bytes', 'b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb', 'zb', 'yb']
    default: 'gb'
    type: str

  force_resize:
    description:
      Forcibly reduce the size. This is required for reducing the size of the LUN to avoid accidentally
      reducing the LUN size.
    type: bool
    default: false

  force_remove:
    description:
    - If "true", override checks that prevent a LUN from being destroyed if it is online and mapped.
    - If "false", destroying an online and mapped LUN will fail.
    type: bool
    default: false

  force_remove_fenced:
    description:
    - If "true", override checks that prevent a LUN from being destroyed while it is fenced.
    - If "false", attempting to destroy a fenced LUN will fail.
    - The default if not specified is "false". This field is available in Data ONTAP 8.2 and later.
    type: bool
    default: false

  vserver:
    required: true
    description:
    - The name of the vserver to use.
    type: str

  ostype:
    description:
    - The os type for the LUN.
    default: 'image'
    type: str

  space_reserve:
    description:
    - This can be set to "false" which will create a LUN without any space being reserved.
    type: bool
    default: True

  space_allocation:
    description:
    - This enables support for the SCSI Thin Provisioning features.  If the Host and file system do
      not support this do not enable it.
    type: bool
    default: False
    version_added: 2.7.0

  use_exact_size:
    description:
    - This can be set to "False" which will round the LUN >= 450g.
    type: bool
    default: True
    version_added: 20.11.0

'''

EXAMPLES = """
- name: Create LUN
  na_ontap_lun:
    state: present
    name: ansibleLUN
    flexvol_name: ansibleVolume
    vserver: ansibleVServer
    size: 5
    size_unit: mb
    ostype: linux
    space_reserve: True
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"

- name: Resize LUN
  na_ontap_lun:
    state: present
    name: ansibleLUN
    force_resize: True
    flexvol_name: ansibleVolume
    vserver: ansibleVServer
    size: 5
    size_unit: gb
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
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapLUN(object):
    ''' create, modify, delete LUN '''
    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str'),
            size=dict(type='int'),
            size_unit=dict(default='gb',
                           choices=['bytes', 'b', 'kb', 'mb', 'gb', 'tb',
                                    'pb', 'eb', 'zb', 'yb'], type='str'),
            force_resize=dict(default=False, type='bool'),
            force_remove=dict(default=False, type='bool'),
            force_remove_fenced=dict(default=False, type='bool'),
            flexvol_name=dict(required=True, type='str'),
            vserver=dict(required=True, type='str'),
            ostype=dict(required=False, type='str', default='image'),
            space_reserve=dict(required=False, type='bool', default=True),
            space_allocation=dict(required=False, type='bool', default=False),
            use_exact_size=dict(required=False, type='bool', default=True),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            required_if=[
                ('state', 'present', ['size'])
            ],
            supports_check_mode=True
        )

        # set up state variables
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        if self.parameters.get('size') is not None:
            self.parameters['size'] *= netapp_utils.POW2_BYTE_MAP[self.parameters['size_unit']]

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def get_luns(self):
        """
        Return list of LUNs matching vserver and volume names.

        :return: list of LUNs in XML format.
        :rtype: list
        """
        luns = []
        tag = None
        while True:
            lun_info = netapp_utils.zapi.NaElement('lun-get-iter')
            if tag:
                lun_info.add_new_child('tag', tag, True)

            query_details = netapp_utils.zapi.NaElement('lun-info')
            query_details.add_new_child('vserver', self.parameters['vserver'])
            query_details.add_new_child('volume', self.parameters['flexvol_name'])

            query = netapp_utils.zapi.NaElement('query')
            query.add_child_elem(query_details)

            lun_info.add_child_elem(query)

            result = self.server.invoke_successfully(lun_info, True)
            if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) >= 1:
                attr_list = result.get_child_by_name('attributes-list')
                luns.extend(attr_list.get_children())

            tag = result.get_child_content('next-tag')

            if tag is None:
                break
        return luns

    def get_lun_details(self, name, lun):
        """
        Extract LUN details, from XML to python dict

        :return: Details about the lun
        :rtype: dict
        """
        return_value = dict(name=name)
        return_value['size'] = int(lun.get_child_content('size'))
        bool_attr_map = {
            'is-space-alloc-enabled': 'space_allocation',
            'is-space-reservation-enabled': 'space_reserve'
        }
        for attr in bool_attr_map:
            value = lun.get_child_content(attr)
            if value is not None:
                return_value[bool_attr_map[attr]] = self.na_helper.get_value_for_bool(True, value)
        attr = 'multiprotocol-type'
        value = lun.get_child_content(attr)
        if value is not None:
            return_value['ostype'] = value

        # Find out if the lun is attached
        attached_to = None
        lun_id = None
        if lun.get_child_content('mapped') == 'true':
            lun_map_list = netapp_utils.zapi.NaElement.create_node_with_children(
                'lun-map-list-info', **{'path': lun.get_child_content('path')})
            result = self.server.invoke_successfully(
                lun_map_list, enable_tunneling=True)
            igroups = result.get_child_by_name('initiator-groups')
            if igroups:
                for igroup_info in igroups.get_children():
                    igroup = igroup_info.get_child_content(
                        'initiator-group-name')
                    attached_to = igroup
                    lun_id = igroup_info.get_child_content('lun-id')

        return_value.update({
            'attached_to': attached_to,
            'lun_id': lun_id
        })
        return return_value

    def get_lun(self):
        """
        Return details about the LUN

        :return: Details about the lun
        :rtype: dict
        """
        return_value = dict()
        luns = self.get_luns()
        # The LUNs have been extracted.
        # Find the specified lun and extract details.
        for lun in luns:
            path = lun.get_child_content('path')
            _rest, _splitter, found_name = path.rpartition('/')

            if found_name == self.parameters['name']:
                return_value = self.get_lun_details(found_name, lun)
                break

        return return_value if return_value else None

    def create_lun(self):
        """
        Create LUN with requested name and size
        """
        path = '/vol/%s/%s' % (self.parameters['flexvol_name'], self.parameters['name'])
        lun_create = netapp_utils.zapi.NaElement.create_node_with_children(
            'lun-create-by-size', **{'path': path,
                                     'size': str(self.parameters['size']),
                                     'ostype': self.parameters['ostype'],
                                     'space-reservation-enabled': str(self.parameters['space_reserve']),
                                     'space-allocation-enabled': str(self.parameters['space_allocation']),
                                     'use-exact-size': str(self.parameters['use_exact_size'])})

        try:
            self.server.invoke_successfully(lun_create, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            self.module.fail_json(msg="Error provisioning lun %s of size %s: %s"
                                  % (self.parameters['name'], self.parameters['size'], to_native(exc)),
                                  exception=traceback.format_exc())

    def delete_lun(self):
        """
        Delete requested LUN
        """
        path = '/vol/%s/%s' % (self.parameters['flexvol_name'], self.parameters['name'])

        lun_delete = netapp_utils.zapi.NaElement.create_node_with_children(
            'lun-destroy', **{'path': path,
                              'force': str(self.parameters['force_remove']),
                              'destroy-fenced-lun':
                                  str(self.parameters['force_remove_fenced'])})

        try:
            self.server.invoke_successfully(lun_delete, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            self.module.fail_json(msg="Error deleting lun %s: %s" % (path, to_native(exc)),
                                  exception=traceback.format_exc())

    def resize_lun(self):
        """
        Resize requested LUN.

        :return: True if LUN was actually re-sized, false otherwise.
        :rtype: bool
        """
        path = '/vol/%s/%s' % (self.parameters['flexvol_name'], self.parameters['name'])

        lun_resize = netapp_utils.zapi.NaElement.create_node_with_children(
            'lun-resize', **{'path': path,
                             'size': str(self.parameters['size']),
                             'force': str(self.parameters['force_resize'])})
        try:
            self.server.invoke_successfully(lun_resize, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            if to_native(exc.code) == "9042":
                # Error 9042 denotes the new LUN size being the same as the
                # old LUN size. This happens when there's barely any difference
                # in the two sizes. For example, from 8388608 bytes to
                # 8194304 bytes. This should go away if/when the default size
                # requested/reported to/from the controller is changed to a
                # larger unit (MB/GB/TB).
                return False
            else:
                self.module.fail_json(msg="Error resizing lun %s: %s" % (path, to_native(exc)),
                                      exception=traceback.format_exc())

        return True

    def set_lun_value(self, key, value):
        key_to_zapi = dict(
            space_allocation='lun-set-space-alloc',
            space_reserve='lun-set-space-reservation-info'
        )
        if key in key_to_zapi:
            zapi = key_to_zapi[key]
        else:
            self.module.fail_json(msg="option %s cannot be modified to %s" % (key, value))

        path = '/vol/%s/%s' % (self.parameters['flexvol_name'], self.parameters['name'])
        enable = self.na_helper.get_value_for_bool(False, value)
        lun_set = netapp_utils.zapi.NaElement.create_node_with_children(zapi, path=path, enable=enable)
        try:
            self.server.invoke_successfully(lun_set, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as exc:
            self.module.fail_json(msg="Error setting lun option %s: %s" % (key, to_native(exc)),
                                  exception=traceback.format_exc())
        return

    def modify_lun(self, modify):
        """
        update LUN properties (except size or name)
        """
        for key, value in modify.items():
            self.set_lun_value(key, value)

    def apply(self):
        netapp_utils.ems_log_event("na_ontap_lun", self.server)
        current = self.get_lun()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        modify = None
        if cd_action is None and self.parameters['state'] == 'present':
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if cd_action == 'create' and self.parameters.get('size') is None:
            self.module.fail_json(msg="size is a required parameter for create.")
        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.create_lun()
            elif cd_action == 'delete':
                self.delete_lun()
            else:
                size_changed = False
                if 'size' in modify:
                    # Ensure that size was actually changed. Please
                    # read notes in 'resize_lun' function for details.
                    size_changed = self.resize_lun()
                    modify.pop('size')
                if modify:
                    self.modify_lun(modify)
                else:
                    self.na_helper.changed = size_changed

        self.module.exit_json(changed=self.na_helper.changed)


def main():
    lun = NetAppOntapLUN()
    lun.apply()


if __name__ == '__main__':
    main()
