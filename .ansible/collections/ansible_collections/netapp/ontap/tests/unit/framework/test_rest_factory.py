# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for Ansible module unit test helper rest_factory """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses


def test_default_responses():
    srr = rest_responses()
    assert srr
    assert 'is_zapi' in srr
    assert srr['is_zapi'] == (400, {}, "Unreachable")


def test_add_response():
    srr = rest_responses(
        {'is_zapi': (444, {'k': 'v'}, "Unknown")}
    )
    assert srr
    assert 'is_zapi' in srr
    assert srr['is_zapi'] == (444, {'k': 'v'}, "Unknown")


def test_negative_add_response():
    with pytest.raises(KeyError) as exc:
        srr = rest_responses(
            {'is_zapi': (444, {'k': 'v'}, "Unknown")}, allow_override=False
        )
    print(exc.value)
    assert 'duplicated key: is_zapi' == exc.value.args[0]


def test_negative_key_does_not_exist():
    srr = rest_responses()
    with pytest.raises(KeyError) as exc:
        srr['bad_key']
    print(exc.value)
    msg = 'bad_key not registered, list of valid keys:'
    assert msg in exc.value.args[0]
