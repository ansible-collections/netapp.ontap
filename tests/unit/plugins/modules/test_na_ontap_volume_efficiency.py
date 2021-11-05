''' unit tests ONTAP Ansible module: na_ontap_volume_efficiency '''
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_efficiency \
    import NetAppOntapVolumeEfficiency as volume_efficiency_module, main  # module under test


if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')

# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_rest_9_10_0': (200, dict(version=dict(generation=9, major=10, minor=0, full='dummy_9_10_0')), None),
    'is_rest_9_10_1': (200, dict(version=dict(generation=9, major=10, minor=1, full='dummy_9_10_1')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {'num_records': 0}, None),
    'nonempty_good': (200, {'num_records': 1, 'cli_output': 'Efficiency for volume "volTest" of Vserver "vs1" is enabled.'}, None),
    'end_of_sequence': (500, None, "Ooops, the UT needs one more SRR response"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'volume_efficiency_enabled_record': (200, {
        'num_records': 1,
        'records': [{
            'path': '/vol/volTest',
            'state': 'enabled',
            'op_status': 'idle',
            'schedule': None,
            'policy': 'auto',
            'inline_compression': True,
            'compression': True,
            'inline_dedupe': True,
            'data_compaction': True,
            'cross_volume_inline_dedupe': True,
            'cross_volume_background_dedupe': True
        }]
    }, None),
    'volume_efficiency_disabled_record': (200, {
        'num_records': 1,
        'records': [{
            'path': '/vol/volTest',
            'state': 'disabled',
            'op_status': 'idle',
            'schedule': None,
            'policy': 'auto',
            'inline_compression': True,
            'compression': True,
            'inline_dedupe': True,
            'data_compaction': True,
            'cross_volume_inline_dedupe': True,
            'cross_volume_background_dedupe': True
        }]
    }, None),
    'volume_efficiency_running_record': (200, {
        'num_records': 1,
        'records': [{
            'path': '/vol/volTest',
            'state': 'enabled',
            'op_status': 'running',
            'schedule': None,
            'policy': 'auto',
            'inline_compression': True,
            'compression': True,
            'inline_dedupe': True,
            'data_compaction': True,
            'cross_volume_inline_dedupe': True,
            'cross_volume_background_dedupe': True
        }]
    }, None)
}


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""


def exit_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'volume_efficiency_enabled':
            xml = self.build_volume_efficiency_enabled_info()
        elif self.type == 'volume_efficiency_disabled':
            xml = self.build_volume_efficiency_disabled_info()
        elif self.type == 'volume_efficiency_running':
            xml = self.build_volume_efficiency_running_info()
        elif self.type == 'volume_efficiency_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_volume_efficiency_enabled_info():
        ''' build xml data for sis-status-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'num-records': 1,
            'attributes-list': {
                'sis-status-info': {
                    'path': '/vol/volTest',
                    'state': 'enabled',
                    'schedule': None,
                    'status': 'idle',
                    'policy': 'auto',
                    'is-inline-compression-enabled': 'true',
                    'is-compression-enabled': 'true',
                    'is-inline-dedupe-enabled': 'true',
                    'is-data-compaction-enabled': 'true',
                    'is-cross-volume-inline-dedupe-enabled': 'true',
                    'is-cross-volume-background-dedupe-enabled': 'true'
                }
            }
        }

        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_volume_efficiency_disabled_info():
        ''' build xml data for sis-status-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'num-records': 1,
            'attributes-list': {
                'sis-status-info': {
                    'path': '/vol/volTest',
                    'state': 'disabled',
                    'status': 'idle',
                    'schedule': None,
                    'policy': 'auto',
                    'is-inline-compression-enabled': 'true',
                    'is-compression-enabled': 'true',
                    'is-inline-dedupe-enabled': 'true',
                    'is-data-compaction-enabled': 'true',
                    'is-cross-volume-inline-dedupe-enabled': 'true',
                    'is-cross-volume-background-dedupe-enabled': 'true'
                }
            }
        }

        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_volume_efficiency_running_info():
        ''' build xml data for sis-status-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'num-records': 1,
            'attributes-list': {
                'sis-status-info': {
                    'path': '/vol/volTest',
                    'state': 'enabled',
                    'schedule': None,
                    'status': 'running',
                    'policy': 'auto',
                    'is-inline-compression-enabled': 'true',
                    'is-compression-enabled': 'true',
                    'is-inline-dedupe-enabled': 'true',
                    'is-data-compaction-enabled': 'true',
                    'is-cross-volume-inline-dedupe-enabled': 'true',
                    'is-cross-volume-background-dedupe-enabled': 'true'
                }
            }
        }

        xml.translate_struct(data)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.server = MockONTAPConnection()
        self.onbox = False

    def set_default_args(self, use_rest=None):
        if self.onbox:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'vs1'
            path = '/vol/volTest'
            policy = 'auto'
            enable_compression = True
            enable_inline_compression = True
            enable_cross_volume_inline_dedupe = True
            enable_inline_dedupe = True
            enable_data_compaction = True
            enable_cross_volume_background_dedupe = True
        else:
            hostname = '10.10.10.10'
            username = 'username'
            password = 'password'
            vserver = 'vs1'
            path = '/vol/volTest'
            policy = 'auto'
            enable_compression = True
            enable_inline_compression = True
            enable_cross_volume_inline_dedupe = True
            enable_inline_dedupe = True
            enable_data_compaction = True
            enable_cross_volume_background_dedupe = True

        args = dict({
            'state': 'present',
            'hostname': hostname,
            'username': username,
            'password': password,
            'vserver': vserver,
            'path': path,
            'policy': policy,
            'enable_compression': enable_compression,
            'enable_inline_compression': enable_inline_compression,
            'enable_cross_volume_inline_dedupe': enable_cross_volume_inline_dedupe,
            'enable_inline_dedupe': enable_inline_dedupe,
            'enable_data_compaction': enable_data_compaction,
            'enable_cross_volume_background_dedupe': enable_cross_volume_background_dedupe
        })

        if use_rest is not None:
            args['use_rest'] = use_rest

        return args

    @staticmethod
    def get_volume_efficiency_mock_object(cx_type='zapi', kind=None):
        volume_efficiency_obj = volume_efficiency_module()
        if cx_type == 'zapi':
            if kind is None:
                volume_efficiency_obj.server = MockONTAPConnection()
            else:
                volume_efficiency_obj.server = MockONTAPConnection(kind=kind)
        return volume_efficiency_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            volume_efficiency_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_get_called_existing(self):
        ''' test get_volume_efficiency for existing config '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = volume_efficiency_module()
        my_obj.server = MockONTAPConnection(kind='volume_efficiency_enabled')
        assert my_obj.get_volume_efficiency()

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_efficiency.NetAppOntapVolumeEfficiency.enable_volume_efficiency')
    def test_successful_enable(self, enable_volume_efficiency):
        ''' enable volume_efficiency and testing idempotency '''
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_disabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        enable_volume_efficiency.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(self.set_default_args(use_rest='Never'))
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_enabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_efficiency.NetAppOntapVolumeEfficiency.disable_volume_efficiency')
    def test_successful_disable(self, disable_volume_efficiency):
        ''' disable volume_efficiency and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['state'] = 'absent'
        set_module_args(data)
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_enabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # disable_volume_efficiency.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_disabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_efficiency.NetAppOntapVolumeEfficiency.modify_volume_efficiency')
    def test_successful_modify(self, modify_volume_efficiency):
        ''' modifying volume_efficiency config and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['policy'] = 'default'
        set_module_args(data)
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_enabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # modify_volume_efficiency.assert_called_with()
        # to reset na_helper from remembering the previous 'changed' value
        data['policy'] = 'auto'
        set_module_args(data)
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_enabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_efficiency.NetAppOntapVolumeEfficiency.start_volume_efficiency')
    def test_successful_start(self, start_volume_efficiency):
        ''' start volume_efficiency and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['volume_efficiency'] = 'start'
        set_module_args(data)
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_enabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(data)
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_running')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_volume_efficiency.NetAppOntapVolumeEfficiency.stop_volume_efficiency')
    def test_successful_stop(self, stop_volume_efficiency):
        ''' stop volume_efficiency and testing idempotency '''
        data = self.set_default_args(use_rest='Never')
        data['volume_efficiency'] = 'stop'
        set_module_args(data)
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_running')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        # to reset na_helper from remembering the previous 'changed' value
        set_module_args(data)
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_enabled')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert not exc.value.args[0]['changed']

    def test_if_all_methods_catch_exception(self):
        data = self.set_default_args(use_rest='Never')
        set_module_args(data)
        my_obj = volume_efficiency_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('volume_efficiency_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.enable_volume_efficiency()
        assert 'Error enabling storage efficiency' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.disable_volume_efficiency()
        assert 'Error disabling storage efficiency' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.modify_volume_efficiency()
        assert 'Error modifying storage efficiency' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_error(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        msg = 'calling: private/cli/volume/efficiency: got %s.' % SRR['generic_error'][2]
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_enable_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_disabled_record'],  # get
            SRR['nonempty_good'],  # patch
            SRR['empty_good'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_enable_rest(self, mock_request):
        data = self.set_default_args()
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_enabled_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_disable_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_enabled_record'],  # get
            SRR['empty_good'],  # disable
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_disable_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'absent'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_disabled_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['policy'] = 'default'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_enabled_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_modify_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_enabled_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_start_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['volume_efficiency'] = 'start'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_enabled_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_start_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_enabled_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_start_rest_all_options(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['volume_efficiency'] = 'start'
        data['start_ve_scan_all'] = True
        data['start_ve_build_metadata'] = True
        data['start_ve_delete_checkpoint'] = True
        data['start_ve_queue_operation'] = True
        data['start_ve_scan_old_data'] = True
        data['start_ve_qos_policy'] = 'background'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_enabled_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_start_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['volume_efficiency'] = 'start'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_enabled_record'],  # get
            SRR['generic_error'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        msg = 'Error in efficiency/start: Expected error'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_successful_stop_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['volume_efficiency'] = 'stop'
        data['stop_ve_all_operations'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_running_record'],  # get
            SRR['empty_good'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_idempotent_stop_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_enabled_record'],  # get
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        assert not exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_stop_rest(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['volume_efficiency'] = 'stop'
        data['stop_ve_all_operations'] = True
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['volume_efficiency_running_record'],  # get
            SRR['generic_error'],  # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        msg = 'Error in efficiency/stop: Expected error'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_modify_rest_se_mode_no_version(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['storage_efficiency_mode'] = 'default'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],     # is_rest
            SRR['is_rest'],     # fail_if_ calls version again!
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        msg = 'Error: option storage_efficiency_mode only supports REST, and requires ONTAP 9.10 or later.  Found: -1.-1.-1.'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_modify_rest_se_mode_version(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['storage_efficiency_mode'] = 'default'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_9_10_0'],  # is_rest
            SRR['is_rest_9_10_0'],  # fail_if_ calls version again!
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_volume_efficiency_mock_object(cx_type='rest').apply()
        msg = 'Error: option storage_efficiency_mode only supports REST, and requires ONTAP 9.10 or later.  Found: 9.10.0.'
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_modify_rest_se_mode(self, mock_request):
        data = self.set_default_args()
        data['state'] = 'present'
        data['storage_efficiency_mode'] = 'default'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest_9_10_1'],      # is_rest
            SRR['is_rest_9_10_1'],      # fail_if_ calls version again!
            SRR['empty_good'],          # get
            SRR['nonempty_good'],       # enable
            SRR['empty_good'],          # patch
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            main()
        assert exc.value.args[0]['changed']
