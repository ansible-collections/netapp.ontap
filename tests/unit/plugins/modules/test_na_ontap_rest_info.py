# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' Unit Tests NetApp ONTAP REST APIs Ansible module: na_ontap_rest_info '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_rest_info \
    import NetAppONTAPGatherInfo as ontap_rest_info_module

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'validate_ontap_version_pass': (200, {'version': 'ontap_version'}, None),
    'validate_ontap_version_fail': (200, None, 'API not found error'),
    'get_subset_info': (200,
                        {'_links': {'self': {'href': 'dummy_href'}},
                         'num_records': 3,
                         'records': [{'name': 'dummy_vol1'},
                                     {'name': 'dummy_vol2'},
                                     {'name': 'dummy_vol3'}],
                         'version': 'ontap_version'}, None),
    'get_subset_info_with_next': (200,
                                  {'_links': {'self': {'href': 'dummy_href'},
                                              'next': {'href': '/api/next_record_api'}},
                                   'num_records': 3,
                                   'records': [{'name': 'dummy_vol1'},
                                               {'name': 'dummy_vol2'},
                                               {'name': 'dummy_vol3'}],
                                   'version': 'ontap_version'}, None),
    'get_next_record': (200,
                        {'_links': {'self': {'href': 'dummy_href'}},
                         'num_records': 2,
                         'records': [{'name': 'dummy_vol1'},
                                     {'name': 'dummy_vol2'}],
                         'version': 'ontap_version'}, None),
    'metrocluster_post': (200,
                          {'job': {
                              'uuid': 'fde79888-692a-11ea-80c2-005056b39fe7',
                              '_links': {
                                  'self': {
                                      'href': '/api/cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7'}}
                          }},
                          None),
    'metrocluster_return': (200,
                            {"_links": {
                                "self": {
                                    "href": "/api/cluster/metrocluster/diagnostics"
                                }
                            }, "aggregate": {
                                "state": "ok",
                                "summary": {
                                    "message": ""
                                }, "timestamp": "2020-07-22T16:42:51-07:00"
                            }}, None),
    'job': (200,
            {
                "uuid": "cca3d070-58c6-11ea-8c0c-005056826c14",
                "description": "POST /api/cluster/metrocluster",
                "state": "success",
                "message": "There are not enough disks in Pool1.",
                "code": 2432836,
                "start_time": "2020-02-26T10:35:44-08:00",
                "end_time": "2020-02-26T10:47:38-08:00",
                "_links": {
                    "self": {
                        "href": "/api/cluster/jobs/cca3d070-58c6-11ea-8c0c-005056826c14"
                    }
                }
            }, None)
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

    def set_args_run_ontap_version_check(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024,
            'gather_subset': ['volume_info']
        })

    def set_args_run_metrocluster_diag(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024,
            'gather_subset': ['cluster/metrocluster/diagnostics']
        })

    def set_args_run_ontap_gather_facts_for_vserver_info(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024,
            'gather_subset': ['vserver_info']
        })

    def set_args_run_ontap_gather_facts_for_volume_info(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024,
            'gather_subset': ['volume_info']
        })

    def set_args_run_ontap_gather_facts_for_all_subsets(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024,
            'gather_subset': ['all']
        })

    def set_args_run_ontap_gather_facts_for_all_subsets_with_fields_section_pass(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024,
            'fields': '*',
            'gather_subset': ['all']
        })

    def set_args_run_ontap_gather_facts_for_all_subsets_with_fields_section_fail(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 1024,
            'fields': ['uuid', 'name', 'node'],
            'gather_subset': ['all']
        })

    def set_args_run_ontap_gather_facts_for_aggregate_info_with_fields_section_pass(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'fields': ['uuid', 'name', 'node'],
            'validate_certs': False,
            'max_records': 1024,
            'gather_subset': ['aggregate_info']
        })

    def set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass(self):
        return dict({
            'hostname': 'hostname',
            'username': 'username',
            'password': 'password',
            'https': True,
            'validate_certs': False,
            'max_records': 3,
            'gather_subset': ['volume_info']
        })

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_run_ontap_version_check_for_9_6_pass(self, mock_request):
        set_module_args(self.set_args_run_ontap_version_check())
        my_obj = ontap_rest_info_module()
        mock_request.side_effect = [
            SRR['validate_ontap_version_pass'],
            SRR['get_subset_info'],
        ]

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_run_ontap_version_check_for_10_2_pass(self, mock_request):
        set_module_args(self.set_args_run_ontap_version_check())
        my_obj = ontap_rest_info_module()
        mock_request.side_effect = [
            SRR['validate_ontap_version_pass'],
            SRR['get_subset_info'],
        ]

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_run_ontap_version_check_for_9_2_fail(self, mock_request):
        ''' Test for Checking the ONTAP version '''
        set_module_args(self.set_args_run_ontap_version_check())
        my_obj = ontap_rest_info_module()
        mock_request.side_effect = [
            SRR['validate_ontap_version_fail'],
        ]

        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['msg'] == SRR['validate_ontap_version_fail'][2]

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_run_metrocluster_pass(self, mock_request):
        set_module_args(self.set_args_run_metrocluster_diag())
        my_obj = ontap_rest_info_module()
        gather_subset = ['cluster/metrocluster/diagnostics']
        mock_request.side_effect = [
            SRR['validate_ontap_version_pass'],
            SRR['metrocluster_post'],
            SRR['job'],
            SRR['metrocluster_return']
        ]

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_run_metrocluster_digag_pass: %s' % repr(exc.value.args))
        assert set(exc.value.args[0]['ontap_info']) == set(gather_subset)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_run_ontap_gather_facts_for_vserver_info_pass(self, mock_request):
        set_module_args(self.set_args_run_ontap_gather_facts_for_vserver_info())
        my_obj = ontap_rest_info_module()
        gather_subset = ['svm/svms']
        mock_request.side_effect = [
            SRR['validate_ontap_version_pass'],
            SRR['get_subset_info'],
        ]

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_run_ontap_gather_facts_for_vserver_info_pass: %s' % repr(exc.value.args))
        assert set(exc.value.args[0]['ontap_info']) == set(gather_subset)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_run_ontap_gather_facts_for_volume_info_pass(self, mock_request):
        set_module_args(self.set_args_run_ontap_gather_facts_for_volume_info())
        my_obj = ontap_rest_info_module()
        gather_subset = ['storage/volumes']
        mock_request.side_effect = [
            SRR['validate_ontap_version_pass'],
            SRR['get_subset_info'],
        ]

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_run_ontap_gather_facts_for_volume_info_pass: %s' % repr(exc.value.args))
        assert set(exc.value.args[0]['ontap_info']) == set(gather_subset)

    # Super Important, Metrocluster doesn't call get_subset_info and has 3 api calls instead of 1!!!!
    # The metrocluster calls need to be in the correct place. The Module return the keys in a sorted list.
    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_run_ontap_gather_facts_for_all_subsets_pass(self, mock_request):
        set_module_args(self.set_args_run_ontap_gather_facts_for_all_subsets())
        my_obj = ontap_rest_info_module()
        gather_subset = ['application/applications', 'application/templates', 'cloud/targets', 'cluster/chassis', 'cluster/jobs',
                         'cluster/metrocluster/diagnostics', 'cluster/metrics', 'cluster/nodes', 'cluster/peers', 'cluster/schedules',
                         'cluster/software', 'cluster/software/download', 'cluster/software/history', 'cluster/software/packages',
                         'name-services/dns', 'name-services/ldap', 'name-services/name-mappings', 'name-services/nis',
                         'network/ethernet/broadcast-domains', 'network/ethernet/ports', 'network/fc/logins', 'network/fc/wwpn-aliases',
                         'network/ip/interfaces', 'network/ip/routes', 'network/ip/service-policies', 'network/ipspaces',
                         'protocols/cifs/home-directory/search-paths', 'protocols/cifs/services', 'protocols/cifs/shares',
                         'protocols/san/fcp/services', 'protocols/san/igroups', 'protocols/san/iscsi/credentials',
                         'protocols/san/iscsi/services', 'protocols/san/lun-maps', 'security/accounts', 'security/roles', 'storage/aggregates',
                         'storage/disks', 'storage/flexcache/flexcaches', 'storage/flexcache/origins', 'storage/luns', 'storage/namespaces',
                         'storage/ports', 'storage/qos/policies', 'storage/qtrees', 'storage/quota/reports', 'storage/quota/rules',
                         'storage/shelves', 'storage/snapshot-policies', 'storage/volumes', 'support/autosupport', 'support/autosupport/messages',
                         'support/ems', 'support/ems/destinations', 'support/ems/events', 'support/ems/filters', 'svm/peers', 'svm/peer-permissions',
                         'svm/svms']
        mock_request.side_effect = [
            SRR['validate_ontap_version_pass'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['metrocluster_post'],
            SRR['job'],
            SRR['metrocluster_return'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
        ]

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_run_ontap_gather_facts_for_all_subsets_pass: %s' % repr(exc.value.args))
        assert set(exc.value.args[0]['ontap_info']) == set(gather_subset)

    # Super Important, Metrocluster doesn't call get_subset_info and has 3 api calls instead of 1!!!!
    # The metrocluster calls need to be in the correct place. The Module return the keys in a sorted list.
    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_run_ontap_gather_facts_for_all_subsets_with_fields_section_pass(self, mock_request):
        set_module_args(self.set_args_run_ontap_gather_facts_for_all_subsets_with_fields_section_pass())
        my_obj = ontap_rest_info_module()
        gather_subset = ['application/applications', 'application/templates', 'cloud/targets', 'cluster/chassis', 'cluster/jobs',
                         'cluster/metrocluster/diagnostics', 'cluster/metrics', 'cluster/nodes', 'cluster/peers', 'cluster/schedules',
                         'cluster/software', 'cluster/software/download', 'cluster/software/history', 'cluster/software/packages',
                         'name-services/dns', 'name-services/ldap', 'name-services/name-mappings', 'name-services/nis',
                         'network/ethernet/broadcast-domains', 'network/ethernet/ports', 'network/fc/logins', 'network/fc/wwpn-aliases',
                         'network/ip/interfaces', 'network/ip/routes', 'network/ip/service-policies', 'network/ipspaces',
                         'protocols/cifs/home-directory/search-paths', 'protocols/cifs/services', 'protocols/cifs/shares',
                         'protocols/san/fcp/services', 'protocols/san/igroups', 'protocols/san/iscsi/credentials',
                         'protocols/san/iscsi/services', 'protocols/san/lun-maps', 'security/accounts', 'security/roles', 'storage/aggregates',
                         'storage/disks', 'storage/flexcache/flexcaches', 'storage/flexcache/origins', 'storage/luns', 'storage/namespaces',
                         'storage/ports', 'storage/qos/policies', 'storage/qtrees', 'storage/quota/reports', 'storage/quota/rules',
                         'storage/shelves', 'storage/snapshot-policies', 'storage/volumes', 'support/autosupport', 'support/autosupport/messages',
                         'support/ems', 'support/ems/destinations', 'support/ems/events', 'support/ems/filters', 'svm/peers', 'svm/peer-permissions',
                         'svm/svms']
        mock_request.side_effect = [
            SRR['validate_ontap_version_pass'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['metrocluster_post'],
            SRR['job'],
            SRR['metrocluster_return'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
        ]

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_run_ontap_gather_facts_for_all_subsets_pass: %s' % repr(exc.value.args))
        assert set(exc.value.args[0]['ontap_info']) == set(gather_subset)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_run_ontap_gather_facts_for_all_subsets_with_fields_section_fail(self, mock_request):
        set_module_args(self.set_args_run_ontap_gather_facts_for_all_subsets_with_fields_section_fail())
        my_obj = ontap_rest_info_module()
        error_message = "Error: fields: %s, only one subset will be allowed." \
                        % self.set_args_run_ontap_gather_facts_for_aggregate_info_with_fields_section_pass()['fields']
        mock_request.side_effect = [
            SRR['validate_ontap_version_pass'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
            SRR['get_subset_info'],
        ]

        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        print('Info: test_run_ontap_gather_facts_for_all_subsets_pass: %s' % repr(exc.value.args))
        assert exc.value.args[0]['msg'] == error_message

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_run_ontap_gather_facts_for_aggregate_info_pass_with_fields_section_pass(self, mock_request):
        set_module_args(self.set_args_run_ontap_gather_facts_for_aggregate_info_with_fields_section_pass())
        my_obj = ontap_rest_info_module()
        gather_subset = ['storage/aggregates']
        mock_request.side_effect = [
            SRR['validate_ontap_version_pass'],
            SRR['get_subset_info'],
        ]

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_run_ontap_gather_facts_for_volume_info_pass: %s' % repr(exc.value.args))
        assert set(exc.value.args[0]['ontap_info']) == set(gather_subset)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass(self, mock_request):
        set_module_args(self.set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass())
        my_obj = ontap_rest_info_module()
        total_records = 5
        mock_request.side_effect = [
            SRR['validate_ontap_version_pass'],
            SRR['get_subset_info_with_next'],
            SRR['get_next_record'],
        ]

        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass: %s' % repr(exc.value.args))
        assert exc.value.args[0]['ontap_info']['storage/volumes']['num_records'] == total_records
