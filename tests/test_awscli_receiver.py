# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import unittest

import mock

from argparse import Namespace

from botocore.exceptions import ClientError
from testfixtures import LogCapture, log_capture

from tests._utils import _import, captured_output, check_logs
awscli_receiver = _import('bac', 'awscli_receiver')
errors = _import('bac', 'errors')

ARGS = {'check': False, 'dry_run': False}
COMMAND = ['aws', 's3api', 'list-buckets']
PROFILES = {'uno', 'dos'}
REGIONS = {'us-east-1', 'eu-west-1'}
SUPPORTED_REGIONS = {'us-east-2', 'eu-west-1', 'eu-west-2'}
EC2_DESCRIBE_REGIONS = {'Regions': [{'Endpoint': 'blah',
                                     'OptInStatus': 'opt-in-not-required',
                                     'RegionName': 'eu-west-1'},
                                    {'Endpoint': 'blah',
                                     'OptInStatus': 'opt-in-not-required',
                                     'RegionName': 'us-east-1'}]}
fake_ec2 = mock.Mock()
fake_ec2.describe_regions.return_value = EC2_DESCRIBE_REGIONS
fake_session = mock.Mock()
fake_session.client.return_value = fake_ec2
SESSIONS = {'uno': fake_session, 'dos': fake_session, 'tres': fake_session}


class AwsCliReceiverEnvTest(unittest.TestCase):
    @mock.patch.dict('os.environ', {'foo': 'oof', 'bar': 'rab'}, clear=True)
    def test_all_supported_env_vars(self):
        receiver = awscli_receiver.AwsCliReceiver(None, None)
        self.assertEqual(receiver._env, {'foo': 'oof', 'bar': 'rab'})

    @mock.patch.dict('os.environ', {'AWS_PROFILE': '1234', 'foo': 'oof'},
                     clear=True)
    @log_capture(level=logging.DEBUG)
    def test_not_supported_env_var(self, captured_log):
        receiver = awscli_receiver.AwsCliReceiver(None, None)
        self.assertEqual(receiver._env, {'foo': 'oof'})
        check_logs(captured_log, 'bac.awscli_receiver',
                   'WARNING', ['Dropping', 'AWS_PROFILE'])


class AwsCliReceiverTest(unittest.TestCase):
    def setUp(self):
        self.args = Namespace(**ARGS)
        self.command = list(COMMAND)
        self.pm = mock.Mock()
        self.pm.active_profiles = PROFILES
        self.pm.active_regions = REGIONS
        self.pm.sessions = SESSIONS
        self.checker = mock.MagicMock()
        self.receiver = awscli_receiver.AwsCliReceiver(self.pm, self.checker)
        self.receiver._env = None

    @mock.patch('subprocess.call')
    def test_help(self, call):
        self.command = ['aws', 's3api', 'help']
        self.receiver.execute_awscli_command(self.command, self.args)
        call.assert_called_once_with(['aws', 's3api', 'help'], env=None)

    @log_capture(level=logging.WARNING)
    def test_no_profiles(self, captured_log):
        self.pm.active_profiles = set()
        self.receiver.execute_awscli_command(self.command, self.args)
        check_logs(captured_log, 'bac.awscli_receiver',
                   'WARNING', 'No profiles')

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._filter_regions',
                mock.Mock(return_value={'us-east-1'}))
    def test_no_regions(self, call):
        self.pm.active_regions = set()
        with captured_output() as (out, err):
            with LogCapture(level=logging.WARNING) as captured_log:
                self.receiver.execute_awscli_command(self.command, self.args)
        results = [
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'uno', '--region', 'us-east-1'], env=None),
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'dos', '--region', 'us-east-1'], env=None)
                ]
        call.assert_has_calls(results, any_order=True)
        check_logs(captured_log, 'bac.awscli_receiver',
                   'WARNING', ['No region', 'us-east-1'])

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._filter_regions',
                mock.Mock(return_value=REGIONS))
    def test_cmd_exec(self, call):
        self.receiver.execute_awscli_command(self.command, self.args)
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
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._filter_regions',
                mock.Mock(return_value=REGIONS))
    def test_cmd_exec_explicit_profile(self, call):
        self.command.extend(['--profile', 'tres'])
        self.receiver.execute_awscli_command(self.command, self.args)
        results = [
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'tres', '--region', 'us-east-1'], env=None),
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'tres', '--region', 'eu-west-1'], env=None),
                ]
        call.assert_has_calls(results, any_order=True)

    def test_handle_invalid_explicit_profile(self):
        self.command.extend(['--profile', 'cuatro'])
        with self.assertRaises(errors.InvalidAwsCliCommandError):
            self.receiver.execute_awscli_command(self.command, self.args)

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._filter_regions',
                mock.Mock(return_value={'ca-central-1'}))
    def test_cmd_exec_explicit_region(self, call):
        self.command.extend(['--region', 'ca-central-1'])
        self.receiver.execute_awscli_command(self.command, self.args)
        results = [
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--region',
                     'ca-central-1', '--profile', 'uno'], env=None),
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--region',
                     'ca-central-1', '--profile', 'dos'], env=None),
                ]
        call.assert_has_calls(results, any_order=True)

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._filter_supported_regions',
                mock.Mock(return_value=SUPPORTED_REGIONS))
    def test_cmd_exec_disables_explicit_region(self, call):
        self.pm.active_regions = {'us-east-1', 'eu-west-1'}
        self.pm.active_profiles = {'uno'}
        self.command.extend(['--region', 'ca-central-1'])
        with captured_output() as (out, err):
            with LogCapture() as captured_log:
                self.receiver.execute_awscli_command(self.command, self.args)
        call.assert_not_called()
        check_logs(captured_log, 'bac.awscli_receiver',
                   'WARNING', ['None', 'regions', 'uno'])

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.paginate')
    def test_filter_regions(self, ssm_paginate, call):
        self.pm.active_regions = {'ca-central-1', 'us-east-1', 'eu-west-1'}
        ssm_paginate.return_value = SUPPORTED_REGIONS
        with captured_output() as (out, err):
            self.receiver.execute_awscli_command(self.command, self.args)
        results = [
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'uno', '--region', 'eu-west-1'], env=None),
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'dos', '--region', 'eu-west-1'], env=None),
                ]
        call.assert_has_calls(results, any_order=True)

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._filter_supported_regions',
                mock.Mock(return_value=SUPPORTED_REGIONS))
    def test_filter_returns_empty_set(self, call):
        self.pm.active_regions = {'ca-central-1'}
        self.pm.active_profiles = {'uno'}
        with captured_output() as (out, err):
            with LogCapture() as captured_log:
                self.receiver.execute_awscli_command(self.command, self.args)
        call.assert_not_called()
        check_logs(captured_log, 'bac.awscli_receiver',
                   'WARNING', ['None', 'regions', 'uno'])

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._get_enabled_regions')
    def test_handle_privilege_filtering_error(self, ec2, call):
        ec2.side_effect = ClientError(dict(), 'UnauthorizedOperation')
        self.pm.active_profiles = {'uno'}
        with captured_output() as (out, err):
            with LogCapture(level=logging.WARNING) as captured_log:
                self.receiver.execute_awscli_command(self.command, self.args)
        results = [
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'uno', '--region', 'us-east-1'], env=None),
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'uno', '--region', 'eu-west-1'], env=None),
                ]
        call.assert_has_calls(results, any_order=True)
        check_logs(captured_log, 'bac.awscli_receiver', 'WARNING',
                   ['insufficient privileges',
                    'Continuing with all active regions'])

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._get_enabled_regions')
    def test_handle_filtering_error(self, ec2, call):
        ec2.side_effect = ClientError(dict(), 'SomeOperation')
        self.pm.active_profiles = {'uno'}
        with captured_output() as (out, err):
            with LogCapture(level=logging.WARNING) as captured_log:
                self.receiver.execute_awscli_command(self.command, self.args)
        results = [
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'uno', '--region', 'us-east-1'], env=None),
                mock.call(
                    ['aws', 's3api', 'list-buckets', '--profile',
                     'uno', '--region', 'eu-west-1'], env=None),
                ]
        call.assert_has_calls(results, any_order=True)
        check_logs(captured_log, 'bac.awscli_receiver', 'WARNING',
                   ['error occured while filtering',
                    'Continuing with all active regions'])

    def test_handle_service_extraction_error(self):
        command = ['aws', '--weird-arg', 's3api', 'list-buckets']
        with self.assertRaises(errors.InvalidAwsCliCommandError):
            self.receiver.execute_awscli_command(command, self.args)

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._filter_supported_regions')
    def test_service_extraction(self, filter_supported, call):
        filter_supported.return_value = set()
        command = ['aws', 'ec2', 'describe-instances']
        self.pm.active_profiles = {'uno'}
        with captured_output() as (out, err):
            self.receiver.execute_awscli_command(command, self.args)
        filter_supported.assert_called_once_with(
                REGIONS, 'ec2', SESSIONS['uno'])
        call.assert_not_called()

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._filter_supported_regions')
    def test_service_extraction_s3api_case(self, filter_supported, call):
        filter_supported.return_value = set()
        self.pm.active_profiles = {'uno'}
        with captured_output() as (out, err):
            self.receiver.execute_awscli_command(self.command, self.args)
        filter_supported.assert_called_once_with(
                REGIONS, 's3', SESSIONS['uno'])
        call.assert_not_called()

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._check')
    def test_dry_run_and_no_check(self, check_method, call):
        vars(self.args)['dry_run'] = True
        vars(self.args)['check'] = False
        self.receiver.execute_awscli_command(self.command, self.args)
        check_method.assert_not_called()
        call.assert_not_called()

    @mock.patch('subprocess.call')
    @mock.patch('bac.awscli_receiver.AwsCliReceiver._check_privileges')
    def test_no_priv_check(self, priv_check_method, call):
        vars(self.args)['dry_run'] = True
        self.receiver.execute_awscli_command(self.command, self.args)
        priv_check_method.assert_not_called()
        call.assert_not_called()

    def test_priv_check(self):
        vars(self.args)['dry_run'] = True
        vars(self.args)['check'] = True
        vars(self.args)['priv_check'] = True
        self.checker.check.return_value = 's3'
        self.receiver.execute_awscli_command(self.command, self.args)
        results = [mock.call('s3', 'uno'), mock.call('s3', 'dos')]
        self.checker.privilege_check.assert_has_calls(results, any_order=True)

    def test_priv_check_explicit_profile(self):
        # self.checker.privilege_check
        vars(self.args)['dry_run'] = True
        vars(self.args)['check'] = True
        vars(self.args)['priv_check'] = True
        self.checker.check.return_value = 's3'
        self.command.extend(['--profile', 'tres'])
        self.receiver.execute_awscli_command(self.command, self.args)
        self.checker.privilege_check.assert_called_once_with('s3', 'tres')

    def test_invalid_command(self):
        # This only ensures that the syntax check error is propagated correctly
        vars(self.args)['check'] = True
        self.checker.check.side_effect = errors.CLICheckerSyntaxError()
        with self.assertRaises(errors.CLICheckerSyntaxError):
            self.receiver.execute_awscli_command(self.command, self.args)

    def test_insufficient_privileges(self):
        # This only ensures that the priv check error is propagated correctly
        vars(self.args)['check'] = True
        vars(self.args)['priv_check'] = True
        self.checker.check.side_effect = errors.CLICheckerPermissionException()
        with self.assertRaises(errors.CLICheckerPermissionException):
            self.receiver.execute_awscli_command(self.command, self.args)
