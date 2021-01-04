#!/usr/bin/python

'''
na_ontap_snapmirror
'''

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
description:
  - Create/Delete/Update/Initialize/Break/Resync/Resume SnapMirror volume/vserver relationships for ONTAP/ONTAP
  - This includes SVM replication, aka vserver DR
  - Create/Delete/Update/Initialize SnapMirror volume relationship between ElementSW and ONTAP
  - Modify schedule for a SnapMirror relationship for ONTAP/ONTAP and ElementSW/ONTAP
  - Pre-requisite for ElementSW to ONTAP relationship or vice-versa is an established SnapMirror endpoint for ONTAP cluster with ElementSW UI
  - Pre-requisite for ElementSW to ONTAP relationship or vice-versa is to have SnapMirror enabled in the ElementSW volume
  - For creating a SnapMirror ElementSW/ONTAP relationship, an existing ONTAP/ElementSW relationship should be present
  - Performs resync if the C(relationship_state=active) and the current mirror state of the snapmirror relationship is broken-off
  - Performs resume if the C(relationship_state=active), the current snapmirror relationship status is quiesced and mirror state is snapmirrored
  - Performs restore if the C(relationship_type=restore) and all other operations will not be performed during this task
extends_documentation_fragment:
  - netapp.ontap.netapp.na_ontap
module: na_ontap_snapmirror
options:
  state:
    choices: ['present', 'absent']
    description:
      - Whether the specified relationship should exist or not.
    default: present
    type: str
  source_volume:
    description:
      - Specifies the name of the source volume for the SnapMirror.
    type: str
  destination_volume:
    description:
      - Specifies the name of the destination volume for the SnapMirror.
    type: str
  source_vserver:
    description:
      - Name of the source vserver for the SnapMirror.
    type: str
  destination_vserver:
    description:
      - Name of the destination vserver for the SnapMirror.
    type: str
  source_path:
    description:
      - Specifies the source endpoint of the SnapMirror relationship.
      - If the source is an ONTAP volume, format should be <[vserver:][volume]> or <[[cluster:]//vserver/]volume>
      - If the source is an ElementSW volume, format should be <[Element_SVIP]:/lun/[Element_VOLUME_ID]>
      - If the source is an ElementSW volume, the volume should have SnapMirror enabled.
    type: str
  destination_path:
    description:
      - Specifies the destination endpoint of the SnapMirror relationship.
    type: str
  relationship_type:
    choices: ['data_protection', 'load_sharing', 'vault', 'restore', 'transition_data_protection',
    'extended_data_protection']
    type: str
    description:
      - Specify the type of SnapMirror relationship.
      - for 'restore' unless 'source_snapshot' is specified the most recent Snapshot copy on the source volume is restored.
      - restore SnapMirror is not idempotent.
      - With REST, only 'extended_data_protection' is supported.  ('restore' is TBD)
  schedule:
    description:
      - Specify the name of the current schedule, which is used to update the SnapMirror relationship.
      - Optional for create, modifiable.
    type: str
  policy:
    description:
      - Specify the name of the SnapMirror policy that applies to this relationship.
    version_added: 2.8.0
    type: str
  source_hostname:
    description:
     - Source hostname or management IP address for ONTAP or ElementSW cluster.
     - Required for SnapMirror delete
    type: str
  source_username:
    description:
     - Source username for ONTAP or ElementSW cluster.
     - Optional if this is same as destination username.
    type: str
  source_password:
    description:
     - Source password for ONTAP or ElementSW cluster.
     - Optional if this is same as destination password.
    type: str
  connection_type:
    description:
     - Type of SnapMirror relationship.
     - Pre-requisite for either elementsw_ontap or ontap_elementsw the ElementSW volume should have enableSnapmirror option set to true.
     - For using ontap_elementsw, elementsw_ontap snapmirror relationship should exist.
    choices: ['ontap_ontap', 'elementsw_ontap', 'ontap_elementsw']
    default: ontap_ontap
    type: str
    version_added: 2.9.0
  max_transfer_rate:
    description:
     - Specifies the upper bound, in kilobytes per second, at which data is transferred.
     - Default is unlimited, it can be explicitly set to 0 as unlimited.
    type: int
    version_added: 2.9.0
  initialize:
    description:
     - Specifies whether to initialize SnapMirror relation.
     - Default is True, it can be explicitly set to False to avoid initializing SnapMirror relation.
    default: true
    type: bool
    version_added: '19.11.0'
  update:
    description:
     - Specifies whether to update the destination endpoint of the SnapMirror relationship only if the relationship is already present and active.
     - Default is True.
    default: true
    type: bool
    version_added: '20.2.0'
  relationship_info_only:
    description:
     - If relationship-info-only is set to true then only relationship information is removed.
    default: false
    type: bool
    version_added: '20.4.0'
  relationship_state:
    description:
     - Specifies whether to break SnapMirror relation or establish a SnapMirror relationship.
     - state must be present to use this option.
    default: active
    choices: ['active', 'broken']
    type: str
    version_added: '20.2.0'
  source_snapshot:
    description:
     - Specifies the Snapshot from the source to be restored.
    type: str
    version_added: '20.6.0'
  identity_preserve:
    description:
     - Specifies whether or not the identity of the source Vserver is replicated to the destination Vserver.
     - If this parameter is set to true, the source Vserver's configuration will additionally be replicated to the destination.
     - If the parameter is set to false, then only the source Vserver's volumes and RBAC configuration are replicated to the destination.
    type: bool
    version_added: 2.9.0
  create_destination:
    description:
      - Requires ONTAP 9.7 or later.
      - Creates the destination volume if enabled and destination_volume is present or destination_path includes a volume name.
      - Creates and peers the destination vserver for SVM DR.
    type: dict
    version_added: 21.1.0
    suboptions:
      enabled:
        description:
          - Whether to create the destination volume or vserver.
          - This is automatically enabled if any other suboption is present.
        type: bool
        default: true
      storage_service:
        description: storage service associated with the destination endpoint.
        type: dict
        suboptions:
          enabled:
            description: whether to create the destination endpoint using storage service.
            type: bool
          enforce_performance:
            description: whether to enforce storage service performance on the destination endpoint.
            type: bool
          name:
            description: the performance service level (PSL) for this volume endpoint.
            type: str
            choices: ['value', 'performance', 'extreme']
      tiering:
        description:
          - Cloud tiering policy.
        type: dict
        suboptions:
          policy:
            description:
              - Cloud tiering policy.
            choices: ['all', 'auto', 'none', 'snapshot-only']
            type: str
          supported:
            description:
              - enable provisioning of the destination endpoint volumes on FabricPool aggregates.
              - only supported for FlexVol volume, FlexGroup volume, and Consistency Group endpoints.
            type: bool
  destination_cluster:
    description:
      - Requires ONTAP 9.7 or higher.
      - Required to create the destination vserver for SVM DR or the destination volume.
    type: str
    version_added: 21.1.0
  source_cluster:
    description:
      - Requires ONTAP 9.7 or higher.
      - Required to create the peering relationship between source and destination SVMs.
    type: str
    version_added: 21.1.0

short_description: "NetApp ONTAP or ElementSW Manage SnapMirror"
version_added: 2.7.0
'''

EXAMPLES = """

    # creates and initializes the snapmirror
    - name: Create ONTAP/ONTAP SnapMirror
      na_ontap_snapmirror:
        state: present
        source_volume: test_src
        destination_volume: test_dest
        source_vserver: ansible_src
        destination_vserver: ansible_dest
        schedule: hourly
        policy: MirrorAllSnapshots
        max_transfer_rate: 1000
        initialize: False
        hostname: "{{ destination_cluster_hostname }}"
        username: "{{ destination_cluster_username }}"
        password: "{{ destination_cluster_password }}"

    # creates and initializes the snapmirror between vservers
    - name: Create ONTAP/ONTAP vserver SnapMirror
      na_ontap_snapmirror:
        state: present
        source_vserver: ansible_src
        destination_vserver: ansible_dest
        identity_preserve: true
        hostname: "{{ destination_cluster_hostname }}"
        username: "{{ destination_cluster_username }}"
        password: "{{ destination_cluster_password }}"

    # existing snapmirror relation with status 'snapmirrored' will be initialized
    - name: Inititalize ONTAP/ONTAP SnapMirror
      na_ontap_snapmirror:
        state: present
        source_path: 'ansible:test'
        destination_path: 'ansible:dest'
        relationship_state: active
        hostname: "{{ destination_cluster_hostname }}"
        username: "{{ destination_cluster_username }}"
        password: "{{ destination_cluster_password }}"

    - name: Delete SnapMirror
      na_ontap_snapmirror:
        state: absent
        destination_path: <path>
        relationship_info_only: True
        source_hostname: "{{ source_hostname }}"
        hostname: "{{ destination_cluster_hostname }}"
        username: "{{ destination_cluster_username }}"
        password: "{{ destination_cluster_password }}"

    - name: Break SnapMirror
      na_ontap_snapmirror:
        state: present
        relationship_state: broken
        destination_path: <path>
        source_hostname: "{{ source_hostname }}"
        hostname: "{{ destination_cluster_hostname }}"
        username: "{{ destination_cluster_username }}"
        password: "{{ destination_cluster_password }}"

    - name: Restore SnapMirror volume using location (Idempotency)
      na_ontap_snapmirror:
        state: present
        source_path: <path>
        destination_path: <path>
        relationship_type: restore
        source_snapshot: "{{ snapshot }}"
        hostname: "{{ destination_cluster_hostname }}"
        username: "{{ destination_cluster_username }}"
        password: "{{ destination_cluster_password }}"

    - name: Set schedule to NULL
      na_ontap_snapmirror:
        state: present
        destination_path: <path>
        schedule: ""
        hostname: "{{ destination_cluster_hostname }}"
        username: "{{ destination_cluster_username }}"
        password: "{{ destination_cluster_password }}"

    - name: Create SnapMirror from ElementSW to ONTAP
      na_ontap_snapmirror:
        state: present
        connection_type: elementsw_ontap
        source_path: '10.10.10.10:/lun/300'
        destination_path: 'ansible_test:ansible_dest_vol'
        schedule: hourly
        policy: MirrorLatest
        hostname: "{{ netapp_hostname }}"
        username: "{{ netapp_username }}"
        password: "{{ netapp_password }}"
        source_hostname: " {{ Element_cluster_mvip }}"
        source_username: "{{ Element_cluster_username }}"
        source_password: "{{ Element_cluster_password }}"

    - name: Create SnapMirror from ONTAP to ElementSW
      na_ontap_snapmirror:
        state: present
        connection_type: ontap_elementsw
        destination_path: '10.10.10.10:/lun/300'
        source_path: 'ansible_test:ansible_dest_vol'
        policy: MirrorLatest
        hostname: "{{ Element_cluster_mvip }}"
        username: "{{ Element_cluster_username }}"
        password: "{{ Element_cluster_password }}"
        source_hostname: " {{ netapp_hostname }}"
        source_username: "{{ netapp_username }}"
        source_password: "{{ netapp_password }}"

    - name: Create SnapMirror relationship (creating destination volume)
      na_ontap_snapmirror:
        state: present
        source_volume: "{{ source_volume }}"
        source_vserver: "{{ source_vserver }}"
        destination_volume: "{{ destination_volume }}"
        destination_vserver: "{{ destination_vserver }}"
        destination_cluster: "{{ destination_cluster | default(omit) }}"
        create_destination:
          enabled: true
        policy: "{{ policy | default(omit) }}"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: "{{ https }}"
        validate_certs: "{{ validate_certs }}"

    - name: Create SnapMirror relationship - SVM DR (creating and peering destination svm)
      na_ontap_snapmirror:
        state: present
        source_vserver: "{{ source_vserver }}"
        source_cluster: "{{ source_cluster | default(omit) }}"
        destination_vserver: "{{ destination_vserver }}"
        destination_cluster: "{{ destination_cluster | default(omit) }}"
        create_destination:
          enabled: true
        policy: "{{ policy | default(omit) }}"
        hostname: "{{ hostname }}"
        username: "{{ username }}"
        password: "{{ password }}"
        https: "{{ https }}"
        validate_certs: "{{ validate_certs }}"
"""

RETURN = """
"""

import re
import time
import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_elementsw_module import NaElementSWModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
import ansible_collections.netapp.ontap.plugins.module_utils.rest_response_helpers as rrh

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()

HAS_SF_SDK = netapp_utils.has_sf_sdk()
try:
    import solidfire.common
except ImportError:
    HAS_SF_SDK = False


class NetAppONTAPSnapmirror(object):
    """
    Class with SnapMirror methods
    """

    def __init__(self):

        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, type='str', choices=['present', 'absent'], default='present'),
            source_vserver=dict(required=False, type='str'),
            destination_vserver=dict(required=False, type='str'),
            source_volume=dict(required=False, type='str'),
            destination_volume=dict(required=False, type='str'),
            source_path=dict(required=False, type='str'),
            destination_path=dict(required=False, type='str'),
            schedule=dict(required=False, type='str'),
            policy=dict(required=False, type='str'),
            relationship_type=dict(required=False, type='str',
                                   choices=['data_protection', 'load_sharing',
                                            'vault', 'restore',
                                            'transition_data_protection',
                                            'extended_data_protection']
                                   ),
            source_hostname=dict(required=False, type='str'),
            connection_type=dict(required=False, type='str',
                                 choices=['ontap_ontap', 'elementsw_ontap', 'ontap_elementsw'],
                                 default='ontap_ontap'),
            source_username=dict(required=False, type='str'),
            source_password=dict(required=False, type='str', no_log=True),
            max_transfer_rate=dict(required=False, type='int'),
            initialize=dict(required=False, type='bool', default=True),
            update=dict(required=False, type='bool', default=True),
            identity_preserve=dict(required=False, type='bool'),
            relationship_state=dict(required=False, type='str', choices=['active', 'broken'], default='active'),
            relationship_info_only=dict(required=False, type='bool', default=False),
            source_snapshot=dict(required=False, type='str'),
            create_destination=dict(required=False, type='dict', options=dict(
                enabled=dict(type='bool', default=True),
                storage_service=dict(type='dict', options=dict(
                    enabled=dict(type='bool'),
                    enforce_performance=dict(type='bool'),
                    name=dict(type='str', choices=['value', 'performance', 'extreme']),
                )),
                tiering=dict(type='dict', options=dict(
                    policy=dict(type='str', choices=['all', 'auto', 'none', 'snapshot-only']),
                    supported=dict(type='bool')
                )),
            )),
            source_cluster=dict(required=False, type='str'),
            destination_cluster=dict(required=False, type='str'),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            required_together=(['source_volume', 'destination_volume'],
                               ['source_vserver', 'destination_vserver']),
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        # setup later if required
        self.source_server = None
        # only for ElementSW -> ONTAP snapmirroring, validate if ElementSW SDK is available
        if self.parameters.get('connection_type') in ['elementsw_ontap', 'ontap_elementsw']:
            if HAS_SF_SDK is False:
                self.module.fail_json(msg="Unable to import the SolidFire Python SDK")

        unsupported_rest_properties = ['identity_preserve', 'max_transfer_rate', 'schedule']
        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        rtype = self.parameters.get('relationship_type')
        if rtype not in (None, 'extended_data_protection'):
            unsupported_rest_properties.append('relationship_type')
        used_unsupported_rest_properties = [x for x in unsupported_rest_properties if x in self.parameters]
        self.use_rest, error = self.rest_api.is_rest(used_unsupported_rest_properties)
        if error is not None:
            if 'relationship_type' in error:
                error = error.replace('relationship_type', 'relationship_type: %s' % rtype)
            self.module.fail_json(msg=error)

        ontap_97_options = ['create_destination', 'source_cluster', 'destination_cluster']
        if not self.use_rest and any(x in self.parameters for x in ontap_97_options):
            self.module.fail_json(msg='Error: %s' % self.rest_api.options_require_ontap_version(ontap_97_options, version='9.7'))

        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        if self.parameters.get('connection_type') != 'ontap_elementsw':
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)
        else:
            if self.parameters.get('source_username'):
                self.module.params['username'] = self.parameters['source_username']
            if self.parameters.get('source_password'):
                self.module.params['password'] = self.parameters['source_password']
            self.module.params['hostname'] = self.parameters['source_hostname']
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def set_element_connection(self, kind):
        if kind == 'source':
            self.module.params['hostname'] = self.parameters['source_hostname']
            self.module.params['username'] = self.parameters['source_username']
            self.module.params['password'] = self.parameters['source_password']
        elif kind == 'destination':
            self.module.params['hostname'] = self.parameters['hostname']
            self.module.params['username'] = self.parameters['username']
            self.module.params['password'] = self.parameters['password']
        elem = netapp_utils.create_sf_connection(module=self.module)
        elementsw_helper = NaElementSWModule(elem)
        return elementsw_helper, elem

    def snapmirror_get_iter(self, destination=None):
        """
        Compose NaElement object to query current SnapMirror relations using destination-path
        SnapMirror relation for a destination path is unique
        :return: NaElement object for SnapMirror-get-iter
        """
        snapmirror_get_iter = netapp_utils.zapi.NaElement('snapmirror-get-iter')
        query = netapp_utils.zapi.NaElement('query')
        snapmirror_info = netapp_utils.zapi.NaElement('snapmirror-info')
        if destination is None:
            destination = self.parameters['destination_path']
        snapmirror_info.add_new_child('destination-location', destination)
        query.add_child_elem(snapmirror_info)
        snapmirror_get_iter.add_child_elem(query)
        return snapmirror_get_iter

    def snapmirror_get(self, destination=None):
        """
        Get current SnapMirror relations
        :return: Dictionary of current SnapMirror details if query successful, else None
        """
        snapmirror_get_iter = self.snapmirror_get_iter(destination)
        snap_info = dict()
        try:
            result = self.server.invoke_successfully(snapmirror_get_iter, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching snapmirror info: %s' % to_native(error),
                                  exception=traceback.format_exc())
        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) > 0:
            snapmirror_info = result.get_child_by_name('attributes-list').get_child_by_name(
                'snapmirror-info')
            snap_info['mirror_state'] = snapmirror_info.get_child_content('mirror-state')
            snap_info['status'] = snapmirror_info.get_child_content('relationship-status')
            snap_info['schedule'] = snapmirror_info.get_child_content('schedule')
            snap_info['policy'] = snapmirror_info.get_child_content('policy')
            snap_info['relationship_type'] = snapmirror_info.get_child_content('relationship-type')
            snap_info['current-transfer-type'] = snapmirror_info.get_child_content('current-transfer-type')
            if snapmirror_info.get_child_by_name('max-transfer-rate'):
                snap_info['max_transfer_rate'] = int(snapmirror_info.get_child_content('max-transfer-rate'))
            if snap_info['schedule'] is None:
                snap_info['schedule'] = ""
            return snap_info
        return None

    def wait_for_status(self):
        timeout = 300       # 5 minutes
        while timeout > 0:
            time.sleep(30)
            current = self.snapmirror_get()
            if current['status'] != 'transferring':
                return True
            timeout -= 30
        return False

    def check_if_remote_volume_exists(self):
        """
        Validate existence of source volume
        :return: True if volume exists, False otherwise
        """
        self.set_source_cluster_connection()
        # do a get volume to check if volume exists or not
        volume_info = netapp_utils.zapi.NaElement('volume-get-iter')
        volume_attributes = netapp_utils.zapi.NaElement('volume-attributes')
        volume_id_attributes = netapp_utils.zapi.NaElement('volume-id-attributes')
        volume_id_attributes.add_new_child('name', self.parameters['source_volume'])
        # if source_volume is present, then source_vserver is also guaranteed to be present
        volume_id_attributes.add_new_child('vserver-name', self.parameters['source_vserver'])
        volume_attributes.add_child_elem(volume_id_attributes)
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(volume_attributes)
        volume_info.add_child_elem(query)
        try:
            result = self.source_server.invoke_successfully(volume_info, True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching source volume details %s : %s'
                                  % (self.parameters['source_volume'], to_native(error)),
                                  exception=traceback.format_exc())
        if result.get_child_by_name('num-records') and int(result.get_child_content('num-records')) > 0:
            return True
        return False

    def snapmirror_policy_rest_get(self, policy_name, svm_name):
        """
        get policy type
        There is a set of system level policies, and users can create their own for a SVM
        REST does not return a svm entry for system policies
        svm_name may not exist yet as it can be created when creating the snapmirror relationship
        """
        policy_type = None
        system_policy_type = None           # policies not associated to a SVM
        api = '/snapmirror/policies'
        query = {
            "name": policy_name,
            "fields": "svm,type"
        }
        response, error = self.rest_api.get(api, query)
        records, error = rrh.check_for_0_or_more_records(api, response, error)
        if error is None and records is not None:
            for record in records:
                if 'svm' in record:
                    if record['svm']['name'] == svm_name:
                        policy_type = record['type']
                        break
                else:
                    system_policy_type = record['type']
        if policy_type is None:
            policy_type = system_policy_type
        return policy_type, error

    def set_initialization_state(self):
        """
        return:
        'snapmirrored' for relationships with a policy of type 'async'
        'in_sync' for relationships with a policy of type 'sync'
        """
        policy_type = 'async'                               # REST defaults to Asynchronous
        if self.parameters.get('policy') is not None:
            # TODO: choose source if ???
            svm_name = self.parameters['destination_vserver']
            policy_type, error = self.snapmirror_policy_rest_get(self.parameters['policy'], svm_name)
            if error:
                pass
            elif policy_type is None:
                error = 'Error: cannot find policy %s for vserver %s' % (self.parameters['policy'], svm_name)
            elif policy_type not in ('async', 'sync'):
                error = 'Error: unexpected type: %s for policy %s for vserver %s' % (policy_type, self.parameters['policy'], svm_name)
            if error:
                self.module.fail_json(msg=error)
        return 'snapmirrored' if policy_type == 'async' else 'in_sync'

    def get_create_body(self):
        initialized = False
        source = dict(path=self.parameters['source_path'])
        if self.na_helper.safe_get(self.parameters, ['source_cluster']):
            source['cluster'] = dict(name=self.parameters['source_cluster'])
        destination = dict(path=self.parameters['destination_path'])
        if self.na_helper.safe_get(self.parameters, ['destination_cluster']):
            destination['cluster'] = dict(name=self.parameters['destination_cluster'])
        body = dict(
            source=source,
            destination=destination,
        )
        if self.na_helper.safe_get(self.parameters, ['create_destination', 'enabled']):     # testing for True
            body['create_destination'] = self.na_helper.filter_out_none_entries(self.parameters['create_destination'])
            if self.parameters['initialize']:
                body['state'] = self.set_initialization_state()
                initialized = True
        if self.na_helper.safe_get(self.parameters, ['policy']) is not None:
            body['policy'] = self.parameters['policy']
        return body, initialized

    def snapmirror_rest_create(self):
        """
        Create a SnapMirror relationship using REST
        """
        body, initialized = self.get_create_body()
        query = dict(return_timeout=60)
        api = 'snapmirror/relationships/'
        response, error = self.rest_api.post(api, body, query)
        response, error = rrh.check_for_error_and_job_results(api, response, error, self.rest_api)
        if error:
            self.module.fail_json(msg=error)
        if self.parameters['initialize'] and not initialized:
            self.snapmirror_initialize()
        return response

    def snapmirror_create(self):
        """
        Create a SnapMirror relationship
        """
        if self.parameters.get('source_hostname') and self.parameters.get('source_volume'):
            if not self.check_if_remote_volume_exists():
                self.module.fail_json(msg='Source volume does not exist. Please specify a volume that exists')
        if self.use_rest:
            return self.snapmirror_rest_create()

        options = {'source-location': self.parameters['source_path'],
                   'destination-location': self.parameters['destination_path']}
        snapmirror_create = netapp_utils.zapi.NaElement.create_node_with_children('snapmirror-create', **options)
        if self.parameters.get('relationship_type'):
            snapmirror_create.add_new_child('relationship-type', self.parameters['relationship_type'])
        if self.parameters.get('schedule'):
            snapmirror_create.add_new_child('schedule', self.parameters['schedule'])
        if self.parameters.get('policy'):
            snapmirror_create.add_new_child('policy', self.parameters['policy'])
        if self.parameters.get('max_transfer_rate'):
            snapmirror_create.add_new_child('max-transfer-rate', str(self.parameters['max_transfer_rate']))
        if self.parameters.get('identity_preserve'):
            snapmirror_create.add_new_child('identity-preserve', str(self.parameters['identity_preserve']))
        try:
            self.server.invoke_successfully(snapmirror_create, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error creating SnapMirror %s' % to_native(error),
                                  exception=traceback.format_exc())
        if self.parameters['initialize']:
            self.snapmirror_initialize()
        return None

    def set_source_cluster_connection(self):
        """
        Setup ontap ZAPI server connection for source hostname
        :return: None
        """
        if self.parameters.get('source_username'):
            self.module.params['username'] = self.parameters['source_username']
        if self.parameters.get('source_password'):
            self.module.params['password'] = self.parameters['source_password']
        self.module.params['hostname'] = self.parameters['source_hostname']
        self.source_server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def delete_snapmirror(self, is_hci, relationship_type, mirror_state):
        """
        Delete a SnapMirror relationship
        #1. Quiesce the SnapMirror relationship at destination
        #2. Break the SnapMirror relationship at the destination
        #3. Release the SnapMirror at source
        #4. Delete SnapMirror at destination
        """
        if not is_hci:
            if not self.parameters.get('source_hostname'):
                self.module.fail_json(msg='Missing parameters for delete: Please specify the '
                                          'source cluster hostname to release the SnapMirror relationship')
        # Quiesce and Break at destination
        if relationship_type not in ['load_sharing', 'vault'] and mirror_state not in ['uninitialized', 'broken-off']:
            self.snapmirror_break()
        # if source is ONTAP, release the destination at source cluster
        if not is_hci:
            self.set_source_cluster_connection()
            if self.get_destination():
                # Release at source
                self.snapmirror_release()
        # Delete at destination
        self.snapmirror_delete()

    def snapmirror_quiesce(self):
        """
        Quiesce SnapMirror relationship - disable all future transfers to this destination
        """
        result = None
        options = {'destination-location': self.parameters['destination_path']}

        snapmirror_quiesce = netapp_utils.zapi.NaElement.create_node_with_children(
            'snapmirror-quiesce', **options)
        try:
            result = self.server.invoke_successfully(snapmirror_quiesce, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error Quiescing SnapMirror : %s'
                                  % (to_native(error)), exception=traceback.format_exc())
        # checking if quiesce was passed successfully
        if result is not None and result['status'] == 'passed':
            return
        elif result is not None and result['status'] != 'passed':
            retries = 5
            while retries > 0:
                time.sleep(5)
                retries = retries - 1
                status = self.snapmirror_get()
                if status['status'] == 'quiesced':
                    return
            if retries == 0:
                self.module.fail_json(msg='Taking a long time to Quiescing SnapMirror, try again later')

    def snapmirror_delete(self):
        """
        Delete SnapMirror relationship at destination cluster
        """
        options = {'destination-location': self.parameters['destination_path']}

        snapmirror_delete = netapp_utils.zapi.NaElement.create_node_with_children(
            'snapmirror-destroy', **options)
        try:
            self.server.invoke_successfully(snapmirror_delete,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error deleting SnapMirror : %s'
                                  % (to_native(error)),
                                  exception=traceback.format_exc())

    def snapmirror_break(self, destination=None):
        """
        Break SnapMirror relationship at destination cluster
        #1. Quiesce the SnapMirror relationship at destination
        #2. Break the SnapMirror relationship at the destination
        """
        self.snapmirror_quiesce()
        if destination is None:
            destination = self.parameters['destination_path']
        options = {'destination-location': destination}
        snapmirror_break = netapp_utils.zapi.NaElement.create_node_with_children(
            'snapmirror-break', **options)
        try:
            self.server.invoke_successfully(snapmirror_break,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error breaking SnapMirror relationship : %s'
                                  % (to_native(error)),
                                  exception=traceback.format_exc())

    def snapmirror_release(self):
        """
        Release SnapMirror relationship from source cluster
        """
        options = {'destination-location': self.parameters['destination_path'],
                   'relationship-info-only': self.na_helper.get_value_for_bool(False, self.parameters['relationship_info_only'])}
        snapmirror_release = netapp_utils.zapi.NaElement.create_node_with_children(
            'snapmirror-release', **options)
        try:
            self.source_server.invoke_successfully(snapmirror_release,
                                                   enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error releasing SnapMirror relationship : %s'
                                  % (to_native(error)),
                                  exception=traceback.format_exc())

    def snapmirror_abort(self):
        """
        Abort a SnapMirror relationship in progress
        """
        options = {'destination-location': self.parameters['destination_path']}
        snapmirror_abort = netapp_utils.zapi.NaElement.create_node_with_children(
            'snapmirror-abort', **options)
        try:
            self.server.invoke_successfully(snapmirror_abort,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error aborting SnapMirror relationship : %s'
                                  % (to_native(error)),
                                  exception=traceback.format_exc())

    def snapmirror_initialize(self):
        """
        Initialize SnapMirror based on relationship state
        """
        current = self.snapmirror_get()
        if current['mirror_state'] != 'snapmirrored':
            initialize_zapi = 'snapmirror-initialize'
            if self.parameters.get('relationship_type') and self.parameters['relationship_type'] == 'load_sharing':
                initialize_zapi = 'snapmirror-initialize-ls-set'
                options = {'source-location': self.parameters['source_path']}
            else:
                options = {'destination-location': self.parameters['destination_path']}
            snapmirror_init = netapp_utils.zapi.NaElement.create_node_with_children(
                initialize_zapi, **options)
            try:
                self.server.invoke_successfully(snapmirror_init,
                                                enable_tunneling=True)
            except netapp_utils.zapi.NaApiError as error:
                self.module.fail_json(msg='Error initializing SnapMirror : %s'
                                      % (to_native(error)),
                                      exception=traceback.format_exc())

    def snapmirror_resync(self):
        """
        resync SnapMirror based on relationship state
        """
        options = {'destination-location': self.parameters['destination_path']}
        snapmirror_resync = netapp_utils.zapi.NaElement.create_node_with_children('snapmirror-resync', **options)
        try:
            self.server.invoke_successfully(snapmirror_resync, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error resyncing SnapMirror : %s'
                                  % (to_native(error)),
                                  exception=traceback.format_exc())

    def snapmirror_resume(self):
        """
        resume SnapMirror based on relationship state
        """
        options = {'destination-location': self.parameters['destination_path']}
        snapmirror_resume = netapp_utils.zapi.NaElement.create_node_with_children('snapmirror-resume', **options)
        try:
            self.server.invoke_successfully(snapmirror_resume, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error resume SnapMirror : %s' % (to_native(error)), exception=traceback.format_exc())

    def snapmirror_restore(self):
        """
        restore SnapMirror based on relationship state
        """
        options = {'destination-location': self.parameters['destination_path'],
                   'source-location': self.parameters['source_path']}
        if self.parameters.get('source_snapshot'):
            options['source-snapshot'] = self.parameters['source_snapshot']
        options['clean-up-failure'] = "true"

        snapmirror_restore = netapp_utils.zapi.NaElement.create_node_with_children('snapmirror-restore', **options)
        try:
            self.server.invoke_successfully(snapmirror_restore, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error restore SnapMirror : %s' % (to_native(error)), exception=traceback.format_exc())

    def snapmirror_modify(self, modify):
        """
        Modify SnapMirror schedule or policy
        """
        options = {'destination-location': self.parameters['destination_path']}
        snapmirror_modify = netapp_utils.zapi.NaElement.create_node_with_children(
            'snapmirror-modify', **options)
        if modify.pop('schedule', None) is not None:
            snapmirror_modify.add_new_child('schedule', modify.get('schedule'))
        if modify.pop('policy', None) is not None:
            snapmirror_modify.add_new_child('policy', modify.get('policy'))
        if modify.pop('max_transfer_rate', None) is not None:
            snapmirror_modify.add_new_child('max-transfer-rate', str(modify.get('max_transfer_rate')))
        if modify:
            self.module.fail_json('Error: unexpected value in modify: %s' % repr(modify))
        try:
            self.server.invoke_successfully(snapmirror_modify,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error modifying SnapMirror schedule or policy : %s'
                                  % (to_native(error)),
                                  exception=traceback.format_exc())

    def snapmirror_update(self, relationship_type):
        """
        Update data in destination endpoint
        """
        zapi = 'snapmirror-update'
        options = {'destination-location': self.parameters['destination_path']}
        if relationship_type == 'load_sharing':
            zapi = 'snapmirror-update-ls-set'
            options = {'source-location': self.parameters['source_path']}

        snapmirror_update = netapp_utils.zapi.NaElement.create_node_with_children(
            zapi, **options)
        try:
            self.server.invoke_successfully(snapmirror_update, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error updating SnapMirror : %s'
                                  % (to_native(error)),
                                  exception=traceback.format_exc())

    def check_parameters(self):
        """
        Validate parameters and fail if one or more required params are missing
        Update source and destination path from vserver and volume parameters
        """
        if self.parameters['state'] == 'present'\
                and (self.parameters.get('source_path') or self.parameters.get('destination_path')):
            if not self.parameters.get('destination_path') or not self.parameters.get('source_path'):
                self.module.fail_json(msg='Missing parameters: Source path or Destination path')
        elif self.parameters.get('source_volume'):
            if not self.parameters.get('source_vserver') or not self.parameters.get('destination_vserver'):
                self.module.fail_json(msg='Missing parameters: source vserver or destination vserver or both')
            self.parameters['source_path'] = self.parameters['source_vserver'] + ":" + self.parameters['source_volume']
            self.parameters['destination_path'] = self.parameters['destination_vserver'] + ":" +\
                self.parameters['destination_volume']
        elif self.parameters.get('source_vserver'):
            self.parameters['source_path'] = self.parameters['source_vserver'] + ":"
            self.parameters['destination_path'] = self.parameters['destination_vserver'] + ":"

    def get_destination(self):
        result = None
        release_get = netapp_utils.zapi.NaElement('snapmirror-get-destination-iter')
        query = netapp_utils.zapi.NaElement('query')
        snapmirror_dest_info = netapp_utils.zapi.NaElement('snapmirror-destination-info')
        snapmirror_dest_info.add_new_child('destination-location', self.parameters['destination_path'])
        query.add_child_elem(snapmirror_dest_info)
        release_get.add_child_elem(query)
        try:
            result = self.source_server.invoke_successfully(release_get, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error fetching snapmirror destinations info: %s' % to_native(error),
                                  exception=traceback.format_exc())
        if result.get_child_by_name('num-records') and \
                int(result.get_child_content('num-records')) > 0:
            return True
        return None

    @staticmethod
    def element_source_path_format_matches(value):
        return re.match(pattern=r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\/lun\/[0-9]+",
                        string=value)

    def check_elementsw_parameters(self, kind='source'):
        """
        Validate all ElementSW cluster parameters required for managing the SnapMirror relationship
        Validate if both source and destination paths are present
        Validate if source_path follows the required format
        Validate SVIP
        Validate if ElementSW volume exists
        :return: None
        """
        path = None
        if kind == 'destination':
            path = self.parameters.get('destination_path')
        elif kind == 'source':
            path = self.parameters.get('source_path')
        if path is None:
            self.module.fail_json(msg="Error: Missing required parameter %s_path for "
                                      "connection_type %s" % (kind, self.parameters['connection_type']))
        else:
            if NetAppONTAPSnapmirror.element_source_path_format_matches(path) is None:
                self.module.fail_json(msg="Error: invalid %s_path %s. "
                                          "If the path is a ElementSW cluster, the value should be of the format"
                                          " <Element_SVIP>:/lun/<Element_VOLUME_ID>" % (kind, path))
        # validate source_path
        elementsw_helper, elem = self.set_element_connection(kind)
        self.validate_elementsw_svip(path, elem)
        self.check_if_elementsw_volume_exists(path, elementsw_helper)

    def validate_elementsw_svip(self, path, elem):
        """
        Validate ElementSW cluster SVIP
        :return: None
        """
        result = None
        try:
            result = elem.get_cluster_info()
        except solidfire.common.ApiServerError as err:
            self.module.fail_json(msg="Error fetching SVIP", exception=to_native(err))
        if result and result.cluster_info.svip:
            cluster_svip = result.cluster_info.svip
            svip = path.split(':')[0]  # split IP address from source_path
            if svip != cluster_svip:
                self.module.fail_json(msg="Error: Invalid SVIP")

    def check_if_elementsw_volume_exists(self, path, elementsw_helper):
        """
        Check if remote ElementSW volume exists
        :return: None
        """
        volume_id, vol_id = None, path.split('/')[-1]
        try:
            volume_id = elementsw_helper.volume_id_exists(int(vol_id))
        except solidfire.common.ApiServerError as err:
            self.module.fail_json(msg="Error fetching Volume details", exception=to_native(err))

        if volume_id is None:
            self.module.fail_json(msg="Error: Source volume does not exist in the ElementSW cluster")

    def asup_log_for_cserver(self, event_name):
        """
        Fetch admin vserver for the given cluster
        Create and Autosupport log event with the given module name
        :param event_name: Name of the event log
        :return: None
        """
        results = netapp_utils.get_cserver(self.server)
        if results is None:
            # We may be running on a vserser
            try:
                netapp_utils.ems_log_event(event_name, self.server)
            except netapp_utils.zapi.NaApiError:
                # Don't fail if we cannot log usage
                pass
        else:
            cserver = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=results)
            netapp_utils.ems_log_event(event_name, cserver)

    def apply(self):
        """
        Apply action to SnapMirror
        """
        self.asup_log_for_cserver("na_ontap_snapmirror")
        # source is ElementSW
        if self.parameters['state'] == 'present' and self.parameters.get('connection_type') == 'elementsw_ontap':
            self.check_elementsw_parameters()
        elif self.parameters.get('connection_type') == 'ontap_elementsw':
            self.check_elementsw_parameters('destination')
        else:
            self.check_parameters()
        if self.parameters['state'] == 'present' and self.parameters.get('connection_type') == 'ontap_elementsw':
            current_elementsw_ontap = self.snapmirror_get(self.parameters['source_path'])
            if current_elementsw_ontap is None:
                self.module.fail_json(msg='Error: creating an ONTAP to ElementSW snapmirror relationship requires an '
                                          'established SnapMirror relation from ElementSW to ONTAP cluster')
        restore = self.parameters.get('relationship_type', '') == 'restore'
        current = self.snapmirror_get() if not restore else None
        # ONTAP automatically convert DP to XDP
        if current and current['relationship_type'] == 'extended_data_protection':
            if self.parameters.get('relationship_type') == 'data_protection':
                self.parameters['relationship_type'] = 'extended_data_protection'
        cd_action = self.na_helper.get_cd_action(current, self.parameters) if not restore else None
        modify = self.na_helper.get_modified_attributes(current, self.parameters) if not restore else None
        if modify and 'relationship_type' in modify:
            self.module.fail_json(msg='Error: cannot modify relationship_type from %s to %s.' %
                                  (current['relationship_type'], modify['relationship_type']))
        actions = list()
        response = None
        element_snapmirror = False
        if self.parameters['state'] == 'present' and restore:
            self.na_helper.changed = True
            actions.append('restore')
            if not self.module.check_mode:
                self.snapmirror_restore()
        elif cd_action == 'create':
            actions.append('create')
            if not self.module.check_mode:
                response = self.snapmirror_create()
        elif cd_action == 'delete':
            if current['status'] == 'transferring':
                actions.append('abort')
                if not self.module.check_mode:
                    self.snapmirror_abort()
                    self.wait_for_status()
            actions.append('delete')
            if not self.module.check_mode:
                element_snapmirror = self.parameters.get('connection_type') == 'elementsw_ontap'
                self.delete_snapmirror(element_snapmirror, current['relationship_type'], current['mirror_state'])
        else:
            if modify:
                actions.append('modify')
                if not self.module.check_mode:
                    self.snapmirror_modify(modify)
            # break relationship when 'relationship_state' == 'broken'
            if current and self.parameters['state'] == 'present' and self.parameters['relationship_state'] == 'broken':
                if current['mirror_state'] == 'uninitialized':
                    self.module.fail_json(msg='SnapMirror relationship cannot be broken if mirror state is uninitialized')
                elif current['relationship_type'] in ['load_sharing', 'vault']:
                    self.module.fail_json(msg='SnapMirror break is not allowed in a load_sharing or vault relationship')
                elif current['mirror_state'] != 'broken-off':
                    actions.append('break')
                    if not self.module.check_mode:
                        self.snapmirror_break()
                    self.na_helper.changed = True
            # check for initialize
            elif current and self.parameters['initialize'] and self.parameters['relationship_state'] == 'active'\
                    and current['mirror_state'] == 'uninitialized' and current['current-transfer-type'] != 'initialize':
                actions.append('initialize')
                if not self.module.check_mode:
                    self.snapmirror_initialize()
                # set changed explicitly for initialize
                self.na_helper.changed = True
            if self.parameters['state'] == 'present' and self.parameters['relationship_state'] == 'active':
                # resume when state is quiesced
                if current['status'] == 'quiesced':
                    actions.append('resume')
                    if not self.module.check_mode:
                        self.snapmirror_resume()
                    # set changed explicitly for resume
                    self.na_helper.changed = True
                # resync when state is broken-off
                if current['mirror_state'] == 'broken-off':
                    actions.append('resync')
                    if not self.module.check_mode:
                        self.snapmirror_resync()
                    # set changed explicitly for resync
                    self.na_helper.changed = True
                # Update when create is called again, or modify is being called
                elif self.parameters['update']:
                    current = self.snapmirror_get()
                    if current['mirror_state'] == 'snapmirrored':
                        actions.append('update')
                        if not self.module.check_mode:
                            self.snapmirror_update(current['relationship_type'])
                        self.na_helper.changed = True
        results = dict(changed=self.na_helper.changed)
        if actions:
            results['actions'] = actions
        if response:
            results['response'] = response
        self.module.exit_json(**results)


def main():
    """Execute action"""
    community_obj = NetAppONTAPSnapmirror()
    community_obj.apply()


if __name__ == '__main__':
    main()
