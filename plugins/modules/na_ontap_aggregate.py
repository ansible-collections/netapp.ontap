#!/usr/bin/python

# (c) 2018-2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_aggregate
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''

module: na_ontap_aggregate
short_description: NetApp ONTAP manage aggregates.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: 2.6.0
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

description:
- Create, delete, or manage aggregates on ONTAP.

options:

  state:
    description:
    - Whether the specified aggregate should exist or not.
    choices: ['present', 'absent']
    default: 'present'
    type: str

  service_state:
    description:
    - Whether the specified aggregate should be enabled or disabled. Creates aggregate if doesnt exist.
    choices: ['online', 'offline']
    type: str

  name:
    description:
    - The name of the aggregate to manage.
    required: true
    type: str

  from_name:
    description:
    - Name of the aggregate to be renamed.
    type: str
    version_added: 2.7.0

  nodes:
    description:
    - Node(s) for the aggregate to be created on.  If no node specified, mgmt lif home will be used.
    - If multiple nodes specified an aggr stripe will be made.
    type: list
    elements: str

  disk_type:
    description:
    - Type of disk to use to build aggregate
    choices: ['ATA', 'BSAS', 'FCAL', 'FSAS', 'LUN', 'MSATA', 'SAS', 'SSD', 'VMDISK']
    type: str
    version_added: 2.7.0

  disk_count:
    description:
    - Number of disks to place into the aggregate, including parity disks.
    - The disks in this newly-created aggregate come from the spare disk pool.
    - The smallest disks in this pool join the aggregate first, unless the C(disk-size) argument is provided.
    - Either C(disk-count) or C(disks) must be supplied. Range [0..2^31-1].
    - Required when C(state=present).
    - Modifiable only if specified disk_count is larger than current disk_count.
    - Cannot create raidgroup with 1 disk when using raid type raid4.
    - If the disk_count % raid_size == 1, only disk_count/raid_size * raid_size will be added.
    - If disk_count is 6, raid_type is raid4, raid_size 4, all 6 disks will be added.
    - If disk_count is 5, raid_type is raid4, raid_size 4, 5/4 * 4 = 4 will be added. 1 will not be added.
    type: int

  disk_size:
    description:
    - Disk size to use in 4K block size.  Disks within 10% of specified size will be used.
    type: int
    version_added: 2.7.0

  disk_size_with_unit:
    description:
    - Disk size to use in the specified unit.
    - It is a positive integer number followed by unit of T/G/M/K. For example, 72G, 1T and 32M.
    - This option is ignored if a specific list of disks is specified through the "disks" parameter.
    - You must only use one of either "disk-size" or "disk-size-with-unit" parameters.
    type: str

  raid_size:
    description:
    - Sets the maximum number of drives per raid group.
    type: int
    version_added: 2.7.0

  raid_type:
    description:
    - Specifies the type of RAID groups to use in the new aggregate.
    - raid_0 is only available on ONTAP Select.
    choices: ['raid4', 'raid_dp', 'raid_tec', 'raid_0']
    type: str
    version_added: 2.7.0

  unmount_volumes:
    description:
    - If set to "TRUE", this option specifies that all of the volumes hosted by the given aggregate are to be unmounted
    - before the offline operation is executed.
    - By default, the system will reject any attempt to offline an aggregate that hosts one or more online volumes.
    type: bool

  disks:
    description:
    - Specific list of disks to use for the new aggregate.
    - To create a "mirrored" aggregate with a specific list of disks, both 'disks' and 'mirror_disks' options must be supplied.
      Additionally, the same number of disks must be supplied in both lists.
    type: list
    elements: str
    version_added: 2.8.0

  is_mirrored:
    description:
    - Specifies that the new aggregate be mirrored (have two plexes).
    - If set to true, then the indicated disks will be split across the two plexes. By default, the new aggregate will not be mirrored.
    - This option cannot be used when a specific list of disks is supplied with either the 'disks' or 'mirror_disks' options.
    type: bool
    version_added: 2.8.0

  mirror_disks:
    description:
    - List of mirror disks to use. It must contain the same number of disks specified in 'disks'.
    type: list
    elements: str
    version_added: 2.8.0

  spare_pool:
    description:
    - Specifies the spare pool from which to select spare disks to use in creation of a new aggregate.
    choices: ['Pool0', 'Pool1']
    type: str
    version_added: 2.8.0

  wait_for_online:
    description:
    - Set this parameter to 'true' for synchronous execution during create (wait until aggregate status is online)
    - Set this parameter to 'false' for asynchronous execution
    - For asynchronous, execution exits as soon as the request is sent, without checking aggregate status
    type: bool
    default: false
    version_added: 2.8.0

  time_out:
    description:
      - time to wait for aggregate creation in seconds
      - default is set to 100 seconds
    type: int
    default: 100
    version_added: 2.8.0

  object_store_name:
    description:
      - Name of the object store configuration attached to the aggregate
    type: str
    version_added: 2.9.0

  snaplock_type:
    description:
      - Type of snaplock for the aggregate being created.
    choices: ['compliance', 'enterprise', 'non_snaplock']
    type: str
    version_added: 20.1.0

  ignore_pool_checks:
    description:
      - only valid when I(disks) option is used.
      - disks in a plex should belong to the same spare pool, and mirror disks to another spare pool.
      - when set to true, these checks are ignored.
    type: bool
    version_added: 20.8.0
'''

EXAMPLES = """
- name: Create Aggregates and wait 5 minutes until aggregate is online
  na_ontap_aggregate:
    state: present
    service_state: online
    name: ansibleAggr
    disk_count: 1
    wait_for_online: True
    time_out: 300
    snaplock_type: non_snaplock
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"

- name: Manage Aggregates
  na_ontap_aggregate:
    state: present
    service_state: offline
    unmount_volumes: true
    name: ansibleAggr
    disk_count: 1
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"

- name: Attach object store
  na_ontap_aggregate:
    state: present
    name: aggr4
    object_store_name: sgws_305
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"

- name: Rename Aggregates
  na_ontap_aggregate:
    state: present
    service_state: online
    from_name: ansibleAggr
    name: ansibleAggr2
    disk_count: 1
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"

- name: Delete Aggregates
  na_ontap_aggregate:
    state: absent
    service_state: offline
    unmount_volumes: true
    name: ansibleAggr
    hostname: "{{ netapp_hostname }}"
    username: "{{ netapp_username }}"
    password: "{{ netapp_password }}"
"""

RETURN = """

"""
import time
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule

HAS_NETAPP_LIB = netapp_utils.has_netapp_lib()


class NetAppOntapAggregate(object):
    ''' object initialize and class methods '''

    def __init__(self):
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            name=dict(required=True, type='str'),
            disks=dict(required=False, type='list', elements='str'),
            disk_count=dict(required=False, type='int', default=None),
            disk_size=dict(required=False, type='int'),
            disk_size_with_unit=dict(required=False, type='str'),
            disk_type=dict(required=False, choices=['ATA', 'BSAS', 'FCAL', 'FSAS', 'LUN', 'MSATA', 'SAS', 'SSD', 'VMDISK']),
            from_name=dict(required=False, type='str'),
            mirror_disks=dict(required=False, type='list', elements='str'),
            nodes=dict(required=False, type='list', elements='str'),
            is_mirrored=dict(required=False, type='bool'),
            raid_size=dict(required=False, type='int'),
            raid_type=dict(required=False, choices=['raid4', 'raid_dp', 'raid_tec', 'raid_0']),
            service_state=dict(required=False, choices=['online', 'offline']),
            spare_pool=dict(required=False, choices=['Pool0', 'Pool1']),
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            unmount_volumes=dict(required=False, type='bool'),
            wait_for_online=dict(required=False, type='bool', default=False),
            time_out=dict(required=False, type='int', default=100),
            object_store_name=dict(required=False, type='str'),
            snaplock_type=dict(required=False, type='str', choices=['compliance', 'enterprise', 'non_snaplock']),
            ignore_pool_checks=dict(required=False, type='bool')
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            required_if=[
                ('service_state', 'offline', ['unmount_volumes']),
            ],
            mutually_exclusive=[
                ('is_mirrored', 'disks'),
                ('is_mirrored', 'mirror_disks'),
                ('is_mirrored', 'spare_pool'),
                ('spare_pool', 'disks'),
                ('disk_count', 'disks'),
                ('disk_size', 'disk_size_with_unit')
            ],
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.using_vserver_msg = None   # This module should be run as cluster admin
        self.parameters = self.na_helper.set_parameters(self.module.params)
        if self.parameters.get('mirror_disks') is not None and self.parameters.get('disks') is None:
            self.module.fail_json(msg="mirror_disks require disks options to be set")
        if HAS_NETAPP_LIB is False:
            self.module.fail_json(msg="the python NetApp-Lib module is required")
        else:
            self.server = netapp_utils.setup_na_ontap_zapi(module=self.module)

    def aggr_get_iter(self, name):
        """
        Return aggr-get-iter query results
        :param name: Name of the aggregate
        :return: NaElement if aggregate found, None otherwise
        """

        aggr_get_iter = netapp_utils.zapi.NaElement('aggr-get-iter')
        query_details = netapp_utils.zapi.NaElement.create_node_with_children(
            'aggr-attributes', **{'aggregate-name': name})
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(query_details)
        aggr_get_iter.add_child_elem(query)
        result = None
        try:
            result = self.server.invoke_successfully(aggr_get_iter, enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            # Error 13040 denotes an aggregate not being found.
            if to_native(error.code) == "13040":
                pass
            else:
                msg = to_native(error)
                if self.using_vserver_msg is not None:
                    msg += '.  Added info: %s.' % self.using_vserver_msg
                self.module.fail_json(msg=msg, exception=traceback.format_exc())
        return result

    def get_aggr(self, name=None):
        """
        Fetch details if aggregate exists.
        :param name: Name of the aggregate to be fetched
        :return:
            Dictionary of current details if aggregate found
            None if aggregate is not found
        """
        if name is None:
            name = self.parameters['name']
        aggr_get = self.aggr_get_iter(name)
        if (aggr_get and aggr_get.get_child_by_name('num-records') and
                int(aggr_get.get_child_content('num-records')) >= 1):
            current_aggr = dict()
            attr = aggr_get.get_child_by_name('attributes-list').get_child_by_name('aggr-attributes')
            current_aggr['service_state'] = attr.get_child_by_name('aggr-raid-attributes').get_child_content('state')
            if attr.get_child_by_name('aggr-raid-attributes').get_child_content('disk-count'):
                current_aggr['disk_count'] = int(attr.get_child_by_name('aggr-raid-attributes').get_child_content('disk-count'))
            return current_aggr
        return None

    def disk_get_iter(self, name):
        """
        Return storage-disk-get-iter query results
        Filter disk list by aggregate name, and only reports disk-name and plex-name
        :param name: Name of the aggregate
        :return: NaElement
        """

        disk_get_iter = netapp_utils.zapi.NaElement('storage-disk-get-iter')
        query_details = {
            'query': {
                'storage-disk-info': {
                    'disk-raid-info': {
                        'disk-aggregate-info': {
                            'aggregate-name': name
                        }
                    }
                }
            }
        }
        disk_get_iter.translate_struct(query_details)
        attributes = {
            'desired-attributes': {
                'storage-disk-info': {
                    'disk-name': None,
                    'disk-raid-info': {
                        'disk_aggregate_info': {
                            'plex-name': None
                        }
                    }
                }
            }
        }
        disk_get_iter.translate_struct(attributes)

        result = None
        try:
            result = self.server.invoke_successfully(disk_get_iter, enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg=to_native(error), exception=traceback.format_exc())
        return result

    def get_aggr_disks(self, name):
        """
        Fetch disks that are used for this aggregate.
        :param name: Name of the aggregate to be fetched
        :return:
            list of tuples (disk-name, plex-name)
            empty list if aggregate is not found
        """
        disks = list()
        aggr_get = self.disk_get_iter(name)
        if (aggr_get and aggr_get.get_child_by_name('num-records') and
                int(aggr_get.get_child_content('num-records')) >= 1):
            attr = aggr_get.get_child_by_name('attributes-list')
            disks = [(disk_info.get_child_content('disk-name'),
                      disk_info.get_child_by_name('disk-raid-info').get_child_by_name('disk-aggregate-info').get_child_content('plex-name'))
                     for disk_info in attr.get_children()]
        return disks

    def object_store_get_iter(self, name):
        """
        Return aggr-object-store-get query results
        :return: NaElement if object-store for given aggregate found, None otherwise
        """

        object_store_get_iter = netapp_utils.zapi.NaElement('aggr-object-store-get-iter')
        query_details = netapp_utils.zapi.NaElement.create_node_with_children(
            'object-store-information', **{'object-store-name': self.parameters.get('object_store_name'),
                                           'aggregate': name})
        query = netapp_utils.zapi.NaElement('query')
        query.add_child_elem(query_details)
        object_store_get_iter.add_child_elem(query)
        result = None
        try:
            result = self.server.invoke_successfully(object_store_get_iter, enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg=to_native(error), exception=traceback.format_exc())
        return result

    def get_object_store(self, name):
        """
        Fetch details if object store attached to the given aggregate exists.
        :return:
            Dictionary of current details if object store attached to the given aggregate is found
            None if object store is not found
        """
        object_store_get = self.object_store_get_iter(name)
        if (object_store_get and object_store_get.get_child_by_name('num-records') and
                int(object_store_get.get_child_content('num-records')) >= 1):
            current_object_store = dict()
            attr = object_store_get.get_child_by_name('attributes-list').\
                get_child_by_name('object-store-information')
            current_object_store['object_store_name'] = attr.get_child_content('object-store-name')
            return current_object_store
        return None

    def aggregate_online(self):
        """
        Set state of an offline aggregate to online
        :return: None
        """
        online_aggr = netapp_utils.zapi.NaElement.create_node_with_children(
            'aggr-online', **{'aggregate': self.parameters['name'],
                              'force-online': 'true'})
        try:
            self.server.invoke_successfully(online_aggr,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error changing the state of aggregate %s to %s: %s' %
                                  (self.parameters['name'], self.parameters['service_state'], to_native(error)),
                                  exception=traceback.format_exc())

    def aggregate_offline(self):
        """
        Set state of an online aggregate to offline
        :return: None
        """
        offline_aggr = netapp_utils.zapi.NaElement.create_node_with_children(
            'aggr-offline', **{'aggregate': self.parameters['name'],
                               'force-offline': 'false',
                               'unmount-volumes': str(self.parameters['unmount_volumes'])})
        try:
            self.server.invoke_successfully(offline_aggr, enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error changing the state of aggregate %s to %s: %s' %
                                  (self.parameters['name'], self.parameters['service_state'], to_native(error)),
                                  exception=traceback.format_exc())

    @staticmethod
    def get_disks_or_mirror_disks_object(name, disks):
        '''
        create ZAPI object for disks or mirror_disks
        '''
        disks_obj = netapp_utils.zapi.NaElement(name)
        for disk in disks:
            disk_info_obj = netapp_utils.zapi.NaElement('disk-info')
            disk_info_obj.add_new_child('name', disk)
            disks_obj.add_child_elem(disk_info_obj)
        return disks_obj

    def create_aggr(self):
        """
        Create aggregate
        :return: None
        """
        options = {'aggregate': self.parameters['name']}
        if self.parameters.get('disk_count'):
            options['disk-count'] = str(self.parameters['disk_count'])
        if self.parameters.get('disk_type'):
            options['disk-type'] = self.parameters['disk_type']
        if self.parameters.get('raid_size'):
            options['raid-size'] = str(self.parameters['raid_size'])
        if self.parameters.get('raid_type'):
            options['raid-type'] = self.parameters['raid_type']
        if self.parameters.get('disk_size'):
            options['disk-size'] = str(self.parameters['disk_size'])
        if self.parameters.get('disk_size_with_unit'):
            options['disk-size-with-unit'] = str(self.parameters['disk_size_with_unit'])
        if self.parameters.get('is_mirrored'):
            options['is-mirrored'] = str(self.parameters['is_mirrored'])
        if self.parameters.get('spare_pool'):
            options['spare-pool'] = self.parameters['spare_pool']
        if self.parameters.get('raid_type'):
            options['raid-type'] = self.parameters['raid_type']
        if self.parameters.get('snaplock_type'):
            options['snaplock-type'] = self.parameters['snaplock_type']
        if self.parameters.get('ignore_pool_checks'):
            options['ignore-pool-checks'] = str(self.parameters['ignore_pool_checks'])
        aggr_create = netapp_utils.zapi.NaElement.create_node_with_children('aggr-create', **options)
        if self.parameters.get('nodes'):
            nodes_obj = netapp_utils.zapi.NaElement('nodes')
            aggr_create.add_child_elem(nodes_obj)
            for node in self.parameters['nodes']:
                nodes_obj.add_new_child('node-name', node)
        if self.parameters.get('disks'):
            aggr_create.add_child_elem(self.get_disks_or_mirror_disks_object('disks', self.parameters.get('disks')))
        if self.parameters.get('mirror_disks'):
            aggr_create.add_child_elem(self.get_disks_or_mirror_disks_object('mirror-disks', self.parameters.get('mirror_disks')))

        try:
            self.server.invoke_successfully(aggr_create, enable_tunneling=False)
            if self.parameters.get('wait_for_online'):
                # round off time_out
                retries = (self.parameters['time_out'] + 5) / 10
                current = self.get_aggr()
                status = None if current is None else current['service_state']
                while status != 'online' and retries > 0:
                    time.sleep(10)
                    retries = retries - 1
                    current = self.get_aggr()
                    status = None if current is None else current['service_state']
            else:
                current = self.get_aggr()
            if current is not None and current.get('disk_count') != self.parameters.get('disk_count'):
                self.module.exit_json(changed=self.na_helper.changed,
                                      warnings="Aggregate created with mismatched disk_count: created %s not %s"
                                      % (current.get('disk_count'), self.parameters.get('disk_count')))
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error provisioning aggregate %s: %s"
                                  % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def delete_aggr(self):
        """
        Delete aggregate.
        :return: None
        """
        aggr_destroy = netapp_utils.zapi.NaElement.create_node_with_children(
            'aggr-destroy', **{'aggregate': self.parameters['name']})

        try:
            self.server.invoke_successfully(aggr_destroy,
                                            enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error removing aggregate %s: %s" % (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def rename_aggregate(self):
        """
        Rename aggregate.
        """
        aggr_rename = netapp_utils.zapi.NaElement.create_node_with_children(
            'aggr-rename', **{'aggregate': self.parameters['from_name'],
                              'new-aggregate-name': self.parameters['name']})

        try:
            self.server.invoke_successfully(aggr_rename, enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error renaming aggregate %s: %s"
                                  % (self.parameters['from_name'], to_native(error)),
                                  exception=traceback.format_exc())

    def modify_aggr(self, modify):
        """
        Modify state of the aggregate
        :param modify: dictionary of parameters to be modified
        :return: None
        """
        if modify.get('service_state') == 'offline':
            self.aggregate_offline()
        else:
            disk_size = 0
            disk_size_with_unit = None
            if modify.get('service_state') == 'online':
                self.aggregate_online()
            if modify.get('disk_size'):
                disk_size = modify.get('disk_size')
            if modify.get('disk_size_with_unit'):
                disk_size_with_unit = modify.get('disk_size_with_unit')
            if modify.get('disk_count'):
                self.add_disks(modify['disk_count'], disk_size=disk_size, disk_size_with_unit=disk_size_with_unit)
            if modify.get('disks_to_add') or modify.get('mirror_disks_to_add'):
                self.add_disks(0, modify.get('disks_to_add'), modify.get('mirror_disks_to_add'))

    def attach_object_store_to_aggr(self):
        """
        Attach object store to aggregate.
        :return: None
        """
        attach_object_store = netapp_utils.zapi.NaElement.create_node_with_children(
            'aggr-object-store-attach', **{'aggregate': self.parameters['name'],
                                           'object-store-name': self.parameters['object_store_name']})

        try:
            self.server.invoke_successfully(attach_object_store,
                                            enable_tunneling=False)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg="Error attaching object store %s to aggregate %s: %s" %
                                  (self.parameters['object_store_name'], self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def add_disks(self, count=0, disks=None, mirror_disks=None, disk_size=0, disk_size_with_unit=None):
        """
        Add additional disks to aggregate.
        :return: None
        """
        options = {'aggregate': self.parameters['name']}
        if count:
            options['disk-count'] = str(count)
        if disks and self.parameters.get('ignore_pool_checks'):
            options['ignore-pool-checks'] = str(self.parameters['ignore_pool_checks'])
        if disk_size:
            options['disk-size'] = str(disk_size)
        if disk_size_with_unit:
            options['disk-size-with-unit'] = disk_size_with_unit
        aggr_add = netapp_utils.zapi.NaElement.create_node_with_children(
            'aggr-add', **options)
        if disks:
            aggr_add.add_child_elem(self.get_disks_or_mirror_disks_object('disks', disks))
        if mirror_disks:
            aggr_add.add_child_elem(self.get_disks_or_mirror_disks_object('mirror-disks', mirror_disks))

        try:
            self.server.invoke_successfully(aggr_add,
                                            enable_tunneling=True)
        except netapp_utils.zapi.NaApiError as error:
            self.module.fail_json(msg='Error adding additional disks to aggregate %s: %s' %
                                  (self.parameters['name'], to_native(error)),
                                  exception=traceback.format_exc())

    def asup_log_for_cserver(self, event_name):
        """
        Fetch admin vserver for the given cluster
        Create and Autosupport log event with the given module name
        :param event_name: Name of the event log
        :return: None
        """
        cserver = netapp_utils.get_cserver(self.server)
        if cserver is None:
            server = self.server
            self.using_vserver_msg = netapp_utils.ERROR_MSG['no_cserver']
            event_name += ':error_no_cserver'
        else:
            server = netapp_utils.setup_na_ontap_zapi(module=self.module, vserver=cserver)
        netapp_utils.ems_log_event(event_name, server)

    def map_plex_to_primary_and_mirror(self, plex_disks, disks, mirror_disks):
        '''
        we have N plexes, and disks, and maybe mirror_disks
        we're trying to find which plex is used for disks, and which one, if applicable, for mirror_disks
        :return: a tuple with the names of the two plexes (disks_plex, mirror_disks_plex)
        the second one can be None
        '''
        disks_plex = None
        mirror_disks_plex = None
        error = None
        for plex in plex_disks:
            common = set(plex_disks[plex]).intersection(set(disks))
            if common:
                if disks_plex is None:
                    disks_plex = plex
                else:
                    error = 'found overlapping plexes: %s and %s' % (disks_plex, plex)
            if mirror_disks is not None:
                common = set(plex_disks[plex]).intersection(set(mirror_disks))
                if common:
                    if mirror_disks_plex is None:
                        mirror_disks_plex = plex
                    else:
                        error = 'found overlapping mirror plexes: %s and %s' % (mirror_disks_plex, plex)
        if error is None:
            # make sure we found a match
            if disks_plex is None:
                error = 'cannot not match disks with current aggregate disks'
            if mirror_disks is not None and mirror_disks_plex is None:
                if error is not None:
                    error += ', and '
                error = 'cannot not match mirror_disks with current aggregate disks'
        if error:
            self.module.fail_json(msg="Error mapping disks for aggregate %s: %s.  Found: %s" %
                                  (self.parameters['name'], error, str(plex_disks)))
        return disks_plex, mirror_disks_plex

    def get_disks_to_add(self, aggr_name, disks, mirror_disks):
        '''
        Get list of disks used by the aggregate, as primary and mirror.
        Report error if:
          the plexes in use cannot be matched with user inputs (we expect some overlap)
          the user request requires some disks to be removed (not supported)
        : return: a tuple of two lists of disks: disks_to_add, mirror_disks_to_add
        '''
        # let's see if we need to add disks
        disks_in_use = self.get_aggr_disks(aggr_name)
        # we expect a list of tuples (disk_name, plex_name), if there is a mirror, we should have 2 plexes
        # let's get a list of disks for each plex
        plex_disks = dict()
        for disk_name, plex_name in disks_in_use:
            plex_disks.setdefault(plex_name, []).append(disk_name)
        # find who is who
        disks_plex, mirror_disks_plex = self.map_plex_to_primary_and_mirror(plex_disks, disks, mirror_disks)
        # Now that we know what is which, find what needs to be removed (error), and what needs to be added
        disks_to_remove = [disk for disk in plex_disks[disks_plex] if disk not in disks]
        if mirror_disks_plex:
            disks_to_remove.extend([disk for disk in plex_disks[mirror_disks_plex] if disk not in mirror_disks])
        if disks_to_remove:
            error = 'these disks cannot be removed: %s' % str(disks_to_remove)
            self.module.fail_json(msg="Error removing disks is not supported.  Aggregate %s: %s.  In use: %s" %
                                  (aggr_name, error, str(plex_disks)))
        # finally, what's to be added
        disks_to_add = [disk for disk in disks if disk not in plex_disks[disks_plex]]
        mirror_disks_to_add = list()
        if mirror_disks_plex:
            mirror_disks_to_add = [disk for disk in mirror_disks if disk not in plex_disks[mirror_disks_plex]]
        if mirror_disks_to_add and not disks_to_add:
            self.module.fail_json(msg="Error cannot add mirror disks %s without adding disks for aggregate %s.  In use: %s" %
                                  (str(mirror_disks_to_add), aggr_name, str(plex_disks)))
        if disks_to_add or mirror_disks_to_add:
            self.na_helper.changed = True

        return disks_to_add, mirror_disks_to_add

    def apply(self):
        """
        Apply action to the aggregate
        :return: None
        """
        self.asup_log_for_cserver("na_ontap_aggregate")
        object_store_cd_action = None
        aggr_name = self.parameters['name']
        current = self.get_aggr()
        # rename and create are mutually exclusive
        rename, cd_action, object_store_current = None, None, None
        if self.parameters.get('from_name'):
            old_aggr = self.get_aggr(self.parameters['from_name'])
            rename = self.na_helper.is_rename_action(old_aggr, current)
            if rename is None:
                self.module.fail_json(msg="Error renaming: aggregate %s does not exist" % self.parameters['from_name'])
            if rename:
                current = old_aggr
                aggr_name = self.parameters['from_name']
        else:
            cd_action = self.na_helper.get_cd_action(current, self.parameters)
        modify = self.na_helper.get_modified_attributes(current, self.parameters)

        if cd_action is None and self.parameters.get('disks') and current is not None:
            modify['disks_to_add'], modify['mirror_disks_to_add'] = \
                self.get_disks_to_add(aggr_name, self.parameters['disks'], self.parameters.get('mirror_disks'))

        if modify.get('disk_count'):
            if int(modify['disk_count']) < int(current['disk_count']):
                self.module.fail_json(msg="specified disk_count is less than current disk_count. Only adding_disk is allowed.")
            else:
                modify['disk_count'] = modify['disk_count'] - current['disk_count']

        if self.parameters.get('object_store_name'):
            object_store_current = None
            if current:
                object_store_current = self.get_object_store(aggr_name)
            object_store_cd_action = self.na_helper.get_cd_action(object_store_current, self.parameters.get('object_store_name'))
            if object_store_cd_action is None and object_store_current is not None\
                    and object_store_current['object_store_name'] != self.parameters.get('object_store_name'):
                self.module.fail_json(msg='Error: object store %s is already associated with aggregate %s.' %
                                      (object_store_current['object_store_name'], aggr_name))

        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                self.create_aggr()
            elif cd_action == 'delete':
                self.delete_aggr()
            else:
                if rename:
                    self.rename_aggregate()
                if modify:
                    self.modify_aggr(modify)
            if object_store_cd_action == 'create':
                self.attach_object_store_to_aggr()
        self.module.exit_json(changed=self.na_helper.changed)


def main():
    """
    Create Aggregate class instance and invoke apply
    :return: None
    """
    obj_aggr = NetAppOntapAggregate()
    obj_aggr.apply()


if __name__ == '__main__':
    main()
