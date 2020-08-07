# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import mock
import os
import unittest

from botocore.exceptions import ClientError
from six import text_type
from testfixtures import log_capture, TempDirectory

from tests._utils import _import, transform
caching = _import('bac', 'caching')

FAKE_CACHED = {'--testing': 'FakeResource'}
USER1 = text_type('123456789012')
USER2 = text_type('098765432109')
REG1 = text_type('us-east-1')
REG2 = text_type('eu-west-1')
VALUE1 = transform(['foo', 'bar', 'baz'])
VALUE2 = transform(['oof', 'rab', 'zab'])


class FakeResource(object):
    pass


class ResourceInitTest(unittest.TestCase):
    @mock.patch('bac.caching.CACHED_RESOURCES', FAKE_CACHED)
    @mock.patch('bac.caching.resources')
    def test_init(self, resources):
        resources.FakeResource = FakeResource
        provider = caching.CacheProvider(None)
        result = {'--testing': FakeResource()}
        self.assertEqual(result.keys(), provider._cached.keys())
        self.assertEqual(
                type(result['--testing']),
                type(provider._cached['--testing'])
                )


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
        def missing_resources(client, region=None):
            return {USER1: VALUE1,
                    USER2: VALUE2}.get(client.profile)

        cache = mock.Mock()
        cache.data = {
                USER1: VALUE1,
                '%s:%s' % (USER1, REG1): VALUE1,
                '%s:%s' % (USER1, REG2): VALUE1,
                      }
        cache.get_missing_resources.side_effect = missing_resources
        self.cache = cache
        return {'test-resource': self.cache}

    def _prepare_profile_manager(self):
        fake_pm = mock.Mock()
        fake_pm.active_profiles = [USER1, USER2]
        fake_pm.account_names = {USER1: USER1, USER2: USER2}
        fake_pm.active_regions = [REG1, REG2]
        session1 = self._prepare_fake_session(USER1)
        session2 = self._prepare_fake_session(USER2)
        fake_pm.sessions = {USER1: session1, USER2: session2}
        return fake_pm

    def _prepare_fake_session(self, profile):
        s = mock.Mock()
        s.profile = profile
        client = mock.Mock()
        client.profile = profile
        s.client.return_value = client
        return s

    def test_toggle_cache(self):
        self.assertEqual(True, self.cache_provider._enabled)
        self.cache_provider.toggle_cache()
        self.assertEqual(False, self.cache_provider._enabled)
        self.cache_provider.toggle_cache()
        self.assertEqual(True, self.cache_provider._enabled)

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

    def populate_cache(self, path):
        os.makedirs(path)
        with open(os.path.join(path, 'foo.txt'), 'w') as f:
            f.write('123456789012:foo,bar')

    def test_refresh_cache(self):
        write_method = self.cache.write_cache
        with TempDirectory() as d:
            with mock.patch('os.getcwd', mock.Mock(return_value=d.path)):
                path = os.path.join(d.path, 'cache')
                self.populate_cache(path)
                assert os.path.exists(os.path.join(path, 'foo.txt'))
                self.cache_provider.refresh_cache()
                # Normally, the 'foo.txt' would be recreated
                # Here, we just check that the cleanup has been succesful
                assert not os.path.exists(os.path.join(path, 'foo.txt'))
        result = [(USER1, VALUE1), (USER2, VALUE2)]
        write_method.assert_called_once_with(result)

    @mock.patch('bac.caching.REGION_SENSITIVE_OPTIONS', {'test-resource'})
    def test_refresh_cache_regional(self):
        write_method = self.cache.write_cache
        with TempDirectory() as d:
            with mock.patch('os.getcwd', mock.Mock(return_value=d.path)):
                path = os.path.join(d.path, 'cache')
                self.populate_cache(path)
                assert os.path.exists(os.path.join(path, 'foo.txt'))
                self.cache_provider.refresh_cache()
                assert not os.path.exists(os.path.join(path, 'foo.txt'))
        result = [
                ('%s:%s' % (USER1, REG1), VALUE1),
                ('%s:%s' % (USER1, REG2), VALUE1),
                ('%s:%s' % (USER2, REG1), VALUE2),
                ('%s:%s' % (USER2, REG2), VALUE2)
                ]
        write_method.assert_called_once_with(result)
