# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import mock
import os
import unittest

from botocore.exceptions import ClientError
from testfixtures import TempDirectory

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


class FakeResource(resources.CachedResource):
    resource_type = 'test-resource'
    service = 'test'
    operation = 'list_resources'
    query = 'Resources[].Name'


class CachedResourceTest(unittest.TestCase):
    def setUp(self):
        self.resource = FakeResource()

    def test_data_setter(self):
        self.assertEqual(self.resource._data, None)
        self.resource.data = 'foo'
        self.assertEqual(self.resource._data, 'foo')

    def test_data_getter_nonexistent_data(self):
        result = self.resource.data
        self.assertEqual(result, dict())

    @mock.patch('os.path.exists', mock.Mock(return_value=True))
    def test_load_cache(self):
        m = mock.mock_open(read_data=RESOURCE_CACHE)
        with mock.patch('bac.resources.open', m):
            data = self.resource.data
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
            data = self.resource.data
            first_row = data['123456789012:us-east-1']
            second_row = data['098765432109:eu-west-1']
        m.assert_called_once_with(
                resources.CACHE_PATH + '/test-resource.txt', 'r')
        self.assertEqual(first_row, ['foo', 'bar', 'baz'])
        self.assertEqual(second_row, ['oof', 'rab', 'zab'])

    def test_write_cache(self):
        with TempDirectory() as d:
            path = os.path.join(d.path, 'cache')
            filename = self.resource.resource_type + '.txt'
            with mock.patch('bac.resources.CACHE_PATH', path):
                self.resource.write_cache(WRITEABLE_RESOURCE)
            with open(os.path.join(path, filename), 'r') as f:
                results = f.read().splitlines()
        expected = RESOURCE_CACHE.splitlines()
        self.assertEqual(results, expected)

    def populate_cache(self, path, filename):
        os.makedirs(path)
        with open(os.path.join(path, filename), 'w') as f:
            f.write('000000000000,uno,dos,tres\n')

    def test_write_cache_append_to_existing(self):
        with TempDirectory() as d:
            path = os.path.join(d.path, 'cache')
            filename = self.resource.resource_type + '.txt'
            self.populate_cache(path, filename)
            with mock.patch('bac.resources.CACHE_PATH', path):
                self.resource.write_cache(WRITEABLE_RESOURCE)
            with open(os.path.join(path, filename), 'r') as f:
                results = f.read().splitlines()
        expected = ['000000000000,uno,dos,tres']
        expected.extend(RESOURCE_CACHE.splitlines())
        self.assertEqual(results, expected)

    def test_get_missing_resources(self):
        fake_client = mock.Mock()
        response = {
                    'Resources': [
                        {'Name': 'foo', 'Mood': 'happy'},
                        {'Name': 'bar', 'Mood': 'sad'}
                        ]
                    }
        fake_client.list_resources.return_value = response
        results = self.resource.get_missing_resources(fake_client)
        self.assertEqual(results, ['foo', 'bar'])

    def _prepare_client_with_exc(self, message):
        fake_client = mock.Mock()
        error = {'Error': {'Message': message}}
        fake_client.list_resources.side_effect = (
                ClientError(error, 'some_operation'))
        return fake_client

    def test_get_missing_resources_exc_handled(self):
        fake_client = self._prepare_client_with_exc('UnauthorizedOperation')
        result = self.resource.get_missing_resources(fake_client)
        self.assertEqual(result, list())

    def test_get_missing_resources_exc_raised(self):
        fake_client = self._prepare_client_with_exc('SomeMessage')
        with self.assertRaises(ClientError):
            self.resource.get_missing_resources(fake_client)
