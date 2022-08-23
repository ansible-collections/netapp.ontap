# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for ONTAP Ansible module: na_ontap_cluster_ha '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest
import sys
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import patch_ansible,\
    create_module, create_and_apply, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import patch_request_and_invoke,\
    register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_cluster_ha \
    import NetAppOntapClusterHA as cluster_ha  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not be available')

DEFAULT_ARGS = {
    'hostname': '10.10.10.10',
    'username': 'user',
    'password': 'pass',
    'state': 'present',
    'use_rest': 'never'
}

cluster_ha_enabled = {
    'attributes': {
        'cluster-ha-info': {'ha-configured': 'true'}
    }
}

cluster_ha_disabled = {
    'attributes': {
        'cluster-ha-info': {'ha-configured': 'false'}
    }
}


ZRR = zapi_responses({
    'cluster_ha_enabled': build_zapi_response(cluster_ha_enabled),
    'cluster_ha_disabled': build_zapi_response(cluster_ha_disabled)
})


SRR = rest_responses({
    'cluster_ha_enabled': (200, {"records": [{
        'configured': True
    }], "num_records": 1}, None),
    'cluster_ha_disabled': (200, {"records": [{
        'configured': False
    }], "num_records": 1}, None)
})


def test_module_fail_when_required_args_missing():
    ''' required arguments are reported as errors '''
    # with python 2.6, dictionaries are not ordered
    fragments = ["missing required arguments:", "hostname"]
    error = create_module(cluster_ha, {}, fail=True)['msg']
    for fragment in fragments:
        assert fragment in error


def test_enable_cluster_ha():
    ''' enable cluster ha '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('cluster-ha-get', ZRR['cluster_ha_disabled']),
        ('cluster-ha-modify', ZRR['success']),
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('cluster-ha-get', ZRR['cluster_ha_enabled'])
    ])
    assert create_and_apply(cluster_ha, DEFAULT_ARGS)['changed']
    assert not create_and_apply(cluster_ha, DEFAULT_ARGS)['changed']


def test_disable_cluster_ha():
    ''' disable cluster ha '''
    register_responses([
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('cluster-ha-get', ZRR['cluster_ha_enabled']),
        ('cluster-ha-modify', ZRR['success']),
        ('vserver-get-iter', ZRR['empty']),
        ('ems-autosupport-log', ZRR['empty']),
        ('cluster-ha-get', ZRR['cluster_ha_disabled']),
    ])
    assert create_and_apply(cluster_ha, DEFAULT_ARGS, {'state': 'absent'})['changed']
    assert not create_and_apply(cluster_ha, DEFAULT_ARGS, {'state': 'absent'})['changed']


def test_if_all_methods_catch_exception():
    register_responses([
        ('cluster-ha-get', ZRR['error']),
        ('cluster-ha-modify', ZRR['error']),
        ('cluster-ha-modify', ZRR['error']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'private/cli/cluster/ha', SRR['generic_error']),
        ('PATCH', 'private/cli/cluster/ha', SRR['generic_error']),
        ('PATCH', 'private/cli/cluster/ha', SRR['generic_error'])
    ])
    ha_obj = create_module(cluster_ha, DEFAULT_ARGS)
    assert 'Error fetching cluster HA' in expect_and_capture_ansible_exception(ha_obj.get_cluster_ha_enabled, 'fail')['msg']
    assert 'Error modifying cluster HA to true' in expect_and_capture_ansible_exception(ha_obj.modify_cluster_ha, 'fail', 'true')['msg']
    assert 'Error modifying cluster HA to false' in expect_and_capture_ansible_exception(ha_obj.modify_cluster_ha, 'fail', 'false')['msg']

    ucm_obj = create_module(cluster_ha, DEFAULT_ARGS, {'use_rest': 'always'})
    assert 'Error fetching cluster HA' in expect_and_capture_ansible_exception(ucm_obj.get_cluster_ha_enabled, 'fail')['msg']
    assert 'Error modifying cluster HA to true' in expect_and_capture_ansible_exception(ucm_obj.modify_cluster_ha, 'fail', 'true')['msg']
    assert 'Error modifying cluster HA to false' in expect_and_capture_ansible_exception(ucm_obj.modify_cluster_ha, 'fail', 'false')['msg']


def test_enable_cluster_ha_rest():
    ''' enable cluster ha in rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'private/cli/cluster/ha', SRR['cluster_ha_disabled']),
        ('PATCH', 'private/cli/cluster/ha', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'private/cli/cluster/ha', SRR['cluster_ha_enabled'])
    ])
    assert create_and_apply(cluster_ha, DEFAULT_ARGS, {'use_rest': 'always'})['changed']
    assert not create_and_apply(cluster_ha, DEFAULT_ARGS, {'use_rest': 'always'})['changed']


def test_disable_cluster_ha_rest():
    ''' disable cluster ha in rest '''
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'private/cli/cluster/ha', SRR['cluster_ha_enabled']),
        ('PATCH', 'private/cli/cluster/ha', SRR['success']),
        ('GET', 'cluster', SRR['is_rest_9_9_0']),
        ('GET', 'private/cli/cluster/ha', SRR['cluster_ha_disabled']),
    ])
    args = {'use_rest': 'always', 'state': 'absent'}
    assert create_and_apply(cluster_ha, DEFAULT_ARGS, args)['changed']
    assert not create_and_apply(cluster_ha, DEFAULT_ARGS, args)['changed']
