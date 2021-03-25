# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP fpolicy ext engine Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_ext_engine \
    import NetAppOntapFpolicyExtEngine as my_module  # module under test

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
        if self.type == 'fpolicy_ext_engine':
            xml = self.build_fpolicy_ext_engine_info()
        elif self.type == 'fpolicy_ext_engine_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_fpolicy_ext_engine_info():
        ''' build xml data for fpolicy-policy-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes-list': {
                'fpolicy-external-engine-info': {
                    'vserver': 'svm1',
                    'engine-name': 'engine1',
                    'primary-servers': [
                        {'ip-address': '10.11.12.13'}
                    ],
                    'port-number': '8787',
                    'extern-engine-type': 'asynchronous',
                    'ssl-option': 'no_auth'
                }
            }
        }
        xml.translate_struct(data)
        return xml


def default_args():
    args = {
        'vserver': 'svm1',
        'name': 'engine1',
        'primary_servers': '10.11.12.13',
        'port': 8787,
        'extern_engine_type': 'asynchronous',
        'ssl_option': 'no_auth',
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
    'one_record_uuid': (200, dict(records=[dict(uuid='a1b2c3')], num_records=1), None),
    'end_of_sequence': (500, None, "Unexpected call to send_request"),
    'generic_error': (400, None, "Expected error"),
    'one_fpolicy_ext_engine_record': (200, {
        "records": [{
            'engine-name': 'engine1',
            'vserver': 'svm1',
            'primary-servers': ['10.11.12.13'],
            'port': 8787,
            'extern-engine-type': 'asynchronous',
            'ssl-option': 'no-auth'
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


def get_fpolicy_ext_engine_mock_object(cx_type='zapi', kind=None):
    fpolicy_ext_engine_obj = my_module()
    if cx_type == 'zapi':
        if kind is None:
            fpolicy_ext_engine_obj.server = MockONTAPConnection()
        else:
            fpolicy_ext_engine_obj.server = MockONTAPConnection(kind=kind)
    return fpolicy_ext_engine_obj


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_ensure_get_called(patch_ansible):
    ''' test get_fpolicy_ext_engine for non-existent engine'''
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    print('starting')
    my_obj = my_module()
    print('use_rest:', my_obj.use_rest)
    my_obj.server = MockONTAPConnection()
    assert my_obj.get_fpolicy_ext_engine is not None


def test_rest_missing_arguments(patch_ansible):     # pylint: disable=redefined-outer-name,unused-argument
    ''' create fpolicy ext engine '''
    args = dict(default_args())
    del args['hostname']
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = 'missing required arguments: hostname'
    assert exc.value.args[0]['msg'] == msg


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_ext_engine.NetAppOntapFpolicyExtEngine.create_fpolicy_ext_engine')
def test_successful_create(self, patch_ansible):
    ''' creating fpolicy_ext_engine and test idempotency '''
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection()
    with patch.object(my_module, 'create_fpolicy_ext_engine', wraps=my_obj.create_fpolicy_ext_engine) as mock_create:
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Create: ' + repr(exc.value))
        assert exc.value.args[0]['changed']
        mock_create.assert_called_with()
    # test idempotency
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fpolicy_ext_engine')
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Create: ' + repr(exc.value))
    assert not exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_ext_engine.NetAppOntapFpolicyExtEngine.delete_fpolicy_ext_engine')
def test_successful_delete(self, patch_ansible):
    ''' delete fpolicy_ext_engine and test idempotency '''
    args = dict(default_args())
    args['use_rest'] = 'never'
    args['state'] = 'absent'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fpolicy_ext_engine')
    with patch.object(my_module, 'delete_fpolicy_ext_engine', wraps=my_obj.delete_fpolicy_ext_engine) as mock_delete:
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Delete: ' + repr(exc.value))
        assert exc.value.args[0]['changed']
        mock_delete.assert_called_with()
    # test idempotency
    args = dict(default_args())
    args['use_rest'] = 'never'
    args['state'] = 'absent'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Delete: ' + repr(exc.value))
    assert not exc.value.args[0]['changed']


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_fpolicy_ext_engine.NetAppOntapFpolicyExtEngine.modify_fpolicy_ext_engine')
def test_successful_modify(self, patch_ansible):
    ''' modifying fpolicy_ext_engine and testing idempotency '''
    args = dict(default_args())
    args['use_rest'] = 'never'
    args['port'] = '9999'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fpolicy_ext_engine')
    with patch.object(my_module, 'modify_fpolicy_ext_engine', wraps=my_obj.modify_fpolicy_ext_engine) as mock_modify:
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Modify: ' + repr(exc.value))
        assert exc.value.args[0]['changed']
        mock_modify.assert_called_with({'port': 9999})
    # test idempotency
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fpolicy_ext_engine')
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Modify: ' + repr(exc.value))
    assert not exc.value.args[0]['changed']


def test_if_all_methods_catch_exception(patch_ansible):
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fpolicy_ext_engine_fail')
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.create_fpolicy_ext_engine()
    assert 'Error creating fPolicy external engine ' in exc.value.args[0]['msg']
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.delete_fpolicy_ext_engine()
    assert 'Error deleting fPolicy external engine ' in exc.value.args[0]['msg']
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.modify_fpolicy_ext_engine(modify={})
    assert 'Error modifying fPolicy external engine ' in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' create fpolicy ext engine '''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],     # get
        SRR['empty_good'],      # post
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_create_no_action(mock_request, patch_ansible):        # pylint: disable=redefined-outer-name,unused-argument
    ''' create fpolicy ext engine idempotent '''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_fpolicy_ext_engine_record'],     # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is False
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 2


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_delete_no_action(mock_request, patch_ansible):    # pylint: disable=redefined-outer-name,unused-argument
    ''' delete fpolicy ext engine '''
    args = dict(default_args())
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['zero_record'],             # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is False
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 2


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_delete(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' delete fpolicy ext engine '''
    args = dict(default_args())
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_fpolicy_ext_engine_record'],    # get
        SRR['empty_good'],                       # delete
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_modify_no_action(mock_request, patch_ansible):        # pylint: disable=redefined-outer-name,unused-argument
    ''' modify fpolicy ext engine '''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_fpolicy_ext_engine_record'],     # get
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
    ''' modify fpolicy ext engine '''
    args = dict(default_args())
    args['port'] = 9999
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_fpolicy_ext_engine_record'],    # get
        SRR['empty_good'],              # patch
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_delete_no_action(mock_request, patch_ansible):        # pylint: disable=redefined-outer-name,unused-argument
    ''' delete fpolicy ext engine '''
    args = dict(default_args())
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['empty_good'],     # get
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
    ''' delete fpolicy ext engine '''
    args = dict(default_args())
    args['state'] = 'absent'
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['one_fpolicy_ext_engine_record'],    # get
        SRR['empty_good'],              # delete
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3
