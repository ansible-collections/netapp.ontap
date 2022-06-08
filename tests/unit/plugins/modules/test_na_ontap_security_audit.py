from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import json

import pytest
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_security_audit import \
  NetAppONTAPSecurityAudit as my_module
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
  AnsibleFailJson, exit_json, fail_json

if not netapp_utils.has_netapp_lib():
  pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

SRR = {
  # common responses
  'is_rest': (200, dict(version=dict(generation=9, major=7, minor=0, full='dummy')), None),
  'empty_good': (200, {}, None),
  'zero_record': (200, dict(records=[], num_records=0), None),
  'get_response': (200, dict(records=[{"cli": True, "http": True, "ontapi": False}], num_records=1), None),
  'get_response_all_false': (
    200,
    {
      'records': [
        {
          "cli": False,
          "http": False,
          "ontapi": False
        }
      ]}, None),
  'get_response_all_true': (
    200,
    {
      'records': [
        {
          "cli": True,
          "http": True,
          "ontapi": True
        }
      ]}, None),
  'get_responses_cliget_true': (200, {
    'records': [
      {
        "cli": True,
        "http": False,
        "ontapi": False
      }
    ]
  }, None),
}


def set_module_args(args):
  """prepare arguments so that they will be picked up during module creation"""
  args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
  basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
  """Exception class to be raised by module.exit_json and caught by the test case"""


class AnsibleFailJson(Exception):
  """Exception class to be raised by module.fail_json and caught by the test case"""


def exit_json(*args, **kwargs):  # pylint: disable=unused-argument
  """function to patch over exit_json; package return data into an exception"""
  if 'changed' not in kwargs:
    kwargs['changed'] = False
  raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
  """function to patch over fail_json; package return data into an exception"""
  kwargs['failed'] = True
  raise AnsibleFailJson(kwargs)


class MockONTAPConnection(object):
  """ mock server connection to ONTAP host """

  def __init__(self, kind=None, data=None):
    self.kind = kind
    self.params = data
    self.xml_in = None
    self.xml_out = None

class TestMyModule(unittest.TestCase):
  def setUp(self):
    self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                             exit_json=exit_json,
                                             fail_json=fail_json)
    self.mock_module_helper.start()
    self.addCleanup(self.mock_module_helper.stop)

  @staticmethod
  def mock_args():
    return {
      'hostname': '192.168.0.1',
      'username': 'roro',
      'https': 'true',
      'validate_certs': 'false',
      'password': '*********!',
      'use_rest': 'always'
    }

  @staticmethod
  def get_security_audit_mock_object():
    m = my_module()
    return m

  def test_module_fail_when_required_args_missing(self):
    """ required arguments are reported as errors """
    with pytest.raises(AnsibleFailJson) as exc:
      set_module_args({})
      my_module()
    print('Info: %s' % exc.value.args[0]['msg'])

  def test_missing_argument(self):
    data = self.mock_args()
    del data['hostname']
    set_module_args(data)
    with pytest.raises(AnsibleFailJson) as exc:
      my_module()
    msg = 'missing required arguments: hostname, security_audit'
    assert exc.value.args[0]['msg'] == msg

  @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
  def test_get_security_audit(self, mock):
    data = self.mock_args()
    data['security_audit'] = {
      'cli': 'False'
    }
    set_module_args(data)
    mock.side_effect = [
      SRR['is_rest'],
      SRR['get_response_all_false']
    ]
    assert  self.get_security_audit_mock_object().get_securiy_audit() is not None

  @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
  def test_apply_security_audit(self, mock):
    data = self.mock_args()
    data['security_audit'] = {
      'cli': 'False',
      'http': 'False',
      'ontapi': 'True'
    }
    set_module_args(data)
    mock.side_effect = [
      SRR['is_rest'],
      SRR['get_response'],
      SRR['empty_good']
    ]
    with pytest.raises(AnsibleExitJson) as exc:
      self.get_security_audit_mock_object().apply()['changed']
    assert exc.value.args[0]['changed']

