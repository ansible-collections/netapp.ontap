#!/usr/bin/python

# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
module: na_ontap_cifs_local_user_set_password
short_description: NetApp ONTAP set local CIFS user password
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '21.8.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
    - Sets the password for the specified local user.
    - NOTE - This module is not idempotent.
    - Password must meet the following criteria
    - The password must be at least six characters in length.
    - The password must not contain user account name.
    - The password must contain characters from three of the following four
    -   English uppercase characters (A through Z)
    -   English lowercase characters (a through z)
    -   Base 10 digits (0 through 9)
    -   Special characters

options:
  vserver:
    description:
    - name of the vserver.
    required: true
    type: str

  user_name:
    description:
    - The name of the local CIFS user to set the password for.
    required: true
    type: str

  user_password:
    description:
    - The password to set for the local CIFS user.
    required: true
    type: str
'''

EXAMPLES = '''
    - name: Set local CIFS pasword for BUILTIN Administrator account
      netapp.ontap.na_ontap_cifs_local_user_set_password:
        user_name: Administrator
        user_password: Test123!
        vserver: ansible
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
'''

RETURN = '''
'''

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule


class NetAppONTAPCifsSetPassword():
    '''
    Set  CIFS local user password.
    '''
    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            vserver=dict(required=True, type='str'),
            user_name=dict(required=True, type='str'),
            user_password=dict(required=True, type='str', no_log=True)
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if not netapp_utils.has_netapp_lib():
            self.module.fail_json(msg=netapp_utils.netapp_lib_is_required())
        self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def cifs_local_set_passwd(self):
        """
        :return: None
        """
        cifs_local_set_passwd = netapp_utils.zapi.NaElement('cifs-local-user-set-password')
        cifs_local_set_passwd.add_new_child('user-name', self.parameters['user_name'])
        cifs_local_set_passwd.add_new_child('user-password', self.parameters['user_password'])

        try:
            self.server.invoke_successfully(cifs_local_set_passwd, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as e:
            self.module.fail_json(msg='Error setting password for local CIFS user %s on vserver %s: %s'
                                  % (self.parameters['user_name'], self.parameters['vserver'], to_native(e)),
                                  exception=traceback.format_exc())

    def ems_log_event(self):
        results = netapp_utils.get_cserver(self.server)
        cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
        netapp_utils.ems_log_event("na_ontap_cifs_local_user_set_password", cserver)

    def apply(self):
        changed = True
        self.ems_log_event()
        if not self.module.check_mode:
            self.cifs_local_set_passwd()

        self.module.exit_json(changed=changed)


def main():
    obj = NetAppONTAPCifsSetPassword()
    obj.apply()


if __name__ == '__main__':
    main()
