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
      - For more information, please read the documentation U(https://mysupport.netapp.com/NOW/download/software/nmsdk/9.4/).
      - Two authentication methods are supported
      - 1. basic authentication, using username and password,
      - 2. SSL certificate authentication, using a ssl client cert file, and optionally a private key file.
      - To use a certificate, the certificate must have been installed in the ONTAP cluster, and cert authentication must have been enabled.
      type: str
      aliases: [ user ]
  password:
      description:
      - Password for the specified user.
      type: str
      aliases: [ pass ]
  cert_filepath:
      description:
      - path to SSL client cert file (.pem).
      - not supported with python 2.6.
      type: str
      version_added: 20.6.0
  key_filepath:
      description:
      - path to SSL client key file.
      type: str
      version_added: 20.6.0
  https:
      description:
      - Enable and disable https.
      - Ignored when using REST as only https is supported.
      - Ignored when using SSL certificate authentication as it requires SSL.
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
      - always -- will always use the REST API
      - never -- will always use the ZAPI
      - auto -- will try to use the REST Api
      default: auto
      type: str
  feature_flags:
      description:
      - Enable or disable a new feature.
      - This can be used to enable an experimental feature or disable a new feature that breaks backward compatibility.
      - Supported keys and values are subject to change without notice.  Unknown keys are ignored.
      type: dict
      version_added: "20.5.0"


requirements:
  - Ansible 2.9
  - Python3 netapp-lib (2018.11.13) or later. Install using 'pip install netapp-lib'
  - netapp-lib 2020.3.12 is strongly recommended as it provides better error reporting for connection issues.
  - A physical or virtual clustered Data ONTAP system. The modules support Data ONTAP 9.1 and onward.
  - REST support requires ONTAP 9.6 or later.
  - To enable http on the cluster you must run the following commands 'set -privilege advanced;' 'system services web modify -http-enabled true;'

notes:
  - The modules prefixed with na_ontap are built to support the ONTAP storage platform.

'''
    # Documentation fragment for ONTAP (na_ontap) peer options
    NA_ONTAP_PEER = r'''
options:
  peer_options:
    version_added: 21.8.0
    description:
      - IP address and connection options for the peer system.
      - If any if these options is not specified, the corresponding source option is used.
    type: dict
    suboptions:
      hostname:
        description:
          - The hostname or IP address of the ONTAP instance.
        type: str
        required: true
      username:
        description:
          - Username when using basic authentication.
        type: str
        aliases: [ user ]
      password:
        description:
          - Password for the specified user.
        type: str
        aliases: [ pass ]
      cert_filepath:
        description:
          - path to SSL client cert file (.pem).
        type: str
      key_filepath:
        description:
          - path to SSL client key file.
        type: str
      https:
        description:
          - Enable and disable https.
        type: bool
      validate_certs:
        description:
          - If set to C(no), the SSL certificates will not be validated.
          - This should only set to C(False) used on personally controlled sites using self-signed certificates.
        type: bool
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
          - always -- will always use the REST API
          - never -- will always use the ZAPI
          - auto -- will try to use the REST Api
        type: str

'''
