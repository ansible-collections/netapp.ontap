#!/usr/bin/python

# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_login_messages
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
module: na_ontap_login_messages
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '20.1.0'
short_description: Setup login banner and message of the day
description:
    - This module allows you to manipulate login banner and motd for a vserver
options:
    banner:
        description:
        - Login banner Text message.
        type: str
    vserver:
        description:
        - The name of the SVM login messages should be set for.
        required: true
        type: str
    motd_message:
        description:
        - MOTD Text message.
        type: str
        aliases:
          - message
    show_cluster_motd:
        description:
        - Set to I(false) if Cluster-level Message of the Day should not be shown
        type: bool
        default: True
'''

EXAMPLES = """

    - name: modify banner vserver
      na_ontap_login_messages:
        vserver: trident_svm
        banner: this is trident vserver
        usename: "{{ username }}"
        password: "{{ password }}"
        hostname: "{{ hostname }}"

    - name: modify motd vserver
      na_ontap_login_messages:
        vserver: trident_svm
        motd_message: this is trident vserver
        show_cluster_motd: True
        usename: "{{ username }}"
        password: "{{ password }}"
        hostname: "{{ hostname }}"

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


class NetAppOntapLoginMessages(object):
    """
    modify and delete login banner and motd
    """

    def __init__(self):
        self.use_rest = False
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            vserver=dict(required=True, type='str'),
            banner=dict(required=False, type='str'),
            motd_message=dict(required=False, type='str', aliases=['message']),
            show_cluster_motd=dict(default=True, type='bool')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True,
            required_one_of=[['show_cluster_motd', 'banner', 'motd_message']]
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        self.rest_api = OntapRestAPI(self.module)
        if self.rest_api.is_rest():
            self.use_rest = True
        else:
            if HAS_NETAPP_LIB is False:
                self.module.fail_json(msg="the python NetApp-Lib module is required")
            else:
                self.server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=self.parameters['vserver'])

    def get_banner_motd(self, uuid=None):
        if self.use_rest:
            api = 'security/login/messages/' + uuid
            params = {
                'fields': '*'
            }
            message, error = self.rest_api.get(api, params)
            if error:
                self.module.fail_json(msg='Error when fetching login_banner info: %s' % error)
            return_result = dict()
            return_result['banner'] = message['banner'].rstrip() if message.get('banner') else ''
            return_result['motd_message'] = message['message'].rstrip() if message.get('message') else ''
            if message.get('show_cluster_message'):
                return_result['show_cluster_message'] = message['show_cluster_message']
            return return_result
        else:
            login_banner_get_iter = netapp_utils.zapi.NaElement('vserver-login-banner-get-iter')
            query = netapp_utils.zapi.NaElement('query')
            login_banner_info = netapp_utils.zapi.NaElement('vserver-login-banner-info')
            login_banner_info.add_new_child('vserver', self.parameters['vserver'])
            query.add_child_elem(login_banner_info)
            login_banner_get_iter.add_child_elem(query)
            return_result = dict()
            try:
                result = self.server.invoke_successfully(login_banner_get_iter, enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error fetching login_banner info: %s' % to_native(error),
                                      exception=traceback.format_exc())
            if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) > 0:
                login_banner_info = result.get_child_by_name('attributes-list').get_child_by_name(
                    'vserver-login-banner-info')
                return_result['banner'] = login_banner_info.get_child_content('message')
                return_result['banner'] = str(return_result['banner']).rstrip()
                # if the message is '-' that means the banner doesn't exist.
                if return_result['banner'] == '-' or return_result['banner'] == 'None':
                    return_result['banner'] = ''

            motd_get_iter = netapp_utils.zapi.NaElement('vserver-motd-get-iter')
            query = netapp_utils.zapi.NaElement('query')
            motd_info = netapp_utils.zapi.NaElement('vserver-motd-info')
            motd_info.add_new_child('vserver', self.parameters['vserver'])
            query.add_child_elem(motd_info)
            motd_get_iter.add_child_elem(query)
            try:
                result = self.server.invoke_successfully(motd_get_iter, enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error fetching motd info: %s' % to_native(error),
                                      exception=traceback.format_exc())
            if result.get_child_by_name('num-records') and \
                    int(result.get_child_content('num-records')) > 0:
                motd_info = result.get_child_by_name('attributes-list').get_child_by_name(
                    'vserver-motd-info')
                return_result['motd_message'] = motd_info.get_child_content('message')
                return_result['motd_message'] = str(return_result['motd_message']).rstrip()
                return_result['show_cluster_motd'] = True if motd_info.get_child_content(
                    'is-cluster-message-enabled') == 'true' else False
                if return_result['motd_message'] == 'None':
                    return_result['motd_message'] = ''
            return return_result

    def modify_banner(self, modify, uuid):
        if self.use_rest:
            api = 'security/login/messages/' + uuid
            params = {
                "banner": modify['banner']
            }
            dummy, error = self.rest_api.patch(api, params)
            if error:
                self.module.fail_json(msg='Error when modifying banner: %s' % error)
        else:
            login_banner_modify = netapp_utils.zapi.NaElement('vserver-login-banner-modify-iter')
            login_banner_modify.add_new_child('message', modify['banner'])
            query = netapp_utils.zapi.NaElement('query')
            login_banner_info = netapp_utils.zapi.NaElement('vserver-login-banner-info')
            login_banner_info.add_new_child('vserver', self.parameters['vserver'])
            query.add_child_elem(login_banner_info)
            login_banner_modify.add_child_elem(query)
            try:
                self.server.invoke_successfully(login_banner_modify, enable_tunneling=False)
            except netapp_utils.zapi.NaApiError as err:
                self.module.fail_json(msg="Error modifying login_banner: %s" % (to_native(err)),
                                      exception=traceback.format_exc())

    def modify_motd(self, modify, uuid):
        if self.use_rest:
            api = 'security/login/messages/' + uuid
            params = {
                'message': modify['motd_message'],
            }
            if modify.get('show_cluster_motd'):
                params['show_cluster_message'] = modify['show_cluster_motd']
            dummy, error = self.rest_api.patch(api, params)
            if error:
                self.module.fail_json(msg='Error when modifying motd: %s' % error)
        else:
            motd_create = netapp_utils.zapi.NaElement('vserver-motd-modify-iter')
            if modify.get('motd_message') is not None:
                motd_create.add_new_child('message', modify['motd_message'])
            if modify.get('show_cluster_motd') is not None:
                motd_create.add_new_child('is-cluster-message-enabled', 'true' if modify['show_cluster_motd'] is True else 'false')
            query = netapp_utils.zapi.NaElement('query')
            motd_info = netapp_utils.zapi.NaElement('vserver-motd-info')
            motd_info.add_new_child('vserver', self.parameters['vserver'])
            query.add_child_elem(motd_info)
            motd_create.add_child_elem(query)
            try:
                self.server.invoke_successfully(motd_create, enable_tunneling=False)
            except netapp_utils.zapi.NaApiError as err:
                self.module.fail_json(msg="Error modifying motd: %s" % (to_native(err)),
                                      exception=traceback.format_exc())

    def get_svm_uuid(self):
        """
        Get a svm's uuid
        :return: uuid of the svm
        """
        params = {'name': self.parameters['vserver'],
                  'fields': 'uuid'
                  }
        api = 'svm/svms'
        message, error = self.rest_api.get(api, params)
        if error is not None:
            self.module.fail_json(msg="%s" % error)
        if message['num_records'] == 0:
            self.module.fail_json(msg="Error fetching specified vserver. Please make sure vserver name is correct. For cluster vserver, Please use ZAPI.")
        return message['records'][0]['uuid']

    def apply(self):
        uuid = None
        modify = None
        if self.use_rest:
            uuid = self.get_svm_uuid()
        else:
            netapp_utils.ems_log_event("na_ontap_login_banner", self.server)

        current = self.get_banner_motd(uuid=uuid)
        modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if modify.get('banner') is not None:
                    self.modify_banner(modify, uuid=uuid)
                if modify.get('show_cluster_motd') is not None or modify.get('motd_message') is not None:
                    self.modify_motd(modify, uuid=uuid)

        self.module.exit_json(changed=self.na_helper.changed)


def main():
    '''Execute action from playbook'''
    messages_obj = NetAppOntapLoginMessages()
    messages_obj.apply()


if __name__ == '__main__':
    main()
