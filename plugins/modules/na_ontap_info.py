#!/usr/bin/python

# (c) 2018 Piotr Olczak <piotr.olczak@redhat.com>
# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = '''
module: na_ontap_info
author: Piotr Olczak (@dprts) <polczak@redhat.com>
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
short_description: NetApp information gatherer
description:
    - This module allows you to gather various information about ONTAP configuration
version_added: "2.9"
requirements:
    - netapp_lib
options:
    state:
        type: str
        description:
            - Returns "info"
        default: "info"
        choices: ['info']
    vserver:
        type: str
        description:
            - The Vserver to run on. Must be used if using VSadmin. Not all info's support VSadmin and may fail
        version_added: '19.11.0'
    gather_subset:
        type: list
        description:
            - When supplied, this argument will restrict the information collected
                to a given subset.  Possible values for this argument include
                "aggregate_info",
                "cifs_server_info",
                "cifs_share_info",
                "cifs_vserver_security_info",
                "cluster_identity_info",
                "cluster_image_info",
                "cluster_node_info",
                "cluster_peer_info",
                "clock_info",
                "export_policy_info",
                "export_rule_info",
                "fcp_adapter_info",
                "fcp_alias_info",
                "fcp_service_info",
                "igroup_info",
                "iscsi_service_info",
                "job_schedule_cron_info",
                "kerberos_realm_info",
                "ldap_client",
                "ldap_config",
                "license_info",
                "lun_info",
                "lun_map_info",
                "net_dns_info",
                "net_failover_group_info",
                "net_firewall_info",
                "net_ifgrp_info",
                "net_interface_info",
                "net_interface_service_policy_info",
                "net_ipspaces_info",
                "net_port_info",
                "net_port_broadcast_domain_info",
                "net_routes_info",
                "net_vlan_info",
                "nfs_info",
                "ntfs_dacl_info",
                "ntfs_sd_info",
                "ntp_server_info",
                "nvme_info",
                "nvme_interface_info",
                "nvme_namespace_info",
                "nvme_subsystem_info",
                "ontap_system_version",
                "ontap_version",
                "ontapi_version",
                "qos_adaptive_policy_info",
                "qos_policy_info",
                "role_info",
                "security_key_manager_key_info",
                "security_login_account_info",
                "service_processor_network_info",
                "sis_policy_info",
                "snapmirror_info",
                "snapmirror_policy_info",
                "snapshot_info",
                "snapshot_policy_info",
                "storage_failover_info",
                "storage_bridge_info",
                "volume_info",
                "vscan_info",
                "vscan_status_info",
                "vscan_scanner_pool_info",
                "vscan_connection_status_all_info",
                "vscan_connection_extended_stats_info",
                "vserver_info",
                "vserver_login_banner_info",
                "vserver_motd_info",
                "vserver_nfs_info",
                "vserver_peer_info",
                Can specify a list of values to include a larger subset.  Values can also be used
                with an initial C(M(!)) to specify that a specific subset should
                not be collected.
            - nvme is supported with ONTAP 9.4 onwards.
            - use "help" to get a list of supported information for your system.
        default: "all"
    max_records:
        type: int
        description:
            - Maximum number of records returned in a single ZAPI call. Valid range is [1..2^32-1].
                This parameter controls internal behavior of this module.
        default: 1024
        version_added: '20.2.0'
'''

EXAMPLES = '''
- name: Get NetApp info as Cluster Admin (Password Authentication)
  na_ontap_info:
    state: info
    hostname: "na-vsim"
    username: "admin"
    password: "admins_password"
  register: ontap_info
- debug:
    msg: "{{ ontap_info.ontap_info }}"

- name: Get NetApp version as Vserver admin
  na_ontap_info:
    state: info
    hostname: "na-vsim"
    username: "vsadmin"
    vserver: trident_svm
    password: "vsadmins_password"

- name: Limit Info Gathering to Aggregate Information as Cluster Admin
  na_ontap_info:
    state: info
    hostname: "na-vsim"
    username: "admin"
    password: "admins_password"
    gather_subset: "aggregate_info"
  register: ontap_info

- name: Limit Info Gathering to Volume and Lun Information as Cluster Admin
  na_ontap_info:
    state: info
    hostname: "na-vsim"
    username: "admin"
    password: "admins_password"
    gather_subset:
      - volume_info
      - lun_info
  register: ontap_info

- name: Gather all info except for volume and lun information as Cluster Admin
  na_ontap_info:
    state: info
    hostname: "na-vsim"
    username: "admin"
    password: "admins_password"
    gather_subset:
      - "!volume_info"
      - "!lun_info"
  register: ontap_info
'''

RETURN = '''
ontap_info:
    description: Returns various information about NetApp cluster configuration
    returned: always
    type: dict
    sample: '{
        "ontap_info": {
            "aggregate_info": {...},
            "cluster_identity_info": {...},
            "cluster_image_info": {...},
            "cluster_node_info": {...},
            "igroup_info": {...},
            "iscsi_service_info": {...},
            "license_info": {...},
            "lun_info": {...},
            "net_dns_info": {...},
            "net_ifgrp_info": {...},
            "net_interface_info": {...},
            "net_interface_service_policy_info": {...},
            "net_port_info": {...},
            "ontap_system_version": {...},
            "ontap_version": {...},
            "ontapi_version": {...},
            "qos_policy_info": {...},
            "qos_adaptive_policy_info": {...}
            "security_key_manager_key_info": {...},
            "security_login_account_info": {...},
            "snapmirror_info": {...}
            "storage_bridge_info": {...}
            "storage_failover_info": {...},
            "volume_info": {...},
            "vserver_login_banner_info": {...},
            "vserver_motd_info": {...},
            "vserver_info": {...},
            "vserver_nfs_info": {...},
            "vscan_status_info": {...},
            "vscan_scanner_pool_info": {...},
            "vscan_connection_status_all_info": {...},
            "vscan_connection_extended_stats_info": {...}
    }'
'''

import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

import copy

try:
    import xmltodict
    HAS_XMLTODICT = True
except ImportError:
    HAS_XMLTODICT = False

try:
    import json
    HAS_JSON = True
except ImportError:
    HAS_JSON = False

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppONTAPGatherInfo(object):
    '''Class with gather info methods'''

    def __init__(self, module, max_records):
        self.module = module
        self.max_records = str(max_records)
        self.netapp_info = dict()

        # thanks to coreywan (https://github.com/ansible/ansible/pull/47016)
        # for starting this
        # min_version identifies the ontapi version which supports this ZAPI
        # use 0 if it is supported since 9.1
        self.info_subsets = {
            'net_dns_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'net-dns-get-iter',
                    'attribute': 'net-dns-info',
                    'field': 'vserver-name',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'net_interface_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'net-interface-get-iter',
                    'attribute': 'net-interface-info',
                    'field': 'interface-name',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'net_interface_service_policy_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'net-interface-service-policy-get-iter',
                    'attribute': 'net-interface-service-policy-info',
                    'field': ('vserver', 'policy'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '150',
            },
            'net_port_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'net-port-get-iter',
                    'attribute': 'net-port-info',
                    'field': ('node', 'port'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'cluster_identity_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'cluster-identity-get',
                    'attributes_list_tag': 'attributes',
                    'attribute': 'cluster-identity-info',
                    'field': 'cluster-name',
                },
                'min_version': '0',
            },
            'cluster_image_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'cluster-image-get-iter',
                    'attribute': 'cluster-image-info',
                    'field': 'current-version',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'cluster_node_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'cluster-node-get-iter',
                    'attribute': 'cluster-node-info',
                    'field': 'node-name',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'security_login_account_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'security-login-get-iter',
                    'attribute': 'security-login-account-info',
                    'field': ('vserver', 'user-name', 'application', 'authentication-method'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'aggregate_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'aggr-get-iter',
                    'attribute': 'aggr-attributes',
                    'field': 'aggregate-name',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'volume_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'volume-get-iter',
                    'attribute': 'volume-attributes',
                    'field': ('name', 'owning-vserver-name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'license_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'license-v2-list-info',
                    'attributes_list_tag': None,
                    'attribute': 'licenses',
                },
                'min_version': '0',
            },
            'lun_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'lun-get-iter',
                    'attribute': 'lun-info',
                    'field': ('vserver', 'path'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'storage_failover_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'cf-get-iter',
                    'attribute': 'storage-failover-info',
                    'field': 'node',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'vserver_motd_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'vserver-motd-get-iter',
                    'attribute': 'vserver-motd-info',
                    'field': 'vserver',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'vserver_login_banner_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'vserver-login-banner-get-iter',
                    'attribute': 'vserver-login-banner-info',
                    'field': 'vserver',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'security_key_manager_key_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'security-key-manager-key-get-iter',
                    'attribute': 'security-key-manager-key-info',
                    'field': ('node', 'key-id'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'vserver_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'vserver-get-iter',
                    'attribute': 'vserver-info',
                    'field': 'vserver-name',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'vserver_nfs_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'nfs-service-get-iter',
                    'attribute': 'nfs-info',
                    'field': 'vserver',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'net_ifgrp_info': {
                'method': self.get_ifgrp_info,
                'kwargs': {},
                'min_version': '0',
            },
            'ontap_system_version': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'system-get-version',
                    'attributes_list_tag': None,
                },
                'min_version': '0',
            },
            'ontap_version': {
                'method': self.ontapi,
                'kwargs': {},
                'min_version': '0',
            },
            'ontapi_version': {
                'method': self.ontapi,
                'kwargs': {},
                'min_version': '0',
            },
            'clock_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'clock-get-clock',
                    'attributes_list_tag': None,
                },
                'min_version': '0'
            },
            'system_node_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'system-node-get-iter',
                    'attribute': 'node-details-info',
                    'field': 'node',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'igroup_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'igroup-get-iter',
                    'attribute': 'initiator-group-info',
                    'field': ('vserver', 'initiator-group-name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'iscsi_service_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'iscsi-service-get-iter',
                    'attribute': 'iscsi-service-info',
                    'field': 'vserver',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'qos_policy_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'qos-policy-group-get-iter',
                    'attribute': 'qos-policy-group-info',
                    'field': 'policy-group',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'vscan_status_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'vscan-status-get-iter',
                    'attribute': 'vscan-status-info',
                    'field': 'vserver',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'vscan_scanner_pool_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'vscan-scanner-pool-get-iter',
                    'attribute': 'vscan-scanner-pool-info',
                    'field': 'vserver',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'vscan_connection_status_all_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'vscan-connection-status-all-get-iter',
                    'attribute': 'vscan-connection-status-all-info',
                    'field': 'vserver',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'vscan_connection_extended_stats_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'vscan-connection-extended-stats-get-iter',
                    'attribute': 'vscan-connection-extended-stats-info',
                    'field': 'vserver',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'snapshot_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'snapshot-get-iter',
                    'attribute': 'snapshot-info',
                    'field': ('vserver', 'volume', 'name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'storage_bridge_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'storage-bridge-get-iter',
                    'attribute': 'storage-bridge-info',
                    'field': 'name',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            # supported in ONTAP 9.3 and onwards
            'qos_adaptive_policy_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'qos-adaptive-policy-group-get-iter',
                    'attribute': 'qos-adaptive-policy-group-info',
                    'field': 'policy-group',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '130',
            },
            # supported in ONTAP 9.4 and onwards
            'nvme_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'nvme-get-iter',
                    'attribute': 'nvme-target-service-info',
                    'field': 'vserver',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '140',
            },
            'nvme_interface_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'nvme-interface-get-iter',
                    'attribute': 'nvme-interface-info',
                    'field': 'vserver',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '140',
            },
            'nvme_subsystem_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'nvme-subsystem-get-iter',
                    'attribute': 'nvme-subsystem-info',
                    'field': 'subsystem',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '140',
            },
            'nvme_namespace_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'nvme-namespace-get-iter',
                    'attribute': 'nvme-namespace-info',
                    'field': 'path',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '140',
            },
            'snapmirror_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'snapmirror-get-iter',
                    'attribute': 'snapmirror-info',
                    'field': 'destination-location',
                    'query': {'max-records': self.max_records},
                },
                'min_version': '140',
            },
            'cifs_server_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'cifs-server-get-iter',
                    'attribute': 'cifs-server-config',
                    # preferred key is <vserver>:<domain>:<cifs-server>
                    # alternate key is <vserver>:<domain-workgroup>:<cifs-server>
                    'field': ('vserver', ('domain', 'domain-workgroup'), 'cifs-server'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'cifs_share_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'cifs-share-get-iter',
                    'attribute': 'cifs-share',
                    'field': ('share-name', 'path', 'cifs-server'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'cifs_vserver_security_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'cifs-security-get-iter',
                    'attribute': 'cifs-security',
                    'field': ('vserver'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'cluster_peer_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'cluster-peer-get-iter',
                    'attribute': 'cluster-peer-info',
                    'field': ('cluster-name', 'remote-cluster-name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'export_policy_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'export-policy-get-iter',
                    'attribute': 'export-policy-info',
                    'field': ('vserver', 'policy-name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'export_rule_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'export-rule-get-iter',
                    'attribute': 'export-rule-info',
                    'field': ('vserver-name', 'policy-name', 'rule-index'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'fcp_adapter_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'ucm-adapter-get-iter',
                    'attribute': 'uc-adapter-info',
                    'field': ('adapter-name', 'node-name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'fcp_alias_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'fcp-wwpnalias-get-iter',
                    'attribute': 'aliases-info',
                    'field': ('aliases-alias', 'vserver'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'fcp_service_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'fcp-service-get-iter',
                    'attribute': 'fcp-service-info',
                    'field': ('vserver'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'job_schedule_cron_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'job-schedule-cron-get-iter',
                    'attribute': 'job-schedule-cron-info',
                    'field': ('job-schedule-name', 'job-schedule-cluster'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'kerberos_realm_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'kerberos-realm-get-iter',
                    'attribute': 'kerberos-realm',
                    'field': ('vserver-name', 'realm'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'ldap_client': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'ldap-client-get-iter',
                    'attribute': 'ldap-client',
                    'field': ('vserver'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'ldap_config': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'ldap-config-get-iter',
                    'attribute': 'ldap-config',
                    'field': ('vserver'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'lun_map_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'lun-map-get-iter',
                    'attribute': 'lun-map-info',
                    'field': ('initiator-group', 'lun-id', 'node', 'path', 'vserver'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'net_failover_group_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'net-failover-group-get-iter',
                    'attribute': 'net-failover-group-info',
                    'field': ('vserver', 'failover-group'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'net_firewall_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'net-firewall-policy-get-iter',
                    'attribute': 'net-firewall-policy-info',
                    'field': ('policy', 'vserver', 'service'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'net_ipspaces_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'net-ipspaces-get-iter',
                    'attribute': 'net-ipspaces-info',
                    'field': ('ipspace'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'net_port_broadcast_domain_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'net-port-broadcast-domain-get-iter',
                    'attribute': 'net-port-broadcast-domain-info',
                    'field': ('broadcast-domain', 'ipspace'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'net_routes_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'net-routes-get-iter',
                    'attribute': 'net-vs-routes-info',
                    'field': ('vserver', 'destination', 'gateway'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'net_vlan_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'net-vlan-get-iter',
                    'attribute': 'vlan-info',
                    'field': ('interface-name', 'node'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'nfs_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'nfs-service-get-iter',
                    'attribute': 'nfs-info',
                    'field': ('vserver'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'ntfs_dacl_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'file-directory-security-ntfs-dacl-get-iter',
                    'attribute': 'file-directory-security-ntfs-dacl',
                    'field': ('vserver', 'ntfs-sd', 'account', 'access-type'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'ntfs_sd_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'file-directory-security-ntfs-get-iter',
                    'attribute': 'file-directory-security-ntfs',
                    'field': ('vserver', 'ntfs-sd'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'ntp_server_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'ntp-server-get-iter',
                    'attribute': 'ntp-server-info',
                    'field': ('server-name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'role_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'security-login-role-get-iter',
                    'attribute': 'security-login-role-info',
                    'field': ('vserver', 'role-name', 'access-level', 'command-directory-name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'service_processor_network_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'service-processor-network-get-iter',
                    'attribute': 'service-processor-network-info',
                    # don't use fields, as we cannot build a key with optional fields
                    # without a key, we'll get a list of dictionaries
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'sis_policy_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'sis-policy-get-iter',
                    'attribute': 'sis-policy-info',
                    'field': ('vserver', 'policy-name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'snapmirror_policy_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'snapmirror-policy-get-iter',
                    'attribute': 'snapmirror-policy-info',
                    'field': ('vserver-name', 'policy-name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'snapshot_policy_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'snapshot-policy-get-iter',
                    'attribute': 'snapshot-policy-info',
                    'field': ('vserver-name', 'policy'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'vscan_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'vscan-status-get-iter',
                    'attribute': 'vscan-status-info',
                    'field': ('vserver'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
            'vserver_peer_info': {
                'method': self.get_generic_get_iter,
                'kwargs': {
                    'call': 'vserver-peer-get-iter',
                    'attribute': 'vserver-peer-info',
                    'field': ('vserver', 'remote-vserver-name'),
                    'query': {'max-records': self.max_records},
                },
                'min_version': '0',
            },
        }

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def ontapi(self):
        '''Method to get ontapi version'''

        api = 'system-get-ontapi-version'
        api_call = netapp_utils.zapi.NaElement(api)
        try:
            results = self.server.invoke_successfully(api_call, enable_tunneling=False)
            ontapi_version = results.get_child_content('minor-version')
            return ontapi_version if ontapi_version is not None else '0'
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error calling API %s: %s" %
                                  (api, to_native(error)), exception=traceback.format_exc())

    def call_api(self, call, attributes_list_tag='attributes-list', query=None):
        '''Main method to run an API call'''

        api_call = netapp_utils.zapi.NaElement(call)
        initial_result = None

        if query:
            for key, val in query.items():
                # Can val be nested?
                api_call.add_new_child(key, val)
        try:
            initial_result = self.server.invoke_successfully(api_call, enable_tunneling=False)
            next_tag = initial_result.get_child_by_name('next-tag')
            result = copy.copy(initial_result)

            while next_tag:
                next_tag_call = netapp_utils.zapi.NaElement(call)
                if query:
                    for key, val in query.items():
                        next_tag_call.add_new_child(key, val)

                next_tag_call.add_new_child("tag", next_tag.get_content(), True)
                next_result = self.server.invoke_successfully(next_tag_call, enable_tunneling=False)

                next_tag = next_result.get_child_by_name('next-tag')
                if attributes_list_tag is None:
                    self.module.fail_json(msg="Error calling API %s: %s" %
                                          (api_call.to_string(), "'next-tag' is not expected for this API"))

                result_attr = result.get_child_by_name(attributes_list_tag)
                new_records = next_result.get_child_by_name(attributes_list_tag)
                if new_records:
                    for record in new_records.get_children():
                        result_attr.add_child_elem(record)

            return result

        except netapp_utils.zapi.NaApiError as error:
            if call in ['security-key-manager-key-get-iter']:
                return result
            else:
                self.module.fail_json(msg="Error calling API %s: %s"
                                      % (call, to_native(error)), exception=traceback.format_exc())

    def get_ifgrp_info(self):
        '''Method to get network port ifgroups info'''

        try:
            net_port_info = self.netapp_info['net_port_info']
        except KeyError:
            net_port_info_calls = self.info_subsets['net_port_info']
            net_port_info = net_port_info_calls['method'](**net_port_info_calls['kwargs'])
        interfaces = net_port_info.keys()

        ifgrps = []
        for ifn in interfaces:
            if net_port_info[ifn]['port_type'] == 'if_group':
                ifgrps.append(ifn)

        net_ifgrp_info = dict()
        for ifgrp in ifgrps:
            query = dict()
            query['node'], query['ifgrp-name'] = ifgrp.split(':')

            tmp = self.get_generic_get_iter('net-port-ifgrp-get', field=('node', 'ifgrp-name'),
                                            attribute='net-ifgrp-info', query=query,
                                            attributes_list_tag='attributes')
            net_ifgrp_info = net_ifgrp_info.copy()
            net_ifgrp_info.update(tmp)
        return net_ifgrp_info

    def get_generic_get_iter(self, call, attribute=None, field=None, query=None, attributes_list_tag='attributes-list'):
        '''Method to run a generic get-iter call'''

        generic_call = self.call_api(call, attributes_list_tag, query)

        if generic_call is None:
            return None

        if attributes_list_tag is None:
            attributes_list = generic_call
        else:
            attributes_list = generic_call.get_child_by_name(attributes_list_tag)

        if attributes_list is None:
            return None

        if field is None:
            out = []
        else:
            out = {}

        for child in attributes_list.get_children():
            dic = xmltodict.parse(child.to_string(), xml_attribs=False)

            if attribute is not None:
                dic = dic[attribute]

            if isinstance(field, str):
                unique_key = _finditem(dic, field)
                out = out.copy()
                out.update({unique_key: convert_keys(json.loads(json.dumps(dic)))})
            elif isinstance(field, tuple):
                unique_key = ':'.join([_finditem(dic, el) for el in field])
                out = out.copy()
                out.update({unique_key: convert_keys(json.loads(json.dumps(dic)))})
            else:
                out.append(convert_keys(json.loads(json.dumps(dic))))

        if attributes_list_tag is None and field is None:
            if len(out) == 1:
                # flatten the list as only 1 element is expected
                out = out[0]
            elif len(out) > 1:
                # aggregate a list of dictionaries into a single dict
                # make sure we only have dicts and no key duplication
                dic = dict()
                key_count = 0
                for item in out:
                    if not isinstance(item, dict):
                        # abort if we don't see a dict
                        key_count = -1
                        break
                    dic.update(item)
                    key_count += len(item)
                if key_count == len(dic):
                    # no duplicates!
                    out = dic

        return out

    def get_all(self, gather_subset):
        '''Method to get all subsets'''

        if self.module.params['vserver']:
            netapp_utils.ems_log_event("na_ontap_info", self.server)
        else:
            results = netapp_utils.get_cserver(self.server)
            cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
            netapp_utils.ems_log_event("na_ontap_info", cserver)

        self.netapp_info['ontapi_version'] = self.ontapi()
        self.netapp_info['ontap_version'] = self.netapp_info['ontapi_version']

        run_subset = self.get_subset(gather_subset, self.netapp_info['ontapi_version'])
        if 'ontap_version' in gather_subset:
            self.netapp_info['deprecation_warning'] = 'ontap_version is deprecated, please use ontapi_version'
        if 'help' in gather_subset:
            self.netapp_info['help'] = sorted(run_subset)
        else:
            for subset in run_subset:
                call = self.info_subsets[subset]
                self.netapp_info[subset] = call['method'](**call['kwargs'])

        return self.netapp_info

    def get_subset(self, gather_subset, version):
        '''Method to get a single subset'''

        runable_subsets = set()
        exclude_subsets = set()
        usable_subsets = [key for key in self.info_subsets.keys() if version >= self.info_subsets[key]['min_version']]
        if 'help' in gather_subset:
            return usable_subsets
        for subset in gather_subset:
            if subset == 'all':
                runable_subsets.update(usable_subsets)
                return runable_subsets
            if subset.startswith('!'):
                subset = subset[1:]
                if subset == 'all':
                    return set()
                exclude = True
            else:
                exclude = False

            if subset not in usable_subsets:
                if subset not in self.info_subsets.keys():
                    self.module.fail_json(msg='Bad subset: %s' % subset)
                self.module.fail_json(msg='Remote system at version %s does not support %s' %
                                      (version, subset))

            if exclude:
                exclude_subsets.add(subset)
            else:
                runable_subsets.add(subset)

        if not runable_subsets:
            runable_subsets.update(usable_subsets)

        runable_subsets.difference_update(exclude_subsets)

        return runable_subsets


# https://stackoverflow.com/questions/14962485/finding-a-key-recursively-in-a-dictionary
def __finditem(obj, key):

    if key in obj:
        return obj[key]
    for dummy, val in obj.items():
        if isinstance(val, dict):
            item = __finditem(val, key)
            if item is not None:
                return item
    return None


def _finditem(obj, keys):
    ''' if keys is a string, use it as a key
        if keys is a tuple, stop on the first valid key
        if no valid key is found, raise a KeyError '''

    value = None
    if isinstance(keys, str):
        value = __finditem(obj, keys)
    elif isinstance(keys, tuple):
        for key in keys:
            value = __finditem(obj, key)
            if value is not None:
                break
    if value is not None:
        return value
    raise KeyError(str(keys))


def convert_keys(d_param):
    '''Method to convert hyphen to underscore'''

    out = {}
    if isinstance(d_param, dict):
        for key, val in d_param.items():
            val = convert_keys(val)
            out[key.replace('-', '_')] = val
    else:
        return d_param
    return out


def main():
    '''Execute action'''

    argument_spec = netapp_utils.na_ontap_host_argument_spec()
    argument_spec.update(dict(
        state=dict(type='str', default='info', choices=['info']),
        gather_subset=dict(default=['all'], type='list'),
        vserver=dict(type='str', default=None, required=False),
        max_records=dict(type='int', default=1024, required=False)
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    if not HAS_XMLTODICT:
        module.fail_json(msg="xmltodict missing")

    if not HAS_JSON:
        module.fail_json(msg="json missing")

    state = module.params['state']
    gather_subset = module.params['gather_subset']
    if gather_subset is None:
        gather_subset = ['all']
    max_records = module.params['max_records']
    gf_obj = NetAppONTAPGatherInfo(module, max_records)
    gf_all = gf_obj.get_all(gather_subset)
    result = {'state': state, 'changed': False}
    module.exit_json(ontap_info=gf_all, **result)


if __name__ == '__main__':
    main()
