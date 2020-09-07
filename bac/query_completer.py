# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import copy
import re

import jmespath

from botocore.exceptions import UnknownServiceError
from botocore.model import OperationNotFoundError
from botocore.session import Session
from intervaltree import IntervalTree
from prompt_toolkit.completion import Completer, Completion
from six import text_type

from bac.data_tables import build_command_table
from bac.errors import (
        InvalidShapeData, ModelLoadingError, NullIntervalException)
from bac.shape_parser import ShapeParser

_FIND_IDENTIFIER = re.compile(r'\w*')
COMPLEX_SIGNS = {'flatten', 'filter'}
CONTEXT_RESET_SIGNS = {
        'comma', 'and', 'or', 'lt', 'gt', 'lte', 'gte', 'ne', 'eq'}
ENCLOSURE_MATCH = {'lparen': 'rparen',
                   'lbrace': 'rbrace',
                   'lbracket': 'rbracket',
                   'filter': 'rbracket'}
IDENTIFIERS = {'unquoted_identifier', 'quoted_identifier'}
STRINGS = {'unquoted_identifier', 'quoted_identifier', 'literal'}
JMESPATH_FLATTEN = jmespath.compile('[] | [0]')
LBRACKET = ['[']
LBRACKETS_CONTINUATION = ['?', '*', ']']


class QueryCompleter(Completer):
    """
    Suggests JMESPath query syntax completions.

    After receiving AWS service and operation names in form
    of awscli command and subcommand, an output shape loaded
    from botocore Session is parsed by the ShapeParser object.
    This object returns a "Dummy response", which is used in
    attempt to provide sensible suggestions.

    At the moment, this completer is unable to provide suggestions
    for JMESPath functions and custom hashes and arrays.
    """
    def __init__(self, session, **kwds):
        self._session = Session(profile=session.profile_name)
        self._command_table = None
        self._shape_parser = ShapeParser()
        self._lexer = jmespath.lexer.Lexer()
        self._service = None
        self._operation = None
        # Attributes below change as the query changes.
        # They are used to to track state to provide suggestions.
        self._should_reparse = True
        self._shape_dict = None
        self._context = None
        self._last_pos = 0
        self._implicit_context = []
        self._stack = []
        self._tree = IntervalTree()
        self._start = 0
        self._colon = False
        self._disable = (False, 0)
        super(QueryCompleter, self).__init__(**kwds)

    @property
    def context(self):
        """
        Get the context attribute.

        This is used to track the state of mutating fake API response.
        """
        if self._context is None:
            self.context = self._shape_dict
        return self._context

    @context.setter
    def context(self, value):
        """Set the value of context attribute."""
        self._context = value

    @property
    def command_table(self):
        """
        Get the command table attribute.

        This is used to transform aws-cli command and subcommand
        into their API operation counterpart.
        """
        if self._command_table is None:
            self._command_table = build_command_table(self._session)
        return self._command_table

    def set_shape_dict(self, service, operation):
        """
        Set the fake response (shape dict).

        This is based on received aws-cli service and operation
        (command, subcommand).
        """
        shape_dict = self._get_shape_dict(service, operation)
        self._shape_dict = shape_dict
        self.context = shape_dict

    def reset(self):
        """Reset the state of the completer."""
        self.context = None
        self._implicit_context = list()
        self._stack = list()
        self._tree = IntervalTree()
        self._start = 0
        self._colon = False
        self._disable = (False, 0)
        self._repeat_suggestion = False

    def get_completions(self, document, c_e):
        """
        Retrieve suggestions for the JMESPath query.

        First parse the existing part of the query with the JMESPath
        lexer. Based on the last token type, choose appropriate
        handler method. This handler method then returns a list of
        suggested completions, which are then yielded from here.

        As the query is being parsed, the Completer
        tracks the state of the query. If the query is being
        corrected, deleted or a larger chunk is pasted at once,
        the Completer has to reparse the query (rebuild the state).
        """
        if not self._shape_dict:
            return
        if self._disable[0]:
            if document.cursor_position > self._disable[1]:
                return
            self._disable = (False, 0)

        should_repeat = not bool(document.get_word_before_cursor())
        self._repeat_suggestion = c_e.completion_requested or should_repeat
        completions = self._parse_completion(document, c_e)
        self._last_pos = document.cursor_position

        if not completions:
            return

        word = document.get_word_before_cursor(pattern=_FIND_IDENTIFIER)
        for c in sorted(completions):
            start_position = 0 if len(c) == 1 else -len(word)
            yield Completion(text_type(c), start_position=start_position)

    def _parse_completion(self, document, c_e):
        text = document.text_before_cursor
        self._text = ' ' if not text else text

        try:
            self._tokens = list(self._lexer.tokenize(self._text))
        except jmespath.exceptions.LexerError:
            return

        if self._tokens[-1]['type'] == 'eof':
            self._tokens.pop()

        if not self._tokens:
            return self.context.keys()

        if self._should_reparse:
            completions = self._reparse_completion()
            self._should_reparse = False
        elif document.cursor_position > self._last_pos:
            completions = self._append_completion()
        elif (document.cursor_position == self._last_pos and
                c_e.completion_requested):
            completions = self._append_completion()
        else:
            completions = self._reparse_completion()
            self._should_reparse = True
        return completions

    def _append_completion(self):
        last_token = self._tokens[-1]
        index = len(self._tokens) - 1
        penultimate_token = self._look_back(index, 1)
        try:
            return self._handle_token(last_token, penultimate_token, index)
        except NullIntervalException as e:
            self._disable = True, e.pos
            return

    def _reparse_completion(self):
        completions = list()
        self.reset()
        for i, token in enumerate(self._tokens):
            if self._disable[0]:
                return
            penultimate_token = self._look_back(i, 1)
            if token['type'] in COMPLEX_SIGNS:
                fake_lbracket = {'type': 'lbracket',
                                 'start': token['start'],
                                 'end': token['end'] - 1}
                self._handle_token(fake_lbracket, penultimate_token, i)
            try:
                completions = self._handle_token(
                        token, penultimate_token, i)
            except NullIntervalException as e:
                self._disable = True, e.pos
                return
        return completions

    def _handle_token(self, token, prev_token, index=None):
        if not index:
            index = len(self._tokens) - 1
        handler = getattr(
                self, '_handle_%s' % token['type'],
                self._handle_others)
        return handler(token, prev_token, index)

    def _handle_lbracket(self, token, prev_token, index):
        if not prev_token:
            if isinstance(self.context, dict):
                return self.context.keys()
            return
        if not self._repeat_suggestion:
            self._switch_into_next_implicit_context(token)

        if (prev_token['type'] in IDENTIFIERS and
                isinstance(self.context, dict)):
            value = self.context.get(prev_token['value'], None)
            if isinstance(value, list):
                if not self._repeat_suggestion:
                    self.context = value
                return LBRACKETS_CONTINUATION
            self._disable = (True, token['end'])
            return

        if prev_token['type'] == 'dot':
            if isinstance(self.context, dict):
                return self.context.keys()
            self._disable = (True, token['end'])
            return

        if isinstance(self.context, list):
            return LBRACKETS_CONTINUATION

    def _handle_filter(self, token, prev_token, index):
        if self._repeat_suggestion:
            return self.context.keys()

        _, index = self._stack.pop()
        promise = token['type'], index
        self._stack.append(promise)
        if not isinstance(self.context, list):
            self._disable = (True, token['end'])
            return

        self.context = next(iter(self.context))
        if not isinstance(self.context, dict):
            self._disable = (True, token['end'])
            return

        self._implicit_context = copy.deepcopy(self.context)
        end = self._tree.end() - 1
        start = next(iter(self._tree.at(end))).begin
        self._tree[start:token['start']] = self._implicit_context
        return self.context.keys()

    def _handle_lbrace(self, token, _, index):
        if not isinstance(self.context, dict):
            self._disable = (True, token['end'])
            return
        if not self._repeat_suggestion:
            self._switch_into_next_implicit_context(token)

    def _handle_colon(self, token, prev_token, index):
        if not self._stack:
            self._disable = True, token['end']
            return
        if self._stack[-1][0] == 'lbracket':
            return
        if self._stack[-1][0] == 'lbrace':
            if not self._colon and prev_token['type'] in IDENTIFIERS:
                self._colon = True
                return self.context.keys()

    def _handle_flatten(self, token, _, index):
        if self._repeat_suggestion:
            return
        self.context = JMESPATH_FLATTEN.search(self.context)
        old_end = token['end']
        self._tree[self._start:old_end] = self._implicit_context
        _, returning_context_index = self._stack.pop()
        context_interval = next(iter(self._tree[returning_context_index]))
        self._implicit_context = context_interval.data
        self._start = old_end

    def _handle_rbracket(self, token, prev_token, index):
        if self._repeat_suggestion:
            return
        is_filter = (self._stack and self._stack[-1][0] == 'filter')
        self._switch_from_prev_implicit_context(token)
        # Handle [*] projection and index access (e.g.: lst[1])
        if prev_token and prev_token['type'] in {'star', 'number'}:
            # need antepenultimate (third to last) token info
            apu_token = self._look_back(index, 2)
            if apu_token and apu_token['type'] == 'lbracket':
                if isinstance(self.context, list):
                    self.context = next(iter(self.context))
            else:
                self._disable = (True, token['end'])
        elif prev_token and prev_token['type'] in STRINGS:
            if not is_filter:
                self._disable = (True, token['end'])

    def _handle_rbrace(self, token, _, index):
        self._disable = True, token['end']
        return

    def _handle_dot(self, token, prev_token, index):
        if not prev_token:
            self._disable = (True, token['end'])
            return
        # Applying subexpression to a JSON object
        if isinstance(self.context, dict):
            if self._repeat_suggestion:
                return self.context.keys()
            # Simulate application of * projection
            if prev_token['type'] == 'star':
                new_context = list(self.context.values())
            # Receive the value of identifier
            elif prev_token['type'] in IDENTIFIERS:
                new_context = self.context.get(prev_token['value'], None)
            elif prev_token['type'] in {'rbracket', 'flatten'}:
                new_context = self.context
            # Nothing else is applicable to JSON objects
            else:
                new_context = dict()
            self.context = new_context
            if isinstance(self.context, dict):
                return self.context.keys()
        # Applying subexpression to a JSON list
        if isinstance(self.context, list):
            if prev_token['type'] == 'flatten':
                self.context = next(iter(self.context))
                if isinstance(self.context, dict):
                    return self.context.keys()
            if prev_token['type'] == 'rbracket':
                return LBRACKET
            self._disable = (True, token['end'])

    def _handle_pipe(self, token, _, index):
        if not self._repeat_suggestion:
            if self._stack:
                pos = self._stack[-1][1]
                context_interval = next(iter((self._tree[pos])))
                context = context_interval.data
                lhs = self._text[pos:token['start']]
                tokens = list(self._lexer.tokenize(lhs))
                for a_token in reversed(tokens):
                    if a_token['type'] in {'colon', 'comma'}:
                        lhs = lhs[a_token['end']:]
                        break
            else:
                lhs = self._text[:token['start']]
                context = self._shape_dict

            tokens = list(self._lexer.tokenize(lhs))
            lhs = self._remove_filters(lhs, tokens)
            try:
                result = jmespath.search(lhs, context)
            except jmespath.exceptions.JMESPathError:
                return
            self.context = result

        if isinstance(self.context, list):
            return LBRACKET
        if isinstance(self.context, dict):
            return self.context.keys()

    def _handle_others(self, token, _, index):
        if (token['type'] == 'comma' and
                self._stack and self._stack[-1][0] == 'lbrace'):
            self._colon = False
            return

        # Drop to fallback context on these... (&& || , > < etc...)
        if token['type'] in CONTEXT_RESET_SIGNS:
            if not self._repeat_suggestion:
                self.context = copy.deepcopy(self._implicit_context)
            if isinstance(self.context, dict):
                return self.context.keys()

        if token['type'] in IDENTIFIERS:
            if (self._stack and self._stack[-1][0] == 'lbrace' and
                    not self._colon):
                return
            identifier = token['value']
            if isinstance(self.context, dict):
                value = self.context.get(identifier, None)
                if isinstance(value, list):
                    return LBRACKET
                completions = [c
                               for c
                               in self.context.keys()
                               if c.startswith(identifier)]
                return completions

    def _switch_into_next_implicit_context(self, token):
        old_end = token['end']
        if self._start == old_end:
            raise NullIntervalException(token['end'])
        self._implicit_context = copy.deepcopy(self.context)
        self._tree[self._start:old_end] = self._implicit_context
        self._start = old_end
        promise = token['type'], old_end - 1
        self._stack.append(promise)

    def _switch_from_prev_implicit_context(self, token):
        if (not self._stack or
                ENCLOSURE_MATCH[self._stack[-1][0]] != token['type']):
            self._disable = (True, token['end'])
            return
        old_end = token['end']
        if self._start == old_end:
            raise NullIntervalException(token['end'])
        self._tree[self._start:old_end] = self._implicit_context
        _, returning_context_index = self._stack.pop()
        self._implicit_context = self._tree[returning_context_index]
        self._start = old_end

    def _look_back(self, index, offset):
        if index < offset:
            return
        index = index - offset
        return self._tokens[index]

    def _remove_filters(self, expression, tokens):
        intervals = self._detect_filters(tokens)
        for interval in reversed(intervals):
            start, end = interval
            expression = expression[:start] + expression[end:]
        return expression

    def _detect_filters(self, tokens):
        in_filter_context = False
        counter = 0
        intervals = list()
        for token in tokens:
            if not in_filter_context and token['type'] == 'filter':
                in_filter_context = True
                start = token['start']
            elif in_filter_context:
                if token['type'] in {'filter', 'lbracket'}:
                    counter += 1
                elif token['type'] == 'rbracket':
                    if counter == 0:
                        in_filter_context = False
                        end = token['end']
                        intervals.append((start, end))
                    else:
                        counter -= 1
        return intervals

    def _get_shape_dict(self, service, operation):
        try:
            service, operation = (
                    self._get_transformed_names(service, operation))
        except InvalidShapeData:
            return None

        try:
            return self._parse_shape(service, operation)
        except ModelLoadingError:
            return None

    def _get_transformed_names(self, service, operation):
        if service == 's3api':
            service = 's3'
        service_data = self.command_table.get(service, None)
        if not service_data:
            raise InvalidShapeData()
        operation = service_data.get_operation_name(operation)
        if not operation:
            raise InvalidShapeData()
        return service, operation

    def _parse_shape(self, service, operation):
        if service != self._service:
            self._service_model = self._load_service_model(service)
            operation_model = (
                    self._load_operation_model(self._service_model, operation))
            parsed = self._shape_parser.parse(operation_model.output_shape)
            self._service = service
            self._operation = operation
            return parsed

        if operation != self._operation:
            operation_model = (
                    self._load_operation_model(self._service_model, operation))
            parsed = self._shape_parser.parse(operation_model.output_shape)
            self._operation = operation
            return parsed

        return self._shape_dict

    def _load_service_model(self, service_name):
        try:
            service_model = self._session.get_service_model(service_name)
        except UnknownServiceError as e:
            raise ModelLoadingError(str(e))
        return service_model

    def _load_operation_model(self, service_model, operation):
        try:
            operation_model = service_model.operation_model(operation)
        except OperationNotFoundError as e:
            raise ModelLoadingError(str(e))
        return operation_model
