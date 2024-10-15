# (c) 2021, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit test for ONTAP disks Ansible module '''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
# pylint: disable=unused-import
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_disks \
    import NetAppOntapDisks as my_module  # module under test

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

        try:
            container_type = self.xml_in['query']['storage-disk-info']['disk-raid-info']['container-type']
        except LookupError:
            container_type = None
        try:
            get_owned_disks = self.xml_in['query']['storage-disk-info']['disk-ownership-info']['home-node-name']
        except LookupError:
            get_owned_disks = None

        api_call = self.xml_in.get_name()

        if self.type == 'fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        elif api_call == 'storage-disk-get-iter':
            if container_type == 'spare':
                xml = self.home_spare_disks()
            elif get_owned_disks:
                xml = self.owned_disks()
            else:
                xml = self.partner_spare_disks()
        elif api_call == 'cf-status':
            xml = self.partner_node_name()
        self.xml_out = xml
        return xml

    @staticmethod
    def owned_disks():
        ''' build xml data for disk-inventory-info owned disks '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes-list': [
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.8'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.7'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.10'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.25'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.18'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.0'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.6'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.11'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.12'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.13'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.23'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.4'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.9'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.21'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.16'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.19'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.2'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.14'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.20'
                        }
                    }
                }
            ],
            'num-records': '19'
        }
        xml.translate_struct(data)
        return xml

    @staticmethod
    def home_spare_disks():
        ''' build xml data for disk-inventory-info home spare disks '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes-list': [
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.9'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.20'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.9'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.22'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.13'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.23'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.16'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.18'
                        }
                    }
                }
            ],
            'num-records': '8'
        }
        xml.translate_struct(data)
        return xml

    @staticmethod
    def partner_spare_disks():
        ''' build xml data for disk-inventory-info partner spare disks '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'attributes-list': [
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.7'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.15'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.21'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.23'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.19'
                        }
                    }
                },
                {
                    'storage-disk-info': {
                        'disk-inventory-info': {
                            'disk-cluster-name': '1.0.11'
                        }
                    }
                }
            ],
            'num-records': '6'
        }
        xml.translate_struct(data)
        return xml

    @staticmethod
    def partner_node_name():
        ''' build xml data for partner node name'''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'cf-status': {
                'partner-name': 'node2'
            }
        }
        xml.translate_struct(data)
        return xml

    @staticmethod
    def unassigned_disk_count():
        ''' build xml data for the count of unassigned disks on a node '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {
            'num-records': '0'
        }
        xml.translate_struct(data)
        return xml


def default_args():
    args = {
        'disk_count': 15,
        'node': 'node1',
        'disk_type': 'SAS',
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
    'owned_disk_record': (
        200, {
            'records': [
                {
                    "name": "1.0.8",
                    "type": "sas",
                    "container_type": "aggregate",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.7",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.10",
                    "type": "sas",
                    "container_type": "aggregate",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.18",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.0",
                    "type": "sas",
                    "container_type": "aggregate",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.6",
                    "type": "sas",
                    "container_type": "aggregate",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.11",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.12",
                    "type": "sas",
                    "container_type": "aggregate",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.13",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.23",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.22",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.4",
                    "type": "sas",
                    "container_type": "aggregate",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.9",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.21",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.16",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.19",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.2",
                    "type": "sas",
                    "container_type": "aggregate",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.14",
                    "type": "sas",
                    "container_type": "aggregate",
                    "home_node": {
                        "name": "node1"
                    }
                },
                {
                    "name": "1.0.20",
                    "type": "sas",
                    "container_type": "spare",
                    "home_node": {
                        "name": "node1"
                    }
                }
            ],
            'num_records': 19},
        None),

    # 'owned_disk_record': (200, {'num_records': 15}),
    'unassigned_disk_record': (
        200, {
            'records': [],
            'num_records': 0},
        None),
    'home_spare_disk_info_record': (
        200, {'records': [
            {
                'name': '1.0.20',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node1'}},
            {
                'name': '1.0.9',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node1'}},
            {
                'name': '1.0.22',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node1'}},
            {
                'name': '1.0.13',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node1'}},
            {
                'name': '1.0.17',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node1'}},
            {
                'name': '1.0.23',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node1'}},
            {
                'name': '1.0.16',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node1'}},
            {
                'name': '1.0.18',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node1'}}
        ],
            'num_records': 8,
            '_links': {'self': {'href': '/api/storage/disks?home_node.name=node1&container_type=spare&type=SAS&fields=name'}}},
        None),

    'partner_node_name_record': (
        200, {'records': [
            {
                'uuid': 'c345c182-a6a0-11eb-af7b-00a0984839de',
                'name': 'node2',
                'ha': {
                    'partners': [
                        {'name': 'node1'}
                    ]
                }
            }
        ],
            'num_records': 1},
        None),

    'partner_spare_disk_info_record': (
        200, {'records': [
            {
                'name': '1.0.7',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node2'}
            },
            {
                'name': '1.0.15',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node2'}
            },
            {
                'name': '1.0.21',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node2'}
            },
            {
                'name': '1.0.23',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node2'}
            },
            {
                'name': '1.0.19',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node2'}
            },
            {
                'name': '1.0.11',
                'type': 'sas',
                'container_type': 'spare',
                'home_node': {'name': 'node2'}
            }
        ],
            'num_records': 6},
        None)
}


def test_successful_assign(patch_ansible):
    ''' successful assign and test idempotency '''
    args = dict(default_args())
    args['use_rest'] = 'never'
    args['disk_count'] = '20'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection()
    my_obj.ems_log_event = Mock(return_value=None)
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
        print('Create: ' + repr(exc.value))
    assert exc.value.args[0]['changed']
    # mock_create.assert_called_with()
    args['use_rest'] = 'never'
    args['disk_count'] = '19'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection()
    my_obj.ems_log_event = Mock(return_value=None)
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
        print('Create: ' + repr(exc.value))
    assert not exc.value.args[0]['changed']


def test_successful_unassign(patch_ansible):
    ''' successful assign and test idempotency '''
    args = dict(default_args())
    args['use_rest'] = 'never'
    args['disk_count'] = '17'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection()
    my_obj.ems_log_event = Mock(return_value=None)
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
        print('Create: ' + repr(exc.value))
    assert exc.value.args[0]['changed']
    # mock_create.assert_called_with()
    args['use_rest'] = 'never'
    args['disk_count'] = '19'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection()
    my_obj.ems_log_event = Mock(return_value=None)
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
        print('Create: ' + repr(exc.value))
    assert not exc.value.args[0]['changed']


def test_module_fail_when_required_args_missing(patch_ansible):
    ''' required arguments are reported as errors '''
    with pytest.raises(AnsibleFailJson) as exc:
        set_module_args({})
        my_module()
    print('Info: %s' % exc.value.args[0]['msg'])


def test_ensure_get_called(patch_ansible):
    ''' test get_disks '''
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    print('starting')
    my_obj = my_module()
    print('use_rest:', my_obj.use_rest)
    my_obj.server = MockONTAPConnection()
    assert my_obj.get_disks is not None


def test_rest_missing_arguments(patch_ansible):     # pylint: disable=redefined-outer-name,unused-argument ##WHAT DOES THIS METHOD DO
    ''' create  scope '''
    args = dict(default_args())
    del args['hostname']
    set_module_args(args)
    with pytest.raises(AnsibleFailJson) as exc:
        my_module()
    msg = 'missing required arguments: hostname'
    assert exc.value.args[0]['msg'] == msg


def test_if_all_methods_catch_exception(patch_ansible):
    args = dict(default_args())
    args['use_rest'] = 'never'
    set_module_args(args)
    my_obj = my_module()
    my_obj.server = MockONTAPConnection('fail')
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_disks(container_type='owned', node='node1')
    assert 'Error getting disk ' in exc.value.args[0]['msg']
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_disks(container_type='unassigned')
    assert 'Error getting disk ' in exc.value.args[0]['msg']
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_disks(container_type='spare', node='node1')
    assert 'Error getting disk ' in exc.value.args[0]['msg']
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.get_partner_node_name()
    assert 'Error getting partner name ' in exc.value.args[0]['msg']
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.disk_assign(needed_disks=2)
    assert 'Error assigning disks ' in exc.value.args[0]['msg']
    with pytest.raises(AnsibleFailJson) as exc:
        my_obj.disk_unassign(['1.0.0', '1.0.1'])
    assert 'Error unassigning disks ' in exc.value.args[0]['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_assign(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Steal disks from partner node and assign them to the requested node '''
    args = dict(default_args())
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['owned_disk_record'],
        SRR['unassigned_disk_record'],
        SRR['home_spare_disk_info_record'],
        SRR['partner_node_name_record'],
        SRR['partner_spare_disk_info_record'],
        SRR['empty_good'],  # unassign
        SRR['empty_good'],  # assign
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 8


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_unassign(mock_request, patch_ansible):      # pylint: disable=redefined-outer-name,unused-argument
    ''' Steal disks from partner node and assign them to the requested node '''
    args = dict(default_args())
    args['disk_count'] = 17
    print(args)
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['owned_disk_record'],
        SRR['unassigned_disk_record'],
        SRR['home_spare_disk_info_record'],
        SRR['partner_node_name_record'],
        SRR['partner_spare_disk_info_record'],
        SRR['empty_good'],  # unassign
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is True
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 6


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
def test_rest_no_action(mock_request, patch_ansible):        # pylint: disable=redefined-outer-name,unused-argument
    ''' disk_count matches arguments, do nothing '''
    args = dict(default_args())
    args['disk_count'] = 19
    set_module_args(args)
    mock_request.side_effect = [
        SRR['is_rest'],
        SRR['owned_disk_record'],
        SRR['unassigned_disk_record'],
        SRR['home_spare_disk_info_record'],   # get
        SRR['end_of_sequence']
    ]
    my_obj = my_module()
    with pytest.raises(AnsibleExitJson) as exc:
        my_obj.apply()
    assert exc.value.args[0]['changed'] is False
    print(mock_request.mock_calls)
    assert len(mock_request.mock_calls) == 4
