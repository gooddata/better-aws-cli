# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import mock
import unittest

from botocore.exceptions import ClientError
from six import text_type
from testfixtures import log_capture

from tests._utils import _import, transform
caching = _import('bac', 'caching')

USER1 = text_type('123456789012')
USER2 = text_type('098765432109')
REG1 = text_type('us-east-1')
REG2 = text_type('eu-west-1')
VALUE1 = transform(['foo', 'bar', 'baz'])
VALUE2 = transform(['oof', 'rab', 'zab'])


class CachingTest(unittest.TestCase):
    def setUp(self):
        self.option = 'test-resource'
        cached = self._prepare_cache()
        pm = self._prepare_profile_manager()
        self.cache_provider = self._prepare_provider(pm, cached)

    def _prepare_provider(self, pm, cached):
        with mock.patch('bac.caching.CacheProvider._init_resources',
                        mock.Mock()):
            provider = caching.CacheProvider(pm)
        provider._cached = cached
        return provider

    def _prepare_cache(self):
        cache = mock.Mock()
        cache.data = {
                USER1: VALUE1,
                '%s:%s' % (USER1, REG1): VALUE1,
                '%s:%s' % (USER1, REG2): VALUE1,
                      }
        cache.get_missing_resources.return_value = VALUE2
        return {'test-resource': cache}

    def _prepare_profile_manager(self):
        fake_pm = mock.Mock()
        fake_pm.active_profiles = [USER1, USER2]
        fake_pm.account_names = {USER1: USER1, USER2: USER2}
        fake_pm.active_regions = [REG1, REG2]
        fake_pm.sessions = {USER1: mock.Mock(), USER2: mock.Mock()}
        return fake_pm

    def test_get_cached_resource(self):
        result = self.cache_provider.get_cached_resource(self.option)
        correct_result = VALUE1 + VALUE2
        self.assertEqual(result, correct_result)

    @mock.patch('bac.caching.REGION_SENSITIVE_OPTIONS', {'test-resource'})
    def test_get_cached_reg_resource(self):
        result = self.cache_provider.get_cached_resource(self.option)
        correct_result = VALUE1 + VALUE1 + VALUE2 + VALUE2
        self.assertEqual(result, correct_result)

    @log_capture(level=logging.DEBUG)
    def test_get_cached_resource_with_exc(self, captured_log):
        cp = self.cache_provider
        pm = cp._profile_manager
        pm.sessions[USER2].profile_name = USER2
        error = {'Error': {'Message': 'Some message'}}
        cp._cached['test-resource'].get_missing_resources.side_effect = (
                ClientError(error, 'some_operation'))
        result = self.cache_provider.get_cached_resource(self.option)
        captured_log.check(('bac.caching', 'DEBUG', text_type('Failed to receive cache for Mock, for profile 098765432109. Received following error: An error occurred (Unknown) when calling the some_operation operation: Some message'))) # noqa
        self.assertEqual(result, VALUE1)

    @mock.patch('bac.caching.REGION_SENSITIVE_OPTIONS', {'test-resource'})
    @log_capture(level=logging.DEBUG)
    def test_get_cached_reg_resource_with_exc(self, captured_log):
        cp = self.cache_provider
        pm = cp._profile_manager
        pm.sessions[USER2].profile_name = USER2
        pm.active_regions = [REG1]
        error = {'Error': {'Message': 'Some message'}}
        cp._cached['test-resource'].get_missing_resources.side_effect = (
                ClientError(error, 'some_operation'))
        result = self.cache_provider.get_cached_resource(self.option)
        captured_log.check(('bac.caching', 'DEBUG', text_type('Failed to receive cache for Mock, for profile 098765432109, for region us-east-1. Received following error: An error occurred (Unknown) when calling the some_operation operation: Some message'))) # noqa
        self.assertEqual(result, VALUE1)
