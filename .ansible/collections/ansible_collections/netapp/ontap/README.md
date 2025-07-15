[![Documentation](https://img.shields.io/badge/docs-brightgreen.svg)](https://docs.ansible.com/ansible/devel/collections/netapp/ontap/index.html)
![example workflow](https://github.com/ansible-collections/netapp.ontap/actions/workflows/main.yml/badge.svg)
[![codecov](https://codecov.io/gh/ansible-collections/netapp.ontap/branch/main/graph/badge.svg?token=weBYkksxSi)](https://codecov.io/gh/ansible-collections/netapp.ontap)
[![Discord](https://img.shields.io/discord/855068651522490400)](https://discord.gg/NetApp)

=============================================================

 netapp.ontap

 NetApp ONTAP Collection

 Copyright (c) 2025 NetApp, Inc. All rights reserved.
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
- ansible-core >= 2.16
- requests >= 2.20
- netapp-lib version >= 2018.11.13 (For ZAPI)

# Module documentation
https://docs.ansible.com/ansible/devel/collections/netapp/ontap/

# Need help
Join our [Discord](https://discord.gg/NetApp) and look for our #ansible channel.

# Deprecation warning
With collection version 22.0.0 ONTAPI (ZAPI) has been deprecated. Please refer to [CPC](https://mysupport.netapp.com/info/communications/ECMLP2880232.html) to stay updated with the End-of-Availability announcement. 
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
The following modules do not have REST equivalent APIs.
  - na_ontap_file_directory_policy
  - na_ontap_svm_options
  - na_ontap_quota_policy

# Release Notes
Please refer to [CHANGELOG.md](https://github.com/ansible-collections/netapp.ontap/blob/main/CHANGELOG.md) for release notes.

# Related Information
For debugging connectivity issues or for tracing API calls, please refer to [this page](https://github.com/ansible-collections/netapp.ontap/wiki/Debugging).

For creating any new issues or enhancements, please visit [this page](https://github.com/ansible-collections/netapp.ontap/issues/new/choose).

# License Information
GNU General Public License v3.0
See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.
