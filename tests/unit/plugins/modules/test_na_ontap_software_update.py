# (c) 2018-2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests ONTAP Ansible module: na_ontap_software_update '''

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type
import pytest

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import\
    assert_warning_was_raised, expect_and_capture_ansible_exception, call_main, create_module, create_and_apply, patch_ansible, print_warnings
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import\
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses
from ansible_collections.netapp.ontap.tests.unit.framework.zapi_factory import build_zapi_error, build_zapi_response, zapi_error_message, zapi_responses

import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.plugins.modules.na_ontap_software_update \
    import NetAppONTAPSoftwareUpdate as my_module, main as my_main      # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def cluster_image_info(mixed=False):
    version1 = 'Fattire__9.3.0'
    version2 = version1
    if mixed:
        version2 += '.1'
    return {
        'num-records': 1,
        # composite response, attributes-list for cluster-image-get-iter and attributes for cluster-image-get
        'attributes-list': [
            {'cluster-image-info': {
                'node-id': 'node4test',
                'current-version': version1}},
            {'cluster-image-info': {
                'node-id': 'node4test',
                'current-version': version2}},
        ],
        'attributes': {
            'cluster-image-info': {
                'node-id': 'node4test',
                'current-version': version1
            }},
    }


def software_update_info(status):
    if status == 'async_pkg_get_phase_complete':
        overall_status = 'completed'
    elif status == 'async_pkg_get_phase_running':
        overall_status = 'in_progress'
    else:
        overall_status = status

    return {
        'num-records': 1,
        # 'attributes-list': {'cluster-image-info': {'node-id': node}},
        'progress-status': status,
        'progress-details': 'some_details',
        'failure-reason': 'failure_reason',
        'attributes': {
            'ndu-progress-info': {
                'overall-status': overall_status,
                'completed-node-count': '0',
                'validation-reports': [{
                    'validation-report-info': {
                        'one_check': 'one',
                        'two_check': 'two'
                    }}]}},
    }


cluster_image_validation_report_list = {
    'cluster-image-validation-report-list': [
        {'cluster-image-validation-report-list-info': {
            'required-action': {
                'required-action-info': {
                    'action': 'some_action',
                    'advice': 'some_advice',
                    'error': 'some_error',
                }
            },
            'ndu-check': 'ndu_ck',
            'ndu-status': 'ndu_st',
        }},
        {'cluster-image-validation-report-list-info': {
            'required-action': {
                'required-action-info': {
                    'action': 'other_action',
                    'advice': 'other_advice',
                    'error': 'other_error',
                }
            },
            'ndu-check': 'ndu_ck',
            'ndu-status': 'ndu_st',
        }},
    ],
}


ZRR = zapi_responses({
    'cluster_image_info': build_zapi_response(cluster_image_info()),
    'cluster_image_info_mixed': build_zapi_response(cluster_image_info(True)),
    'software_update_info_running': build_zapi_response(software_update_info('async_pkg_get_phase_running')),
    'software_update_info_complete': build_zapi_response(software_update_info('async_pkg_get_phase_complete')),
    'software_update_info_error': build_zapi_response(software_update_info('error')),
    'cluster_image_validation_report_list': build_zapi_response(cluster_image_validation_report_list),
    'error_18408': build_zapi_error(18408, 'pkg exists!')
})


DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'package_version': 'Fattire__9.3.0',
    'package_url': 'abc.com',
    'https': 'true',
    'stabilize_minutes': 10
}


@patch('time.sleep')
def test_ensure_apply_for_update_called(dont_sleep):
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-package-download', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_complete']),
        ('ZAPI', 'cluster-image-update', ZRR['success']),
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['software_update_info_complete']),
        ('ZAPI', 'cluster-image-package-delete', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never",
        "package_version": "PlinyTheElder",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_ensure_apply_for_update_called_node(dont_sleep):
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-package-download', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_complete']),
        ('ZAPI', 'cluster-image-update', ZRR['success']),
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['software_update_info_complete']),
        ('ZAPI', 'cluster-image-package-delete', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never",
        "nodes": ["node_abc"],
        "package_version": "PlinyTheElder",
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_ensure_apply_for_update_called_idempotent(dont_sleep):
    # image already installed
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),

    ])
    module_args = {
        "use_rest": "never",
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_ensure_apply_for_update_called_idempotent_node(dont_sleep):
    # image already installed
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get', ZRR['cluster_image_info']),

    ])
    module_args = {
        "use_rest": "never",
        "nodes": ["node_abc"],
    }
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_ensure_apply_for_update_called_with_validation(dont_sleep):
    # for validation before update
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-package-download', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_complete']),
        ('ZAPI', 'cluster-image-validate', ZRR['success']),
        ('ZAPI', 'cluster-image-update', ZRR['success']),
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['software_update_info_complete']),
        ('ZAPI', 'cluster-image-package-delete', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never",
        "package_version": "PlinyTheElder",
        "validate_after_download": True,
    }
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


@patch('time.sleep')
def test_negative_download_error(dont_sleep):
    ''' downloading software - error while downloading the image - first request '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-package-download', ZRR['error']),
    ])
    module_args = {
        "use_rest": "never",
        "package_version": "PlinyTheElder",
    }
    error = zapi_error_message('Error downloading cluster image package for abc.com')
    assert error in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_negative_download_progress_error(dont_sleep):
    ''' downloading software - error while downloading the image - progress error '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-package-download', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_error']),
    ])
    module_args = {
        "use_rest": "never",
        "package_version": "PlinyTheElder",
    }
    error = 'Error downloading package: failure_reason'
    assert error in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_negative_download_progress_error_no_status(dont_sleep):
    ''' downloading software - error while downloading the image - progress error '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-package-download', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['success']),    # retrying if status cannot be found
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_error']),
    ])
    module_args = {
        "use_rest": "never",
        "package_version": "PlinyTheElder",
    }
    error = 'Error downloading package: failure_reason'
    assert error in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_negative_download_progress_error_fetching_status(dont_sleep):
    ''' downloading software - error while downloading the image - progress error '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-package-download', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['error']),
    ])
    module_args = {
        "use_rest": "never",
        "package_version": "PlinyTheElder",
    }
    error = zapi_error_message('Error fetching cluster image package download progress for abc.com')
    assert error in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_negative_update_error_zapi(dont_sleep):
    ''' updating software - error while updating the image '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-package-download', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_complete']),
        ('ZAPI', 'cluster-image-update', ZRR['error']),
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['error']),       # additional error details
        ('ZAPI', 'cluster-image-validate', ZRR['error']),                   # additional error details
    ])
    module_args = {
        "use_rest": "never",
        "package_version": "PlinyTheElder",
    }
    error = zapi_error_message('Error updating cluster image for PlinyTheElder')
    assert error in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_negative_update_error(dont_sleep):
    ''' updating software - error while updating the image '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-package-download', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_complete']),
        ('ZAPI', 'cluster-image-update', ZRR['success']),
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['software_update_info_error']),
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['software_update_info_error']),
    ])
    module_args = {
        "use_rest": "never",
        "package_version": "PlinyTheElder",
    }
    error = 'Error updating image: overall_status: error.'
    assert error in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('time.sleep')
def test_negative_update_error_timeout(dont_sleep):
    ''' updating software - error while updating the image '''
    register_responses([
        ('ZAPI', 'vserver-get-iter', ZRR['cserver']),
        ('ZAPI', 'ems-autosupport-log', ZRR['success']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-package-download', ZRR['success']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_running']),
        ('ZAPI', 'cluster-image-get-download-progress', ZRR['software_update_info_complete']),
        ('ZAPI', 'cluster-image-update', ZRR['success']),
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['software_update_info_error']),
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['software_update_info_running']),
    ])
    module_args = {
        "use_rest": "never",
        "package_version": "PlinyTheElder",
    }
    error = 'Timeout error updating image: overall_status: in_progress.  Should the timeout value be increased?'\
            '  Current value is 1800 seconds.  The software update continues in background.'
    assert error in create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


@patch('ansible_collections.netapp.ontap.plugins.module_utils.netapp.has_netapp_lib')
def test_fail_netapp_lib_error(mock_has_netapp_lib):
    mock_has_netapp_lib.return_value = False
    assert 'Error: the python NetApp-Lib module is required.  Import error: None' == call_main(my_main, DEFAULT_ARGS, fail=True)['msg']


def test_fail_with_http():
    args = dict(DEFAULT_ARGS)
    args.pop('https')
    assert 'Error: https parameter must be True' == call_main(my_main, args, fail=True)['msg']


def test_is_update_required():
    ''' update is required if nodes have different images, or version does not match '''
    register_responses([
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info_mixed']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info']),
        ('ZAPI', 'cluster-image-get-iter', ZRR['cluster_image_info_mixed']),
    ])
    module_args = {
        "use_rest": "never"
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert not my_obj.is_update_required()
    assert my_obj.is_update_required()
    my_obj.parameters["package_version"] = "PlinyTheElder"
    assert my_obj.is_update_required()
    assert my_obj.is_update_required()


def test_cluster_image_validate():
    ''' check error, then check that reports are read correctly '''
    register_responses([
        ('ZAPI', 'cluster-image-validate', ZRR['error']),
        ('ZAPI', 'cluster-image-validate', ZRR['cluster_image_validation_report_list']),
    ])
    module_args = {
        "use_rest": "never"
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.cluster_image_validate() == zapi_error_message('Error running cluster image validate')
    reports = my_obj.cluster_image_validate()
    assert 'required_action' in reports[0]
    assert 'action' in reports[0]['required_action']
    assert reports[0]['required_action']['action'] == 'some_action'
    assert reports[1]['required_action']['action'] == 'other_action'


def test_cluster_image_zapi_errors():
    ''' ZAPi error on delete '''
    register_responses([
        ('ZAPI', 'cluster-image-get-iter', ZRR['error']),
        ('ZAPI', 'cluster-image-get', ZRR['error']),
        ('ZAPI', 'cluster-image-package-delete', ZRR['error']),
    ])
    module_args = {
        "use_rest": "never"
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert expect_and_capture_ansible_exception(my_obj.cluster_image_get, 'fail')['msg'] ==\
        zapi_error_message('Error fetching cluster image details: Fattire__9.3.0')
    assert expect_and_capture_ansible_exception(my_obj.cluster_image_get_for_node, 'fail', 'node')['msg'] ==\
        zapi_error_message('Error fetching cluster image details for node')
    assert expect_and_capture_ansible_exception(my_obj.cluster_image_package_delete, 'fail')['msg'] ==\
        zapi_error_message('Error deleting cluster image package for Fattire__9.3.0')


def test_cluster_image_get_for_node_none_none():
    ''' empty response on get '''
    register_responses([
        ('ZAPI', 'cluster-image-get', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never"
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert my_obj.cluster_image_get_for_node('node') == (None, None)


def test_cluster_image_package_download():
    ''' ZAPI error on download '''
    register_responses([
        ('ZAPI', 'cluster-image-package-download', ZRR['error']),
        ('ZAPI', 'cluster-image-package-download', ZRR['error_18408']),
        ('ZAPI', 'cluster-image-package-download', ZRR['success']),
    ])
    module_args = {
        "use_rest": "never"
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert expect_and_capture_ansible_exception(my_obj.cluster_image_package_download, 'fail')['msg'] ==\
        zapi_error_message('Error downloading cluster image package for abc.com')
    assert my_obj.cluster_image_package_download()
    assert not my_obj.cluster_image_package_download()


def test_cluster_image_update_progress_get_error():
    ''' ZAPI error on progress get '''
    register_responses([
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['error']),
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['error']),
        ('ZAPI', 'cluster-image-update-progress-info', ZRR['error']),
    ])
    module_args = {
        "use_rest": "never"
    }
    my_obj = create_module(my_module, DEFAULT_ARGS, module_args)
    assert expect_and_capture_ansible_exception(my_obj.cluster_image_update_progress_get, 'fail', ignore_connection_error=False)['msg'] ==\
        zapi_error_message('Error fetching cluster image update progress details')
    assert my_obj.cluster_image_update_progress_get() == {}
    assert my_obj.cluster_image_update_progress_get(ignore_connection_error=True) == {}
