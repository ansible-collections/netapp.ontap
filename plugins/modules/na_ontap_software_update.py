#!/usr/bin/python

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_software_update
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - Update ONTAP software
  - Requires an https connection and is not supported over http
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
module: na_ontap_software_update
options:
  state:
    choices: ['present', 'absent']
    description:
      - Whether the specified ONTAP package should update or not.
    default: present
    type: str
  nodes:
    description:
      - List of nodes to be updated, the nodes have to be a part of a HA Pair.
    aliases:
      - node
    type: list
    elements: str
  package_version:
    required: true
    description:
      - Specifies the package version to update software.
    type: str
  package_url:
    required: true
    type: str
    description:
      - Specifies the package URL to download the package.
  ignore_validation_warning:
    description:
      - Allows the update to continue if warnings are encountered during the validation phase.
    default: False
    type: bool
  download_only:
    description:
      - Allows to download image without update.
    default: False
    type: bool
    version_added: 20.4.0
  stabilize_minutes:
    description:
      - Number of minutes that the update should wait after a takeover or giveback is completed.
    type: int
    version_added: 20.6.0
  timeout:
    description:
      - how long to wait for the update to complete, in seconds.
    default: 1800
    type: int
  force_update:
    description:
      - force an update, even if package_version matches what is reported as installed.
    default: false
    type: bool
    version_added: 20.11.0
short_description: NetApp ONTAP Update Software
version_added: 2.7.0
'''

EXAMPLES = """

    - name: ONTAP software update
      na_ontap_software_update:
        state: present
        nodes: vsim1
        package_url: "{{ url }}"
        package_version: "{{ version_name }}"
        ignore_validation_warning: True
        download_only: True
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
"""

RETURN = """
"""

import time
import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppONTAPSoftwareUpdate(object):
    """
    Class with ONTAP software update methods
    """

    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            nodes=dict(required=False, type='list', elements='str', aliases=["node"]),
            package_version=dict(required=True, type='str'),
            package_url=dict(required=True, type='str'),
            ignore_validation_warning=dict(required=False, type='bool', default=False),
            download_only=dict(required=False, type='bool', default=False),
            stabilize_minutes=dict(required=False, type='int'),
            timeout=dict(required=False, type='int', default=1800),
            force_update=dict(required=False, type='bool', default=False),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    @staticmethod
    def cluster_image_get_iter():
        """
        Compose NaElement object to query current version
        :return: NaElement object for cluster-image-get-iter with query
        """
        cluster_image_get = netapp_utils.zapi.NaElement('cluster-image-get-iter')
        query = netapp_utils.zapi.NaElement('query')
        cluster_image_info = netapp_utils.zapi.NaElement('cluster-image-info')
        query.add_child_elem(cluster_image_info)
        cluster_image_get.add_child_elem(query)
        return cluster_image_get

    def cluster_image_get(self):
        """
        Get current cluster image info
        :return: True if query successful, else return None
        """
        cluster_image_get_iter = self.cluster_image_get_iter()
        try:
            result = self.server.invoke_successfully(cluster_image_get_iter, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching cluster image details: %s: %s'
                                  % (self.parameters['package_version'], to_native(error)),
                                  exception=traceback.format_exc())
        # return cluster image details
        node_versions = list()
        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) > 0:
            for image_info in result.get_child_by_name('attributes-list').get_children():
                node_versions.append((image_info.get_child_content('node-id'), image_info.get_child_content('current-version')))
        return node_versions

    def cluster_image_get_for_node(self, node_name):
        """
        Get current cluster image info for given node
        """
        cluster_image_get = netapp_utils.zapi.NaElement('cluster-image-get')
        cluster_image_get.add_new_child('node-id', node_name)
        try:
            result = self.server.invoke_successfully(cluster_image_get, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching cluster image details for %s: %s'
                                  % (node_name, to_native(error)),
                                  exception=traceback.format_exc())
        # return cluster image version
        if result.get_child_by_name('attributes').get_child_by_name('cluster-image-info'):
            image_info = result.get_child_by_name('attributes').get_child_by_name('cluster-image-info')
            if image_info:
                return image_info.get_child_content('node-id'), image_info.get_child_content('current-version')
        return None, None

    @staticmethod
    def get_localname(tag):
        return netapp_utils.zapi.etree.QName(tag).localname

    def cluster_image_update_progress_get(self, ignore_connection_error=True):
        """
        Get current cluster image update progress info
        :return: Dictionary of cluster image update progress if query successful, else return None
        """
        cluster_update_progress_get = netapp_utils.zapi.NaElement('cluster-image-update-progress-info')
        cluster_update_progress_info = dict()
        try:
            result = self.server.invoke_successfully(cluster_update_progress_get, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            # return empty dict on error to satisfy package delete upon image update
            if ignore_connection_error:
                return cluster_update_progress_info
            self.module.fail_json(msg='Error fetching cluster image update progress details: %s' % (to_native(error)),
                                  exception=traceback.format_exc())
        # return cluster image update progress details
        if result.get_child_by_name('attributes').get_child_by_name('ndu-progress-info'):
            update_progress_info = result.get_child_by_name('attributes').get_child_by_name('ndu-progress-info')
            cluster_update_progress_info['overall_status'] = update_progress_info.get_child_content('overall-status')
            cluster_update_progress_info['completed_node_count'] = update_progress_info.\
                get_child_content('completed-node-count')
            reports = update_progress_info.get_child_by_name('validation-reports')
            if reports:
                cluster_update_progress_info['validation_reports'] = list()
                for report in reports.get_children():
                    checks = dict()
                    for check in report.get_children():
                        checks[self.get_localname(check.get_name())] = check.get_content()
                    cluster_update_progress_info['validation_reports'].append(checks)
        return cluster_update_progress_info

    def cluster_image_update(self):
        """
        Update current cluster image
        """
        cluster_update_info = netapp_utils.zapi.NaElement('cluster-image-update')
        cluster_update_info.add_new_child('package-version', self.parameters['package_version'])
        cluster_update_info.add_new_child('ignore-validation-warning',
                                          str(self.parameters['ignore_validation_warning']))
        if self.parameters.get('stabilize_minutes'):
            cluster_update_info.add_new_child('stabilize-minutes',
                                              self.na_helper.get_value_for_int(False, self.parameters['stabilize_minutes']))
        if self.parameters.get('nodes'):
            cluster_nodes = netapp_utils.zapi.NaElement('nodes')
            for node in self.parameters['nodes']:
                cluster_nodes.add_new_child('node-name', node)
            cluster_update_info.add_child_elem(cluster_nodes)
        try:
            self.server.invoke_successfully(cluster_update_info, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            msg = 'Error updating cluster image for %s: %s' % (self.parameters['package_version'], to_native(error))
            cluster_update_progress_info = self.cluster_image_update_progress_get(ignore_connection_error=True)
            validation_reports = str(cluster_update_progress_info.get('validation_reports'))
            if validation_reports == "None":
                validation_reports = str(self.cluster_image_validate())
            self.module.fail_json(msg=msg, validation_reports=validation_reports, exception=traceback.format_exc())

    def cluster_image_package_download(self):
        """
        Get current cluster image package download
        :return: True if package already exists, else return False
        """
        cluster_image_package_download_info = netapp_utils.zapi.NaElement('cluster-image-package-download')
        cluster_image_package_download_info.add_new_child('package-url', self.parameters['package_url'])
        try:
            self.server.invoke_successfully(cluster_image_package_download_info, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            # Error 18408 denotes Package image with the same name already exists
            if to_native(error.code) == "18408":
                # TODO: if another package is using the same image name, we're stuck
                return True
            else:
                self.module.fail_json(msg='Error downloading cluster image package for %s: %s'
                                      % (self.parameters['package_url'], to_native(error)),
                                      exception=traceback.format_exc())
        return False

    def cluster_image_package_delete(self):
        """
        Delete current cluster image package
        """
        cluster_image_package_delete_info = netapp_utils.zapi.NaElement('cluster-image-package-delete')
        cluster_image_package_delete_info.add_new_child('package-version', self.parameters['package_version'])
        try:
            self.server.invoke_successfully(cluster_image_package_delete_info, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting cluster image package for %s: %s'
                                  % (self.parameters['package_version'], to_native(error)),
                                  exception=traceback.format_exc())

    def cluster_image_package_download_progress(self):
        """
        Get current cluster image package download progress
        :return: Dictionary of cluster image download progress if query successful, else return None
        """
        cluster_image_package_download_progress_info = netapp_utils.zapi.\
            NaElement('cluster-image-get-download-progress')
        try:
            result = self.server.invoke_successfully(
                cluster_image_package_download_progress_info, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching cluster image package download progress for %s: %s'
                                  % (self.parameters['package_url'], to_native(error)),
                                  exception=traceback.format_exc())
        # return cluster image download progress details
        cluster_download_progress_info = dict()
        if result.get_child_by_name('progress-status'):
            cluster_download_progress_info['progress_status'] = result.get_child_content('progress-status')
            cluster_download_progress_info['progress_details'] = result.get_child_content('progress-details')
            cluster_download_progress_info['failure_reason'] = result.get_child_content('failure-reason')
            return cluster_download_progress_info
        return None

    def cluster_image_validate(self):
        """
        Validate that NDU is feasible.
        :return: List of dictionaries
        """
        cluster_image_validation_info = netapp_utils.zapi.NaElement('cluster-image-validate')
        cluster_image_validation_info.add_new_child('package-version', self.parameters['package_version'])
        try:
            result = self.server.invoke_successfully(
                cluster_image_validation_info, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            msg = 'Error running cluster image validate: %s' % to_native(error)
            return msg
        # return cluster validation report
        cluster_report_info = list()
        if result.get_child_by_name('cluster-image-validation-report-list'):
            for report in result.get_child_by_name('cluster-image-validation-report-list').get_children():
                cluster_report_info.append(dict(
                    ndu_check=report.get_child_content('ndu-check'),
                    ndu_status=report.get_child_content('ndu-status'),
                    required_action=report.get_child_content('required-action')
                ))
        return cluster_report_info

    def autosupport_log(self):
        """
        Autosupport log for software_update
        :return:
        """
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("na_ontap_software_update", cserver)

    def is_update_required(self):
        ''' return True if at least one node is not at the correct version '''
        if self.parameters.get('nodes'):
            versions = [self.cluster_image_get_for_node(node) for node in self.parameters['nodes']]
        else:
            versions = self.cluster_image_get()
        current_versions = set([x[1] for x in versions])
        if len(current_versions) != 1:
            # mixed set, need to update
            return True
        # only update if versions differ
        return current_versions.pop() != self.parameters['package_version']

    def apply(self):
        """
        Apply action to update ONTAP software
        """
        # TODO: cluster image update only works for HA configurations.
        # check if node image update can be used for other cases.
        if self.parameters.get('https') is not True:
            self.module.fail_json(msg='https parameter must be True')
        self.autosupport_log()
        changed = self.parameters['force_update'] or self.is_update_required()
        validation_reports = 'only available after update'
        if not self.module.check_mode and changed:
            if self.parameters.get('state') == 'present':
                package_exists = self.cluster_image_package_download()
                if package_exists is False:
                    cluster_download_progress = self.cluster_image_package_download_progress()
                    while cluster_download_progress.get('progress_status') == 'async_pkg_get_phase_running':
                        time.sleep(5)
                        cluster_download_progress = self.cluster_image_package_download_progress()
                    if not cluster_download_progress.get('progress_status') == 'async_pkg_get_phase_complete':
                        self.module.fail_json(msg='Error downloading package: %s'
                                              % (cluster_download_progress['failure_reason']))
                if self.parameters['download_only'] is False:
                    self.cluster_image_update()
                    # delete package once update is completed
                    cluster_update_progress = dict()
                    time_left = self.parameters['timeout']
                    polling_interval = 25
                    # assume in_progress if dict is empty
                    while time_left > 0 and cluster_update_progress.get('overall_status', 'in_progress') == 'in_progress':
                        time.sleep(polling_interval)
                        time_left -= polling_interval
                        cluster_update_progress = self.cluster_image_update_progress_get(ignore_connection_error=True)
                    if cluster_update_progress.get('overall_status') == 'completed':
                        validation_reports = str(cluster_update_progress.get('validation_reports'))
                        self.cluster_image_package_delete()
                    else:
                        cluster_update_progress = self.cluster_image_update_progress_get(ignore_connection_error=False)
                        if cluster_update_progress.get('overall_status') != 'completed':
                            if cluster_update_progress.get('overall_status') == 'in_progress':
                                msg = 'Timeout error'
                                action = '  Should the timeout value be increased?  Current value is %d seconds.' % self.parameters['timeout']
                                action += '  The software update continues in background.'
                            else:
                                msg = 'Error'
                                action = ''
                            msg += ' updating image: overall_status: %s.' % (cluster_update_progress.get('overall_status', 'cannot get status'))
                            msg += action
                            validation_reports = str(cluster_update_progress.get('validation_reports'))
                            self.module.fail_json(msg=msg, validation_reports=validation_reports)

        self.module.exit_json(changed=changed, validation_reports=validation_reports)


def main():
    """Execute action"""
    community_obj = NetAppONTAPSoftwareUpdate()
    community_obj.apply()


if __name__ == '__main__':
    main()
