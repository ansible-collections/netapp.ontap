# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test template for ONTAP Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import copy
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_no_warnings, assert_no_warnings_except_zapi, assert_warning_was_raised, call_main, create_and_apply, print_warnings, set_module_args,\
    AnsibleExitJson, patch_ansible
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_response, zapi_responses
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_nfs \
    import NetAppONTAPNFS as nfs_module, main as my_main    # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


nfs_info = {
    "attributes-list": {
        "nfs-info": {
            "auth-sys-extended-groups": "false",
            "cached-cred-harvest-timeout": "86400000",
            "cached-cred-negative-ttl": "7200000",
            "cached-cred-positive-ttl": "86400000",
            "cached-transient-err-ttl": "30000",
            "chown-mode": "use_export_policy",
            "enable-ejukebox": "true",
            "extended-groups-limit": "32",
            "file-session-io-grouping-count": "5000",
            "file-session-io-grouping-duration": "120",
            "ignore-nt-acl-for-root": "false",
            "is-checksum-enabled-for-replay-cache": "true",
            "is-mount-rootonly-enabled": "true",
            "is-netgroup-dns-domain-search": "true",
            "is-nfs-access-enabled": "false",
            "is-nfs-rootonly-enabled": "false",
            "is-nfsv2-enabled": "false",
            "is-nfsv3-64bit-identifiers-enabled": "false",
            "is-nfsv3-connection-drop-enabled": "true",
            "is-nfsv3-enabled": "true",
            "is-nfsv3-fsid-change-enabled": "true",
            "is-nfsv4-fsid-change-enabled": "true",
            "is-nfsv4-numeric-ids-enabled": "true",
            "is-nfsv40-acl-enabled": "false",
            "is-nfsv40-enabled": "true",
            "is-nfsv40-migration-enabled": "false",
            "is-nfsv40-read-delegation-enabled": "false",
            "is-nfsv40-referrals-enabled": "false",
            "is-nfsv40-req-open-confirm-enabled": "false",
            "is-nfsv40-write-delegation-enabled": "false",
            "is-nfsv41-acl-enabled": "false",
            "is-nfsv41-acl-preserve-enabled": "true",
            "is-nfsv41-enabled": "true",
            "is-nfsv41-migration-enabled": "false",
            "is-nfsv41-pnfs-enabled": "true",
            "is-nfsv41-read-delegation-enabled": "false",
            "is-nfsv41-referrals-enabled": "false",
            "is-nfsv41-state-protection-enabled": "true",
            "is-nfsv41-write-delegation-enabled": "false",
            "is-qtree-export-enabled": "false",
            "is-rquota-enabled": "false",
            "is-tcp-enabled": "false",
            "is-udp-enabled": "false",
            "is-v3-ms-dos-client-enabled": "false",
            "is-validate-qtree-export-enabled": "true",
            "is-vstorage-enabled": "false",
            "map-unknown-uid-to-default-windows-user": "true",
            "mountd-port": "635",
            "name-service-lookup-protocol": "udp",
            "netgroup-trust-any-ns-switch-no-match": "false",
            "nfsv4-acl-max-aces": "400",
            "nfsv4-grace-seconds": "45",
            "nfsv4-id-domain": "defaultv4iddomain.com",
            "nfsv4-lease-seconds": "30",
            "nfsv41-implementation-id-domain": "netapp.com",
            "nfsv41-implementation-id-name": "NetApp Release Kalyaniblack__9.4.0",
            "nfsv41-implementation-id-time": "1541070767",
            "nfsv4x-session-num-slots": "180",
            "nfsv4x-session-slot-reply-cache-size": "640",
            "nlm-port": "4045",
            "nsm-port": "4046",
            "ntacl-display-permissive-perms": "false",
            "ntfs-unix-security-ops": "use_export_policy",
            "permitted-enc-types": {
                "string": ["des", "des3", "aes_128", "aes_256"]
            },
            "rpcsec-ctx-high": "0",
            "rpcsec-ctx-idle": "0",
            "rquotad-port": "4049",
            "showmount": "true",
            "showmount-timestamp": "1548372452",
            "skip-root-owner-write-perm-check": "false",
            "tcp-max-xfer-size": "1048576",
            "udp-max-xfer-size": "32768",
            "v3-search-unconverted-filename": "false",
            "v4-inherited-acl-preserve": "false",
            "vserver": "ansible"
        }
    },
    "num-records": "1"
}

nfs_info_no_tcp_max_xfer_size = copy.deepcopy(nfs_info)
del nfs_info_no_tcp_max_xfer_size['attributes-list']['nfs-info']['tcp-max-xfer-size']


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None, data=None, job_error=None):
        ''' save arguments '''
        self.kind = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.kind == 'nfs':
            xml = self.build_nfs_info(self.params)
        self.xml_out = xml
        if self.kind == 'nfs_status':
            xml = self.build_nfs_status_info(self.params)
        return xml

    @staticmethod
    def build_nfs_info(nfs_details):
        ''' build xml data for volume-attributes '''
        xml = netapp_utils.zapi.NaElement('xml')
        xml.translate_struct(nfs_info)
        return xml

    @staticmethod
    def build_nfs_status_info(nfs_status_details):
        ''' build xml data for volume-attributes '''
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'is-enabled': "true"
        }
        xml.translate_struct(attributes)
        return xml


DEFAULT_ARGS = {
    'vserver': 'nfs_vserver',
    'hostname': 'test',
    'username': 'test_user',
    'password': 'test_pass!',
    'https': 'false',
    'use_rest': 'never'
}


SRR = zapi_responses({
    'nfs_info': build_zapi_response(nfs_info),
    'nfs_info_no_tcp_max_xfer_size': build_zapi_response(nfs_info_no_tcp_max_xfer_size)
})


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_nfs_group = {
            'vserver': DEFAULT_ARGS['vserver'],
        }

    def mock_args(self):
        return dict(DEFAULT_ARGS)

    def get_nfs_mock_object(self, kind=None):
        """
        Helper method to return an na_ontap_volume object
        :param kind: passes this param to MockONTAPConnection()
        :return: na_ontap_volume object
        """
        nfsy_obj = nfs_module()
        nfsy_obj.asup_log_for_cserver = Mock(return_value=None)
        nfsy_obj.cluster = Mock()
        nfsy_obj.cluster.invoke_successfully = Mock()
        if kind is None:
            nfsy_obj.server = MockONTAPConnection()
        else:
            nfsy_obj.server = MockONTAPConnection(kind=kind, data=self.mock_nfs_group)
        return nfsy_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        error = 'missing required arguments'
        assert error in call_main(my_main, {}, fail=True)['msg']

    def test_get_nonexistent_nfs(self):
        ''' Test if get_nfs_service returns None for non-existent nfs '''
        set_module_args(self.mock_args())
        result = self.get_nfs_mock_object().get_nfs_service()
        assert result is None

    def test_get_existing_nfs(self):
        ''' Test if get_policy_group returns details for existing nfs '''
        set_module_args(self.mock_args())
        result = self.get_nfs_mock_object('nfs').get_nfs_service()
        assert result['nfsv3']

    def test_get_nonexistent_nfs_status(self):
        ''' Test if get__nfs_status returns None for non-existent nfs '''
        set_module_args(self.mock_args())
        result = self.get_nfs_mock_object().get_nfs_status()
        assert result is None

    def test_get_existing_nfs_status(self):
        ''' Test if get__nfs_status returns details for nfs '''
        set_module_args(self.mock_args())
        result = self.get_nfs_mock_object('nfs_status').get_nfs_status()
        assert result

    def test_modify_nfs(self):
        ''' Test if modify_nfs runs for existing nfs '''
        data = self.mock_args()
        current = {
            'nfsv3': 'enabled',
            'nfsv3_fsid_change': 'enabled',
            'nfsv4': 'enabled',
            'nfsv41': 'enabled',
            'vstorage_state': 'enabled',
            'tcp': 'enabled',
            'udp': 'enabled',
            'nfsv4_id_domain': 'nfsv4_id_domain',
            'nfsv40_acl': 'enabled',
            'nfsv40_read_delegation': 'enabled',
            'nfsv40_write_delegation': 'enabled',
            'nfsv41_acl': 'enabled',
            'nfsv41_read_delegation': 'enabled',
            'nfsv41_write_delegation': 'enabled',
            'showmount': 'enabled',
            'tcp_max_xfer_size': '1048576',
        }

        data.update(current)
        set_module_args(data)
        self.get_nfs_mock_object('nfs_status').modify_nfs_service(current)

    def test_successfully_modify_nfs(self):
        ''' Test modify nfs successful for modifying tcp max xfer size. '''
        data = self.mock_args()
        data['tcp_max_xfer_size'] = 8192
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_nfs_mock_object('nfs').apply()
        assert exc.value.args[0]['changed']

    def test_modify_nfs_idempotency(self):
        ''' Test modify nfs idempotency '''
        data = self.mock_args()
        data['tcp_max_xfer_size'] = '1048576'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_nfs_mock_object('nfs').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_nfs.NetAppONTAPNFS.delete_nfs_service')
    def test_successfully_delete_nfs(self, delete_nfs_service):
        ''' Test successfully delete nfs '''
        data = self.mock_args()
        data['state'] = 'absent'
        set_module_args(data)
        obj = self.get_nfs_mock_object('nfs')
        with pytest.raises(AnsibleExitJson) as exc:
            obj.apply()
        assert exc.value.args[0]['changed']
        delete_nfs_service.assert_called_with()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_nfs.NetAppONTAPNFS.get_nfs_service')
    def test_successfully_enable_nfs(self, get_nfs_service):
        ''' Test successfully enable nfs on non-existent nfs '''
        data = self.mock_args()
        data['state'] = 'present'
        set_module_args(data)
        get_nfs_service.side_effect = [
            None,
            {}
        ]
        obj = self.get_nfs_mock_object('nfs')
        with pytest.raises(AnsibleExitJson) as exc:
            obj.apply()
        assert exc.value.args[0]['changed']


def test_modify_tcp_max_xfer_size():
    ''' if ZAPI returned a None value, a modify is attempted '''
    register_responses([
        # ONTAP 9.4 and later, tcp_max_xfer_size is an INT
        ('ZAPI', 'ems-autosupport-log', SRR['success']),
        ('ZAPI', 'nfs-service-get-iter', SRR['nfs_info']),
        ('ZAPI', 'nfs-status', SRR['success']),
        ('ZAPI', 'nfs-service-modify', SRR['success']),
        # ONTAP 9.4 and later, tcp_max_xfer_size is an INT, idempotency
        ('ZAPI', 'ems-autosupport-log', SRR['success']),
        ('ZAPI', 'nfs-service-get-iter', SRR['nfs_info']),
        # ONTAP 9.3 and earlier, tcp_max_xfer_size is not set
        ('ZAPI', 'ems-autosupport-log', SRR['success']),
        ('ZAPI', 'nfs-service-get-iter', SRR['nfs_info_no_tcp_max_xfer_size']),
    ])
    module_args = {
        'tcp_max_xfer_size': 4500
    }
    assert create_and_apply(nfs_module, DEFAULT_ARGS, module_args)['changed']
    module_args = {
        'tcp_max_xfer_size': 1048576
    }
    assert not create_and_apply(nfs_module, DEFAULT_ARGS, module_args)['changed']
    error = 'Error: tcp_max_xfer_size is not supported on ONTAP 9.3 or earlier.'
    assert create_and_apply(nfs_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error
    assert_no_warnings_except_zapi()


def test_warning_on_nfsv41_alias():
    ''' if ZAPI returned a None value, a modify is attempted '''
    register_responses([
        # ONTAP 9.4 and later, tcp_max_xfer_size is an INT
        ('ZAPI', 'ems-autosupport-log', SRR['success']),
        ('ZAPI', 'nfs-service-get-iter', SRR['nfs_info']),
        ('ZAPI', 'nfs-status', SRR['success']),
        ('ZAPI', 'nfs-service-modify', SRR['success']),
    ])
    module_args = {
        'nfsv4.1': 'disabled'
    }
    assert call_main(my_main, DEFAULT_ARGS, module_args)['changed']
    print_warnings()
    assert_warning_was_raised('Error: "nfsv4.1" option conflicts with Ansible naming conventions - please use "nfsv41".')
