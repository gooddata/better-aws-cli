# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import six

from prompt_toolkit.completion import Completer
from prompt_toolkit.completion.word_completer import WordCompleter
from prompt_toolkit.document import Document


class NestedCompleter(Completer):
    """
    Backport of prompt_toolkit.completion.NestedCompleter class.

    Completer which wraps around several other completers, and calls
    any the one that corresponds with the first word of the input.

    This class is available as a part of prompt toolkit library version
    3.0.5 or higher. In order to ensure Python 2/3 compatibility,
    python-prompt-toolkit version 2.0.9 is used within this project.
    In order to ensure the compatibility, yielded completions are
    wrapped in six.text_type.
    """
    def __init__(self, options, ignore_case=True):
        """
        :param options: Dict of options to complete from
        :type: dict
        :param ignore_case: Decides case sensitivity of the completer
        :type: bool
        :rtype: None
        """
        self.options = options
        self.ignore_case = ignore_case

    @classmethod
    def from_nested_dict(cls, data):
        """
        Create a `NestedCompleter`, starting from a nested dictionary data
        structure, like this:

        .. code::

            data = {
                'show': {
                    'version': None,
                    'interfaces': None,
                    'clock': None,
                    'ip': {'interface': {'brief'}}
                },
                'exit': None
                'enable': None
            }

        The value should be `None` if there is no further completion at some
        point. If all values in the dictionary are None, it is also possible to
        use a set instead.

        Values in this data structure can be a completers as well.
        """
        options = {}
        for key, value in data.items():
            if isinstance(value, Completer):
                options[key] = value
            elif isinstance(value, dict):
                options[key] = cls.from_nested_dict(value)
            elif isinstance(value, set):
                options[key] = cls.from_nested_dict(
                        {item: None for item in value})
            else:
                assert value is None
                options[key] = None

        return cls(options)

    def get_completions(self, document, complete_event):
        # Split document.
        text = document.text_before_cursor.lstrip()
        stripped_len = len(document.text_before_cursor) - len(text)

        # If there is a space, check for the first term, and use a
        # subcompleter.
        if " " in text:
            first_term = text.split()[0]
            completer = self.options.get(first_term)

            # If we have a sub completer, use this for the completions.
            if completer is not None:
                remaining_text = text[len(first_term):].lstrip()
                move_cursor = len(text) - len(remaining_text) + stripped_len

                new_document = Document(
                    remaining_text,
                    cursor_position=document.cursor_position - move_cursor,
                )

                for c in completer.get_completions(
                                new_document, complete_event):
                    yield c

        # No space in the input: behave exactly like `WordCompleter`.
        else:
            keys = sorted(six.text_type(key) for key in self.options.keys())
            completer = WordCompleter(keys, WORD=True,
                                      ignore_case=self.ignore_case)
            for c in completer.get_completions(document, complete_event):
                yield c
