# (c) 2018, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module: na_ontap_aggregate """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import json
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, Mock
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_aggregate \
    import NetAppOntapAggregate as my_module  # module under test

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


AGGR_NAME = 'aggr_name'
OS_NAME = 'abc'


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None, parm1=None, parm2=None):
        ''' save arguments '''
        self.type = kind
        self.parm1 = parm1
        self.parm2 = parm2
        self.xml_in = None
        self.xml_out = None
        self.zapis = list()

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        print('request:', xml.to_string())
        zapi = xml.get_name()
        self.zapis.append(zapi)
        if zapi == 'aggr-object-store-get-iter':
            if self.type in ('aggregate_no_object_store',):
                xml = None
            else:
                xml = self.build_object_store_info()
        elif self.type in ('aggregate', 'aggr_disks', 'aggr_mirrors', 'aggregate_no_object_store'):
            with_os = self.type != 'aggregate_no_object_store'
            xml = self.build_aggregate_info(self.parm1, self.parm2, with_object_store=with_os)
            if self.type in ('aggr_disks', 'aggr_mirrors'):
                self.type = 'disks'
        elif self.type == 'no_aggregate':
            xml = None
        elif self.type == 'no_aggregate_then_aggregate':
            xml = None
            self.type = 'aggregate'
        elif self.type == 'disks':
            xml = self.build_disk_info()
        elif self.type == 'aggregate_fail':
            raise netapp_utils.zapi.NaApiError(code='TEST', message="This exception is from the unit test")
        self.xml_out = xml
        return xml

    @staticmethod
    def build_aggregate_info(vserver, aggregate, with_object_store):
        ''' build xml data for aggregate and vserser-info '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 3,
                'attributes-list':
                    {'aggr-attributes':
                     {'aggregate-name': aggregate,
                      'aggr-raid-attributes': {'state': 'offline'}
                      },
                     'object-store-information': {'object-store-name': 'abc'}
                     },
                'vserver-info':
                    {'vserver-name': vserver
                     }
                }
        if not with_object_store:
            del data['attributes-list']['object-store-information']
        xml.translate_struct(data)
        print(xml.to_string())
        return xml

    @staticmethod
    def build_object_store_info():
        ''' build xml data for object_store '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 3,
                'attributes-list':
                    {'object-store-information': {'object-store-name': 'abc'}
                     }
                }
        xml.translate_struct(data)
        print(xml.to_string())
        return xml

    @staticmethod
    def build_disk_info():
        ''' build xml data for disk '''
        xml = netapp_utils.zapi.NaElement('xml')
        data = {'num-records': 1,
                'attributes-list': [
                    {'disk-info':
                     {'disk-name': '1',
                      'disk-raid-info':
                      {'disk-aggregate-info':
                       {'plex-name': 'plex0'}
                       }}},
                    {'disk-info':
                     {'disk-name': '2',
                      'disk-raid-info':
                      {'disk-aggregate-info':
                       {'plex-name': 'plex0'}
                       }}},
                    {'disk-info':
                     {'disk-name': '3',
                      'disk-raid-info':
                      {'disk-aggregate-info':
                       {'plex-name': 'plexM'}
                       }}},
                    {'disk-info':
                     {'disk-name': '4',
                      'disk-raid-info':
                      {'disk-aggregate-info':
                       {'plex-name': 'plexM'}
                       }}},
                ]}
        xml.translate_struct(data)
        print(xml.to_string())
        return xml


class TestMyModule(unittest.TestCase):
    ''' a group of related Unit Tests '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.server = MockONTAPConnection('aggregate', '12', 'name')
        # whether to use a mock or a simulator
        self.onbox = False
        self.zapis = list()

    def set_default_args(self):
        if self.onbox:
            hostname = '10.193.74.78'
            username = 'admin'
            password = 'netapp1!'
            name = 'name'
        else:
            hostname = 'hostname'
            username = 'username'
            password = 'password'
            name = AGGR_NAME
        return dict({
            'hostname': hostname,
            'username': username,
            'password': password,
            'name': name
        })

    def call_command(self, module_args, what=None):
        ''' utility function to call apply '''
        args = dict(self.set_default_args())
        args.update(module_args)
        set_module_args(args)
        my_obj = my_module()
        my_obj.asup_log_for_cserver = Mock(return_value=None)
        aggregate = 'aggregate'
        if what == 'disks':
            aggregate = 'aggr_disks'
        elif what == 'mirrors':
            aggregate = 'aggr_mirrors'
        elif what is not None:
            aggregate = what

        if not self.onbox:
            # mock the connection
            my_obj.server = MockONTAPConnection(aggregate, '12', AGGR_NAME)
            self.zapis = my_obj.server.zapis
        with pytest.raises(AnsibleExitJson) as exc:
            my_obj.apply()
        return exc.value.args[0]['changed']

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            my_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_create(self):
        module_args = {
            'disk_count': '2',
            'is_mirrored': 'true',
        }
        changed = self.call_command(module_args, what='no_aggregate')
        assert changed
        assert 'aggr-object-store-attach' not in self.zapis

    def test_create_with_object_store(self):
        module_args = {
            'disk_count': '2',
            'is_mirrored': 'true',
            'object_store_name': 'abc'
        }
        changed = self.call_command(module_args, what='no_aggregate')
        assert changed
        assert 'aggr-object-store-attach' in self.zapis

    def test_is_mirrored(self):
        module_args = {
            'disk_count': '2',
            'is_mirrored': 'true',
        }
        changed = self.call_command(module_args)
        assert not changed

    def test_disks_list(self):
        module_args = {
            'disks': ['1', '2'],
        }
        changed = self.call_command(module_args, 'disks')
        assert not changed

    def test_mirror_disks(self):
        module_args = {
            'disks': ['1', '2'],
            'mirror_disks': ['3', '4']
        }
        changed = self.call_command(module_args, 'mirrors')
        assert not changed

    def test_spare_pool(self):
        module_args = {
            'disk_count': '2',
            'spare_pool': 'Pool1'
        }
        changed = self.call_command(module_args)
        assert not changed

    def test_rename(self):
        module_args = {
            'from_name': 'test_name2'
        }
        changed = self.call_command(module_args, 'no_aggregate_then_aggregate')
        assert changed
        assert 'aggr-rename' in self.zapis

    def test_rename_error_no_from(self):
        module_args = {
            'from_name': 'test_name2'
        }
        with pytest.raises(AnsibleFailJson) as exc:
            self.call_command(module_args, 'no_aggregate')
        msg = 'Error renaming: aggregate %s does not exist' % module_args['from_name']
        assert msg in exc.value.args[0]['msg']

    def test_rename_with_add_object_store(self):
        module_args = {
            'from_name': 'test_name2'
        }
        changed = self.call_command(module_args, 'aggregate_no_object_store')
        assert not changed

    def test_object_store_present(self):
        module_args = {
            'object_store_name': 'abc'
        }
        changed = self.call_command(module_args)
        assert not changed

    def test_object_store_create(self):
        module_args = {
            'object_store_name': 'abc'
        }
        changed = self.call_command(module_args, 'aggregate_no_object_store')
        assert changed

    def test_object_store_modify(self):
        ''' not supported '''
        module_args = {
            'object_store_name': 'def'
        }
        with pytest.raises(AnsibleFailJson) as exc:
            self.call_command(module_args)
        msg = 'Error: object store %s is already associated with aggregate %s.' % (OS_NAME, AGGR_NAME)
        assert msg in exc.value.args[0]['msg']

    def test_if_all_methods_catch_exception(self):
        module_args = {}
        module_args.update(self.set_default_args())
        module_args.update({'service_state': 'online'})
        module_args.update({'unmount_volumes': 'True'})
        module_args.update({'from_name': 'test_name2'})
        set_module_args(module_args)
        my_obj = my_module()
        if not self.onbox:
            my_obj.server = MockONTAPConnection('aggregate_fail')
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.aggr_get_iter(module_args.get('name'))
        assert '' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.aggregate_online()
        assert 'Error changing the state of aggregate' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.aggregate_offline()
        assert 'Error changing the state of aggregate' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.create_aggr()
        assert 'Error provisioning aggregate' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.delete_aggr()
        assert 'Error removing aggregate' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.rename_aggregate()
        assert 'Error renaming aggregate' in exc.value.args[0]['msg']
        with pytest.raises(AnsibleFailJson) as exc:
            my_obj.asup_log_for_cserver = Mock(return_value=None)
            my_obj.apply()
        assert 'TEST:This exception is from the unit test' in exc.value.args[0]['msg']

    def test_disks_bad_mapping(self):
        module_args = {
            'disks': ['0'],
        }
        with pytest.raises(AnsibleFailJson) as exc:
            self.call_command(module_args, 'mirrors')
        msg = "Error mapping disks for aggregate %s: cannot not match disks with current aggregate disks." % AGGR_NAME
        assert exc.value.args[0]['msg'].startswith(msg)

    def test_disks_overlapping_mirror(self):
        module_args = {
            'disks': ['1', '2', '3'],
        }
        with pytest.raises(AnsibleFailJson) as exc:
            self.call_command(module_args, 'mirrors')
        msg = "Error mapping disks for aggregate %s: found overlapping plexes:" % AGGR_NAME
        assert exc.value.args[0]['msg'].startswith(msg)

    def test_disks_removing_disk(self):
        module_args = {
            'disks': ['1'],
        }
        with pytest.raises(AnsibleFailJson) as exc:
            self.call_command(module_args, 'mirrors')
        msg = "Error removing disks is not supported.  Aggregate %s: these disks cannot be removed: ['2']." % AGGR_NAME
        assert exc.value.args[0]['msg'].startswith(msg)

    def test_disks_removing_mirror_disk(self):
        module_args = {
            'disks': ['1', '2'],
            'mirror_disks': ['4', '6']
        }
        with pytest.raises(AnsibleFailJson) as exc:
            self.call_command(module_args, 'mirrors')
        msg = "Error removing disks is not supported.  Aggregate %s: these disks cannot be removed: ['3']." % AGGR_NAME
        assert exc.value.args[0]['msg'].startswith(msg)

    def test_disks_add(self):
        module_args = {
            'disks': ['1', '2', '5'],
        }
        changed = self.call_command(module_args, 'disks')
        assert changed

    def test_mirror_disks_add(self):
        module_args = {
            'disks': ['1', '2', '5'],
            'mirror_disks': ['3', '4', '6']
        }
        changed = self.call_command(module_args, 'mirrors')
        assert changed

    def test_mirror_disks_add_unbalanced(self):
        module_args = {
            'disks': ['1', '2'],
            'mirror_disks': ['3', '4', '6']
        }
        with pytest.raises(AnsibleFailJson) as exc:
            self.call_command(module_args, 'mirrors')
        msg = "Error cannot add mirror disks ['6'] without adding disks for aggregate %s." % AGGR_NAME
        assert exc.value.args[0]['msg'].startswith(msg)
