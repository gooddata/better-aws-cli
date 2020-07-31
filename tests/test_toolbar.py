# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import unittest
import mock

from six import text_type

from tests._utils import _import
shell = _import('bac', 'shell')
toolbar = _import('bac', 'toolbar')


class ToolbarTest(unittest.TestCase):
    @mock.patch('bac.shell.BACCompleter', mock.Mock())
    @mock.patch('bac.shell.ProfileManager')
    def setUp(self, pm):
        self.fake_pm = mock.Mock()
        self._set_active([], [])
        pm.return_value = self.fake_pm
        self.bac = shell.BAC(None)
        self.toolbar = toolbar.Toolbar(
                lambda: self.bac._fuzzy,
                lambda: self.bac._cache_completion,
                lambda: self.bac._profile_manager.active_profiles,
                lambda: self.bac._profile_manager.active_regions)

    def _set_active(self, profiles, regions):
        self.fake_pm.active_profiles = set(profiles)
        self.fake_pm.active_regions = set(regions)

    def _prepare_tb(self, top, bottom):
        top_tb = '   '.join(top)
        bottom_tb = '   '.join(bottom)
        return text_type('\n'.join((top_tb, bottom_tb)))

    def test_toolbar_toggles_on(self):
        top_tb = [
                'Active profiles: None',
                'Active regions: default(us-east-1)',
                ]
        bottom_tb = [
                '[F2] Fuzzy: ON',
                '[F3] Caching: ON',
                '[F5] Refresh cache'
                ]
        expected = self._prepare_tb(top_tb, bottom_tb)
        result = self.toolbar.handler()
        self.assertEqual(expected, result.value)

    def test_toolbar_toggles_off(self):
        self.bac.toggle_fuzzy()
        self.bac.toggle_cache()
        top_tb = [
                'Active profiles: None',
                'Active regions: default(us-east-1)',
                ]
        bottom_tb = [
                '[F2] Fuzzy: OFF',
                '[F3] Caching: OFF',
                '[F5] Refresh cache'
                ]
        expected = self._prepare_tb(top_tb, bottom_tb)
        result = self.toolbar.handler()
        self.assertEqual(expected, result.value)

    def test_toolbar_some_profiles(self):
        self._set_active(['prof1', 'prof2'], ['a', 'b', 'c'])
        top_tb = [
                'Active profiles: 2',
                'Active regions: 3',
                ]
        bottom_tb = [
                '[F2] Fuzzy: ON',
                '[F3] Caching: ON',
                '[F5] Refresh cache'
                ]
        expected = self._prepare_tb(top_tb, bottom_tb)
        result = self.toolbar.handler()
        self.assertEqual(expected, result.value)
