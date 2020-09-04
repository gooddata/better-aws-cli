# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import mock
import unittest

from botocore.exceptions import BotoCoreError, ClientError
from six.moves import configparser
from testfixtures import LogCapture, log_capture

from tests._utils import _import, captured_output, check_logs
profile_manager = _import('bac', 'profile_manager')
errors = _import('bac', 'errors')

ACC1 = '123456789012'
ACC2 = '098765432109'
PROFILE1 = 'profile_uno'
PROFILE2 = 'profile_dos'
REG1 = 'us-east-1'
REG2 = 'eu-west-1'
PM_ABS_IMPORT = 'bac.profile_manager.ProfileManager'


class ProfileManagerInitTest(unittest.TestCase):
    @mock.patch('bac.profile_manager.AWS_CREDENTIALS', '')
    @log_capture(level=logging.ERROR)
    def test_handle_missing_credentials_file(self, captured_log):
        with self.assertRaises(errors.NoProfilesError):
            profile_manager.ProfileManager()
        check_logs(captured_log, 'bac.profile_manager', 'ERROR',
                   ['Failed to parse user profiles',
                    'File not found', 'Exiting BAC'])

    @mock.patch('six.moves.configparser.RawConfigParser.read')
    @mock.patch('os.path.exists', mock.Mock(return_value=True))
    def test_handle_parse_error(self, parse):
        parse.side_effect = configparser.ParsingError(filename='foo')
        with LogCapture() as captured_log:
            with self.assertRaises(errors.NoProfilesError):
                profile_manager.ProfileManager()
        check_logs(captured_log, 'bac.profile_manager', 'ERROR',
                   ['Failed to parse user profiles',
                    'error occured while parsing', 'Exiting BAC'])

    @mock.patch('bac.profile_manager.AWS_CONFIG', '')
    @mock.patch('%s._load_users' % PM_ABS_IMPORT, mock.Mock())
    @mock.patch('%s._load_account_names' % PM_ABS_IMPORT, mock.Mock())
    @mock.patch('%s._load_regions' % PM_ABS_IMPORT, mock.Mock())
    @log_capture(level=logging.ERROR)
    def test_handle_missing_config_file(self, captured_log):
        profile_manager.ProfileManager()
        check_logs(captured_log, 'bac.profile_manager', 'ERROR',
                   ['Failed to parse role profiles',
                    'File not found'])

    @mock.patch('bac.profile_manager.AWS_CONFIG', 'tests/config')
    @mock.patch('bac.profile_manager.AWS_CREDENTIALS', 'tests/credentials')
    @mock.patch('boto3.session.Session')
    def test_load_users(self, faked_session):
        def fake_session(profile_name):
            fake_session = mock.Mock()

            def fake_client(service, region_name=None):
                faked_client = mock.Mock()
                if service == 'sts':
                    response = {'Account': '%s_id' % profile_name}
                    faked_client.get_caller_identity.return_value = response
                elif service == 'organizations':
                    response = {'Account': {'Name': '%s_name' % profile_name}}
                    if profile_name == 'dos':
                        error = {'Error': {'Message': 'Some message'}}
                        faked_client.describe_account.side_effect = (
                                ClientError(error, 'DescribeAccount'))
                    else:
                        faked_client.describe_account.return_value = response
                elif service == 'ec2':
                    response = {
                            'Regions': [
                                {
                                    'Endpoint': 'blah',
                                    'RegionName': 'us-east-1'
                                    },
                                {
                                    'Endpoint': 'blah',
                                    'RegionName': 'eu-west-1'
                                        }
                                ]
                            }
                    if profile_name == 'uno':
                        error = {'Error': {'Message': 'Some message'}}
                        faked_client.describe_regions.side_effect = (
                                ClientError(error, 'DescribeAccount'))
                    else:
                        faked_client.describe_regions.return_value = response

                return faked_client

            fake_session.client.side_effect = fake_client
            fake_session.profile_name = profile_name
            return fake_session

        faked_session.side_effect = fake_session
        pm = profile_manager.ProfileManager()
        expected_names = {
                'uno': 'uno_name',
                'dos': 'dos_id',
                'tres': 'three',
                'cuatro': 'another_role'
                }
        expected_regions = {'us-east-1', 'eu-west-1'}
        for k, v in pm.sessions.items():
            self.assertEqual(k, v.profile_name)
        self.assertEqual(expected_names, pm.account_names)
        self.assertEqual(expected_regions, pm.available_regions)

    @mock.patch('bac.profile_manager.AWS_CREDENTIALS', 'tests/credentials')
    @mock.patch('boto3.session.Session')
    def test_handle_all_profiles_invalid(self, faked_session):
        faked_session.side_effect = BotoCoreError
        with LogCapture() as captured_log:
            with self.assertRaises(errors.NoProfilesError):
                profile_manager.ProfileManager()
        check_logs(captured_log, 'bac.profile_manager', 'ERROR',
                   ['No valid profiles found', 'Exiting BAC.'])


class ProfileManagerTest(unittest.TestCase):
    def setUp(self):
        self.pm = self.prepare_pm()

    @mock.patch('%s._load_users' % PM_ABS_IMPORT, mock.Mock())
    @mock.patch('%s._load_account_names' % PM_ABS_IMPORT, mock.Mock())
    @mock.patch('%s._load_roles' % PM_ABS_IMPORT, mock.Mock())
    @mock.patch('%s._load_regions' % PM_ABS_IMPORT, mock.Mock())
    def prepare_pm(self):
        pm = profile_manager.ProfileManager()
        pm.available_regions = {REG1, REG2}
        pm.account_names = {PROFILE1: ACC1, PROFILE2: ACC2}
        pm.sessions = {PROFILE1: mock.Mock(), PROFILE2: mock.Mock()}
        return pm

    def check_items_in_result(self, expected, actual):
        for i in expected:
            self.assertIn(i, actual)

    def check_command(self, cmd, args):
        with captured_output() as (out, err):
            self.pm.handle_command(cmd, args)
        return out.getvalue()

    def test_call_invalid_command(self):
        result = self.pm.handle_command('foo', None)
        assert not result

    def test_list_available_profiles(self):
        cmd = 'list-available-profiles'
        output = self.check_command(cmd, None)
        expected = set(self.pm.sessions.keys())
        self.assertEqual(expected, {PROFILE1, PROFILE2})
        self.check_items_in_result(expected, output)

    def test_list_available_regions(self):
        cmd = 'list-available-regions'
        output = self.check_command(cmd, None)
        expected = self.pm.available_regions
        self.assertEqual(expected, {REG1, REG2})
        self.check_items_in_result(expected, output)

    def test_list_available_accounts(self):
        cmd = 'list-available-accounts'
        output = self.check_command(cmd, None)
        expected = set(self.pm.account_names.values())
        self.assertEqual(expected, {ACC1, ACC2})
        self.check_items_in_result(expected, output)

    def test_list_available_accounts_empty(self):
        self.pm.account_names = dict()
        cmd = 'list-available-accounts'
        output = self.check_command(cmd, None)
        expected = 'No available accounts found'
        self.check_items_in_result(expected, output)

    def test_include_profiles(self):
        cmd1 = 'list-active-profiles'
        cmd2 = 'include-profiles'
        output = self.check_command(cmd1, None)
        expected = 'No profiles active at the moment.\n'
        self.assertEqual(expected, output)
        self.pm.handle_command(cmd2, [cmd2, PROFILE1])
        output = self.check_command(cmd1, None)
        self.check_items_in_result([PROFILE1], output)
        self.pm.handle_command(cmd2, [cmd2, '*'])
        output = self.check_command(cmd1, None)
        expected = self.pm.sessions.keys()
        self.check_items_in_result(expected, output)

    @log_capture(level=logging.WARNING)
    def test_handle_invalid_profiles(self, captured_log):
        cmd = 'include-profiles'
        self.pm.handle_command(cmd, [cmd, PROFILE1, 'foo'])
        check_logs(captured_log, 'bac.profile_manager', 'WARNING',
                   ['Following profiles/roles have not been found:', 'foo'])
        expected = {PROFILE1}
        self.assertEqual(self.pm.active_profiles, expected)

    def test_exclude_profiles(self):
        cmd1 = 'list-active-profiles'
        cmd2 = 'exclude-profiles'
        output = self.check_command(cmd1, None)
        expected = 'No profiles active at the moment.\n'
        self.pm.active_profiles = set(self.pm.sessions.keys())
        self.pm.handle_command(cmd2, [cmd2, PROFILE1])
        output = self.check_command(cmd1, None)
        self.check_items_in_result([PROFILE2], output)
        self.pm.handle_command(cmd2, [cmd2, '*'])
        output = self.check_command(cmd1, None)
        expected = 'No profiles active at the moment.\n'
        self.check_items_in_result(expected, output)

    def test_switch_profiles(self):
        cmd1 = 'list-active-profiles'
        cmd2 = 'switch-profiles'
        output = self.check_command(cmd1, None)
        expected = 'No profiles active at the moment.\n'
        self.assertEqual(expected, output)
        self.pm.handle_command(cmd2, [cmd2, PROFILE1])
        output = self.check_command(cmd1, None)
        self.check_items_in_result([PROFILE1], output)
        self.pm.handle_command(cmd2, [cmd2, PROFILE2])
        output = self.check_command(cmd1, None)
        self.check_items_in_result([PROFILE2], output)
        self.pm.handle_command(cmd2, [cmd2, '*'])
        output = self.check_command(cmd1, None)
        expected = self.pm.sessions.keys()
        self.check_items_in_result(expected, output)

    def test_include_regions(self):
        cmd1 = 'list-active-regions'
        cmd2 = 'include-regions'
        output = self.check_command(cmd1, None)
        expected = 'No regions active at the moment.\n'
        self.assertEqual(expected, output)
        self.pm.handle_command(cmd2, [cmd2, REG1])
        output = self.check_command(cmd1, None)
        self.check_items_in_result([REG1], output)
        self.pm.handle_command(cmd2, [cmd2, '*'])
        output = self.check_command(cmd1, None)
        expected = self.pm.available_regions
        self.check_items_in_result(expected, output)

    @log_capture(level=logging.WARNING)
    def test_handle_invalid_regions(self, captured_log):
        cmd = 'include-regions'
        self.pm.handle_command(cmd, [cmd, REG1, 'oof'])
        check_logs(captured_log, 'bac.profile_manager', 'WARNING',
                   ['Following regions have not been found:', 'oof'])
        expected = {REG1}
        self.assertEqual(self.pm.active_regions, expected)

    def test_exclude_regions(self):
        cmd1 = 'list-active-regions'
        cmd2 = 'exclude-regions'
        output = self.check_command(cmd1, None)
        expected = 'No regions active at the moment.\n'
        self.pm.active_regions = self.pm.available_regions
        self.pm.handle_command(cmd2, [cmd2, REG1])
        output = self.check_command(cmd1, None)
        self.check_items_in_result([REG2], output)
        self.pm.handle_command(cmd2, [cmd2, '*'])
        output = self.check_command(cmd1, None)
        expected = 'No regions active at the moment.\n'
        self.check_items_in_result(expected, output)

    def test_switch_regions(self):
        cmd1 = 'list-active-regions'
        cmd2 = 'switch-regions'
        output = self.check_command(cmd1, None)
        expected = 'No regions active at the moment.\n'
        self.assertEqual(expected, output)
        self.pm.handle_command(cmd2, [cmd2, REG1])
        output = self.check_command(cmd1, None)
        self.check_items_in_result([REG1], output)
        self.pm.handle_command(cmd2, [cmd2, REG2])
        output = self.check_command(cmd1, None)
        self.check_items_in_result([REG2], output)
        self.pm.handle_command(cmd2, [cmd2, '*'])
        output = self.check_command(cmd1, None)
        expected = self.pm.available_regions
        self.check_items_in_result(expected, output)

    def test_get_first_profile(self):
        result = self.pm.get_first_profile()
        self.assertEqual(result, PROFILE1)

    def test_get_first_session(self):
        self.pm.sessions[PROFILE1] = 'Would be session'
        result = self.pm.get_first_session()
        self.assertEqual(result, 'Would be session')
