# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import mock
import unittest

from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from six import assertCountEqual, text_type

from tests._utils import _import, transform
query_completer = _import('bac', 'query_completer')


SHAPE = {
        'Buckets': [
            {
                'CreationDate': 'CreationDate:timestamp',
                'Name': 'BucketName:string'
            }
        ],
        'Owner': {
            'DisplayName': 'DisplayName:string',
            'ID': 'ID:string'
        }
 }


class QueryCompletionTest(unittest.TestCase):
    def setUp(self):
        fake_session = mock.Mock()
        self.completer = query_completer.QueryCompleter(fake_session)
        self.completer._shape_dict = SHAPE

    def get_completions(self, text):
        text = text_type(text)
        doc = Document(text, len(text))
        c_e = CompleteEvent()
        completions = self.completer.get_completions(doc, c_e)
        c = [text_type(c.text) for c in completions]
        return c

    def test_complete_identifier(self):
        c = self.get_completions('')
        result = transform(['Buckets', 'Owner'])
        assertCountEqual(self, c, result)

    def test_complete_identifier_2(self):
        c = self.get_completions('B')
        result = transform(['Buckets'])
        assertCountEqual(self, c, result)

    def test_complete_identifier_3(self):
        c = self.get_completions('Buckets')
        result = transform(['['])
        assertCountEqual(self, c, result)

    def test_complete_lbracket(self):
        c = self.get_completions('Buckets[')
        result = transform(['?', '*', ']'])
        assertCountEqual(self, c, result)

    def test_complete_filter(self):
        c = self.get_completions('Buckets[?')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)

    def test_complete_filter_2(self):
        c = self.get_completions('Buckets[?C')
        result = transform(['CreationDate'])
        assertCountEqual(self, c, result)

    def test_complete_filter_context_reset(self):
        c = self.get_completions('Buckets[?CreationDate==\'value\' &&')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)

    def test_complete_filter_rbracket(self):
        c = self.get_completions('Buckets[?CreationDate==\'value\']')
        result = list()
        assertCountEqual(self, c, result)

    def test_complete_filter_rbracket_dot(self):
        c = self.get_completions('Buckets[?CreationDate==\'value\'].')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)

    def test_complete_flatten(self):
        c = self.get_completions('Buckets[]')
        result = list()
        assertCountEqual(self, c, result)

    def test_complete_flatten_dot(self):
        c = self.get_completions('Buckets[].')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)

    def test_complete_lbracket_star(self):
        c = self.get_completions('Buckets[*].')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)

    def test_complete_lbracket_star_2(self):
        c = self.get_completions('Buckets[*].C')
        result = transform(['CreationDate'])
        assertCountEqual(self, c, result)

    def test_complete_lbracket_star_pipe(self):
        c = self.get_completions('Buckets[*].CreationDate |')
        result = transform(['['])
        assertCountEqual(self, c, result)

    def test_complete_flatten_pipe(self):
        c = self.get_completions('Buckets[].CreationDate |')
        result = transform(['['])
        assertCountEqual(self, c, result)

    def check_progression(self, lst):
        for text, result in lst:
            c = self.get_completions(text)
            assertCountEqual(self, c, transform(result))

    def test_continuous(self):
        lst = [
                ('', ['Buckets', 'Owner']),
                ('B', ['Buckets']),
                ('Buckets', ['[']),
                ('Buckets[', ['?', '*', ']']),
                ('Buckets[]', list()),
                ('Buckets[].', ['Name', 'CreationDate']),
                ('Buckets[].N', ['Name']),
                ('Buckets[].Name |', ['[']),
                ('Buckets[].Name | ', ['[']),
                ('Buckets[].N', ['Name']),
                ('Buckets[].', ['Name', 'CreationDate']),
                ('Buckets[]', list()),
                ('Buckets[', ['?', '*', ']']),
                ('Buckets', ['[']),
                ('Bucket', ['Buckets']),
                ('Buckets', ['[']),
                ('Buckets[', ['?', '*', ']']),
                ('Buckets[]', list()),
                ('Buckets[].', ['Name', 'CreationDate']),
                ('Buckets[].N', ['Name']),
                ('Buckets[].Name |', ['[']),
                ('Buckets[].Name | ', ['['])
            ]
        self.check_progression(lst)

    def test_continuous2(self):
        lst = [
                ('', ['Buckets', 'Owner']),
                ('B', ['Buckets']),
                ('Buckets', ['[']),
                ('Buckets[', ['?', '*', ']']),
                ('Buckets[?', ['Name', 'CreationDate']),
                ('Buckets[?N', ['Name']),
                ('Buckets[?Name==\'value\' &', list()),
                ('Buckets[?Name==\'value\' &&', ['Name', 'CreationDate']),
                ('Buckets[?Name==\'value\' &', list()),
                ('Buckets[?Name==\'value\' &&', ['Name', 'CreationDate']),
                ('Buckets[?Name==\'value\' &', list()),
                ('Buckets[?Name==\'value\'', list()),
                ('Buckets[?Name==\'value\']', list()),
                ('Buckets[?Name==\'value\'].', ['Name', 'CreationDate']),
                ('Buckets[?Name==\'value\'].N', ['Name']),
                ('Buckets[?Name==\'value\'].', ['Name', 'CreationDate']),
                ('Buckets[?Name==\'value\']', list()),
                ('Buckets[?Name==\'value\'', list()),
                ('Buckets[?N', ['Name']),
                ('Buckets[?', ['Name', 'CreationDate']),
                ('Buckets[', ['?', '*', ']']),
                ('Buckets', ['[']),
                ('B', ['Buckets'])
            ]
        self.check_progression(lst)

    def test_continuous3(self):
        lst = [
                ('', ['Buckets', 'Owner']),
                ('Buckets[?N', ['Name']),
                ('Buckets[?Name==\'value\' &&', ['Name', 'CreationDate']),
                ('B', ['Buckets']),
                ('Buckets[', ['?', '*', ']'])
            ]
        self.check_progression(lst)
