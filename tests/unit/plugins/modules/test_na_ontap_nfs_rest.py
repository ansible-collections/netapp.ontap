# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_nfs \
    import NetAppONTAPNFS as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

# REST API canned responses when mocking send_request.
# The rest_factory provides default responses shared across testcases.
SRR = rest_responses({
    # module specific responses
    'one_record': (200, {"records": [
        {
            "svm": {
                "uuid": "671aa46e-11ad-11ec-a267-005056b30cfa",
                "name": "ansibleSVM"
            },
            "transport": {
                "udp_enabled": True,
                "tcp_enabled": True
            },
            "protocol": {
                "v3_enabled": True,
                "v4_id_domain": "carchi8py.com",
                "v40_enabled": False,
                "v41_enabled": False,
                "v40_features": {
                    "acl_enabled": False,
                    "read_delegation_enabled": False,
                    "write_delegation_enabled": False
                },
                "v41_features": {
                    "acl_enabled": False,
                    "read_delegation_enabled": False,
                    "write_delegation_enabled": False,
                    "pnfs_enabled": False
                }
            },
            "vstorage_enabled": False,
            "showmount_enabled": True
        }
    ]}, None),
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'vserver': 'ansibleSVM',
    'use_rest': 'always',
}


def set_default_args():
    return dict({
        'hostname': 'hostname',
        'username': 'username',
        'password': 'password',
        'vserver': 'ansibleSVM',
        'use_rest': 'always',
    })


def test_get_nfs_rest_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/nfs/services', SRR['empty_records'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    assert my_obj.get_nfs_service_rest() is None


def test_partially_supported_rest():
    register_responses([('GET', 'cluster', SRR['is_rest_96'])])
    module_args = set_default_args()
    module_args['showmount'] = 'enabled'
    set_module_args(module_args)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = "Error: Minimum version of ONTAP for showmount is (9, 8)."
    assert msg in exc.value.args[0]['msg']


def test_get_nfs_rest_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/nfs/services', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error getting nfs services for SVM ansibleSVM: calling: protocols/nfs/services: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_nfs_service_rest, 'fail')['msg']


def test_get_nfs_rest_one_record():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/nfs/services', SRR['one_record'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    assert my_obj.get_nfs_service_rest() is not None


def test_create_nfs():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/nfs/services', SRR['empty_records']),
        ('POST', 'protocols/nfs/services', SRR['empty_good'])
    ])
    assert create_and_apply(my_module, DEFAULT_ARGS, {})['changed']


def test_create_nfs_all_options():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'protocols/nfs/services', SRR['empty_good'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['nfsv3'] = True
    my_obj.parameters['nfsv4'] = False
    my_obj.parameters['nfsv41'] = False
    my_obj.parameters['nfsv41_pnfs'] = False
    my_obj.parameters['vstorage_state'] = False
    my_obj.parameters['nfsv4_id_domain'] = 'carchi8py.com'
    my_obj.parameters['tcp'] = True
    my_obj.parameters['udp'] = True
    my_obj.parameters['nfsv40_acl'] = False
    my_obj.parameters['nfsv40_read_delegation'] = False
    my_obj.parameters['nfsv40_write_delegation'] = False
    my_obj.parameters['nfsv41_acl'] = False
    my_obj.parameters['nfsv41_read_delegation'] = False
    my_obj.parameters['nfsv41_write_delegation'] = False
    my_obj.parameters['showmount'] = True
    my_obj.parameters['service_state'] = 'stopped'
    my_obj.create_nfs_service_rest()
    assert get_mock_record().is_record_in_json({'svm.name': 'ansibleSVM'}, 'POST', 'protocols/nfs/services')


def test_create_nfs_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('POST', 'protocols/nfs/services', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error creating nfs service for SVM ansibleSVM: calling: protocols/nfs/services: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.create_nfs_service_rest, 'fail')['msg']


def test_delete_nfs():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/nfs/services', SRR['one_record']),
        ('DELETE', 'protocols/nfs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good'])
    ])
    module_args = {
        'state': 'absent'
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_nfs_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('DELETE', 'protocols/nfs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['generic_error'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['state'] = 'absent'
    my_obj.svm_uuid = '671aa46e-11ad-11ec-a267-005056b30cfa'
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.delete_nfs_service_rest()
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = "Error deleting nfs service for SVM ansibleSVM"
    assert msg == exc.value.args[0]['msg']


def test_delete_nfs_no_uuid_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    module_args = {
        'state': 'absent'
    }
    my_module_object = create_module(my_module, DEFAULT_ARGS, module_args)
    msg = "Error deleting nfs service for SVM ansibleSVM: svm.uuid is None"
    assert msg in expect_and_capture_ansible_exception(my_module_object.delete_nfs_service_rest, 'fail')['msg']


def test_modify_nfs():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('GET', 'protocols/nfs/services', SRR['one_record']),
        ('PATCH', 'protocols/nfs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['empty_good'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['nfsv3'] = 'disabled'
    my_obj.svm_uuid = '671aa46e-11ad-11ec-a267-005056b30cfa'
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed']


def test_modify_nfs_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
        ('PATCH', 'protocols/nfs/services/671aa46e-11ad-11ec-a267-005056b30cfa', SRR['generic_error'])
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['nfsv3'] = 'disabled'
    my_obj.svm_uuid = '671aa46e-11ad-11ec-a267-005056b30cfa'
    modify = {'nfsv3': False}
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.modify_nfs_service_rest(modify)
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = "Error modifying nfs service for SVM ansibleSVM: calling: protocols/nfs/services/671aa46e-11ad-11ec-a267-005056b30cfa: got Expected error."
    assert msg == exc.value.args[0]['msg']


def test_modify_nfs_no_uuid_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest']),
    ])
    set_module_args(set_default_args())
    my_obj = my_module()
    my_obj.parameters['nfsv3'] = 'disabled'
    modify = {'nfsv3': False}
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.modify_nfs_service_rest(modify)
    print('Info: %s' % exc.value.args[0]['msg'])
    msg = "Error modifying nfs service for SVM ansibleSVM: svm.uuid is None"
    assert msg == exc.value.args[0]['msg']
