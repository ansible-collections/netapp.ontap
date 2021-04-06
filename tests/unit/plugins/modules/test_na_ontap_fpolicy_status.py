# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP fpolicy status Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_status \
    import NetAppOntapFpolicyStatus as my_module  # module under test

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
        if self.type == 'fpolicy_policy_enabled':
            xml = self.build_fpolicy_status_info_enabled()
        elif self.type == 'fpolicy_policy_disabled':
            xml = self.build_fpolicy_status_info_disabled()
        elif self.type == 'fpolicy_policy_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_fpolicy_status_info_enabled():
        ''' build xml data for fpolicy-policy-status-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes-list': {
                'fpolicy-policy-status-info': {
                    'vserver': 'svm1',
                    'policy-name': 'fPolicy1',
                    'status': 'true'
                }
            }
        }
        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_fpolicy_status_info_disabled():
        ''' build xml data for fpolicy-policy-status-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes-list': {
                'fpolicy-policy-status-info': {
                    'vserver': 'svm1',
                    'policy-name': 'fPolicy1',
                    'status': 'false'
                }
            }
        }
        xml.translate_struct(data)
        return xml


def default_args():
    args = {
        'vserver': 'svm1',
        'policy_name': 'fPolicy1',
        'sequence_number': '10',
        'hostname': '10.10.10.10',
        'username': 'username',
        'password': 'password',
        'use_rest': 'always'
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
    # 'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'uuid': (200, {
        'records': [{
            'uuid': '56ab5d21'
        }],
        'num_records': 1
    }, None),
    'fpolicy_status_info_enabled': (200, {
        'records': [{
            'svm': {
                'uuid': '56ab5d21',
                'name': 'svm1'
            },
            'policies': [{
                'name': 'fPolicy1',
                'enabled': True,
                'priority': 10
            }]
        }],
        'num_records': 1
    }, None),
    'fpolicy_status_info_disabled': (200, {
        'records': [{
            'svm': {
                'uuid': '56ab5d21',
                'name': 'svm1'
            },
            'policies': [{
                'name': 'fPolicy1',
                'enabled': False
            }]
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


def get_fpolicy_status_mock_object(cx_type='zapi', kind=None):
    fpolicy_status_obj = my_module()
    if cx_type == 'zapi':
        if kind is None:
            fpolicy_status_obj.server = MockONTAPConnection()
        else:
            fpolicy_status_obj.server = MockONTAPConnection(kind=kind)
    return fpolicy_status_obj


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_ensure_get_called(patch_ansible):
    ''' test get_fpolicy_policy_status for non-existent fPolicy'''
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    print('starting')
    my_obj = my_module()
    print('use_rest:', my_obj.use_rest)
    my_obj.server = MockONTAPConnection('fpolicy_policy_enabled')
    assert my_obj.get_fpolicy_policy_status is not None


def test_rest_missing_arguments(patch_ansible):     # pylint: disable=redefined-outer-name,unused-argument
    ''' enable fpolicy '''
    args = dict(default_args())
    del args['hostname']
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = 'missing required arguments: hostname'
    assert exc.value.args[0]['msg'] == msg


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_status.NetAppOntapFpolicyStatus.enable_fpolicy_policy')
def test_successful_enable(self, patch_ansible):
    ''' Enable fPolicy and test idempotency '''
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fpolicy_policy_disabled')
    with patch.object(my_module, 'enable_fpolicy_policy', wraps=my_obj.enable_fpolicy_policy) as mock_enable:
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Enable: ' + repr(exc.value))
        assert exc.value.args[0]['changed']
        mock_enable.assert_called_with()
    # test idempotency
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fpolicy_policy_enabled')
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Enable: ' + repr(exc.value))
    assert not exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_status.NetAppOntapFpolicyStatus.disable_fpolicy_policy')
def test_successful_disable(self, patch_ansible):
    ''' Disable fPolicy and test idempotency '''
    args = dict(default_args())
    args['use_rest'] = 'never'
    args['state'] = 'absent'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fpolicy_policy_enabled')
    with patch.object(my_module, 'disable_fpolicy_policy', wraps=my_obj.disable_fpolicy_policy) as mock_disable:
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Enable: ' + repr(exc.value))
        assert exc.value.args[0]['changed']
        mock_disable.assert_called_with()
    # test idempotency
    args = dict(default_args())
    args['use_rest'] = 'never'
    args['state'] = 'absent'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fpolicy_policy_disabled')
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Enable: ' + repr(exc.value))
    assert not exc.value.args[0]['changed']


def test_if_all_methods_catch_exception(patch_ansible):
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fpolicy_policy_fail')
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.enable_fpolicy_policy()
    print(str(exc.value.args[0]['msg']))
    assert 'Error enabling fPolicy policy ' in exc.value.args[0]['msg']
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.disable_fpolicy_policy()
    assert 'Error disabling fPolicy policy ' in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_enable(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' enable fPolicy policy '''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['uuid'],    # get
        SRR['fpolicy_status_info_disabled'],     # get
        SRR['empty_good'],      # patch
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 4


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_disable(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' disable fPolicy policy '''
    args = dict(default_args())
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['uuid'],    # get
        SRR['fpolicy_status_info_enabled'],     # get
        SRR['empty_good'],      # patch
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 4
