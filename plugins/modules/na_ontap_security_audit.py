from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic

DOCUMENTATION = '''
module: na_ontap_security_audit
short_description: Modify NetApp ONTAP security audit
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 21.24.1
author: gheorghe.luca96@gmail.com <gikuluca>
description:
- Enable or disable ontap, cli, http for security audit 
options:
  cli:
    description: 
      - Enable cli audit 
    type: bool
  ontapi:
    description:
      - Enable ontap audit
    type: bool
  http:
    description:
      - Enable http audit
    type: bool
'''
EXAMPLES = """
- name: Manage security audit options
  na_ontap_security_audit:
    hostname: <cluster ip>
    username: admin
    password: password
    validate_certs: false
    security_audit:
      cli: True
      http: True
      ontapi: True
"""

from ansible.module_utils.basic import AnsibleModule
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI


class NetAppONTAPSecurityAudit:

  def __init__(self):
    self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
    self.argument_spec.update(
      dict(
        security_audit=dict(
          type='dict',
          required=True,
          options=dict(
            cli=dict(required=False, type='bool'),
            http=dict(required=False, type='bool'),
            ontapi=dict(required=False, type='bool')
          )
        )
      )
    )

    self.module = AnsibleModule(
      argument_spec=self.argument_spec,
      supports_check_mode=True
    )

    self.na_helper = NetAppModule()
    self.parameters = self.na_helper.set_parameters(self.module.params)

    self.rest_api = OntapRestAPI(self.module)
    self.use_rest = self.rest_api.is_rest()
    self.api = 'security/audit'

    if not self.use_rest:
      self.module.fail_json(msg="Always use REST, this module support only ontap REST API")

  def get_securiy_audit(self):
    '''
        Get security audit
    '''
    record, error = rest_generic.get_one_record(self.rest_api, self.api, fields='cli,http,ontapi')
    response = {}
    if record is not None:
      for element in ('ontapi', 'cli', 'http'):
        value = record.get(f"{element}")
        if value is not None:
          response[element] = value

    if error:
      self.module.fail_json(msg=error)
    return response

  def patch_security_audit(self, modify):

    message, error = rest_generic.patch_async(self.rest_api, self.api, None, modify)
    if error:
     self.module.fail_json(msg=error)

  def apply(self):
    current = self.get_securiy_audit()
    modify = self.na_helper.get_modified_attributes(current, self.parameters['security_audit'])
    if self.na_helper.changed and not self.module.check_mode:
      self.patch_security_audit(modify)
    self.module.exit_json(changed=self.na_helper.changed)


def main():
  cfg = NetAppONTAPSecurityAudit()
  cfg.apply()


if __name__ == '__main__':
  main()

