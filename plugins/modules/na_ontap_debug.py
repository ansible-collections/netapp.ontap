#!/usr/bin/python
"""
create Debug module to diagnose netapp-lib import and connection
"""

# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
module: na_ontap_debug
short_description: NetApp ONTAP Debug netapp-lib import and connection.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 21.1.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
- Display issues related to importing netapp-lib and connection with diagnose
options:
  vserver:
    description:
    - The vserver name to test for ZAPI tunneling.
    required: false
    type: str
'''
EXAMPLES = """
    - name: Check import netapp-lib
      na_ontap_debug:
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
"""

RETURN = """
"""
import sys
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule


class NetAppONTAPDebug(object):
    """Class with Debug methods"""

    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            vserver=dict(required=False, type="str"),

        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        self.log_list = []
        self.error_list = []
        self.server = None

    def import_lib(self):
        if not netapp_utils.has_netapp_lib():
            syspath = ','.join(sys.path)
            msgs = list()
            msgs.append('Error importing netapp-lib or a dependency: %s.' % str(netapp_utils.IMPORT_EXCEPTION))
            msgs.append('Install the python netapp-lib module or a missing dependency.')
            msgs.append('Additional diagnostic information:')
            msgs.append('Python Executable Path: ' + sys.executable)
            msgs.append('Python Version: Python Version: %s.' + sys.version)
            msgs.append('System Path: ' + syspath)
            self.error_list.append('  '.join(msgs))
            return
        self.log_list.append('netapp-lib imported successfully.')

    def check_connection(self, connection_type):
        """
        check connection errors and diagnose
        """
        error_string = None
        if connection_type == "rest":
            api = 'cluster/'
            message, error_string = self.rest_api.get(api)
        elif connection_type == "zapi":
            if 'vserver' not in self.parameters:
                self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)
            else:
                self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])
            version_obj = netapp_utils.zapi.NaElement("system-get-version")
            try:
                result = self.server.invoke_successfully(version_obj, True)
            except netapp_utils.zapi.NaApiError as error:
                error_string = to_native(error)
        if error_string is not None:
            summary_msg = None
            error_patterns = ['Connection timed out',
                              'Resource temporarily unavailable',
                              'ConnectTimeoutError',
                              'Network is unreachable']
            if any([x in error_string for x in error_patterns]):
                summary_msg = 'Error: invalid or unreachable hostname: %s' % self.parameters['hostname']
                if 'vserver' in self.parameters:
                    summary_msg += ' for SVM: %s ' % self.parameters['vserver']
                self.error_list.append('Error in hostname - Address does not exist or is not reachable: ' + error_string)
                self.error_list.append(summary_msg + ' using %s.' % connection_type)
                return
            error_patterns = ['Name or service not known', 'Name does not resolve']
            if any([x in error_string for x in error_patterns]):
                summary_msg = 'Error: unknown or not resolvable hostname: %s' % self.parameters['hostname']
                if 'vserver' in self.parameters:
                    summary_msg += ' for SVM: %s ' % self.parameters['vserver']
                self.error_list.append('Error in hostname - DNS name cannot be resolved: ' + error_string)
                self.error_list.append(summary_msg + ' cannot be resolved using' + connection_type)
            else:
                self.error_list.append('Other error for hostname: %s using %s: %s.' % (self.parameters['hostname'], connection_type, error_string))
                self.error_list.append('Unclassified, see msg')
        else:
            if connection_type == 'zapi':
                ontap_version = result['version']
            elif connection_type == 'rest':
                ontap_version = message['version']['full']

            self.log_list.append(connection_type + ' connected successfully.')
            self.log_list.append('ONTAP version: %s' % ontap_version)

    def asup_log_for_cserver(self, event_name):
        """
        Fetch admin vserver for the given cluster
        Create and Autosupport log event with the given module name
        :param event_name: Name of the event log
        :return: None
        """
        cserver = netapp_utils.get_cserver(self.server)
        if cserver is None:
            server = self.server
            event_name += ':error_no_cserver'
        else:
            server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=cserver)
        netapp_utils.ems_log_event(event_name, server)

    def apply(self):
        """
        Apply debug
        """
        # check import netapp-lib
        self.import_lib()

        # check zapi connection errors only if import successful
        if netapp_utils.has_netapp_lib():
            self.check_connection("zapi")

        # check rest connection errors
        self.check_connection("rest")

        # log asup event with current event_name
        if netapp_utils.has_netapp_lib():
            try:
                self.asup_log_for_cserver("na_ontap_debug")
            except netapp_utils.zapi.NaApiError as error:
                self.log_list.append('Failed to log EMS message: %s' % str(error))

        if self.error_list != []:
            self.module.fail_json(msg=self.error_list, msg_passed=self.log_list)
        self.module.exit_json(msg=self.log_list)


def main():
    """Execute action"""
    debug_obj = NetAppONTAPDebug()
    debug_obj.apply()


if __name__ == '__main__':
    main()
