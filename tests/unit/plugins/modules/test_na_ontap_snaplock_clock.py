# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP fpolicy ext engine Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible


from ansible_collections.netapp.ontap.plugins.modules.na_ontap_snaplock_clock \
    import NetAppOntapSnaplockClock as my_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


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
        if self.type == 'snaplock_clock_set':
            xml = self.build_snaplock_clock_info_set()
        elif self.type == 'snaplock_clock_not_set':
            xml = self.build_snaplock_clock_info_not_set()
        elif self.type == 'snaplock_clock_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_snaplock_clock_info_set():
        ''' build xml data for snaplock-get-node-compliance-clock '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'snaplock-node-compliance-clock': {
                'compliance-clock-info': {
                    'formatted-snaplock-compliance-clock': 'Tue Mar 23 09:56:07 EDT 2021 -04:00'
                }
            }
        }
        xml.translate_struct(data)
        return xml

    @staticmethod
    def build_snaplock_clock_info_not_set():
        ''' build xml data for snaplock-get-node-compliance-clock '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'snaplock-node-compliance-clock': {
                'compliance-clock-info': {
                    'formatted-snaplock-compliance-clock': 'ComplianceClock is not configured.'
                }
            }
        }
        xml.translate_struct(data)
        return xml


def default_args():
    args = {
        'node': 'node1',
        'hostname': 'hostname',
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
    'snaplock_clock_set_record': (200, {
        "records": [{
            'node': 'node1',
            'time': 'Tue Mar 23 09:56:07 EDT 2021 -04:00'
        }],
        'num_records': 1
    }, None),
    'snaplock_clock_not_set_record': (200, {
        "records": [{
            'node': 'node1',
            'time': 'ComplianceClock is not configured.'
        }],
        'num_records': 1
    }, None)

}


def get_snaplock_clock_mock_object(cx_type='zapi', kind=None):
    snaplock_clock_obj = my_module()
    if cx_type == 'zapi':
        if kind is None:
            snaplock_clock_obj.server = MockONTAPConnection()
        else:
            snaplock_clock_obj.server = MockONTAPConnection(kind=kind)
    return snaplock_clock_obj


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_ensure_get_called(patch_ansible):
    ''' test get_snaplock_clock for non initialized clock'''
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    print('starting')
    my_obj = my_module()
    print('use_rest:', my_obj.use_rest)
    my_obj.server = MockONTAPConnection(kind='snaplock_clock_not_set')
    assert my_obj.get_snaplock_node_compliance_clock is not None


def test_rest_missing_arguments(patch_ansible):     # pylint: disable=redefined-outer-name,unused-argument
    ''' test for missing arguments '''
    args = dict(default_args())
    del args['hostname']
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = 'missing required arguments: hostname'
    assert exc.value.args[0]['msg'] == msg


@patch('ansible_collections.netapp.ontap.plugins.modules.na_ontap_snaplock_clock.NetAppOntapSnaplockClock.set_snaplock_node_compliance_clock')
def test_successful_initialize(self, patch_ansible):
    ''' Initializing snaplock_clock and test idempotency '''
    args = dict(default_args())
    args['use_rest'] = 'never'
    args['feature_flags'] = {'no_cserver_ems': True}
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection(kind='snaplock_clock_not_set')
    with patch.object(my_module, 'set_snaplock_node_compliance_clock', wraps=my_obj.set_snaplock_node_compliance_clock) as mock_create:
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        print('Create: ' + repr(exc.value))
        assert exc.value.args[0]['changed']
        mock_create.assert_called_with()
    # test idempotency
    args = dict(default_args())
    args['use_rest'] = 'never'
    args['feature_flags'] = {'no_cserver_ems': True}
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('snaplock_clock_set')
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    print('Create: ' + repr(exc.value))
    assert not exc.value.args[0]['changed']


def test_if_all_methods_catch_exception(patch_ansible):
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('snaplock_clock_fail')
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.set_snaplock_node_compliance_clock()
    assert 'Error setting snaplock compliance clock for node ' in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_initialize(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Initialize snaplock clock '''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['snaplock_clock_not_set_record'],     # get
        SRR['empty_good'],                        # post
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 3


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_initialize_no_action(mock_request, patch_ansible):        # pylint: disable=redefined-outer-name,unused-argument
    ''' Initialize snaplock clock idempotent '''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['snaplock_clock_set_record'],     # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is False
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 2
