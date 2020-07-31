# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import mock
import unittest

from tests._utils import _import, captured_output
profile_manager = _import('bac', 'profile_manager')

ACC1 = '123456789012'
ACC2 = '098765432109'
PROFILE1 = 'profile_uno'
PROFILE2 = 'profile_dos'
REG1 = 'us-east-1'
REG2 = 'eu-west-1'
PM_ABS_IMPORT = 'bac.profile_manager.ProfileManager'


class ProfileManagerInitTest(unittest.TestCase):
    """
    TODO -> Test suite for proper initialization of ProfileManager.
            Checking if config and credentials is parsed properly
            and how errors are handled.
    """
    def setUp(self):
        pass

    def test_file_not_found(self):
        pass


class ProfileManagerTest(unittest.TestCase):
    def setUp(self):
        self.pm = self.prepare_pm()

    @mock.patch('%s._load_users' % PM_ABS_IMPORT, mock.Mock())
    @mock.patch('%s._load_account_names' % PM_ABS_IMPORT, mock.Mock())
    @mock.patch('%s._load_roles' % PM_ABS_IMPORT, mock.Mock())
    @mock.patch('%s._load_regions' % PM_ABS_IMPORT, mock.Mock())
    def prepare_pm(self):
        pm = profile_manager.ProfileManager(None)
        pm.available_regions = {REG1, REG2}
        pm.acount_names = {PROFILE1: ACC1, PROFILE2: ACC2}
        pm.sessions = {PROFILE1: mock.Mock(), PROFILE2: mock.Mock()}
        return pm

    def check_items_in_result(self, expected, actual):
        for i in expected:
            self.assertIn(i, actual)

    def check_command(self, cmd, args):
        with captured_output() as (out, err):
            self.pm.handle_command(cmd, args)
        return out.getvalue()

    def test_list_available_profiles(self):
        cmd = 'list-available-profiles'
        output = self.check_command(cmd, None)
        expected = self.pm.sessions.keys()
        self.check_items_in_result(expected, output)

    def test_list_available_regions(self):
        cmd = 'list-available-regions'
        output = self.check_command(cmd, None)
        expected = self.pm.available_regions
        self.check_items_in_result(expected, output)

    def test_list_available_accounts(self):
        cmd = 'list-available-accounts'
        output = self.check_command(cmd, None)
        expected = self.pm.account_names.values()
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
