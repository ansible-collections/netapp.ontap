#!/usr/bin/python

# (c) 2020, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''

module: na_ontap_security_certificates
short_description: NetApp ONTAP manage security certificates.
extends_documentation_fragment:
    - netapp.ontap.netapp.na_ontap
version_added: '20.7.0'
author: NetApp Ansible Team (@carchi8py) <ng-ansibleteam@netapp.com>

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
    - Ignored for sign and delete.
    type: str

  name:
    required: true
    description:
    - The unique name of the security certificate per SVM.
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
    - Ignored for sign and delete.
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
    - Hashing function. Can be provided when creating a self-signed certificate or when signing a certificate.
    - Allowed values for create and sign are sha256, sha224, sha384, sha512.
    type: str

  intermediate_certificates:
    description:
    - Chain of intermediate Certificates in PEM format.
    - Only valid when installing a certificate.
    type: list
'''

EXAMPLES = """
- name: install certificate
  na_ontap_security_certificates:
    # <<: *cert_login
    common_name: "{{ ontap_cert_common_name }}"
    name: "{{ ontap_cert_name }}"
    public_certificate: "{{ ssl_certificate }}"
    type: client_ca
    svm: "{{ vserver }}"

- name: create certificate
  na_ontap_security_certificates:
    # <<: *cert_login
    common_name: "{{ ontap_cert_root_common_name }}"
    name: "{{ ontap_cert_name }}"
    type: root_ca
    svm: "{{ vserver }}"
    expiry_time: P365DT     # one year

- name: sign certificate using newly create certificate
  tags: sign_request
  na_ontap_security_certificates:
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
  na_ontap_security_certificates:
    # <<: *cert_login
    state: absent
    name: "{{ ontap_cert_name }}"
    svm: "{{ vserver }}"
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
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.module_utils.netapp_module import NetAppModule
from ansible_collections.netapp.ontap.plugins.module_utils.netapp import OntapRestAPI


class NetAppOntapSecurityCertificates(object):
    ''' object initialize and class methods '''

    def __init__(self):
        self.use_rest = False
        self.argument_spec = netapp_utils.na_ontap_host_argument_spec()
        self.argument_spec.update(dict(
            common_name=dict(required=False, type='str'),
            name=dict(required=True, type='str'),
            state=dict(required=False, choices=['present', 'absent'], default='present'),
            type=dict(required=False, choices=['client', 'server', 'client_ca', 'server_ca', 'root_ca']),
            svm=dict(required=False, type='str', aliases=['vserver']),
            public_certificate=dict(required=False, type='str'),
            private_key=dict(required=False, type='str'),
            signing_request=dict(required=False, type='str'),
            expiry_time=dict(required=False, type='str'),
            key_size=dict(required=False, type='int'),
            hash_function=dict(required=False, type='str'),
            intermediate_certificates=dict(required=False, type='list'),
        ))

        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )

        self.na_helper = NetAppModule()
        self.parameters = self.na_helper.set_parameters(self.module.params)

        # API should be used for ONTAP 9.6 or higher
        self.restApi = OntapRestAPI(self.module)
        if self.restApi.is_rest():
            self.use_rest = True
        else:
            self.module.fail_json(msg="this module requires ONTAP 9.6 or later")

    def get_certificate(self):
        """
        Fetch uuid if certificate exists.
        :return:
            Dictionary if certificate with same name is found
            None if not found
        """
        data = {'fields': 'uuid,name',
                'name': self.parameters['name'],
                }
        if self.parameters.get('svm') is not None:
            data['svm.name'] = self.parameters['svm']
        api = "security/certificates"
        message, error = self.restApi.get(api, data)
        if error:
            self.module.fail_json(msg=error)
        if len(message['records']) != 0:
            return message['records'][0]
        return None

    def create_or_install_certificate(self):
        """
        Create or install certificate
        :return: message (should be empty dict)
        """
        required_keys = ['type', 'name', 'common_name']
        optional_keys = ['public_certificate', 'private_key', 'expiry_time', 'key_size', 'hash_function']
        # special key: svm

        if not set(required_keys).issubset(set(self.parameters.keys())):
            self.module.fail_json(msg='Error creating or installing certificate %s: one or more of the following options are missing '
                                      '%s' % (self.parameters['name'], ', '.join(required_keys)))

        data = dict()
        if self.parameters.get('svm') is not None:
            data['svm'] = {'name': self.parameters['svm']}
        for key in required_keys + optional_keys:
            if self.parameters.get(key) is not None:
                data[key] = self.parameters[key]
        api = "security/certificates"
        message, error = self.restApi.post(api, data)
        if error:
            if self.parameters.get('svm') is None and error.get('target') == 'uuid':
                error['target'] = 'cluster'
            if error.get('message') == 'duplicate entry':
                error['message'] += '.  Same certificate may already exist under a different name.'
            self.module.fail_json(msg="Error creating or installing certificate: %s" % error)
        return message

    def sign_certificate(self, uuid):
        """
        sign certificate
        :return: a dictionary with key "public_certificate"
        """
        api = "security/certificates/%s/sign" % uuid
        data = {'signing_request': self.parameters['signing_request']}
        optional_keys = ['expiry_time', 'hash_function']
        for key in optional_keys:
            if self.parameters.get(key) is not None:
                data[key] = self.parameters[key]
        message, error = self.restApi.post(api, data)
        if error:
            self.module.fail_json(msg="Error signing certificate: %s" % error)
        return message

    def delete_certificate(self, uuid):
        """
        Delete certificate
        :return: message (should be empty dict)
        """
        api = "security/certificates/"
        data = {'uuid': uuid}
        message, error = self.restApi.delete(api, data)
        if error:
            self.module.fail_json(msg="Error deleting certificate: %s" % error)
        return message

    def apply(self):
        """
        Apply action to create/install/sign/delete certificate
        :return: None
        """
        # TODO: add telemetry for REST
        # TODO: add sign action, and test creation

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
            self.na_helper.changed = True

        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if cd_action == 'create':
                    message = self.create_or_install_certificate()
                elif cd_action == 'delete':
                    message = self.delete_certificate(current['uuid'])
                elif self.parameters.get('signing_request') is not None:
                    message = self.sign_certificate(current['uuid'])

        results = {'changed': self.na_helper.changed}
        if message:
            results['ontap_info'] = message
        self.module.exit_json(**results)


def main():
    """
    Create instance and invoke apply
    :return: None
    """
    secCert = NetAppOntapSecurityCertificates()
    secCert.apply()


if __name__ == '__main__':
    main()
