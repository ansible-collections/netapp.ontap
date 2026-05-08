""" Support functions for NetApp ansible modules
    Provides common processing for responses and errors from REST calls
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible_collections.netapp.ontap.plugins.module_utils import rest_generic

# Below method of checking ONTAP personality is not valid for vsadmin login
# def check_ontap_personality(rest_api):
#     api = "private/cli/debug/smdb/table/OntapPersonality" if rest_api.meets_rest_minimum_version(True, 9, 17, 1) \
#           else "private/cli/debug/smdb/table/OntapMode"
#     response, error = rest_generic.get_one_record(rest_api, api)
#     return response, error


# def is_asa_r2_system(rest_api, module):
#     """ Checks if the given host is ASA r2 system """
#     record, error = check_ontap_personality(rest_api)
#     if error:
#         module.fail_json(msg='Failed while checking if the given host is an ASA r2 system or not')
#     return record.get("ASA_R2") or record.get('ASA_NEXT')


def check_ontap_personality(rest_api):
    api = "cluster"
    fields = "san_optimized,disaggregated"
    response, error = rest_generic.get_one_record(rest_api, api, fields=fields)
    return response, error


def is_asa_r2_system(rest_api, module):
    """ Checks if the given host is ASA r2 system """
    record, error = check_ontap_personality(rest_api)
    if error:
        module.fail_json(msg='Failed while checking if the given host is an ASA r2 system or not')

    # If both san_optimized and disaggregated are true, the system is ASA r2.
    # If san_optimized is false but disaggregated is true, the system is AFX (aka OAM)
    # If disaggregated is false and san_optimized is true, the system is the original ASA.
    # If disaggregated is false, the system is Unified ONTAP.
    return record.get("san_optimized") and record.get("disaggregated")
