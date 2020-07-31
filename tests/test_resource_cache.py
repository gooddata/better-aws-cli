# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import mock
import os
import unittest

from botocore.exceptions import ClientError

from tests._utils import _import
resources = _import('bac', 'resources')

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
CACHE_PATH = os.path.join(BASE_PATH, 'cache')
RESOURCE_CACHE = ('123456789012,foo,bar,baz\n'
                  '098765432109,oof,rab,zab\n')
RESOURCE_CACHE_REG = ('123456789012:us-east-1,foo,bar,baz\n'
                      '098765432109:eu-west-1,oof,rab,zab')
WRITEABLE_RESOURCE = [
        ('123456789012', ['foo', 'bar', 'baz']),
        ('098765432109', ['oof', 'rab', 'zab'])
        ]


class TestResource(resources.CachedResource):

    resource_type = 'test-resource'
    service = 'test'
    operation = 'list_resources'
    query = 'Resources[].Name'


class CachedResourceTest(unittest.TestCase):
    def setUp(self):
        self._resource = TestResource()

    @mock.patch('os.path.exists', mock.Mock(return_value=True))
    def test_load_cache(self):
        m = mock.mock_open(read_data=RESOURCE_CACHE)
        with mock.patch('bac.resources.open', m):
            data = self._resource.data
            first_row = data['123456789012']
            second_row = data['098765432109']
        m.assert_called_once_with(
                resources.CACHE_PATH + '/test-resource.txt', 'r')
        self.assertEqual(first_row, ['foo', 'bar', 'baz'])
        self.assertEqual(second_row, ['oof', 'rab', 'zab'])

    @mock.patch('os.path.exists', mock.Mock(return_value=True))
    def test_load_regional_cache(self):
        m = mock.mock_open(read_data=RESOURCE_CACHE_REG)
        with mock.patch('bac.resources.open', m):
            data = self._resource.data
            first_row = data['123456789012:us-east-1']
            second_row = data['098765432109:eu-west-1']
        m.assert_called_once_with(
                resources.CACHE_PATH + '/test-resource.txt', 'r')
        self.assertEqual(first_row, ['foo', 'bar', 'baz'])
        self.assertEqual(second_row, ['oof', 'rab', 'zab'])

    @mock.patch('os.path.exists', mock.Mock(return_value=True))
    def test_write_cache(self):
        m = mock.mock_open()
        with mock.patch('bac.resources.open', m):
            self._resource.write_cache(WRITEABLE_RESOURCE)
        m.assert_called_once_with(
                resources.CACHE_PATH + '/test-resource.txt', 'a')
        handle = m()
        results = [
                mock.call('123456789012,foo,bar,baz\n'),
                mock.call('098765432109,oof,rab,zab\n')
                ]
        handle.write.assert_has_calls(results)

    def test_get_missing_resources(self):
        def list_resources():
            response = {
                        'Resources': [
                            {'Name': 'foo', 'Mood': 'happy'},
                            {'Name': 'bar', 'Mood': 'sad'}
                            ]
                        }
            return response

        fake_client = mock.Mock()
        fake_client.list_resources = list_resources
        fake_session = mock.Mock()
        fake_session.client.return_value = fake_client
        results = self._resource.get_missing_resources(fake_session, None)
        fake_session.client.assert_called_once_with('test', region_name=None)
        self.assertEqual(results, ['foo', 'bar'])

    def _prepare_session_with_exc(self, message):
        fake_client = mock.Mock()
        error = {'Error': {'Message': message}}
        fake_client.list_resources.side_effect = (
                ClientError(error, 'some_operation'))
        fake_session = mock.Mock()
        fake_session.client.return_value = fake_client
        return fake_session

    def test_get_missing_resources_exc_handled(self):
        fake_session = self._prepare_session_with_exc('UnauthorizedOperation')
        self._resource.get_missing_resources(fake_session, None)
        fake_session.client.assert_called_once_with('test', region_name=None)

    def test_get_missing_resources_exc_raised(self):
        fake_session = self._prepare_session_with_exc('SomeMessage')
        with self.assertRaises(ClientError):
            self._resource.get_missing_resources(fake_session, None)
        fake_session.client.assert_called_once_with('test', region_name=None)
