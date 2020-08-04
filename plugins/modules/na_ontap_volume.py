#!/usr/bin/python

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''

module: na_ontap_volume

short_description: NetApp ONTAP manage volumes.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '2.6'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
- Create or destroy or modify volumes on NetApp ONTAP.

options:

  state:
    description:
    - Whether the specified volume should exist or not.
    choices: ['present', 'absent']
    type: str
    default: 'present'

  name:
    description:
    - The name of the volume to manage.
    type: str
    required: true

  vserver:
    description:
    - Name of the vserver to use.
    type: str
    required: true

  from_name:
    description:
    - Name of the existing volume to be renamed to name.
    type: str
    version_added: 2.7.0

  is_infinite:
    type: bool
    description:
      Set True if the volume is an Infinite Volume.
      Deleting an infinite volume is asynchronous.

  is_online:
    type: bool
    description:
    - Whether the specified volume is online, or not.
    default: True

  aggregate_name:
    description:
    - The name of the aggregate the flexvol should exist on.
    - Required when C(state=present).
    type: str

  size:
    description:
    - The size of the volume in (size_unit). Required when C(state=present).
    type: int

  size_unit:
    description:
    - The unit used to interpret the size parameter.
    choices: ['bytes', 'b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb', 'zb', 'yb']
    type: str
    default: 'gb'

  type:
    description:
    - The volume type, either read-write (RW) or data-protection (DP).
    type: str

  policy:
    description:
    - Name of the export policy.
    type: str

  junction_path:
    description:
    - Junction path of the volume.
    - To unmount, use junction path C('').
    type: str

  space_guarantee:
    description:
    - Space guarantee style for the volume.
    choices: ['none', 'file', 'volume']
    type: str

  percent_snapshot_space:
    description:
    - Amount of space reserved for snapshot copies of the volume.
    type: int

  volume_security_style:
    description:
    - The security style associated with this volume.
    choices: ['mixed', 'ntfs', 'unified', 'unix']
    default: 'unix'
    type: str

  encrypt:
    type: bool
    description:
    - Whether or not to enable Volume Encryption.
    default: False
    version_added: 2.7.0

  efficiency_policy:
    description:
    - Allows a storage efficiency policy to be set on volume creation.
    type: str
    version_added: 2.7.0

  unix_permissions:
    description:
    - Unix permission bits in octal or symbolic format.
    - For example, 0 is equivalent to ------------, 777 is equivalent to ---rwxrwxrwx,both formats are accepted.
    - The valid octal value ranges between 0 and 777 inclusive.
    type: str
    version_added: 2.8.0

  group_id:
    description:
    - The UNIX group ID for the volume. The default value is 0 ('root').
    type: int
    version_added: '20.1.0'

  user_id:
    description:
    - The UNIX user ID for the volume. The default value is 0 ('root').
    type: int
    version_added: '20.1.0'

  snapshot_policy:
    description:
    - The name of the snapshot policy.
    - the default policy name is 'default'.
    type: str
    version_added: 2.8.0

  aggr_list:
    description:
    -  an array of names of aggregates to be used for FlexGroup constituents.
    type: list
    elements: str
    version_added: 2.8.0

  aggr_list_multiplier:
    description:
    -  The number of times to iterate over the aggregates listed with the aggr_list parameter when creating a FlexGroup.
    type: int
    version_added: 2.8.0

  auto_provision_as:
    description:
    - Automatically provision a FlexGroup volume.
    version_added: 2.8.0
    choices: ['flexgroup']
    type: str

  snapdir_access:
    description:
    - This is an advanced option, the default is False.
    - Enable the visible '.snapshot' directory that is normally present at system internal mount points.
    - This value also turns on access to all other '.snapshot' directories in the volume.
    type: bool
    version_added: 2.8.0

  atime_update:
    description:
    - This is an advanced option, the default is True.
    - If false, prevent the update of inode access times when a file is read.
    - This value is useful for volumes with extremely high read traffic,
      since it prevents writes to the inode file for the volume from contending with reads from other files.
    - This field should be used carefully.
    - That is, use this field when you know in advance that the correct access time for inodes will not be needed for files on that volume.
    type: bool
    version_added: 2.8.0

  wait_for_completion:
    description:
    - Set this parameter to 'true' for synchronous execution during create (wait until volume status is online)
    - Set this parameter to 'false' for asynchronous execution
    - For asynchronous, execution exits as soon as the request is sent, without checking volume status
    type: bool
    default: false
    version_added: 2.8.0

  time_out:
    description:
    - time to wait for flexGroup creation, modification, or deletion in seconds.
    - Error out if task is not completed in defined time.
    - if 0, the request is asynchronous.
    - default is set to 3 minutes.
    default: 180
    type: int
    version_added: 2.8.0

  language:
    description:
    - Language to use for Volume
    - Default uses SVM language
    - Possible values   Language
    - c                 POSIX
    - ar                Arabic
    - cs                Czech
    - da                Danish
    - de                German
    - en                English
    - en_us             English (US)
    - es                Spanish
    - fi                Finnish
    - fr                French
    - he                Hebrew
    - hr                Croatian
    - hu                Hungarian
    - it                Italian
    - ja                Japanese euc-j
    - ja_v1             Japanese euc-j
    - ja_jp.pck         Japanese PCK (sjis)
    - ja_jp.932         Japanese cp932
    - ja_jp.pck_v2      Japanese PCK (sjis)
    - ko                Korean
    - no                Norwegian
    - nl                Dutch
    - pl                Polish
    - pt                Portuguese
    - ro                Romanian
    - ru                Russian
    - sk                Slovak
    - sl                Slovenian
    - sv                Swedish
    - tr                Turkish
    - zh                Simplified Chinese
    - zh.gbk            Simplified Chinese (GBK)
    - zh_tw             Traditional Chinese euc-tw
    - zh_tw.big5        Traditional Chinese Big 5
    - To use UTF-8 as the NFS character set, append '.UTF-8' to the language code
    type: str
    version_added: 2.8.0

  qos_policy_group:
    description:
    - Specifies a QoS policy group to be set on volume.
    type: str
    version_added: 2.9.0

  qos_adaptive_policy_group:
    description:
    - Specifies a QoS adaptive policy group to be set on volume.
    type: str
    version_added: 2.9.0

  tiering_policy:
    description:
    - The tiering policy that is to be associated with the volume.
    - This policy decides whether the blocks of a volume will be tiered to the capacity tier.
    - snapshot-only policy allows tiering of only the volume snapshot copies not associated with the active file system.
    - auto policy allows tiering of both snapshot and active file system user data to the capacity tier.
    - backup policy on DP volumes allows all transferred user data blocks to start in the capacity tier.
    - When set to none, the Volume blocks will not be tiered to the capacity tier.
    - If no value specified, the volume is assigned snapshot only by default.
    - Requires ONTAP 9.4 or later.
    choices: ['snapshot-only', 'auto', 'backup', 'none']
    type: str
    version_added: 2.9.0

  space_slo:
    description:
    - Specifies the space SLO type for the volume. The space SLO type is the Service Level Objective for space management for the volume.
    - The space SLO value is used to enforce existing volume settings so that sufficient space is set aside on the aggregate to meet the space SLO.
    - This parameter is not supported on Infinite Volumes.
    choices: ['none', 'thick', 'semi-thick']
    type: str
    version_added: 2.9.0

  nvfail_enabled:
    description:
    - If true, the controller performs additional work at boot and takeover times if it finds that there has been any potential data loss in the volume's
      constituents due to an NVRAM failure.
    - The volume's constituents would be put in a special state called 'in-nvfailed-state' such that protocol access is blocked.
    - This will cause the client applications to crash and thus prevent access to stale data.
    - To get out of this situation, the admin needs to manually clear the 'in-nvfailed-state' on the volume's constituents.
    type: bool
    version_added: 2.9.0

  vserver_dr_protection:
    description:
    - Specifies the protection type for the volume in a Vserver DR setup.
    choices: ['protected', 'unprotected']
    type: str
    version_added: 2.9.0

  comment:
    description:
    - Sets a comment associated with the volume.
    type: str
    version_added: 2.9.0

  snapshot_auto_delete:
    description:
    - A dictionary for the auto delete options and values.
    - Supported options include 'state', 'commitment', 'trigger', 'target_free_space', 'delete_order', 'defer_delete',
      'prefix', 'destroy_list'.
    - Option 'state' determines if the snapshot autodelete is currently enabled for the volume. Possible values are 'on' and 'off'.
    - Option 'commitment' determines the snapshots which snapshot autodelete is allowed to delete to get back space.
      Possible values are 'try', 'disrupt' and 'destroy'.
    - Option 'trigger' determines the condition which starts the automatic deletion of snapshots.
      Possible values are 'volume', 'snap_reserve' and DEPRECATED 'space_reserve'.
    - Option 'target_free_space' determines when snapshot autodelete should stop deleting snapshots. Depending on the trigger,
      snapshots are deleted till we reach the target free space percentage. Accepts int type.
    - Option 'delete_order' determines if the oldest or newest snapshot is deleted first. Possible values are 'newest_first' and 'oldest_first'.
    - Option 'defer_delete' determines which kind of snapshots to delete in the end. Possible values are 'scheduled', 'user_created',
      'prefix' and 'none'.
    - Option 'prefix' can be set to provide the prefix string for the 'prefix' value of the 'defer_delete' option.
      The prefix string length can be 15 char long.
    - Option 'destroy_list' is a comma seperated list of services which can be destroyed if the snapshot backing that service is deleted.
      For 7-mode, the possible values for this option are a combination of 'lun_clone', 'vol_clone', 'cifs_share', 'file_clone' or 'none'.
      For cluster-mode, the possible values for this option are a combination of 'lun_clone,file_clone' (for LUN clone and/or file clone),
      'lun_clone,sfsr' (for LUN clone and/or sfsr), 'vol_clone', 'cifs_share', or 'none'.
    type: dict
    version_added: '20.4.0'

  cutover_action:
    description:
    - Specifies the action to be taken for cutover.
    - Possible values are 'abort_on_failure', 'defer_on_failure', 'force' and 'wait'. Default is 'defer_on_failure'.
    choices: ['abort_on_failure', 'defer_on_failure', 'force', 'wait']
    type: str
    version_added: '20.5.0'

  check_interval:
    description:
    - The amount of time in seconds to wait between checks of a volume to see if it has moved successfully.
    default: 30
    type: int
    version_added: '20.6.0'

  from_vserver:
    description:
    - The source vserver of the volume is rehosted.
    type: str
    version_added: '20.6.0'

  auto_remap_luns:
    description:
    - Flag to control automatic map of LUNs.
    type: bool
    version_added: '20.6.0'

  force_unmap_luns:
    description:
    - Flag to control automatic unmap of LUNs.
    type: bool
    version_added: '20.6.0'

  force_restore:
    description:
    - If this field is set to "true", the Snapshot copy is restored even if the volume has one or more newer Snapshot
      copies which are currently used as reference Snapshot copy by SnapMirror. If a restore is done in this
      situation, this will cause future SnapMirror transfers to fail.
    - Option should only be used along with snapshot_restore.
    type: bool
    version_added: '20.6.0'

  preserve_lun_ids:
    description:
    - If this field is set to "true", LUNs in the volume being restored will remain mapped and their identities
      preserved such that host connectivity will not be disrupted during the restore operation. I/O's to the LUN will
      be fenced during the restore operation by placing the LUNs in an unavailable state. Once the restore operation
      has completed, hosts will be able to resume I/O access to the LUNs.
    - Option should only be used along with snapshot_restore.
    type: bool
    version_added: '20.6.0'

  snapshot_restore:
    description:
    - Name of snapshot to restore from.
    - Not supported on Infinite Volume.
    type: str
    version_added: '20.6.0'
'''

EXAMPLES = """

    - name: Create FlexVol
      na_ontap_volume:
        state: present
        name: ansibleVolume12
        is_infinite: False
        aggregate_name: ansible_aggr
        size: 100
        size_unit: mb
        user_id: 1001
        group_id: 2002
        space_guarantee: none
        tiering_policy: auto
        policy: default
        percent_snapshot_space: 60
        qos_policy_group: max_performance_gold
        vserver: ansibleVServer
        wait_for_completion: True
        space_slo: none
        nvfail_enabled: False
        comment: ansible created volume
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Volume Delete
      na_ontap_volume:
        state: absent
        name: ansibleVolume12
        aggregate_name: ansible_aggr
        vserver: ansibleVServer
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Make FlexVol offline
      na_ontap_volume:
        state: present
        name: ansibleVolume
        is_infinite: False
        is_online: False
        vserver: ansibleVServer
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Create flexGroup volume manually
      na_ontap_volume:
        state: present
        name: ansibleVolume
        is_infinite: False
        aggr_list: "{{ aggr_list }}"
        aggr_list_multiplier: 2
        size: 200
        size_unit: mb
        space_guarantee: none
        policy: default
        vserver: "{{ vserver }}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: False
        unix_permissions: 777
        snapshot_policy: default
        time_out: 0

    - name: Create flexGroup volume auto provsion as flex group
      na_ontap_volume:
        state: present
        name: ansibleVolume
        is_infinite: False
        auto_provision_as: flexgroup
        size: 200
        size_unit: mb
        space_guarantee: none
        policy: default
        vserver: "{{ vserver }}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: False
        unix_permissions: 777
        snapshot_policy: default
        time_out: 0

    - name: Create FlexVol with QoS adaptive
      na_ontap_volume:
        state: present
        name: ansibleVolume15
        is_infinite: False
        aggregate_name: ansible_aggr
        size: 100
        size_unit: gb
        space_guarantee: none
        policy: default
        percent_snapshot_space: 10
        qos_adaptive_policy_group: extreme
        vserver: ansibleVServer
        wait_for_completion: True
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"

    - name: Modify volume dr protection (vserver of the volume must be in a snapmirror relationship)
      na_ontap_volume:
        state: present
        name: ansibleVolume
        vserver_dr_protection: protected
        vserver: "{{ vserver }}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: False

    - name: Modify volume with snapshot auto delete options
      na_ontap_volume:
        state: present
        name: vol_auto_delete
        snapshot_auto_delete:
          state: "on"
          commitment: try
          defer_delete: scheduled
          target_free_space: 30
          destroy_list: lun_clone,vol_clone
          delete_order: newest_first
        aggregate_name: "{{ aggr }}"
        vserver: "{{ vserver }}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: False

    - name: Move volume with force cutover action
      na_ontap_volume:
        name: ansible_vol
        aggregate_name: aggr_ansible
        cutover_action: force
        vserver: "{{ vserver }}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: false

    - name: Rehost volume to another vserver auto remap luns
      na_ontap_volume:
        name: ansible_vol
        from_vserver: ansible
        auto_remap_luns: true
        vserver: "{{ vserver }}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: false

    - name: Rehost volume to another vserver force unmap luns
      na_ontap_volume:
        name: ansible_vol
        from_vserver: ansible
        force_unmap_luns: true
        vserver: "{{ vserver }}"
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: false

    - name: Snapshot restore volume
      na_ontap_volume:
        name: ansible_vol
        vserver: ansible
        snapshot_restore: 2020-05-24-weekly
        force_restore: true
        preserve_lun_ids: true
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        https: false
"""

RETURN = """
"""

import time
import traceback
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapVolume(object):
    '''Class with volume operations'''

    def __init__(self):
        '''Initialize module parameters'''
        self._size_unit_map = dict(
            bytes=1,
            b=1,
            kb=1024,
            mb=1024 ** 2,
            gb=1024 ** 3,
            tb=1024 ** 4,
            pb=1024 ** 5,
            eb=1024 ** 6,
            zb=1024 ** 7,
            yb=1024 ** 8
        )

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            name=dict(required=True, type='str'),
            vserver=dict(required=True, type='str'),
            from_name=dict(required=False, type='str'),
            is_infinite=dict(required=False, type='bool', default=False),
            is_online=dict(required=False, type='bool', default=True),
            size=dict(type='int', default=None),
            size_unit=dict(default='gb', choices=['bytes', 'b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb', 'zb', 'yb'], type='str'),
            aggregate_name=dict(type='str', default=None),
            type=dict(type='str', default=None),
            policy=dict(type='str', default=None),
            junction_path=dict(type='str', default=None),
            space_guarantee=dict(choices=['none', 'file', 'volume'], default=None),
            percent_snapshot_space=dict(type='int', default=None),
            volume_security_style=dict(choices=['mixed', 'ntfs', 'unified', 'unix'], default='unix'),
            encrypt=dict(required=False, type='bool', default=False),
            efficiency_policy=dict(required=False, type='str'),
            unix_permissions=dict(required=False, type='str'),
            group_id=dict(required=False, type='int'),
            user_id=dict(required=False, type='int'),
            snapshot_policy=dict(required=False, type='str'),
            aggr_list=dict(required=False, type='list', elements='str'),
            aggr_list_multiplier=dict(required=False, type='int'),
            snapdir_access=dict(required=False, type='bool'),
            atime_update=dict(required=False, type='bool'),
            auto_provision_as=dict(choices=['flexgroup'], required=False, type='str'),
            wait_for_completion=dict(required=False, type='bool', default=False),
            time_out=dict(required=False, type='int', default=180),
            language=dict(type='str', required=False),
            qos_policy_group=dict(required=False, type='str'),
            qos_adaptive_policy_group=dict(required=False, type='str'),
            nvfail_enabled=dict(type='bool', required=False),
            space_slo=dict(type='str', required=False, choices=['none', 'thick', 'semi-thick']),
            tiering_policy=dict(type='str', required=False, choices=['snapshot-only', 'auto', 'backup', 'none']),
            vserver_dr_protection=dict(type='str', required=False, choices=['protected', 'unprotected']),
            comment=dict(type='str', required=False),
            snapshot_auto_delete=dict(type='dict', required=False),
            cutover_action=dict(required=False, type='str', choices=['abort_on_failure', 'defer_on_failure', 'force', 'wait']),
            check_interval=dict(required=False, type='int', default=30),
            from_vserver=dict(required=False, type='str'),
            auto_remap_luns=dict(required=False, type='bool'),
            force_unmap_luns=dict(required=False, type='bool'),
            force_restore=dict(required=False, type='bool'),
            preserve_lun_ids=dict(required=False, type='bool'),
            snapshot_restore=dict(required=False, type='str')
        ))
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            mutually_exclusive=[
                ['space_guarantee', 'space_slo'], ['auto_remap_luns', 'force_unmap_luns']
            ],
            supports_check_mode=True
        )
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.check_and_set_parameters(self.module)
        self.volume_style = None

        if self.parameters.get('size'):
            self.parameters['size'] = self.parameters['size'] * \
                self._size_unit_map[self.parameters['size_unit']]
        # ONTAP will return True and False as the string true and false.
        if 'snapdir_access' in self.parameters:
            self.parameters['snapdir_access'] = str(self.parameters['snapdir_access']).lower()
        if 'atime_update' in self.parameters:
            self.parameters['atime_update'] = str(self.parameters['atime_update']).lower()
        if 'snapshot_auto_delete' in self.parameters:
            for key in self.parameters['snapshot_auto_delete']:
                if key not in ['commitment', 'trigger', 'target_free_space', 'delete_order', 'defer_delete',
                               'prefix', 'destroy_list', 'state']:
                    self.module.fail_json(msg="snapshot_auto_delete option '%s' is not valid." % key)
        if HAS_NETAPP_LIB is False:
            self.module.fail_json(
                msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(
                module=self.module, vserver=self.parameters['vserver'])
            self.cluster = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def volume_get_iter(self, vol_name=None):
        """
        Return volume-get-iter query results
        :param vol_name: name of the volume
        :return: NaElement
        """
        volume_info = netapp_utils.zapi.NaElement('volume-get-iter')
        volume_attributes = netapp_utils.zapi.NaElement('volume-attributes')
        volume_id_attributes = netapp_utils.zapi.NaElement('volume-id-attributes')
        volume_id_attributes.add_new_child('name', vol_name)
        volume_id_attributes.add_new_child('vserver', self.parameters['vserver'])
        volume_attributes.add_child_elem(volume_id_attributes)
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(volume_attributes)
        volume_info.add_child_elem(query)

        try:
            result = self.server.invoke_successfully(volume_info, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching volume %s : %s'
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        return result

    def get_volume(self, vol_name=None):
        """
        Return details about the volume
        :param:
            name : Name of the volume
        :return: Details about the volume. None if not found.
        :rtype: dict
        """
        if vol_name is None:
            vol_name = self.parameters['name']
        volume_get_iter = self.volume_get_iter(vol_name)
        return_value = None
        if volume_get_iter.get_child_by_name('num-records') and \
                int(volume_get_iter.get_child_content('num-records')) > 0:

            volume_attributes = volume_get_iter['attributes-list']['volume-attributes']
            volume_space_attributes = volume_attributes['volume-space-attributes']
            volume_state_attributes = volume_attributes['volume-state-attributes']
            volume_id_attributes = volume_attributes['volume-id-attributes']
            try:
                volume_export_attributes = volume_attributes['volume-export-attributes']
            except KeyError:  # does not exist for MDV volumes
                volume_export_attributes = None
            volume_security_unix_attributes = volume_attributes['volume-security-attributes']['volume-security-unix-attributes']
            volume_snapshot_attributes = volume_attributes['volume-snapshot-attributes']
            volume_performance_attributes = volume_attributes['volume-performance-attributes']
            volume_snapshot_auto_delete_attributes = volume_attributes['volume-snapshot-autodelete-attributes']
            try:
                volume_comp_aggr_attributes = volume_attributes['volume-comp-aggr-attributes']
            except KeyError:  # Not supported in 9.1 to 9.3
                volume_comp_aggr_attributes = None
            # Get volume's state (online/offline)
            current_state = volume_state_attributes['state']
            is_online = (current_state == "online")

            return_value = {
                'name': vol_name,
                'size': int(volume_space_attributes['size']),
                'is_online': is_online,
                'unix_permissions': volume_security_unix_attributes['permissions'],
                'snapshot_policy': volume_snapshot_attributes['snapshot-policy']
            }
            if volume_export_attributes is not None:
                return_value['policy'] = volume_export_attributes['policy']
            else:
                return_value['policy'] = None
            if volume_security_unix_attributes.get_child_by_name('group-id'):
                return_value['group_id'] = int(volume_security_unix_attributes['group-id'])
            if volume_security_unix_attributes.get_child_by_name('user-id'):
                return_value['user_id'] = int(volume_security_unix_attributes['user-id'])
            if self.parameters.get('efficiency_policy'):
                return_value['efficiency_policy'] = self.get_efficiency_policy()
            if volume_comp_aggr_attributes is not None:
                return_value['tiering_policy'] = volume_comp_aggr_attributes['tiering-policy']
            if volume_space_attributes.get_child_by_name('encrypt'):
                return_value['encrypt'] = volume_attributes['encrypt']
            if volume_space_attributes.get_child_by_name('percentage-snapshot-reserve'):
                return_value['percent_snapshot_space'] = int(volume_space_attributes['percentage-snapshot-reserve'])
            if volume_space_attributes.get_child_by_name('space-slo'):
                return_value['space_slo'] = volume_space_attributes['space-slo']
            else:
                return_value['space_slo'] = None
            if volume_state_attributes.get_child_by_name('is-nvfail-enabled') is not None:
                return_value['nvfail_enabled'] = volume_state_attributes['is-nvfail-enabled'] == 'true'
            else:
                return_value['nvfail_enabled'] = None
            if volume_id_attributes.get_child_by_name('containing-aggregate-name'):
                return_value['aggregate_name'] = volume_id_attributes['containing-aggregate-name']
            else:
                return_value['aggregate_name'] = None
            if volume_id_attributes.get_child_by_name('junction-path'):
                return_value['junction_path'] = volume_id_attributes['junction-path']
            else:
                return_value['junction_path'] = ''
            if volume_id_attributes.get_child_by_name('comment'):
                return_value['comment'] = volume_id_attributes['comment']
            else:
                return_value['comment'] = None
            if volume_attributes['volume-security-attributes'].get_child_by_name('style'):
                # style is not present if the volume is still offline or of type: dp
                return_value['volume_security_style'] = volume_attributes['volume-security-attributes']['style']
            if volume_id_attributes.get_child_by_name('style-extended'):
                return_value['style_extended'] = volume_id_attributes['style-extended']
            else:
                return_value['style_extended'] = None
            if volume_space_attributes.get_child_by_name('space-guarantee'):
                return_value['space_guarantee'] = volume_space_attributes['space-guarantee']
            else:
                return_value['space_guarantee'] = None
            if volume_snapshot_attributes.get_child_by_name('snapdir-access-enabled'):
                return_value['snapdir_access'] = volume_snapshot_attributes['snapdir-access-enabled']
            else:
                return_value['snapdir_access'] = None
            if volume_performance_attributes.get_child_by_name('is-atime-update-enabled'):
                return_value['atime_update'] = volume_performance_attributes['is-atime-update-enabled']
            else:
                return_value['atime_update'] = None
            if volume_attributes.get_child_by_name('volume-qos-attributes'):
                volume_qos_attributes = volume_attributes['volume-qos-attributes']
                if volume_qos_attributes.get_child_by_name('policy-group-name'):
                    return_value['qos_policy_group'] = volume_qos_attributes['policy-group-name']
                else:
                    return_value['qos_policy_group'] = None
                if volume_qos_attributes.get_child_by_name('adaptive-policy-group-name'):
                    return_value['qos_adaptive_policy_group'] = volume_qos_attributes['adaptive-policy-group-name']
                else:
                    return_value['qos_adaptive_policy_group'] = None
            else:
                return_value['qos_policy_group'] = None
                return_value['qos_adaptive_policy_group'] = None
            if volume_attributes.get_child_by_name('volume-vserver-dr-protection-attributes'):
                volume_vserver_dr_protection_attributes = volume_attributes['volume-vserver-dr-protection-attributes']
                if volume_vserver_dr_protection_attributes.get_child_by_name('vserver-dr-protection'):
                    return_value['vserver_dr_protection'] = volume_vserver_dr_protection_attributes['vserver-dr-protection']
                else:
                    return_value['vserver_dr_protection'] = None
            # snapshot_auto_delete options
            auto_delete = dict()
            if volume_snapshot_auto_delete_attributes.get_child_by_name('commitment'):
                auto_delete['commitment'] = volume_snapshot_auto_delete_attributes['commitment']
            else:
                auto_delete['commitment'] = None
            if volume_snapshot_auto_delete_attributes.get_child_by_name('defer-delete'):
                auto_delete['defer_delete'] = volume_snapshot_auto_delete_attributes['defer-delete']
            else:
                auto_delete['defer_delete'] = None
            if volume_snapshot_auto_delete_attributes.get_child_by_name('delete-order'):
                auto_delete['delete_order'] = volume_snapshot_auto_delete_attributes['delete-order']
            else:
                auto_delete['delete_order'] = None
            if volume_snapshot_auto_delete_attributes.get_child_by_name('destroy-list'):
                auto_delete['destroy_list'] = volume_snapshot_auto_delete_attributes['destroy-list']
            else:
                auto_delete['destroy_list'] = None
            if volume_snapshot_auto_delete_attributes.get_child_by_name('is-autodelete-enabled'):
                if volume_snapshot_auto_delete_attributes['is-autodelete-enabled'] == 'false':
                    auto_delete['state'] = 'off'
                else:
                    auto_delete['state'] = 'on'
            else:
                auto_delete['is_autodelete_enabled'] = None
            if volume_snapshot_auto_delete_attributes.get_child_by_name('prefix'):
                auto_delete['prefix'] = volume_snapshot_auto_delete_attributes['prefix']
            else:
                auto_delete['prefix'] = None
            if volume_snapshot_auto_delete_attributes.get_child_by_name('target-free-space'):
                auto_delete['target_free_space'] = int(volume_snapshot_auto_delete_attributes['target-free-space'])
            else:
                auto_delete['target_free_space'] = None
            if volume_snapshot_auto_delete_attributes.get_child_by_name('trigger'):
                auto_delete['trigger'] = volume_snapshot_auto_delete_attributes['trigger']
            else:
                auto_delete['trigger'] = None
            return_value['snapshot_auto_delete'] = auto_delete

        return return_value

    def create_volume(self):
        '''Create ONTAP volume'''
        if self.volume_style == 'flexGroup':
            self.create_volume_async()
        else:
            options = self.create_volume_options()
            volume_create = netapp_utils.zapi.NaElement.create_node_with_children('volume-create', **options)
            try:
                self.server.invoke_successfully(volume_create, enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error provisioning volume %s of size %s: %s'
                                      % (self.parameters['name'], self.parameters['size'], to_native(error)),
                                      exception=traceback.format_exc())
            self.ems_log_event("volume-create")

            if self.parameters.get('wait_for_completion'):
                # round off time_out
                retries = (self.parameters['time_out'] + 5) // 10
                is_online = None
                errors = list()
                while not is_online and retries > 0:
                    try:
                        current = self.get_volume()
                        is_online = None if current is None else current['is_online']
                    except KeyError as err:
                        # get_volume may receive incomplete data as the volume is being created
                        errors.append(repr(err))
                    if not is_online:
                        time.sleep(10)
                    retries = retries - 1
                if not is_online:
                    errors.append("Timeout after %s seconds" % self.parameters['time_out'])
                    self.module.fail_json(msg='Error waiting for volume %s to come online: %s'
                                          % (self.parameters['name'], str(errors)))

        if self.parameters.get('efficiency_policy'):
            self.assign_efficiency_policy()

        if self.parameters.get('snapshot_auto_delete'):
            self.set_snapshot_auto_delete()

    def create_volume_async(self):
        '''
        create volume async.
        '''
        options = self.create_volume_options()
        volume_create = netapp_utils.zapi.NaElement.create_node_with_children('volume-create-async', **options)
        if self.parameters.get('aggr_list'):
            aggr_list_obj = netapp_utils.zapi.NaElement('aggr-list')
            volume_create.add_child_elem(aggr_list_obj)
            for aggr in self.parameters['aggr_list']:
                aggr_list_obj.add_new_child('aggr-name', aggr)
        try:
            result = self.server.invoke_successfully(volume_create, enable_tunneling=True)
            self.ems_log_event("volume-create")
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error provisioning volume %s of size %s: %s'
                                  % (self.parameters['name'], self.parameters['size'], to_native(error)),
                                  exception=traceback.format_exc())
        self.check_invoke_result(result, 'create')

        if self.parameters.get('efficiency_policy'):
            self.assign_efficiency_policy_async()

    def create_volume_options(self):
        '''Set volume options for create operation'''
        options = {}
        if self.volume_style == 'flexGroup':
            options['volume-name'] = self.parameters['name']
            if self.parameters.get('aggr_list_multiplier'):
                options['aggr-list-multiplier'] = str(self.parameters['aggr_list_multiplier'])
            if self.parameters.get('auto_provision_as'):
                options['auto-provision-as'] = self.parameters['auto_provision_as']
            if self.parameters.get('space_guarantee'):
                options['space-guarantee'] = self.parameters['space_guarantee']
        else:
            options['volume'] = self.parameters['name']
            if self.parameters.get('aggregate_name') is None:
                self.module.fail_json(msg='Error provisioning volume %s: aggregate_name is required'
                                      % self.parameters['name'])
            options['containing-aggr-name'] = self.parameters['aggregate_name']
            if self.parameters.get('space_guarantee'):
                options['space-reserve'] = self.parameters['space_guarantee']

        if self.parameters.get('size'):
            options['size'] = str(self.parameters['size'])
        if self.parameters.get('snapshot_policy'):
            options['snapshot-policy'] = self.parameters['snapshot_policy']
        if self.parameters.get('unix_permissions') is not None:
            options['unix-permissions'] = self.parameters['unix_permissions']
        if self.parameters.get('group_id') is not None:
            options['group-id'] = str(self.parameters['group_id'])
        if self.parameters.get('user_id') is not None:
            options['user-id'] = str(self.parameters['user_id'])
        if self.parameters.get('volume_security_style'):
            options['volume-security-style'] = self.parameters['volume_security_style']
        if self.parameters.get('policy'):
            options['export-policy'] = self.parameters['policy']
        if self.parameters.get('junction_path'):
            options['junction-path'] = self.parameters['junction_path']
        if self.parameters.get('comment'):
            options['volume-comment'] = self.parameters['comment']
        if self.parameters.get('type'):
            options['volume-type'] = self.parameters['type']
        if self.parameters.get('percent_snapshot_space') is not None:
            options['percentage-snapshot-reserve'] = str(self.parameters['percent_snapshot_space'])
        if self.parameters.get('language'):
            options['language-code'] = self.parameters['language']
        if self.parameters.get('qos_policy_group'):
            options['qos-policy-group-name'] = self.parameters['qos_policy_group']
        if self.parameters.get('qos_adaptive_policy_group'):
            options['qos-adaptive-policy-group-name'] = self.parameters['qos_adaptive_policy_group']
        if self.parameters.get('nvfail_enabled') is not None:
            options['is-nvfail-enabled'] = str(self.parameters['nvfail_enabled'])
        if self.parameters.get('space_slo'):
            options['space-slo'] = self.parameters['space_slo']
        if self.parameters.get('tiering_policy'):
            options['tiering-policy'] = self.parameters['tiering_policy']
        if self.parameters.get('encrypt'):
            options['encrypt'] = str(self.parameters['encrypt'])
        if self.parameters.get('vserver_dr_protection'):
            options['vserver-dr-protection'] = self.parameters['vserver_dr_protection']
        if self.parameters['is_online']:
            options['volume-state'] = 'online'
        else:
            options['volume-state'] = 'offline'
        return options

    def delete_volume(self, current):
        '''Delete ONTAP volume'''
        if self.parameters.get('is_infinite') or self.volume_style == 'flexGroup':
            if current['is_online']:
                self.change_volume_state(call_from_delete_vol=True)
            volume_delete = netapp_utils.zapi.NaElement.create_node_with_children(
                'volume-destroy-async', **{'volume-name': self.parameters['name']})
        else:
            volume_delete = netapp_utils.zapi.NaElement.create_node_with_children(
                'volume-destroy', **{'name': self.parameters['name'], 'unmount-and-offline': 'true'})
        try:
            result = self.server.invoke_successfully(volume_delete, enable_tunneling=True)
            if self.parameters.get('is_infinite') or self.volume_style == 'flexGroup':
                self.check_invoke_result(result, 'delete')
            self.ems_log_event("volume-delete")
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting volume %s: %s'
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def move_volume(self):
        '''Move volume from source aggregate to destination aggregate'''
        volume_move = netapp_utils.zapi.NaElement.create_node_with_children(
            'volume-move-start', **{'source-volume': self.parameters['name'],
                                    'vserver': self.parameters['vserver'],
                                    'dest-aggr': self.parameters['aggregate_name']})
        if self.parameters.get('cutover_action'):
            volume_move.add_new_child('cutover-action', self.parameters['cutover_action'])
        try:
            self.cluster.invoke_successfully(volume_move,
                                             enable_tunneling=True)
            self.ems_log_event("volume-move")
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error moving volume %s: %s'
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def wait_for_volume_move(self):
        waiting = True
        fail_count = 0
        while waiting:
            volume_move_iter = netapp_utils.zapi.NaElement('volume-move-get-iter')
            volume_move_info = netapp_utils.zapi.NaElement('volume-move-info')
            volume_move_info.add_new_child('volume', self.parameters['name'])
            query = netapp_utils.zapi.NaElement('query')
            query.add_child_elem(volume_move_info)
            volume_move_iter.add_child_elem(query)
            try:
                result = self.cluster.invoke_successfully(volume_move_iter, enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                if fail_count < 3:
                    fail_count += 1
                    time.sleep(self.parameters['check_interval'])
                    continue
                self.module.fail_json(msg='Error getting volume move status: %s' % (to_native(error)),
                                      exception=traceback.format_exc())
            # reset fail count to 0
            fail_count = 0
            volume_move_status = result.get_child_by_name('attributes-list').get_child_by_name('volume-move-info').\
                get_child_content('state')
            # We have 5 states that can be returned.
            # warning and healthy are state where the move is still going so we don't need to do anything for thouse.
            if volume_move_status == 'done':
                waiting = False
            if volume_move_status in ['failed', 'alert']:
                self.module.fail_json(msg='Error moving volume %s: %s' %
                                          (self.parameters['name'],
                                           result.get_child_by_name('attributes-list')[0].get_child_by_name('details')))
            time.sleep(self.parameters['check_interval'])

    def rename_volume(self):
        """
        Rename the volume.

        Note: 'is_infinite' needs to be set to True in order to rename an
        Infinite Volume. Use time_out parameter to set wait time for rename completion.
        """
        vol_rename_zapi, vol_name_zapi = ['volume-rename-async', 'volume-name'] if self.parameters['is_infinite']\
            else ['volume-rename', 'volume']
        volume_rename = netapp_utils.zapi.NaElement.create_node_with_children(
            vol_rename_zapi, **{vol_name_zapi: self.parameters['from_name'],
                                'new-volume-name': str(self.parameters['name'])})
        try:
            result = self.server.invoke_successfully(volume_rename, enable_tunneling=True)
            if vol_rename_zapi == 'volume-rename-async':
                self.check_invoke_result(result, 'rename')
            self.ems_log_event("volume-rename")
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error renaming volume %s: %s'
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def resize_volume(self):
        """
        Re-size the volume.

        Note: 'is_infinite' needs to be set to True in order to rename an
        Infinite Volume.
        """
        vol_size_zapi, vol_name_zapi = ['volume-size-async', 'volume-name']\
            if (self.parameters['is_infinite'] or self.volume_style == 'flexGroup')\
            else ['volume-size', 'volume']
        volume_resize = netapp_utils.zapi.NaElement.create_node_with_children(
            vol_size_zapi, **{vol_name_zapi: self.parameters['name'],
                              'new-size': str(self.parameters['size'])})
        try:
            result = self.server.invoke_successfully(volume_resize, enable_tunneling=True)
            if vol_size_zapi == 'volume-size-async':
                self.check_invoke_result(result, 'resize')
            self.ems_log_event("volume-resize")
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error re-sizing volume %s: %s'
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def change_volume_state(self, call_from_delete_vol=False):
        """
        Change volume's state (offline/online).
        """
        if self.parameters['is_online'] and not call_from_delete_vol:    # Desired state is online, setup zapi APIs respectively
            vol_state_zapi, vol_name_zapi, action = ['volume-online-async', 'volume-name', 'online']\
                if (self.parameters['is_infinite'] or self.volume_style == 'flexGroup')\
                else ['volume-online', 'name', 'online']
        else:   # Desired state is offline, setup zapi APIs respectively
            vol_state_zapi, vol_name_zapi, action = ['volume-offline-async', 'volume-name', 'offline']\
                if (self.parameters['is_infinite'] or self.volume_style == 'flexGroup')\
                else ['volume-offline', 'name', 'offline']
            volume_unmount = netapp_utils.zapi.NaElement.create_node_with_children(
                'volume-unmount', **{'volume-name': self.parameters['name']})
        volume_change_state = netapp_utils.zapi.NaElement.create_node_with_children(
            vol_state_zapi, **{vol_name_zapi: self.parameters['name']})
        try:
            if not self.parameters['is_online'] or call_from_delete_vol:  # Unmount before offline
                self.server.invoke_successfully(volume_unmount, enable_tunneling=True)
            result = self.server.invoke_successfully(volume_change_state, enable_tunneling=True)
            if self.volume_style == 'flexGroup' or self.parameters['is_infinite']:
                self.check_invoke_result(result, action)
            self.ems_log_event("change-state")
        except netapp_utils.zapi.NaApiError as error:
            state = "online" if self.parameters['is_online'] else "offline"
            self.module.fail_json(msg='Error changing the state of volume %s to %s: %s'
                                  % (self.parameters['name'], state, to_native(error)),
                                  exception=traceback.format_exc())

    def create_volume_attribute(self, zapi_object, parent_attribute, attribute, value):
        """

        :param parent_attribute:
        :param child_attribute:
        :param value:
        :return:
        """
        if isinstance(parent_attribute, str):
            vol_attribute = netapp_utils.zapi.NaElement(parent_attribute)
            vol_attribute.add_new_child(attribute, value)
            zapi_object.add_child_elem(vol_attribute)
        else:
            zapi_object.add_new_child(attribute, value)
            parent_attribute.add_child_elem(zapi_object)

    def volume_modify_attributes(self, params):
        """
        modify volume parameter 'policy','unix_permissions','snapshot_policy','space_guarantee', 'percent_snapshot_space',
                                'qos_policy_group', 'qos_adaptive_policy_group'
        """
        # TODO: refactor this method
        if self.volume_style == 'flexGroup' or self.parameters['is_infinite']:
            vol_mod_iter = netapp_utils.zapi.NaElement('volume-modify-iter-async')
        else:
            vol_mod_iter = netapp_utils.zapi.NaElement('volume-modify-iter')
        attributes = netapp_utils.zapi.NaElement('attributes')
        vol_mod_attributes = netapp_utils.zapi.NaElement('volume-attributes')
        # Volume-attributes is split in to 25 sub categories
        # volume-space-attributes
        vol_space_attributes = netapp_utils.zapi.NaElement('volume-space-attributes')
        if self.parameters.get('space_guarantee'):
            self.create_volume_attribute(vol_space_attributes, vol_mod_attributes,
                                         'space-guarantee', self.parameters['space_guarantee'])
        if self.parameters.get('percent_snapshot_space') is not None:
            self.create_volume_attribute(vol_space_attributes, vol_mod_attributes,
                                         'percentage-snapshot-reserve', str(self.parameters['percent_snapshot_space']))
        if self.parameters.get('space_slo'):
            self.create_volume_attribute(vol_space_attributes, vol_mod_attributes, 'space-slo', self.parameters['space_slo'])
        # volume-snapshot-attributes
        vol_snapshot_attributes = netapp_utils.zapi.NaElement('volume-snapshot-attributes')
        if self.parameters.get('snapshot_policy'):
            self.create_volume_attribute(vol_snapshot_attributes, vol_mod_attributes,
                                         'snapshot-policy', self.parameters['snapshot_policy'])
        if self.parameters.get('snapdir_access'):
            self.create_volume_attribute(vol_snapshot_attributes, vol_mod_attributes,
                                         'snapdir-access-enabled', self.parameters['snapdir_access'])
        # volume-export-attributes
        if self.parameters.get('policy'):
            self.create_volume_attribute(vol_mod_attributes, 'volume-export-attributes',
                                         'policy', self.parameters['policy'])
        # volume-security-attributes
        if self.parameters.get('unix_permissions') is not None or self.parameters.get('group_id') is not None or self.parameters.get('user_id') is not None:
            vol_security_attributes = netapp_utils.zapi.NaElement('volume-security-attributes')
            vol_security_unix_attributes = netapp_utils.zapi.NaElement('volume-security-unix-attributes')
            if self.parameters.get('unix_permissions') is not None:
                self.create_volume_attribute(vol_security_unix_attributes, vol_security_attributes,
                                             'permissions', self.parameters['unix_permissions'])
            if self.parameters.get('group_id') is not None:
                self.create_volume_attribute(vol_security_unix_attributes, vol_security_attributes,
                                             'group-id', str(self.parameters['group_id']))
            if self.parameters.get('user_id') is not None:
                self.create_volume_attribute(vol_security_unix_attributes, vol_security_attributes,
                                             'user-id', str(self.parameters['user_id']))
            vol_mod_attributes.add_child_elem(vol_security_attributes)
        if params and params.get('volume_security_style'):
            self.create_volume_attribute(vol_mod_attributes, 'volume-security-attributes',
                                         'style', self.parameters['volume_security_style'])

        # volume-performance-attributes
        if self.parameters.get('atime_update'):
            self.create_volume_attribute(vol_mod_attributes, 'volume-performance-attributes',
                                         'is-atime-update-enabled', self.parameters['atime_update'])
        # volume-qos-attributes
        if self.parameters.get('qos_policy_group'):
            self.create_volume_attribute(vol_mod_attributes, 'volume-qos-attributes',
                                         'policy-group-name', self.parameters['qos_policy_group'])
        if self.parameters.get('qos_adaptive_policy_group'):
            self.create_volume_attribute(vol_mod_attributes, 'volume-qos-attributes',
                                         'adaptive-policy-group-name', self.parameters['qos_adaptive_policy_group'])
        # volume-comp-aggr-attributes
        if params and params.get('tiering_policy'):
            self.create_volume_attribute(vol_mod_attributes, 'volume-comp-aggr-attributes',
                                         'tiering-policy', self.parameters['tiering_policy'])
        # volume-state-attributes
        if self.parameters.get('nvfail_enabled') is not None:
            self.create_volume_attribute(vol_mod_attributes, 'volume-state-attributes', 'is-nvfail-enabled', str(self.parameters['nvfail_enabled']))
        # volume-dr-protection-attributes
        if self.parameters.get('vserver_dr_protection') is not None:
            self.create_volume_attribute(vol_mod_attributes, 'volume-vserver-dr-protection-attributes',
                                         'vserver-dr-protection', self.parameters['vserver_dr_protection'])
        # volume-id-attributes
        if self.parameters.get('comment') is not None:
            self.create_volume_attribute(vol_mod_attributes, 'volume-id-attributes',
                                         'comment', self.parameters['comment'])
        # End of Volume-attributes sub attributes
        attributes.add_child_elem(vol_mod_attributes)
        query = netapp_utils.zapi.NaElement('query')
        vol_query_attributes = netapp_utils.zapi.NaElement('volume-attributes')
        self.create_volume_attribute(vol_query_attributes, 'volume-id-attributes',
                                     'name', self.parameters['name'])
        query.add_child_elem(vol_query_attributes)
        vol_mod_iter.add_child_elem(attributes)
        vol_mod_iter.add_child_elem(query)
        try:
            result = self.server.invoke_successfully(vol_mod_iter, enable_tunneling=True)
            failures = result.get_child_by_name('failure-list')
            if self.volume_style == 'flexGroup' or self.parameters['is_infinite']:
                success = result.get_child_by_name('success-list')
                success = success.get_child_by_name('volume-modify-iter-async-info')
                results = dict()
                for key in ('status', 'jobid'):
                    if success.get_child_by_name(key):
                        results[key] = success[key]
                status = results.get('status')
                if status == 'in_progress' and 'jobid' in results:
                    if self.parameters['time_out'] == 0:
                        return
                    error = self.check_job_status(results['jobid'])
                    if error is None:
                        return
                    else:
                        self.module.fail_json(msg='Error when modify volume: %s' % error)
                self.module.fail_json(msg='Unexpected error when modify volume: results is: %s' % repr(results))
            # handle error if modify space, policy, or unix-permissions parameter fails
            if failures is not None:
                if failures.get_child_by_name('volume-modify-iter-info') is not None:
                    return_info = 'volume-modify-iter-info'
                    error_msg = failures.get_child_by_name(return_info).get_child_content('error-message')
                    self.module.fail_json(msg="Error modifying volume %s: %s"
                                          % (self.parameters['name'], error_msg),
                                          exception=traceback.format_exc())
                elif failures.get_child_by_name('volume-modify-iter-async-info') is not None:
                    return_info = 'volume-modify-iter-async-info'
                    error_msg = failures.get_child_by_name(return_info).get_child_content('error-message')
                    self.module.fail_json(msg="Error modifying volume %s: %s"
                                          % (self.parameters['name'], error_msg),
                                          exception=traceback.format_exc())
            self.ems_log_event("volume-modify")
        except netapp_utils.zapi.NaApiError as error:
            error_msg = to_native(error)
            if 'volume-comp-aggr-attributes' in error_msg:
                error_msg += ". Added info: tiering option requires 9.4 or later."
            self.module.fail_json(msg='Error modifying volume %s: %s'
                                  % (self.parameters['name'], error_msg),
                                  exception=traceback.format_exc())

    def volume_mount(self):
        """
        Mount an existing volume in specified junction_path
        :return: None
        """
        vol_mount = netapp_utils.zapi.NaElement('volume-mount')
        vol_mount.add_new_child('volume-name', self.parameters['name'])
        vol_mount.add_new_child('junction-path', self.parameters['junction_path'])
        try:
            self.server.invoke_successfully(vol_mount, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error mounting volume %s on path %s: %s'
                                      % (self.parameters['name'], self.parameters['junction_path'],
                                         to_native(error)), exception=traceback.format_exc())

    def volume_unmount(self):
        """
        Unmount an existing volume
        :return: None
        """
        vol_unmount = netapp_utils.zapi.NaElement.create_node_with_children(
            'volume-unmount', **{'volume-name': self.parameters['name']})
        try:
            self.server.invoke_successfully(vol_unmount, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error unmounting volume %s: %s'
                                      % (self.parameters['name'], to_native(error)), exception=traceback.format_exc())

    def modify_volume(self, modify):
        '''Modify volume action'''
        attributes = modify.keys()
        # order matters here, if both is_online and mount in modify, must bring the volume online first.
        if 'is_online' in attributes:
            self.change_volume_state()
        for attribute in attributes:
            if attribute in ['space_guarantee', 'policy', 'unix_permissions', 'group_id', 'user_id', 'tiering_policy',
                             'snapshot_policy', 'percent_snapshot_space', 'snapdir_access', 'atime_update', 'volume_security_style',
                             'nvfail_enabled', 'space_slo', 'qos_policy_group', 'qos_adaptive_policy_group', 'vserver_dr_protection', 'comment']:
                self.volume_modify_attributes(modify)
                break
        if 'snapshot_auto_delete' in attributes:
            self.set_snapshot_auto_delete()
        if 'junction_path' in attributes:
            if modify.get('junction_path') == '':
                self.volume_unmount()
            else:
                self.volume_mount()
        if 'size' in attributes:
            self.resize_volume()
        if 'aggregate_name' in attributes:
            # keep it last, as it may take some time
            self.move_volume()
            if self.parameters.get('wait_for_completion'):
                self.wait_for_volume_move()

    def compare_chmod_value(self, current):
        """
        compare current unix_permissions to desire unix_permissions.
        :return: True if the same, False it not the same or desire unix_permissions is not valid.
        """
        desire = self.parameters
        if current is None:
            return False
        octal_value = ''
        unix_permissions = desire['unix_permissions']
        if unix_permissions.isdigit():
            return int(current['unix_permissions']) == int(unix_permissions)
        else:
            if len(unix_permissions) != 12:
                return False
            if unix_permissions[:3] != '---':
                return False
            for i in range(3, len(unix_permissions), 3):
                if unix_permissions[i] not in ['r', '-'] or unix_permissions[i + 1] not in ['w', '-']\
                        or unix_permissions[i + 2] not in ['x', '-']:
                    return False
                group_permission = self.char_to_octal(unix_permissions[i:i + 3])
                octal_value += str(group_permission)
            return int(current['unix_permissions']) == int(octal_value)

    def char_to_octal(self, chars):
        """
        :param chars: Characters to be converted into octal values.
        :return: octal value of the individual group permission.
        """
        total = 0
        if chars[0] == 'r':
            total += 4
        if chars[1] == 'w':
            total += 2
        if chars[2] == 'x':
            total += 1
        return total

    def get_volume_style(self, current):
        '''Get volume style, infinite or standard flexvol'''
        if current is None:
            if self.parameters.get('aggr_list') or self.parameters.get('aggr_list_multiplier') or self.parameters.get('auto_provision_as'):
                return 'flexGroup'
        else:
            if current.get('style_extended'):
                if current['style_extended'] == 'flexgroup':
                    return 'flexGroup'
                else:
                    return current['style_extended']
        return None

    def get_job(self, jobid, server):
        """
        Get job details by id
        """
        job_get = netapp_utils.zapi.NaElement('job-get')
        job_get.add_new_child('job-id', jobid)
        try:
            result = server.invoke_successfully(job_get, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            if to_native(error.code) == "15661":
                # Not found
                return None
            self.module.fail_json(msg='Error fetching job info: %s' % to_native(error),
                                  exception=traceback.format_exc())
        job_info = result.get_child_by_name('attributes').get_child_by_name('job-info')
        results = {
            'job-progress': job_info['job-progress'],
            'job-state': job_info['job-state']
        }
        if job_info.get_child_by_name('job-completion') is not None:
            results['job-completion'] = job_info['job-completion']
        else:
            results['job-completion'] = None
        return results

    def check_job_status(self, jobid):
        """
        Loop until job is complete
        """
        server = self.server
        sleep_time = 5
        time_out = self.parameters['time_out']
        results = self.get_job(jobid, server)
        error = 'timeout'

        while time_out > 0:
            results = self.get_job(jobid, server)
            # If running as cluster admin, the job is owned by cluster vserver
            # rather than the target vserver.
            if results is None and server == self.server:
                results = netapp_utils.get_cserver(self.server)
                server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
                continue
            if results is None:
                error = 'cannot locate job with id: %d' % int(jobid)
                break
            if results['job-state'] in ('queued', 'running'):
                time.sleep(sleep_time)
                time_out -= sleep_time
                continue
            if results['job-state'] in ('success', 'failure'):
                break
            else:
                self.module.fail_json(msg='Unexpected job status in: %s' % repr(results))

        if results is not None:
            if results['job-state'] == 'success':
                error = None
            elif results['job-state'] in ('queued', 'running'):
                error = 'job completion exceeded expected timer of: %s seconds' % \
                        self.parameters['time_out']
            else:
                if results['job-completion'] is not None:
                    error = results['job-completion']
                else:
                    error = results['job-progress']
        return error

    def check_invoke_result(self, result, action):
        '''
        check invoked api call back result.
        '''
        results = dict()
        for key in ('result-status', 'result-jobid'):
            if result.get_child_by_name(key):
                results[key] = result[key]
        status = results.get('result-status')
        if status == 'in_progress' and 'result-jobid' in results:
            if self.parameters['time_out'] == 0:
                return
            error = self.check_job_status(results['result-jobid'])
            if error is None:
                return
            else:
                self.module.fail_json(msg='Error when %s volume: %s' % (action, error))
        if status == 'failed':
            self.module.fail_json(msg='Operation failed when %s volume.' % action)

    def assign_efficiency_policy(self):
        '''Set efficiency policy'''
        options = {'path': '/vol/' + self.parameters['name']}
        efficiency_enable = netapp_utils.zapi.NaElement.create_node_with_children('sis-enable', **options)
        try:
            self.server.invoke_successfully(efficiency_enable, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            # Error 40043 denotes an Operation has already been enabled.
            if to_native(error.code) == "40043":
                pass
            else:
                self.module.fail_json(msg='Error enable efficiency on volume %s: %s'
                                          % (self.parameters['name'], to_native(error)),
                                      exception=traceback.format_exc())

        options['policy-name'] = self.parameters['efficiency_policy']
        efficiency_start = netapp_utils.zapi.NaElement.create_node_with_children('sis-set-config', **options)
        try:
            self.server.invoke_successfully(efficiency_start, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error setting up an efficiency policy %s on volume %s: %s'
                                      % (self.parameters['efficiency_policy'], self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def assign_efficiency_policy_async(self):
        """Set efficiency policy in asynchronous mode"""
        options = {'volume-name': self.parameters['name']}
        efficiency_enable = netapp_utils.zapi.NaElement.create_node_with_children('sis-enable-async', **options)
        try:
            result = self.server.invoke_successfully(efficiency_enable, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error enable efficiency on volume %s: %s'
                                      % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        self.check_invoke_result(result, 'enable efficiency on')

        options['policy-name'] = self.parameters['efficiency_policy']
        efficiency_start = netapp_utils.zapi.NaElement.create_node_with_children('sis-set-config-async', **options)
        try:
            result = self.server.invoke_successfully(efficiency_start, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error setting up an efficiency policy on volume %s: %s'
                                      % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())
        self.check_invoke_result(result, 'set efficiency policy on')

    def get_efficiency_policy(self):
        """
        get the name of the efficiency policy assigned to volume.
        :return: String, name of the policy. If it doesn't exist, return None.
        """
        sis_info = netapp_utils.zapi.NaElement('sis-get-iter')
        sis_status_info = netapp_utils.zapi.NaElement('sis-status-info')
        sis_status_info.add_new_child('path', '/vol/' + self.parameters['name'])
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(sis_status_info)
        sis_info.add_child_elem(query)
        try:
            result = self.server.invoke_successfully(sis_info, True)
            if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) >= 1:
                sis_attributes = result.get_child_by_name('attributes-list'). get_child_by_name('sis-status-info')
                return_value = sis_attributes.get_child_content('policy')
                return return_value
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching efficiency policy for volume %s : %s'
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

        return None

    def modify_volume_efficiency_policy(self, efficiency_policy_modify_value):
        if efficiency_policy_modify_value == 'async':
            self.assign_efficiency_policy_async()
        elif efficiency_policy_modify_value == 'sync':
            self.assign_efficiency_policy()

    def set_snapshot_auto_delete(self):
        options = {'volume': self.parameters['name']}
        desired_options = self.parameters['snapshot_auto_delete']
        for k, v in desired_options.items():
            options['option-name'] = k
            options['option-value'] = str(v)

            snapshot_auto_delete = netapp_utils.zapi.NaElement.create_node_with_children('snapshot-autodelete-set-option', **options)

            try:
                self.server.invoke_successfully(snapshot_auto_delete, enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error setting snapshot auto delete options for volume %s: %s'
                                      % (self.parameters['name'], to_native(error)),
                                      exception=traceback.format_exc())

    def rehost_volume(self):
        volume_rehost = netapp_utils.zapi.NaElement.create_node_with_children(
            'volume-rehost', **{'vserver': self.parameters['from_vserver'],
                                'destination-vserver': self.parameters['vserver'],
                                'volume': self.parameters['name']})
        if self.parameters.get('auto_remap_luns') is not None:
            volume_rehost.add_new_child('auto-remap-luns', str(self.parameters['auto_remap_luns']))
        if self.parameters.get('force_unmap_luns') is not None:
            volume_rehost.add_new_child('force-unmap-luns', str(self.parameters['force_unmap_luns']))
        try:
            self.cluster.invoke_successfully(volume_rehost, enable_tunneling=True)
            self.ems_log_event("volume-rehost")
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error rehosting volume %s: %s'
                                      % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def snapshot_restore_volume(self):
        snapshot_restore = netapp_utils.zapi.NaElement.create_node_with_children(
            'snapshot-restore-volume', **{'snapshot': self.parameters['snapshot_restore'],
                                          'volume': self.parameters['name']})
        if self.parameters.get('force_restore') is not None:
            snapshot_restore.add_new_child('force', str(self.parameters['force_restore']))
        if self.parameters.get('preserve_lun_ids') is not None:
            snapshot_restore.add_new_child('preserve-lun-ids', str(self.parameters['preserve_lun_ids']))
        try:
            self.server.invoke_successfully(snapshot_restore, enable_tunneling=True)
            self.ems_log_event("snapshot-restore-volume")
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error restoring volume %s: %s'
                                      % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def apply(self):
        '''Call create/modify/delete operations'''
        efficiency_policy_modify = None
        current = self.get_volume()
        self.volume_style = self.get_volume_style(current)
        # rename and create are mutually exclusive
        rename, rehost, snapshot_restore, cd_action, modify = None, None, None, None, None
        if self.parameters.get('from_name'):
            rename = self.na_helper.is_rename_action(self.get_volume(self.parameters['from_name']), current)
        elif self.parameters.get('from_vserver'):
            rehost = True
            self.na_helper.changed = True
        elif self.parameters.get('snapshot_restore'):
            snapshot_restore = True
            self.na_helper.changed = True
        else:
            cd_action = self.na_helper.get_cd_action(current, self.parameters)
        if self.parameters.get('unix_permissions') is not None:
            # current stores unix_permissions' numeric value.
            # unix_permission in self.parameter can be either numeric or character.
            if self.compare_chmod_value(current) or not self.parameters['is_online']:
                # don't change if the values are the same
                # can't change permissions if not online
                del self.parameters['unix_permissions']
        if cd_action is None and rename is None and rehost is None and self.parameters['state'] == 'present':
            # snapshot_auto_delete's value is a dict, get_modified_attributes function doesn't support dict as value.
            auto_delete_info = current.pop('snapshot_auto_delete', None)
            modify = self.na_helper.get_modified_attributes(current, self.parameters)
            if self.parameters.get('snapshot_auto_delete') is not None:
                auto_delete_modify = self.na_helper.get_modified_attributes(auto_delete_info,
                                                                            self.parameters['snapshot_auto_delete'])
                if len(auto_delete_modify) > 0:
                    modify['snapshot_auto_delete'] = auto_delete_modify

            if modify.get('efficiency_policy'):
                if self.parameters.get('is_infinite') or self.volume_style == 'flexGroup':
                    efficiency_policy_modify = 'async'
                else:
                    efficiency_policy_modify = 'sync'
        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if rename:
                    self.rename_volume()
                if rehost:
                    self.rehost_volume()
                if snapshot_restore:
                    self.snapshot_restore_volume()
                if cd_action == 'create':
                    self.create_volume()
                    # if we create, and modify only variable are set (snapdir_access or atime_update) we need to run a modify
                    if 'snapdir_access' in self.parameters:
                        self.volume_modify_attributes({'snapdir_access': self.parameters['snapdir_access']})
                    if 'atime_update' in self.parameters:
                        self.volume_modify_attributes({'atime_update': self.parameters['atime_update']})
                elif cd_action == 'delete':
                    self.delete_volume(current)
                elif modify:
                    if modify.get('is_online'):
                        # when moving to online, include parameters that get does not return when volume is offline
                        for field in ['volume_security_style', 'group_id', 'user_id', 'percent_snapshot_space']:
                            if self.parameters.get(field) is not None:
                                modify[field] = self.parameters[field]
                    self.modify_volume(modify)
                    if efficiency_policy_modify is not None:
                        self.modify_volume_efficiency_policy(efficiency_policy_modify)
        self.module.exit_json(changed=self.na_helper.changed)

    def ems_log_event(self, state):
        '''Autosupport log event'''
        if state == 'create':
            message = "A Volume has been created, size: " + \
                str(self.parameters['size']) + str(self.parameters['size_unit'])
        elif state == 'volume-delete':
            message = "A Volume has been deleted"
        elif state == 'volume-move':
            message = "A Volume has been moved"
        elif state == 'volume-rename':
            message = "A Volume has been renamed"
        elif state == 'volume-resize':
            message = "A Volume has been resized to: " + \
                str(self.parameters['size']) + str(self.parameters['size_unit'])
        elif state == 'volume-rehost':
            message = "A Volume has been rehosted"
        elif state == 'snapshot-restore-volume':
            message = "A Volume has been restored by snapshot"
        elif state == 'volume-change':
            message = "A Volume state has been changed"
        else:
            message = "na_ontap_volume has been called"
        netapp_utils.ems_log_event(
            "na_ontap_volume", self.server, event=message)


def main():
    '''Apply volume operations from playbook'''
    obj = NetAppOntapVolume()
    obj.apply()


if __name__ == '__main__':
    main()
