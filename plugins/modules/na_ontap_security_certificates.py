#!/usr/bin/python

# (c) 2020-2026, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
na_ontap_security_certificates
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''

module: na_ontap_security_certificates
short_description: NetApp ONTAP manage security certificates.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '20.7.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansible-team@netapp.com>

description:
- Install or delete security certificates on ONTAP.  (Create and sign will come in a second iteration)

options:

  state:
    description:
    - Whether the specified security certificate should exist or not.
    choices: ['present', 'absent']
    default: 'present'
    type: str

  common_name:
    description:
    - Common name of the certificate.
    - Required for create and install.
    - If name is present, ignored for sign and delete.
    - If name is absent or ignored, required for sign and delete.
    type: str

  name:
    description:
    - The unique name of the security certificate per SVM.
    - This parameter is not supported for ONTAP 9.6 or 9.7, as the REST API does not support it.
    - If present with ONTAP 9.6 or 9.7, it is ignored by default, see I(ignore_name_if_not_supported).
    - It is strongly recommended to use name for newer releases of ONTAP.
    type: str

  svm:
    description:
    - The name of the SVM (vserver).
    - If present, the certificate is installed in the SVM.
    - If absent, the certificate is installed in the cluster.
    type: str
    aliases:
    - vserver

  type:
    description:
    - Type of certificate
    - Required for create and install.
    - If name is present, ignored for sign and delete.
    - If name is absent or ignored, required for sign and delete.
    choices: ['client', 'server', 'client_ca', 'server_ca', 'root_ca']
    type: str

  public_certificate:
    description:
    - Public key certificate in PEM format.
    - Required when installing a certificate.  Ignored otherwise.
    type: str

  private_key:
    description:
    - Private key certificate in PEM format.
    - Required when installing a CA-signed certificate.  Ignored otherwise.
    type: str

  signing_request:
    description:
    - If present, the certificate identified by name and svm is used to sign the request.
    - A signed certificate is returned.
    type: str

  expiry_time:
    description:
    - Certificate expiration time. Specifying an expiration time is recommended when creating a certificate.
    - Can be provided when signing a certificate.
    type: str

  key_size:
    description:
    - Key size of the certificate in bits. Specifying a strong key size is recommended when creating a certificate.
    - Ignored for sign and delete.
    type: int

  hash_function:
    description:
    - Hashing function. Can be provided when creating a self-signed certificate, when signing a certificate,
      or when generating a certificate signing request.
    - Allowed values are sha1, sha224, sha256, sha384, and sha512.
    type: str
    default: sha256
    choices: ['sha1', 'sha224', 'sha256', 'sha384', 'sha512']

  intermediate_certificates:
    description:
    - Chain of intermediate Certificates in PEM format.
    - Only valid when installing a certificate.
    type: list
    elements: str

  ignore_name_if_not_supported:
    description:
    - ONTAP 9.6 and 9.7 REST API does not support I(name).
    - If set to true, no error is reported if I(name) is present, and I(name) is not used.
    type: bool
    default: true
    version_added: '20.8.0'

  algorithm:
    description:
    - Asymmetric Encryption Algorithm.
    type: str
    default: rsa
    choices: ['rsa','ec']
    version_added: '23.5.0'

  security_strength:
    description:
    - Security strength of the certificate in bits.
    type: int
    default: 112
    choices: [112, 128, 192]
    version_added: '23.5.0'

  subject_alternatives:
    description:
    - Subject alternative names for the certificate.
    type: dict
    suboptions:
      email:
        description:
        - List of email subject alternative names.
        type: list
        elements: str
      dns:
        description:
        - List of DNS subject alternative names.
        type: list
        elements: str
      ip:
        description:
        - List of IP subject alternative names.
        type: list
        elements: str
      uri:
        description:
        - List of URI subject alternative names.
        type: list
        elements: str
    version_added: '23.5.0'

  subject_name:
    description:
    - Subject name details of the certificate. The format is a list of comma separated key=value pairs.
    type: str
    version_added: '23.5.0'

  extended_key_usages:
    description:
    - A list of extended key usage extensions.
    type: list
    elements: str
    choices: ['serverauth', 'clientauth', 'timestamping', 'dvcs', 'ocspsigning', 'codesigning', 'emailprotection', 'anyextendedkeyusage', 'critical']
    version_added: '23.5.0'

  generate_csr:
    description:
    - Generate a Certificate Signing Request (CSR) instead of creating or installing a certificate.
    - When true, the CSR is generated based on the provided parameters and returned in the output.
    type: bool
    default: false
    version_added: '23.5.0'

  key_usages:
    description:
    - A list of key usage extensions.
    type: list
    elements: str
    choices: ['digitalsignature', 'nonrepudiation', 'keyencipherment', 'dataencipherment',
              'keyagreement', 'keycertsign', 'crlsign', 'encipheronly', 'decipheronly', 'critical']
    version_added: '23.5.0'

notes:
  - supports check mode.
  - only supports REST. Requires ONTAP 9.6 or later, ONTAP 9.8 or later is recommended.
  - Module is not idempotent when generating CSR.
'''

EXAMPLES = """
- name: install certificate
  netapp.ontap.na_ontap_security_certificates:
    # <<: *cert_login
    common_name: "{{ ontap_cert_common_name }}"
    name: "{{ ontap_cert_name }}"
    public_certificate: "{{ ssl_certificate }}"
    type: client_ca
    svm: "{{ vserver }}"

# ignore svm option for cluster/admin vserver.
- name: install certificate in cluster vserver.
  netapp.ontap.na_ontap_security_certificates:
    # <<: *cert_login
    common_name: "{{ ontap_cert_common_name }}"
    name: "{{ ontap_cert_name }}"
    public_certificate: "{{ ssl_certificate }}"
    type: client_ca

- name: create certificate
  netapp.ontap.na_ontap_security_certificates:
    # <<: *cert_login
    common_name: "{{ ontap_cert_root_common_name }}"
    name: "{{ ontap_cert_name }}"
    type: root_ca
    svm: "{{ vserver }}"
    expiry_time: P365DT     # one year

- name: Create Certificate Signing Request
  tags: sign_request
  netapp.ontap.na_ontap_security_certificates:
    # <<: *login
    generate_csr: true
    subject_name: "C=US,O=NTAP,CN=test.domain.com"
    security_strength: 128
    hash_function: "sha256"
    algorithm: "rsa"
    name: "test_cert"
    key_usages: "digitalsignature,keyencipherment"
    extended_key_usages: "serverauth,clientauth"
    subject_alternatives:
      dns:
        - main.example.com
        - www.example.com
        - api.example.com
      email:
        - admin@example.com
        - security@example.com
      ip:
        - 192.168.1.100
        - 10.0.0.50
      uri:
        - https://example.com
        - https://api.example.com

- name: sign certificate using newly create certificate
  tags: sign_request
  netapp.ontap.na_ontap_security_certificates:
    # <<: *login
    name: "{{ ontap_cert_name }}"
    svm: "{{ vserver }}"
    signing_request: |
      -----BEGIN CERTIFICATE REQUEST-----
      MIIChDCCAWwCAQAwPzELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAkNBMRIwEAYDVQQH
      DAlTdW5ueXZhbGUxDzANBgNVBAoMBk5ldEFwcDCCASIwDQYJKoZIhvcNAQEBBQAD
      ggEPADCCAQoCggEBALgXCj6Si/I4xLdV7wjWYTbt8jY20fQOjk/4E7yBT1vFBflE
      ks6YDc6dhC2G18cnoj9E3DiR8lIHPoAlFB/VmBNDev3GZkbFlrbV7qYmf8OEx2H2
      tAefgSP0jLmCHCN1yyhJoCG6FsAiD3tf6yoyFF6qS9ureGL0tCJJ/osx64WzUz+Q
      EN8lx7VSxriEFMSjreXZDhUFaCdIYKKRENuEWyYvdy5cbBmczhuM8EP6peOVv5Hm
      BJzPUDkq7oTtEHmttpATq2Y92qzNzETO0bXN5X/93AWri8/yEXdX+HEw1C/omtsE
      jGsCXrCrIJ+DgUdT/GHNdBWlXl/cWGtEgEQ4vrUCAwEAAaAAMA0GCSqGSIb3DQEB
      CwUAA4IBAQBjZNoQgr/JDm1T8zyRhLkl3zw4a16qKNu/MS7prqZHLVQgrptHRegU
      Hbz11XoHfVOdbyuvtzEe95QsDd6FYCZ4qzZRF3se4IjMeqwdQZ5WP0/GFiwM8Uln
      /0TCWjt759XMeUX7+wgOg5NRjJ660eWMXzu/UJf+vZO0Q2FiPIr13JvvY3TjT+9J
      UUtK4r9PaUuOPN2YL9IQqSD3goh8302Qr3nBXUgjeUGLkgfUM5S39apund2hyTX2
      JCLQsKr88pwU9iDho2tHLv/2QgLwNZLPu8V+7IGu6G4vB28lN4Uy7xbhxFOKtyWu
      fK4sEdTw3B/aDN0tB8MHFdPYycNZsEac
      -----END CERTIFICATE REQUEST-----
    expiry_time: P180DT

- name: delete certificate
  netapp.ontap.na_ontap_security_certificates:
    # <<: *cert_login
    state: absent
    name: "{{ ontap_cert_name }}"
    svm: "{{ vserver }}"

# For ONTAP 9.6 or 9.7, use common_name and type, in addition to, or in lieu of name
- name: install certificate
  netapp.ontap.na_ontap_security_certificates:
    # <<: *cert_login
    common_name: "{{ ontap_cert_common_name }}"
    public_certificate: "{{ ssl_certificate }}"
    type: client_ca
    svm: "{{ vserver }}"

- name: create certificate
  netapp.ontap.na_ontap_security_certificates:
    # <<: *cert_login
    common_name: "{{ ontap_cert_root_common_name }}"
    type: root_ca
    svm: "{{ vserver }}"
    expiry_time: P365DT     # one year

- name: sign certificate using newly create certificate
  tags: sign_request
  netapp.ontap.na_ontap_security_certificates:
    # <<: *login
    common_name: "{{ ontap_cert_root_common_name }}"
    type: root_ca
    svm: "{{ vserver }}"
    signing_request: |
      -----BEGIN CERTIFICATE REQUEST-----
      MIIChDCCAWwCAQAwPzELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAkNBMRIwEAYDVQQH
      DAlTdW5ueXZhbGUxDzANBgNVBAoMBk5ldEFwcDCCASIwDQYJKoZIhvcNAQEBBQAD
      ggEPADCCAQoCggEBALgXCj6Si/I4xLdV7wjWYTbt8jY20fQOjk/4E7yBT1vFBflE
      ks6YDc6dhC2G18cnoj9E3DiR8lIHPoAlFB/VmBNDev3GZkbFlrbV7qYmf8OEx2H2
      tAefgSP0jLmCHCN1yyhJoCG6FsAiD3tf6yoyFF6qS9ureGL0tCJJ/osx64WzUz+Q
      EN8lx7VSxriEFMSjreXZDhUFaCdIYKKRENuEWyYvdy5cbBmczhuM8EP6peOVv5Hm
      BJzPUDkq7oTtEHmttpATq2Y92qzNzETO0bXN5X/93AWri8/yEXdX+HEw1C/omtsE
      jGsCXrCrIJ+DgUdT/GHNdBWlXl/cWGtEgEQ4vrUCAwEAAaAAMA0GCSqGSIb3DQEB
      CwUAA4IBAQBjZNoQgr/JDm1T8zyRhLkl3zw4a16qKNu/MS7prqZHLVQgrptHRegU
      Hbz11XoHfVOdbyuvtzEe95QsDd6FYCZ4qzZRF3se4IjMeqwdQZ5WP0/GFiwM8Uln
      /0TCWjt759XMeUX7+wgOg5NRjJ660eWMXzu/UJf+vZO0Q2FiPIr13JvvY3TjT+9J
      UUtK4r9PaUuOPN2YL9IQqSD3goh8302Qr3nBXUgjeUGLkgfUM5S39apund2hyTX2
      JCLQsKr88pwU9iDho2tHLv/2QgLwNZLPu8V+7IGu6G4vB28lN4Uy7xbhxFOKtyWu
      fK4sEdTw3B/aDN0tB8MHFdPYycNZsEac
      -----END CERTIFICATE REQUEST-----
    expiry_time: P180DT

- name: delete certificate
  netapp.ontap.na_ontap_security_certificates:
    # <<: *cert_login
    state: absent
    common_name: "{{ ontap_cert_root_common_name }}"
    type: root_ca
    name: "{{ ontap_cert_name }}"
    svm: "{{ vserver }}"

- name: install certificate - server certificate with chain of intermediate certificates
  netapp.ontap.na_ontap_security_certificates:
    # <<: *cert_login
    common_name: "{{ ontap_cert_common_name }}"
    public_certificate: "{{ ssl_certificate }}"
    type: server
    svm: "{{ vserver }}"
    private_key: "-----BEGIN CERTIFICATE-----\nPrivate Key\n-----END CERTIFICATE-----"
    intermediat_certificates: ["-----BEGIN CERTIFICATE-----\nIntermediate certificate1\n-----END CERTIFICATE-----",
                               "-----BEGIN CERTIFICATE-----\nIntermediate certificate2\n-----END CERTIFICATE-----",
                               "-----BEGIN CERTIFICATE-----\nRoot certificate\n-----END CERTIFICATE-----"]
"""

RETURN = """
ontap_info:
    description: Returns public_certificate when signing, empty for create, install, and delete.
    returned: always
    type: dict
    sample: '{
        "ontap_info": {
            "public_certificate": "-----BEGIN CERTIFICATE-----\n........-----END CERTIFICATE-----\n"
            }
        }'
"""

from ansible.module_utils.basic import AnsibleModule
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils import rest_vserver


class NetAppOntapSecurityCertificates:
    ''' object initialize and class methods '''

    def __init__(self):
        self.use_rest = False
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            common_name=dict(required=False, type='str'),
            name=dict(required=False, type='str'),
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            type=dict(required=False, choices=['client', 'server', 'client_ca', 'server_ca', 'root_ca']),
            svm=dict(required=False, type='str', aliases=['vserver']),
            public_certificate=dict(required=False, type='str'),
            private_key=dict(required=False, type='str', no_log=True),
            signing_request=dict(required=False, type='str'),
            expiry_time=dict(required=False, type='str'),
            key_size=dict(required=False, type='int'),
            intermediate_certificates=dict(required=False, type='list', elements='str'),
            ignore_name_if_not_supported=dict(required=False, type='bool', default=True),

            generate_csr=dict(required=False, type='bool', default=False),
            subject_name=dict(required=False, type='str'),
            subject_alternatives=dict(required=False, type='dict', options=dict(
                email=dict(required=False, type='list', elements='str'),
                dns=dict(required=False, type='list', elements='str'),
                ip=dict(required=False, type='list', elements='str'),
                uri=dict(required=False, type='list', elements='str')
            )),
            security_strength=dict(required=False, type='int', default=112, choices=[112, 128, 192]),
            hash_function=dict(required=False, type='str', default='sha256',
                               choices=['sha1', 'sha224', 'sha256', 'sha384', 'sha512']),
            algorithm=dict(required=False, type='str', default='rsa', choices=['rsa', 'ec']),
            key_usages=dict(required=False, type='list', elements='str',
                            choices=['digitalsignature', 'nonrepudiation', 'keyencipherment', 'dataencipherment',
                                     'keyagreement', 'keycertsign', 'crlsign', 'encipheronly', 'decipheronly', 'critical']),
            extended_key_usages=dict(required=False, type='list', elements='str',
                                     choices=['serverauth', 'clientauth', 'timestamping', 'dvcs', 'ocspsigning', 'codesigning',
                                              'emailprotection', 'anyextendedkeyusage', 'critical']),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        if self.parameters.get('name') is None and (self.parameters.get('common_name') is None or self.parameters.get('type') is None):
            error = "Error: 'name' or ('common_name' and 'type') are required parameters."
            self.module.fail_json(msg=error)
        # ONTAP 9.6 and 9.7 do not support name.  We'll change this to True if we detect an issue.
        self.ignore_name_param = False
        self.rest_api = netapp_utils.OntapRestAPI(self.module)
        self.use_rest = self.rest_api.is_rest()
        # API should be used for ONTAP 9.6 or higher
        self.rest_api.fail_if_not_rest_minimum_version('na_ontap_security_certificates', 9, 6)

        if not self.use_rest:
            self.module.fail_json(msg="This module require REST with ONTAP 9.6 or higher")
        if self.parameters.get('generate_csr') and not self.rest_api.meets_rest_minimum_version(self.use_rest, 9, 8, 0):
            self.module.fail_json(msg=self.rest_api.options_require_ontap_version('generate_csr', '9.8', use_rest=self.use_rest))

    def get_certificate(self):
        """
        Fetch uuid if certificate exists.
        NOTE: because of a bug in ONTAP 9.6 and 9.7, name is not supported. We are
        falling back to using common_name and type, but unicity is not guaranteed.
        :return:
            Dictionary if certificate with same name is found
            None if not found
        """
        # REST allows setting cluster/admin svm in create certificate, but no records returned in GET.
        # error if data svm not found
        if 'svm' in self.parameters:
            rest_vserver.get_vserver_uuid(self.rest_api, self.parameters['svm'], self.module, True)

        error = "'name' or ('common_name', 'type') are required."
        for key in ('name', 'common_name'):
            if self.parameters.get(key) is None:
                continue
            data = {'fields': 'uuid',
                    key: self.parameters[key],
                    }
            if self.parameters.get('svm') is not None:
                data['svm.name'] = self.parameters['svm']
            else:
                data['scope'] = 'cluster'
            if key == 'common_name':
                if self.parameters.get('type') is not None:
                    data['type'] = self.parameters['type']
                else:
                    error = "When using 'common_name', 'type' is required."
                    break

            api = "security/certificates"
            message, error = self.rest_api.get(api, data)
            if error:
                try:
                    name_not_supported_error = (key == 'name') and (error['message'] == 'Unexpected argument "name".')
                except (KeyError, TypeError):
                    name_not_supported_error = False
                if name_not_supported_error:
                    if self.parameters['ignore_name_if_not_supported'] and self.parameters.get('common_name') is not None:
                        # let's attempt a retry using common_name
                        self.ignore_name_param = True
                        continue
                    error = "ONTAP 9.6 and 9.7 do not support 'name'.  Use 'common_name' and 'type' as a work-around."
            # report success, or any other error as is
            break

        if error:
            self.module.fail_json(msg='Error calling API: %s - %s' % (api, error))

        if len(message['records']) == 1:
            return message['records'][0]
        if len(message['records']) > 1:
            error = 'Duplicate records with same common_name are preventing safe operations: %s' % repr(message)
            self.module.fail_json(msg=error)
        return None

    def create_or_install_certificate(self, validate_only=False):
        """
        Create or install certificate
        :return: message (should be empty dict)
        """
        required_keys = ['type', 'common_name']
        if validate_only:
            if not set(required_keys).issubset(set(self.parameters.keys())):
                self.module.fail_json(msg='Error creating or installing certificate: one or more of the following options are missing: %s'
                                      % (', '.join(required_keys)))
            return

        optional_keys = ['public_certificate', 'private_key', 'expiry_time', 'key_size', 'hash_function', 'intermediate_certificates']
        if not self.ignore_name_param:
            optional_keys.append('name')
        # special key: svm

        body = {}
        if self.parameters.get('svm') is not None:
            body['svm'] = {'name': self.parameters['svm']}
        for key in required_keys + optional_keys:
            if self.parameters.get(key) is not None:
                body[key] = self.parameters[key]
        params = {
            "return_records": "true"
        }
        api = "security/certificates"
        message, error = self.rest_api.post(api, body, params)
        if error:
            if self.parameters.get('svm') is None and error.get('target') == 'uuid':
                error['target'] = 'cluster'
            if error.get('message') == 'duplicate entry':
                error['message'] += '.  Same certificate may already exist under a different name.'
            self.module.fail_json(msg="Error creating or installing certificate: %s" % error)
        return message

    def generate_csr_rest(self):
        """
        Generate Certificate Signing Request using REST API
        """
        api = 'security/certificate-signing-request'

        body = {}
        if self.parameters.get('subject_name'):
            body['subject_name'] = self.parameters['subject_name']
        if self.parameters.get('subject_alternatives'):
            body['subject_alternatives'] = self.parameters['subject_alternatives']
        # Validate required parameters
        if not body.get('subject_name') and not body.get('subject_alternatives'):
            self.module.fail_json(msg="Either subject_name or subject_alternatives must be specified for CSR generation")
        for key in ('security_strength', 'hash_function', 'algorithm', 'key_usages', 'extended_key_usages'):
            if key in self.parameters:
                body[key] = self.parameters[key]
        csr_response, error = self.rest_api.post(api, body)
        if error:
            self.module.fail_json(msg="Error generating CSR: %s" % error)
        return csr_response

    def validate_csr_parameters(self):
        """
        Validate CSR-specific parameters
        """
        if not self.parameters.get('subject_name') and not self.parameters.get('subject_alternatives'):
            self.module.fail_json(
                msg="Either subject_name or subject_alternatives must be specified when generate_csr=true"
            )

        if self.parameters.get('algorithm') == 'ec' and self.parameters.get('security_strength') not in [128, 192]:
            self.module.fail_json(
                msg="Value of at least 128 is necessary when using EC algorithm if the certificate is to be used in the context of TLSv1.3."
            )

    def sign_certificate(self, uuid):
        """
        sign certificate
        :return: a dictionary with key "public_certificate"
        """
        api = "security/certificates/%s/sign" % uuid
        body = {'signing_request': self.parameters['signing_request']}
        optional_keys = ['expiry_time', 'hash_function']
        for key in optional_keys:
            if self.parameters.get(key) is not None:
                body[key] = self.parameters[key]
        params = {
            "return_records": "true"
        }
        message, error = self.rest_api.post(api, body, params)
        if error:
            self.module.fail_json(msg="Error signing certificate: %s" % error)
        return message

    def delete_certificate(self, uuid):
        """
        Delete certificate
        :return: message (should be empty dict)
        """
        api = "security/certificates/%s" % uuid
        message, error = self.rest_api.delete(api)
        if error:
            self.module.fail_json(msg="Error deleting certificate: %s" % error)
        return message

    def apply(self):
        """
        Apply action to create/install/sign/delete certificate
        :return: None
        """
        # TODO: add telemetry for REST

        if self.parameters.get('generate_csr'):
            self.validate_csr_parameters()
            generated_csr = self.generate_csr_rest()
            self.module.exit_json(
                changed=True,
                msg="CSR generated successfully",
                csr=generated_csr.get('csr', ''),
                private_key=generated_csr.get('generated_private_key', '')
            )

        current = self.get_certificate()
        cd_action = self.na_helper.get_cd_action(current, self.parameters)
        message = None
        if self.parameters.get('signing_request') is not None:
            error = None
            if self.parameters['state'] == 'absent':
                error = "'signing_request' is not supported with 'state' set to 'absent'"
            elif current is None:
                scope = 'cluster' if self.parameters.get('svm') is None else "svm: %s" % self.parameters.get('svm')
                error = "signing certificate with name '%s' not found on %s" % (self.parameters.get('name'), scope)
            elif cd_action is not None:
                error = "'signing_request' is exclusive with other actions: create, install, delete"
            if error is not None:
                self.module.fail_json(msg=error)
            cd_action = 'sign'
            self.na_helper.changed = True

        if self.na_helper.changed and cd_action == 'create':
            # validate as much as we can in check_mode or not
            self.create_or_install_certificate(validate_only=True)

        if self.na_helper.changed and not self.module.check_mode:
            if cd_action == 'create':
                message = self.create_or_install_certificate()
            elif cd_action == 'sign':
                message = self.sign_certificate(current['uuid'])
            elif cd_action == 'delete':
                message = self.delete_certificate(current['uuid'])

        results = netapp_utils.generate_result(self.na_helper.changed, cd_action, extra_responses={'ontap_info': message})
        self.module.exit_json(**results)


def main():
    """
    Create instance and invoke apply
    :return: None
    """
    sec_cert = NetAppOntapSecurityCertificates()
    sec_cert.apply()


if __name__ == '__main__':
    main()
