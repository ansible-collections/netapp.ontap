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
from ansible.module_utils.basic import AnsibleModule
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI
from ansible.module_utils._text import to_native


class NetAppONTAPDebug(object):
    """Class with Debug methods"""

    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.module = AnsibleModule(
            argument_spec=self.argument_spec
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

    def import_lib(self):
        try:
            from netapp_lib.api.zapi import zapi
        except ImportError:
            import sys
            syspath = ','.join(sys.path)
            self.module.fail_json(msg='Install the python NetApp-Lib module. Some useful diagnostic information here:',
                                  pythonbinarypath='Python Executable Path: %s.' % sys.executable,
                                  pythonversion='Python Version: %s.' % sys.version,
                                  syspath='System Path: %s.' % syspath)

    def check_zapi_connection(self):
        """
        check zapi connection errors and diagnose
        """
        self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)
        version_obj = netapp_utils.zapi.NaElement("system-get-version")

        output = None
        try:
            output = self.server.invoke_successfully(version_obj, True)
        except netapp_utils.zapi.NaApiError as error:
            error_string = to_native(error)
            if 'Connection timed out' in error_string or 'Resource temporarily unavailable' in error_string:
                self.module.fail_json(msg='Error in hostname - Address does not exist or is not reachable: %s' % error_string,
                                      summary='Invalid or unreachable hostname: %s' % self.parameters['hostname'])
            if 'Name or service not known' in error_string or 'Name does not resolve' in error_string:
                self.module.fail_json(msg='Error in hostname - DNS name cannot be resolved: %s' % error_string,
                                      summary='Error in hostname, %s cannot be resolved.' % self.parameters['hostname'])
            self.module.fail_json(msg='Other error: %s' % error_string,
                                      summary='Unclassified, see msg')

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
            self.using_vserver_msg = netapp_utils.ERROR_MSG['no_cserver']
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

        # check zapi connection errors
        self.check_zapi_connection()

        # log asup event with current event_name
        self.asup_log_for_cserver("na_ontap_debug")
        self.module.exit_json()


def main():
    """Execute action"""
    debug_obj = NetAppONTAPDebug()
    debug_obj.apply()


if __name__ == '__main__':
    main()
