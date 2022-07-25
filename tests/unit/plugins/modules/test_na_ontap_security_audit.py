import unittest

''' unit test for ONTAP security audit Ansible module '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
  AnsibleFailJson, AnsibleExitJson, patch_ansible, expect_and_capture_ansible_exception, call_main, create_module
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, print_requests, register_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_audit import \
  NetAppONTAPSecuriyAudit as audit_module  # module under test

if not netapp_utils.has_netapp_lib():
  pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


class MockONTAPConnection():
  """ mock server connection to ONTAP host """

  def __init__(self, kind=None):
    self.type = kind
    self.xml_in = None
    self.xml_out = None

  def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
    ''' mock invoke_successfully returning xml data '''
    self.xml_in = xml
    if self.type == 'asup':
      xml = self.build_asup_info()
    elif self.type == 'asup_fail':
      raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
    self.xml_out = xml
    return xml

  @staticmethod



def default_args():
  args = {
    'hostname': '141.94.231.150',
    'username': 'admin',
    'https': 'true',
    'validate_certs': 'false',
    'password': 'Storage2020!',
    'use_rest': 'always'
  }
  return args


SRR = {
  # common responses
  'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
  'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
  'is_zapi': (400, {}, "Unreachable"),
  'empty_good': (200, {}, None),
  'zero_record': (200, dict(records=[], num_records=0), None),
  'end_of_sequence': (500, None, "Unexpected call to send_request"),
  'generic_error': (400, None, "Expected error"),
  'get_response_all_true': (
    200,
    {
      'records': [
        {
          "cliget": true,
          "httpget": true,
          "ontapiget": true
        }
      ]}, None),
  'get_responses_cliget_true' : (200,{
    'records': [
                {
                  "cliget": true,
                  "httpget": true,
                  "ontapiget": true
                }
              ]
            }, None),


}


def get_asup_mock_object(cx_type='zapi', kind=None):
  audit_obj = audit_module()
  if cx_type == 'zapi':
    if kind is None:
      audit_obj.server = MockONTAPConnection()
    else:
      audit_obj.server = MockONTAPConnection(kind=kind)
  return audit_obj


def test_module_fail_when_required_args_missing(patch_ansible):
  ''' required arguments are reported as errors '''
  with pytest.raises(AnsibleFailJson) as exc:
    set_module_args({})
    audit_module()
  print('Info: %s' % exc.value.args[0]['msg'])


def test_rest_missing_arguments(patch_ansible):  # pylint: disable=redefined-outer-name,unused-argument
  ''' create asup '''
  args = dict(default_args())
  del args['hostname']
  set_module_args(args)
  with pytest.raises(AnsibleFailJson) as exc:
    audit_module()
  msg = 'missing required arguments: hostname'
  assert exc.value.args[0]['msg'] == msg

def test_apply_security_audit():
  register_responses([
    ('PATCH', 'security/audit', SRR['empty_good']),
    ('GET', 'security/audit', SRR['get_response_all_true'])
  ])

  module_args  =  {
    'cliget' : True,
    'httpget' : True,
    'ontapiget' : True
  }
  assert create_and_apply(audit_module, default_args(), module_args)['changed']


if __name__ == '__main__':
  unittest.main()
