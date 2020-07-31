# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
"""
This test suite for nested completer is insiped by the one
implemented within the python-prompt-toolkit (ver. >= 3.0)
library github repository.
"""
import unittest

from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from six import assertCountEqual, text_type

from tests._utils import _import, transform

nested = _import('bac', 'nested_completer')


class NestedCompleterTest(unittest.TestCase):
    def setUp(self):
        self.completer = nested.NestedCompleter.from_nested_dict(
            {
                "show": {
                    "version": None,
                    "clock": None,
                    "interfaces": None,
                    "ip": {"interface": {"brief"}},
                },
                "exit": None,
            }
        )

    def get_completion(self, text):
        text = text_type(text)
        doc = Document(text, len(text))
        c_e = CompleteEvent()
        completions = self.completer.get_completions(doc, c_e)
        return [text_type(c.text) for c in completions]

    def test_empty_input(self):
        # Empty input.
        c = self.get_completion('')
        result = transform(['show', 'exit'])
        assertCountEqual(self, c, result)

    def test_single_char(self):
        # One character.
        c = self.get_completion('s')
        result = transform(['show'])
        assertCountEqual(self, c, result)

    def test_one_word(self):
        # One word.
        c = self.get_completion('show')
        result = transform(['show'])
        assertCountEqual(self, c, result)

    def test_one_word_space(self):
        # One word + space.
        c = self.get_completion('show ')
        result = transform(['version', 'clock', 'interfaces', 'ip'])
        assertCountEqual(self, c, result)

    def test_one_word_space_one_char(self):
        # One word + space + one character.
        c = self.get_completion('show i')
        result = transform(['ip', 'interfaces'])
        assertCountEqual(self, c, result)

    def test_one_space_one_word_space_one_char(self):
        # One space + one word + space + one character.
        c = self.get_completion(' show i')
        result = transform(['ip', 'interfaces'])
        assertCountEqual(self, c, result)

    def test_nested_set(self):
        # Test nested set.
        c = self.get_completion('show ip interface br')
        result = transform(['brief'])
        assertCountEqual(self, c, result)
