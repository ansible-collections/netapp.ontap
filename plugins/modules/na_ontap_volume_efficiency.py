#!/usr/bin/python

# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
module: na_ontap_volume_efficiency
short_description: NetApp ONTAP enables, disables or modifies volume efficiency
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '21.2.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Enable, modify or disable volume efficiency
options:
  state:
    description:
    - Whether the specified volume efficiency should be enabled or not.
    choices: ['present', 'absent']
    default: present
    type: str

  vserver:
    description:
    - Specifies the vserver for the volume.
    required: true
    type: str

  path:
    description:
    - Specifies the path for the volume.
    required: true
    type: str

  schedule:
    description:
    - Specifies the storage efficiency schedule.
    type: str

  policy:
    description:
    - Specifies the storage efficiency policy to use, only supported on AFF systems.
    choices: ['auto', 'default', 'inline-only', '-']
    type: str

  enable_compression:
    description:
    - Specifies if compression is to be enabled.
    type: bool

  enable_inline_compression:
    description:
    - Specifies if in-line compression is to be enabled.
    type: bool

  enable_inline_dedupe:
    description:
    - Specifies if in-line deduplication is to be enabled, only supported on AFF systems or hybrid aggregates.
    type: bool

  enable_data_compaction:
    description:
    - Specifies if compaction is to be enabled.
    type: bool

  enable_cross_volume_inline_dedupe:
    description:
    - Specifies if in-line cross volume inline deduplication is to be enabled, this can only be enabled when inline deduplication is enabled.
    type: bool

  enable_cross_volume_background_dedupe:
    description:
    - Specifies if cross volume background deduplication is to be enabled, this can only be enabled when inline deduplication is enabled.
    type: bool

  volume_efficiency:
    description:
    - Start or Stop a volume efficiency operation on a given volume path.
    choices: ['start', 'stop']
    version_added: '21.4.0'
    type: str

  start_ve_scan_all:
    description:
    - Specifies the scanner to scan the entire volume without applying share block optimization.
    version_added: '21.4.0'
    type: bool

  start_ve_build_metadata:
    description:
    - Specifies the scanner to scan the entire and generate fingerprint database without attempting the sharing.
    version_added: '21.4.0'
    type: bool

  start_ve_delete_checkpoint:
    description:
    - Specifies the scanner to delete existing checkpoint and start the operation from the begining.
    version_added: '21.4.0'
    type: bool

  start_ve_queue_operation:
    description:
    - Specifies the operation to queue if an exisitng operation is already running on the volume and in the fingerprint verification phase.
    version_added: '21.4.0'
    type: bool

  start_ve_scan_old_data:
    description:
    - Specifies the operation to scan the file system to process all the existing data.
    version_added: '21.4.0'
    type: bool

  start_ve_qos_policy:
    description:
    - Specifies the QoS policy for the operation.
    choices: ['background', 'best-effort']
    default: best-effort
    version_added: '21.4.0'
    type: str

  stop_ve_all_operations:
    description:
    - Specifies that all running and queued operations to be stopped.
    version_added: '21.4.0'
    type: bool

"""

EXAMPLES = """
    - name: Enable Volume efficiency
      na_ontap_volume_efficiency:
        state: present
        vserver: "TESTSVM"
        path: "/vol/test_sis"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Disable Volume efficiency test
      na_ontap_volume_efficiency:
        state: absent
        vserver: "TESTSVM"
        path: "/vol/test_sis"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Modify storage efficiency policy
      na_ontap_volume_efficiency:
        state: present
        vserver: "TESTSVM"
        path: "/vol/test_sis"
        schedule: "mon-sun@0,1,23"
        enable_compression: "True"
        enable_inline_compression: "True"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Start volume efficiency
      na_ontap_volume_efficiency:
        state: present
        vserver: "TESTSVM"
        volume_efficiency: "start"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: true
        validate_certs: false

    - name: Stop volume efficiency
      na_ontap_volume_efficiency:
        state: present
        vserver: "TESTSVM"
        volume_efficiency: "stop"
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
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapVolumeEfficiency(object):
    """
        Creates, Modifies and Disables a Volume Efficiency
    """
    def __init__(self):
        """
            Initialize the ONTAP Volume Efficiency class
        """
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            vserver=dict(required=True, type='str'),
            path=dict(required=True, type='str'),
            schedule=dict(required=False, type='str'),
            policy=dict(required=False, choices=['auto', 'default', 'inline-only', '-'], type='str'),
            enable_inline_compression=dict(required=False, type='bool'),
            enable_compression=dict(required=False, type='bool'),
            enable_inline_dedupe=dict(required=False, type='bool'),
            enable_data_compaction=dict(required=False, type='bool'),
            enable_cross_volume_inline_dedupe=dict(required=False, type='bool'),
            enable_cross_volume_background_dedupe=dict(required=False, type='bool'),
            volume_efficiency=dict(required=False, choices=['start', 'stop'], type='str'),
            start_ve_scan_all=dict(required=False, type='bool'),
            start_ve_build_metadata=dict(required=False, type='bool'),
            start_ve_delete_checkpoint=dict(required=False, type='bool'),
            start_ve_queue_operation=dict(required=False, type='bool'),
            start_ve_scan_old_data=dict(required=False, type='bool'),
            start_ve_qos_policy=dict(required=False, choices=['background', 'best-effort'], type='str', default='best-effort'),
            stop_ve_all_operations=dict(required=False, type='bool')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True,
            required_if=[('start_ve_scan_all', True, ['start_ve_scan_old_data'])],
            mutually_exclusive=[('policy', 'schedule')]
        )

        # set up variables
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        if self.parameters['state'] == 'present':
            self.parameters['enabled'] = 'enabled'
        else:
            self.parameters['enabled'] = 'disabled'

        if 'volume_efficiency' in self.parameters:
            if self.parameters['volume_efficiency'] == 'start':
                self.parameters['status'] = 'running'
            else:
                self.parameters['status'] = 'idle'

        self.rest_api = OntapRestAPI(self.module)
        self.use_rest = self.rest_api.is_rest()

        if not self.use_rest:
            if HAS_NETAPP_LIB is False:
                self.module.fail_json(msg="the python NetApp-Lib module is required")
            else:
                self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def get_volume_efficiency(self):
        """
        get the storage efficiency for a given path
        :return: dict of sis if exist, None if not
        """

        return_value = None

        if self.use_rest:
            api = 'private/cli/volume/efficiency'
            query = {
                'fields': 'path,volume,state,op_status,schedule,compression,inline_compression,inline_dedupe,policy,data_compaction,'
                          'cross_volume_inline_dedupe,cross_volume_background_dedupe',
                'path': self.parameters['path'],
                'vserver': self.parameters['vserver']
            }
            message, error = self.rest_api.get(api, query)

            if error:
                self.module.fail_json(msg=error)
            if len(message.keys()) == 0:
                return None
            if 'records' in message and len(message['records']) == 0:
                return None
            if 'records' not in message:
                error = "Unexpected response in api call from %s: %s" % (api, repr(message))
                self.module.fail_json(msg=error)
            return_value = {
                'path': message['records'][0]['path'],
                'enabled': message['records'][0]['state'],
                'status': message['records'][0]['op_status'],
                'schedule': message['records'][0]['schedule'],
                'enable_inline_compression': message['records'][0]['inline_compression'],
                'enable_compression': message['records'][0]['compression'],
                'enable_inline_dedupe': message['records'][0]['inline_dedupe'],
                'enable_data_compaction': message['records'][0]['data_compaction'],
                'enable_cross_volume_inline_dedupe': message['records'][0]['cross_volume_inline_dedupe'],
                'enable_cross_volume_background_dedupe': message['records'][0]['cross_volume_background_dedupe']
            }

            if 'policy' in message['records'][0]:
                return_value['policy'] = message['records'][0]['policy']
            else:
                return_value['policy'] = '-'
            return return_value

        else:

            sis_get_iter = netapp_utils.zapi.NaElement('sis-get-iter')
            sis_status_info = netapp_utils.zapi.NaElement('sis-status-info')
            sis_status_info.add_new_child('path', self.parameters['path'])
            query = netapp_utils.zapi.NaElement('query')
            query.add_child_elem(sis_status_info)
            sis_get_iter.add_child_elem(query)
            result = self.server.invoke_successfully(sis_get_iter, True)

            try:

                if result.get_child_by_name('attributes-list'):
                    sis_status_attributes = result['attributes-list']['sis-status-info']
                    return_value = {
                        'path': sis_status_attributes['path'],
                        'enabled': sis_status_attributes['state'],
                        'status': sis_status_attributes['status'],
                        'schedule': sis_status_attributes['schedule'],
                        'enable_inline_compression': self.na_helper.get_value_for_bool(
                            True, sis_status_attributes.get_child_content('is-inline-compression-enabled')
                        ),
                        'enable_compression': self.na_helper.get_value_for_bool(True, sis_status_attributes.get_child_content('is-compression-enabled')),
                        'enable_inline_dedupe': self.na_helper.get_value_for_bool(True, sis_status_attributes.get_child_content('is-inline-dedupe-enabled')),
                        'enable_data_compaction': self.na_helper.get_value_for_bool(
                            True, sis_status_attributes.get_child_content('is-data-compaction-enabled')
                        ),
                        'enable_cross_volume_inline_dedupe': self.na_helper.get_value_for_bool(
                            True, sis_status_attributes.get_child_content('is-cross-volume-inline-dedupe-enabled')
                        ),
                        'enable_cross_volume_background_dedupe': self.na_helper.get_value_for_bool(
                            True, sis_status_attributes.get_child_content('is-cross-volume-background-dedupe-enabled')
                        )
                    }

                    if sis_status_attributes.get_child_by_name('policy'):
                        return_value['policy'] = sis_status_attributes['policy']
                    else:
                        return_value['policy'] = '-'

            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error getting volume efficiency for path %s on vserver %s: %s' % (
                    self.parameters['path'], self.parameters['vserver'], to_native(error)), exception=traceback.format_exc()
                )

            return return_value

    def enable_volume_efficiency(self):
        """
        Enables Volume efficiency for a given volume by path
        """

        if self.use_rest:
            api = 'private/cli/volume/efficiency/on'
            body = dict()
            query = {
                'path': self.parameters['path'],
                'vserver': self.parameters['vserver']
            }
            message, error = self.rest_api.patch(api, body, query)

            if error:
                self.module.fail_json(msg=error)
            elif message['num_records'] == 0:
                error = 'Error enabling storage efficiency for path %s on vserver %s as the path provided does not exist.' % (self.parameters['path'],
                                                                                                                              self.parameters['vserver'])
                self.module.fail_json(msg=error)

        else:
            sis_enable = netapp_utils.zapi.NaElement("sis-enable")
            sis_enable.add_new_child("path", self.parameters['path'])

            try:
                self.server.invoke_successfully(sis_enable, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error enabling storage efficiency for path %s on vserver %s: %s' % (self.parameters['path'],
                                      self.parameters['vserver'], to_native(error)), exception=traceback.format_exc())

    def disable_volume_efficiency(self):
        """
        Disables Volume efficiency for a given volume by path
        """
        if self.use_rest:
            api = 'private/cli/volume/efficiency/off'
            body = dict()
            query = {
                'path': self.parameters['path'],
                'vserver': self.parameters['vserver']
            }
            dummy, error = self.rest_api.patch(api, body, query)
            if error:
                self.module.fail_json(msg=error)

        else:

            sis_disable = netapp_utils.zapi.NaElement("sis-disable")
            sis_disable.add_new_child("path", self.parameters['path'])

            try:
                self.server.invoke_successfully(sis_disable, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error disabling storage efficiency for path %s: %s' % (self.parameters['path'], to_native(error)),
                                      exception=traceback.format_exc())

    def modify_volume_efficiency(self):
        """
        Modifies volume efficiency settings for a given volume by path
        """

        if self.use_rest:
            api = 'private/cli/volume/efficiency'
            body = dict()
            query = {
                'path': self.parameters['path'],
                'vserver': self.parameters['vserver']
            }

            if 'schedule' in self.parameters:
                body['schedule'] = self.parameters['schedule']
            if 'policy' in self.parameters:
                body['policy'] = self.parameters['policy']
            if 'enable_compression' in self.parameters:
                body['compression'] = self.parameters['enable_compression']
            if 'enable_inline_compression' in self.parameters:
                body['inline_compression'] = self.parameters['enable_inline_compression']
            if 'enable_inline_dedupe' in self.parameters:
                body['inline_dedupe'] = self.parameters['enable_inline_dedupe']
            if 'enable_data_compaction' in self.parameters:
                body['data_compaction'] = self.parameters['enable_data_compaction']
            if 'enable_cross_volume_inline_dedupe' in self.parameters:
                body['cross_volume_inline_dedupe'] = self.parameters['enable_cross_volume_inline_dedupe']
            if 'enable_cross_volume_background_dedupe' in self.parameters:
                body['cross_volume_background_dedupe'] = self.parameters['enable_cross_volume_background_dedupe']

            dummy, error = self.rest_api.patch(api, body, query)
            if error:
                self.module.fail_json(msg=error)

        else:

            sis_config_obj = netapp_utils.zapi.NaElement("sis-set-config")
            sis_config_obj.add_new_child('path', self.parameters['path'])
            if 'schedule' in self.parameters:
                sis_config_obj.add_new_child('schedule', self.parameters['schedule'])
            if 'policy' in self.parameters:
                sis_config_obj.add_new_child('policy-name', self.parameters['policy'])
            if 'enable_compression' in self.parameters:
                sis_config_obj.add_new_child('enable-compression', self.na_helper.get_value_for_bool(False, self.parameters['enable_compression']))
            if 'enable_inline_compression' in self.parameters:
                sis_config_obj.add_new_child('enable-inline-compression', self.na_helper.get_value_for_bool(
                    False, self.parameters['enable_inline_compression'])
                )
            if 'enable_inline_dedupe' in self.parameters:
                sis_config_obj.add_new_child('enable-inline-dedupe', self.na_helper.get_value_for_bool(
                    False, self.parameters['enable_inline_dedupe'])
                )
            if 'enable_data_compaction' in self.parameters:
                sis_config_obj.add_new_child('enable-data-compaction', self.na_helper.get_value_for_bool(
                    False, self.parameters['enable_data_compaction'])
                )
            if 'enable_cross_volume_inline_dedupe' in self.parameters:
                sis_config_obj.add_new_child('enable-cross-volume-inline-dedupe', self.na_helper.get_value_for_bool(
                    False, self.parameters['enable_cross_volume_inline_dedupe'])
                )
            if 'enable_cross_volume_background_dedupe' in self.parameters:
                sis_config_obj.add_new_child('enable-cross-volume-background-dedupe', self.na_helper.get_value_for_bool(
                    False, self.parameters['enable_cross_volume_background_dedupe'])
                )

            try:
                self.server.invoke_successfully(sis_config_obj, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error modifying storage efficiency for path %s: %s' % (self.parameters['path'], to_native(error)),
                                      exception=traceback.format_exc())

    def start_volume_efficiency(self):
        """
        Starts volume efficiency for a given flex volume by path
        """

        if self.use_rest:
            api = 'private/cli/volume/efficiency/start'
            body = dict()
            query = {
                'path': self.parameters['path'],
                'vserver': self.parameters['vserver']
            }

            if 'start_ve_scan_all' in self.parameters:
                body['scan_all'] = self.parameters['start_ve_scan_all']
            if 'start_ve_build_metadata' in self.parameters:
                body['build_metadata'] = self.parameters['start_ve_build_metadata']
            if 'start_ve_delete_checkpoint' in self.parameters:
                body['delete_checkpoint'] = self.parameters['start_ve_delete_checkpoint']
            if 'start_ve_queue_operation' in self.parameters:
                body['queue'] = self.parameters['start_ve_queue_operation']
            if 'start_ve_scan_old_data' in self.parameters:
                body['scan_old_data'] = self.parameters['start_ve_scan_old_data']
            if 'start_ve_qos_policy' in self.parameters:
                body['qos-policy'] = self.parameters['start_ve_qos_policy']

            dummy, error = self.rest_api.patch(api, body, query)
            if error:
                self.module.fail_json(msg=error)

        else:

            sis_start = netapp_utils.zapi.NaElement('sis-start')
            sis_start.add_new_child('path', self.parameters['path'])

            if 'start_ve_scan_all' in self.parameters:
                sis_start.add_new_child('scan-all', self.na_helper.get_value_for_bool(
                    False, self.parameters['start_ve_scan_all'])
                )
            if 'start_ve_build_metadata' in self.parameters:
                sis_start.add_new_child('build-metadata', self.na_helper.get_value_for_bool(
                    False, self.parameters['start_ve_build_metadata'])
                )
            if 'start_ve_delete_checkpoint' in self.parameters:
                sis_start.add_new_child('delete-checkpoint', self.na_helper.get_value_for_bool(
                    False, self.parameters['start_ve_delete_checkpoint'])
                )
            if 'start_ve_queue_operation' in self.parameters:
                sis_start.add_new_child('queue-operation', self.na_helper.get_value_for_bool(
                    False, self.parameters['start_ve_queue_operation'])
                )
            if 'start_ve_scan_old_data' in self.parameters:
                sis_start.add_new_child('scan', self.na_helper.get_value_for_bool(
                    False, self.parameters['start_ve_scan_old_data'])
                )
            if 'start_ve_qos_policy' in self.parameters:
                sis_start.add_new_child('qos-policy', self.parameters['start_ve_qos_policy'])

            try:
                self.server.invoke_successfully(sis_start, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error starting storage efficiency for path %s on vserver %s: %s' % (self.parameters['path'],
                                      self.parameters['vserver'], to_native(error)), exception=traceback.format_exc())

    def stop_volume_efficiency(self):
        """
        Stops volume efficiency for a given flex volume by path
        """

        if self.use_rest:
            api = 'private/cli/volume/efficiency/stop'
            body = dict()
            query = {
                'path': self.parameters['path'],
                'vserver': self.parameters['vserver']
            }

            if 'stop_ve_all_operations' in self.parameters:
                body['all'] = self.parameters['stop_ve_all_operations']  # look and check parameter

            dummy, error = self.rest_api.patch(api, body, query)
            if error:
                self.module.fail_json(msg=error)

        else:

            sis_stop = netapp_utils.zapi.NaElement('sis-stop')
            sis_stop.add_new_child('path', self.parameters['path'])
            if 'stop_ve_all_operations' in self.parameters:
                sis_stop.add_new_child('all-operations', self.na_helper.get_value_for_bool(
                    False, self.parameters['stop_ve_all_operations'])
                )

            try:
                self.server.invoke_successfully(sis_stop, True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error stopping storage efficiency for path %s on vserver %s: %s' % (self.parameters['path'],
                                      self.parameters['vserver'], to_native(error)), exception=traceback.format_exc())

    def apply(self):
        if not self.use_rest:
            netapp_utils.ems_log_event("na_ontap_volume_efficiency", self.server)

        current = self.get_volume_efficiency()
        ve_status = None

        # If the volume efficiency does not exist for a given path to create this current is set to disabled
        # this is for ONTAP systems that do not enable efficiency by default.
        if current is None:
            current = {'enabled': 'disabled'}

        modify = self.na_helper.get_modified_attributes(current, self.parameters)

        if self.na_helper.changed:
            if not self.module.check_mode:
                if self.parameters['state'] == 'present' and current['enabled'] == 'disabled':
                    self.enable_volume_efficiency()
                    # Checking to see if there are any additional parameters that need to be set after enabling volume efficiency required for Non-AFF systems
                    current = self.get_volume_efficiency()
                    modify = self.na_helper.get_modified_attributes(current, self.parameters)
                elif self.parameters['state'] == 'absent' and current['enabled'] == 'enabled':
                    self.disable_volume_efficiency()

                if 'enabled' in modify:
                    del modify['enabled']
                if 'status' in modify:
                    ve_status = modify['status']
                    del modify['status']
                # Removed the enabled and volume efficiency status,
                # if there is anything remaining in the modify dict we need to modify.
                if modify:
                    self.modify_volume_efficiency()
                if ve_status == 'running':
                    self.start_volume_efficiency()
                elif ve_status == 'idle':
                    self.stop_volume_efficiency()

        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """
    Enables, modifies or disables NetApp Ontap volume efficiency
    """
    obj = NetAppOntapVolumeEfficiency()
    obj.apply()


if __name__ == '__main__':
    main()
