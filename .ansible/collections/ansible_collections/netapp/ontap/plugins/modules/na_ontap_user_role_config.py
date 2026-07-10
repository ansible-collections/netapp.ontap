#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2026, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
module: na_ontap_user_role_config
short_description: NetApp ONTAP local user account restrictions
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap_rest
version_added: 23.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansible-team@netapp.com>
description:
  - Modify local user account and password restrictions.
options:
  state:
    description:
      - Configure local user account restrictions, only present is supported.
    choices: ['present']
    type: str
    default: present

  vserver:
    description:
      - Specifies the SVM name associated with the profile configuration.
    required: false
    type: str

  role:
    description:
      - Specifies the role whose account restrictions are to be modified.
    type: str
    required: true

  username_minlength:
    description:
      - Specifies the required minimum length of the user name.
      - Supported values are 3 to 32 characters. The default setting is 3 characters.
    type: int
    default: 3

  username_alphanum:
    description:
      - If this parameter is enabled, a user name must contain at least one letter and one number.
      - The default setting is disabled.
    type: bool
    default: false

  passwd_minlength:
    description:
      - Specifies the required minimum length of a password.
      - Supported values are 3 to 127 characters. The default setting is 8 characters.
    type: int
    default: 8

  passwd_alphanum:
    description:
      - If this parameter is enabled, a password must contain at least one letter and one number.
      - The default setting is enabled.
    type: bool
    default: true

  passwd_min_special_chars:
    description:
      - Specifies the minimum number of special characters required in a password.
      - Supported values are from 0 to 127 special characters. The default setting is 0.
    type: int
    default: 0

  passwd_expiry_time:
    description:
      - Specifies password expiration in days.
      - A value of 0 means all passwords associated with the accounts in the role expire now.
        The default setting is -1 (unlimited), which means the passwords never expire.
    type: int
    default: -1

  require_initial_passwd_update:
    description:
      - Specifies whether users must change their passwords when logging in for the first time.
      - The default setting is disabled.
    type: bool
    default: false

  max_failed_login_attempts:
    description:
      - Specifies the allowed maximum number of consecutive invalid login attempts.
      - When the failed login attempts reach the specified maximum, the account is automatically locked. The default is 5.
    type: int
    default: 5

  disallowed_reuse:
    description:
      - Specifies the number of previous passwords that are disallowed for reuse.
      - The default setting is 6. The minimum allowed value is 6.
    type: int
    default: 6

  change_delay:
    description:
      - Specifies the number of days that must pass between password changes. The default setting is 0.
    type: int
    default: 0

  delay_after_failed_login:
    description:
      - Specifies the amount of delay observed by the system in seconds upon invalid login attempts.
      - The default setting is 4 seconds.
    type: int
    default: 4

  passwd_min_lowercase_chars:
    description:
      - Specifies the minimum number of lowercase characters required in a password.
      - The default setting is 0.
    type: int
    default: 0

  passwd_min_uppercase_chars:
    description:
      - Specifies the minimum number of uppercase characters required in a password.
      - The default setting is 0.
    type: int
    default: 0

  passwd_min_digits:
    description:
      - Specifies the minimum number of digits required in a password.
      - The default setting is 0.
    type: int
    default: 0

  passwd_expiry_warn_time:
    description:
      - Specifies the warning period for password expiry in days.
      - A value of 0 means warn user about password expiry upon every successful login.
      - The default setting is -1 (unlimited), which means never warn about password expiry.
    type: int
    default: -1

  account_expiry_time:
    description:
      - Specifies account expiration in days.
      - The default setting is -1 (unlimited), which means the accounts never expire.
      - The account expiry time must be greater than account inactive limit.
    type: int
    default: -1

  account_inactive_limit:
    description:
      - Specifies inactive account expiry limit in days.
      - The default setting is -1 (unlimited), which means the inactive accounts never expire.
    type: int
    default: -1

  account_lockout_duration:
    description:
      - Specifies the duration in ISO 8601 format (P[<int>D]T[<int>H][<int>M][<int>S]) for which an account is locked
        if the failed login attempts reach the allowed maximum.
      - The default is 1 hour.
    type: str
    default: PT1H

notes:
  - Only supported with REST and requires ONTAP 9.6 or later.
"""

EXAMPLES = """
- name: Modify user account restrictions - minimum size of the password
  netapp.ontap.na_ontap_user_role_config:
    state: present
    role: csahu_role1
    vserver: svm1
    passwd_minlength: 10
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"
    use_rest: always

- name: Modify user account restrictions - maximum allowed invalid login attempts
  netapp.ontap.na_ontap_user_role_config:
    state: present
    role: csahu_role1
    vserver: svm1
    max_failed_login_attempts: 3
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
    https: true
    validate_certs: "{{ validate_certs }}"
    use_rest: always
"""

RETURN = """
"""

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic


class NetAppOntapUserRoleConfiguration:
    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_rest_only_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present'], default='present'),
            role=dict(required=True, type='str'),
            vserver=dict(required=False, type='str'),
            username_minlength=dict(required=False, type='int', default=3),
            username_alphanum=dict(required=False, type='bool', default=False),
            passwd_minlength=dict(required=False, type='int', default=8, no_log=False),
            passwd_alphanum=dict(required=False, type='bool', default=True),
            passwd_min_special_chars=dict(required=False, type='int', default=0, no_log=False),
            passwd_expiry_time=dict(required=False, type='int', default=-1, no_log=False),
            require_initial_passwd_update=dict(required=False, type='bool', default=False),
            max_failed_login_attempts=dict(required=False, type='int', default=5),
            disallowed_reuse=dict(required=False, type='int', default=6),
            change_delay=dict(required=False, type='int', default=0),
            delay_after_failed_login=dict(required=False, type='int', default=4),
            passwd_min_lowercase_chars=dict(required=False, type='int', default=0, no_log=False),
            passwd_min_uppercase_chars=dict(required=False, type='int', default=0, no_log=False),
            passwd_min_digits=dict(required=False, type='int', default=0, no_log=False),
            passwd_expiry_warn_time=dict(required=False, type='int', default=-1, no_log=False),
            account_expiry_time=dict(required=False, type='int', default=-1),
            account_inactive_limit=dict(required=False, type='int', default=-1),
            account_lockout_duration=dict(required=False, type='str', default='PT1H')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule(self.module)
        self.parameters = self.na_helper.check_and_set_parameters(self.module)

        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        self.rest_api.fail_if_not_rest_minimum_version('na_ontap_user_role_config:', 9, 6)

    def get_user_role_config(self):
        """ Retrieves user role configuration for the given node """
        api = 'private/cli/security/login/role/config'
        params = {
            'role': self.parameters['role'],
            'vserver': self.parameters['vserver'],
            'fields': 'vserver,'
                      'role,'
                      'username-minlength,'
                      'username-alphanum,'
                      'passwd-minlength,'
                      'passwd-alphanum,'
                      'passwd-min-special-chars,'
                      'passwd-expiry-time,'
                      'require-initial-passwd-update,'
                      'max-failed-login-attempts,'
                      'disallowed-reuse,'
                      'change-delay,'
                      'delay-after-failed-login,'
                      'passwd-min-lowercase-chars,'
                      'passwd-min-uppercase-chars,'
                      'passwd-min-digits,'
                      'passwd-expiry-warn-time,'
                      'account-expiry-time,'
                      'account-inactive-limit,'
                      'account-lockout-duration'
        }
        record, error = rest_generic.get_one_record(self.rest_api, api, params)
        if error:
            self.module.fail_json(msg="Error fetching user account configurations for role %s: %s" % (self.parameters['role'], to_native(error)),
                                  exception=traceback.format_exc())
        if record:
            for key in ('passwd_expiry_time', 'passwd_expiry_warn_time', 'account_expiry_time', 'account_inactive_limit'):
                if record.get(key) == 'unlimited':
                    record[key] = -1
            return {
                'username_minlength': record.get('username_minlength'),
                'username_alphanum': self.enabled_to_bool(record.get('username_alphanum')),
                'passwd_minlength': record.get('passwd_minlength'),
                'passwd_alphanum': self.enabled_to_bool(record.get('passwd_alphanum')),
                'passwd_min_special_chars': record.get('passwd_min_special_chars'),
                'passwd_expiry_time': record.get('passwd_expiry_time'),
                'require_initial_passwd_update': self.enabled_to_bool(record.get('require_initial_passwd_update')),
                'max_failed_login_attempts': record.get('max_failed_login_attempts'),
                'disallowed_reuse': record.get('disallowed_reuse'),
                'change_delay': record.get('change_delay'),
                'delay_after_failed_login': record.get('delay_after_failed_login'),
                'passwd_min_lowercase_chars': record.get('passwd_min_lowercase_chars'),
                'passwd_min_uppercase_chars': record.get('passwd_min_uppercase_chars'),
                'passwd_min_digits': record.get('passwd_min_digits'),
                'passwd_expiry_warn_time': record.get('passwd_expiry_warn_time'),
                'account_expiry_time': record.get('account_expiry_time'),
                'account_inactive_limit': record.get('account_inactive_limit'),
                'account_lockout_duration': record.get('account_lockout_duration', 'PT1H')
            }
        return None

    def modify_user_role_config(self, modify):
        """ Modifies user role configuration for the given node """
        api = 'private/cli/security/login/role/config'
        params = {
            'role': self.parameters['role'],
            'vserver': self.parameters['vserver']
        }
        # Convert boolean values to enabled/disabled for API body
        if modify:
            for key in ('username_alphanum', 'passwd_alphanum'):
                if key in modify and isinstance(modify[key], bool):
                    modify[key] = self.bool_to_enabled(modify[key])
            for key in ('passwd_expiry_time', 'passwd_expiry_warn_time', 'account_expiry_time', 'account_inactive_limit'):
                if key in modify and modify[key] == -1:
                    modify[key] = 'unlimited'
        dummy, error = rest_generic.patch_async(self.rest_api, api, uuid_or_name=None, body=modify, query=params)
        if error:
            self.module.fail_json(msg='Error modifying user account configurations for role %s: %s.' % (self.parameters['role'], to_native(error)),
                                  exception=traceback.format_exc())

    @staticmethod
    def bool_to_enabled(item):
        return 'enabled' if item else 'disabled'

    @staticmethod
    def enabled_to_bool(item, reverse=False):
        """ convertes enabled/disabled to true/false or vice versa """
        if reverse:
            return 'enabled' if item else 'disabled'
        return True if item == 'enabled' else False

    def apply(self):
        current = self.get_user_role_config()
        modify = self.na_helper.get_modified_attributes(current, self.parameters)
        if self.na_helper.changed and not self.module.check_mode:
            self.modify_user_role_config(modify)
        result = netapp_utils.generate_result(self.na_helper.changed, modify=modify)
        self.module.exit_json(**result)


def main():
    user_role_config = NetAppOntapUserRoleConfiguration()
    user_role_config.apply()


if __name__ == '__main__':
    main()
