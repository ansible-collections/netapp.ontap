# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_firmware_upgrade '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible.module_utils import basic
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade\
    import NetAppONTAPFirmwareUpgrade as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def mock_warn(me, log):
    print('WARNING', log)


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None, parm1=None, parm2=None, parm3=None):
        ''' save arguments '''
        self.type = kind
        self.parm1 = parm1
        self.parm2 = parm2
        # self.parm3 = parm3
        self.xml_in = None
        self.xml_out = None
        self.firmware_type = 'None'

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        print('xml_in', xml.to_string())
        print('kind', self.type)
        if self.type == 'firmware_upgrade':
            xml = self.build_firmware_upgrade_info(self.parm1, self.parm2)
        if self.type == 'acp':
            xml = self.build_acp_firmware_info(self.firmware_type)
        if self.type == 'disk_fw_info':
            xml = self.build_disk_firmware_info(self.firmware_type)
        if self.type == 'shelf_fw_info':
            xml = self.build_shelf_firmware_info(self.firmware_type)
        if self.type == 'firmware_download':
            xml = self.build_system_cli_info(error=self.parm1)
        if self.type == 'exception':
            raise netapp_utils.zapi.NaApiError(self.parm1, self.parm2)
        self.xml_out = xml
        print('xml_out', xml.to_string())
        return xml

    @staticmethod
    def build_firmware_upgrade_info(version, node):
        ''' build xml data for service-processor firmware info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'num-records': 1,
            'attributes-list': {'service-processor-info': {'firmware-version': '3.4'}}
        }
        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_acp_firmware_info(firmware_type):
        ''' build xml data for acp firmware info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            # 'num-records': 1,
            'attributes-list': {'storage-shelf-acp-module': {'state': 'firmware_update_required'}}
        }
        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_disk_firmware_info(firmware_type):
        ''' build xml data for disk firmware info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'num-records': 1,
            'attributes-list': [{'storage-disk-info': {'disk-uid': '1', 'disk-inventory-info': {'firmware-revision': '1.2.3'}}}]
        }
        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_shelf_firmware_info(firmware_type):
        ''' build xml data for shelf firmware info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'num-records': 1,
            'attributes-list': [{'storage-shelf-info': {'shelf-modules': {'storage-shelf-module-info': {'module-id': '1', 'module-fw-revision': '1.2.3'}}}}]
        }
        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_system_cli_info(error=None):
        ''' build xml data for system-cli info '''
        if error is None:
            # make it a string, to be able to compare easily
            error = ""
        xml = netapp_utils.zapi.NaElement('results')
        output = "" if error == 'empty_output' else 'Download complete.'
        data = {
            'cli-output': output,
            'cli-result-value': 1
        }
        xml.translate_struct(data)
        status = "failed" if error == 'status_failed' else "passed"
        if error != 'no_status_attr':
            xml.add_attr('status', status)
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.server = MockONTAPConnection()
        self.use_vsim = False

    def set_default_args(self):
        if self.use_vsim:
            hostname = '10.10.10.10'
            username = 'admin'
            password = 'admin'
            node = 'vsim1'
        else:
            hostname = 'hostname'
            username = 'username'
            password = 'password'
            node = 'abc'
        package = 'test1.zip'
        force_disruptive_update = False
        clear_logs = True
        install_baseline_image = False
        update_type = 'serial_full'
        use_rest = 'never'
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'node': node,
            'package': package,
            'clear_logs': clear_logs,
            'install_baseline_image': install_baseline_image,
            'update_type': update_type,
            'https': 'true',
            'force_disruptive_update': force_disruptive_update,
            'use_rest': use_rest,
            'feature_flags': {'trace_apis': True}
        })

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_ensure_sp_firmware_get_called(self):
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'service-processor'
        set_module_args(module_args)
        my_obj = my_module()
        my_obj.server = self.server
        firmware_image_get = my_obj.firmware_image_get('node')
        print('Info: test_firmware_upgrade_get: %s' % repr(firmware_image_get))
        assert firmware_image_get is None

    def test_negative_package_and_baseline_present(self):
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'service-processor'
        module_args['package'] = 'test1.zip'
        module_args['install_baseline_image'] = True
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args(module_args)
            my_module()
        msg = 'With ZAPI and firmware_type set to service-processor: do not specify both package and install_baseline_image: true.'
        print('info: ' + exc.value.args[0]['msg'])
        assert exc.value.args[0]['msg'] == msg

    def test_negative_package_and_baseline_absent(self):
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'service-processor'
        module_args.pop('package')
        module_args['install_baseline_image'] = False
        module_args['force_disruptive_update'] = True
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args(module_args)
            my_module()
        msg = 'With ZAPI and firmware_type set to service-processor: specify at least one of package or install_baseline_image: true.'
        print('info: ' + exc.value.args[0]['msg'])
        assert exc.value.args[0]['msg'] == msg

    def test_ensure_acp_firmware_update_required_called(self):
        ''' a test tp verify acp firmware upgrade is required or not  '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'acp'
        set_module_args(module_args)
        my_obj = my_module()
        # my_obj.server = self.server
        my_obj.server = MockONTAPConnection(kind='acp')
        acp_firmware_update_required = my_obj.acp_firmware_update_required()
        print('Info: test_acp_firmware_upgrade_required_get: %s' % repr(acp_firmware_update_required))
        assert acp_firmware_update_required is True

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.sp_firmware_image_update')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.sp_firmware_image_update_progress_get')
    def test_ensure_apply_for_firmware_upgrade_called(self, get_mock, upgrade_mock, ems_log):
        ''' updgrading firmware and checking idempotency '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['package'] = 'test1.zip'
        module_args['firmware_type'] = 'service-processor'
        module_args['force_disruptive_update'] = True
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_firmware_upgrade_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('firmware_upgrade', '3.5', 'true')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_firmware_upgrade_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        upgrade_mock.assert_called_with()

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.shelf_firmware_upgrade')
    def test_shelf_firmware_upgrade(self, upgrade_mock, ems_log):
        ''' Test shelf firmware upgrade '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'shelf'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_firmware_upgrade_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        assert not upgrade_mock.called

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.shelf_firmware_upgrade')
    def test_shelf_firmware_upgrade_force(self, upgrade_mock, ems_log):
        ''' Test shelf firmware upgrade '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'shelf'
        module_args['force_disruptive_update'] = True
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = self.server
        upgrade_mock.return_value = True
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_firmware_upgrade_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        assert upgrade_mock.called

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.shelf_firmware_upgrade')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.shelf_firmware_update_required')
    def test_shelf_firmware_upgrade_force_update_required(self, update_required_mock, upgrade_mock, ems_log):
        ''' Test shelf firmware upgrade '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'shelf'
        module_args['force_disruptive_update'] = True
        module_args['shelf_module_fw'] = "version"
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = self.server
        update_required_mock.return_value = True
        upgrade_mock.return_value = True
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_firmware_upgrade_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        assert upgrade_mock.called

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.acp_firmware_upgrade')
    def test_acp_firmware_upgrade(self, upgrade_mock, ems_log):
        ''' Test ACP firmware upgrade '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'acp'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_firmware_upgrade_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        assert not upgrade_mock.called

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.acp_firmware_upgrade')
    def test_acp_firmware_upgrade_force(self, upgrade_mock, ems_log):
        ''' Test ACP firmware upgrade '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'acp'
        module_args['force_disruptive_update'] = True
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection(kind='acp')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_firmware_upgrade_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        assert upgrade_mock.called

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.disk_firmware_upgrade')
    def test_disk_firmware_upgrade(self, upgrade_mock, ems_log):
        ''' Test disk firmware upgrade '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'disk'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_firmware_upgrade_apply: %s' % repr(exc.value))
        assert not exc.value.args[0]['changed']
        assert not upgrade_mock.called

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.disk_firmware_upgrade')
    def test_disk_firmware_upgrade_force(self, upgrade_mock, ems_log):
        ''' Test disk firmware upgrade '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'disk'
        module_args['force_disruptive_update'] = True
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = self.server
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_firmware_upgrade_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        assert upgrade_mock.called

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.disk_firmware_upgrade')
    @patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_firmware_upgrade.NetAppONTAPFirmwareUpgrade.disk_firmware_update_required')
    def test_disk_firmware_upgrade_force_update_required(self, update_required_mock, upgrade_mock, ems_log):
        ''' Test disk firmware upgrade '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['firmware_type'] = 'disk'
        module_args['force_disruptive_update'] = True
        module_args['disk_fw'] = "version"
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = self.server
        update_required_mock.return_value = True
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Info: test_firmware_upgrade_apply: %s' % repr(exc.value))
        assert exc.value.args[0]['changed']
        assert upgrade_mock.called

    def test_acp_firmware_update_required(self):
        ''' Test acp_firmware_update_required '''
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('acp')
        result = my_obj.acp_firmware_update_required()
        assert result

    def test_acp_firmware_update_required_false(self):
        ''' Test acp_firmware_update_required '''
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection()
        result = my_obj.acp_firmware_update_required()
        assert not result

    def test_negative_acp_firmware_update_required(self):
        ''' Test acp_firmware_update_required '''
        module_args = {}
        module_args.update(self.set_default_args())
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('exception')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.acp_firmware_update_required()
        msg = "Error fetching acp firmware details details: NetApp API failed. Reason - None:None"
        assert msg in exc.value.args[0]['msg']

    def test_disk_firmware_update_required(self):
        ''' Test disk_firmware_update_required '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['disk_fw'] = '1.2.4'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('disk_fw_info')
        result = my_obj.disk_firmware_update_required()
        assert result

    def test_negative_disk_firmware_update_required(self):
        ''' Test disk_firmware_update_required '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['disk_fw'] = '1.2.4'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('exception')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.disk_firmware_update_required()
        msg = "Error fetching disk module firmware  details: NetApp API failed. Reason - None:None"
        assert msg in exc.value.args[0]['msg']

    def test_shelf_firmware_update_required(self):
        ''' Test shelf_firmware_update_required '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['shelf_module_fw'] = '1.2.4'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('shelf_fw_info')
        result = my_obj.shelf_firmware_update_required()
        assert result

    def test_negative_shelf_firmware_update_required(self):
        ''' Test shelf_firmware_update_required '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['shelf_module_fw'] = '1.2.4'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('exception')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.shelf_firmware_update_required()
        msg = "Error fetching shelf module firmware  details: NetApp API failed. Reason - None:None"
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_firmware_download(self, ems_log):
        ''' Test firmware download '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['package_url'] = 'dummy_url'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('firmware_download')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        msg = "Firmware download completed.  Extra info: Download complete."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_60(self, mock_ems_log):
        ''' Test firmware download '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['package_url'] = 'dummy_url'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('exception', 60, 'ZAPI timeout')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        msg = "Firmware download completed, slowly."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_firmware_download_502(self, mock_ems_log):
        ''' Test firmware download '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['package_url'] = 'dummy_url'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('exception', 502, 'Bad GW')
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        assert exc.value.args[0]['changed']
        msg = "Firmware download still in progress."
        assert exc.value.args[0]['msg'] == msg

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_firmware_download_502_as_error(self, mock_ems_log):
        ''' Test firmware download '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['package_url'] = 'dummy_url'
        module_args['fail_on_502_error'] = True
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('exception', 502, 'Bad GW')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = "NetApp API failed. Reason - 502:Bad GW"
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_firmware_download_no_num_error(self, mock_ems_log):
        ''' Test firmware download '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['package_url'] = 'dummy_url'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('exception', 'some error string', 'whatever')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = "NetApp API failed. Reason - some error string:whatever"
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_firmware_download_no_status_attr(self, ems_log):
        ''' Test firmware download '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['package_url'] = 'dummy_url'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('firmware_download', 'no_status_attr')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = "unable to download package from dummy_url: 'status' attribute missing."
        assert exc.value.args[0]['msg'].startswith(msg)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_firmware_download_status_failed(self, ems_log):
        ''' Test firmware download '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['package_url'] = 'dummy_url'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('firmware_download', 'status_failed')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = "unable to download package from dummy_url: check 'status' value."
        assert exc.value.args[0]['msg'].startswith(msg)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.ems_log_event_cserver')
    def test_firmware_download_empty_output(self, ems_log):
        ''' Test firmware download '''
        module_args = {}
        module_args.update(self.set_default_args())
        module_args['package_url'] = 'dummy_url'
        set_module_args(module_args)
        my_obj = my_module()
        if not self.use_vsim:
            my_obj.server = MockONTAPConnection('firmware_download', 'empty_output')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.apply()
        msg = "unable to download package from dummy_url: check console permissions."
        assert exc.value.args[0]['msg'].startswith(msg)


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, {'num_records': 0}, None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    # module specific responses
    'uuid_record': (200,
                    {'records': [{"uuid": '1cd8a442-86d1-11e0-ae1c-123478563412'}]}, None),
    'nodes_record': (200,
                     {'records': [{"name": 'node1'}, {"name": 'node2'}]}, None),
    'net_routes_record': (200,
                          {'records': [{"destination": {"address": "176.0.0.0",
                                                        "netmask": "24",
                                                        "family": "ipv4"},
                                        "gateway": '10.193.72.1',
                                        "uuid": '1cd8a442-86d1-11e0-ae1c-123478563412',
                                        "svm": {"name": "test_vserver"}}]}, None),
    'modified_record': (200,
                        {'records': [{"destination": {"address": "0.0.0.0",
                                                      "netmask": "0",
                                                      "family": "ipv4"},
                                      "gateway": "10.193.72.1",
                                      "uuid": '1cd8a442-86d1-11e0-ae1c-123478563412',
                                      "svm": {"name": "test_vserver"}}]}, None),
    'sp_state_online': (200,
                        {'service_processor': {'state': 'online'}}, None),
    'sp_state_rebooting': (200,
                           {'service_processor': {'state': 'rebooting'}}, None),
    'unexpected_arg': (400, None, 'Unexpected argument "service_processor.action"'),
}


def set_default_module_args(use_rest='always'):
    hostname = 'hostname'
    username = 'username'
    password = 'password'
    use_rest = 'always'
    return dict({
        'hostname': hostname,
        'username': username,
        'password': password,
        'https': 'true',
        'use_rest': use_rest,
        'package_url': 'https://download.site.com'
    })


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successfully_download(mock_request, patch_ansible):
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['reboot_sp'] = False
    set_module_args(data)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_good'],          # post download
        SRR['is_rest'],
        SRR['empty_good'],          # post download
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleExitJson) as exc:
        my_module().apply()
    assert exc.value.args[0]['changed']
    print(mock_request.call_args)
    json = {'url': 'https://download.site.com'}
    expected = call('POST', 'cluster/software/download', None, json=json, headers=None, files=None)
    assert mock_request.call_args == expected
    data['server_username'] = 'user'
    data['server_password'] = 'pass'
    set_module_args(data)
    with pytest.raises(AnsibleExitJson) as exc:
        my_module().apply()
    print(mock_request.call_args)
    json = {'url': 'https://download.site.com', 'username': 'user', 'password': 'pass'}
    expected = call('POST', 'cluster/software/download', None, json=json, headers=None, files=None)
    assert mock_request.call_args == expected


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_download(mock_request, patch_ansible):
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['reboot_sp'] = False
    set_module_args(data)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],       # post download
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_module().apply()
    msg = 'Error downloading software: calling: cluster/software/download: got Expected error.'
    assert msg in exc.value.args[0]['msg']


@patch('time.sleep')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successfully_reboot_sp_and_download(mock_request, dont_sleep, patch_ansible):
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['reboot_sp'] = True
    data['node'] = 'node4'
    data['firmware_type'] = 'service-processor'
    set_module_args(data)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['uuid_record'],         # get UUID
        SRR['empty_good'],          # patch reboot
        SRR['empty_good'],          # post download
        SRR['sp_state_rebooting'],  # get sp state
        SRR['sp_state_rebooting'],  # get sp state
        SRR['sp_state_online'],     # get sp state
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleExitJson) as exc:
        my_module().apply()
    assert exc.value.args[0]['changed']


@patch('time.sleep')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_reboot_sp_and_download_bad_sp(mock_request, dont_sleep, patch_ansible):
    """fail to read SP state"""
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['reboot_sp'] = True
    data['node'] = 'node4'
    data['firmware_type'] = 'service-processor'
    set_module_args(data)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['uuid_record'],         # get UUID
        SRR['empty_good'],          # patch reboot
        SRR['empty_good'],          # post download
        SRR['sp_state_rebooting'],  # get sp state
        SRR['sp_state_rebooting'],  # get sp state
        SRR['generic_error'],     # get sp state
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_module().apply()
    msg = 'Error getting node SP state:'
    assert msg in exc.value.args[0]['msg']


@patch('time.sleep')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_reboot_sp_and_download_sp_timeout(mock_request, dont_sleep, patch_ansible):
    """fail to read SP state"""
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['reboot_sp'] = True
    data['node'] = 'node4'
    data['firmware_type'] = 'service-processor'
    set_module_args(data)
    responses = [
        SRR['is_rest'],
        SRR['uuid_record'],         # get UUID
        SRR['empty_good'],          # patch reboot
        SRR['empty_good'],          # post download
    ]
    # 20 retries
    responses.extend([SRR['sp_state_rebooting']] * 20)
    responses.append(SRR['sp_state_online'])
    responses.append(SRR['end_of_sequence'])
    mock_request.side_effect = responses
    with pytest.raises(AnsibleExitJson) as exc:
        my_module().apply()
    # msg = 'Error getting node SP state:'
    # assert msg in exc.value.args[0]['msg']
    print('RETRIES', exc.value.args[0])


@patch('time.sleep')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_successfully_reboot_sp_and_download_cli(mock_request, dont_sleep, patch_ansible):
    ''' switch back to REST CLI for reboot '''
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['reboot_sp'] = True
    data['node'] = 'node4'
    data['firmware_type'] = 'service-processor'
    set_module_args(data)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['uuid_record'],         # get UUID
        SRR['unexpected_arg'],      # patch reboot
        SRR['empty_good'],          # REST CLI reboot
        SRR['empty_good'],          # post download
        SRR['sp_state_rebooting'],  # get sp state
        SRR['sp_state_rebooting'],  # get sp state
        SRR['sp_state_online'],     # get sp state
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleExitJson) as exc:
        my_module().apply()
    assert exc.value.args[0]['changed']


@patch('time.sleep')
@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_reboot_sp_and_download_cli(mock_request, dont_sleep, patch_ansible):
    ''' switch back to REST CLI for reboot '''
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['reboot_sp'] = True
    data['node'] = 'node4'
    data['firmware_type'] = 'service-processor'
    set_module_args(data)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['uuid_record'],         # get UUID
        SRR['unexpected_arg'],      # patch reboot
        SRR['generic_error'],       # REST CLI reboot
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_module().apply()
    msg = 'Error rebooting node SP: reboot_sp requires ONTAP 9.10.1 or newer, falling back to CLI passthrough failed'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_reboot_sp_and_download_uuid_error(mock_request, patch_ansible):
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['reboot_sp'] = True
    data['node'] = 'node4'
    data['firmware_type'] = 'service-processor'
    set_module_args(data)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['generic_error'],       # get UUID
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_module().apply()
    msg = 'Error reading node UUID: calling: cluster/nodes: got Expected error.'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_reboot_sp_and_download_node_not_found(mock_request, patch_ansible):
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['reboot_sp'] = True
    data['node'] = 'node4'
    data['firmware_type'] = 'service-processor'
    set_module_args(data)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],         # get UUID
        SRR['nodes_record'],        # get nodes
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_module().apply()
    msg = 'Error: node not found node4, current nodes: node1, node2.'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_reboot_sp_and_download_nodes_get_error(mock_request, patch_ansible):
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['reboot_sp'] = True
    data['node'] = 'node4'
    data['firmware_type'] = 'service-processor'
    set_module_args(data)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],         # get UUID
        SRR['generic_error'],       # get nodes
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_module().apply()
    msg = 'Error reading nodes: calling: cluster/nodes: got Expected error.'
    assert msg in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_negative_unsupported_option_with_rest(mock_request, patch_ansible):
    data = set_default_module_args(use_rest='always')
    data['state'] = 'present'
    data['clear_logs'] = False
    data['node'] = 'node4'
    set_module_args(data)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['end_of_sequence']
    ]
    with pytest.raises(AnsibleFailJson) as exc:
        my_module().apply()
    msg = "REST API currently does not support 'clear_logs'"
    assert msg in exc.value.args[0]['msg']
