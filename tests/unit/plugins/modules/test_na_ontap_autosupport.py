# (c) 2018-2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP autosupport Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_autosupport \
    import NetAppONTAPasup as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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


class MockONTAPConnection():
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None):
        ''' save arguments '''
        self.type = kind
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.type == 'asup':
            xml = self.build_asup_info()
        elif self.type == 'asup_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_asup_info():
        ''' build xml data for asup-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes': {
                'autosupport-config-info': {
                    'is-enabled': 'true',
                    'node-name': 'node1',
                    'transport': 'http',
                    'post-url': 'support.netapp.com/asupprod/post/1.0/postAsup',
                    'from': 'Postmaster',
                    'proxy-url': 'username1@host.com:8080',
                    'retry-count': '16',
                    'max-http-size': '10485760',
                    'max-smtp-size': '5242880',
                    'is-support-enabled': 'true',
                    'is-node-in-subject': 'true',
                    'is-nht-data-enabled': 'false',
                    'is-perf-data-enabled': 'true',
                    'is-reminder-enabled': 'true',
                    'is-private-data-removed': 'false',
                    'is-local-collection-enabled': 'true',
                    'is-ondemand-enabled': 'true',
                    'validate-digital-certificate': 'true',

                }
            }
        }
        xml.translate_struct(data)
        return xml


def default_args():
    args = {
        'state': 'present',
        'hostname': '10.10.10.10',
        'username': 'admin',
        'https': 'true',
        'validate_certs': 'false',
        'password': 'password',
        'node_name': 'node1',
        'retry_count': '16',
        'transport': 'http',
        'ondemand_enabled': 'true'
    }
    return args


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, dict(version=dict(generation=9, major=9, minor=0, full='dummy')), None),
    'is_rest_9_8': (200, dict(version=dict(generation=9, major=8, minor=0, full='dummy')), None),
    'is_zapi': (400, {}, "Unreachable"),
    'empty_good': (200, {}, None),
    'zero_record': (200, dict(records=[], num_records=0), None),
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'one_asup_record': (200, {
        "records": [{
            'node': 'node1',
            'state': True,
            'from': 'Postmaster',
            'support': True,
            'transport': 'http',
            'url': 'support.netapp.com/asupprod/post/1.0/postAsup',
            'proxy_url': 'username1@host.com:8080',
            'hostname_subj': True,
            'nht': False,
            'perf': True,
            'retry_count': 16,
            'reminder': True,
            'max_http_size': 10485760,
            'max_smtp_size': 5242880,
            'remove_private_data': False,
            'local_collection': True,
            'ondemand_state': True,
            'ondemand_server_url': 'https://support.netapp.com/aods/asupmessage'
        }],
        'num_records': 1
    }, None)
}


# using pytest natively, without unittest.TestCase
@pytest.fixture
def patch_ansible():
    with patch.multiple(basic.AnsibleModule,
                        exit_json=exit_json,
                        fail_json=fail_json) as mocks:
        yield mocks


def get_asup_mock_object(cx_type='zapi', kind=None):
    asup_obj = my_module()
    if cx_type == 'zapi':
        if kind is None:
            asup_obj.server = MockONTAPConnection()
        else:
            asup_obj.server = MockONTAPConnection(kind=kind)
    return asup_obj


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_ensure_get_called(patch_ansible):
    ''' test get_asup for non-existent policy'''
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    print('starting')
    my_obj = my_module()
    print('use_rest:', my_obj.use_rest)
    my_obj.server = MockONTAPConnection()
    assert my_obj.get_autosupport_config is not None


def test_rest_missing_arguments(patch_ansible):     # pylint: disable=redefined-outer-name,unused-argument
    ''' create asup '''
    args = dict(default_args())
    del args['hostname']
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = 'missing required arguments: hostname'
    assert exc.value.args[0]['msg'] == msg


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_autosupport.NetAppONTAPasup.modify_autosupport_config')
def test_successful_modify(self, patch_ansible):
    ''' modifying asup and testing idempotency '''
    args = dict(default_args())
    args['use_rest'] = 'never'
    args['local_collection_enabled'] = False
    set_module_args(args)
    my_obj = my_module()
    my_obj.ems_log_event = Mock(return_value=None)
    my_obj.server = MockONTAPConnection('asup')
    with patch.object(my_module, 'modify_autosupport_config', wraps=my_obj.modify_autosupport_config) as mock_modify:
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Modify: ' + repr(exc.value))
        assert exc.value.args[0]['changed']
        mock_modify.assert_called_with({'local_collection_enabled': False})
    # test idempotency
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.ems_log_event = Mock(return_value=None)
    my_obj.server = MockONTAPConnection('asup')
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Modify: ' + repr(exc.value))
    print(exc.value.args[0]['changed'])
    assert not exc.value.args[0]['changed']


def test_if_all_methods_catch_exception(patch_ansible):
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('asup_fail')
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.modify_autosupport_config(modify={})
    assert 'Error modifying ' in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_modify_no_action(mock_request, patch_ansible):        # pylint: disable=redefined-outer-name,unused-argument
    ''' modify asup '''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_asup_record'],     # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is False
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 2


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_modify_prepopulate(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' modify asup '''
    args = dict(default_args())
    args['ondemand_enabled'] = False
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_asup_record'],    # get
        SRR['empty_good'],              # patch
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3
