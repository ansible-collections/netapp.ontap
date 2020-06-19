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
    required: true
    description:
    - Common name of the certificate.
    - Required for create, install, or sign.
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
    - Required for create, install, or sign.
    choices: ['client', 'server', 'client_ca', 'server_ca', 'root_ca']
    type: str

  public_certificate:
    description:
    - Public key certificate in PEM format.
    - Required when installing a certificate.
    type: str

  private_key:
    description:
    - Private key certificate in PEM format.
    - Required when installing a CA-signed certificate.
    type: str
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

- name: delete certificate
  na_ontap_security_certificates:
    # <<: *cert_login
    state: absent
    name: "{{ ontap_cert_name }}"
    svm: "{{ vserver }}"
"""

RETURN = """

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
        with open('/tmp/cert.txt', 'a') as f:
            f.write(repr(message))
            f.write('\n')
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
            self.module.fail_json(msg=error)
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
            self.module.fail_json(msg=error)
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

        if self.na_helper.changed:
            if self.module.check_mode:
                pass
            else:
                if cd_action == 'create':
                    message = self.create_or_install_certificate()
                elif cd_action == 'delete':
                    uuid = current['uuid']
                    message = self.delete_certificate(uuid)

        results = {'changed': self.na_helper.changed}
        if message:
            results['msg'] = message
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
