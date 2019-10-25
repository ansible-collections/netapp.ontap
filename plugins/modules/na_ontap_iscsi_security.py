#!/usr/bin/python

# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - Create/Delete/Modify iscsi security.
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
module: na_ontap_iscsi_security
options:
  state:
    choices: ['present', 'absent']
    description:
      - Whether the specified initiator should exist or not.
    default: present
    type: str
  vserver:
    description:
      - Name of the vserver to use.
    required: true
    type: str
  auth_type:
    description:
      - Specifies the authentication type.
    choices: ['chap', 'none', 'deny']
    type: str
  initiator:
    description:
      - Specifies the name of the initiator.
    required: true
    type: str
  address_ranges:
    description:
      - May be a single IPv4 or IPv6 address or a range containing a startaddress and an end address.
      - The start and end addresses themselves are included in the range.
      - If not present, the initiator is allowed to log in from any IP address.
    type: list
  inbound_username:
    description:
      - Inbound CHAP username.
    type: str
  inbound_password:
    description:
      - Inbound CHAP user password.
      - Can not be modified. If want to change password, delete and re-create the initiator.
    type: str
  outbound_username:
    description:
      - Outbound CHAP user name.
    type: str
  outbound_password:
    description:
      - Outbound CHAP user password.
      - Can not be modified. If want to change password, delete and re-create the initiator.
    type: str
short_description: "NetApp ONTAP Manage iscsi security."
version_added: "19.10.1"
'''

EXAMPLES = """
    - name: create
      na_ontap_iscsi_security:
        hostname: 0.0.0.0
        username: user
        password: pass
        vserver: test_svm
        state: present
        initiator: eui.9999956789abcdef
        inbound_username: user_1
        inbound_password: password_1
        outbound_username: user_2
        outbound_password: password_2
        auth_type: chap
        address_ranges: 10.125.10.0-10.125.10.10,10.125.193.78

    - name: modify outbound username
      na_ontap_iscsi_security:
        hostname: 0.0.0.0
        username: user
        password: pass
        vserver: test_svm
        state: present
        initiator: eui.9999956789abcdef
        inbound_username: user_1
        inbound_password: password_1
        outbound_username: user_out_3
        outbound_password: password_3
        auth_type: chap
        address_ranges: 10.125.10.0-10.125.10.10,10.125.193.78

    - name: modify address
      na_ontap_iscsi_security:
        hostname: 0.0.0.0
        username: user
        password: pass
        vserver: test_svm
        state: present
        initiator: eui.9999956789abcdef
        address_ranges: 10.125.193.90,10.125.10.20-10.125.10.30
"""

RETURN = """
"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI


class NetAppONTAPIscsiSecurity(object):
    """
    Class with iscsi security methods
    """
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            vserver=dict(required=True, type='str'),
            auth_type=dict(required=False, type='str', choices=['chap', 'none', 'deny']),
            inbound_password=dict(required=False, type='str'),
            inbound_username=dict(required=False, type='str'),
            initiator=dict(required=True, type='str'),
            address_ranges=dict(required=False, type='list'),
            outbound_password=dict(required=False, type='str'),
            outbound_username=dict(required=False, type='str'),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True,
            required_if=[
                ['auth_type', 'chap', ['inbound_username', 'inbound_password']]
            ],
            required_together=[
                ['inbound_username', 'outbound_password'],
                ['outbound_username', 'outbound_password']
            ]
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        self.restApi = OntapRestAPI(self.module)
        self.uuid = self.get_svm_uuid()

    def get_initiator(self):
        """
        Get current initiator.
        :return: dict of current initiator details.
        """
        params = {'fields': '*', 'initiator': self.parameters['initiator']}
        api = '/protocols/san/iscsi/credentials/'
        message, error = self.restApi.get(api, params)
        if error is not None:
            self.module.fail_json(msg="Error on fetching initiator: %s" % error)
        if message['num_records'] > 0:
            record = message['records'][0]
            initiator_details = dict()
            initiator_details['auth_type'] = record['authentication_type']
            if initiator_details['auth_type'] == 'chap':
                if record['chap'].get('inbound'):
                    initiator_details['inbound_username'] = record['chap']['inbound']['user']
                else:
                    initiator_details['inbound_username'] = None
                if record['chap'].get('outbound'):
                    initiator_details['outbound_username'] = record['chap']['outbound']['user']
                else:
                    initiator_details['outbound_username'] = None
            if record.get('initiator_address'):
                if record['initiator_address'].get('ranges'):
                    ranges = []
                    for address_range in record['initiator_address']['ranges']:
                        if address_range['start'] == address_range['end']:
                            ranges.append(address_range['start'])
                        else:
                            ranges.append(address_range['start'] + '-' + address_range['end'])
                    initiator_details['address_ranges'] = ranges
                else:
                    initiator_details['address_ranges'] = None
            return initiator_details

    def create_initiator(self):
        """
        Create initiator.
        :return: None.
        """
        params = dict()
        params['authentication_type'] = self.parameters['auth_type']
        params['initiator'] = self.parameters['initiator']
        if self.parameters['auth_type'] == 'chap':
            chap_info = dict()
            chap_info['inbound'] = {'user': self.parameters['inbound_username'], 'password': self.parameters['inbound_password']}
            if self.parameters.get('outbound_username'):
                chap_info['outbound'] = {'user': self.parameters['outbound_username'], 'password': self.parameters['outbound_password']}
            params['chap'] = chap_info
        address_info = self.get_address_info(self.parameters.get('address_ranges'))
        if address_info is not None:
            params['initiator_address'] = {'ranges': address_info}
        params['svm'] = {'uuid': self.uuid, 'name': self.parameters['vserver']}
        api = '/protocols/san/iscsi/credentials'
        message, error = self.restApi.post(api, params)
        if error is not None:
            self.module.fail_json(msg="Error on creating initiator: %s" % error)

    def delete_initiator(self):
        """
        Delete initiator.
        :return: None.
        """
        api = '/protocols/san/iscsi/credentials/{0}/{1}'.format(self.uuid, self.parameters['initiator'])
        message, error = self.restApi.delete(api, {})
        if error is not None:
            self.module.fail_json(msg="Error on deleting initiator: %s" % error)

    def modify_initiator(self, modify):
        """
        Modify initiator.
        :param modify: dict of modify attributes.
        :return: None.
        """
        params = dict()
        if modify.get('auth_type'):
            params['authentication_type'] = self.parameters['auth_type']
            if modify['auth_type'] == 'chap':
                chap_info = dict()
                if modify.get('inbound_username'):
                    chap_info['inbound'] = {'user': self.parameters['inbound_username'], 'password': self.parameters['inbound_password']}
                if modify.get('outbound_username'):
                    chap_info['outbound'] = {'user': self.parameters['outbound_username'], 'password': self.parameters['outbound_password']}
                params['chap'] = chap_info
        address_info = self.get_address_info(modify.get('address_ranges'))
        if address_info is not None:
            params['initiator_address'] = {'ranges': address_info}
        api = '/protocols/san/iscsi/credentials/{0}/{1}'.format(self.uuid, self.parameters['initiator'])
        message, error = self.restApi.patch(api, params)
        if error is not None:
            self.module.fail_json(msg="Error on modifying initiator: %s" % error)

    def get_address_info(self, address_ranges):
        if address_ranges is None:
            return None
        else:
            address_info = []
            for address in address_ranges:
                address_range = {}
                if '-' in address:
                    address_range['end'] = address.split('-')[1]
                    address_range['start'] = address.split('-')[0]
                else:
                    address_range['end'] = address
                    address_range['start'] = address
                address_info.append(address_range)
            return address_info

    def apply(self):
        """
        check create/delete/modify operations if needed.
        :return: None.
        """
        current = self.get_initiator()
        action = self.na_helper.get_cd_action(current, self.parameters)
        modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if action == 'create':
                    self.create_initiator()
                elif action == 'delete':
                    self.delete_initiator()
                elif modify:
                    self.modify_initiator(modify)
        self.module.exit_json(changed=self.na_helper.changed)

    def get_svm_uuid(self):
        """
        Get a svm's UUID
        :return: uuid of the svm.
        """
        params = {'fields': 'uuid', 'name': self.parameters['vserver']}
        api = "svm/svms"
        message, error = self.restApi.get(api, params)
        if error is not None:
            self.module.fail_json(msg="Error on fetching svm uuid: %s" % error)
        return message['records'][0]['uuid']


def main():
    """Execute action"""
    iscsi_obj = NetAppONTAPIscsiSecurity()
    iscsi_obj.apply()


if __name__ == '__main__':
    main()
