# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module unit test helper zapi_factory """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.framework import zapi_factory as uut

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')    # pragma: no cover

AGGR_INFO = {'num-records': 3,
             'attributes-list':
                 {'aggr-attributes':
                     {'aggregate-name': 'aggr_name',
                      'aggr-raid-attributes': {
                          'state': 'online',
                          'disk-count': '4',
                          'encrypt-with-aggr-key': 'true'},
                      'aggr-snaplock-attributes': {'snaplock-type': 'snap_t'}}
                  },
             }


def test_build_zapi_response_empty():
    empty, valid = uut.build_zapi_response({})
    assert valid == 'valid'
    print(empty.to_string())
    assert empty.to_string() == b'<results status="passed"/>'


def test_build_zapi_response_dict():
    aggr_info, valid = uut.build_zapi_response(AGGR_INFO)
    assert valid == 'valid'
    print(aggr_info.to_string())
    aggr_str = aggr_info.to_string()
    assert b'<aggregate-name>aggr_name</aggregate-name>' in aggr_str
    assert b'<aggr-snaplock-attributes><snaplock-type>snap_t</snaplock-type></aggr-snaplock-attributes>' in aggr_str
    assert b'<results status="passed">' in aggr_str
    assert b'<num-records>3</num-records>' in aggr_str


def test_build_zapi_error():
    zapi1, valid = uut.build_zapi_error('54321', 'error_text')
    assert valid == 'valid'
    zapi2, valid = uut.build_zapi_error(54321, 'error_text')
    assert valid == 'valid'
    assert zapi1.to_string() == zapi2.to_string()
    print(zapi1.to_string())
    assert zapi1.to_string() == b'<results errno="54321" reason="error_text"/>'


def test_default_responses():
    zrr = uut.zapi_responses()
    assert zrr
    assert 'empty' in zrr
    print(zrr['empty'][0].to_string())
    assert zrr['empty'][0].to_string() == uut.build_zapi_response({})[0].to_string()


def test_add_response():
    zrr = uut.zapi_responses(
        {'empty': uut.build_zapi_response({'k': 'v'}, 1)}
    )
    assert zrr
    assert 'empty' in zrr
    print(zrr['empty'][0].to_string())
    assert zrr['empty'][0].to_string() == uut.build_zapi_response({'k': 'v'}, 1)[0].to_string()


def test_negative_add_response():
    with pytest.raises(KeyError) as exc:
        zrr = uut.zapi_responses(
            {'empty': uut.build_zapi_response({})}, allow_override=False
        )
    print(exc.value)
    assert 'duplicated key: empty' == exc.value.args[0]


def test_negative_add_default_error():
    uut._DEFAULT_ERRORS['empty'] = uut.build_zapi_error(12345, 'hello')
    with pytest.raises(KeyError) as exc:
        zrr = uut.zapi_responses(allow_override=False)
    print(exc.value)
    assert 'duplicated key: empty' == exc.value.args[0]
    del uut._DEFAULT_ERRORS['empty']


def test_negative_add_error():
    with pytest.raises(KeyError) as exc:
        zrr = uut.zapi_responses(
            {'empty': uut.build_zapi_error(12345, 'hello')}, allow_override=False
        )
    print(exc.value)
    assert 'duplicated key: empty' == exc.value.args[0]


def test_negative_key_does_not_exist():
    zrr = uut.zapi_responses()
    with pytest.raises(KeyError) as exc:
        zrr['bad_key']
    print(exc.value)
    msg = 'bad_key not registered, list of valid keys:'
    assert msg in exc.value.args[0]
