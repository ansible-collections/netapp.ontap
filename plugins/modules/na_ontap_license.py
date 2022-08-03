#!/usr/bin/python

# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_license
'''
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''

module: na_ontap_license

short_description: NetApp ONTAP protocol and feature license packages
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
  - Add or remove license packages on NetApp ONTAP.
  - Note that the module is asymmetrical.
  - It requires license codes to add packages and the package name is not visible.
  - It requires package names and as serial number to remove packages.

options:
  state:
    description:
      - Whether the specified license packages should be installed or removed.
    choices: ['present', 'absent']
    type: str
    default: present

  remove_unused:
    description:
      - Remove license packages that have no controller affiliation in the cluster.
      - Not supported with REST.
    type: bool

  remove_expired:
    description:
      - Remove license packages that have expired in the cluster.
      - Not supported with REST.
    type: bool

  serial_number:
    description:
      - Serial number of the node or cluster associated with the license package.
      - This parameter is required when removing a license package.
      - With REST, '*' is accepted and matches any serial number.
    type: str

  license_names:
    type: list
    elements: str
    description:
      - List of license package names to remove.
    suboptions:
      base:
        description:
          - Cluster Base License
      nfs:
        description:
          - NFS License
      cifs:
        description:
          - CIFS License
      iscsi:
        description:
          - iSCSI License
      fcp:
        description:
          - FCP License
      cdmi:
        description:
          - CDMI License
      snaprestore:
        description:
          - SnapRestore License
      snapmirror:
        description:
          - SnapMirror License
      flexclone:
        description:
          - FlexClone License
      snapvault:
        description:
          - SnapVault License
      snaplock:
        description:
          - SnapLock License
      snapmanagersuite:
        description:
          - SnapManagerSuite License
      snapprotectapps:
        description:
          - SnapProtectApp License
      v_storageattach:
        description:
          - Virtual Attached Storage License

  license_codes:
    description:
      - List of license codes to be installed.
    type: list
    elements: str

'''


EXAMPLES = """
- name: Add licenses
  netapp.ontap.na_ontap_license:
    state: present
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    serial_number: #################
    license_codes: CODE1,CODE2

- name: Remove licenses
  netapp.ontap.na_ontap_license:
    state: absent
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    remove_unused: false
    remove_expired: true
    serial_number: #################
    license_names: nfs,cifs
"""

RETURN = """
updated_licenses:
    description: return list of updated package names
    returned: always
    type: dict
    sample: "['nfs']"
"""

import time
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic


def local_cmp(a, b):
    """
        compares with only values and not keys, keys should be the same for both dicts
        :param a: dict 1
        :param b: dict 2
        :return: difference of values in both dicts
        """
    return [key for key in a if a[key] != b[key]]


class NetAppOntapLicense:
    '''ONTAP license class'''

    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            serial_number=dict(required=False, type='str'),
            remove_unused=dict(default=None, type='bool'),
            remove_expired=dict(default=None, type='bool'),
            license_codes=dict(default=None, type='list', elements='str'),
            license_names=dict(default=None, type='list', elements='str'),
        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=False,
            required_if=[
                ('state', 'absent', ['serial_number', 'license_names'])]
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        # Set up REST API
        self.rest_api = OntapRestAPI(self.module)
        unsupported_rest_properties = ['remove_unused', 'remove_expired']
        self.use_rest = self.rest_api.is_rest_supported_properties(self.parameters, unsupported_rest_properties)
        if not self.use_rest:
            if not netapp_utils.has_netapp_lib():
                self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
            else:
                self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def get_licensing_status(self):
        """
            Check licensing status

            :return: package (key) and licensing status (value)
            :rtype: dict
        """
        if self.use_rest:
            return self.get_licensing_status_rest()
        license_status = netapp_utils.zapi.NaElement(
            'license-v2-status-list-info')
        result = None
        try:
            result = self.server.invoke_successfully(license_status,
                                                     enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error checking license status: %s" %
                                  to_native(error), exception=traceback.format_exc())

        return_dictionary = {}
        license_v2_status = result.get_child_by_name('license-v2-status')
        if license_v2_status:
            for license_v2_status_info in license_v2_status.get_children():
                package = license_v2_status_info.get_child_content('package')
                status = license_v2_status_info.get_child_content('method')
                return_dictionary[package] = status
        return return_dictionary

    def get_licensing_status_rest(self):
        api = 'cluster/licensing/licenses'
        # By default, the GET method only returns licensed packages.
        # To retrieve all the available package state details, below query is used.
        query = {'state': 'compliant, noncompliant, unlicensed, unknown'}
        fields = 'name,state'
        records, error = rest_generic.get_0_or_more_records(self.rest_api, api, query, fields)
        if error:
            self.module.fail_json(msg=error)
        current = {}
        if records:
            for package in records:
                current[package['name']] = package['state']
        return current

    def remove_licenses(self, package_name):
        """
        Remove requested licenses
        :param:
          package_name: Name of the license to be deleted
        """
        if self.use_rest:
            return self.remove_licenses_rest(package_name)
        license_delete = netapp_utils.zapi.NaElement('license-v2-delete')
        license_delete.add_new_child('serial-number', self.parameters['serial_number'])
        license_delete.add_new_child('package', package_name)
        try:
            self.server.invoke_successfully(license_delete,
                                            enable_tunneling=False)
            return True
        except netapp_utils.zapi.NaApiError as error:
            # Error 15661 - Object not found
            if to_native(error.code) == "15661":
                return False
            else:
                self.module.fail_json(msg="Error removing license %s" %
                                      to_native(error), exception=traceback.format_exc())

    def remove_licenses_rest(self, package_name):
        api = 'cluster/licensing/licenses'
        query = {'serial_number': self.parameters['serial_number']}
        dummy, error = rest_generic.delete_async(self.rest_api, api, package_name, query)
        if error:
            if "entry doesn't exist" in error:
                return False
            self.module.fail_json(msg=error)
        return True

    def remove_unused_licenses(self):
        """
        Remove unused licenses
        """
        remove_unused = netapp_utils.zapi.NaElement('license-v2-delete-unused')
        try:
            self.server.invoke_successfully(remove_unused,
                                            enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error removing unused licenses: %s" %
                                  to_native(error), exception=traceback.format_exc())

    def remove_expired_licenses(self):
        """
        Remove expired licenses
        """
        remove_expired = netapp_utils.zapi.NaElement(
            'license-v2-delete-expired')
        try:
            self.server.invoke_successfully(remove_expired,
                                            enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error removing expired licenses: %s" %
                                  to_native(error), exception=traceback.format_exc())

    def add_licenses(self):
        """
        Add licenses
        """
        if self.use_rest:
            return self.add_licenses_rest()
        license_add = netapp_utils.zapi.NaElement('license-v2-add')
        codes = netapp_utils.zapi.NaElement('codes')
        for code in self.parameters['license_codes']:
            codes.add_new_child('license-code-v2', str(code.strip().lower()))
        license_add.add_child_elem(codes)
        try:
            self.server.invoke_successfully(license_add,
                                            enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error adding licenses: %s" %
                                  to_native(error), exception=traceback.format_exc())

    def add_licenses_rest(self):
        api = 'cluster/licensing/licenses'
        body = {'keys': self.parameters['license_codes']}
        dummy, error = rest_generic.post_async(self.rest_api, api, body)
        if error:
            self.module.fail_json(msg=error)

    def compare_license_status(self, previous_license_status):
        changed_keys = []
        for __ in range(5):
            error = None
            new_license_status = self.get_licensing_status()
            try:
                changed_keys = local_cmp(previous_license_status, new_license_status)
                break
            except KeyError as exc:
                # when a new license is added, it seems REST may not report all licenses
                # wait for things to stabilize
                error = exc
                time.sleep(5)
        if error:
            self.module.fail_json(msg='Error: mismatch in license package names: %s.  Expected: %s, found: %s.'
                                  % (error, previous_license_status.keys(), new_license_status.keys()))
        return changed_keys

    def apply(self):
        '''Call add, delete or modify methods'''
        changed = False
        changed_keys = None
        create_license = False
        remove_license = False
        if not self.use_rest:
            netapp_utils.ems_log_event_cserver("na_ontap_license", self.server, self.module)
        # Add / Update licenses.
        license_status = self.get_licensing_status()
        if self.parameters['state'] == 'absent':  # delete
            changed = True
        else:  # add or update
            if self.parameters.get('license_codes') is not None:
                create_license = True
                changed = True
            if self.parameters.get('remove_unused') is not None:
                remove_license = True
                changed = True
            if self.parameters.get('remove_expired') is not None:
                remove_license = True
                changed = True
        if changed and not self.module.check_mode:
            if self.parameters['state'] == 'present':  # execute create
                if create_license:
                    self.add_licenses()
                if self.parameters.get('remove_unused') is not None:
                    self.remove_unused_licenses()
                if self.parameters.get('remove_expired') is not None:
                    self.remove_expired_licenses()
                # not able to detect that a new license is required until we try to install it.
                if create_license or remove_license:
                    changed_keys = self.compare_license_status(license_status)
            else:  # execute delete
                license_deleted = False
                # not able to detect which license is required to delete until we try it.
                changed_keys = [package for package in self.parameters['license_names'] if self.remove_licenses(package)]
            if not changed_keys:
                changed = False

        self.module.exit_json(changed=changed, updated_licenses=changed_keys)


def main():
    '''Apply license operations'''
    obj = NetAppOntapLicense()
    obj.apply()


if __name__ == '__main__':
    main()
