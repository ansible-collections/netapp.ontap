#!/usr/bin/python

# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" NetApp ONTAP Info using REST APIs """


from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}

DOCUMENTATION = '''
module: na_ontap_rest_info
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
short_description: NetApp ONTAP information gatherer using REST APIs
description:
    - This module allows you to gather various information about ONTAP configuration using REST APIs
version_added: 20.5.0

options:
    state:
        type: str
        description:
            - deprecated as of 21.1.0.
            - this option was ignored and continues to be ignored.
    gather_subset:
        type: list
        elements: str
        description:
            - When supplied, this argument will restrict the information collected
                to a given subset.  Either the info name or the Rest API can be given.
                Possible values for this argument include
                "aggregate_info" or "storage/aggregates",
                "application_info" or "application/applications",
                "application_template_info" or "application/templates",
                "autosupport_config_info" or "support/autosupport",
                "autosupport_messages_history" or "support/autosupport/messages",
                "broadcast_domains_info" or "network/ethernet/broadcast-domains",
                "cifs_home_directory_info" or "protocols/cifs/home-directory/search-paths",
                "cifs_services_info" or "protocols/cifs/services",
                "cifs_share_info" or "protocols/cifs/shares",
                "cloud_targets_info" or "cloud/targets",
                "cluster_chassis_info" or "cluster/chassis",
                "cluster_jobs_info" or "cluster/jobs",
                "cluster_metrics_info" or "cluster/metrics",
                "cluster_node_info" or "cluster/nodes",
                "cluster_peer_info" or "cluster/peers",
                "cluster_schedules" or "cluster/schedules",
                "cluster_software_download" or "cluster/software/download",
                "cluster_software_history" or "cluster/software/history",
                "cluster_software_packages" or "cluster/software/packages",
                "disk_info" or "storage/disks",
                "event_notification_info" or "support/ems/destinations",
                "event_notification_destination_info" or "support/ems/destinations",
                "initiator_groups_info" or "protocols/san/igroups",
                "ip_interfaces_info" or "network/ip/interfaces",
                "ip_routes_info" or "network/ip/routes",
                "ip_service_policies" or "network/ip/service-policies",
                "network_ipspaces_info" or "network/ipspaces",
                "network_ports_info" or "network/ethernet/ports",
                "ontap_system_version" or "cluster/software",
                "san_fc_logins_info" or "network/fc/logins",
                "san_fc_wppn-aliases" or "network/fc/wwpn-aliases",
                "san_fcp_services" or "protocols/san/fcp/services",
                "san_iscsi_credentials" or "protocols/san/iscsi/credentials",
                "san_iscsi_services" or "protocols/san/iscsi/services",
                "san_lun_maps" or "protocols/san/lun-maps",
                "security_login_info" or "security/accounts",
                "security_login_rest_role_info" or "security/roles",
                "storage_flexcaches_info" or "storage/flexcache/flexcaches",
                "storage_flexcaches_origin_info" or "storage/flexcache/origins",
                "storage_luns_info" or "storage/luns",
                "storage_NVMe_namespaces" or "storage/namespaces",
                "storage_ports_info" or "storage/ports",
                "storage_qos_policies" or "storage/qos/policies",
                "storage_qtrees_config" or "storage/qtrees",
                "storage_quota_reports" or "storage/quota/reports",
                "storage_quota_policy_rules" or "storage/quota/rules",
                "storage_shelves_config" or "storage/shelves",
                "storage_snapshot_policies" or "storage/snapshot-policies",
                "support_ems_config" or "support/ems",
                "support_ems_events" or "support/ems/events",
                "support_ems_filters" or "support/ems/filters",
                "svm_dns_config_info" or "name-services/dns",
                "svm_ldap_config_info" or "name-services/ldap",
                "svm_name_mapping_config_info" or "name-services/name-mappings",
                "svm_nis_config_info" or "name-services/nis",
                "svm_peers_info" or "svm/peers",
                "svm_peer-permissions_info" or "svm/peer-permissions",
                "vserver_info" or "svm/svms",
                "volume_info" or "storage/volumes",
                Can specify a list of values to include a larger subset.
            - REST APIs are supported with ONTAP 9.6 onwards.
        default: "all"
    max_records:
        type: int
        description:
            - Maximum number of records returned in a single call.
        default: 1024
    fields:
        type: list
        elements: str
        description:
            - Request specific fields from subset.
               '*' to return all the fields, one or more subsets are allowed.
               '<list of fields>'  to return specified fields, only one subset will be allowed.
            - If the option is not present, return all the fields.
        version_added: '20.6.0'
    parameters:
        description:
        - Allows for any rest option to be passed in
        type: dict
        version_added: '20.7.0'
'''

EXAMPLES = '''
- name: run ONTAP gather facts for vserver info
  na_ontap_info_rest:
      hostname: "1.2.3.4"
      username: "testuser"
      password: "test-password"
      https: true
      validate_certs: false
      use_rest: Always
      gather_subset:
      - vserver_info
- name: run ONTAP gather facts for aggregate info and volume info
  na_ontap_info_rest:
      hostname: "1.2.3.4"
      username: "testuser"
      password: "test-password"
      https: true
      validate_certs: false
      use_rest: Always
      gather_subset:
      - aggregate_info
      - volume_info
- name: run ONTAP gather facts for all subsets
  na_ontap_info_rest:
      hostname: "1.2.3.4"
      username: "testuser"
      password: "test-password"
      https: true
      validate_certs: false
      use_rest: Always
      gather_subset:
      - all
- name: run ONTAP gather facts for aggregate info and volume info with fields section
  na_ontap_info_rest:
      hostname: "1.2.3.4"
      username: "testuser"
      password: "test-password"
      https: true
      fields:
      - '*'
      validate_certs: false
      use_rest: Always
      gather_subset:
      - aggregate_info
      - volume_info
- name: run ONTAP gather facts for aggregate info with specified fields
  na_ontap_info_rest:
      hostname: "1.2.3.4"
      username: "testuser"
      password: "test-password"
      https: true
      fields:
      - 'uuid'
      - 'name'
      - 'node'
      validate_certs: false
      use_rest: Always
      gather_subset:
      - aggregate_info
'''

from ansible.module_utils.basic import AnsibleModule
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI


class NetAppONTAPGatherInfo(object):
    '''Class with gather info methods'''

    def __init__(self):
        """
        Parse arguments, setup state variables,
        check paramenters and ensure request module is installed
        """
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(type='str', required=False),
            gather_subset=dict(default=['all'], type='list', elements='str', required=False),
            max_records=dict(type='int', default=1024, required=False),
            fields=dict(type='list', elements='str', required=False),
            parameters=dict(type='dict', required=False)
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        # set up variables
        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)
        self.fields = list()

        self.rest_api = OntapRestAPI(self.module)

    def validate_ontap_version(self):
        """
            Method to validate the ONTAP version
        """

        api = 'cluster'
        data = {'fields': ['version']}

        ontap_version, error = self.rest_api.get(api, data)

        if error:
            self.module.fail_json(msg=error)

        return ontap_version

    def get_subset_info(self, gather_subset_info):
        """
            Gather ONTAP information for the given subset using REST APIs
            Input for REST APIs call : (api, data)
            return gathered_ontap_info
        """

        api = gather_subset_info['api_call']
        if gather_subset_info.pop('post', False):
            self.run_post(gather_subset_info)
        data = {'max_records': self.parameters['max_records'], 'fields': self.fields}
        # allow for passing in any additional rest api fields
        if self.parameters.get('parameters'):
            for each in self.parameters['parameters']:
                data[each] = self.parameters['parameters'][each]

        gathered_ontap_info, error = self.rest_api.get(api, data)

        if error:
            # Fail the module if error occurs from REST APIs call
            if int(error.get('code', 0)) == 6:
                self.module.fail_json(msg="%s user is not authorized to make %s api call" % (self.parameters.get('username'), api))
            # if Aggr recommender can't make a recommendation it will fail with the following error code.
            # We don't want to fail
            elif int(error.get('code', 0)) == 19726344 and "No recommendation can be made for this cluster" in error.get('message'):
                return error.get('message')
            # If the API doesn't exist (using an older system) we don't want to fail
            elif int(error.get('code', 0)) == 3:
                return error.get('message')
            else:
                self.module.fail_json(msg=error)
        else:
            return gathered_ontap_info

        return None

    def run_post(self, gather_subset_info):
        api = gather_subset_info['api_call']
        post_return, error = self.rest_api.post(api, None)
        if error:
            return None
        dummy, error = self.rest_api.wait_on_job(post_return['job'], increment=5)
        if error:
            self.module.fail_json(msg="%s" % error)

    def get_next_records(self, api):
        """
            Gather next set of ONTAP information for the specified api
            Input for REST APIs call : (api, data)
            return gather_subset_info
        """

        data = {}
        gather_subset_info, error = self.rest_api.get(api, data)

        if error:
            self.module.fail_json(msg=error)

        return gather_subset_info

    def convert_subsets(self):
        """
        Convert an info to the REST API
        """
        info_to_rest_mapping = {
            "aggregate_info": "storage/aggregates",
            "application_info": "application/applications",
            "application_template_info": "application/templates",
            "autosupport_config_info": "support/autosupport",
            "autosupport_messages_history": "support/autosupport/messages",
            "broadcast_domains_info": "network/ethernet/broadcast-domains",
            "cifs_home_directory_info": "protocols/cifs/home-directory/search-paths",
            "cifs_services_info": "protocols/cifs/services",
            "cifs_share_info": "protocols/cifs/shares",
            "cloud_targets_info": "cloud/targets",
            "cluster_chassis_info": "cluster/chassis",
            "cluster_jobs_info": "cluster/jobs",
            "cluster_metrocluster_diagnostics": "cluster/metrocluster/diagnostics",
            "cluster_metrics_info": "cluster/metrics",
            "cluster_node_info": "cluster/nodes",
            "cluster_peer_info": "cluster/peers",
            "cluster_schedules": "cluster/schedules",
            "cluster_software_download": "cluster/software/download",
            "cluster_software_history": "cluster/software/history",
            "cluster_software_packages": "cluster/software/packages",
            "disk_info": "storage/disks",
            "event_notification_info": "support/ems/destinations",
            "event_notification_destination_info": "support/ems/destinations",
            "initiator_groups_info": "protocols/san/igroups",
            "ip_interfaces_info": "network/ip/interfaces",
            "ip_routes_info": "network/ip/routes",
            "ip_service_policies": "network/ip/service-policies",
            "network_ipspaces_info": "network/ipspaces",
            "network_ports_info": "network/ethernet/ports",
            "ontap_system_version": "cluster/software",
            "san_fc_logins_info": "network/fc/logins",
            "san_fc_wppn-aliases": "network/fc/wwpn-aliases",
            "san_fcp_services": "protocols/san/fcp/services",
            "san_iscsi_credentials": "protocols/san/iscsi/credentials",
            "san_iscsi_services": "protocols/san/iscsi/services",
            "san_lun_maps": "protocols/san/lun-maps",
            "security_login_info": "security/accounts",
            "security_login_rest_role_info": "security/roles",
            "storage_flexcaches_info": "storage/flexcache/flexcaches",
            "storage_flexcaches_origin_info": "storage/flexcache/origins",
            "storage_luns_info": "storage/luns",
            "storage_NVMe_namespaces": "storage/namespaces",
            "storage_ports_info": "storage/ports",
            "storage_qos_policies": "storage/qos/policies",
            "storage_qtrees_config": "storage/qtrees",
            "storage_quota_reports": "storage/quota/reports",
            "storage_quota_policy_rules": "storage/quota/rules",
            "storage_shelves_config": "storage/shelves",
            "storage_snapshot_policies": "storage/snapshot-policies",
            "support_ems_config": "support/ems",
            "support_ems_events": "support/ems/events",
            "support_ems_filters": "support/ems/filters",
            "svm_dns_config_info": "name-services/dns",
            "svm_ldap_config_info": "name-services/ldap",
            "svm_name_mapping_config_info": "name-services/name-mappings",
            "svm_nis_config_info": "name-services/nis",
            "svm_peers_info": "svm/peers",
            "svm_peer-permissions_info": "svm/peer-permissions",
            "vserver_info": "svm/svms",
            "volume_info": "storage/volumes"
        }
        # Add rest API names as there info version, also make sure we don't add a duplicate
        subsets = []
        for subset in self.parameters['gather_subset']:
            if subset in info_to_rest_mapping:
                if info_to_rest_mapping[subset] not in subsets:
                    subsets.append(info_to_rest_mapping[subset])
            else:
                if subset not in subsets:
                    subsets.append(subset)
        return subsets

    def apply(self):
        """
        Perform pre-checks, call functions and exit
        """

        result_message = dict()

        # Validating ONTAP version
        self.validate_ontap_version()

        # Defining gather_subset and appropriate api_call
        get_ontap_subset_info = {
            'application/applications': {
                'api_call': 'application/applications',
            },
            'application/templates': {
                'api_call': 'application/templates',
            },
            'cloud/targets': {
                'api_call': 'cloud/targets',
            },
            'cluster/chassis': {
                'api_call': 'cluster/chassis',
            },
            'cluster/jobs': {
                'api_call': 'cluster/jobs',
            },
            'cluster/metrocluster/diagnostics': {
                'api_call': 'cluster/metrocluster/diagnostics',
                'post': True
            },
            'cluster/metrics': {
                'api_call': 'cluster/metrics',
            },
            'cluster/nodes': {
                'api_call': 'cluster/nodes',
            },
            'cluster/peers': {
                'api_call': 'cluster/peers',
            },
            'cluster/schedules': {
                'api_call': 'cluster/schedules',
            },
            'cluster/software': {
                'api_call': 'cluster/software',
            },
            'cluster/software/download': {
                'api_call': 'cluster/software/download',
            },
            'cluster/software/history': {
                'api_call': 'cluster/software/history',
            },
            'cluster/software/packages': {
                'api_call': 'cluster/software/packages',
            },
            'name-services/dns': {
                'api_call': 'name-services/dns',
            },
            'name-services/ldap': {
                'api_call': 'name-services/ldap',
            },
            'name-services/name-mappings': {
                'api_call': 'name-services/name-mappings',
            },
            'name-services/nis': {
                'api_call': 'name-services/nis',
            },
            'network/ethernet/broadcast-domains': {
                'api_call': 'network/ethernet/broadcast-domains',
            },
            'network/ethernet/ports': {
                'api_call': 'network/ethernet/ports',
            },
            'network/fc/logins': {
                'api_call': 'network/fc/logins',
            },
            'network/fc/wwpn-aliases': {
                'api_call': 'network/fc/wwpn-aliases',
            },
            'network/ip/interfaces': {
                'api_call': 'network/ip/interfaces',
            },
            'network/ip/routes': {
                'api_call': 'network/ip/routes',
            },
            'network/ip/service-policies': {
                'api_call': 'network/ip/service-policies',
            },
            'network/ipspaces': {
                'api_call': 'network/ipspaces',
            },
            'protocols/cifs/home-directory/search-paths': {
                'api_call': 'protocols/cifs/home-directory/search-paths',
            },
            'protocols/cifs/services': {
                'api_call': 'protocols/cifs/services',
            },
            'protocols/cifs/shares': {
                'api_call': 'protocols/cifs/shares',
            },
            'protocols/san/fcp/services': {
                'api_call': 'protocols/san/fcp/services',
            },
            'protocols/san/igroups': {
                'api_call': 'protocols/san/igroups',
            },
            'protocols/san/iscsi/credentials': {
                'api_call': 'protocols/san/iscsi/credentials',
            },
            'protocols/san/iscsi/services': {
                'api_call': 'protocols/san/iscsi/services',
            },
            'protocols/san/lun-maps': {
                'api_call': 'protocols/san/lun-maps',
            },
            'security/accounts': {
                'api_call': 'security/accounts',
            },
            'security/roles': {
                'api_call': 'security/roles',
            },
            'storage/aggregates': {
                'api_call': 'storage/aggregates',
            },
            'storage/disks': {
                'api_call': 'storage/disks',
            },
            'storage/flexcache/flexcaches': {
                'api_call': 'storage/flexcache/flexcaches',
            },
            'storage/flexcache/origins': {
                'api_call': 'storage/flexcache/origins',
            },
            'storage/luns': {
                'api_call': 'storage/luns',
            },
            'storage/namespaces': {
                'api_call': 'storage/namespaces',
            },
            'storage/ports': {
                'api_call': 'storage/ports',
            },
            'storage/qos/policies': {
                'api_call': 'storage/qos/policies',
            },
            'storage/qtrees': {
                'api_call': 'storage/qtrees',
            },
            'storage/quota/reports': {
                'api_call': 'storage/quota/reports',
            },
            'storage/quota/rules': {
                'api_call': 'storage/quota/rules',
            },
            'storage/shelves': {
                'api_call': 'storage/shelves',
            },
            'storage/snapshot-policies': {
                'api_call': 'storage/snapshot-policies',
            },
            'storage/volumes': {
                'api_call': 'storage/volumes',
            },
            'support/autosupport': {
                'api_call': 'support/autosupport',
            },
            'support/autosupport/messages': {
                'api_call': 'support/autosupport/messages',
            },
            'support/ems': {
                'api_call': 'support/ems',
            },
            'support/ems/destinations': {
                'api_call': 'support/ems/destinations',
            },
            'support/ems/events': {
                'api_call': 'support/ems/events',
            },
            'support/ems/filters': {
                'api_call': 'support/ems/filters',
            },
            'svm/peers': {
                'api_call': 'svm/peers',
            },
            'svm/peer-permissions': {
                'api_call': 'svm/peer-permissions',
            },
            'svm/svms': {
                'api_call': 'svm/svms',
            }
        }

        if 'all' in self.parameters['gather_subset']:
            # If all in subset list, get the information of all subsets
            self.parameters['gather_subset'] = sorted(get_ontap_subset_info.keys())

        length_of_subsets = len(self.parameters['gather_subset'])

        if self.parameters.get('fields') is not None:
            # If multiple fields specified to return, convert list to string
            self.fields = ','.join(self.parameters.get('fields'))

            if self.fields != '*' and length_of_subsets > 1:
                # Restrict gather subsets to one subset if fields section is list_of_fields
                self.module.fail_json(msg="Error: fields: %s, only one subset will be allowed." % self.parameters.get('fields'))
        converted_subsets = self.convert_subsets()

        for subset in converted_subsets:
            try:
                # Verify whether the supported subset passed
                specified_subset = get_ontap_subset_info[subset]
            except KeyError:
                self.module.fail_json(msg="Specified subset %s is not found, supported subsets are %s" %
                                      (subset, list(get_ontap_subset_info.keys())))

            result_message[subset] = self.get_subset_info(specified_subset)

            if result_message[subset] is not None:
                if isinstance(result_message[subset], dict):
                    while result_message[subset]['_links'].get('next'):
                        # Get all the set of records if next link found in subset_info for the specified subset
                        next_api = result_message[subset]['_links']['next']['href']
                        gathered_subset_info = self.get_next_records(next_api.replace('/api', ''))

                        # Update the subset info for the specified subset
                        result_message[subset]['_links'] = gathered_subset_info['_links']
                        result_message[subset]['records'].extend(gathered_subset_info['records'])

                    # metrocluster doesn't have a records field, so we need to skip this
                    if result_message[subset].get('records') is not None:
                        # Getting total number of records
                        result_message[subset]['num_records'] = len(result_message[subset]['records'])

        results = {'changed': False}
        if self.parameters.get('state') is not None:
            results['state'] = self.parameters['state']
            results['warnings'] = "option 'state' is deprecated."
        self.module.exit_json(ontap_info=result_message, **results)


def main():
    """
    Main function
    """
    obj = NetAppONTAPGatherInfo()
    obj.apply()


if __name__ == '__main__':
    main()
