=============================================================

 netapp.ontap

 NetApp ONTAP Collection

 Copyright (c) 2019 NetApp, Inc. All rights reserved.
 Specifications subject to change without notice.

=============================================================
# Installation
```bash
ansible-galaxy collection install netapp.ontap
```
To use Collection add the following to the top of your playbook, with out this you will be using Ansible 2.9 version of the module
```
collections:
  - netapp.ontap
```
# Need help
Join our Slack Channel at [Netapp.io](http://netapp.io/slack)

# Release Notes

## 20.2.0

### New Modules
- na_ontap_volume_snaplock: modify volume snaplock retention.

### New Options
- na_ontap_info: New info's added `snapshot_info`
- na_ontap_info: `max_records` option to set maximum number of records to return per subset.
- na_ontap_snapmirror: `relationship_state` option for breaking the snapmirror relationship.
- na_ontap_snapmirror: `update_snapmirror` option for updating the snapmirror relationship.

### Bug Fixes
- na_ontap_nvme_subsystem: fixed bug when creating subsystem, vserver was not filtered.
- na_ontap_svm: if snapshot policy is changed, modify fails with "Extra input: snapshot_policy"
- na_ontap_svm: if language: C.UTF-8 is specified, the module is not idempotent
- na_ontap_volume_clone: fixed 'Extra input: parent-vserver' error when running as cluster admin.

### Role Changes
- na_ontap_nas_create role: fix typo in README file, add CIFS example.

## 20.1.0

### New Modules
- na_ontap_login_messages: create/modify/delete security login messages including banner and mtod.

### New Options
- na_ontap_aggregate: add `snaplock_type`.
- na_ontap_info: New info's added `cifs_server_info`, `cifs_share_info`, `cifs_vserver_security_info`, `cluster_peer_info`, `clock_info`, `export_policy_info`, `export_rule_info`, `fcp_adapter_info`, `fcp_alias_info`, `fcp_service_info`, `job_schedule_cron_info`, `kerberos_realm_info`, `ldap_client`, `ldap_config`, `net_failover_group_info`, `net_firewall_info`, `net_ipspaces_info`, `net_port_broadcast_domain_info`, `net_routes_info`, `net_vlan_info`, `nfs_info`, `ntfs_dacl_info`, `ntfs_sd_info`, `ntp_server_info`, `role_info`, `service_processor_network_info`, `sis_policy_info`, `snapmirror_policy_info`, `snapshot_policy_info`, `vscan_info`, `vserver_peer_info`
- na_ontap_igroup_initiator: `force_remove` to forcibly remove initiators from an igroup that is currently mapped to a LUN.
- na_ontap_interface: `failover_group` to specify the failover group for the LIF. `is_ipv4_link_local` to specify the LIF's are to acquire a ipv4 link local address.
- na_ontap_rest_cli: add OPTIONS as a supported verb and return list of allowed verbs.
- na_ontap_volume: add `group_id` and `user_id`.

### Bug Fixes
- na_ontap_aggregate: Fixed traceback when running as vsadmin and cleanly error out.
- na_ontap_command: stdout_lines_filter contains data only if include/exlude_lines parameter is used. (zeten30)
- na_ontap_command: stripped_line len is checked only once, filters are inside if block. (zeten30)
- na_ontap_interface: allow module to run on node before joining the cluster.
- na_ontap_net_ifgrp: Fixed error for na_ontap_net_ifgrp if no port is given.
- na_ontap_snapmirror: Fixed traceback when running as vsadmin.  Do not attempt to break a relationship that is 'Uninitialized'.
- na_ontap_snapshot_policy: Fixed KeyError: 'prefix' bug when prefix parameter isn't supplied.
- na_ontap_volume: Fixed error reporting if efficiency policy cannot be read.  Do not attempt to read efficiency policy if not needed.
- na_ontap_volume: Fixed error when modifying volume efficiency policy.
- na_ontap_volume_clone: Fixed KeyError exception on 'volume'

### Added REST support to existing modules
- na_ontap_dns: added REST support for dns creation and modification on cluster vserver.

### Role Changes

## 19.11.0

### New Modules
- na_ontap_quota_policy: create/rename/delete quota policy.

### New Options
- na_ontap_cluster: added single node cluster option, also now supports for modify cluster contact and location option.
- na_ontap_info: Now allow you use to VSadmin to get info (Must user `vserver` option).
- na_ontap_info: Added `vscan_status_info`, `vscan_scanner_pool_info`, `vscan_connection_status_all_info`, `vscan_connection_extended_stats_info`
- na_ontap_efficiency_policy: `changelog_threshold_percent` to set the percentage at which the changelog will be processed for a threshold type of policy, tested once each hour.

### Bug Fixes
- na_ontap_cluster: autosupport log pushed after cluster create is performed, removed license add or remove option.
- na_ontap_dns: report error if modify or delete operations are attempted on cserver when using REST.  Make create operation idempotent for cserver when using REST.  Support for modify/delete on cserver when using REST will be added later.
- na_ontap_firewall_policy: portmap added as a valid service
- na_ontap_net_routes: REST does not support the 'metric' attribute
- na_ontap_snapmirror: added initialize boolean option which specifies whether to initialize SnapMirror relation.
- na_ontap_volume: fixed error when deleting flexGroup volume with ONTAP 9.7.
- na_ontap_volume: tiering option requires 9.4 or later (error on volume-comp-aggr-attributes)
- na_ontap_vscan_scanner_pool: fix module only gets one scanner pool.

### Added REST support to existing modules

### Role Changes

## 19.10.0
Changes in 19.10.0 and September collection releases compared to Ansible 2.9

### New Modules
- na_ontap_name_service_switch: create/modify/delete name service switch configuration.
- na_ontap_iscsi_security: create/modify/delete iscsi security.

### New Options
- na_ontap_command: `vserver`: to allow command to run as either cluster admin or vserver admin.  To run as vserver admin you must use the vserver option.
- na_ontap_motd: rename `message` to `motd_message` to avoid conflict with Ansible internal variable name.
- na_ontap_nvme_namespace: `size_unit` to specify size in different units.
- na_ontap_snapshot_policy: `prefix`: option to use for creating snapshot policy.

### Bug Fixes
- na_ontap_ndmp: minor documentation changes for restore_vm_cache_size and data_port_range.
- na_ontap_qtree: REST API takes "unix_permissions" as parameter instead of "mode".
- na_ontap_qtree: unix permission is not available when security style is ntfs
- na_ontap_user: minor documentation update for application parameter.
- na_ontap_volume: `efficiency_policy` was ignored
- na_ontap_volume: enforce that space_slo and space_guarantee are mutually exclusive
- na_ontap_svm: "allowed_protocols" added to param in proper way in case of using REST API
- na_ontap_firewall_policy: documentation changed for supported service parameter.
- na_ontap_net_subnet: fix ip_ranges option fails on existing subnet.
- na_ontap_snapshot_policy: fix vsadmin approach for managing snapshot policy.
- na_ontap_nvme_subsystem: fix fetching unique nvme subsytem based on vserver filter.
- na ontap_net_routes: change metric type from string to int.
- na_ontap_cifs_server: minor documentation changes correction of create example with "name" parameter and adding type to parameters.
- na_ontap_vserver_cifs_security: fix int and boolean options when modifying vserver cifs security.
- na_ontap_net_subnet: fix rename idempotency issue and updated rename check.

### Added REST support to existing modules
By default, the module will use REST if the target system supports it, and the options are supported.  Otherwise, it will switch back to ZAPI.  This behavior can be controlled with the `use_rest` option:
1. Always: to force REST.  The module fails and reports an error if REST cannot be used.
1. Never: to force ZAPI.  This could be useful if you find some incompatibility with REST, or want to confirm the behavior is identical between REST and ZAPI.
1. Auto: the default, as described above.

- na_ontap_ipspace
- na_ontap_export_policy
- na_ontap_ndmp
-- Note: only `enable` and `authtype` are supported with REST
- na_ontap_net_routes
- na_ontap_qtree
-- Note: `oplocks` is not supported with REST, defaults to enable.
- na_ontap_svm
-- Note: `root_volume`, `root_volume_aggregate`, `root_volume_security_style` are not supported with REST.
- na_ontap_job_schedule

### Role Changes
- na_ontap_cluster_config updated to all cleaner playbook
- na_ontap_vserver_create updated to all cleaner playbook
- na_ontap_nas_create updated to all cleaner playbook
- na_ontap_san_create updated to all cleaner playbook

