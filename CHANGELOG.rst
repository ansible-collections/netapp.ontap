=====================================
NetApp ONTAP Collection Release Notes
=====================================

.. contents:: Topics


v21.12.0
========

Minor Changes
-------------

- na_ontap_cluster - Added REST support to the cluster module.
- na_ontap_firewall_policy - added ``none`` as a choice for ``service`` which is supported from 9.8 ONTAP onwards.
- na_ontap_svm - new option ``max_volumes``.
- na_ontap_svm - support ``allowed protocols`` with REST for ONTAP 9.6 and later.

Bugfixes
--------

- na_ontap_job_schedule - cannot modify options not present in create when using REST.
- na_ontap_job_schedule - fix idempotency issue with ZAPI when job_minutes is set to -1.
- na_ontap_job_schedule - modify error if month is changed from some values to all (-1) when using REST.
- na_ontap_job_schedule - modify error if month is present but not changed with 0 offset when using REST.
- na_ontap_vserver_delete role - fix typos for cifs.

v21.11.0
========

Minor Changes
-------------

- na_ontap_interface - new option ``from_name`` to rename an interface.
- na_ontap_ntp - Added REST support to the ntp module
- na_ontap_ntp - Added REST support to the ntp module
- na_ontap_software_update - new option ``validate_after_download`` to run ONTAP software update validation checks.
- na_ontap_software_update - remove ``absent`` as a choice for ``state`` as it has no use.
- na_ontap_svm - ignore ``aggr_list`` with ``'*'`` when using REST.
- na_ontap_svm - new option ``ignore_rest_unsupported_options`` to ignore older ZAPI options not available in REST.
- na_ontap_svm - new option ``services`` to allow and/or enable protocol services.

Bugfixes
--------

- na_ontap_job_schedule - fix idempotency issue with REST when job_minutes is set to -1.
- na_ontap_ldap_client - remove limitation on schema so that custom schemas can be used.

v21.10.0
========

Minor Changes
-------------

- na_ontap_cifs_server - ``force`` option is supported when state is absent to ignore communication errors.

Bugfixes
--------

- all modules - traceback on ONTAP 9.3 (and earlier) when trying to detect REST support.
- na_ontap_vserver_delete role - delete iSCSI igroups and CIFS server before deleting vserver.

v21.9.0
=======

Minor Changes
-------------

- na_ontap_job_schedule - new option ``month_offset`` to explictly select 0 or 1 for January.
- na_ontap_object_store - new option ``port``, ``certificate_validation_enabled``, ``ssl_enabled`` for target server.
- na_ontap_rest_info - All Info that exist in ``na_ontap_info`` that has REST equivalents have been implemented. Note that the returned structure for REST and the variable names in the structure is different from the ZAPI based ``na_ontap_info``. Some default variables in ZAPI are no longer returned by default in REST and will need to be specified using the ``field`` option.
- na_ontap_rest_info - The Default for ``gather_subset`` has been changed to demo which returns ``cluster/software``, ``svm/svms``, ``cluster/nodes``. To return all Info must specificly list ``all`` in your playbook. Do note ``all`` is a very resource-intensive action and it is highly recommended to call just the info/APIs you need.
- na_ontap_rest_info - The following info subsets have been added ``system_node_info``, ``net_interface_info``, ``net_port_info``, ``security_login_account_info``, ``vserver_peer_info``, ``cluster_image_info``, ``cluster_log_forwarding_info``, ``metrocluster_info``, ``metrocluster_node_info``, ``net_dns_info``, ``net_interface_service_policy_info``, ``vserver_nfs_info``, ``clock_info``, ``igroup_info``, ``vscan_status_info``, ``vscan_connection_status_all_info``, ``storage_bridge_info``, ``nvme_info``, ``nvme_interface_info``, ``nvme_subsystem_info``, ``cluster_switch_info``, ``export_policy_info``, ``kerberos_realm_info``,``sis_info``, ``sis_policy_info``, ``snapmirror_info``, ``snapmirror_destination_info``, ``snapmirror_policy_info``, ``sys_cluster_alerts``, ``cifs_vserver_security_info``
- na_ontap_rest_info - added file_directory_security to return the effective permissions of the directory. When using file_directory_security it must be called with gather_subsets and path and vserver must be specified in parameters.
- na_ontap_rest_info - new option ``use_python_keys`` to replace ``svm/svms`` with ``svm_svms`` to simplify post processing.
- na_ontap_snmp - Added REST support to the SNMP module

Bugfixes
--------

- na_ontap_job_schedule - fix documentation for REST ranges for months.
- na_ontap_object_store - when using REST, wait for job status to correctly report errors.
- na_ontap_quotas - attempt to retry on ``13001:success`` ZAPI error.  Add debug data.
- na_ontap_rest_cli - removed incorrect statement indicating that console access is required.

v21.8.1
=======

Bugfixes
--------

- all REST modules - 9.4 and 9.5 were incorrectly detected as supporting REST.
- na_ontap_snapmirror - improve error message when option is not supported with ZAPI.

v21.8.0
=======

Minor Changes
-------------

- na_ontap_cluster_peer - new option ``peer_options`` to use different credentials on peer.
- na_ontap_debug - additional checks when REST is available to help debug vserver connectivity issues.
- na_ontap_flexcache - corrected module name in documentation Examples
- na_ontap_net_port - change option types to bool and int respectively for ``autonegotiate_admin`` and ``mtu``.
- na_ontap_net_port - new option ``up_admin`` to set administrative state.
- na_ontap_rest_info - add examples for ``parameters`` option.
- na_ontap_snapshot - add REST support to create, modify, rename, and delete snapshot.
- na_ontap_snapshot - new option ``expiry_time``.
- na_ontap_volume - show warning when resize is ignored because threshold is not reached.
- na_ontap_vserver_create role - add ``nfsv3``, ``nfsv4``, ``nfsv41`` options.
- na_ontap_vserver_peer - new option ``peer_options`` to use different credentials on peer.

Bugfixes
--------

- all modules - fix traceback TypeError 'NoneType' object is not subscriptable when hostname points to a web server.
- na_ontap_cluster_peer - KeyError on dest_cluster_name if destination is unreachable.
- na_ontap_cluster_peer - KeyError on username when using certicate.
- na_ontap_export_policy_rule - change ``anonymous_user_id`` type to str to accept user name and user id.   (A warning is now triggered when a number is not quoted.)
- na_ontap_volume_clone - ``parent_vserver`` can not be given with ``junction_path``, ``uid``, or ``gid``
- na_ontap_vserver_peer - KeyError on username when using certicate.

New Modules
-----------

- netapp.ontap.na_ontap_cifs_local_user_set_password - NetApp ONTAP set local CIFS user password
- netapp.ontap.na_ontap_fdsd - NetApp ONTAP create or remove a File Directory security descriptor.
- netapp.ontap.na_ontap_fdsp - NetApp ONTAP create or delete a file directory security policy
- netapp.ontap.na_ontap_fdspt - NetApp ONTAP create, delete or modify File Directory security policy tasks
- netapp.ontap.na_ontap_fdss - NetApp ONTAP File Directory Security Set.
- netapp.ontap.na_ontap_partitions - NetApp ONTAP Assign partitions and disks to nodes.

v21.7.0
=======

Minor Changes
-------------

- License displayed correctly in Github
- na_ontap_cifs - new option ``comment`` to associate a description to a CIFS share.
- na_ontap_disks - added REST support for the module.
- na_ontap_disks - added functionality to reassign spare disks from a partner node to the desired node.
- na_ontap_disks - new option min_spares.
- na_ontap_lun - new suboption ``exclude_aggregates`` for SAN application.
- na_ontap_volume - new suboption ``exclude_aggregates`` for NAS application.

Bugfixes
--------

- na_ontap_flexcache - one occurrence of msg missing in call to fail_json.
- na_ontap_igroup - one occurrence of msg missing in call to fail_json.
- na_ontap_igroups - nested igroups are not supported on ONTAP 9.9.0 but are on 9.9.1.
- na_ontap_iscsi_security - IndexError list index out of range if vserver does not exist
- na_ontap_iscsi_security - cannot change authentication_type
- na_ontap_lun - three occurrencse of msg missing in call to fail_json.
- na_ontap_lun_map_reporting_nodes - one occurrence of msg missing in call to fail_json.
- na_ontap_snapmirror - one occurrence of msg missing in call to fail_json.

New Modules
-----------

- netapp.ontap.na_ontap_publickey - NetApp ONTAP publickey configuration
- netapp.ontap.na_ontap_service_policy - NetApp ONTAP service policy configuration

v21.6.1
=======

Bugfixes
--------

- na_ontap_autosupport - KeyError - No element by given name validate-digital-certificate.

v21.6.0
=======

Minor Changes
-------------

- na_ontap_rest_info - Added "autosupport_check_info"/"support/autosupport/check" to the attributes that will be collected when gathering info using the module.
- na_ontap_users - new option ``application_dicts`` to associate multiple authentication methods to an application.
- na_ontap_users - new option ``application_strs`` to disambiguate ``applications``.
- na_ontap_users - new option ``replace_existing_apps_and_methods``.
- na_ontap_users - new suboption ``second_authentication_method`` with ``application_dicts`` option.
- na_ontap_vserver_peer - new options ``local_name_for_source`` and ``local_name_for_peer`` added.

Bugfixes
--------

- na_ontap_autosupport - TypeError - '>' not supported between instances of 'str' and 'list'.
- na_ontap_quotas - fail to reinitialize on create if quota is already on.

v21.5.0
=======

Major Changes
-------------

- na_ontap_autosupport - Added REST support to the module.

Minor Changes
-------------

- na_ontap_autosupport - new option ``local_collection_enabled`` to specify whether collection of AutoSupport data when the AutoSupport daemon is disabled.
- na_ontap_autosupport - new option ``max_http_size`` to specify delivery size limit for the HTTP transport protocol (in bytes).
- na_ontap_autosupport - new option ``max_smtp_size`` to specify delivery size limit for the SMTP transport protocol (in bytes).
- na_ontap_autosupport - new option ``nht_data_enabled`` to specify whether the disk health data is collected as part of the AutoSupport data.
- na_ontap_autosupport - new option ``ondemand_enabled`` to specify whether the AutoSupport OnDemand Download feature is enabled.
- na_ontap_autosupport - new option ``perf_data_enabled`` to specify whether the performance data is collected as part of the AutoSupport data.
- na_ontap_autosupport - new option ``private_data_removed`` to specify the removal of customer-supplied data.
- na_ontap_autosupport - new option ``reminder_enabled`` to specify whether AutoSupport reminders are enabled or disabled.
- na_ontap_autosupport - new option ``retry_count`` to specify the maximum number of delivery attempts for an AutoSupport message.
- na_ontap_autosupport - new option ``validate_digital_certificate`` which when set to true each node will validate the digital certificates that it receives.
- na_ontap_info - Added "autosupport_check_info" to the attributes that will be collected when gathering info using the module.

Bugfixes
--------

- na_ontap_qtree - wait for completion when creating or modifying a qtree with REST.
- na_ontap_volume - ignore read error because of insufficient privileges for efficiency options so that the module can be run as vsadmin.

v21.4.0
=======

Minor Changes
-------------

- na_ontap_igroups - new option ``initiator_names`` as a replacement for ``initiators`` (still supported as an alias).
- na_ontap_igroups - new option ``initiator_objects`` to support initiator comments (requires ONTAP 9.9).
- na_ontap_lun - allow new LUNs to use different igroup or os_type when using SAN application.
- na_ontap_lun - ignore small increase (lower than provisioned) and small decrease (< 10%) in ``total_size``.
- na_ontap_node - added REST support for ONTAP node modify and rename.
- na_ontap_volume - warn when attempting to modify application only options.
- na_ontap_volume_efficiency - new option 'start_ve_build_metadata' scan the entire and generate fingerprint database.
- na_ontap_volume_efficiency - new option 'start_ve_delete_checkpoint' delete checkpoint and start the operation from the begining.
- na_ontap_volume_efficiency - new option 'start_ve_qos_policy' defines the QoS policy for the operation.
- na_ontap_volume_efficiency - new option 'start_ve_queue_operation' queue if an exisitng operation is already running.
- na_ontap_volume_efficiency - new option 'start_ve_scan_all' scan the entire volume without applying share block optimization.
- na_ontap_volume_efficiency - new option 'start_ve_scan_old_data' scan the file system to process all the existing data.
- na_ontap_volume_efficiency - new option 'stop_ve_all_operations' all running and queued operations to be stopped.
- na_ontap_volume_efficiency - new option to allow volume efficiency to be started and stopped 'volume_efficiency'.

Bugfixes
--------

- na_ontap_autosupport - warn when password is present in ``proxy_url`` as it makes the operation not idempotent.
- na_ontap_cluster - ignore ZAPI EMS log error when in pre-cluster mode.
- na_ontap_lun - SAN application is not supported on 9.6 and only partially supported on 9.7 (no modify).
- na_ontap_svm - iscsi current status is not read correctly (mispelled issi).

New Modules
-----------

- netapp.ontap.na_ontap_cifs_local_user_modify - NetApp ONTAP modify local CIFS user.
- netapp.ontap.na_ontap_disk_options - NetApp ONTAP modify storage disk options
- netapp.ontap.na_ontap_fpolicy_event - NetApp ONTAP FPolicy policy event configuration
- netapp.ontap.na_ontap_fpolicy_ext_engine - NetApp ONTAP fPolicy external engine configuration.
- netapp.ontap.na_ontap_fpolicy_scope - NetApp ONTAP - Create, delete or modify an FPolicy policy scope configuration.
- netapp.ontap.na_ontap_fpolicy_status - NetApp ONTAP - Enables or disables the specified fPolicy policy
- netapp.ontap.na_ontap_snaplock_clock - NetApp ONTAP Sets the snaplock compliance clock.

v21.3.1
=======

Bugfixes
--------

- na_ontap_snapmirror - check for consistency_group_volumes always fails on 9.7, and cluster or ipspace when using endpoints with ZAPI.

v21.3.0
=======

Minor Changes
-------------

- na_ontap_debug - improve error reporting for import errors on netapp_lib.
- na_ontap_flexcache - mount/unmount the FlexCache volume when using REST.
- na_ontap_flexcache - support REST APIs in addition to ZAPI for create and delete.
- na_ontap_flexcache - support for ``prepopulate`` option when using REST (requires ONTAP 9.8).
- na_ontap_igroups - new option ``igroups`` to support nested igroups (requires ONTAP 9.9).
- na_ontap_info - improve error reporting for import errors on netapp_lib, json, xlmtodict.
- na_ontap_motd - deprecated module warning and to use na_ontap_login_messages.
- na_ontap_volume - new suboption ``dr_cache`` when creating flexcache using NAS application template.
- na_ontap_volume_efficiency - to allow for FAS ONTAP systems to enable volume efficiency when it does not exist and apply additional parameters.
- na_ontap_volume_efficiency - to allow for FAS ONTAP systems to enable volume efficiency when it does not exist.

Bugfixes
--------

- na_ontap_ldap_client - ``port`` was incorrectly used instead of ``tcp_port``.
- na_ontap_node - KeyError fix for location ans asset-tag parameters in get_node().
- na_ontap_snapmirror - SVM scoped policies were not found when using a destination path with REST application.
- na_ontap_volume - changes in ``encrypt`` settings were ignored.
- na_ontap_volume - unmount volume before deleting it when using REST.

New Modules
-----------

- netapp.ontap.na_ontap_domain_tunnel - NetApp ONTAP domain tunnel
- netapp.ontap.na_ontap_fpolicy_policy - NetApp ONTAP - Create, delete or modify an FPolicy policy.
- netapp.ontap.na_ontap_security_config - NetApp ONTAP modify security config for SSL.
- netapp.ontap.na_ontap_storage_auto_giveback - Enables or disables NetApp ONTAP storage auto giveback for a specified node
- netapp.ontap.na_ontap_storage_failover - Enables or disables NetApp Ontap storage failover for a specified node

v21.2.0
=======

Minor Changes
-------------

- azure_rm_netapp_account - new option ``active_directories`` to support SMB volumes.
- azure_rm_netapp_volume - new option ``protocol_types`` to support SMB volumes.
- na_ontap_igroup - added REST support for ONTAP igroup creation, modification, and deletion.
- na_ontap_lun - add ``comment`` option.
- na_ontap_lun - convert existing LUNs and supporting volume to a smart container within a SAN application.
- na_ontap_lun - new option ``qos_adaptive_policy_group``.
- na_ontap_lun - new option ``scope`` to explicitly force operations on the SAN application or a single LUN.
- na_ontap_node - added modify function for location and asset tag for node.
- na_ontap_snapmirror - add new options ``source_endpoint`` and ``destination_endpoint`` to group endpoint suboptions.
- na_ontap_snapmirror - add new suboptions ``consistency_group_volumes`` and ``ipspace`` to endpoint options.
- na_ontap_snapmirror - deprecate older options for source and destination paths, volumes, vservers, and clusters.
- na_ontap_snapmirror - improve error reporting or warn when REST option is not supported.
- na_ontap_snapmirror - report warning when relationship is present but not healthy.

Bugfixes
--------

- All REST modules - ONTAP 9.4 and 9.5 are incorrectly detected as supporting REST with ``use_rest:auto``.
- na_ontap_igroup - report error when attempting to modify an option that cannot be changed.
- na_ontap_lun - ``qos_policy_group`` could not be modified if a value was not provided at creation.
- na_ontap_lun - tiering options were ignored in san_application_template.
- na_ontap_volume - report error from resize operation when using REST.
- na_ontap_volume - returns an error now if deleting a volume with REST api fails.

New Modules
-----------

- netapp.ontap.na_ontap_cifs_local_group_member - NetApp Ontap - Add or remove CIFS local group member
- netapp.ontap.na_ontap_log_forward - NetApp ONTAP Log Forward Configuration
- netapp.ontap.na_ontap_lun_map_reporting_nodes - NetApp ONTAP LUN maps reporting nodes
- netapp.ontap.na_ontap_volume_efficiency - NetApp Ontap enables, disables or modifies volume efficiency

v21.1.0
=======

Minor Changes
-------------

- general - improve error reporting when older version of netapp-lib is used.
- na_ontap_cluster - ``time_out`` to wait for cluster creation, adding and removing a node.
- na_ontap_debug - connection diagnostics added for invalid ipaddress and DNS hostname errors.
- na_ontap_firmware_upgrade - new option for firmware type ``storage`` added.
- na_ontap_info - deprecate ``state`` option.
- na_ontap_lun - new options ``total_size`` and ``total_size_unit`` when using SAN application template.
- na_ontap_lun - support increasing lun_count and total_size when using SAN application template.
- na_ontap_quota - allow to turn quota on/off without providing quota_target or type.
- na_ontap_rest_info - deprecate ``state`` option.
- na_ontap_snapmirror - new option ``create_destination`` to automatically create destination endpoint (ONTAP 9.7).
- na_ontap_snapmirror - new option ``destination_cluster`` to automatically create destination SVM for SVM DR (ONTAP 9.7).
- na_ontap_snapmirror - new option ``source_cluster`` to automatically set SVM peering (ONTAP 9.7).
- na_ontap_snapmirror - use REST API for create action if target supports it.  (ZAPIs are still used for all other actions).
- na_ontap_volume - use REST API for delete operation if targets supports it.

Bugfixes
--------

- na_ontap_lun - REST expects 'all' for tiering policy and not 'backup'.
- na_ontap_quotas - Handle blank string idempotency issue for ``quota_target`` in quotas module.
- na_ontap_rest_info - ``changed`` was set to "False" rather than boolean False.
- na_ontap_snapmirror - fix job update failures for load_sharing mirrors.
- na_ontap_snapmirror - report error when attempting to change relationship_type.
- na_ontap_snapmirror - wait up to 5 minutes for abort to complete before issuing a delete.
- na_ontap_snmp - SNMP module wrong ``access_control`` issue and error handling fix.
- na_ontap_volume - REST expects 'all' for tiering policy and not 'backup'.
- na_ontap_volume - detect and report error when attempting to change FlexVol into FlexGroup.
- na_ontap_volume - report error if ``aggregate_name`` option is used with a FlexGroup.

New Modules
-----------

- netapp.ontap.na_ontap_debug - NetApp ONTAP Debug netapp-lib import and connection.

v20.12.0
========

Minor Changes
-------------

- all ZAPI modules - new ``classic_basic_authorization`` feature_flag to disable adding Authorization header proactively.
- all ZAPI modules - optimize Basic Authentication by adding Authorization header proactively.
- na_ontap_igroup - new option ``os_type`` to replace ``ostype`` (but ostype is still accepted).
- na_ontap_info - New options ``cifs_options_info``, ``cluster_log_forwarding_info``, ``event_notification_destination_info``, ``event_notification_info``, ``security_login_role_config_info``, ``security_login_role_info`` have been added.
- na_ontap_lun - new option ``from_name`` to rename a LUN.
- na_ontap_lun - new option ``os_type`` to replace ``ostype`` (but ostype is still accepted), and removed default to ``image``.
- na_ontap_lun - new option ``qos_policy_group`` to assign a qos_policy_group to a LUN.
- na_ontap_lun - new option ``san_application_template`` to create LUNs without explicitly creating a volume and using REST APIs.
- na_ontap_qos_policy_group - new option ``is_shared`` for sharing QOS SLOs or not.
- na_ontap_quota_policy - new option ``auto_assign`` to assign quota policy to vserver.
- na_ontap_quotas - New option ``activate_quota_on_change`` to resize or reinitialize quotas.
- na_ontap_quotas - New option ``perform_user_mapping`` to perform user mapping for the user specified in quota-target.
- na_ontap_rest_info - Support for gather subsets - ``cifs_home_directory_info, cluster_software_download, event_notification_info, event_notification_destination_info, security_login_info, security_login_rest_role_info``
- na_ontap_volume - ``compression`` to enable compression on a FAS volume.
- na_ontap_volume - ``inline-compression`` to enable inline compression on a volume.
- na_ontap_volume - ``nas_application_template`` to create a volume using nas application REST API.
- na_ontap_volume - ``size_change_threshold`` to ignore small changes in volume size.
- na_ontap_volume - ``sizing_method`` to resize a FlexGroup using REST.

Bugfixes
--------

- na_ontap_broadcast_domain_ports - handle ``changed`` for check_mode and report correctly.
- na_ontap_cifs - fix for AttributeError - 'NoneType' object has no attribute 'get' on line 300
- na_ontap_svm - warning for ``aggr_list`` wildcard value(``*``) in create idempotency.
- na_ontap_user - application expects only ``service_processor`` but module supports ``service-processor``.
- na_ontap_volume - checking for success before failure lead to 'NoneType' object has no attribute 'get_child_by_name' when modifying a Flexcache volume.
- na_ontap_volume - fix volume type modify issue by reporting error.

v20.11.0
========

Minor Changes
-------------

- na_ontap_cifs - output ``modified`` if a modify action is taken.
- na_ontap_cluster_peer - optional parameter ``ipspace`` added for cluster peer.
- na_ontap_export_policy_rule - minor doc updates.
- na_ontap_info - do not require write access privileges.   This also enables other modules to work in check_mode without write access permissions.
- na_ontap_interface - minor example update.
- na_ontap_lun - ``use_exact_size`` to create a lun with the exact given size so that the lun is not rounded up.
- na_ontap_lun - support modify for space_allocation and space_reserve.
- na_ontap_mcc_mediator - improve error reporting when REST is not available.
- na_ontap_metrocluster - improve error reporting when REST is not available.
- na_ontap_software_update - add `force_update` option to ignore current version.
- na_ontap_svm - output ``modified`` if a modify action is taken.
- na_ontap_wwpn_alias - improve error reporting when REST is not available.

Bugfixes
--------

- All REST modules, will not fail if a job fails
- na_ontap_cifs - fix idempotency issue when ``show-previous-versions`` is used.
- na_ontap_firmware_upgrade - fix ValueError issue when processing URL error.
- na_ontap_info - Use ``node-id`` as key rather than ``current-version``.
- na_ontap_ipspace - invalid call in error reporting (double error).
- na_ontap_software_update - module is not idempotent.

New Modules
-----------

- netapp.ontap.na_ontap_metrocluster_dr_group - NetApp ONTAP manage MetroCluster DR Group

v20.10.0
========

Minor Changes
-------------

- na_ontap_rest_info - Support for gather subsets - ``application_info, application_template_info, autosupport_config_info , autosupport_messages_history, ontap_system_version, storage_flexcaches_info, storage_flexcaches_origin_info, storage_ports_info, storage_qos_policies, storage_qtrees_config, storage_quota_reports, storage_quota_policy_rules, storage_shelves_config, storage_snapshot_policies, support_ems_config, support_ems_events, support_ems_filters``

Bugfixes
--------

- na_ontap_aggregate - support concurrent actions for rename/modify/add_object_store and create/add_object_store.
- na_ontap_cluster - ``single_node_cluster`` option was ignored.
- na_ontap_info - KeyError on ``tree`` for quota_report_info.
- na_ontap_info - better reporting on KeyError traceback, option to ignore error.
- na_ontap_snapmirror_policy - report error when attempting to change ``policy_type`` rather than taking no action.
- na_ontap_volume - ``encrypt`` with a value of ``false`` is ignored when creating a volume.

v20.9.0
=======

Minor Changes
-------------

- na_ontap_cluster - ``node_name`` to set the node name when adding a node, or as an alternative to `cluster_ip_address`` to remove a node.
- na_ontap_cluster - ``state`` can be set to ``absent`` to remove a node identified with ``cluster_ip_address`` or ``node_name``.
- na_ontap_qtree - ``wait_for_completion`` and ``time_out`` to wait for qtree deletion when using REST.
- na_ontap_quotas - ``soft_disk_limit`` and ``soft_file_limit`` for the quota target.
- na_ontap_rest_info - Support for gather subsets - ``initiator_groups_info, san_fcp_services, san_iscsi_credentials, san_iscsi_services, san_lun_maps, storage_luns_info, storage_NVMe_namespaces.``

Bugfixes
--------

- na_ontap_* - change version_added from '2.6' to '2.6.0' where applicable to satisfy sanity checker.
- na_ontap_cluster - ``check_mode`` is now working properly.
- na_ontap_interface - ``home_node`` is not required in pre-cluster mode.
- na_ontap_interface - ``role`` is not required if ``service_policy`` is present and ONTAP version is 9.8.
- na_ontap_interface - traceback in get_interface if node is not reachable.
- na_ontap_job_schedule - allow ``job_minutes`` to set number to -1 for job creation with REST too.
- na_ontap_qtree - fixed ``None is not subscriptable`` exception on rename operation.
- na_ontap_volume - fixed ``KeyError`` exception on ``size`` when reporting creation error.
- netapp.py - uncaught exception (traceback) on zapi.NaApiError.

New Modules
-----------

- netapp.ontap.na_ontap_active_directory - NetApp ONTAP configure active directory
- netapp.ontap.na_ontap_mcc_mediator - NetApp ONTAP Add and Remove MetroCluster Mediator
- netapp.ontap.na_ontap_metrocluster - NetApp ONTAP set up a MetroCluster

v20.8.0
=======

Minor Changes
-------------

- add ``type:`` and ``elements:`` information where missing.
- na_ontap_aggregate - support ``disk_size_with_unit`` option.
- na_ontap_ldap_client - support ``ad_domain`` and ``preferred_ad_server`` options.
- na_ontap_qtree - ``force_delete`` option with a DEFAULT of ``true`` so that ZAPI behavior is aligned with REST.
- na_ontap_rest_info - Support for gather subsets - ``cloud_targets_info, cluster_chassis_info, cluster_jobs_info, cluster_metrics_info, cluster_schedules, broadcast_domains_info, cluster_software_history, cluster_software_packages, network_ports_info, ip_interfaces_info, ip_routes_info, ip_service_policies, network_ipspaces_info, san_fc_logins_info, san_fc_wppn-aliases, svm_dns_config_info, svm_ldap_config_info, svm_name_mapping_config_info, svm_nis_config_info, svm_peers_info, svm_peer-permissions_info``.
- na_ontap_rest_info - Support for gather subsets for 9.8+ - ``cluster_metrocluster_diagnostics``.
- na_ontap_security_certificates - ``ignore_name_if_not_supported`` option to not fail if ``name`` is present since ``name`` is not supported in ONTAP 9.6 and 9.7.
- na_ontap_software_update - added ``timeout`` option to give enough time for the update to complete.
- update ``required:`` information.
- use a three group format for ``version_added``.  So 2.7 becomes 2.7.0.  Same thing for 2.8 and 2.9.

Bugfixes
--------

- na_ontap_aggregate - ``disk-info`` error when using ``disks`` option.
- na_ontap_autosupport_invoke - ``message`` has changed to ``autosupport_message`` as Redhat has reserved this word. ``message`` has been alias'd to ``autosupport_message``.
- na_ontap_cifs_vserver - fix documentation and add more examples.
- na_ontap_cluster - module was not idempotent when changing location or contact information.
- na_ontap_igroup - idempotency issue when using uppercase hex digits (A, B, C, D, E, F) in WWN (ONTAP uses lowercase).
- na_ontap_igroup_initiator - idempotency issue when using uppercase hex digits (A, B, C, D, E, F) in WWN (ONTAP uses lowercase).
- na_ontap_info - Fixed error causing module to fail on ``metrocluster_check_info``, ``env_sensors_info`` and ``volume_move_target_aggr_info``.
- na_ontap_security_certificates - allows (``common_name``, ``type``) as an alternate key since ``name`` is not supported in ONTAP 9.6 and 9.7.
- na_ontap_snapmirror - fixed KeyError when accessing ``elationship_type`` parameter.
- na_ontap_snapmirror_policy - fixed a race condition when creating a new policy.
- na_ontap_snapmirror_policy - fixed idempotency issue withis_network_compression_enabled for REST.
- na_ontap_software_update - ignore connection errors during update as nodes cannot be reachable.
- na_ontap_user - enable lock state and password to be set in the same task for existing user.
- na_ontap_volume - issue when snapdir_access and atime_update not passed together.
- na_ontap_vscan_on_access_policy - ``bool`` type was not properly set for ``scan_files_with_no_ext``.
- na_ontap_vscan_on_access_policy - ``policy_status`` enable/disable option was not supported.
- na_ontap_vscan_on_demand_task - ``file_ext_to_include`` was not handled properly.
- na_ontap_vscan_scanner_pool_policy - scanner_pool apply policy support on modification.
- na_ontap_vserver_create(role) - lif creation now defaults to system-defined unless iscsi lif type.
- use_rest is now case insensitive.

New Modules
-----------

- netapp.ontap.na_ontap_file_directory_policy - NetApp ONTAP create, delete, or modify vserver security file-directory policy
- netapp.ontap.na_ontap_ssh_command - NetApp ONTAP Run any cli command over plain SSH using paramiko.
- netapp.ontap.na_ontap_wait_for_condition - NetApp ONTAP wait_for_condition.  Loop over a get status request until a condition is met.

v20.7.0
=======

Minor Changes
-------------

- module_utils/netapp - add retry on wait_on_job when job failed. Abort 3 consecutive errors.
- na_ontap_info - support ``continue_on_error`` option to continue when a ZAPI is not supported on a vserver, or for cluster RPC errors.
- na_ontap_info - support ``query`` option to specify which objects to return.
- na_ontap_info - support ``vserver`` tunneling to limit output to one vserver.
- na_ontap_pb_get_online_volumes.yml - example playbook to list volumes that are online (or offline).
- na_ontap_pb_install_SSL_certificate_REST.yml - example playbook to install SSL certificates using REST APIs.
- na_ontap_rest_info - Support for gather subsets - ``cluster_node_info, cluster_peer_info, disk_info, cifs_services_info, cifs_share_info``.
- na_ontap_snapmirror_policy - support for SnapMirror policy rules.
- na_ontap_vscan_scanner_pool - support modification.

Bugfixes
--------

- na_ontap_command - replace invalid backspace characters (0x08) with '.'.
- na_ontap_firmware_download - exception on PCDATA if ONTAP returns a BEL (0x07) character.
- na_ontap_info - lists were incorrectly processed in convert_keys, returning {}.
- na_ontap_info - qtree_info is missing most entries.  Changed key from `vserver:id` to `vserver:volume:id` .
- na_ontap_iscsi_security - adding no_log for password parameters.
- na_ontap_portset - adding explicit error message as modify portset is not supported.
- na_ontap_snapmirror - fixed snapmirror delete for loadsharing to not go to quiesce state for the rest of the set.
- na_ontap_ucadapter - fixed KeyError if type is not provided and mode is 'cna'.
- na_ontap_user - checked `applications` does not contain snmp when using REST API call.
- na_ontap_user - fixed KeyError if locked key not set with REST API call.
- na_ontap_user - fixed KeyError if vserver - is empty with REST API call (useful to indicate cluster scope).
- na_ontap_volume - fixed KeyError when getting info on a MVD volume

New Modules
-----------

- netapp.ontap.na_ontap_security_certificates - NetApp ONTAP manage security certificates.

v20.6.1
=======

Minor Changes
-------------

- na_ontap_firmware_upgrade - ``reboot_sp`` - reboot service processor before downloading package.
- na_ontap_firmware_upgrade - ``rename_package`` - rename file when downloading service processor package.
- na_ontap_firmware_upgrade - ``replace_package`` - replace local file when downloading service processor package.

Bugfixes
--------

- na_ontap_firmware_upgrade - images are not downloaded, but the module reports success.
- na_ontap_password - do not error out if password is identical to previous password (idempotency).
- na_ontap_user - fixed KeyError if password is not provided.

v20.6.0
=======

Minor Changes
-------------

- all modules - SSL certificate authentication in addition to username/password (python 2.7 or 3.x).
- all modules - ``cert_filepath``, ``key_filepath`` to enable SSL certificate authentication (python 2.7 or 3.x).
- na_ontap_disks - ``disk_type`` option allows to assign specified type of disk.
- na_ontap_firmware_upgrade - ignore timeout when downloading image unless ``fail_on_502_error`` is set to true.
- na_ontap_info - ``desired_attributes`` advanced feature to select which fields to return.
- na_ontap_info - ``use_native_zapi_tags`` to disable the conversion of '_' to '-' for attribute keys.
- na_ontap_pb_install_SSL_certificate.yml - playbook example - installing a self-signed SSL certificate, and enabling SSL certificate authentication.
- na_ontap_rest_info - ``fields`` options to request specific fields from subset.
- na_ontap_snapmirror - now performs restore with optional field ``source_snapshot`` for specific snapshot or uses latest.
- na_ontap_software_update - ``stabilize_minutes`` option specifies number of minutes needed to stabilize node before update.
- na_ontap_ucadapter - ``pair_adapters`` option allows specifying the list of adapters which also need to be offline.
- na_ontap_user - ``authentication_password`` option specifies password for the authentication protocol of SNMPv3 user.
- na_ontap_user - ``authentication_protocol`` option specifies authentication protocol fo SNMPv3 user.
- na_ontap_user - ``engine_id`` option specifies authoritative entity's EngineID for the SNMPv3 user.
- na_ontap_user - ``privacy_password`` option specifies password for the privacy protocol of SNMPv3 user.
- na_ontap_user - ``privacy_protocol`` option specifies privacy protocol of SNMPv3 user.
- na_ontap_user - ``remote_switch_ipaddress`` option specifies the IP Address of the remote switch of SNMPv3 user.
- na_ontap_user - added REST support for ONTAP user creation, modification & deletion.
- na_ontap_volume - ``auto_remap_luns`` option controls automatic mapping of LUNs during volume rehost.
- na_ontap_volume - ``check_interval`` option checks if a volume move has been completed and then waits this number of seconds before checking again.
- na_ontap_volume - ``force_restore`` option forces volume to restore even if the volume has one or more newer Snapshotcopies.
- na_ontap_volume - ``force_unmap_luns`` option controls automatic unmapping of LUNs during volume rehost.
- na_ontap_volume - ``from_vserver`` option allows volume rehost from one vserver to another.
- na_ontap_volume - ``preserve_lun_ids`` option controls LUNs in the volume being restored will remain mapped and their identities preserved.
- na_ontap_volume - ``snapshot_restore`` option specifies name of snapshot to restore from.

Bugfixes
--------

- module_utils/netapp_module - cater for empty lists in get_modified_attributes().
- module_utils/netapp_module - cater for lists with duplicate elements in compare_lists().
- na_ontap_firmware_upgrade - ignore timeout when downloading firmware images by default.
- na_ontap_info - conversion from '-' to '_' was not done for lists of dictionaries.
- na_ontap_ntfs_dacl - example fix in documentation string.
- na_ontap_snapmirror - could not delete all rules (bug in netapp_module).
- na_ontap_volume - `wait_on_completion` is supported with volume moves.
- na_ontap_volume - fix KeyError on 'style' when volume is of type - data-protection.
- na_ontap_volume - modify was invoked multiple times when once is enough.

v20.5.0
=======

Minor Changes
-------------

- na_ontap_aggregate - ``raid_type`` options supports 'raid_0' for ONTAP Select.
- na_ontap_cluster_config - role - Port Flowcontrol and autonegotiate can be set in role
- na_ontap_cluster_peer - ``encryption_protocol_proposed`` option allows specifying encryption protocol to be used for inter-cluster communication.
- na_ontap_info - new fact - aggr_efficiency_info.
- na_ontap_info - new fact - cluster_switch_info.
- na_ontap_info - new fact - disk_info.
- na_ontap_info - new fact - env_sensors_info.
- na_ontap_info - new fact - net_dev_discovery_info.
- na_ontap_info - new fact - service_processor_info.
- na_ontap_info - new fact - shelf_info.
- na_ontap_info - new fact - sis_info.
- na_ontap_info - new fact - subsys_health_info.
- na_ontap_info - new fact - sys_cluster_alerts.
- na_ontap_info - new fact - sysconfig_info.
- na_ontap_info - new fact - volume_move_target_aggr_info.
- na_ontap_info - new fact - volume_space_info.
- na_ontap_nvme_namespace - ``block_size`` option allows specifying size in bytes of a logical block.
- na_ontap_snapmirror - snapmirror now allows resume feature.
- na_ontap_volume - ``cutover_action`` option allows specifying the action to be taken for cutover.

Bugfixes
--------

- REST API call now honors the ``http_port`` parameter.
- REST API detection now works with vserver (use_rest - Auto).
- na_ontap_autosupport_invoke - when using ZAPI and name is not given, send autosupport message to all nodes in the cluster.
- na_ontap_cg_snapshot - properly states it does not support check_mode.
- na_ontap_cluster - ONTAP 9.3 or earlier does not support ZAPI element single-node-cluster.
- na_ontap_cluster_ha - support check_mode.
- na_ontap_cluster_peer - EMS log wrongly uses destination credentials with source hostname.
- na_ontap_cluster_peer - support check_mode.
- na_ontap_disks - support check_mode.
- na_ontap_dns - support check_mode.
- na_ontap_efficiency_policy - change ``duration`` type from int to str to support '-' input.
- na_ontap_fcp - support check_mode.
- na_ontap_flexcache - support check_mode.
- na_ontap_info - `metrocluster_check_info` does not trigger a traceback but adds an "error" info element if the target system is not set up for metrocluster.
- na_ontap_license - support check_mode.
- na_ontap_login_messages - fix documentation link.
- na_ontap_node - support check mode.
- na_ontap_ntfs_sd - documentation string update for examples and made sure owner or group not mandatory.
- na_ontap_ports - now support check mode.
- na_ontap_restit - error can be a string in addition to a dict.  This fix removes a traceback with AttributeError.
- na_ontap_routes - support Check Mode correctly.
- na_ontap_snapmirror - support check_mode.
- na_ontap_software_update - Incorrectly stated that it support check mode, it does not.
- na_ontap_svm_options - support check_mode.
- na_ontap_volume - fix KeyError on 'style' when volume is offline.
- na_ontap_volume - improve error reporting if required parameter is present but not set.
- na_ontap_volume - suppress traceback in wait_for_completion as volume may not be completely ready.
- na_ontap_volume_autosize - Support check_mode when `reset` option is given.
- na_ontap_volume_snaplock - fix documentation link.
- na_ontap_vserver_peer - EMS log wrongly uses destination credentials with source hostname.
- na_ontap_vserver_peer - support check_mode.

New Modules
-----------

- netapp.ontap.na_ontap_rest_info - NetApp ONTAP information gatherer using REST APIs

v20.4.1
=======

Minor Changes
-------------

- na_ontap_autosupport_invoke - added REST support for sending autosupport message.
- na_ontap_firmware_upgrade - ``force_disruptive_update`` and ``package_url`` options allows to make choices for download and upgrading packages.
- na_ontap_vserver_create has a new default variable ``netapp_version`` set to 140. If you are running 9.2 or below please add the variable to your playbook and set to 120

Bugfixes
--------

- na_ontap_info - ``metrocluster_check_info`` has been removed as it was breaking the info module for everyone who didn't have a metrocluster set up. We are working on adding this back in a future update.
- na_ontap_volume - ``volume_security_style`` option now allows modify.

v20.4.0
=======

Minor Changes
-------------

- na_ontap_aggregate - ``disk_count`` option allows adding additional disk to aggregate.
- na_ontap_info - ``max_records`` option specifies maximum number of records returned in a single ZAPI call.
- na_ontap_info - ``summary`` option specifies a boolean flag to control return all or none of the info attributes.
- na_ontap_info - new fact - iscsi_service_info.
- na_ontap_info - new fact - license_info.
- na_ontap_info - new fact - metrocluster_check_info.
- na_ontap_info - new fact - metrocluster_info.
- na_ontap_info - new fact - metrocluster_node_info.
- na_ontap_info - new fact - net_interface_service_policy_info.
- na_ontap_info - new fact - ontap_system_version.
- na_ontap_info - new fact - ontapi_version (and deprecate ontap_version, both fields are reported for now).
- na_ontap_info - new fact - qtree_info.
- na_ontap_info - new fact - quota_report_info.
- na_ontap_info - new fact - snapmirror_destination_info.
- na_ontap_interface - ``service_policy`` option to identify a single service or a list of services that will use a LIF.
- na_ontap_kerberos_realm - ``ad_server_ip`` option specifies IP Address of the Active Directory Domain Controller (DC).
- na_ontap_kerberos_realm - ``ad_server_name`` option specifies Host name of the Active Directory Domain Controller (DC).
- na_ontap_snapmirror - ``relationship-info-only`` option allows to manage relationship information.
- na_ontap_snapmirror_policy - REST is included and all defaults are removed from options.
- na_ontap_software_update - ``download_only`` options allows to download cluster image without software update.
- na_ontap_volume - ``snapshot_auto_delete`` option allows to manage auto delete settings of a specified volume.

Bugfixes
--------

- na_ontap_cifs_server - delete AD account if username and password are provided when state=absent
- na_ontap_info - cifs_server_info - fix KeyError exception on ``domain`` if only ``domain-workgroup`` is present.
- na_ontap_info - return all records of each gathered subset.
- na_ontap_iscsi_security - Fixed modify functionality for CHAP and typo correction
- na_ontap_kerberos_realm - fix ``kdc_vendor`` case sensitivity issue.
- na_ontap_snapmirror - calling quiesce before snapmirror break.

New Modules
-----------

- netapp.ontap.na_ontap_autosupport_invoke - NetApp ONTAP send AutoSupport message
- netapp.ontap.na_ontap_ntfs_dacl - NetApp Ontap create, delate or modify NTFS DACL (discretionary access control list)
- netapp.ontap.na_ontap_ntfs_sd - NetApp ONTAP create, delete or modify NTFS security descriptor
- netapp.ontap.na_ontap_restit - NetApp ONTAP Run any REST API on ONTAP
- netapp.ontap.na_ontap_wwpn_alias - NetApp ONTAP set FCP WWPN Alias
- netapp.ontap.na_ontap_zapit - NetApp ONTAP Run any ZAPI on ONTAP

v20.3.0
=======

Minor Changes
-------------

- na_ontap_info - New info's added ``storage_bridge_info``
- na_ontap_info - New info's added `cluster_identity_info``
- na_ontap_snapmirror - performs resync when the ``relationship_state`` is active and the current state is broken-off.

Bugfixes
--------

- na_ontap_volume_snaplock - Fixed KeyError exception on 'is-volume-append-mode-enabled'
- na_ontap_vscan_scanner_pool - has been updated to match the standard format used for all other ontap modules

New Modules
-----------

- netapp.ontap.na_ontap_snapmirror_policy - NetApp ONTAP create, delete or modify SnapMirror policies
- netapp.ontap.na_ontap_snmp_traphosts - NetApp ONTAP SNMP traphosts.

v20.2.0
=======

Minor Changes
-------------

- na_ontap_info - New info's added ``snapshot_info``
- na_ontap_info - ``max_records`` option to set maximum number of records to return per subset.
- na_ontap_nas_create - role - fix typo in README file, add CIFS example. -
- na_ontap_snapmirror - ``relationship_state`` option for breaking the snapmirror relationship.
- na_ontap_snapmirror - ``update_snapmirror`` option for updating the snapmirror relationship.
- na_ontap_volume_clone - ``split`` option to split clone volume from parent volume.

Bugfixes
--------

- na_ontap_cifs_server - Fixed KeyError exception on 'cifs_server_name'
- na_ontap_command - fixed traceback when using return_dict if u'1' is present in result value.
- na_ontap_login_messages - Fixed example documentation and spelling mistake issue
- na_ontap_nvme_subsystem - fixed bug when creating subsystem, vserver was not filtered.
- na_ontap_qtree - Fixed issue with Get function for REST
- na_ontap_svm - if language C.UTF-8 is specified, the module is not idempotent
- na_ontap_svm - if snapshot policy is changed, modify fails with "Extra input - snapshot_policy"
- na_ontap_volume_clone - fixed 'Extra input - parent-vserver' error when running as cluster admin.

New Modules
-----------

- netapp.ontap.na_ontap_volume_snaplock - NetApp ONTAP manage volume snaplock retention.

v20.1.0
=======

Minor Changes
-------------

- na_ontap_aggregate - add ``snaplock_type``.
- na_ontap_dns - added REST support for dns creation and modification on cluster vserver.
- na_ontap_igroup_initiator - ``force_remove`` to forcibly remove initiators from an igroup that is currently mapped to a LUN.
- na_ontap_info - New info's added ``cifs_server_info``, ``cifs_share_info``, ``cifs_vserver_security_info``, ``cluster_peer_info``, ``clock_info``, ``export_policy_info``, ``export_rule_info``, ``fcp_adapter_info``, ``fcp_alias_info``, ``fcp_service_info``, ``job_schedule_cron_info``, ``kerberos_realm_info``, ``ldap_client``, ``ldap_config``, ``net_failover_group_info``, ``net_firewall_info``, ``net_ipspaces_info``, ``net_port_broadcast_domain_info``, ``net_routes_info``, ``net_vlan_info``, ``nfs_info``, ``ntfs_dacl_info``, ``ntfs_sd_info``, ``ntp_server_info``, ``role_info``, ``service_processor_network_info``, ``sis_policy_info``, ``snapmirror_policy_info``, ``snapshot_policy_info``, ``vscan_info``, ``vserver_peer_info``
- na_ontap_interface - ``failover_group`` to specify the failover group for the LIF. ``is_ipv4_link_local`` to specify the LIF's are to acquire a ipv4 link local address.
- na_ontap_rest_cli - add OPTIONS as a supported verb and return list of allowed verbs.
- na_ontap_volume - add ``group_id`` and ``user_id``.

Bugfixes
--------

- na_ontap_aggregate - Fixed traceback when running as vsadmin and cleanly error out.
- na_ontap_command - stdout_lines_filter contains data only if include/exlude_lines parameter is used. (zeten30)
- na_ontap_command - stripped_line len is checked only once, filters are inside if block. (zeten30)
- na_ontap_interface - allow module to run on node before joining the cluster.
- na_ontap_net_ifgrp - Fixed error for na_ontap_net_ifgrp if no port is given.
- na_ontap_snapmirror - Fixed traceback when running as vsadmin.  Do not attempt to break a relationship that is 'Uninitialized'.
- na_ontap_snapshot_policy - Fixed KeyError on ``prefix`` issue when prefix parameter isn't supplied.
- na_ontap_volume - Fixed error reporting if efficiency policy cannot be read.  Do not attempt to read efficiency policy if not needed.
- na_ontap_volume - Fixed error when modifying volume efficiency policy.
- na_ontap_volume_clone - Fixed KeyError exception on ``volume``

New Modules
-----------

- netapp.ontap.na_ontap_login_messages - Setup login banner and message of the day

v19.11.0
========

Minor Changes
-------------

- na_ontap_cluster - added single node cluster option, also now supports for modify cluster contact and location option.
- na_ontap_efficiency_policy - ``changelog_threshold_percent`` to set the percentage at which the changelog will be processed for a threshold type of policy, tested once each hour.
- na_ontap_info - Added ``vscan_status_info``, ``vscan_scanner_pool_info``, ``vscan_connection_status_all_info``, ``vscan_connection_extended_stats_info``
- na_ontap_info - Now allow you use to vsadmin to get info (Must user ``vserver`` option).

Bugfixes
--------

- na_ontap_cluster - autosupport log pushed after cluster create is performed, removed license add or remove option.
- na_ontap_dns - report error if modify or delete operations are attempted on cserver when using REST.  Make create operation idempotent for cserver when using REST.  Support for modify/delete on cserver when using REST will be added later.
- na_ontap_firewall_policy - portmap added as a valid service
- na_ontap_net_routes - REST does not support the ``metric`` attribute
- na_ontap_snapmirror - added initialize boolean option which specifies whether to initialize SnapMirror relation.
- na_ontap_volume - fixed error when deleting flexGroup volume with ONTAP 9.7.
- na_ontap_volume - tiering option requires 9.4 or later (error on volume-comp-aggr-attributes)
- na_ontap_vscan_scanner_pool - fix module only gets one scanner pool.

New Modules
-----------

- netapp.ontap.na_ontap_quota_policy - NetApp Ontap create, rename or delete quota policy

v19.10.1
========

New Modules
-----------

- netapp.ontap.na_ontap_iscsi_security - NetApp ONTAP Manage iscsi security.

v19.10.0
========

Minor Changes
-------------

- Added REST support to existing modules.
    By default, the module will use REST if the target system supports it, and the options are supported.  Otherwise, it will switch back to ZAPI.
    This behavior can be controlled with the ``use_rest`` option.
    Always - to force REST.  The module fails and reports an error if REST cannot be used.
    Never - to force ZAPI.  This could be useful if you find some incompatibility with REST, or want to confirm the behavior is identical between REST and ZAPI.
    Auto - the default, as described above.
- na_ontap_cluster_config - role updated to support a cleaner playbook
- na_ontap_command - ``vserver`` - to allow command to run as either cluster admin or vserver admin.  To run as vserver admin you must use the vserver option.
- na_ontap_export_policy - REST support
- na_ontap_ipspace - REST support
- na_ontap_job_schedule - REST support
- na_ontap_motd - rename ``message`` to ``motd_message`` to avoid conflict with Ansible internal variable name.
- na_ontap_nas_create - role updated to support a cleaner playbook
- na_ontap_ndmp - REST support - only ``enable`` and ``authtype`` are supported with REST
- na_ontap_net_routes - REST support
- na_ontap_nvme_namespace - ``size_unit`` to specify size in different units.
- na_ontap_qtree - REST support - ``oplocks`` is not supported with REST, defaults to enable.
- na_ontap_san_create - role updated to support a cleaner playbook
- na_ontap_snapshot_policy - ``prefix`` - option to use for creating snapshot policy.
- na_ontap_svm - REST support - ``root_volume``, ``root_volume_aggregate``, ``root_volume_security_style`` are not supported with REST.
- na_ontap_vserver_create - role updated to support a cleaner playbook

Bugfixes
--------

- na ontap_net_routes - change metric type from string to int.
- na_ontap_cifs_server - minor documentation changes correction of create example with "name" parameter and adding type to parameters.
- na_ontap_firewall_policy - documentation changed for supported service parameter.
- na_ontap_ndmp - minor documentation changes for restore_vm_cache_size and data_port_range.
- na_ontap_net_subnet - fix ip_ranges option fails on existing subnet.
- na_ontap_net_subnet - fix rename idempotency issue and updated rename check.
- na_ontap_nvme_subsystem - fix fetching unique nvme subsytem based on vserver filter.
- na_ontap_qtree - REST API takes "unix_permissions" as parameter instead of "mode".
- na_ontap_qtree - unix permission is not available when security style is ntfs
- na_ontap_snapshot_policy - fix vsadmin approach for managing snapshot policy.
- na_ontap_svm - ``allowed_protocols`` added to param in proper way in case of using REST API
- na_ontap_user - minor documentation update for application parameter.
- na_ontap_volume - ``efficiency_policy`` was ignored
- na_ontap_volume - enforce that space_slo and space_guarantee are mutually exclusive
- na_ontap_vserver_cifs_security - fix int and boolean options when modifying vserver cifs security.

v2.9.0
======

New Modules
-----------

- netapp.ontap.na_ontap_efficiency_policy - NetApp ONTAP manage efficiency policies (sis policies)
- netapp.ontap.na_ontap_firmware_upgrade - NetApp ONTAP firmware upgrade for SP, shelf, ACP, and disk.
- netapp.ontap.na_ontap_info - NetApp information gatherer
- netapp.ontap.na_ontap_ipspace - NetApp ONTAP Manage an ipspace
- netapp.ontap.na_ontap_kerberos_realm - NetApp ONTAP vserver nfs kerberos realm
- netapp.ontap.na_ontap_ldap - NetApp ONTAP LDAP
- netapp.ontap.na_ontap_ldap_client - NetApp ONTAP LDAP client
- netapp.ontap.na_ontap_ndmp - NetApp ONTAP NDMP services configuration
- netapp.ontap.na_ontap_object_store - NetApp ONTAP manage object store config.
- netapp.ontap.na_ontap_ports - NetApp ONTAP add/remove ports
- netapp.ontap.na_ontap_qos_adaptive_policy_group - NetApp ONTAP Adaptive Quality of Service policy group.
- netapp.ontap.na_ontap_rest_cli - NetApp ONTAP Run any cli command, the username provided needs to have console login permission.
- netapp.ontap.na_ontap_volume_autosize - NetApp ONTAP manage volume autosize
- netapp.ontap.na_ontap_vscan - NetApp ONTAP Vscan enable/disable.
- netapp.ontap.na_ontap_vserver_cifs_security - NetApp ONTAP vserver CIFS security modification

v2.8.0
======

New Modules
-----------

- netapp.ontap.na_ontap_flexcache - NetApp ONTAP FlexCache - create/delete relationship
- netapp.ontap.na_ontap_igroup_initiator - NetApp ONTAP igroup initiator configuration
- netapp.ontap.na_ontap_lun_copy - NetApp ONTAP copy LUNs
- netapp.ontap.na_ontap_net_subnet - NetApp ONTAP Create, delete, modify network subnets.
- netapp.ontap.na_ontap_nvme - NetApp ONTAP Manage NVMe Service
- netapp.ontap.na_ontap_nvme_namespace - NetApp ONTAP Manage NVME Namespace
- netapp.ontap.na_ontap_nvme_subsystem - NetApp ONTAP Manage NVME Subsystem
- netapp.ontap.na_ontap_portset - NetApp ONTAP Create/Delete portset
- netapp.ontap.na_ontap_qos_policy_group - NetApp ONTAP manage policy group in Quality of Service.
- netapp.ontap.na_ontap_quotas - NetApp ONTAP Quotas
- netapp.ontap.na_ontap_security_key_manager - NetApp ONTAP security key manager.
- netapp.ontap.na_ontap_snapshot_policy - NetApp ONTAP manage Snapshot Policy
- netapp.ontap.na_ontap_unix_group - NetApp ONTAP UNIX Group
- netapp.ontap.na_ontap_unix_user - NetApp ONTAP UNIX users
- netapp.ontap.na_ontap_vscan_on_access_policy - NetApp ONTAP Vscan on access policy configuration.
- netapp.ontap.na_ontap_vscan_on_demand_task - NetApp ONTAP Vscan on demand task configuration.
- netapp.ontap.na_ontap_vscan_scanner_pool - NetApp ONTAP Vscan Scanner Pools Configuration.

v2.7.0
======

New Modules
-----------

- netapp.ontap.na_ontap_autosupport - NetApp ONTAP Autosupport
- netapp.ontap.na_ontap_cg_snapshot - NetApp ONTAP manage consistency group snapshot
- netapp.ontap.na_ontap_cluster_peer - NetApp ONTAP Manage Cluster peering
- netapp.ontap.na_ontap_command - NetApp ONTAP Run any cli command, the username provided needs to have console login permission.
- netapp.ontap.na_ontap_disks - NetApp ONTAP Assign disks to nodes
- netapp.ontap.na_ontap_dns - NetApp ONTAP Create, delete, modify DNS servers.
- netapp.ontap.na_ontap_fcp - NetApp ONTAP Start, Stop and Enable FCP services.
- netapp.ontap.na_ontap_firewall_policy - NetApp ONTAP Manage a firewall policy
- netapp.ontap.na_ontap_motd - Setup motd
- netapp.ontap.na_ontap_node - NetApp ONTAP Rename a node.
- netapp.ontap.na_ontap_snapmirror - NetApp ONTAP or ElementSW Manage SnapMirror
- netapp.ontap.na_ontap_software_update - NetApp ONTAP Update Software
- netapp.ontap.na_ontap_svm_options - NetApp ONTAP Modify SVM Options
- netapp.ontap.na_ontap_vserver_peer - NetApp ONTAP Vserver peering

v2.6.0
======

New Modules
-----------

- netapp.ontap.na_ontap_aggregate - NetApp ONTAP manage aggregates.
- netapp.ontap.na_ontap_broadcast_domain - NetApp ONTAP manage broadcast domains.
- netapp.ontap.na_ontap_broadcast_domain_ports - NetApp ONTAP manage broadcast domain ports
- netapp.ontap.na_ontap_cifs - NetApp ONTAP Manage cifs-share
- netapp.ontap.na_ontap_cifs_acl - NetApp ONTAP manage cifs-share-access-control
- netapp.ontap.na_ontap_cifs_server - NetApp ONTAP CIFS server configuration
- netapp.ontap.na_ontap_cluster - NetApp ONTAP cluster - create a cluster and add/remove nodes.
- netapp.ontap.na_ontap_cluster_ha - NetApp ONTAP Manage HA status for cluster
- netapp.ontap.na_ontap_export_policy - NetApp ONTAP manage export-policy
- netapp.ontap.na_ontap_export_policy_rule - NetApp ONTAP manage export policy rules
- netapp.ontap.na_ontap_igroup - NetApp ONTAP iSCSI or FC igroup configuration
- netapp.ontap.na_ontap_interface - NetApp ONTAP LIF configuration
- netapp.ontap.na_ontap_iscsi - NetApp ONTAP manage iSCSI service
- netapp.ontap.na_ontap_job_schedule - NetApp ONTAP Job Schedule
- netapp.ontap.na_ontap_license - NetApp ONTAP protocol and feature licenses
- netapp.ontap.na_ontap_lun - NetApp ONTAP manage LUNs
- netapp.ontap.na_ontap_lun_map - NetApp ONTAP LUN maps
- netapp.ontap.na_ontap_net_ifgrp - NetApp Ontap modify network interface group
- netapp.ontap.na_ontap_net_port - NetApp ONTAP network ports.
- netapp.ontap.na_ontap_net_routes - NetApp ONTAP network routes
- netapp.ontap.na_ontap_net_vlan - NetApp ONTAP network VLAN
- netapp.ontap.na_ontap_nfs - NetApp ONTAP NFS status
- netapp.ontap.na_ontap_ntp - NetApp ONTAP NTP server
- netapp.ontap.na_ontap_qtree - NetApp ONTAP manage qtrees
- netapp.ontap.na_ontap_service_processor_network - NetApp ONTAP service processor network
- netapp.ontap.na_ontap_snapshot - NetApp ONTAP manage Snapshots
- netapp.ontap.na_ontap_snmp - NetApp ONTAP SNMP community
- netapp.ontap.na_ontap_svm - NetApp ONTAP SVM
- netapp.ontap.na_ontap_ucadapter - NetApp ONTAP UC adapter configuration
- netapp.ontap.na_ontap_user - NetApp ONTAP user configuration and management
- netapp.ontap.na_ontap_user_role - NetApp ONTAP user role configuration and management
- netapp.ontap.na_ontap_volume - NetApp ONTAP manage volumes.
- netapp.ontap.na_ontap_volume_clone - NetApp ONTAP manage volume clones.
