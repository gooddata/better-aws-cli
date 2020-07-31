# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import mock
import unittest

from argparse import Namespace

from tests._utils import _import
awscli_receiver = _import('bac', 'awscli_receiver')

ARGS = {'check': False, 'dry_run': False}
COMMAND = ['aws', 's3api', 'list-buckets']
PROFILES = {'uno', 'dos'}
REGIONS = {'us-east-1', 'eu-west-1'}
SESSIONS = {
        'uno': mock.Mock(),
        'dos': mock.Mock()
        }


class AwsCliReceiverTest(unittest.TestCase):
    def setUp(self):
        pm = mock.Mock()
        pm.active_profiles = PROFILES
        pm.active_regions = REGIONS
        pm.sessions = SESSIONS

        self.receiver = awscli_receiver.AwsCliReceiver(pm, None)
        self.receiver._env = None

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._filter_regions',
                mock.Mock(return_value=REGIONS))
    def test_cmd_exec(self, call):
        args = Namespace(**ARGS)
        self.receiver.execute_awscli_command(COMMAND, args)
        results = [
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'uno', '--region', 'us-east-1'], env=None),
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'uno', '--region', 'eu-west-1'], env=None),
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'dos', '--region', 'us-east-1'], env=None),
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'dos', '--region', 'eu-west-1'], env=None)
                ]
        call.assert_has_calls(results, any_order=True)

    @mock.patch('subprocess.call')
    def test_dry_run(self, call):
        ARGS['dry_run'] = True
        args = Namespace(**ARGS)
        self.receiver.execute_awscli_command(COMMAND, args)
        call.assert_not_called()
