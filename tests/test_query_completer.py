# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import mock
import unittest

from botocore.exceptions import UnknownServiceError
from botocore.model import OperationNotFoundError
from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from six import assertCountEqual, text_type

from tests._utils import _import, transform
query_completer = _import('bac', 'query_completer')
errors = _import('bac', 'errors')


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


class QueryCompleterInitializationTest(unittest.TestCase):
    @mock.patch('botocore.session.Session')
    @mock.patch('bac.shape_parser.ShapeParser', mock.Mock())
    def setUp(self, faked_session):
        faked_session = mock.Mock()
        self.session = faked_session
        self.completer = query_completer.QueryCompleter(self.session)
        self.completer._session = self.session
        self.fake_service_data = mock.Mock()

        def get_operation_name(operation):
            if operation == 'list_buckets':
                return 'ListBuckets'
            raise errors.InvalidShapeData()

        self.fake_service_data.get_operation_name.side_effect = (
                get_operation_name)
        self.completer._command_table = {'s3': self.fake_service_data}

    def test_handle_bad_service_name(self):
        self.completer.set_shape_dict('foo', 'list_buckets')
        self.assertEqual(self.completer._shape_dict, None)

    def test_handle_bad_operation_name(self):
        self.completer.set_shape_dict('s3api', 'bar')
        self.assertEqual(self.completer._shape_dict, None)

    def test_handle_service_model_load_failure(self):
        self.session.get_service_model.side_effect = (
                UnknownServiceError(service_name='s3', known_service_names=''))
        self.completer.set_shape_dict('s3api', 'list_buckets')
        self.assertEqual(self.completer._shape_dict, None)

    def test_handle_operation_model_load_failure(self):
        fake_service_model = mock.Mock()
        fake_service_model.operation_model.side_effect = (
                OperationNotFoundError())
        self.session.get_service_model.return_value = fake_service_model
        self.completer.set_shape_dict('s3api', 'list-buckets')
        self.assertEqual(self.completer._shape_dict, None)


class QueryCompletionTest(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.completer = query_completer.QueryCompleter(self.session)
        self.completer._shape_dict = SHAPE

    def get_completions(self, text):
        return self._get_completions(text)

    def request_completions(self, text):
        return self._get_completions(text, requested=True)

    def _get_completions(self, text, requested=False):
        text = text_type(text)
        doc = Document(text, len(text))
        c_e = CompleteEvent(completion_requested=requested)
        completions = self.completer.get_completions(doc, c_e)
        c = [text_type(c.text) for c in completions]
        return c

    @mock.patch('bac.query_completer.build_command_table', mock.Mock())
    def test_command_table_getter(self):
        self.assertEqual(self.completer._command_table, None)
        self.completer.command_table
        assert self.completer._command_table is not None

    def test_no_shape_dict(self):
        self.completer._shape_dict = None
        c = self.get_completions('')
        self.assertEqual(c, list())

    def test_enabling_disabled(self):
        lst = [
                ('', ['Buckets', 'Owner']),
                (']', list()),
                ('] ', list()),
                (']', list()),
                ('', ['Buckets', 'Owner'])
                ]
        self.check_progression(lst)

    def test_handle_lexer_error(self):
        c = self.get_completions('\"\'')
        self.assertEqual(c, list())

    def test_request_completion(self):
        c = self.get_completions('B')
        result = transform(['Buckets'])
        assertCountEqual(self, c, result)
        c = self.request_completions('B')
        result = transform(['Buckets'])
        assertCountEqual(self, c, result)

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

    def test_handle_invalid_identifier_lbracket(self):
        c = self.get_completions('Foo[')
        result = list()
        assertCountEqual(self, c, result)

    def test_complete_custom_list_first(self):
        c = self.get_completions('[')
        result = transform(['Buckets', 'Owner'])
        assertCountEqual(self, c, result)

    def test_complete_custom_hash_first(self):
        c = self.get_completions('{foo:')
        result = transform(['Buckets', 'Owner'])
        assertCountEqual(self, c, result)

    def test_complete_filter(self):
        c = self.get_completions('Buckets[?')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)
        c = self.request_completions('Buckets[?')
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

    def test_handle_bad_filter_rbracket(self):
        c = self.get_completions('Buckets[?CreationDate==*]')
        result = list()
        assertCountEqual(self, c, result)

    def test_complete_filter_rbracket_dot(self):
        c = self.get_completions('Buckets[?CreationDate==\'value\'].')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)

    def test_handle_filter_with_dict_context(self):
        c = self.get_completions('Buckets[0].[?')
        result = list()
        assertCountEqual(self, c, result)

    def test_handle_filter_with_list_subcontext(self):
        c = self.get_completions('Buckets[].[Name].[?')
        result = list()
        assertCountEqual(self, c, result)

    def test_handle_bad_subexpression_lbracket(self):
        c = self.get_completions('Buckets.[')
        result = list()
        assertCountEqual(self, c, result)

    def test_handle_bad_index_access(self):
        c = self.get_completions('Buckets.[0]')
        result = list()
        assertCountEqual(self, c, result)
        c = self.request_completions('Buckets.[0]')
        result = list()
        assertCountEqual(self, c, result)

    def test_handle_identifier_in_brackets(self):
        c = self.request_completions('Buckets[foo]')
        result = list()
        assertCountEqual(self, c, result)

    def test_complete_flatten(self):
        c = self.get_completions('Buckets[]')
        result = list()
        assertCountEqual(self, c, result)
        c = self.request_completions('Buckets[]')
        result = list()
        assertCountEqual(self, c, result)

    def test_complete_flatten_dot(self):
        c = self.get_completions('Buckets[].')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)
        c = self.request_completions('Buckets[].')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)

    def test_complete_lbracket_star(self):
        c = self.get_completions('Buckets[*]')
        result = list()
        c = self.request_completions('Buckets[*]')
        result = list()
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

    def test_complete_flatten_pipe_lbracket(self):
        c = self.get_completions('Buckets[].CreationDate | [')
        result = transform(['?', '*', ']'])
        assertCountEqual(self, c, result)

    def test_dot_lbracket_with_dict_context(self):
        c = self.get_completions('Buckets[].[')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)

    def test_dot_lbracket_with_list_context(self):
        c = self.get_completions('Buckets.[')
        result = list()
        assertCountEqual(self, c, result)

    def test_colon_first(self):
        c = self.get_completions(':')
        result = list()
        assertCountEqual(self, c, result)

    def test_colon_in_list(self):
        c = self.get_completions('Buckets[:')
        result = list()
        assertCountEqual(self, c, result)

    def test_colon_without_identifier(self):
        c = self.get_completions('Buckets[].{:')
        result = list()
        assertCountEqual(self, c, result)

    def test_dot_lbrace_with_dict_context(self):
        c = self.get_completions('Buckets[].{foo:')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)

    def test_custom_hash_with_comma(self):
        c = self.get_completions('Buckets[].{foo:Name, bar:')
        result = transform(['Name', 'CreationDate'])
        assertCountEqual(self, c, result)

    def test_disable_on_custom_hash(self):
        # Custom hashes are currently not supported
        c = self.get_completions('Buckets[].{foo:Name}')
        result = list()
        assertCountEqual(self, c, result)

    def test_handle_bad_dot(self):
        c = self.get_completions('.')
        result = list()
        assertCountEqual(self, c, result)

    def test_handle_star(self):
        c = self.get_completions('Buckets[0].*.')
        result = list()
        assertCountEqual(self, c, result)

    def test_handle_number_dot(self):
        c = self.get_completions('42.')
        result = list()
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
