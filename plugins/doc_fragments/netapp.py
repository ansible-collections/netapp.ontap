# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Sumit Kumar <sumit4@netapp.com>, chris Archibald <carchi@netapp.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


class ModuleDocFragment(object):

    DOCUMENTATION = r'''
options:
  - See respective platform section for more details
requirements:
  - See respective platform section for more details
notes:
  - Ansible modules are available for the following NetApp Storage Platforms: E-Series, ONTAP, SolidFire
'''

    # Documentation fragment for ONTAP (na_ontap)
    NA_ONTAP = r'''
options:
  hostname:
      description:
      - The hostname or IP address of the ONTAP instance.
      type: str
      required: true
  username:
      description:
      - This can be a Cluster-scoped or SVM-scoped account, depending on whether a Cluster-level or SVM-level API is required.
        For more information, please read the documentation U(https://mysupport.netapp.com/NOW/download/software/nmsdk/9.4/).
      type: str
      required: true
      aliases: [ user ]
  password:
      description:
      - Password for the specified user.
      type: str
      required: true
      aliases: [ pass ]
  https:
      description:
      - Enable and disable https
      type: bool
      default: no
  validate_certs:
      description:
      - If set to C(no), the SSL certificates will not be validated.
      - This should only set to C(False) used on personally controlled sites using self-signed certificates.
      type: bool
      default: yes
  http_port:
      description:
      - Override the default port (80 or 443) with this port
      type: int
  ontapi:
      description:
      - The ontap api version to use
      type: int
  use_rest:
      description:
      - REST API if supported by the target system for all the resources and attributes the module requires. Otherwise will revert to ZAPI.
      - Always -- will always use the REST API
      - Never -- will always use the ZAPI
      - Auto -- will try to use the REST Api
      default: Auto
      choices: ['Never', 'Always', 'Auto']
      type: str


requirements:
  - A physical or virtual clustered Data ONTAP system. The modules support Data ONTAP 9.1 and onward
  - Ansible 2.6
  - Python2 netapp-lib (2017.10.30) or later. Install using 'pip install netapp-lib'
  - Python3 netapp-lib (2018.11.13) or later. Install using 'pip install netapp-lib'
  - To enable http on the cluster you must run the following commands 'set -privilege advanced;' 'system services web modify -http-enabled true;'

notes:
  - The modules prefixed with na\\_ontap are built to support the ONTAP storage platform.

'''
