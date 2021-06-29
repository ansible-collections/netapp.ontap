Role Name
=========

This role deletes an ONTAP vserver and dependents:
- all volumes are deleted, including any user data !!!
- clones and snapshots are deleted as well !!!
- network interfaces are deleted
- as the vserver is deleted, the associated, DNS entries, routes, NFS/CIFS/iSCSI servers as applicable, export policies and rules, are automatically deleted by ONTAP.

Requirements
------------

- ONTAP collection.
- ONTAP with REST support (9.6 or later).

- The module requires the jmespath python package.

Role Variables
--------------

This role expects the following variables to be set:
- hostname: IP address of ONTAP admin interface (can be vsadmin too).
- username: user account with admin or vsadmin role.
- password: for the user account with admin or vsadmin role.
- vserver_name: name of vserver to delete.

The following variables are preset but can be changed
- https: true 
- validate_certs: true     (true is strongly recommended)
- debug_level: 0
- enable_check_mode: false
- confirm_before_removing_volumes: true
- confirm_before_removing_interfaces: true


Example Playbook
----------------



```
---
- hosts: localhost
  gather_facts: no
  vars:
    login: &login
      hostname: ip_address
      username: admin
      password: XXXXXXXXX
      https: true
      validate_certs: false
  roles:
    - role: netapp.ontap.na_ontap_vserver_delete
      vars:
        <<: *login
        vserver_name: ansibleSVM
        # uncomment the following line to accept volumes will be permanently deleted
        # removing_volumes_permanently_destroy_user_data: I agree
        # turn confirmation prompts on or off
        confirm_before_removing_interfaces: false
        # optional - change the following to false to remove any confirmation prompt before deleting volumes !!!
        # when confirmations are on, you may receive two prompts:
        # 1. delete all clones if they exist.  The prompt is not shown if no clone exists.
        # 2. delete all volumes if any.  The prompt is not shown if no volume exists.
        confirm_before_removing_volumes: true

```

License
-------

BSD

Author Information
------------------

https://github.com/ansible-collections/netapp.ontap
