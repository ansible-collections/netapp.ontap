# (c) 2020-2023, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' Unit Tests NetApp ONTAP REST APIs Ansible module: na_ontap_rest_info '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import call_main, create_module, \
    expect_and_capture_ansible_exception, patch_ansible, create_and_apply, assert_warning_was_raised, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_rest_info \
    import NetAppONTAPGatherInfo as ontap_rest_info_module, main as my_main

if sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

# REST API canned responses when mocking send_request
SRR = rest_responses({
    # common responses
    'validate_ontap_version_pass': (
        200, dict(version=dict(generation=9, major=10, minor=1, full='dummy_9_10_1')), None),
    'validate_ontap_version_fail': (200, None, 'API not found error'),
    'error_invalid_api': (500, None, {'code': 3, 'message': 'Invalid API'}),
    'error_user_is_not_authorized': (500, None, {'code': 6, 'message': 'user is not authorized'}),
    'error_no_processing': (500, None, {'code': 123, 'message': 'error reported as is'}),
    'error_no_aggr_recommendation': (
        500, None, {'code': 19726344, 'message': 'No recommendation can be made for this cluster'}),
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
    'get_subset_info_without_hal_links': (200,
                                          {'num_records': 3,
                                           'records': [{'name': 'dummy_vol1'},
                                                       {'name': 'dummy_vol2'},
                                                       {'name': 'dummy_vol3'}],
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
            }, None),
    'get_private_cli_subset_info': (200,
                                    {
                                        'records': [
                                            {'node': 'node1', 'check_type': 'type'},
                                            {'node': 'node1', 'check_type': 'type'},
                                            {'node': 'node1', 'check_type': 'type'}],
                                        "num_records": 3}, None),
    'get_private_cli_vserver_security_file_directory_info': (
        200,
        {
            'records': [
                {'acls': ['junk', 'junk', 'DACL - ACEs', 'AT-user-0x123']},
                {'node': 'node1', 'check_type': 'type'},
                {'node': 'node1', 'check_type': 'type'}],
            "num_records": 3}, None),
    'lun_info': (200, {'records': [{"serial_number": "z6CcD+SK5mPb"}]}, None),
    'volume_info': (200, {"uuid": "7882901a-1aef-11ec-a267-005056b30cfa"}, None),
    'svm_uuid': (200, {"records": [{"uuid": "test_uuid"}], "num_records": 1}, None),
    'get_uuid_policy_id_export_policy': (
        200,
        {
            "records": [{
                "svm": {
                    "uuid": "uuid",
                    "name": "svm"},
                "id": 123,
                "name": "ansible"
            }],
            "num_records": 1}, None),
    'vscan_on_access_policies': (
        200, {"records": [
            {
                "name": "on-access-test",
                "mandatory": True,
                "scope": {
                    "scan_readonly_volumes": True,
                    "exclude_paths": [
                        "\\dir1\\dir2\\name",
                        "\\vol\\a b",
                        "\\vol\\a,b\\"
                    ],
                    "scan_without_extension": True,
                    "include_extensions": [
                        "mp*",
                        "txt"
                    ],
                    "exclude_extensions": [
                        "mp*",
                        "txt"
                    ],
                    "only_execute_access": True,
                    "max_file_size": "2147483648"
                },
                "enabled": True
            }
        ]}, None
    ),
    'vscan_on_demand_policies': (
        200, {"records": [
            {
                "log_path": "/vol0/report_dir",
                "scan_paths": [
                    "/vol1/",
                    "/vol2/cifs/"
                ],
                "name": "task-1",
                "svm": {
                    "_links": {
                        "self": {
                            "href": "/api/resourcelink"
                        }
                    },
                    "name": "svm1",
                    "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
                },
                "scope": {
                    "exclude_paths": [
                        "/vol1/cold-files/",
                        "/vol1/cifs/names"
                    ],
                    "scan_without_extension": True,
                    "include_extensions": [
                        "vmdk",
                        "mp*"
                    ],
                    "exclude_extensions": [
                        "mp3",
                        "mp4"
                    ],
                    "max_file_size": "10737418240"
                },
                "schedule": {
                    "_links": {
                        "self": {
                            "href": "/api/resourcelink"
                        }
                    },
                    "name": "weekly",
                    "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
                }
            }
        ]}, None
    ),
    'vscan_scanner_pools': (
        200, {"records": [
            {
                "cluster": {
                    "_links": {
                        "self": {
                            "href": "/api/resourcelink"
                        }
                    },
                    "name": "cluster1",
                    "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
                },
                "name": "scanner-1",
                "servers": [
                    "1.1.1.1",
                    "10.72.204.27",
                    "vmwin204-27.fsct.nb"
                ],
                "privileged_users": [
                    "cifs\\u1",
                    "cifs\\u2"
                ],
                "svm": {
                    "_links": {
                        "self": {
                            "href": "/api/resourcelink"
                        }
                    },
                    "name": "svm1",
                    "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"
                },
                "role": "primary"
            }
        ]}, None
    )
})

ALL_SUBSETS = ['application/applications',
               'application/consistency-groups',
               'application/templates',
               'cloud/targets',
               'cluster',
               'cluster/chassis',
               'cluster/counter/tables',
               'cluster/firmware/history',
               'cluster/jobs',
               'cluster/licensing/capacity-pools',
               'cluster/licensing/license-managers',
               'cluster/licensing/licenses',
               'cluster/mediators',
               'cluster/metrics',
               'cluster/metrocluster',
               'cluster/metrocluster/diagnostics',
               'cluster/metrocluster/dr-groups',
               'cluster/metrocluster/interconnects',
               'cluster/metrocluster/nodes',
               'cluster/metrocluster/operations',
               'cluster/metrocluster/svms',
               'cluster/nodes',
               'cluster/ntp/keys',
               'cluster/ntp/servers',
               'cluster/peers',
               'cluster/schedules',
               'cluster/sensors',
               'cluster/software',
               'cluster/software/download',
               'cluster/software/history',
               'cluster/software/packages',
               'cluster/web',
               'name-services/cache/group-membership/settings',
               'name-services/cache/host/settings',
               'name-services/cache/netgroup/settings',
               'name-services/cache/setting',
               'name-services/cache/unix-group/settings',
               'name-services/dns',
               'name-services/ldap',
               'name-services/ldap-schemas',
               'name-services/local-hosts',
               'name-services/name-mappings',
               'name-services/nis',
               'name-services/unix-groups',
               'name-services/unix-users',
               'network/ethernet/broadcast-domains',
               'network/ethernet/ports',
               'network/ethernet/switch/ports',
               'network/ethernet/switches',
               'network/fc/fabrics',
               'network/fc/interfaces',
               'network/fc/logins',
               'network/fc/ports',
               'network/fc/wwpn-aliases',
               'network/http-proxy',
               'network/ip/bgp/peer-groups',
               'network/ip/interfaces',
               'network/ip/routes',
               'network/ip/service-policies',
               'network/ip/subnets',
               'network/ipspaces',
               'private/support/alerts',
               'protocols/active-directory',
               'protocols/audit',
               'protocols/cifs/connections',
               'protocols/cifs/domains',
               'protocols/cifs/group-policies',
               'protocols/cifs/home-directory/search-paths',
               'protocols/cifs/local-groups',
               'protocols/cifs/local-users',
               'protocols/cifs/netbios',
               'protocols/cifs/services',
               'protocols/cifs/session/files',
               'protocols/cifs/sessions',
               'protocols/cifs/shadow-copies',
               'protocols/cifs/shadowcopy-sets',
               'protocols/cifs/shares',
               'protocols/cifs/users-and-groups/privileges',
               'protocols/cifs/unix-symlink-mapping',
               'protocols/fpolicy',
               'protocols/locks',
               'protocols/ndmp',
               'protocols/ndmp/nodes',
               'protocols/ndmp/sessions',
               'protocols/ndmp/svms',
               'protocols/nfs/connected-clients',
               'protocols/nfs/connected-client-maps',
               'protocols/nfs/connected-client-settings',
               'protocols/nfs/export-policies',
               'protocols/nfs/kerberos/interfaces',
               'protocols/nfs/kerberos/realms',
               'protocols/nfs/services',
               'protocols/nvme/interfaces',
               'protocols/nvme/services',
               'protocols/nvme/subsystems',
               'protocols/nvme/subsystem-controllers',
               'protocols/nvme/subsystem-maps',
               'protocols/s3/buckets',
               'protocols/s3/services',
               'protocols/san/fcp/services',
               'protocols/san/igroups',
               'protocols/san/iscsi/credentials',
               'protocols/san/iscsi/services',
               'protocols/san/iscsi/sessions',
               'protocols/san/lun-maps',
               'protocols/san/portsets',
               'protocols/san/vvol-bindings',
               'protocols/vscan',
               'protocols/vscan/server-status',
               'security',
               'security/accounts',
               'security/anti-ransomware/suspects',
               'security/audit',
               'security/audit/destinations',
               'security/audit/messages',
               'security/authentication/cluster/ad-proxy',
               'security/authentication/cluster/ldap',
               'security/authentication/cluster/nis',
               'security/authentication/cluster/saml-sp',
               'security/authentication/publickeys',
               'security/aws-kms',
               'security/azure-key-vaults',
               'security/certificates',
               'security/gcp-kms',
               'security/ipsec',
               'security/ipsec/ca-certificates',
               'security/ipsec/policies',
               'security/ipsec/security-associations',
               'security/key-manager-configs',
               'security/key-managers',
               'security/key-stores',
               'security/login/messages',
               'security/multi-admin-verify',
               'security/multi-admin-verify/approval-groups',
               'security/multi-admin-verify/requests',
               'security/multi-admin-verify/rules',
               'security/roles',
               'security/ssh',
               'security/ssh/svms',
               'snapmirror/policies',
               'snapmirror/relationships',
               'storage/aggregates',
               'storage/bridges',
               'storage/cluster',
               'storage/disks',
               'storage/file/clone/split-loads',
               'storage/file/clone/split-status',
               'storage/file/clone/tokens',
               'storage/file/moves',
               'storage/flexcache/flexcaches',
               'storage/flexcache/origins',
               'storage/luns',
               'storage/namespaces',
               'storage/pools',
               'storage/ports',
               'storage/qos/policies',
               'storage/qos/workloads',
               'storage/qtrees',
               'storage/quota/reports',
               'storage/quota/rules',
               'storage/shelves',
               'storage/snaplock/audit-logs',
               'storage/snaplock/compliance-clocks',
               'storage/snaplock/event-retention/operations',
               'storage/snaplock/event-retention/policies',
               'storage/snaplock/file-fingerprints',
               'storage/snaplock/litigations',
               'storage/snapshot-policies',
               'storage/switches',
               'storage/tape-devices',
               'storage/volumes',
               'storage/volume-efficiency-policies',
               'support/autosupport',
               'support/autosupport/check',
               'support/autosupport/messages',
               'support/auto-update',
               'support/auto-update/configurations',
               'support/auto-update/updates',
               'support/configuration-backup',
               'support/configuration-backup/backups',
               'support/coredump/coredumps',
               'support/ems',
               'support/ems/destinations',
               'support/ems/events',
               'support/ems/filters',
               'support/ems/messages',
               'support/snmp',
               'support/snmp/traphosts',
               'support/snmp/users',
               'svm/migrations',
               'svm/peers',
               'svm/peer-permissions',
               'svm/svms']

# Super Important, Metrocluster doesn't call get_subset_info and has 3 api calls instead of 1!!!!
# The metrocluster calls need to be in the correct place. The Module return the keys in a sorted list.
ALL_RESPONSES = [
    ('GET', 'cluster', SRR['validate_ontap_version_pass']),
    ('GET', 'application/applications', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', 'application/templates', SRR['get_subset_info']),
    ('GET', 'cloud/targets', SRR['get_subset_info']),
    ('GET', 'cluster', SRR['get_subset_info']),
    ('GET', 'cluster/chassis', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', 'cluster/jobs', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', 'cluster/licensing/licenses', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', 'cluster/metrics', SRR['get_subset_info']),
    ('GET', 'cluster/metrocluster', SRR['get_subset_info']),
    # MCC DIAGs
    ('POST', 'cluster/metrocluster/diagnostics', SRR['metrocluster_post']),
    ('GET', 'cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7', SRR['job']),
    ('GET', 'cluster/metrocluster/diagnostics', SRR['metrocluster_return']),
    # Back to normal
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', 'cluster/metrocluster/nodes', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', 'cluster/nodes', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', 'cluster/ntp/servers', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', 'support/ems/filters', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', '*', SRR['get_subset_info']),
    ('GET', 'svm/peer-permissions', SRR['get_subset_info']),
    ('GET', 'svm/peers', SRR['get_subset_info']),
    ('GET', 'svm/svms', SRR['get_private_cli_subset_info']),
]


def set_default_args():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'https': True,
        'validate_certs': False
    })


def set_args_run_ontap_gather_facts_disable_hal_links():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'https': True,
        'validate_certs': False,
        'hal_linking': False
    })


def set_args_run_ontap_version_check():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'https': True,
        'validate_certs': False,
        'max_records': 1024,
        'gather_subset': ['volume_info']
    })


def set_args_run_metrocluster_diag():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'https': True,
        'validate_certs': False,
        'max_records': 1024,
        'gather_subset': ['cluster/metrocluster/diagnostics']
    })


def set_args_run_ontap_gather_facts_for_vserver_info():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'https': True,
        'validate_certs': False,
        'max_records': 1024,
        'gather_subset': ['vserver_info']
    })


def set_args_run_ontap_gather_facts_for_volume_info():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'https': True,
        'validate_certs': False,
        'max_records': 1024,
        'gather_subset': ['volume_info']
    })


def set_args_run_ontap_gather_facts_for_all_subsets():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'https': True,
        'validate_certs': False,
        'max_records': 1024,
        'gather_subset': ['all']
    })


def set_args_run_ontap_gather_facts_for_all_subsets_with_fields_section_pass():
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


def set_args_run_ontap_gather_facts_for_all_subsets_with_fields_section_fail():
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


def set_args_run_ontap_gather_facts_for_aggregate_info_with_fields_section_pass():
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


def set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'https': True,
        'validate_certs': False,
        'max_records': 3,
        'gather_subset': ['volume_info']
    })


def test_run_ontap_version_check_for_9_6_pass():
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['get_subset_info']),
    ])
    assert not create_and_apply(ontap_rest_info_module, set_args_run_ontap_version_check())['changed']


def test_run_ontap_version_check_for_10_2_pass():
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['get_subset_info']),
    ])
    assert not create_and_apply(ontap_rest_info_module, set_args_run_ontap_version_check())['changed']


def test_run_ontap_version_check_for_9_2_fail():
    ''' Test for Checking the ONTAP version '''
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_fail']),
    ])
    assert call_main(my_main, set_args_run_ontap_version_check(),
                     fail=True)['msg'] == 'Error using REST for version, error: %s.' % SRR['validate_ontap_version_fail'][2]


def test_version_warning_message():
    gather_subset = ['cluster/metrocluster/diagnostics']
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
    ])
    create_and_apply(ontap_rest_info_module, set_args_run_metrocluster_diag())
    assert_warning_was_raised('The following subset have been removed from your query as they are not supported on ' +
                              'your version of ONTAP cluster/metrocluster/diagnostics requires (9, 8), ')


def test_owning_resource_warning_message():
    gather_subset = ['cluster/nodes']
    register_responses([
        ('GET', 'cluster', SRR['is_rest_96']),
        ('GET', 'storage/volumes', SRR['get_subset_info']),
    ])
    extra_args = {
        'owning_resource': {'svm_name': 'testSVM'}
    }
    create_and_apply(ontap_rest_info_module, set_args_run_ontap_version_check(), extra_args)
    assert_warning_was_raised("Kindly refer to Ansible documentation to check the subsets that support option 'owning_resource'.")


# metrocluster/diagnostics doesn't call get_subset_info and has 3 api calls instead of 1
def test_run_metrocluster_pass():
    gather_subset = ['cluster/metrocluster/diagnostics']
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('POST', 'cluster/metrocluster/diagnostics', SRR['metrocluster_post']),
        ('GET', 'cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7', SRR['job']),
        ('GET', 'cluster/metrocluster/diagnostics', SRR['metrocluster_return']),
    ])
    assert set(create_and_apply(ontap_rest_info_module, set_args_run_metrocluster_diag())['ontap_info']) == set(
        gather_subset)


def test_run_ontap_gather_facts_for_vserver_info_pass():
    gather_subset = ['svm/svms']
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'svm/svms', SRR['get_subset_info']),
    ])
    assert set(create_and_apply(ontap_rest_info_module, set_args_run_ontap_gather_facts_for_vserver_info())['ontap_info']) == set(gather_subset)


def test_run_ontap_gather_facts_for_volume_info_pass():
    gather_subset = ['storage/volumes']
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['get_subset_info']),
    ])
    assert set(create_and_apply(ontap_rest_info_module, set_args_run_ontap_gather_facts_for_volume_info())['ontap_info']) == set(gather_subset)


def test_run_ontap_gather_facts_for_all_subsets_pass():
    gather_subset = ALL_SUBSETS
    register_responses(ALL_RESPONSES)
    assert set(create_and_apply(ontap_rest_info_module, set_args_run_ontap_gather_facts_for_all_subsets())['ontap_info']) == set(gather_subset)


def test_run_ontap_gather_facts_for_all_subsets_with_fields_section_pass():
    gather_subset = ALL_SUBSETS
    register_responses(ALL_RESPONSES)
    assert set(create_and_apply(ontap_rest_info_module,
                                set_args_run_ontap_gather_facts_for_all_subsets_with_fields_section_pass()
                                )['ontap_info']) == set(gather_subset)


def test_run_ontap_gather_facts_for_all_subsets_with_fields_section_fail():
    error_message = "Error: fields: %s, only one subset will be allowed." \
                    % set_args_run_ontap_gather_facts_for_aggregate_info_with_fields_section_pass()['fields']
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
    ])
    assert \
        create_and_apply(ontap_rest_info_module,
                         set_args_run_ontap_gather_facts_for_all_subsets_with_fields_section_fail(),
                         fail=True
                         )['msg'] == error_message


def test_run_ontap_gather_facts_for_aggregate_info_pass_with_fields_section_pass():
    gather_subset = ['storage/aggregates']
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/aggregates', SRR['get_subset_info']),
    ])
    assert set(create_and_apply(ontap_rest_info_module,
                                set_args_run_ontap_gather_facts_for_aggregate_info_with_fields_section_pass()
                                )['ontap_info']) == set(gather_subset)


def test_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass():
    total_records = 5
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['get_subset_info_with_next']),
        ('GET', '/next_record_api', SRR['get_next_record']),
    ])
    assert create_and_apply(ontap_rest_info_module,
                            set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass()
                            )['ontap_info']['storage/volumes']['num_records'] == total_records


def test_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass_python_keys():
    args = set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass()
    args['use_python_keys'] = True
    args['state'] = 'info'
    total_records = 5
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['get_subset_info_with_next']),
        ('GET', '/next_record_api', SRR['get_next_record']),
    ])
    assert create_and_apply(ontap_rest_info_module, args)['ontap_info']['storage_volumes']['num_records'] == total_records


def test_get_all_records_for_volume_info_with_parameters():
    args = set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass()
    args['use_python_keys'] = True
    args['parameters'] = {'fields': '*'}
    total_records = 5
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['get_subset_info_with_next']),
        ('GET', '/next_record_api', SRR['get_next_record']),
    ])
    assert create_and_apply(ontap_rest_info_module, args)['ontap_info']['storage_volumes']['num_records'] == total_records


def test_negative_error_on_get_next():
    args = set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass()
    args['use_python_keys'] = True
    args['parameters'] = {'fields': '*'}
    total_records = 5
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['get_subset_info_with_next']),
        ('GET', '/next_record_api', SRR['generic_error']),
    ])
    assert create_and_apply(ontap_rest_info_module, args, fail=True)['msg'] == 'Expected error'


def test_negative_bad_api():
    args = set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass()
    args['use_python_keys'] = True
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['error_invalid_api']),
    ])
    assert create_and_apply(ontap_rest_info_module, args)['ontap_info']['storage_volumes'] == 'Invalid API'


def test_negative_error_no_aggr_recommendation():
    args = set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass()
    args['use_python_keys'] = True
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['error_no_aggr_recommendation']),
    ])
    assert create_and_apply(ontap_rest_info_module, args)['ontap_info']['storage_volumes'] == 'No recommendation can be made for this cluster'


def test_negative_error_not_authorized():
    args = set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass()
    args['use_python_keys'] = True
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['error_user_is_not_authorized']),
    ])
    assert 'user is not authorized to make' in create_and_apply(ontap_rest_info_module, args, fail=True)['msg']


def test_negative_error_no_processing():
    args = set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass()
    args['use_python_keys'] = True
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['error_no_processing']),
    ])
    assert create_and_apply(ontap_rest_info_module, args, fail=True)['msg']['message'] == 'error reported as is'


def test_strip_dacls():
    record = {}
    response = {
        'records': [record]
    }
    assert ontap_rest_info_module.strip_dacls(response) is None
    record['acls'] = []
    assert ontap_rest_info_module.strip_dacls(response) is None
    record['acls'] = ['junk', 'junk', 'DACL - ACEs']
    assert ontap_rest_info_module.strip_dacls(response) == []
    record['acls'] = ['junk', 'junk', 'DACL - ACEs', 'AT-user-0x123']
    assert ontap_rest_info_module.strip_dacls(response) == [{'access_type': 'AT', 'user_or_group': 'user'}]
    record['acls'] = ['junk', 'junk', 'DACL - ACEs', 'AT-user-0x123', 'AT2-group-0xABC']
    assert ontap_rest_info_module.strip_dacls(response) == [{'access_type': 'AT', 'user_or_group': 'user'},
                                                            {'access_type': 'AT2', 'user_or_group': 'group'}]


def test_private_cli_vserver_security_file_directory():
    args = set_args_get_all_records_for_volume_info_to_check_next_api_call_functionality_pass()
    args['gather_subset'] = 'private/cli/vserver/security/file-directory'
    args['use_python_keys'] = True
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'private/cli/vserver/security/file-directory', SRR['get_private_cli_vserver_security_file_directory_info']),
    ])
    assert create_and_apply(ontap_rest_info_module, args)['ontap_info'] == {
        'private_cli_vserver_security_file_directory': [{'access_type': 'AT', 'user_or_group': 'user'}]}


def test_get_ontap_subset_info_all_with_field():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'some/api', SRR['get_subset_info']),
    ])
    my_obj = create_module(ontap_rest_info_module, set_default_args())
    subset_info = {'subset': {'api_call': 'some/api'}}
    assert my_obj.get_ontap_subset_info_all('subset', 'fields', subset_info)['num_records'] == 3


def test_negative_get_ontap_subset_info_all_bad_subset():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
    ])
    my_obj = create_module(ontap_rest_info_module, set_default_args())
    msg = 'Specified subset bad_subset is not found, supported subsets are []'
    assert expect_and_capture_ansible_exception(my_obj.get_ontap_subset_info_all, 'fail', 'bad_subset', None, {})['msg'] == msg


def test_demo_subset():
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'cluster/software', SRR['get_subset_info']),
        ('GET', 'svm/svms', SRR['get_subset_info']),
        ('GET', 'cluster/nodes', SRR['get_subset_info']),
    ])
    assert 'cluster/nodes' in call_main(my_main, set_default_args(), {'gather_subset': 'demo'})['ontap_info']


def test_demo_subset_without_hal_links():
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'cluster/software', SRR['get_subset_info_without_hal_links']),
        ('GET', 'svm/svms', SRR['get_subset_info_without_hal_links']),
        ('GET', 'cluster/nodes', SRR['get_subset_info_without_hal_links']),
    ])
    assert 'cluster/nodes' in call_main(my_main, set_args_run_ontap_gather_facts_disable_hal_links(), {'gather_subset': 'demo'})['ontap_info']


def test_subset_with_default_fields():
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/aggregates', SRR['get_subset_info']),
    ])
    assert 'storage/aggregates' in \
           create_and_apply(ontap_rest_info_module, set_default_args(), {'gather_subset': 'aggr_efficiency_info'})[
               'ontap_info']


def test_negative_error_on_post():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('POST', 'api', SRR['generic_error']),
    ])
    assert create_module(ontap_rest_info_module, set_default_args()).run_post({'api_call': 'api'}) is None


@patch('time.sleep')
def test_negative_error_on_wait_after_post(sleep_mock):
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('POST', 'api', SRR['metrocluster_post']),
        ('GET', 'cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7', SRR['generic_error']),
        ('GET', 'cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7', SRR['generic_error']),  # retries
        ('GET', 'cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7', SRR['generic_error']),
        ('GET', 'cluster/jobs/fde79888-692a-11ea-80c2-005056b39fe7', SRR['generic_error']),
    ])
    my_obj = create_module(ontap_rest_info_module, set_default_args())
    assert expect_and_capture_ansible_exception(my_obj.run_post, 'fail', {'api_call': 'api'})['msg'] == ' - '.join(
        ['Expected error'] * 4)


def test_owning_resource_snapshot():
    args = set_default_args()
    args['gather_subset'] = 'storage/volumes/snapshots'
    args['owning_resource'] = {'volume_name': 'vol1', 'svm_name': 'svm1'}
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['volume_info']),
        ('GET', 'storage/volumes/7882901a-1aef-11ec-a267-005056b30cfa/snapshots', SRR['volume_info'])
    ])
    assert create_and_apply(ontap_rest_info_module, args)['ontap_info']


def test_owning_resource_snapshot_missing_1_resource():
    args = set_default_args()
    args['gather_subset'] = 'storage/volumes/snapshots'
    args['owning_resource'] = {'volume_name': 'vol1'}
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
    ])
    msg = 'Error: volume_name, svm_name are required for storage/volumes/snapshots'
    assert create_and_apply(ontap_rest_info_module, args, fail=True)['msg'] == msg


def test_owning_resource_snapshot_missing_resource():
    args = set_default_args()
    args['gather_subset'] = 'storage/volumes/snapshots'
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
    ])
    msg = 'Error: volume_name, svm_name are required for storage/volumes/snapshots'
    assert create_and_apply(ontap_rest_info_module, args, fail=True)['msg'] == msg


def test_owning_resource_snapshot_volume_not_found():
    args = set_default_args()
    args['gather_subset'] = 'storage/volumes/snapshots'
    args['owning_resource'] = {'volume_name': 'vol1', 'svm_name': 'svm1'}
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/volumes', SRR['generic_error']),
    ])
    msg = 'Could not find volume vol1 on SVM svm1'
    assert create_and_apply(ontap_rest_info_module, args, fail=True)['msg'] == msg


def test_owning_resource_vscan_on_access_policies():
    args = set_default_args()
    args['gather_subset'] = 'protocols/vscan/on-access-policies'
    args['owning_resource'] = {'svm_name': 'svm1'}
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/test_uuid/on-access-policies', SRR['vscan_on_access_policies'])
    ])
    assert create_and_apply(ontap_rest_info_module, args)['ontap_info']


def test_owning_resource_vscan_on_demand_policies():
    args = set_default_args()
    args['gather_subset'] = 'protocols/vscan/on-demand-policies'
    args['owning_resource'] = {'svm_name': 'svm1'}
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/test_uuid/on-demand-policies', SRR['vscan_on_access_policies'])
    ])
    assert create_and_apply(ontap_rest_info_module, args)['ontap_info']


def test_owning_resource_vscan_scanner_pools():
    args = set_default_args()
    args['gather_subset'] = 'protocols/vscan/scanner-pools'
    args['owning_resource'] = {'svm_name': 'svm1'}
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'svm/svms', SRR['svm_uuid']),
        ('GET', 'protocols/vscan/test_uuid/scanner-pools', SRR['vscan_scanner_pools'])
    ])
    assert create_and_apply(ontap_rest_info_module, args)['ontap_info']


def test_owning_resource_export_policies_rules():
    args = set_default_args()
    args['gather_subset'] = 'protocols/nfs/export-policies/rules'
    args['owning_resource'] = {'policy_name': 'policy_name', 'svm_name': 'svm1', 'rule_index': '1'}
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'protocols/nfs/export-policies', SRR['get_uuid_policy_id_export_policy']),
        ('GET', 'protocols/nfs/export-policies/123/rules/1', SRR['get_uuid_policy_id_export_policy'])
    ])
    assert create_and_apply(ontap_rest_info_module, args)['ontap_info']


def test_owning_resource_export_policies_rules_missing_resource():
    args = set_default_args()
    args['gather_subset'] = 'protocols/nfs/export-policies/rules'
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
    ])
    msg = 'Error: policy_name, svm_name, rule_index are required for protocols/nfs/export-policies/rules'
    assert create_and_apply(ontap_rest_info_module, args, fail=True)['msg'] == msg


def test_owning_resource_export_policies_rules_missing_1_resource():
    args = set_default_args()
    args['gather_subset'] = 'protocols/nfs/export-policies/rules'
    args['owning_resource'] = {'policy_name': 'policy_name', 'svm_name': 'svm1'}
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
    ])
    msg = 'Error: policy_name, svm_name, rule_index are required for protocols/nfs/export-policies/rules'
    assert create_and_apply(ontap_rest_info_module, args, fail=True)['msg'] == msg


def test_owning_resource_export_policies_rules_policy_not_found():
    args = set_default_args()
    args['gather_subset'] = 'protocols/nfs/export-policies/rules'
    args['owning_resource'] = {'policy_name': 'policy_name', 'svm_name': 'svm1', 'rule_index': '1'}
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'protocols/nfs/export-policies', SRR['generic_error']),
    ])
    msg = 'Could not find export policy policy_name on SVM svm1'
    assert create_and_apply(ontap_rest_info_module, args, fail=True)['msg'] == msg


def test_lun_info_with_serial():
    args = set_default_args()
    args['gather_subset'] = 'storage/luns'
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/luns', SRR['lun_info']),
    ])
    info = create_and_apply(ontap_rest_info_module, args)
    assert 'ontap_info' in info
    assert 'storage/luns' in info['ontap_info']
    assert 'records' in info['ontap_info']['storage/luns']
    records = info['ontap_info']['storage/luns']['records']
    assert records
    lun_info = records[0]
    print('INFO', lun_info)
    assert lun_info['serial_number'] == 'z6CcD+SK5mPb'
    assert lun_info['serial_hex'] == '7a364363442b534b356d5062'
    assert lun_info['naa_id'] == 'naa.600a0980' + '7a364363442b534b356d5062'


def test_ignore_api_errors():
    args = set_default_args()
    args['gather_subset'] = 'storage/luns'
    args['ignore_api_errors'] = ['something', 'Expected error']
    args['fields'] = ['**']
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
        ('GET', 'storage/luns', SRR['error_record']),
    ])
    info = create_and_apply(ontap_rest_info_module, args)
    assert 'ontap_info' in info
    assert 'storage/luns' in info['ontap_info']
    assert 'error' in info['ontap_info']['storage/luns']
    error = info['ontap_info']['storage/luns']['error']
    assert error
    assert error['code'] == 6
    assert error['message'] == 'Expected error'
    print_warnings()
    assert_warning_was_raised('Using ** can put an extra load on the system and should not be used in production')


def test_private_cli_fields():
    register_responses([
        ('GET', 'cluster', SRR['validate_ontap_version_pass']),
    ])
    args = set_default_args()
    my_obj = create_module(ontap_rest_info_module, args)
    error = 'Internal error, no field for unknown_api'
    assert error in expect_and_capture_ansible_exception(my_obj.private_cli_fields, 'fail', 'unknown_api')['msg']
    assert my_obj.private_cli_fields('private/cli/vserver/security/file-directory') == 'acls'
    assert my_obj.private_cli_fields('support/autosupport/check') == 'node,corrective-action,status,error-detail,check-type,check-category'
    my_obj.parameters['fields'] = ['f1', 'f2']
    assert my_obj.private_cli_fields('private/cli/vserver/security/file-directory') == 'f1,f2'
