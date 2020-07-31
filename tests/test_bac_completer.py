# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import mock
import unittest

from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from tests._utils import _import, transform
from six import assertCountEqual, text_type

bac_completer = _import('bac', 'bac_completer')
errors = _import('bac', 'errors')

PROFILE_SESSIONS = {'prof1': mock.Mock(), 'prof2': mock.Mock()}
ACC_NAMES = {'prof1': '123456789012', 'prof2': '098765432109'}
REGS = {'us-east-1', 'eu-west-1'}
BUCKETS = ['foo', 'bar', 'baz', 'foobar']


class BACCommandsTest(unittest.TestCase):
    @mock.patch('bac.bac_completer.CacheProvider')
    def setUp(self, cache_provider):

        fake_cp = mock.Mock()
        fake_cp.get_cached_resource.return_value = transform(BUCKETS)
        cache_provider.return_value = fake_cp
        fake_pm = self._get_profile_manager()
        self.completer = bac_completer.BACCompleter(fake_pm)

    def _get_profile_manager(self):
        pm = mock.Mock()
        pm.available_regions = REGS
        pm.account_names = ACC_NAMES
        pm.sessions = PROFILE_SESSIONS
        return pm

    def get_completion(self, text):
        text = text_type(text)
        doc = Document(text, len(text))
        c_e = CompleteEvent()
        completions = self.completer.get_completions(doc, c_e)
        c = [text_type(c.text) for c in completions]
        return c

    def check_progression(self, lst):
        for text, result in lst:
            c = self.get_completions(text)
            assertCountEqual(self, c, transform(result))

    def test_bac_commands_all(self):
        c = self.get_completion('')
        result = transform(list(bac_completer.COMMANDS_MAP.keys()))
        assertCountEqual(self, c, result)

    def test_bac_commands(self):
        c = self.get_completion('i')
        result = transform(['include-profiles', 'include-regions'])
        assertCountEqual(self, c, result)

    def test_bac_commands_none(self):
        c = self.get_completion('z')
        result = list()
        assertCountEqual(self, c, result)

    def test_aws_cmd_completion_blank(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws')
        result = list()
        assertCountEqual(self, c, result)

    def test_aws_cmd_1(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3')
        result = transform(['s3', 's3api', 's3control'])
        assertCountEqual(self, c, result)

    def test_aws_cmd_2(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3a')
        result = transform(['s3api'])
        assertCountEqual(self, c, result)

    def test_aws_cmd_3(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3api')
        result = transform(['s3api'])
        assertCountEqual(self, c, result)

    def test_aws_cmd_4(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3api co')
        result = transform(['complete-multipart-upload', 'copy-object'])
        assertCountEqual(self, c, result)

    def test_aws_cmd_5(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3api list-buckets')
        result = transform(['list-buckets'])
        assertCountEqual(self, c, result)

    def test_aws_cmd_6(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3api list-buckets --o')
        result = transform(['--output'])
        assertCountEqual(self, c, result)

    def test_aws_cmd_7(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3api list-buckets --output ')
        result = transform(['json', 'text', 'table'])
        assertCountEqual(self, c, result)

    def test_aws_cmd_8(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3api list-buckets --output te')
        result = transform(['text'])
        assertCountEqual(self, c, result)

    def test_aws_cmd_9(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3api list-buckets --output text ')
        result = list()
        assertCountEqual(self, c, result)

    def test_aws_cmd_10(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3api list-buckets --output text --que')
        result = transform(['--query'])
        assertCountEqual(self, c, result)

    def test_aws_cmd_del_1(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3 ')
        result = transform(['ls', 'website', 'mv', 'cp', 'rm',
                            'sync', 'mb', 'rb', 'presign'])
        assertCountEqual(self, c, result)
        c = self.get_completion('aws s')
        result = transform(['s3api', 'sts'])
        for r in result:
            self.assertIn(r, c)

    def test_resource_comp_1(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3api put-buckets-acl --bucket ')
        result = transform(BUCKETS)
        assertCountEqual(self, c, result)

    def test_resource_comp_2(self):
        self.completer.toggle_fuzzy()
        c = self.get_completion('aws s3api put-buckets-acl --bucket bar')
        result = transform(['bar'])
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_completion_blank(self):
        c = self.get_completion('aws')
        result = list()
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_1(self):
        c = self.get_completion('aws s3')
        result = transform(['s3', 's3api', 's3control'])
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_2(self):
        c = self.get_completion('aws s3a')
        result = transform(['s3api'])
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_3(self):
        c = self.get_completion('aws 3a')
        result = transform(['s3api', 'route53domains'])
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_4(self):
        c = self.get_completion('aws s3api')
        result = transform(['s3api'])
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_5(self):
        c = self.get_completion('aws s3api copy')
        result = transform(['upload-part-copy', 'copy-object'])
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_6(self):
        c = self.get_completion('aws s3api lsbs')
        result = text_type('list-buckets')
        self.assertIn(result, c)

    def test_fuzzy_aws_cmd_7(self):
        c = self.get_completion('aws s3api list-buckets --qr')
        result = transform(['--query'])
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_8(self):
        c = self.get_completion('aws s3api list-buckets --output ')
        result = transform(['json', 'text', 'table'])
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_9(self):
        c = self.get_completion('aws s3api list-buckets --output tx')
        result = transform(['text'])
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_10(self):
        c = self.get_completion('aws s3api list-buckets --output text ')
        result = list()
        assertCountEqual(self, c, result)

    def test_fuzzy_aws_cmd_11(self):
        c = self.get_completion('aws s3api list-buckets --output text --qr')
        result = transform(['--query'])
        assertCountEqual(self, c, result)

    def test_fuzzy_resource_comp_1(self):
        c = self.get_completion('aws s3api put-buckets-acl --bucket ')
        result = transform(BUCKETS)
        assertCountEqual(self, c, result)

    def test_fuzzy_resource_comp_2(self):
        c = self.get_completion('aws s3api put-buckets-acl --bucket bar')
        result = transform(['bar', 'foobar'])
        assertCountEqual(self, c, result)
