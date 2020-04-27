# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' Unit Tests NetApp ONTAP REST APIs Ansible module: na_ontap_rest_info '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from requests import Response
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_rest_info \
    import NetAppONTAPGatherInfo as ontap_rest_info_module


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""
    pass


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""
    pass


def exit_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


class TestMyModule(unittest.TestCase):
    ''' A group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)

    def set_default_args(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False
        })

    def set_args_run_Ontap_version_check(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024
        })

    def set_args_run_Ontap_gather_facts_for_vserver_info(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024,
            'gather_subset': ['vserver_info']
        })

    def set_args_run_Ontap_gather_facts_for_volume_info(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024,
            'gather_subset': ['volume_info']
        })

    def set_args_run_Ontap_gather_facts_for_all_subsets(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024,
            'gather_subset': ['all']
        })

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.get')
    def test_run_Ontap_version_check_for_9_6_pass(self, ontap_get_api):
        set_module_args(self.set_args_run_Ontap_version_check())
        my_obj = ontap_rest_info_module()
        response = {
            "code": 200,
            "version": "ontap_version"
        }
        ontap_get_api.return_value = response, None

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.get')
    def test_run_Ontap_version_check_for_10_2_pass(self, ontap_get_api):
        set_module_args(self.set_args_run_Ontap_version_check())
        my_obj = ontap_rest_info_module()
        response = {
            "code": 200,
            "version": "ontap_version"
        }
        ontap_get_api.return_value = response, None

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.get')
    def test_run_Ontap_version_check_for_9_2_fail(self, ontap_get_api):
        ''' Test for Checking the ONTAP version '''
        set_module_args(self.set_args_run_Ontap_version_check())
        my_obj = ontap_rest_info_module()
        error_message = "API not found error"
        ontap_get_api.return_value = None, error_message

        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['msg'] == error_message

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.get')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_rest_info.NetAppONTAPGatherInfo.validate_ontap_version')
    def test_run_Ontap_gather_facts_for_vserver_info_pass(self, validate_ontap_version, get_subset_info):
        set_module_args(self.set_args_run_Ontap_gather_facts_for_vserver_info())
        my_obj = ontap_rest_info_module()
        gather_subset = ['vserver_info']
        response = {'records': [{'name': 'test_vserver'}]}
        get_subset_info.return_value = response, None

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_run_Ontap_gather_facts_for_vserver_info_pass: %s' % repr(exc.value.args))
        assert set(exc.value.args[0]['ontap_info']) == set(gather_subset)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.get')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_rest_info.NetAppONTAPGatherInfo.validate_ontap_version')
    def test_run_Ontap_gather_facts_for_volume_info_pass(self, validate_ontap_version, get_subset_info):
        set_module_args(self.set_args_run_Ontap_gather_facts_for_volume_info())
        my_obj = ontap_rest_info_module()
        gather_subset = ['volume_info']
        response = {'records': [{'name': 'test_volume'}]}
        get_subset_info.return_value = response, None

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_run_Ontap_gather_facts_for_volume_info_pass: %s' % repr(exc.value.args))
        assert set(exc.value.args[0]['ontap_info']) == set(gather_subset)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.get')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_rest_info.NetAppONTAPGatherInfo.validate_ontap_version')
    def test_run_Ontap_gather_facts_for_all_subsets_pass(self, validate_ontap_version, get_subset_info):
        set_module_args(self.set_args_run_Ontap_gather_facts_for_all_subsets())
        my_obj = ontap_rest_info_module()
        gather_subset = ['aggregate_info', 'vserver_info', 'volume_info']
        response = {'records': [{'name': 'dummy'}]}
        get_subset_info.return_value = response, None

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_run_Ontap_gather_facts_for_all_subsets_pass: %s' % repr(exc.value.args))
        assert set(exc.value.args[0]['ontap_info']) == set(gather_subset)
