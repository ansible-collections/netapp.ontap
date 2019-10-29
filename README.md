=============================================================

 netapp.ontap

 NetApp ONTAP Collection

 Copyright (c) 2019 NetApp, Inc. All rights reserved.
 Specifications subject to change without notice.

=============================================================

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
- na_ontap_net_subnet: fix ip_ranges option fails on existing subnet.
- na_ontap_snapshot_policy: fix vsadmin approach for managing snapshot policy.
- na_ontap_nvme_subsystem: fix fetching unique nvme subsytem based on vserver filter.
- na ontap_net_routes: change metric type from string to int. 

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

