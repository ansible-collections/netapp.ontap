# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# Author: Laurent Nicolas, laurentn@netapp.com

""" unit tests for Ansible modules for ONTAP:
    shared utility functions
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import sys


def is_indexerror_exception_formatted():
    """ some versions of python do not format IndexError exception properly
        the error message is not reported in str() or repr()
        We see this for older versions of Ansible, where the python version is frozen
        - fails on 3.5.7 but works on 3.5.10
        - fails on 3.6.8 but works on 3.6.9
        - fails on 3.7.4 but works on 3.7.5
        - fails on 3.8.0 but works on 3.8.1
    """
    return (
        sys.version_info[:2] == (2, 7)
        or (sys.version_info[:2] == (3, 5) and sys.version_info[:3] > (3, 5, 7))
        or (sys.version_info[:2] == (3, 6) and sys.version_info[:3] > (3, 6, 8))
        or (sys.version_info[:2] == (3, 7) and sys.version_info[:3] > (3, 7, 4))
        or (sys.version_info[:2] == (3, 8) and sys.version_info[:3] > (3, 8, 0))
        or sys.version_info[:2] >= (3, 9)
    )
