[![Documentation](https://img.shields.io/badge/docs-brightgreen.svg)](https://docs.ansible.com/ansible/devel/collections/netapp/ontap/index.html)
![example workflow](https://github.com/ansible-collections/netapp.ontap/actions/workflows/main.yml/badge.svg)
[![codecov](https://codecov.io/gh/ansible-collections/netapp.ontap/branch/main/graph/badge.svg?token=weBYkksxSi)](https://codecov.io/gh/ansible-collections/netapp.ontap)
[![Discord](https://img.shields.io/discord/855068651522490400)](https://discord.gg/NetApp)

=============================================================

 netapp.ontap

 NetApp ONTAP Collection

 Copyright (c) 2022 NetApp, Inc. All rights reserved.
 Specifications subject to change without notice.

=============================================================

# Installation
```bash
ansible-galaxy collection install netapp.ontap
```
To use this collection, add the following to the top of your playbook, without this you will be using Ansible 2.9 version of the module
```
collections:
  - netapp.ontap
```
# Requirements
- ansible version >= 7.0
- requests >= 2.20
- netapp-lib version >= 2018.11.13

# Module documentation
https://docs.ansible.com/ansible/devel/collections/netapp/ontap/

# Need help
Join our [Discord](https://discord.gg/NetApp) and look for our #ansible channel.

# Deprecation warning
The ONTAP 9.12.1 release will be the last ONTAP version to support ONTAPI (ZAPI). Future versions of ONTAP will only support REST. 
This change will effect the modules listed below.

### Replaced Modules
These are modules user will need to migrate from their playbook to use the REST version of the module. Do note because REST
return values differently than ZAPI you will need to update your playbooks to work with the new module.
  - na_ontap_broadcast_domain_ports -> na_ontap_ports
  - na_ontap_command -> na_ontap_rest_cli
  - na_ontap_firewall_policy -> na_ontap_service_policy
  - na_ontap_info -> na_ontap_rest_info
  - na_ontap_ldap -> na_ontap_ldap_client
  - na_ontap_motd -> na_ontap_login_messages
  - na_ontap_ntfs_dacl -> na_ontap_file_security_permissions
  - na_ontap_ntfs_sd -> na_ontap_file_security_permissions
  - na_ontap_qos_adaptive_policy_group -> na_ontap_qos_policy_group
  - na_ontap_volume_snaplock -> na_ontap_volume
  - na_ontap_vserver_cifs_security -> na_ontap_cifs_server
  - na_ontap_zapit -> na_ontap_restit

### Deprecated Modules
The following modules do not have REST equivalent APIs. They will stop working on any ONTAP release after CY22-Q4 release.
  - na_ontap_file_directory_policy
  - na_ontap_svm_options
  - na_ontap_quota_policy

# Release Notes

## 22.13.0

### Minor Changes
  - na_ontap_svm - added `allowed` option for `s3` service, requires ONTAP 9.7 or later.
  - na_ontap_rest_info - removed example which has option `gather_subset` set to `all` from documentation.
  - na_ontap_cifs_server - added new option `comment` for cifs server, requires ONTAP 9.6 or later.
  - all modules supporting only REST - change in documentation for `use_rest`, updated `extends_documentation_fragment`.
  - na_ontap_s3_services - new option `is_http_enabled`, `is_https_enabled`, `port` and `secure_port` added in REST, requires ONTAP 9.8 or later.
  - na_ontap_flexcache - new option to enable `writeback` added in REST, requires ONTAP 9.12 or later.
  - na_ontap_s3_users - new option `regenerate_keys` and `delete_keys` added in REST, `delete_keys` requires ONTAP 9.14 or later.
  - na_ontap_active_directory - return error message when attempting to modify `account_name`.
  - na_ontap_s3_buckets - new option `versioning_state` added, requires ONTAP 9.11.1 or later.
  - na_ontap_volume - new option `granular_data` added in REST, requires ONTAP 9.12 or later.
  - na_ontap_volume - new option `nas_application_template.cifs_share_name` added in REST, requires ONTAP 9.11 or later.
  - na_ontap_volume - new option `nas_application_template.snaplock.*` added in REST, requires ONTAP 9.12 or later.
  - na_ontap_volume - new option `nas_application_template.snapshot_locking_enabled` added in REST, requires ONTAP 9.13.1 or later.

### Bug Fixes
  - na_ontap_snapshot_policy - fix issue with `retention_period` in REST.
  - all modules supporting REST - avoid duplicate calls to api/cluster to get ONTAP version.
  - na_ontap_rest_info - rectified subset name to `cluster/firmware/history`.
  - na_ontap_broadcast_domain - fix issue with port modification in REST.
  - na_ontap_flexcache - fix typo error in the query 'origins.cluster.name' in REST.

### New Modules
  - na_ontap_bgp_config - REST only support for managing BGP configuration for a node, requires ONTAP 9.6 or later.
  - na_ontap_cifs_privileges - REST only support for managing privileges of the local or Active Directory user or group, requires ONTAP 9.10.1 or later.

## 22.12.0

### Minor Changes
  - na_ontap_bgp_peer_group - added new option `use_peer_as_next_hop`, requires ONTAP 9.9 or later.
  - na_ontap_volume - new option `snapshot_locking` added in REST, requires ONTAP 9.12 or later.
  - na_ontap_volume - new option `activity_tracking` added in REST, requires ONTAP 9.10 or later.
  - na_ontap_snapshot_policy - new option `retention_period` added in REST, requires ONTAP 9.12 or later.
  - na_ontap_security_key_manager - added warning message in REST when passphrase is not changed.
  - Requires Ansible 2.15 or higher.
  - na_ontap_cifs - added REST support for option `vscan_fileop_profile`, requires ONTAP 9.15.1 or later.
  - all modules supporting ZAPI & REST - throw authentication error instead of falling back to ZAPI when username/password is incorrect.
  - na_ontap_rest_cli - return command output for GET and OPTIONS verbs during check mode.

### Bug Fixes
  - na_ontap_export_policy_rule - fix issue with idempotency in REST.
  - na_ontap_volume_efficiency - fix issue with modifying volume efficiency in REST.
  - na_ontap_volume - added error message while trying to modify efficiency configuration for a volume in REST, when efficiency is disabled.
  - na_ontap_quotas - fix error with `quota_target` while trying to set default user quota rule in REST.
  - na_ontap_rest_info - fixed issue with capturing error.
  - na_ontap_flexcache - add warning for flexcache relationship deletion in ZAPI.
  - na_ontap_user_role - fix issue with setting multiple permissions with REST.
  - na_ontap_qtree - add warning for job still running for deletion operation in REST, when wait_for_completion is not set.
  - na_ontap_snapshot_policy - fix issue with idempotency when `snapmirror_label` is set to empty in REST.
  - na_ontap_file_security_permissions - set `apply_to` as optional and default value as true.

## 22.11.0

### Minor Changes
  - na_ontap_vserver_audit - new options `schedule.*` added under `log.rotation`, requires ONTAP 9.6 or later.
  - na_ontap_cifs - new option `offline_files` added in REST, requires ONTAP 9.10 or later.
  - na_ontap_net_ifgrp - updated documentation for parameter `name`.
  - na_ontap_security_config - added warning for missing `supported_cipher_suites` to maintain idempotency in REST.

### Bug Fixes
  - na_ontap_fpolicy_policy - fixed issue with idempotency in REST.
  - na_ontap_dns - fix issue with modifying DNS servers in REST.
  - na_ontap_quotas - fixed issue with idempotency in REST.

## 22.10.0

### Minor Changes
  - na_ontap_rest_info - added warning message if given subset doesn't support option `owning_resource`.
  - na_ontap_export_policy_rule - added `actions` and `modify` in module output.
  - na_ontap_file_security_permissions_acl - added `actions` and `modify` in module output.
  - na_ontap_igroup_initiator - added `actions` in module output.
  - na_ontap_name_mappings - added `actions` and `modify` in module output.
  - na_ontap_node - added `modify` in module output.
  - na_ontap_lun_map - added `actions` in module output.
  - na_ontap_lun_map_reporting_nodes - added `actions` in module output.
  - na_ontap_storage_auto_giveback - added information on modifed attributes in module output.
  - na_ontap_vscan_scanner_pool - added REST support to Vscan Scanner Pools Configuration module, requires ONTAP 9.6 or later.
  - na_ontap_cifs_server - new option `is_multichannel_enabled` added in REST, requires ONTAP 9.10 or later.
  - na_ontap_vserver_audit - new options `schedule.*` added under `log.rotation`.

### Bug Fixes
  - na_ontap_igroup_initiator - fixed issue with idempotency.

## 22.9.0

### New Options
  - na_ontap_cifs_server - new option `lm_compatibility_level` added in REST, requires ONTAP 9.8 or later.
  - na_ontap_cluster - new option `certificate.uuid` added in REST, requires ONTAP 9.10 or later.
  - na_ontap_ems_destination - new options `syslog`, `port`, `transport`, `message_format`, `timestamp_format_override` and `hostname_format_override` added in REST, requires ONTAP 9.12.1 or later.

### Minor Changes
  - na_ontap_s3_services - create, modify S3 service returns `s3_service_info` in module output.
  - na_ontap_nfs - fix error with `windows` in REST for ONTAP 9.10 or earlier.
  - na_ontap_cluster_peer - added REST only support for modifying remote intercluster addresses in cluster peer relation.
  - na_ontap_snapmirror - updated resync and resume operation for synchronous snapmirror relationship in REST.

### Bug Fixes
  - na_ontap_snapshot_policy - fix issue with modifying snapshot policy in REST.
  - na_ontap_volume - modified `type` to be case insensitive in REST.
  - na_ontap_security_certificates - fix error with ontap_info returned in module output in REST.

### New Modules
  - na_ontap_snmp_config - REST only support for modifying SNMP configuration, requires ONTAP 9.7 or later.
  - na_ontap_cli_timeout - REST only support for setting CLI inactivity timeout value, requires ONTAP 9.6 or later.
  - na_ontap_cifs_unix_symlink_mapping - REST only support for managing UNIX symbolic link mapping for CIFS clients, requires ONTAP 9.6 or later.

## 22.8.3

### Bug Fixes
  - na_ontap_vserver_peer - fix issue with peering multiple clusters with same vserver name in REST.
  - na_ontap_ems_destination - fix field error with `certificate.name` for ONTAP 9.11.1 or later in REST.
  - na_ontap_snmp - fix for getting error when `authentication_method` set to default with ZAPI.

## 22.8.1

### Bug Fixes
  - na_ontap_dns - fix keyerror for uuid when DNS is set to vserver in REST.
  - na_ontap_volume - fix invalid field error with 'space.snapshot.autodelete' in REST.

## 22.8.0

### New Options
  - na_ontap_lun - new option `qtree_name` added in REST.
  - na_ontap_rest_info - new option `hal_linking` added.
  - na_ontap_cifs_server - new option `default_site` added in REST, requires ONTAP 9.13.1 or later.
  - na_ontap_ems_destination - new option `certificate`, `ca` added.
  - na_ontap_volume - added new REST only options `vol_nearly_full_threshold_percent` and `vol_full_threshold_percent`, requires ONTAP 9.9 or later.
  - na_ontap_qos_policy_group - added new REST only options `expected_iops_allocation` and `peak_iops_allocation`, requires ONTAP 9.10.1 or later.

### Minor Changes
  - na_ontap_user - added warning message when password is not changed.
  - na_ontap_restit - returns changed as False for GET method.
  - na_ontap_kerberos_realm - added REST support for `admin_server_ip`, `admin_server_port`, `pw_server_ip`, `pw_server_port` and `clock_skew`, requires ONTAP 9.13.1 or later.
  - na_ontap_volume - added REST support for `atime_update` requires ONTAP 9.8 or later, `snapdir_access` and `snapshot_auto_delete` requires ONTAP 9.13.1 or later.
  - na_ontap_net_ifgrp - return `name` and other details of a newly created interface group in module output in REST.
  - na_ontap_cg_snapshot - added REST support to the cg snapshot module, requires ONTAP 9.10.1 or later.
  - na_ontap_snmp - added REST support for `snmpv3` user.

### Bug Fixes
  - na_ontap_nfs - fix `default_user` under `windows` not getting modified, if not set previously, in REST.
  - na_ontap_dns - fix DNS not working with Cluster mode.
  - na_ontap_ems_filter - fix modify operation to add rule in existing filter.
  - na_ontap_svm - fix REST version warning for `ndmp` under `services`.
  - na_ontap_login_messages - fix idempotency issue in Cluster scope in REST.

### New Modules
  - na_ontap_ems_config - REST only support for modifying EMS configuration, requires ONTAP 9.6 or later.

## 22.7.0

### New Options
  - na_ontap_s3_buckets - new option `nas_path` added, requires ONTAP 9.12.1 or later.

### Minor Changes
  - na_ontap_name_mappings - added choices `s3_win` and `s3_unix` to `direction`, requires ONTAP 9.12.1 or later.

### Bug Fixes
  - na_ontap_login_messages - fix `banner` and `motd_message` not idempotent when trailing '\n' is present.
  - na_ontap_login_messages - fix idempotent issue on `show_cluster_motd` option when try to set banner or motd_message for the first time in REST.

### New Modules
  - na_ontap_active_directory_domain_controllers - Added REST support for ONTAP 9.12.0 or later and cli support for lower versions.

## 22.6.0

### New Options
  - na_ontap_aggregate - new REST only option `tags` added, requires ONTAP 9.13.1 or later version.
  - na_ontap_qos_policy_group - new REST only option `adaptive_qos_options.block_size` added, requires ONTAP 9.10.1 or later version.
  - na_ontap_s3_buckets - new option `type` added, requires ONTAP 9.12.1 or later.
  - na_ontap_volume - new REST only option `tags` added, requires ONTAP 9.13.1 or later version.

### Minor Changes
  - retry create or modify when getting temporarily locked from changes error in REST.
  - na_ontap_export_policy - added `name` to modify in module output if export policy is renamed.
  - na_ontap_broadcast_domain - skip checking modify when `state` is absent.
  - na_ontap_qos_policy_group - skip checking modify when `state` is absent.

### Bug Fixes
  - na_ontap_export_policy - fix cannot delete export policy if `from_name` option is set.
  - na_ontap_file_security_permissions_acl - fix idempotent issue on `propagation_mode` option.
  - na_ontap_qos_policy_group - one occurrence of msg missing in call to fail_json.
  - na_ontap_s3_groups - fix error when current s3 groups has no users configured.
  - na_ontap_s3_groups - fix cannot modify `policies` if not configured in create.
  - na_ontap_security_certificates - fix duplicate entry error when `vserver` option is set with admin vserver.
  - na_ontap_snapmirror_policy - fix cannot disable `is_network_compression_enabled` in REST.
  - na_ontap_svm - skip modify validation when trying to delete svm.
  - na_ontap_qos_adaptive_policy_group - rename group when from_name is present and state is present.

### New Modules
  - na_ontap_kerberos_interface - Enable or disable Kerberos interface config, requires ONTAP 9.7 or later version.

## 22.5.0

### New Options
  - na_ontap_cifs - new options `browsable` and `show_previous_versions` added in REST.

### Minor Changes
  - na_ontap_cifs - removed default value for `unix_symlink` as its not supported with ZAPI.
  - na_ontap_cifs - updated documentation and examples for REST.
  - na_ontap_file_security_permissions - updated module examples.
  - na_ontap_ipspace - improved module fail error message in REST.
  - na_ontap_rest_info - improved documentation for `parameters` option.
  - na_ontap_security_config - updated documentation for `supported_cipher_suites`.
  - na_ontap_user: option ``vserver`` is not required with REST, ignore this option to create cluster scoped user.

### Bug Fixes
  - na_ontap_cifs - throw error if set `unix_symlink` in ZAPI.
  - na_ontap_cifs - throw error if used options that require recent ONTAP version.
  - na_ontap_file_security_permissions - error if more than one desired ACLs has same user, access, access_control and apply_to.
  - na_ontap_file_security_permissions - fix idempotency issue on `acls.propagation_mode` option.
  - na_ontap_file_security_permissions - fix TypeError when current acls is None.
  - na_ontap_ipspace - fix cannot delete ipspace if `from_ipspace` is present.
  - na_ontap_iscsi_security - error module if use_rest never is set.
  - na_ontap_iscsi_security - fix KeyError on `outbound_username` option.
  - na_ontap_qtree - ignore job entry doesn't exist error when creating qtree with REST to bypass ONTAP issue with FSx.
  - na_ontap_quotas - ignore job entry doesn't exist error when creating quota with REST to bypass ONTAP issue with FSx.
  - na_ontap_security_config - fix error on specifying protocol version `TLSv1.1` when fips is enabled.
  - na_ontap_snapmirror - error if identity_preservation set in ZAPI.
  - na_ontap_snapmirror - Added option `identity_preservation` support from ONTAP 9.11.1 in REST.

## 22.4.1

### Bug Fixes
  - na_ontap_snapmirror - fix invalid value error for return_timeout, modified the value to 120 seconds.

## 22.4.0

### New Options
  - na_ontap_security_config - new option `supported_cipher_suites` added in REST.
  - na_ontap_snapmirror - new option `identity_preservation` added in REST.

### Minor Changes
  - na_ontap_user_role - add support for rest-role `privileges.access` choices `read_create`, `read_modify` and `read_create_modify`, supported only with REST and requires ONTAP 9.11.1 or later versions.
  - na_ontap_user_role - `command_directory_name` requires 9.11.1 or later with REST.
  - na_ontap_rest_cli - returns changed only for verbs POST, PATCH and DELETE.
  - na_ontap_snapmirror - wait 600 seconds for snapmirror creation to complete in REST.
  - na_ontap_security_config - Replaced private cli with REST API for GET and PATCH.
  - na_ontap_security_config - Added support for protocol version `TLSV1.3`.

### Bug Fixes
  - na_ontap_interface - fix incorrect warning raised when try to rename interface.
  - na_ontap_ldap_client - fix duplicate entry error when used cluster vserver in REST.
  - na_ontap_ldap_client - fix KeyError on `name` in ZAPI.
  - na_ontap_san_create - Role documentation correct to from nas to san.
  - na_ontap_user - fix KeyError vserver in ZAPI.
  - na_ontap_user_role - report error when command/command directory path set in REST for ONTAP earlier versions.
  - na_ontap_volume - fix error when try to unmount volume and modify snaplock attribute.
  - na_ontap_volume - fix idempotent issue when try to offline and modify other volume options.
  - na_ontap_vserver_audit - fix invalid field value error of log retention count and duration.
  - na_ontap_vserver_audit - Added `log_path` option in modify.

### New Modules
  - na_ontap_ems_filter - Create, delete, or modify EMS filters.

## 22.3.0

### New Options
  - na_ontap_aggregate - new option `allow_flexgroups` added.
  - na_ontap_cifs - new options `access_based_enumeration`, `change_notify`, `encryption`,`home_directory`, `oplocks`, `show_snapshot`, `allow_unencrypted_access`, `namespace_caching` and `continuously_available` added in REST.
  - na_ontap_nfs - new options `root`, `windows` and `security` added in REST.
  - na_ontap_volume_efficiency - new option `volume_name` added.

### Minor Changes
  - na_ontap_dns - `skip_validation` option requires 9.9.1 or later with REST and ignored for cluster DNS operations.
  - na_ontap_dns - support cluster scope for modify and delete.
  - na_ontap_interface - do not attempt to migrate FC interface if desired `home_port`, `home_node` and `current_port`, `current_node` are same.
  - na_ontap_license - support for NLF v2 license files.
  - na_ontap_user_role - `path` is required if `privileges` set in REST.
  - na_ontap_user_role - `command_directory_name` is required if `privileges` not set in REST.
  - na_ontap_volume_efficiency - updated private cli with REST API.
  - na_ontap_volume_efficiency - REST support for `policy` requires 9.7 or later, `path` requires 9.9.1 or later and `volume_efficiency` and `start_ve_scan_old_data` requires 9.11.1 or later.
  - na_ontap_volume_efficiency - `schedule`, `start_ve_scan_all`, `start_ve_build_metadata`, `start_ve_delete_checkpoint`, `start_ve_queue_operation`, `start_ve_qos_policy` and `stop_ve_all_operations` options are not supported with REST.

### Bug Fixes
  - na_ontap_aggregate - try to offline aggregate when disk add operation is in progress in ZAPI.
  - na_ontap_interface - fix idempotency issue when `home_port` not set in creating FC interface.
  - na_ontap_rest_info - fix field issue with private/cli and support/autosupport/check APIs.
  - na_ontap_snapshot - fix cannot modify `snapmirror_label`, `expiry_time` and `comment` if not configured in create.
  - na_ontap_user_role - fix AttributeError 'NetAppOntapUserRole' object has no attribute 'name'.
  - na_ontap_user_role - fix duplicate entry error in ZAPI.
  - na_ontap_user_role - fix entry does not exist error when trying to delete privilege in REST.
  - na_ontap_user_role - fix KeyError on `vserver`, `command_directory_name` in ZAPI and `path`, `query` in REST.
  - na_ontap_volume_efficiency - fix idempotent issue when state is absent and efficiency options are set in ZAPI.

### New Modules
  - na_ontap_vserver_audit - added REST only support for create, modify and delete vserver audit configuration.
  - na_ontap_vserver_peer_permissions - added REST only support for create, modify and delete vserver peer permissions for an SVM.

## 22.2.0

### New Options
  - na_ontap_interface - new option `fail_if_subnet_conflicts` - requires REST and ONTAP 9.11.1 or later.
  - na_ontap_interface - option `subnet_name` is now supported with REST with ONTAP 9.11.1 or later.
  - na_ontap_snapmirror - support `schedule` with REST and ONTAP 9.11.1, add alias `transfer_schedule`.
  - na_ontap_snapmirror_policy - new option `copy_latest_source_snapshot`, `create_snapshot_on_source` and `sync_type` added in REST.
  - na_ontap_snapmirror_policy - new option `transfer_schedule` for async policy types.
  - na_ontap_snapmirror_policy - Added new choices sync and async for policy type in REST.
  - na_ontap_iscsi - new option `target_alias` added in REST.

### Minor Changes
  - na_ontap_active_directory - add `fqdn` as aliases for `domain`.
  - na_ontap_snapmirror_policy - warn when replacing policy type `async_mirror`, `mirror_vault` and `vault` with policy type `async` and `strict_sync_mirror`, `sync_mirror` with `sync` in REST.
  - na_ontap_snapmirror_policy - add unsupported options in ZAPI.
  - na_ontap_snapmirror_policy - add support for cluster scoped policy with REST.
  - na_ontap_svm - warn in case of mismatch in language option spelling.

### Bug Fixes
  - na_ontap_quotas - fix duplicate entry error when trying to add quota rule in REST.
  - na_ontap_quotas - fix entry does not exist error when trying to modify quota status in REST.
  - na_ontap_security_ipsec_policy - fix cannot get current security IPsec policy with ipspace.
  - na_ontap_security_ipsec_policy - fix KeyError on `authentication_method`.
  - na_ontap_security_key_manager - requires 9.7+ to work with REST.
  - na_ontap_snapmirror_policy - fixed idempotency issue on `identity_preservation` option when using REST.
  - na_ontap_snapmirror_policy - fix desired policy type not configured in cli with REST.
  - na_ontap_snapmirror_policy - deleting all retention rules would trigger an error when the existing policy requires at least one rule.
  - na_ontap_snapmirror_policy - index error on rules with ONTAP 9.12.1 as not all fields are present.
  - na_ontap_volume - fixed bug preventing unmount and taking a volume off line at the same time

### Added REST support to existing modules
  - na_ontap_active_directory - REST requires ONTAP 9.12.1 or later.

### New Modules
  - na_ontap_cifs_local_user - ability to create/modify/delete a cifs local user


## 22.1.0

### New Options
  - na_ontap_interface - new option `probe_port` for Azure load balancer.
  - na_ontap_snapmirror_policy - new option `copy_all_source_snapshots` added in REST.

### Minor Changes
  - na_ontap_aggregate - add support for `service_state` option from ONTAP 9.11.1 or later in REST.
  - na_ontap_aggregate - add `name` to modify in module output if aggregate is renamed.
  - na_ontap_cifs_local_group_member - Added REST API support to retrieve, add and remove CIFS group member.
  - na_ontap_cifs_local_group_member - REST support is from ONTAP 9.10.1 or later.
  - na_ontap_cifs_server - skip `service_state` option in create if not set.
  - na_ontap_quotas - for qtree type, allow quota_target in path format /vol/vol_name/qtree_name in REST.
  - na_ontap_volume - report error if vserver does not exist or is not a data vserver on create.

### Bug Fixes
  - na_ontap_active_directory - updated doc as only ZAPI is supported at present, force an error with use_rest always.
  - na_ontap_aggregate - fix examples in documentation.
  - na_ontap_aggregate - allow adding disks before trying to offline aggregate.
  - na_ontap_aggregate - error if `unmount_volumes` set in REST, by default REST unmount volumes when trying to offline aggregate.
  - na_ontap_aggregate - fix `service_state` option skipped if its set to offline in create.
  - na_ontap_cg_snapshot - updated doc with deprecation warning as it is a ZAPI only module.
  - na_ontap_cifs_server - fix `service_state` is stopped when trying to modify cifs server in REST.
  - na_ontap_file_directory_policy - updated doc with deprecation warning as it is a ZAPI only module.
  - na_ontap_file_security_permissions - updated notes to indicate ONTAP 9.9.1 or later is required.
  - na_ontap_file_security_permissions_acl - updated notes to indicate ONTAP 9.9.1 or later is required.
  - na_ontap_interface - fix cannot set `location.home_node.name` and `location.node.name` error when trying to create or modify fc interface.
  - na_ontap_interface - fix unexpected argument error with `ipspace` when trying to get fc interface.
  - na_ontap_interface - fix error when trying to migrate fc interface in REST.
  - na_ontap_qtree - fix cannot get current qtree if enclosed in curly braces.
  - na_ontap_quota_policy - updated doc with deprecation warning as it is a ZAPI only module.
  - na_ontap_quotas - fix default tree quota rule gets modified when `quota_target` is set in REST.
  - na_ontap_quotas - fix user/group quota rule without qtree gets modified when `qtree` is set.
  - na_ontap_svm_options - updated doc with deprecation warning as it is a ZAPI only module.

### New Modules
  - na_ontap_cifs_local_group - added REST only support for create, modify, rename and delete CIFS local group of an SVM.
  - na_ontap_security_ipsec_ca_certificate - add or delete IPsec CA certificate.
  - na_ontap_security_ipsec_config - Manage IPsec configuration.
  - na_ontap_security_ipsec_policy - Create, modify and delete security IPsec policy.

## 22.0.1

### Bug Fixes
  - na_ontap_interface - fix `netmask` not idempotent in REST.
  - na_ontap_mcc_mediator - Fix error that would prevent mediator deletion.

### Minor Changes
  - na_ontap_interface - allow setting `netmask` with netmask length in ZAPI.

## 22.0.0

### Major Changes
  - With this release all modules except for the modules called up above now support REST.
  - ZAPI calls will continue to work, but will return a warning that they are deprecated and users should migrate to REST.

### New Rest Info
  - na_ontap_rest_info - support added for protocols/active-directory.
  - na_ontap_rest_info - support added for protocols/cifs/group-policies.
  - na_ontap_rest_info - support added for protocols/nfs/connected-client-settings.
  - na_ontap_rest_info - support added for security/aws-kms.

### Minor Changes
  - na_ontap_debug - report python executable version and path.
  - na_ontap_net_routes - `metric` option is supported from ONTAP 9.11.0 or later in REST.
  - na_ontap_service_policy - update services for 9.11.1 - make it easier to add new services.
  - na_ontap_snapmirror - `schedule` is handled through `policy` for REST.
  - na_ontap_snapmirror_policy - improve error reporting and report errors in check_mode.
  - na_ontap_volume - `wait_for_completion` and `check_interval` is now supported for volume move and encryption in REST.

### New Options
  - na_ontap_export_policy_rule - `allow_suid`, `allow_device_creation` and `chown_mode` is now supported from ONTAP 9.9.1 or later in REST.
  - na_ontap_export_policy_rule - `allow_device_creation` and `chown_mode` is now supported in ZAPI.
  - na_ontap_ldap_client - new option `skip_config_validation`.
  - na_ontap_service_policy - new options `known_services` and `additional_services`.
  - na_ontap_snapmirror_policy - new option `identity_preservation` added.
  - na_ontap_snapmirror_policy - `name` added as an alias for `policy_name`.
  - na_ontap_volume - new option `max_wait_time` added.
  - na_ontap_volume - new REST option `analytics` added.
  - tracing - allow to selectively trace headers and authentication.

### Bug Fixes
  - iso8601 filters - fix documentation generation issue.
  - na_ontap_info - Added vserver in key_fields of net_interface_info.
  - na_ontap_interface - fix error where an `address` with an IPV6 ip would try to modify each time playbook was run.
  - na_ontap_ldap_client - `servers` not accepted when using ZAPI and `ldap_servers` not handling a single server properly.
  - na_ontap_rest_info - fixed error where module would fail silently when using `owning_resouce` and a non-existent vserver.
  - na_ontap_user_role - fixed Invalid JSON input. Expecting "privileges" to be an array.
  - na_ontap_volume - fix error when trying to move encrypted volume and `encrypt` is True in REST.
  - na_ontap_volume - fix error when trying to unencrypt volume in REST.
  - na_ontap_volume - fix KeyError on `aggregate_name` when trying to unencrypt volume in ZAPI.
  - na_ontap_volume - `snapdir_access` is not supported by REST and will currently inform you now if you try to use it with REST.
  - na_ontap_volume - when deleting a volume, don't report a warning when unmount is successful (error is None).
  - ZAPI only modules -- no longer have `use_rest` as an option.
  - tracing - redact headers and authentication secrets by default.

### New Modules
  - na_ontap_local_hosts - added REST only support for create, update and delete IP to hostname mappings for SVM of the cluster.
  - na_ontap_bgp_peer_group - Create, modify and delete BGP peer groups.
  - na_ontap_file_security_permissions - Update SD and ACLs.
  - na_ontap_file_security_permissions_acl - Add, update, or delete a single ACL.
  - na_ontap_name_mappings - added REST only support for create, update and delete name mappings configuration.

## 21.24.1

### Bug Fixes
  - new meta/execution-environment.yml is failing ansible-builder sanitize step.

## 21.24.0

### New Options
  - na_ontap_cluster - `timezone.name` to modify cluster timezone. REST only.
  - na_ontap_restit - `files` and `accept_header` to support multipart/form-data for write and read.
  - na_ontap_snmp_traphosts - Added `host` option in REST.
  - na_ontap_svm - Added `ndmp` option to services in REST.

### Minor Changes
  - na_ontap_ems_destination - improve error messages - augment UT coverage (thanks to bielawb).
  - na_ontap_interface - `dns_domain_name` is now supported from ONTAP 9.9.0 or later in REST.
  - na_ontap_interface - `is_dns_update_enabled` is now supported from ONTAP 9.9.1 or later in REST.
  - na_ontap_interface - attempt to set interface_type to `ip` when `protocols` is set to "none".
  - na_ontap_vserver_create - `protocol` is now optional.  `role` is not set when protocol is absent.
  - na_ontap_vserver_create - `firewall_policy` is not set when `service_policy` is present, as `service_policy` is preferred.
  - na_ontap_vserver_create - added `interface_type`.  Only a value of `ip` is currently supported.
  - na_ontap_vserver_create - added support for vserver management interface when using REST.
  - na_ontap_rest_info - Allowed the support of multiple subsets and warn when using `**` in fields.

### New Rest Info
  - All REST GET's up to and including 9.11.1 that do not require a UUID/KEY to be past in are now supported
  - na_ontap_rest_info - support added for cluster.
  - na_ontap_rest_info - support added for cluster/counter/tables.
  - na_ontap_rest_info - support added for cluster/licensing/capacity-pools.
  - na_ontap_rest_info - support added for cluster/licensing/license-managers.
  - na_ontap_rest_info - support added for cluster/metrocluster/svms.
  - na_ontap_rest_info - support added for cluster/sensors.
  - na_ontap_rest_info - support added for name-services/cache/group-membership/settings.
  - na_ontap_rest_info - support added for name-services/cache/host/settings.
  - na_ontap_rest_info - support added for name-services/cache/netgroup/settings.
  - na_ontap_rest_info - support added for name-services/cache/setting.
  - na_ontap_rest_info - support added for name-services/cache/unix-group/settings.
  - na_ontap_rest_info - support added for name-services/ldap-schemas.
  - na_ontap_rest_info - support added for network/fc/fabrics.
  - na_ontap_rest_info - support added for network/fc/interfaces.
  - na_ontap_rest_info - support added for network/fc/interfaces.
  - na_ontap_rest_info - support added for network/ip/subnets.
  - na_ontap_rest_info - support added for protocols/cifs/connections.
  - na_ontap_rest_info - support added for protocols/cifs/netbios.
  - na_ontap_rest_info - support added for protocols/cifs/session/files.
  - na_ontap_rest_info - support added for protocols/cifs/shadow-copies.
  - na_ontap_rest_info - support added for protocols/cifs/shadowcopy-sets.
  - na_ontap_rest_info - support added for protocols/nfs/connected-client-maps.
  - na_ontap_rest_info - support added for security.
  - na_ontap_rest_info - support added for security/multi-admin-verify.
  - na_ontap_rest_info - support added for security/multi-admin-verify/approval-groups.
  - na_ontap_rest_info - support added for security/multi-admin-verify/requests.
  - na_ontap_rest_info - support added for security/multi-admin-verify/rules.
  - na_ontap_rest_info - support added for storage/file/moves.
  - na_ontap_rest_info - support added for storage/pools.

### Bug Fixes
  - na_ontap_cifs - fix KeyError on `unix_symlink` field when using REST.
  - na_ontap_cifs_acl - use `type` when deleting unix-user or unix-group from ACL in ZAPI.
  - na_ontap_command - do not run command in check_mode (thanks to darksoul42).
  - na_ontap_ems_destination - fix idempotency issue when `type` value is rest_api.
  - na_ontap_interface - improve error message when interface type is required with REST.
  - na_ontap_qtree - fix KeyError on unix_permissions.
  - na_ontap_rest_cli - do not run command in check_mode (thanks to darksoul42).
  - na_ontap_s3_groups - if `policies` is None module should no longer fail
  - na_ontap_user - fix idempotency issue with 9.11 because of new is_ldap_fastbind field.
  - na_ontap_volume_efficiency -- Missing fields in REST get should return None and not crash module.

### Added REST support to existing modules
  - na_ontap_quotas - added REST support.
  - na_ontap_net_subnet - added REST support.

### New Module
  - na_ontap_security_ssh - Updates the SSH server configuration for cluster and SVM scopes - REST only.

### New Filters
  - iso8601_duration_to_seconds - to convert a duration in ISO 8601 format to seconds.
  - iso8601_duration_from_seconds - to convert seconds to a duration in ISO 8601 format.

## 21.23.0

### New Options
  - all REST modules - new option `force_ontap_version` to bypass permission issues with custom vsadmin roles.
  - na_ontap_export_policy_rule - new option `force_delete_on_first_match` to support duplicate entries on delete.
  - na_ontap_rest_info - new option `ignore_api_errors` to report error in subset rather than breaking execution.
  - na_ontap_security_key_manager - new REST options `external` and `vserver` for external key manager.
  - na_ontap_security_key_manager - new REST option `onboard` for onboard key manager.

### New Rest Info
  - na_ontap_rest_info - support added for protocols/vscan/on-access-policies.
  - na_ontap_rest_info - support added for protocols/vscan/on-demand-policies.
  - na_ontap_rest_info - support added for protocols/vscan/scanner-pools.

### Bug Fixes
  - na_ontap_cifs_acl - use `type` if present when fetching existing ACL with ZAPI.
  - na_ontap_cifs_local_user_set_password - when using ZAPI, do not require cluster admin privileges.
  - na_ontap_cluster_config Role - incorrect license was show - updated to GNU General Public License v3.0
  - na_ontap_flexcache - properly use `origin_cluster` in GET but not in POST when using REST.
  - na_ontap_kerberos_realm - fix cannot modify `comment` option in ZAPI.
  - na_ontap_lun_copy - fix key error on `source_vserver` option.
  - na_ontap_s3_buckets - fix options that cannot be modified if not set in creating s3 buckets.
  - na_ontap_s3_buckets - fix TypeError if `conditions` not present in policy statements.
  - na_ontap_s3_buckets - updated correct choices in options `audit_event_selector.access` and `audit_event_selector.permission`.
  - na_ontap_ntp - fixed typeError on `key_id` field with ZAPI.

### Minor Changes
  - na_ontap_export_policy_rule - `rule_index` is now optional for create and delete.
  - na_ontap_interface - improved validations for unsupported options with FC interfaces.
  - na_ontap_kerberos_realm - change `kdc_port` option type to int.
  - na_ontap_ntp - for ONTAP version 9.6 or below fall back to ZAPI when `use_rest` is set to `auto` or fail when REST is desired.
  - na_ontap_ntp_key - fail for ONTAP version 9.6 or below when `use_rest` is set to `auto` or when REST is desired.
  - na_ontap_volume - attempt to delete volume even when unmounting or offlining failed.

### Added REST support to existing modules
  - na_ontap_cifs_local_user_set_password -- added REST support.
  - na_ontap_cluster_ha - added REST support.
  - na_ontap_lun_copy - added REST support.
  - na_ontap_lun_map_reporting_nodes - added REST support.
  - na_ontap_kerberos_realm - added REST support.
  - na_ontap_security_key_manager - added REST support.
  - na_ontap_ucadapter - added REST support.
  - na_ontap_user_role -- added REST support.

### New Module
  - na_ontap_ems_destination - Manage EMS destination - Contribution by Bartosz Bielawski (@bielawb).

## 21.22.0

### New Options
  - na_ontap_job_schedule - new option `cluster` added.
  - na_ontap_ldap_client - Added `ldaps_enabled` option in ZAPI.

### Bug Fixes
  - na_ontap_cluster_peer - report an error if there is an attempt to use the already peered clusters.
  - na_ontap_interface - fix error deleting fc interface if it is enabled in REST.
  - na_ontap_license - fix intermittent KeyError when adding licenses with REST.
  - na_ontap_lun - Added `lun_modify` after `app_modify` to fix idempotency issue.
  - na_ontap_name_service_switch - fix AttributeError 'NoneType' object has no attribute 'get_children' if `sources` is '-' in current.
  - na_ontap_name_service_switch - fix idempotency issue on `sources` option.
  - na_ontap_security_key_manager - fix KeyError on `node`.
  - na_ontap_ntp - fixed typeError on `key_id` field with ZAPI.
  - na_ontap_service_processor_network - fix idempotency issue on `dhcp` option in ZAPI.
  - na_ontap_service_processor_network - fail module when trying to disable `dhcp` and not setting one of `ip_address`, `netmask`, `gateway_ip_address` different than current.
  - na_ontap_service_processor_network - allow manually configuring network if all of `ip_address`, `netmask`, `gateway_ip_address` set and `dhcp` not present in REST.
  - na_ontap_service_processor_network - fix setting `dhcp` v4 takes more than `wait_for_completion` retries.
  - na_ontap_service_processor_network - fix `wait_for_completion` ignored when trying to enable service processor network interface in ZAPI.
  - na_ontap_software_update - improve error handling if image file is already present.
  - na_ontap_software_update - improve error handling when node is rebooting with REST.
  - na_ontap_software_update - when using REST with ONTAP 9.9 or later, timeout value is properly set.
  - na_ontap_user - enforce that all methods are under a single application.
  - na_ontap_user - is_locked was not properly read with ZAPI, making the module not idempotent.

### Minor Changes
  - na_ontap_license - return list of updated package names.
  - na_ontap_nvme_subsystem - report subsystem as absent if vserver cannot be found when attempting a delete.
  - na_ontap_rest_info - Will now warn you if a `gather_subset` is not supported by your version of ONTAP.
  - na_ontap_rest_info - Will now include a message in return output about `gather_subset` not supported by your version of ONTAP.
  - na_ontap_security_key_manager - indicate that `node` is not used and is deprecated.
  - na_ontap_software_update - deleting a software package is now supported with ZAPI and REST.
  - na_ontap_svm - added vserver as a convenient alias for name when using module_defaults.
  - na_ontap_wait_for_condition - added `snapmirror_relationship` to wait on `state` or `transfer_state` (REST only).
  - na_ontap_ldap - fall back to ZAPI when `use_rest` is set to `auto` or fail when REST is desired.
  - all modules - do not fail on ZAPI EMS log when vserver does not exist.

### Added REST support to existing modules
  - na_ontap_ldap_client - added REST support.
  - na_ontap_name_service_switch - added REST support.
  - na_ontap_wait_for_condition - added REST support.

## 21.21.0

### New Options
  - na_ontap_cluster_config role - support `broadcast_domain` and `service_policy` with REST.
  - na_ontap_interface - support `broadcast_domain` with REST.
  - na_ontap_lun - support `qos_adaptive_policy_group` with REST.
  - na_ontap_ntp - added `key_id` for both REST and ZAPI
  - na_ontap_qtree - added `unix_user` and `unix_group` options in REST.
  - na_ontap_snapmirror - new option `validate_source_path` to disable this validation.
  - na_ontap_unix_user - added new option `primary_gid` aliased to `group_id`.
  - na_ontap_vserver_create role - support `broadcast_domain`, `ipspace`, and `service_policy` with REST.

### Bug Fixes
  - na_ontap_interface - enforce requirement for address/netmask for interfaces other than FC.
  - na_ontap_interface - fix idempotency issue for cluster scoped interfaces when using REST.
  - na_ontap_interface - fix potential node and uuid issues with LIF migration.
  - na_ontap_interface - FC interfaces - scope is not supported.
  - na_ontap_interface - FC interfaces - home_port is not supported for ONTAP 9.7 or earlier.
  - na_ontap_interface - FC interfaces - home_node should not be sent as location.home_node.
  - na_ontap_interface - FC interfaces - service_policy is not supported.
  - na_ontap_interface - ignore 'none' when using REST rather than reporting unexpected protocol.
  - na_ontap_lun - catch ZAPI error on get LUN.
  - na_ontap_lun - ignore resize error if no change was required.
  - na_ontap_lun - report error if flexvol_name is missing when using ZAPI.
  - na_ontap_net_subnet - fix `ipspace` option ignored in getting net subnet.
  - na_ontap_qtree - fix idempotency issue on `unix_permissions` option.
  - na_ontap_s3_buckets - accept `sid` as a number or a string.
  - na_ontap_s3_buckets - Module will set `enabled` during create.
  - na_ontap_s3_buckets - Module will not fail on create if no `policy` is given.
  - na_ontap_svm - KeyError on CIFS when using REST with ONTAP 9.8 or lower.
  - na_ontap_volume - fix idempotency issue on `unix_permissions` option.
  - na_ontap_volume - `volume_security_style` was not modified if other security options were present with ZAPI.
  - na_ontap_vserver_create role - add rule index as it is now required.
  - na_ontap_snapmirror - relax check for source when using REST.
  - na_ontap_snapmirror - fix potential issue when destination is using REST but source is using ZAPI.

### New Module
  - na_ontap_ntp_key - Manage NTP keys.
  - na_ontap_s3_groups - Manage s3 groups.
  - na_ontap_s3_policies - Manage S3 policies.

### Minor Changes
  - na_ontap_info - add quota-policy-info.
  - na_ontap_info - add computed serial_hex and naa_id for lun_info.
  - na_ontap_login_messages - support cluster scope when using REST.
  - na_ontap_motd - deprecated in favor of `na_ontap_login_messages`.  Fail when use_rest is set to `always` as REST is not supported.
  - na_ontap_rest_info - add computed serial_hex and naa_id for storage/luns when serial_number is present.
  - na_ontap_s3_users - `secret_key` and `access_token` are now returned when creating a user.
  - na_ontap_snapmirror - validate source endpoint for ZAPI and REST, accounting for vserver local name.
  - na_ontap_snapmirror - improve errror messages to be more specific and consistent.
  - na_ontap_snapmirror - wait for the relationship to come back to idle after a resync.
  - na_ontap_user - accept `service_processor` as an alias for `service-processor` with ZAPI, to be consistent with REST.

### Known Issues:
  - na_ontap_snapshot - added documentation to use UTC format for `expiry_time`.

### Added REST support to existing modules
  - na_ontap_service_processor_network - Added REST support.
  - na_ontap_unix_group - added REST support.
  - na_ontap_unix_user - added REST support.
  - na_ontap_volume - now defaults to REST with `use_rest: auto`, like every other module.  ZAPI can be forced with `use_rest: never`.


## 21.20.0

### Bug Fixes
  - na_ontap_autosupport - fix idempotency issue on `state` field with ONTAP 9.11.
  - na_ontap_autosupport - TypeError on `support` and `ondemand_enabled` field with ONTAP 9.11.
  - na_ontap_net_subnet - delete fails if ipspace is different than Default.
  - na_ontap_portset - fixed idempotency issue when `ports` has identical values.
  - na_ontap_portset - fixed error when trying to remove partial ports from portset if igroups are bound to it.
  - na_ontap_quotas - fix another quota operation is currently in progress issue.
  - na_ontap_quotas - fix idempotency issue on `threshold` option.
  - na_ontap_snapmirror - support for SSL certificate authentication for both sides when using ONTAP.
  - na_ontap_snapmirror - fix issue where there was no wait on quiesce before aborting.
  - na_ontap_snapmirror - fix issue where there was no wait on the relationship to end transferring.
  - na_ontap_snapmirror - fix error in snapmirror restore by changing option `clean_up_failure` as optional when using ZAPI.
  - na_ontap_software_update - now reports changed=False when the package is already present.
  - na_ontap_user - fix idempotency issue with SSH with second_authentication_method.
  - na_ontap_vscan_on_access_policy - fixed options `filters`, `file_ext_to_exclude` and `paths_to_exclude` cannot be reset to empty values in ZAPI.
  - na_ontap_zapit - fix failure in precluster mode.

### New Options
  - na_ontap_cifs_server - added `security` options in REST.
  - na_ontap_export_policy_rule - added `from_index` for both REST and ZAPI. Change `rule_index` to required.
  - na_ontap_snapmirror - new option `peer_options` to define source connection parameters.
  - na_ontap_snapmirror - new option `transferring_time_out` to define how long to wait for transfer to complete on create or initialize.
  - na_ontap_vscan_on_access_policy - new REST options `scan_readonly_volumes` and `only_execute_access` added.
  - na_ontap_vserver_cifs_security - added option `encryption_required_for_dc_connections` and `use_ldaps_for_ad_ldap` in ZAPI.

### New Modules
  - na_ontap_s3_service - Manage S3 services.
  - na_ontap_s3_users - Manage S3 users.

### Minor Changes
  - na_ontap_aggregate - updated `disk_types` in documentation.
  - na_ontap_snapmirror - when deleting, attempt to delete even when the relationship cannot be broken.
  - na_ontap_snapmirror - rewrite update for REST using POST to initiate transfer.
  - na_ontap_svm - added documentation for `allowed_protocol`, ndmp is default in REST.
  - na_ontap_user - add support for SAML authentication_method.
  - na_ontap_vserver_cifs_security - added `use_ldaps_for_ad_ldap` and `use_start_tls_for_ad_ldap` as mutually exclusive in ZAPI.
  - na_ontap_vserver_cifs_security - fall back to ZAPI when `use_rest` is set to `auto` or fail when REST is desired.

### Added REST support to existing modules
  - na_ontap_nvme_namespace - added REST support.
  - na_ontap_nvme_subsystem - added REST support.
  - na_ontap_portset - added REST support.
  - na_ontap_software_update - added REST support.
  - na_ontap_vscan_on_access_policy - added REST support.
  - na_ontap_vscan_on_demand_task - added REST support.

## 21.19.1

### Bug Fixes
  - na_ontap_cluster_config - fix the role to be able to create intercluster LIFs with REST (ipspace is required).
  - na_ontap_interface - ignore `vserver` when using REST if role is one of 'cluster', 'node-mgmt', 'intercluster', 'cluster-mgmt'.
  - na_ontap_nvme - fixed invalid boolean value error for `status_admin` when creating nvme service in ZAPI.
  - na_ontap_nvme - fixed `status_admin` option is ignored if set to False when creating nvme service in REST. 
  - na_ontap_service_policy - fixed error in modify by changing resulting json of an existing record in REST.
  - na_ontap_snapmirror - when using ZAPI, wait for the relationship to be quiesced before breaking.
  - na_ontap_snapmirror - when using REST with a policy, fix AttributeError - 'str' object has no attribute 'get'.

## 21.19.0

### Minor Changes
  - na_ontap_interface - use REST when `use_rest` is set to `auto`.
  - na_ontap_qos_adaptive_policy_group - warn about deprecation, fall back to ZAPI or fail when REST is desired.
  - na_ontap_quotas - support TB as a unit, update doc with size format description.

### New Options
  - na_ontap_cifs_server - Added new option `force` for create, delete and `from_name`, `force` for rename when using REST.
  - na_ontap_qos_policy_group - Added REST only supported option `adaptive_qos_options` for configuring adaptive policy.
  - na_ontap_qos_policy_group - Added REST only supported option `fixed_qos_options` for configuring max/min throughput policy.
  - na_ontap_rest_info - new option `owning_resource` for REST info that requires an owning resource. For instance volume for a snapshot
  - na_ontap_cifs - Added `unix_symlink` option in REST.

### New Module
  - na_ontap_s3_bucket - Manage S3 Buckets.

### Bug Fixes
  - na_ontap_cifs - fixed `symlink_properties` option silently ignored for cifs share creation when using REST.
  - na_ontap_cifs - fixed error in modifying comment if it is not set while creating CIFS share in REST.
  - na_ontap_command - fix typo in example.
  - na_ontap_interface - rename fails with 'inconsistency in rename action' for cluster interface with REST.
  - na_ontap_login_messages - fix typo in examples for username.
  - na_ontap_nfs - fix TypeError on NoneType as `tcp_max_xfer_size` is not supported in earlier ONTAP versions.
  - na_ontap_nfs - fix `Extra input` error with ZAPI for `is-nfsv4-enabled`.
  - na_ontap_quotas - Fix idempotency issue on `disk_limit` and `soft_disk_limit`.
  - na_ontap_rest_info: REST API's with hyphens in the name will now be converted to underscores when `use_python_keys` is set to `True` so that YAML parsing works correctly.
  - na_ontap_service_policy - fix examples in documentation.
  - na_ontap_volume - use `time_out` value when creating/modifying/deleting volumes with REST rathar than hardcoded value.
  - na_ontap_volume - QOS policy was not set when using NAS application.
  - na_ontap_volume - correctly warn when attempting to modify NAS application.
  - na_ontap_volume - do not set encrypt on modify, as it is already handled with specialized ZAPI calls.
  - na_ontap_volume_autosize - improve error reporting.

### New Rest Info
  - na_ontap_rest_info - support added for application/consistency-groups
  - na_ontap_rest_info - support added for cluster/fireware/history
  - na_ontap_rest_info - support added for cluster/mediators
  - na_ontap_rest_info - support added for cluster/metrocluster/dr-groups
  - na_ontap_rest_info - support added for cluster/metrocluster/interconnects
  - na_ontap_rest_info - support added for cluster/metrocluster/operations
  - na_ontap_rest_info - support added for cluster/ntp/keys
  - na_ontap_rest_info - support added for cluster/web
  - na_ontap_rest_info - support added for name-services/local-hosts
  - na_ontap_rest_info - support added for name-services/unix-groups
  - na_ontap_rest_info - support added for name-services/unix-users
  - na_ontap_rest_info - support added for network/ethernet/switch/ports
  - na_ontap_rest_info - support added for network/fc/ports
  - na_ontap_rest_info - support added for network/http-proxy
  - na_ontap_rest_info - support added for network/ip/bgp/peer-groups
  - na_ontap_rest_info - support added for protocols/audit
  - na_ontap_rest_info - support added for protocols/cifs/domains
  - na_ontap_rest_info - support added for protocols/cifs/local-groups
  - na_ontap_rest_info - support added for protocols/cifs/local-users
  - na_ontap_rest_info - support added for protocols/cifs/sessions
  - na_ontap_rest_info - support added for protocols/cifs/users-and-groups/privilege
  - na_ontap_rest_info - support added for protocols/cifs/unix-symlink-mapping
  - na_ontap_rest_info - support added for protocols/file-access-tracing/events
  - na_ontap_rest_info - support added for protocols/file-access-tracing/filters
  - na_ontap_rest_info - support added for protocols/fpolicy
  - na_ontap_rest_info - support added for protocols/locks
  - na_ontap_rest_info - support added for protocols/ndmp
  - na_ontap_rest_info - support added for protocols/ndmp/nodes
  - na_ontap_rest_info - support added for protocols/ndmp/sessions
  - na_ontap_rest_info - support added for protocols/ndmp/svms
  - na_ontap_rest_info - support added for protocols/nfs/connected-clients
  - na_ontap_rest_info - support added for protocols/nfs/export-policies/rules (Requires owning_resource to be set)
  - na_ontap_rest_info - support added for protocols/nfs/kerberos/interfaces
  - na_ontap_rest_info - support added for protocols/nvme/subsystem-controllers
  - na_ontap_rest_info - support added for protocols/nvme/subsystem-maps
  - na_ontap_rest_info - support added for protocols/s3/buckets
  - na_ontap_rest_info - support added for protocols/s3/services
  - na_ontap_rest_info - support added for protocols/san/iscsi/sessions
  - na_ontap_rest_info - support added for protocols/san/portsets
  - na_ontap_rest_info - support added for protocols/san/vvol-bindings
  - na_ontap_rest_info - support added for security/anti-ransomware/suspects
  - na_ontap_rest_info - support added for security/audit
  - na_ontap_rest_info - support added for security/audit/messages
  - na_ontap_rest_info - support added for security/authentication/cluster/ad-proxy
  - na_ontap_rest_info - support added for security/authentication/cluster/ldap
  - na_ontap_rest_info - support added for security/authentication/cluster/nis
  - na_ontap_rest_info - support added for security/authentication/cluster/saml-sp
  - na_ontap_rest_info - support added for security/authentication/publickeys
  - na_ontap_rest_info - support added for security/azure-key-vaults
  - na_ontap_rest_info - support added for security/certificates
  - na_ontap_rest_info - support added for security/gcp-kms
  - na_ontap_rest_info - support added for security/ipsec
  - na_ontap_rest_info - support added for security/ipsec/ca-certificates
  - na_ontap_rest_info - support added for security/ipsec/policies
  - na_ontap_rest_info - support added for security/ipsec/security-associations
  - na_ontap_rest_info - support added for security/key-manager-configs
  - na_ontap_rest_info - support added for security/key-managers
  - na_ontap_rest_info - support added for security/key-stores
  - na_ontap_rest_info - support added for security/login/messages
  - na_ontap_rest_info - support added for security/ssh
  - na_ontap_rest_info - support added for security/ssh/svms
  - na_ontap_rest_info - support added for storage/cluster
  - na_ontap_rest_info - support added for storage/file/clone/split-loads
  - na_ontap_rest_info - support added for storage/file/clone/split-status
  - na_ontap_rest_info - support added for storage/file/clone/tokens
  - na_ontap_rest_info - support added for storage/monitored-files
  - na_ontap_rest_info - support added for storage/qos/workloads
  - na_ontap_rest_info - support added for storage/snaplock/audit-logs
  - na_ontap_rest_info - support added for storage/snaplock/compliance-clocks
  - na_ontap_rest_info - support added for storage/snaplock/event-retention/operations
  - na_ontap_rest_info - support added for storage/snaplock/event-retention/policies
  - na_ontap_rest_info - support added for storage/snaplock/file-fingerprints
  - na_ontap_rest_info - support added for storage/snaplock/litigations
  - na_ontap_rest_info - support added for storage/switches
  - na_ontap_rest_info - support added for storage/tape-devices
  - na_ontap_rest_info - support added for storage/volumes/snapshots (Requires owning_resource to be set)
  - na_ontap_rest_info - support added for support/auto-update
  - na_ontap_rest_info - support added for support/auto-update/configurations
  - na_ontap_rest_info - support added for support/auto-update/updates
  - na_ontap_rest_info - support added for support/configuration-backup
  - na_ontap_rest_info - support added for support/configuration-backup/backups
  - na_ontap_rest_info - support added for support/coredump/coredumps
  - na_ontap_rest_info - support added for support/ems/messages
  - na_ontap_rest_info - support added for support/snmp
  - na_ontap_rest_info - support added for support/snmp/users
  - na_ontap_rest_info - support added for svm/migrations

### Added REST support to existing modules
  - na_ontap_igroup_initiator - Added REST support.
  - na_ontap_iscsi - Added REST support.
  - na_ontap_nvme - Added REST support.
  - na_ontap_qos_policy_group - Added REST support.


## 21.18.1

### Bug Fixes
  - na_ontap_iscsi - fixed error starting iscsi service on vserver where Service, adapter, or operation already started.
  - na_ontap_lun - Fixed KeyError on options `force_resize`, `force_remove` and `force_remove_fenced` in ZAPI.
  - na_ontap_lun - Fixed `force_remove` option silently ignored in REST.
  - na_ontap_snapshot_policy - Don't validate parameter when state is `absent` and fix KeyError on `comment`.

## 21.18.0

### New Options
  - na_ontap_export_policy_rule - new option `ntfs_unix_security` for NTFS export UNIX security options added.
  - na_ontap_volume - add support for SnapLock - only for REST.
  - na_ontap_volume - new option `max_files` to increase the inode count value.

### Minor Changes
  - na_ontap_cluster_config role - use na_ontap_login_messages as na_ontap_motd is deprecated.
  - na_ontap_debug - report ansible version and ONTAP collection version.
  - na_ontap_snapmirror -- Added more descriptive error messages for REST
  - na_ontap_svm - add support for web services (ssl modify) - REST only with 9.8 or later.
  - na_ontap_volume - allow to modify volume after rename.
  - na_ontap_vserver_create role - support max_volumes option.

### Bug Fixes
  - na_ontap_aggregate - Fixed error in delete aggregate if the `disk_count` is less than current disk count.
  - na_ontap_autosupport - Fixed `partner_address` not working in REST.
  - na_ontap_command - document that a READONLY user is not supported, even for show commands.
  - na_ontap_disk_options - ONTAP 9.10.1 returns on/off rather than True/False.
  - na_ontap_info - [#54] Fixes issue with na_ontap_info failing in 9.1 because of `job-schedule-cluster`.
  - na_ontap_iscsi - Fixed issue with `start_state` always being set to stopped when creating an ISCSI.
  - na_ontap_qtree - Fixed issue with `oplocks` not being changed during a modify in ZAPI.
  - na_ontap_qtree - Fixed issue with `oplocks` not warning user about not being supported in REST.
  - na_ontap_snapshot - fix key error on volume when using REST.
  - na_ontap_snapshot - add error message if volume is not found with REST.
  - na_ontap_svm - fixed KeyError issue on protocols when vserver is stopped.
  - na_ontap_volume - fix idempotency issue with compression settings when using REST.
  - na_ontap_volume - do not attempt to mount volume if current state is offline.
  - na_ontap_vserver_peer - Fixed AttributeError if `dest_hostname` or `peer_options` not present.
  - na_ontap_vserver_peer - Fixed `local_name_for_peer` and `local_name_for_source` options silently ignored in REST.
  - na_ontap_vserver_peer - Added cluster peer accept code in REST.
  - na_ontap_vserver_peer - Get peer cluster name if remote peer exist else use local cluster name.
  - na_ontap_vserver_peer - ignore job entry doesn't exist error with REST to bypass ONTAP issue with FSx.
  - na_ontap_vserver_peer - report error if SVM peer does not see a peering relationship after create.
  - Fixed ONTAP minor version ignored in checking minimum ONTAP version.

### Added REST support to existing modules
  - na_ontap_efficiency_policy - Added REST support.
  - na_ontap_lun - Added Rest Support.
  - na_ontap_snapshot_policy - Added Rest Support.

## 21.17.3

### Bug Fixes
  - na_ontap_lun_map - TypeError - '>' not supported between instances of 'int' and 'str '.
  - na_ontap_snapmirror - Fixed bug by adding use_rest condition for the REST support to work when `use_rest: always`.

## 21.17.2

### Bug Fixes
  - na_ontap_rest_info - Fixed an issue with adding field to specific info that didn't have a direct REST equivalent.
  - na_ontap_lun_map - Fixed bug when deleting lun map using REST.

## 21.17.1

### Bug Fixes
  - na_ontap_lun_map - fixed bugs resulting in REST support to not work.

## 21.17.0

### New Options
  - na_ontap_cifs_acl - new option `type` for user-group-type.

### Minor changes
  - all modules that only support ZAPI - warn when `use_rest: always` is ignored.

### Bug Fixes
  - na_ontap_aggregate - Fixed UUID issue when attempting to attach object store as part of creating the aggregate with REST.
  - na_ontap_cifs_server -  error out if ZAPI only options `force` or `workgroup` are used with REST.
  - na_ontap_cluster_peer - Fixed KeyError if both `source_intercluster_lifs` and `dest_intercluster_lifs` are not present in creating cluster.
  - na_ontap_rest_info - Fixed example with wrong indentation for `use_python_keys`.
  
### Added REST support to existing modules
  - na_ontap_cifs - Added REST support to the CIFS share module. 
  - na_ontap_cifs_acl - Added REST support to the cifs share access control module.
  - na_ontap_cluster_peer - Added REST support.
  - na_ontap_lun_map - Added REST support.
  - na_ontap_nfs - Added Rest Support.
  - na_ontap_volume_clone - Added REST support.

## 21.16.0

### New Options
  - na_ontap_aggregate - Added `disk_class` option for REST and ZAPI.
  - na_ontap_aggregate - Extended accepted `disk_type` values for ZAPI.
  - na_ontap_volume - `logical_space_enforcement` to specifies whether to perform logical space accounting on the volume.
  - na_ontap_volume - `logical_space_reporting` to specifies whether to report space logically on the volume.
  - na_ontap_volume - `tiering_minimum_cooling_days` to specify how many days must pass before inactive data in a volume using the Auto or Snapshot-Only policy is considered cold and eligible for tiering.

### Bug Fixes
  - na_ontap_active_directory - Fixed idempotency and traceback issues.
  - na_ontap_aggregate - Fixed KeyError on unmount_volumes when offlining a volume if option is not set.
  - na_ontap_aggregate - Report an error when attempting to change snaplock_type.
  - na_ontap_igroup - `force_remove_initiator` option was ignored when removing initiators from existing igroup.
  - na_ontap_info - Add active_directory_account_info.
  - na_ontap_security_certificates - `intermediate_certificates` option was ignored.
  - na_ontap_user - Fixed lock state is not set if password is not changed.
  - na_ontap_user - Fixed TypeError 'tuple' object does not support item assignment.
  - na_ontap_user - Fixed issue when attempting to change pasword for absent user when set_password is set.
  - na_ontap_volume - Report error when attempting to change the nas_application tiering control from disalllowed to required, or reciprocally.
  - na_ontap_volume - Fixed error with unmounting junction_path in rest.
  - na_ontap_volume - Fixed error when creating a flexGroup when `aggregate_name` and `aggr_list_multiplier` are not set in rest.
  - four modules (mediator, metrocluster, security_certificates, wwpn_alias) would report a None error when REST is not available.
  - module_utils - fixed KeyError on Allow when using OPTIONS method and the API failed.

### Added REST support to existing modules
  - na_ontap_aggregate - Added REST support.
  - na_ontap_cifs_server - Added REST support to the cifs server module.
  - na_ontap_ports - Added REST support to the ports module.
  - na_ontap_volume_clone -- Added REST support.

## 21.15.1

### Bug Fixes
  - na_ontap_export_policy_rule - Fixed bug that prevent ZAPI and REST calls from working correctly.

## 21.15.0

### New Options
  - na_ontap_broadcast_domain - new REST only option `from_ipspace` added.
  - na_ontap_svm - new REST options of svm admin_state `stopped` and `running` added.

### Bug Fixes
  - na_ontap_info - Fixed KeyError on node for aggr_efficiency_info option against a metrocluster system.
  - na_ontap_volume - Fixed issue that would fail the module in REST when changing `is_online` if two vserver volume had the same name.
  - na_ontap_volume_efficiency - Removed restriction on policy name.
  - na_ontap_broadcast_domain - fix idempotency issue when `ports` has identical values.

### Minor Changes
  - na_ontap_broadcast_domain_ports - warn about deprecation, fall back to ZAPI or fail when REST is desired.
  - na_ontap_rest_info - update documention for `fields` to clarify the list of fields that are return by default.
  - na_ontap_volume - If using REST and ONTAP 9.6 and `efficiency_policy` module will fail as `efficiency_policy` is not supported in ONTAP 9.6.

### Added REST support to existing modules
  - na_ontap_broadcast_domain - Added REST support to the broadcast domain module.
  - na_ontap_export_policy_rule -- Added Rest support for Export Policy Rules.
  - na_ontap_firmware_upgrade - REST support to download firmware and reboot SP.
  - na_ontap_license - Added REST support to the license module.
  - na_ontap_snapmirror - Added REST support to the na_ontap_snapmirror module.

## 21.14.1

### Bug Fixes
  - na_ontap_net_ifgrp - fix error in modify ports with zapi.

## 21.14.0

### New Options
  - na_ontap_aggregate - new option `encryption` to enable encryption with ZAPI.
  - na_ontap_net_ifgrp - new REST only options `from_lag_ports`, `broadcast_domain` and `ipspace` added.
  - na_ontap_restit - new option `wait_for_completion` to support asynchronous operations and wait for job completion.
  - na_ontap_volume_efficiency - new option `storage_efficiency_mode` for AFF only with 9.10.1 or later.

### Bug Fixes
  - na_ontap_cifs_local_user_modify - unexpected argument `name` error with REST.
  - na_ontap_cifs_local_user_modify - KeyError on `description` or `full_name` with REST.
  - na_ontap_export_policy - fix error if more than 1 verser matched search name, the wrong uuid could be given.
  - na_ontap_interface - fix error where module will fail for ONTAP 9.6 if use_rest: was set to auto.
  - na_ontap_net_routes - metric was not always modified with ZAPI.
  - na_ontap_net_routes - support cluster-scoped routes with REST.
  - na_ontap_vserver_delete role - report error if ONTAP version is 9.6 or older.
  
### Minor Changes
  - na_ontap_vserver_delete role - added set_fact to accept `netapp_{hostname|username|password}` or `hostname`, `username` and `password` variables.
  - na_ontap_vserver_delete role - do not report an error if the vserver does not exist.

### Added REST support to existing modules
  - na_ontap_fcp -- Added REST support for FCP.
  - na_ontap_net_ifgrp - Added REST support to the net ifgrp module.
  - na_ontap_net_port - Added REST support to the net port module.
  - na_ontap_volume - Added REST support to the volume module.
  - na_ontap_vserver_peer - Added REST support to the vserver_peer module.

## 21.13.1

### Bug Fixes
  - cluster scoped modules are failing on FSx with 'Vserver API missing vserver parameter' error.

## 21.13.0

### Minor Changes
  - na_ontap_object_store: support modifying an object store config with REST.
  - PR15 - allow usage of Ansible module group defaults - for Ansible 2.12+.

### New Options
  - na_ontap_cluster - add `force` option when deleting a node.
  - na_ontap_object_store: new REST options `owner` and `change_password`.
  - na_ontap_net_vlan - new options `broadcast_domain`, `ipspace` and `enabled` when using REST.

### Bug Fixes
  - na_ontap_cluster - `single_node_cluster` was silently ignored with REST.
  - na_ontap_cluster - switch to ZAPI when DELETE is required with ONTAP 9.6.
  - na_ontap_snapshot - `expiry_time` required REST api, will return error if set when using ZAPI.
  - na_ontap_snapshot - `snapmirror_label` is supported with REST on ONTAP 9.7 or higher, report error if used on ONTAP 9.6.
  - na_ontap_snapmirror - `source_path` and `source_hostname` parameters are not mandatory to delete snapmirror relationship when source cluster is unknown, if specified it will delete snapmirror at destination and release the same at source side.  if not, it only deletes the snapmirror at destination and will not look for source to perform snapmirror release.
  - na_ontap_snapmirror - modify policy, schedule and other parameter failure are fixed.
  - na_ontap_svm - module will on init if a rest only and zapi only option are used at the same time. 
  - na_ontap_storage_failover - KeyError on 'ha' if the system is not configured as HA.

### Added REST support to existing modules
  - na_ontap_interface - Added REST support to the interface module (for IP and FC interfaces).
  - na_ontap_net_vlan - Added REST support to the net vlan module.

## 21.12.0

### Minor Changes
  - na_ontap_firewall_policy - added `none` as a choice for `service` which is supported from 9.8 ONTAP onwards.

### New Options
  - na_ontap_svm - new option `max_volumes`.

### Bug Fixes
  - na_ontap_job_schedule - fix idempotency issue with ZAPI when job_minutes is set to -1.
  - na_ontap_job_schedule - cannot modify options not present in create when using REST.
  - na_ontap_job_schedule - modify error if month is present but not changed with 0 offset when using REST.
  - na_ontap_job_schedule - modify error if month is changed from some values to all (-1) when using REST.
  - na_ontap_svm - support `allowed protocols` with REST for ONTAP 9.6 and later.
  - na_ontap_vserver_delete role - fix typos for cifs.

### Added REST support to existing modules
  - na_ontap_cluster - Added REST support to the cluster module.

## 21.11.0

### New Options
  - na_ontap_interface - new option `from_name` to rename an interface.
  - na_ontap_software_update - new option `validate_after_download` to run ONTAP software update validation checks.
  - na_ontap_svm - new option `services` to allow and/or enable protocol services when using REST.
  - na_ontap_svm - new option `ignore_rest_unsupported_options` to ignore older ZAPI options not available in REST.

### Minor Changes
  - na_ontap_software_update - remove `absent` as a choice for `state` as it has no use.
  - na_ontap_svm - ignore `aggr_list: '*'` when using REST.
  
### Bug Fixes
  - na_ontap_job_schedule - fix idempotency issue with REST when job_minutes is set to -1.
  - na_ontap_ldap_client - remove limitation on schema so that custom schemas can be used.

### Added REST support to existing modules
  - na_ontap_ntp - Added REST support to the ntp module.

## 21.10.0

### Minor Changes
  - na_ontap_cifs_server - `force` option is supported when state is absent to ignore communication errors.

### Bug Fixes
  - na_ontap_vserver_delete role - delete iSCSI igroups and CIFS server before deleting vserver.
  - all modules - traceback on ONTAP 9.3 (and earlier) when trying to detect REST support.


## 21.9.0

### Minor Changes
  - na_ontap_rest_info - The Default for `gather_subset` has been changed to demo which returns `cluster/software`, `svm/svms`, `cluster/nodes`. To return all Info must specifically list `all` in your playbook. Do note `all` is a very resource-intensive action and it is highly recommended to call just the info/APIs you need.
  - na_ontap_rest_info -  added file_directory_security to return the effective permissions of the directory. When using file_directory_security it must be called with gather_subsets and path and vserver must be specified in parameters.

### New Options
  - na_ontap_job_schedule - new option `month_offset` to explictly select 0 or 1 for January.
  - na_ontap_object_store - new options `port`, `certificate_validation_enabled`, `ssl_enabled` for target server.
  - na_ontap_rest_info - new option `use_python_keys` to replace `svm/svms` with `svm_svms` to simplify post processing.

### Added REST support to existing modules
  - na_ontap_snmp - Added REST support to the SNMP module
  - na_ontap_rest_info - All Info that exist in `na_ontap_info` that has REST equivalents have been implemented. Note that the returned structure for REST and the variable names in the structure is different from the ZAPI based `na_ontap_info`. Some default variables in ZAPI are no longer returned by default in REST and will need to be specified using the `field` option
  - na_ontap_rest_info - The following info's have been added `system_node_info`, `net_interface_info`, `net_port_info`, `security_login_account_info`, `vserver_peer_info`, `cluster_image_info`, `cluster_log_forwarding_info`, `metrocluster_info`, `metrocluster_node_info`, `net_dns_info`, `net_interface_service_policy_info`, `vserver_nfs_info`, `clock_info`, `igroup_info`, `vscan_status_info`, `vscan_connection_status_all_info`, `storage_bridge_info`, `nvme_info`, `nvme_interface_info`, `nvme_subsystem_info`, `cluster_switch_info`, `export_policy_info`, `kerberos_realm_info`,`sis_info`, `sis_policy_info`, `snapmirror_info`, `snapmirror_destination_info`, `snapmirror_policy_info`, `sys_cluster_alerts`, `cifs_vserver_security_info`

### Bug Fixes
  - na_ontap_job_schedule - fix documentation for REST ranges for months.
  - na_ontap_quotas - attempt a retry on `13001:success` ZAPI error.  Add debug data.
  - na_ontap_object_store - when using REST, wait for job status to correctly report errors.
  - na_ontap_rest_cli - removed incorrect statement indicating that console access is required.

## 21.8.1

### Bug Fixes
  - all REST modules: 9.4 and 9.5 were incorrectly detected as supporting REST.
  - na_ontap_snapmirror: improve error message when option is not supported with ZAPI.

## 21.8.0

### New Modules
  - na_ontap_cifs_local_user_set_password - set local user password - ZAPI only.
  - na_ontap_fdsd - add or remove File Directory Security Descriptor - REST only.
  - na_ontap_fdsp - create or delete a File Directory Security Policy - REST only.
  - na_ontap_fdspt - add, remove or modify a File Directory Security Policy Task - REST only.
  - na_ontap_fdss - apply security policy settings to files and directories in a vserver.
  - na_ontap_partitions - assign/unassign disk partitions - REST only.

### New role
  - na_ontap_vserver_delete - delete vserver and all associated data and resources - REST only.

### New Options
  - na_ontap_cluster_peer - new option `peer_options` to use different credentials on peer.
  - na_ontap_net_port - new option `up_admin` to set administrative state.
  - na_ontap_snapshot - new option `expiry_time`.
  - na_ontap_vserver_peer - new option `peer_options` to use different credentials on peer.

### Added REST support to existing modules
  - na_ontap_snapshot - added REST support for snapshot creation, modification & deletion.

### Bug Fixes
  - na_ontap_cluster_peer - KeyError on dest_cluster_name if destination is unreachable.
  - na_ontap_cluster_peer - KeyError on username when using certicate.
  - na_ontap_export_policy_rule - change `anonymous_user_id` type to str to accept user name and user id.  (A warning is now triggered when a number is not quoted.)
  - na_ontap_vserver_peer - KeyError on username when using certicate.
  - na_ontap_volume_clone - `parent_vserver` can not be given with `junction_path`, `uid`, or `gid`
  - all modules - fix traceback TypeError 'NoneType' object is not subscriptable when hostname points to a web server.

### Minor Changes
  - na_ontap_debug - additional checks when REST is available to help debug vserver connectivity issues.
  - na_ontap_net_port - change option types to bool and int respectively for `autonegotiate_admin` and `mtu`.
  - na_ontap_rest_info - add examples for `parameters` option.
  - na_ontap_volume - show warning when resize is ignored because threshold is not reached.
    [WARNING]: resize request ignored: 2.5% is below the threshold: 10%
  - na_ontap_vserver_create role - add `nfsv3`, `nfsv4`, `nfsv41` options.
  - na_ontap_flexcache - corrected module name in documentation Examples

## 21.7.0

### New Modules
  - na_ontap_publickey - add/remove/modify public keys for SSH authentication - REST only.
  - na_ontap_service_policy - add/remove/modify service policies for IP interfaces - REST only.

### New Options
  - na_ontap_cifs - new option `comment` to associate a description to a CIFS share.
  - na_ontap_disks - new option `min_spares`.
  - na_ontap_lun - new suboption `exclude_aggregates` for SAN application.
  - na_ontap_volume - new suboption `exclude_aggregates` for NAS application.

### Minor Changes
  - na_ontap_disks - added REST support for the module.
  - na_ontap_disks - added functionality to reassign spare disks from a partner node to the desired node.
  - na_ontap_igroups - nested igroups are not supported on ONTAP 9.9.0 but are on 9.9.1.
  - License displayed correctly in Github

### Bug Fixes
  - na_ontap_iscsi_security - cannot change authentication_type
  - na_ontap_iscsi_security - IndexError list index out of range if vserver does not exist

## 21.6.1

### Bug Fixes
  - na_ontap_autosupport - KeyError: No element by given name validate-digital-certificate.
  - na_ontap_flexcache - one occurrence of msg missing in call to fail_json.
  - na_ontap_igroup - one occurrence of msg missing in call to fail_json.
  - na_ontap_lun - three occurrencse of msg missing in call to fail_json.
  - na_ontap_lun_map_reporting_nodes - one occurrence of msg missing in call to fail_json.
  - na_ontap_snapmirror - one occurrence of msg missing in call to fail_json.

## 21.6.0

### New Options
  - na_ontap_users - new option `application_dicts` to associate multiple authentication methods to an application.
  - na_ontap_users - new option `application_strs` to disambiguate `applications`.
  - na_ontap_users - new option `replace_existing_apps_and_methods`.
  - na_ontap_users - new suboption `second_authentication_method` with `application_dicts` option.
  - na_ontap_vserver_peer - new options `local_name_for_source` and `local_name_for_peer` added.

### Minor changes
  - na_ontap_rest_info - Added "autosupport_check_info"/"support/autosupport/check" to the attributes that will be collected when gathering info using the module.

### Bug Fixes
  - na_ontap_autosupport - TypeError - '>' not supported between instances of 'str' and 'list'.
  - na_ontap_quotas - fail to reinitialize on create if quota is already on.

## 21.5.0

### New Options
  - na_ontap_autosupport - new option 'nht_data_enabled' to specify whether the disk health data is collected as part of the AutoSupport data.
  - na_ontap_autosupport - new option 'perf_data_enabled' to specify whether the performance data is collected as part of the AutoSupport data.
  - na_ontap_autosupport - new option 'retry_count' to specify the maximum number of delivery attempts for an AutoSupport message.
  - na_ontap_autosupport - new option 'reminder_enabled' to specify whether AutoSupport reminders are enabled or disabled.
  - na_ontap_autosupport - new option 'max_http_size' to specify delivery size limit for the HTTP transport protocol (in bytes).
  - na_ontap_autosupport - new option 'max_smtp_size' to specify delivery size limit for the SMTP transport protocol (in bytes).
  - na_ontap_autosupport - new option 'private_data_removed' to specify the removal of customer-supplied data.
  - na_ontap_autosupport - new option 'local_collection_enabled' to specify whether collection of AutoSupport data when the AutoSupport daemon is disabled.
  - na_ontap_autosupport - new option 'ondemand_enabled' to specify whether the AutoSupport OnDemand Download feature is enabled.
  - na_ontap_autosupport - new option 'validate_digital_certificate' which when set to true each node will validate the digital certificates that it receives.

### Added REST support to existing modules
  - na_ontap_autosupport - added REST support for ONTAP autosupport modification.

### Bug Fixes
  - na_ontap_qtree - wait for completion when creating or modifying a qtree with REST.
  - na_ontap_volume - ignore read error because of insufficient privileges for efficiency options so that the module can be run as vsadmin.

### Minor changes
  - na_ontap_info - Added "autosupport_check_info" to the attributes that will be collected when gathering info using the module.

## 21.4.0

### New Modules
  - na_ontap_cifs_local_user_modify: Modify a local CIFS user.
  - na_ontap_disk_options: Modify storage disk options.
  - na_ontap_fpolicy_event: Create, delete or modify an FPolicy policy event.
  - na_ontap_fpolicy_ext_engine: Create, modify or delete an fPolicy External Engine.  
  - na_ontap_fpolicy_scope: Create, delete or modify an FPolicy policy scope.
  - na_ontap_fpolicy_status: Enable or disable an existing fPolicy policy.
  - na_ontap_snaplock_clock: Initialize snaplock compliance clock.

### New Options
  - na_ontap_igroups - new option `initiator_objects` to support initiator comments (requires ONTAP 9.9).
  - na_ontap_igroups - new option `initiator_names` as a replacement for `initiators` (still supported as an alias).

### Minor changes
  - na_ontap_lun - allow new LUNs to use different igroup or os_type when using SAN application.
  - na_ontap_lun - ignore small increase (lower than provisioned) and small decrease (< 10%) in `total_size`.
  - na_ontap_volume_efficiency - updated to now allow for storage efficiency start and storage efficiency stop.

### Bug fixes
  - na_ontap_autosupport - warn when password is present in `proxy_url` as it makes the operation not idempotent.
  - na_ontap_cluster - ignore ZAPI EMS log error when in pre-cluster mode.
  - na_ontap_lun - SAN application is not supported on 9.6 and only partially supported on 9.7 (no modify).
  - na_ontap_svm - iscsi current status is not read correctly (mispelled issi).
  - na_ontap_volume - warn when attempting to modify application only options.

## 21.3.1

### Bug fixes
  - na_ontap_snapmirror: check for consistency_group_volumes always fails on 9.7, and cluster or ipspace when using endpoints with ZAPI.

## 21.3.0

### New Modules
  - na_ontap_domain_tunnel: Create, delete or modify the domain tunnel.
  - na_ontap_storage_failover: Enables and disables storage failover.
  - na_ontap_security_config: Modify the security configuration for SSL.
  - na_ontap_storage_auto_giveback: Enables and disables storage auto giveback.
  - na_ontap_fpolicy_policy: Create, delete or modify an fpolicy policy

### New Options
  - na_ontap_flexcache - support for `prepopulate` option when using REST (requires ONTAP 9.8).
  - na_ontap_igroups - new option `igroups` to support nested igroups (requires ONTAP 9.9).
  - na_ontap_ldap_client - `tcp_port` replaces `port`.
  - na_ontap_volume - new suboption `dr_cache` when creating flexcache using NAS application template (requires ONTAP 9.9).

### Minor changes
  - na_ontap_debug - improve error reporting for import errors on netapp_lib.
  - na_ontap_flexcache - mount/unmount the FlexCache volume when using REST.
  - na_ontap_info - improve error reporting for import errors on netapp_lib, json, xlmtodict.

### Added REST support to existing modules
  - na_ontap_flexcache - added REST support for ONTAP FlexCache creation and deletion.
  - na_ontap_node - added REST support for Node modify and rename.
  - na_ontap_snapmirror - SVM scoped policies were not found when using a destination path with REST application.

### Bug fixes
  - na_ontap_ldap_client - `port` was incorrectly used instead of `tcp_port`.
  - na_ontap_motd - added warning for deprecated and to use na_ontap_login_messages module.
  - na_ontap_node - KeyError fix for location and asset-tag.
  - na_ontap_volume - changes in `encrypt` settings were ignored.
  - na_ontap_volume - unmount volume before deleting it when using REST.
  - na_ontap_volume_efficiency - `policy` updated to allow for supported '-' as a valid entry.
  - na_ontap_volume_efficiency - to allow for FAS ONTAP systems to enable volume efficiency.
  - na_ontap_volume_efficiency - to allow for FAS ONTAP systems to enable volume efficiency and apply parameters in one execution.

## 21.2.0

### New Modules
  - na_ontap_cifs_local_group_member: Add or remove CIFS local group member
  - na_ontap_volume_efficiency: Enables, disables or modifies volume efficiency
  - na_ontap_log_forward: Create, delete or modify the log forward configuration
  - na_ontap_lun_map_reporting_nodes: Add and remove lun map reporting nodes

### New Options
  - na_ontap_lun - new option `comment`.
  - na_ontap_lun - new option `qos_adaptive_policy_group`.
  - na_ontap_lun - new option `scope` to explicitly force operations on the SAN application or a single LUN.
  - na_ontap_node - added modify function for location and asset tag for node.
  - na_ontap_snapmirror - new options `source_endpoint` and `destination_endpoint` to group endpoint suboptions.
  - na_ontap_snapmirror - new suboptions `consistency_group_volumes` and `ipspace` to endpoint options.

### Minor changes
  - na_ontap_lun - convert existing LUNs and supporting volume to a smart container within a SAN application.
  - na_ontap_snapmirror - improve error reporting or warn when REST option is not supported.
  - na_ontap_snapmirror - deprecate older options for source and destination paths, volumes, vservers, and clusters.
  - na_ontap_snapmirror - report warning when relationship is present but not healthy.

### Bug fixes
  - na_ontap_igroup - report error when attempting to modify an option that cannot be changed.
  - na_ontap_lun - `qos_policy_group` could not be modified if a value was not provided at creation.
  - na_ontap_lun - `tiering` options were ignored in san_application_template.
  - na_ontap_volume - returns an error now if deleting a volume with REST api fails.
  - na_ontap_volume - report error from resize operation when using REST.

### Added REST support to existing modules
  - na_ontap_igroup - added REST support for ONTAP igroup creation, modification, and deletion.

## 21.1.1

### Bug fixes
  - All REST modules: ONTAP 9.4 and 9.5 are incorrectly detected as supporting REST with `use_rest: auto`.

## 21.1.0

### New Modules
  - na_ontap_debug: Diagnose netapp-lib import errors and provide useful information.

### New Options
  - na_ontap_cluster - `time_out` to wait for cluster creation, adding and removing a node.
  - na_ontap_debug - connection diagnostics added for invalid ipaddress and DNS hostname errors.
  - na_ontap_lun - `total_size` and `total_size_unit` when using SAN application template.
  - na_ontap_snapmirror - `create_destination` to automatically create destination endpoint (ONTAP 9.7).
  - na_ontap_snapmirror - `destination_cluster` to automatically create destination SVM for SVM DR (ONTAP 9.7).
  - na_ontap_snapmirror - `source_cluster` to automatically set SVM peering (ONTAP 9.7).

### Minor changes
  - na_ontap_firmware_upgrade - Added a new 'storage' type as default firmware_type.
  - na_ontap_info - deprecate `state` option.
  - na_ontap_lun - support increasing lun_count and total_size when using SAN application template.
  - na_ontap_quota - allow to turn quota on/off without providing quota_target or type.
  - na_ontap_rest_info - deprecate `state` option.
  - na_ontap_snapmirror - use REST API for create action if target supports it.  (ZAPIs are still used for all other actions).
  - na_ontap_volume - use REST API for delete operation if targets supports it.
  - general - improve error reporting when older version of netapp-lib is used.

### Bug fixes
  - na_ontap_lun - REST expects 'all' for tiering policy and not 'backup'.
  - na_ontap_quotas - Handle blank string idempotency issue for `quota_target` in quotas module.
  - na_ontap_rest_info - `changed` was set to "False" rather than boolean False.
  - na_ontap_snapmirror - report error when attempting to change relationship_type.
  - na_ontap_snapmirror - fix job update failures for load_sharing mirrors.
  - na_ontap_snapmirror - wait up to 5 minutes for abort to complete before issuing a delete.
  - na_ontap_snmp - SNMP module wrong access_control issue and error handling fix.
  - na_ontap_volume - REST expects 'all' for tiering policy and not 'backup'.
  - na_ontap_volume - detect and report error when attempting to change FlexVol into FlexGroup.
  - na_ontap_volume - report error if `aggregate_name` option is used with a FlexGroup.

## 20.12.0

### New Options
  - na_ontap_igroup - new option `os_type` to replace `ostype` (but ostype is still accepted).
  - na_ontap_info - new fact: cifs_options_info.
  - na_ontap_info - new fact: cluster_log_forwarding_info.
  - na_ontap_info - new fact: event_notification_destination_info.
  - na_ontap_info - new fact: event_notification_info.
  - na_ontap_info - new fact: security_login_role_config_info.
  - na_ontap_info - new fact: security_login_role_info.
  - na_ontap_lun - new option `from_name` to rename a LUN.
  - na_ontap_lun - new option `os_type` to replace `ostype` (but ostype is still accepted), and removed default to `image`.
  - na_ontap_lun - new option `qos_policy_group` to assign a qos_policy_group to a LUN.
  - na_ontap_lun - new option `san_application_template` to create LUNs without explicitly creating a volume and using REST APIs.
  - na_ontap_qos_policy_group - new option `is_shared` for sharing QOS SLOs or not.
  - na_ontap_quota_policy - new option `auto_assign` to assign quota policy to vserver.
  - na_ontap_quotas - new option `activate_quota_on_change` to resize or reinitialize quotas.
  - na_ontap_quotas - new option `perform_user_mapping` to perform user mapping for the user specified in quota-target.
  - na_ontap_rest_info - Support for gather subsets: `cifs_home_directory_info, cluster_software_download, event_notification_info, event_notification_destination_info, security_login_info, security_login_rest_role_info`
  - na_ontap_svm - warning for `aggr_list` wildcard value(`*`) in create\modify idempotency.
  - na_ontap_volume - `compression` to enable compression on a FAS volume.
  - na_ontap_volume - `inline-compression` to enable inline compression on a volume.
  - na_ontap_volume - `nas_application_template` to create a volume using nas application REST API.
  - na_ontap_volume - `size_change_threshold` to ignore small changes in volume size.
  - na_ontap_volume - `sizing_method` to resize a FlexGroup using REST.

### Bug fixes
  - na_ontap_broadcast_domain_ports - properly report check_mode `changed`.
  - na_ontap_cifs - fix for AttributeError - 'NoneType' object has no attribute 'get' on line 300
  - na_ontap_user - application parameter expects only `service_processor` but module supports `service-processor`.
  - na_ontap_volume - change in volume type was ignored and now reporting an error.
  - na_ontap_volume - checking for success before failure lead to 'NoneType' object has no attribute 'get_child_by_name' when modifying a Flexcache volume.

## 20.11.0

### New Modules
  - na_ontap_metrocluster_dr_group: Configure a Metrocluster DR group (Supports ONTAP 9.8+)

### Minor changes
  - na_ontap_cifs - output `modified` if a modify action is taken.
  - na_ontap_cluster_peer: optional parameter 'ipspace' added for cluster peer.
  - na_ontap_info - do not require write access privileges.   This also enables other modules to work in check_mode without write access permissions.
  - na_ontap_lun - support modify for space_allocation and space_reserve.
  - na_ontap_mcc_mediator - improve error reporting when REST is not available.
  - na_ontap_metrocluster - improve error reporting when REST is not available.
  - na_ontap_wwpn_alias - improve error reporting when REST is not available.
  - na_ontap_software_update - add `force_update` option to ignore current version.
  - na_ontap_svm - output `modified` if a modify action is taken.
  - all ZAPI modules - optimize Basic Authentication by adding Authorization header proactively.
  - This can be disabled by setting the `classic_basic_authorization` feature_flag to True.

### Bug fixes
  - All REST modules, will not fail if a job fails
  - na_ontap_cifs - fix idempotency issue when `show-previous-versions` is used.
  - na_ontap_firmware_upgrade - fix ValueError issue when processing URL error.
  - na_ontap_info - Use `node-id` as key rather than `current-version`.
  - na_ontap_ipspace - invalid call in error reporting (double error).
  - na_ontap_lun - `use_exact_size` to create a lun with the exact given size so that the lun is not rounded up.
  - na_ontap_metrocluster: Fix issue where module would fail on waiting for rest api job
  - na_ontap_software_update - module is not idempotent.

## 20.10.0

### New Options
- na_ontap_rest_info: Support for gather subsets - `application_info, application_template_info, autosupport_config_info , autosupport_messages_history, ontap_system_version, storage_flexcaches_info, storage_flexcaches_origin_info, storage_ports_info, storage_qos_policies, storage_qtrees_config, storage_quota_reports, storage_quota_policy_rules, storage_shelves_config, storage_snapshot_policies, support_ems_config, support_ems_events, support_ems_filters`

### Bug fixes
- na_ontap_aggregate: support concurrent actions for rename/modify/add_object_store and create/add_object_store.
- na_ontap_cluster: `single_node_cluster` option was ignored.
- na_ontap_info: better reporting on KeyError traceback, option to ignore error.
- na_ontap_info: KeyError on `tree` for quota_report_info.
- na_ontap_snapmirror_policy: report error when attempting to change `policy_type` rather than taking no action.
- na_ontap_volume: `encrypt: false` is ignored when creating a volume.

## 20.9.0

### New Modules
- na_ontap_active_directory: configure active directory.
- na_ontap_mcc_mediator: Configure a MCC Mediator (Supports ONTAP 9.8+).
- na_ontap_metrocluster: Configure a metrocluster (Supports ONTAP 9.8+).

### New Options
- na_ontap_cluster: `node_name` to set the node name when adding a node, or as an alternative to `cluster_ip_address` to remove a node.
- na_ontap_cluster: `state` can be set to `absent` to remove a node identified with `cluster_ip_address` or `node_name`.
- na_ontap_qtree: `wait_for_completion` and `time_out` to wait for qtree deletion when using REST.
- na_ontap_quotas: `soft_disk_limit` and `soft_file_limit` for the quota target.
- na_ontap_rest_info: Support for gather subsets - `initiator_groups_info, san_fcp_services, san_iscsi_credentials, san_iscsi_services, san_lun_maps, storage_luns_info, storage_NVMe_namespaces.`

### Bug fixes
- na_ontap_cluster: `check_mode` is now working properly.
- na_ontap_interface: `home_node` is not required in pre-cluster mode.
- na_ontap_interface: `role` is not required if `service_policy` is present and ONTAP version is 9.8.
- na_ontap_interface: traceback in get_interface if node is not reachable.
- na_ontap_job_schedule: allow 'job_minutes' to set number to -1 for job creation with REST too.
- na_ontap_qtree: fixed `None is not subscriptable` exception on rename operation.
- na_ontap_volume: fixed `KeyError` exception on `size` when reporting creation error.
- na_ontap_*: change version_added: '2.6' to version_added: 2.6.0 where applicable to satisfy sanity checker.
- netapp.py: uncaught exception (traceback) on zapi.NaApiError.

## 20.8.0

### New Modules
- na_ontap_file_directory_policy: create, modify, delete vserver security file directory policy/task.
- na_ontap_ssh_command: send CLI command over SSH using paramiko for corner cases where ZAPI or REST are not yet ready.
- na_ontap_wait_for_condition: wait for event to be present or absent (currently sp_upgrade/in_progress and sp_version).

### New Options
- na_ontap_aggregate: support `disk_size_with_unit` option.
- na_ontap_ldap_client: support `ad_domain` and `preferred_ad_server` options.
- na_ontap_rest_info: Support for gather subsets - `cloud_targets_info, cluster_chassis_info, cluster_jobs_info, cluster_metrics_info, cluster_schedules, broadcast_domains_info, cluster_software_history, cluster_software_packages, network_ports_info, ip_interfaces_info, ip_routes_info, ip_service_policies, network_ipspaces_info, san_fc_logins_info, san_fc_wppn-aliases, svm_dns_config_info, svm_ldap_config_info, svm_name_mapping_config_info, svm_nis_config_info, svm_peers_info, svm_peer-permissions_info`.
- na_ontap_rest_info: Support for gather subsets for 9.8+ - `cluster_metrocluster_diagnostics.
- na_ontap_qtree: `force_delete` option with a DEFAULT of `true` so that ZAPI behavior is aligned with REST.
- na_ontap_security_certificates:`ignore_name_if_not_supported` option to not fail if `name` is present since `name` is not supported in ONTAP 9.6 and 9.7.
- na_ontap_software_update: added `timeout` option to give enough time for the update to complete.

### Bug fixes
- na_ontap_aggregate: `disk-info` error when using `disks` option.
- na_ontap_autosupport_invoke: `message` has changed to `autosupport_message` as Redhat has reserved this word. `message` has been alias'd to `autosupport_message`.
- na_ontap_cifs_vserver: fix documentation and add more examples.
- na_ontap_cluster: module was not idempotent when changing location or contact information.
- na_ontap_igroup: idempotency issue when using uppercase hex digits (A, B, C, D, E, F) in WWN (ONTAP uses lowercase).
- na_ontap_igroup_initiator: idempotency issue when using uppercase hex digits (A, B, C, D, E, F) in WWN (ONTAP uses lowercase).
- na_ontap_security_certificates: allows (`common_name`, `type`) as an alternate key since `name` is not supported in ONTAP 9.6 and 9.7.
- na_ontap_info: Fixed error causing module to fail on `metrocluster_check_info`, `env_sensors_info` and `volume_move_target_aggr_info`.
- na_ontap_snapmirror: fixed KeyError when accessing `relationship_type` parameter.
- na_ontap_snapmirror_policy: fixed a race condition when creating a new policy.
- na_ontap_snapmirror_policy: fixed idempotency issue withis_network_compression_enabled for REST.
- na_ontap_software_update: ignore connection errors during update as nodes cannot be reachable.
- na_ontap_user: enable lock state and password to be set in the same task for existing user.
- na_ontap_volume: issue when snapdir_access and atime_update not passed together.
- na_ontap_vscan_on_access_policy: `bool` type was not properly set for `scan_files_with_no_ext`.
- na_ontap_vscan_on_access_policy: `policy_status` enable/disable option was not supported.
- na_ontap_vscan_on_demand_task: `file_ext_to_include` was not handled properly.
- na_ontap_vscan_scanner_pool_policy: scanner_pool apply policy support on modification.
- na_ontap_vserver_create(role): lif creation now defaults to system-defined unless iscsi lif type.
- use_rest supports case insensitive.

### Module documentation changes
- use a three group format for `version_added`.  So 2.7 becomes 2.7.0.  Same thing for 2.8 and 2.9.
- add `type:` and `elements:` information where missing.
- update `required:` information.

## 20.7.0

### New Modules
- na_ontap_security_certificates: Install, create, sign, delete security certificates.

### New Options:
- na_ontap_info: support `continue_on_error` option to continue when a ZAPI is not supported on a vserver, or for cluster RPC errors.
- na_ontap_info: support `query` option to specify which objects to return.
- na_ontap_info: support `vserver` tunneling to limit output to one vserver.
- na_ontap_snapmirror_policy: support for SnapMirror policy rules.
- na_ontap_vscan_scanner_pool: support modification.
- na_ontap_rest_info: Support for gather subsets - `cluster_node_info, cluster_peer_info, disk_info, cifs_services_info, cifs_share_info`.
- module_utils/netapp: add retry on wait_on_job when job failed. Abort 3 consecutive errors.

### Bug fixes:
- na_ontap_command: replace invalid backspace characters (0x08) with '.'.
- na_ontap_firmware_download: exception on PCDATA if ONTAP returns a BEL (0x07) character.
- na_ontap_info: lists were incorrectly processed in convert_keys, returning {}.
- na_ontap_info: qtree_info is missing most entries.  Changed key from `vserver:id` to `vserver:volume:id` .
- na_ontap_iscsi_security: adding no_log for password parameters.
- na_ontap_portset: adding explicit error message as modify portset is not supported.
- na_ontap_snapmirror: fixed snapmirror delete for loadsharing to not go to quiesce state for the rest of the set.
- na_ontap_ucadapter: fixed KeyError if type is not provided and mode is 'cna'.
- na_ontap_user: checked `applications` does not contain snmp when using REST API call.
- na_ontap_user: fixed KeyError if locked key not set with REST API call.
- na_ontap_user: fixed KeyError if vserver: is empty with REST API call (useful to indicate cluster scope).
- na_ontap_volume: fixed KeyError when getting info on a MVD volume

### Example playbook
- na_ontap_pb_get_online_volumes.yml: list of volumes that are online (or offline).
- na_ontap_pb_install_SSL_certificate_REST.yml: installing SSL certificate using REST APIs.

## 20.6.1

### New Options:
- na_ontap_firmware_upgrade: `reboot_sp`: reboot service processor before downloading package.
- na_ontap_firmware_upgrade: `rename_package`: rename file when downloading service processor package.
- na_ontap_firmware_upgrade: `replace_package`: replace local file when downloading service processor package.

### Bug Fixes
- na_ontap_firmware_upgrade: images are not downloaded, but the module reports success.
- na_ontap_user: fixed KeyError if password is not provided.
- na_ontap_password: do not error out if password is identical to previous password (idempotency).

## 20.6.0

### Support for SSL certificate authentication in addition to password
The ONTAP Ansible modules currently require a username/password combination to authenticate with ONTAPI or REST APIs.
It is now possible to use SSL certificate authentication with ONTAPI or REST.
You will first need to install a SSL certificate in ONTAP, see for instance the first part of:
https://netapp.io/2016/11/08/certificate-based-authentication-netapp-manageability-sdk-ontap/
The applications that need to be authorized for `cert` are `ontapi` and `http`.

The new `cert_filepath`, `key_filepath` options enable SSL certificate authentication.
This is mutually exclusive with using `username` and `password`.

ONTAP does not support `cert` authentication for console, so this is not supported for `na_ontap_command`.

SSL certificate authentication requires python2.7 or 3.x.

### New Options
- na_ontap_disks: `disk_type` option allows to assign specified type of disk.
- na_ontap_firmware_upgrade: ignore timeout when downloading image unless `fail_on_502_error` is set to true.
- na_ontap_info: `desired_attributes` advanced feature to select which fields to return.
- na_ontap_info: `use_native_zapi_tags` to disable the conversion of '_' to '-' for attribute keys.
- na_ontap_rest_info: `fields` options to request specific fields from subset.
- na_ontap_software_update: `stabilize_minutes` option specifies number of minutes needed to stabilize node before update.
- na_ontap_snapmirror: now performs restore with optional field `source_snapshot` for specific snapshot or uses latest.
- na_ontap_ucadapter: `pair_adapters` option allows specifying the list of adapters which also need to be offline.
- na_ontap_user: `authentication_password` option specifies password for the authentication protocol of SNMPv3 user.
- na_ontap_user: `authentication_protocol` option specifies authentication protocol fo SNMPv3 user.
- na_ontap_user: `engine_id` option specifies authoritative entity's EngineID for the SNMPv3 user.
- na_ontap_user: `privacy_password` option specifies password for the privacy protocol of SNMPv3 user.
- na_ontap_user: `privacy_protocol` option specifies privacy protocol of SNMPv3 user.
- na_ontap_user: `remote_switch_ipaddress` option specifies the IP Address of the remote switch of SNMPv3 user.
- na_ontap_volume: `check_interval` option checks if a volume move has been completed and then waits this number of seconds before checking again.
- na_ontap_volume: `auto_remap_luns` option controls automatic mapping of LUNs during volume rehost.
- na_ontap_volume: `force_restore` option forces volume to restore even if the volume has one or more newer Snapshotcopies.
- na_ontap_volume: `force_unmap_luns` option controls automatic unmapping of LUNs during volume rehost.
- na_ontap_volume: `from_vserver` option allows volume rehost from one vserver to another.
- na_ontap_volume: `preserve_lun_ids` option controls LUNs in the volume being restored will remain mapped and their identities preserved.
- na_ontap_volume: `snapshot_restore` option specifies name of snapshot to restore from.
- all modules: `cert_filepath`, `key_filepath` to enable SSL certificate authentication (python 2.7 or 3.x).

### Bug Fixes
- na_ontap_firmware_upgrade: ignore timeout when downloading firmware images by default.
- na_ontap_info: conversion from '-' to '_' was not done for lists of dictionaries.
- na_ontap_ntfs_dacl: example fix in documentation string.
- na_ontap_snapmirror: could not delete all rules (bug in netapp_module).
- na_ontap_volume: modify was invoked multiple times when once is enough.
- na_ontap_volume: fix KeyError on 'style' when volume is of type: data-protection.
- na_ontap_volume: `wait_on_completion` is supported with volume moves.
- module_utils/netapp_module: cater for empty lists in get_modified_attributes().
- module_utils/netapp_module: cater for lists with duplicate elements in compare_lists().

### Example playbook
- na_ontap_pb_install_SSL_certificate.yml: installing a self-signed SSL certificate, and enabling SSL certificate authentication.

### Added REST support to existing modules
- na_ontap_user: added REST support for ONTAP user creation, modification & deletion.


## 20.5.0

### New Options:
- na_ontap_aggregate: `raid_type` options supports 'raid_0' for ONTAP Select.
- na_ontap_cluster_peer: `encryption_protocol_proposed` option allows specifying encryption protocol to be used for inter-cluster communication.
- na_ontap_info: new fact: aggr_efficiency_info.
- na_ontap_info: new fact: cluster_switch_info.
- na_ontap_info: new fact: disk_info.
- na_ontap_info: new fact: env_sensors_info.
- na_ontap_info: new fact: net_dev_discovery_info.
- na_ontap_info: new fact: service_processor_info.
- na_ontap_info: new fact: shelf_info.
- na_ontap_info: new fact: sis_info.
- na_ontap_info: new fact: subsys_health_info.
- na_ontap_info: new fact: sysconfig_info.
- na_ontap_info: new fact: sys_cluster_alerts.
- na_ontap_info: new fact: volume_move_target_aggr_info.
- na_ontap_info: new fact: volume_space_info.
- na_ontap_nvme_namespace: `block_size` option allows specifying size in bytes of a logical block.
- na_ontap_snapmirror: snapmirror now allows resume feature.
- na_ontap_volume: `cutover_action` option allows specifying the action to be taken for cutover.

### Bug Fixes
- REST API call now honors the `http_port` parameter.
- REST API detection now works with vserver (use_rest: Auto).
- na_ontap_autosupport_invoke: when using ZAPI and name is not given, send autosupport message to all nodes in the cluster.
- na_ontap_cg_snapshot: properly states it does not support check_mode.
- na_ontap_cluster: ONTAP 9.3 or earlier does not support ZAPI element single-node-cluster.
- na_ontap_cluster_ha: support check_mode.
- na_ontap_cluster_peer: support check_mode.
- na_ontap_cluster_peer: EMS log wrongly uses destination credentials with source hostname.
- na_ontap_disks: support check_mode.
- na_ontap_dns: support check_mode.
- na_ontap_efficiency_policy: change `duration` type from int to str to support '-' input.
- na_ontap_fcp: support check_mode.
- na_ontap_flexcache: support check_mode.
- na_ontap_info: `metrocluster_check_info` does not trigger a traceback but adds an "error" info element if the target system is not set up for metrocluster.
- na_ontap_license: support check_mode.
- na_ontap_login_messages: fix documentation link.
- na_ontap_node: support check mode.
- na_ontap_ntfs_sd: documentation string update for examples and made sure owner or group not mandatory.
- na_ontap_ports: now support check mode.
- na_ontap_restit: error can be a string in addition to a dict.  This fix removes a traceback with AttributeError.
- na_ontap_routes: support Check Mode correctly.
- na_ontap_snapmirror: support check_mode.
- na_ontap_software_update: Incorrectly stated that it support check mode, it does not.
- na_ontap_svm_options: support check_mode.
- na_ontap_volume: improve error reporting if required parameter is present but not set.
- na_ontap_volume: suppress traceback in wait_for_completion as volume may not be completely ready.
- na_ontap_volume: fix KeyError on 'style' when volume is offline.
- na_ontap_volume_autosize: Support check_mode when `reset` option is given.
- na_ontap_volume_snaplock: fix documentation link.
- na_ontap_vserver_peer: support check_mode.
- na_ontap_vserver_peer: EMS log wrongly uses destination credentials with source hostname.

### New Modules
- na_ontap_rest_info: Gather ONTAP subset information using REST APIs (9.6 and Above).

### Role Change
- na_ontap_cluster_config: Port Flowcontrol and autonegotiate can be set in role

## 20.4.1

### New Options
- na_ontap_firmware_upgrade: `force_disruptive_update` and `package_url` options allows to make choices for download and upgrading packages.

### Added REST support to existing modules
- na_ontap_autosupport_invoke: added REST support for sending autosupport message.

### Bug Fixes
- na_ontap_volume: `volume_security_style` option now allows modify.
- na_ontap_info: `metrocluster_check_info` has been removed as it was breaking the info module for everyone who didn't have a metrocluster set up. We are working on adding this back in a future update

### Role Changes
- na_ontap_vserver_create has a new default variable `netapp_version` set to 140.  If you are running 9.2 or below please add the variable to your playbook and set to 120

## 20.4.0

### New Options
- na_ontap_aggregate: `disk_count` option allows adding additional disk to aggregate.
- na_ontap_info: `max_records` option specifies maximum number of records returned in a single ZAPI call.
- na_ontap_info: `summary` option specifies a boolean flag to control return all or none of the info attributes.
- na_ontap_info: new fact: iscsi_service_info.
- na_ontap_info: new fact: license_info.
- na_ontap_info: new fact: metrocluster_info.
- na_ontap_info: new fact: metrocluster_check_info.
- na_ontap_info: new fact: metrocluster_node_info.
- na_ontap_info: new fact: net_interface_service_policy_info.
- na_ontap_info: new fact: ontap_system_version.
- na_ontap_info: new fact: ontapi_version (and deprecate ontap_version, both fields are reported for now).
- na_ontap_info: new fact: qtree_info.
- na_ontap_info: new fact: quota_report_info.
- na_ontap_info: new fact: snapmirror_destination_info.
- na_ontap_interface: `service_policy` option to identify a single service or a list of services that will use a LIF.
- na_ontap_kerberos_realm: `ad_server_ip` option specifies IP Address of the Active Directory Domain Controller (DC).
- na_ontap_kerberos_realm: `ad_server_name` option specifies Host name of the Active Directory Domain Controller (DC).
- na_ontap_snapmirror_policy: REST is included and all defaults are removed from options.
- na_ontap_snapmirror: `relationship-info-only` option allows to manage relationship information.
- na_ontap_software_update: `download_only` options allows to download cluster image without software update.
- na_ontap_volume: `snapshot_auto_delete` option allows to manage auto delete settings of a specified volume.

### Bug Fixes
- na_ontap_cifs_server: delete AD account if username and password are provided when state=absent
- na_ontap_info: return all records of each gathered subset.
- na_ontap_info: cifs_server_info: fix KeyError exception on `domain` if only `domain-workgroup` is present.
- na_ontap_iscsi_security: Fixed modify functionality for CHAP and typo correction
- na_ontap_kerberos_realm: fix `kdc_vendor` case sensitivity issue.
- na_ontap_snapmirror: calling quiesce before snapmirror break.

### New Modules
- na_ontap_autosupport_invoke: send autosupport message.
- na_ontap_ntfs_dacl: create/modify/delete ntfs dacl (discretionary access control list).
- na_ontap_ntfs_sd: create/modify/delete ntfs security descriptor.
- na_ontap_restit: send any REST API request to ONTAP (9.6 and above).
- na_ontap_snmp_traphosts: Create and delete snmp traphosts (9.7 and Above)
- na_ontap_wwpn_alias: create/modify/delete vserver fcp wwpn-alias.
- na_ontap_zapit: send any ZAPI request to ONTAP.

## 20.3.0

### New Options
- na_ontap_info: New info's added `cluster_identity_info`
- na_ontap_info: New info's added `storage_bridge_info`
- na_ontap_snapmirror: performs resync when the `relationship_state` is active and the current state is broken-off.

### Bug Fixes
- na_ontap_vscan_scanner_pool: has been updated to match the standard format used for all other ontap modules
- na_ontap_volume_snaplock: Fixed KeyError exception on 'is-volume-append-mode-enabled'

### New Modules
- na_ontap_snapmirror_policy: create/modify/delete snapmirror policy.

## 20.2.0

### New Modules
- na_ontap_volume_snaplock: modify volume snaplock retention.

### New Options
- na_ontap_info: New info's added `snapshot_info`
- na_ontap_info: `max_records` option to set maximum number of records to return per subset.
- na_ontap_snapmirror: `relationship_state` option for breaking the snapmirror relationship.
- na_ontap_snapmirror: `update_snapmirror` option for updating the snapmirror relationship.
- na_ontap_volume_clone: `split` option to split clone volume from parent volume.

### Bug Fixes
- na_ontap_cifs_server: Fixed KeyError exception on 'cifs_server_name'
- na_ontap_command: fixed traceback when using return_dict if u'1' is present in result value.
- na_ontap_login_messages: Fixed example documentation and spelling mistake issue
- na_ontap_nvme_subsystem: fixed bug when creating subsystem, vserver was not filtered.
- na_ontap_svm: if snapshot policy is changed, modify fails with "Extra input: snapshot_policy"
- na_ontap_svm: if language: C.UTF-8 is specified, the module is not idempotent
- na_ontap_volume_clone: fixed 'Extra input: parent-vserver' error when running as cluster admin.
- na_ontap_qtree: Fixed issue with Get function for REST

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
