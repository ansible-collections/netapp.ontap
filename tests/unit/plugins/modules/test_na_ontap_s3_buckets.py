# (c) 2022, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest
import sys

from ansible_collections.netapp.ontap.tests.unit.compat.mock import patch, call
import ansible_collections.netapp.ontap.plugins.module_utils.netapp as netapp_utils
from ansible_collections.netapp.ontap.tests.unit.plugins.module_utils.ansible_mocks import set_module_args, \
    patch_ansible, create_and_apply, create_module, expect_and_capture_ansible_exception
from ansible_collections.netapp.ontap.tests.unit.framework.mock_rest_and_zapi_requests import get_mock_record, \
    patch_request_and_invoke, register_responses
from ansible_collections.netapp.ontap.tests.unit.framework.rest_factory import rest_responses

from ansible_collections.netapp.ontap.plugins.modules.na_ontap_s3_buckets \
    import NetAppOntapS3Buckets as my_module, main as my_main  # module under test

if not netapp_utils.HAS_REQUESTS and sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip('Skipping Unit Tests on 2.6 as requests is not available')

SRR = rest_responses({
    's3_bucket_more_policy': (200, {"records": [{
        'comment': 'carchi8py was here again',
        'name': 'bucket1',
        'policy': {
            'statements': [
                {
                    "sid": 1,
                    "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
                    "effect": "deny",
                    "conditions": [{"operator": "ip_address", "source_ips": ["1.1.1.1/32", "1.2.2.0/24"]}],
                    "principals": ["user1", "user2"],
                    "resources": ["bucket1", "bucket1/*"]
                },
                {
                    "sid": 2,
                    "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
                    "effect": "deny",
                    "conditions": [{"operator": "ip_address", "source_ips": ["1.1.1.1/32", "1.2.2.0/24"]}],
                    "principals": ["user1", "user2"],
                    "resources": ["bucket1", "bucket1/*"]
                }
            ]
        },
        'qos_policy': {
            'max_throughput_iops': 100,
            'max_throughput_mbps': 150,
            'min_throughput_iops': 0,
            'min_throughput_mbps': 0,
            'name': 'ansibleSVM_auto_gen_policy_9be26687_2849_11ed_9696_005056b3b297',
            'uuid': '9be28517-2849-11ed-9696-005056b3b297'
        },
        'size': 938860800,
        'svm': {'name': 'ansibleSVM', 'uuid': '969ansi97'},
        'uuid': '9bdefd59-2849-11ed-9696-005056b3b297',
        'volume': {'uuid': '1cd8a442-86d1-11e0-abcd-123478563412'}}], "num_records": 1}, None),
    's3_bucket_without_condition': (200, {"records": [{
        'comment': 'carchi8py was here again',
        'name': 'bucket1',
        'policy': {
            'statements': [
                {
                    "sid": 1,
                    "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
                    "effect": "deny",
                    "principals": ["user1", "user2"],
                    "resources": ["bucket1", "bucket1/*"]
                },
                {
                    "sid": 2,
                    "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
                    "effect": "deny",
                    "principals": ["user1", "user2"],
                    "resources": ["bucket1", "bucket1/*"]
                }
            ]
        },
        'qos_policy': {
            'max_throughput_iops': 100,
            'max_throughput_mbps': 150,
            'min_throughput_iops': 0,
            'min_throughput_mbps': 0,
            'name': 'ansibleSVM_auto_gen_policy_9be26687_2849_11ed_9696_005056b3b297',
            'uuid': '9be28517-2849-11ed-9696-005056b3b297'
        },
        'size': 938860800,
        'svm': {'name': 'ansibleSVM', 'uuid': '969ansi97'},
        'uuid': '9bdefd59-2849-11ed-9696-005056b3b297',
        'volume': {'uuid': '1cd8a442-86d1-11e0-abcd-123478563412'}}], "num_records": 1}, None),
    's3_bucket_9_10': (200, {
        "logical_used_size": 0,
        "uuid": "414b29a1-3b26-11e9-bd58-0050568ea055",
        "size": 1677721600,
        "protection_status": {"destination": {}},
        "constituents_per_aggregate": 4,
        "qos_policy": {
            "max_throughput_iops": 10000,
            "max_throughput_mbps": 500,
            "name": "performance",
            "min_throughput_iops": 2000,
            "min_throughput_mbps": 500,
            "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
        },
        "policy": {
            "statements": [
                {
                    "sid": "FullAccessToUser1",
                    "resources": ["bucket1", "bucket1/*"],
                    "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
                    "effect": "allow",
                    "conditions": [
                        {
                            "operator": "ip-address",
                            "max_keys": ["1000"],
                            "delimiters": ["/"],
                            "source-ips": ["1.1.1.1", "1.2.2.0/24"],
                            "prefixes": ["pref"],
                            "usernames": ["user1"]
                        }
                    ],
                    "principals": ["user1", "group/grp1"]
                }
            ]
        },
        "storage_service_level": "value",
        "audit_event_selector": {"access": "all", "permission": "all"},
        "name": "bucket1",
        "comment": "S3 bucket.",
        "svm": {"name": "svm1", "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"},
        "volume": {"uuid": "1cd8a442-86d1-11e0-abcd-123478563412"}
    }, None),
    's3_bucket_9_8': (200, {
        "logical_used_size": 0,
        "uuid": "414b29a1-3b26-11e9-bd58-0050568ea055",
        "size": 1677721600,
        "protection_status": {"destination": {}},
        "constituents_per_aggregate": 4,
        "qos_policy": {
            "max_throughput_iops": 10000,
            "max_throughput_mbps": 500,
            "name": "performance",
            "min_throughput_iops": 2000,
            "min_throughput_mbps": 500,
            "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"
        },
        "policy": {
            "statements": [
                {
                    "sid": "FullAccessToUser1",
                    "resources": ["bucket1", "bucket1/*"],
                    "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
                    "effect": "allow",
                    "conditions": [
                        {
                            "operator": "ip-address",
                            "max_keys": ["1000"],
                            "delimiters": ["/"],
                            "source-ips": ["1.1.1.1", "1.2.2.0/24"],
                            "prefixes": ["pref"],
                            "usernames": ["user1"]
                        }
                    ],
                    "principals": ["user1", "group/grp1"]
                }
            ]
        },
        "storage_service_level": "value",
        "name": "bucket1",
        "comment": "S3 bucket.",
        "svm": {"name": "svm1", "uuid": "02c9e252-41be-11e9-81d5-00a0986138f7"},
        "volume": {"uuid": "1cd8a442-86d1-11e0-abcd-123478563412"}
    }, None),
    'volume_info': (200, {
        "aggregates": [{"name": "aggr1", "uuid": "1cd8a442-86d1-11e0-ae1c-123478563412"}],
    }, None),
})

DEFAULT_ARGS = {
    'hostname': 'hostname',
    'username': 'username',
    'password': 'password',
    'name': 'bucket1',
    'vserver': 'vserver'
}

POLICY_ARGS = {
    "statements": [{
        "sid": "FullAccessToUser1",
        "resources": ["bucket1", "bucket1/*"],
        "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
        "effect": "allow",
        "conditions": [
            {
                "operator": "ip_address",
                "max_keys": ["1000"],
                "delimiters": ["/"],
                "source_ips": ["1.1.1.1", "1.2.2.0/24"],
                "prefixes": ["pref"],
                "usernames": ["user1"]
            }
        ],
        "principals": ["user1", "group/grp1"]
    }]
}

REAL_POLICY_ARGS = {
    "statements": [{
        "sid": "FullAccessToUser1",
        "resources": ["bucket1", "bucket1/*"],
        "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
        "effect": "allow",
        "conditions": [{"operator": "ip_address", "source_ips": ["1.1.1.1", "1.2.2.0/24"]}],
        "principals": ["user1", "group/grp1"]
    }]
}

REAL_POLICY_WTIH_NUM_ARGS = {
    "statements": [{
        "sid": 1,
        "resources": ["bucket1", "bucket1/*"],
        "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
        "effect": "allow",
        "conditions": [{"operator": "ip_address", "source_ips": ["1.1.1.1", "1.2.2.0/24"]}],
        "principals": ["user1", "group/grp1"]
    }]
}

MODIFY_POLICY_ARGS = {
    "statements": [{
        "sid": "FullAccessToUser1",
        "resources": ["bucket1", "bucket1/*"],
        "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
        "effect": "allow",
        "conditions": [
            {
                "operator": "ip_address",
                "max_keys": ["100"],
                "delimiters": ["/"],
                "source_ips": ["2.2.2.2", "1.2.2.0/24"],
                "prefixes": ["pref"],
                "usernames": ["user2"]
            }
        ],
        "principals": ["user1", "group/grp1"]
    }]
}


MULTIPLE_POLICY_STATEMENTS = {
    "statements": [
        {
            "sid": 1,
            "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
            "effect": "deny",
            "conditions": [{"operator": "ip_address", "source_ips": ["1.1.1.1", "1.2.2.0/24"]}],
            "principals": ["user1", "user2"],
            "resources": ["*"]
        },
        {
            "sid": 2,
            "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
            "effect": "deny",
            "conditions": [{"operator": "ip_address", "source_ips": ["1.1.1.1", "1.2.2.0/24"]}],
            "principals": ["user1", "user2"],
            "resources": ["*"]
        }
    ]
}


SAME_POLICY_STATEMENTS = {
    "statements": [
        {
            "sid": 1,
            "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
            "effect": "deny",
            "conditions": [{"operator": "ip_address", "source_ips": ["1.1.1.1", "1.2.2.0/24"]}],
            "principals": ["user1", "user2"],
            "resources": ["*"]
        },
        {
            "sid": 1,
            "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
            "effect": "deny",
            "conditions": [{"operator": "ip_address", "source_ips": ["1.1.1.1", "1.2.2.0/24"]}],
            "principals": ["user1", "user2"],
            "resources": ["*"]
        },
    ]
}


MULTIPLE_POLICY_CONDITIONS = {
    "statements": [
        {
            "sid": 1,
            "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
            "effect": "deny",
            "conditions": [
                {"operator": "ip_address", "source_ips": ["1.1.1.1", "1.2.2.0/24"]},
                {"operator": "not_ip_address", "source_ips": ["2.1.1.1", "1.2.2.0/24"]}
            ],
            "principals": ["user1", "user2"],
            "resources": ["*"]
        },
        {
            "sid": 2,
            "actions": ["GetObject", "PutObject", "DeleteObject", "ListBucket"],
            "effect": "deny",
            "conditions": [{"operator": "ip_address", "source_ips": ["1.1.1.1", "1.2.2.0/24"]}],
            "principals": ["user1", "user2"],
            "resources": ["*"]
        }
    ]
}


QOS_ARGS = {
    "max_throughput_iops": 10000,
    "max_throughput_mbps": 500,
    "name": "performance",
    "min_throughput_iops": 2000,
    "min_throughput_mbps": 500,
}

MODIFY_QOS_ARGS = {
    "max_throughput_iops": 20000,
    "max_throughput_mbps": 400,
    "name": "performance",
    "min_throughput_iops": 3000,
    "min_throughput_mbps": 400,
}

AUDIT_EVENT = {
    "access": "all",
    "permission": "all"
}

MODIFY_AUDIT_EVENT = {
    "access": "read",
    "permission": "allow"
}


def test_low_version():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_97']),
        ('GET', 'cluster', SRR['is_rest_97'])
    ])
    error = create_module(my_module, DEFAULT_ARGS, fail=True)['msg']
    print('Info: %s' % error)
    msg = 'Error: na_ontap_s3_bucket only supports REST, and requires ONTAP 9.8.0 or later.  Found: 9.7.0.'
    assert msg in error


def test_get_s3_bucket_none():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['empty_records'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_s3_bucket() is None


def test_get_s3_bucket_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['generic_error'])
    ])
    my_module_object = create_module(my_module, DEFAULT_ARGS)
    msg = 'Error fetching S3 bucket bucket1: calling: protocols/s3/buckets: got Expected error.'
    assert msg in expect_and_capture_ansible_exception(my_module_object.get_s3_bucket, 'fail')['msg']


def test_get_s3_bucket_9_8():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_9_8'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_s3_bucket() is not None


def test_get_s3_bucket_9_10():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_9_10'])
    ])
    set_module_args(DEFAULT_ARGS)
    my_obj = my_module()
    assert my_obj.get_s3_bucket() is not None


def test_create_s3_bucket_9_8():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['empty_records']),
        ('POST', 'protocols/s3/buckets', SRR['empty_good'])
    ])
    module_args = {'comment': 'carchi8py was here',
                   'aggregates': ['aggr1'],
                   'constituents_per_aggregate': 4,
                   'size': 838860800,
                   'policy': POLICY_ARGS,
                   'qos_policy': QOS_ARGS}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_s3_bucket_9_10():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['empty_records']),
        ('POST', 'protocols/s3/buckets', SRR['empty_good'])
    ])
    module_args = {'comment': 'carchi8py was here',
                   'aggregates': ['aggr1'],
                   'constituents_per_aggregate': 4,
                   'size': 838860800,
                   'policy': POLICY_ARGS,
                   'qos_policy': QOS_ARGS,
                   'audit_event_selector': AUDIT_EVENT}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_with_real_policy_s3_bucket_9_10():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['empty_records']),
        ('POST', 'protocols/s3/buckets', SRR['empty_good'])
    ])
    module_args = {'comment': 'carchi8py was here',
                   'aggregates': ['aggr1'],
                   'constituents_per_aggregate': 4,
                   'size': 838860800,
                   'policy': REAL_POLICY_ARGS,
                   'qos_policy': QOS_ARGS,
                   'audit_event_selector': AUDIT_EVENT}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_with_real_policy_with_sid_as_number_s3_bucket_9_10():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['empty_records']),
        ('POST', 'protocols/s3/buckets', SRR['empty_good'])
    ])
    module_args = {'comment': 'carchi8py was here',
                   'aggregates': ['aggr1'],
                   'constituents_per_aggregate': 4,
                   'size': 838860800,
                   'policy': REAL_POLICY_WTIH_NUM_ARGS,
                   'qos_policy': QOS_ARGS,
                   'audit_event_selector': AUDIT_EVENT}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_create_s3_bucket_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('POST', 'protocols/s3/buckets', SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'carchi8py was here'
    my_obj.parameters['aggregates'] = ['aggr1']
    my_obj.parameters['constituents_per_aggregate'] = 4
    my_obj.parameters['size'] = 838860800
    error = expect_and_capture_ansible_exception(my_obj.create_s3_bucket, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error creating S3 bucket bucket1: calling: protocols/s3/buckets: got Expected error.' == error


def test_delete_s3_bucket():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_9_10']),
        ('DELETE', 'protocols/s3/buckets/02c9e252-41be-11e9-81d5-00a0986138f7/414b29a1-3b26-11e9-bd58-0050568ea055',
         SRR['empty_good'])
    ])
    module_args = {'state': 'absent'}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_delete_s3_bucket_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('DELETE', 'protocols/s3/buckets/02c9e252-41be-11e9-81d5-00a0986138f7/414b29a1-3b26-11e9-bd58-0050568ea055',
         SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['state'] = 'absent'
    my_obj.uuid = '414b29a1-3b26-11e9-bd58-0050568ea055'
    my_obj.svm_uuid = '02c9e252-41be-11e9-81d5-00a0986138f7'
    error = expect_and_capture_ansible_exception(my_obj.delete_s3_bucket, 'fail')['msg']
    print('Info: %s' % error)
    assert 'Error deleting S3 bucket bucket1: calling: ' \
           'protocols/s3/buckets/02c9e252-41be-11e9-81d5-00a0986138f7/414b29a1-3b26-11e9-bd58-0050568ea055: got Expected error.' == error


def test_modify_s3_bucket_9_8():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_9_8']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['volume_info']),
        ('PATCH', 'protocols/s3/buckets/02c9e252-41be-11e9-81d5-00a0986138f7/414b29a1-3b26-11e9-bd58-0050568ea055',
         SRR['empty_good'])
    ])
    module_args = {'comment': 'carchi8py was here',
                   'size': 943718400,
                   'policy': MODIFY_POLICY_ARGS,
                   'qos_policy': MODIFY_QOS_ARGS}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_s3_bucket_9_10():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_9_10']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['volume_info']),
        ('PATCH', 'protocols/s3/buckets/02c9e252-41be-11e9-81d5-00a0986138f7/414b29a1-3b26-11e9-bd58-0050568ea055',
         SRR['empty_good'])
    ])
    module_args = {'comment': 'carchi8py was here',
                   'size': 943718400,
                   'policy': MODIFY_POLICY_ARGS,
                   'qos_policy': MODIFY_QOS_ARGS,
                   'audit_event_selector': MODIFY_AUDIT_EVENT}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_modify_s3_bucket_policy_statements():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_9_10']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['volume_info']),
        ('PATCH', 'protocols/s3/buckets/02c9e252-41be-11e9-81d5-00a0986138f7/414b29a1-3b26-11e9-bd58-0050568ea055',
         SRR['empty_good']),
        # add multiple statements.
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_more_policy']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['volume_info']),
        # try to modify with identical statements.
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_more_policy']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['volume_info']),
        ('PATCH', 'protocols/s3/buckets/969ansi97/9bdefd59-2849-11ed-9696-005056b3b297', SRR['empty_good']),
        # empty policy statements.
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_9_10']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['volume_info']),
        ('PATCH', 'protocols/s3/buckets/02c9e252-41be-11e9-81d5-00a0986138f7/414b29a1-3b26-11e9-bd58-0050568ea055',
         SRR['empty_good'])
    ])
    module_args = {'policy': MULTIPLE_POLICY_STATEMENTS}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert not create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args = {'policy': SAME_POLICY_STATEMENTS}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    assert create_and_apply(my_module, DEFAULT_ARGS, {'policy': {'statements': []}})


def test_modify_s3_bucket_policy_statements_conditions():
    register_responses([
        # modify if desired statements has conditions and current statement conditions is None.
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_without_condition']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['volume_info']),
        ('PATCH', 'protocols/s3/buckets/969ansi97/9bdefd59-2849-11ed-9696-005056b3b297', SRR['empty_good']),
        # empty policy statements conditions.
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_more_policy']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['volume_info']),
        ('PATCH', 'protocols/s3/buckets/969ansi97/9bdefd59-2849-11ed-9696-005056b3b297', SRR['empty_good']),
        # add multiple conditions.
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_more_policy']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['volume_info']),
        ('PATCH', 'protocols/s3/buckets/969ansi97/9bdefd59-2849-11ed-9696-005056b3b297', SRR['empty_good'])
    ])
    module_args = {'policy': MULTIPLE_POLICY_STATEMENTS}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args = {'policy': MULTIPLE_POLICY_STATEMENTS.copy()}
    module_args['policy']['statements'][0]['conditions'] = []
    module_args['policy']['statements'][1]['conditions'] = []
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']
    module_args = {'policy': MULTIPLE_POLICY_CONDITIONS}
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args)['changed']


def test_error_when_try_set_empty_dict_to_policy():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_10_1']),
        ('GET', 'cluster', SRR['is_rest_9_10_1'])
    ])
    module_args = {'policy': {'statements': [{}]}}
    assert 'cannot set empty dict' in create_module(my_module, DEFAULT_ARGS, module_args, fail=True)['msg']


def test_modify_s3_bucket_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('PATCH', 'protocols/s3/buckets/02c9e252-41be-11e9-81d5-00a0986138f7/414b29a1-3b26-11e9-bd58-0050568ea055',
         SRR['generic_error'])
    ])
    my_obj = create_module(my_module, DEFAULT_ARGS)
    my_obj.parameters['comment'] = 'carchi8py was here'
    my_obj.parameters['size'] = 943718400
    current = {'comment': 'carchi8py was here', 'size': 943718400}
    my_obj.uuid = '414b29a1-3b26-11e9-bd58-0050568ea055'
    my_obj.svm_uuid = '02c9e252-41be-11e9-81d5-00a0986138f7'
    error = expect_and_capture_ansible_exception(my_obj.modify_s3_bucket, 'fail', current)['msg']
    print('Info: %s' % error)
    assert 'Error modifying S3 bucket bucket1: calling: ' \
           'protocols/s3/buckets/02c9e252-41be-11e9-81d5-00a0986138f7/414b29a1-3b26-11e9-bd58-0050568ea055: got Expected error.' == error


def test_new_aggr_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_9_8']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['volume_info']),
    ])
    module_args = {'aggregates': ['aggr2']}
    error = 'Aggregates can not be modified for S3 bucket bucket1'
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error


def test_volume_error():
    register_responses([
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'cluster', SRR['is_rest_9_8_0']),
        ('GET', 'protocols/s3/buckets', SRR['s3_bucket_9_8']),
        ('GET', 'storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412', SRR['generic_error']),
    ])
    module_args = {'aggregates': ['aggr2']}
    error = 'calling: storage/volumes/1cd8a442-86d1-11e0-abcd-123478563412: got Expected error.'
    assert create_and_apply(my_module, DEFAULT_ARGS, module_args, fail=True)['msg'] == error
