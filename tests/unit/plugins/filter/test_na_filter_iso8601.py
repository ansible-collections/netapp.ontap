# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

""" unit tests for iso8601 filter """

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

from ansible.errors import AnsibleFilterError
from ansible_collections.netapp.ontap.plugins.filter import na_filter_iso8601
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.tests.unit.framework import ut_utilities

if na_filter_iso8601.IMPORT_ERROR and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as isodate is not available')

ISO_DURATION = 'P689DT13H57M44S'
ISO_DURATION_WEEKS = 'P98W'
SECONDS_DURATION = 59579864


def test_class_filter():
    my_obj = na_filter_iso8601.FilterModule()
    assert len(my_obj.filters()) == 2


def test_iso8601_duration_to_seconds():
    my_obj = na_filter_iso8601.FilterModule()
    assert my_obj.filters()['iso8601_duration_to_seconds'](ISO_DURATION) == SECONDS_DURATION


def test_negative_iso8601_duration_to_seconds():
    my_obj = na_filter_iso8601.FilterModule()
    with pytest.raises(AnsibleFilterError) as exc:
        my_obj.filters()['iso8601_duration_to_seconds']('BAD_DATE')
    print('EXC', exc)
    # exception is not properly formatted with older 3.x versions, assuming same issue as for IndexError
    if ut_utilities.is_indexerror_exception_formatted():
        assert 'BAD_DATE' in str(exc)


def test_iso8601_duration_from_seconds():
    my_obj = na_filter_iso8601.FilterModule()
    assert my_obj.filters()['iso8601_duration_from_seconds'](SECONDS_DURATION) == ISO_DURATION


def test_negative_iso8601_duration_from_seconds_str():
    my_obj = na_filter_iso8601.FilterModule()
    with pytest.raises(AnsibleFilterError) as exc:
        my_obj.filters()['iso8601_duration_from_seconds']('BAD_INT')
    print('EXC', exc)
    if ut_utilities.is_indexerror_exception_formatted():
        assert 'BAD_INT' in str(exc)


@patch('ansible_collections.netapp.ontap.plugins.filter.na_filter_iso8601.IMPORT_ERROR', 'import failed')
def test_negative_check_for_import():
    my_obj = na_filter_iso8601.FilterModule()
    with pytest.raises(AnsibleFilterError) as exc:
        my_obj.filters()['iso8601_duration_to_seconds'](ISO_DURATION)
    print('EXC', exc)
    if ut_utilities.is_indexerror_exception_formatted():
        assert 'import failed' in str(exc)
