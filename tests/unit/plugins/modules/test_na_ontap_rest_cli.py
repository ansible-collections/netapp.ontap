# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_rest_cli'''

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat import unittest
from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args,\
    AnsibleFailJson, AnsibleExitJson, patch_ansible

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_rest_cli \
    import NetAppONTAPCommandREST as rest_cli_module, main  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


# REST API canned responses when mocking send_request
SRR = {
    # common responses
    'is_rest': (200, {}, None),
    'empty_good': (200, {}, None),
    'end_of_sequence': (500, None, "Ooops, the UT needs one more SRR response"),
    'generic_error': (400, None, "Expected error"),
    # module specific response
    'allow': (200, {'Allow': ['GET', 'WHATEVER']}, None)
}


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_job_schedule '''

    def mock_args(self):
        return {
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!',
            'https': False,
            'command': 'volume',
            'verb': 'GET',
            'params': {'fields': 'size,percent_used'}
        }

    def get_cli_mock_object(self):
        # For rest, mocking is achieved through side_effect
        return rest_cli_module()

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            rest_cli_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_cli(self, mock_request):
        data = dict(self.mock_args())
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['empty_good'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_cli_mock_object().apply()
        assert exc.value.args[0]['changed']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_rest_cli_options(self, mock_request):
        data = dict(self.mock_args())
        data['verb'] = 'OPTIONS'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['allow'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_cli_mock_object().apply()
        assert exc.value.args[0]['changed']
        assert 'Allow' in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_connection_error(self, mock_request):
        data = dict(self.mock_args())
        data['verb'] = 'OPTIONS'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            self.get_cli_mock_object().apply()
        msg = "failed to connect to REST over test: ['Expected error'].  Use na_ontap_command for non-rest CLI."
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def check_verb(self, verb, mock_request):
        data = dict(self.mock_args())
        data['verb'] = verb
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['allow'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_cli_mock_object().apply()
        assert exc.value.args[0]['changed']
        assert 'Allow' in exc.value.args[0]['msg']
        assert mock_request.call_args[0][0] == verb

    def test_verbs(self):
        for verb in ['POST', 'DELETE', 'PATCH', 'OPTIONS', 'PATCH']:
            self.check_verb(verb)

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_verb(self, mock_request):
        data = dict(self.mock_args())
        data['verb'] = 'GET'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['end_of_sequence']
        ]
        uut = self.get_cli_mock_object()
        with pytest.raises(AnsibleFailJson) as exc:
            uut.verb = 'INVALID'
            uut.run_command()
        msg = 'Error: unexpected verb INVALID'
        assert msg in exc.value.args[0]['msg']

    @patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.OntapRestAPI.send_request')
    def test_negative_error(self, mock_request):
        data = dict(self.mock_args())
        data['verb'] = 'GET'
        set_module_args(data)
        mock_request.side_effect = [
            SRR['is_rest'],
            SRR['generic_error'],
            SRR['end_of_sequence']
        ]
        with pytest.raises(AnsibleFailJson) as exc:
            main()
        msg = 'Error: Expected error'
        assert msg in exc.value.args[0]['msg']
