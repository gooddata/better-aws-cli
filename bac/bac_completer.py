# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import os

from awscli.completer import Completer as AwscliCompleter
from six import text_type
from prompt_toolkit.document import Document
from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.filters import to_filter
from prompt_toolkit.completion.word_completer import WordCompleter
from prompt_toolkit.completion.fuzzy_completer import FuzzyCompleter

from bac.caching import CacheProvider
from bac.constants import CACHED_OPTIONS, PROFILE_COMMANDS, REGION_COMMANDS
from bac.nested_completer import NestedCompleter
from bac.query_completer import QueryCompleter
from bac.utils import extract_positional_args

log = logging.getLogger(__name__)


COMMANDS_MAP = {
        'aws': None,
        'batch-command': None,
        'list-available-profiles': None,
        'list-available-accounts': None,
        'list-active-profiles': None,
        'list-available-regions': None,
        'list-active-regions': None,
        'switch-profiles': None,
        'include-profiles': None,
        'exclude-profiles': None,
        'switch-regions': None,
        'include-regions': None,
        'exclude-regions': None,
}


class BACCompleter(Completer):
    """
    This class provides the tool with all of the completions.

    This is achieved with help of other subcompleters. Initialization
    of the subcompleters as well as the correct delegation of work to
    them is managed within this class.
    """

    def __init__(self, profile_manager):
        """
        :param profile_manager: an instance of ProfileManager used
            to receive currently active regions and profiles.
        :type: bac.profile_manager.ProfileManager
        :rtype: None
        """
        self._profile_manager = profile_manager
        self._fuzzy = True
        self._init_subcompleters()
        self._nested_completer = NestedCompleter.from_nested_dict(COMMANDS_MAP)
        self._cache = CacheProvider(self._profile_manager)
        self._query_context = None

    def _init_subcompleters(self):
        log.debug('Initializing completers')
        profile_names = sorted(text_type(name) for name
                               in self._profile_manager.sessions.keys())
        region_names = sorted(text_type(name) for name
                              in self._profile_manager.available_regions)

        profile_meta_dict = {
              text_type(profile): text_type(account_name)
              for profile, account_name
              in self._profile_manager.account_names.items()
        }
        profile_completer = WordCompleter(
                profile_names, WORD=True, meta_dict=profile_meta_dict)
        self._profile_completer = FuzzyCompleter(profile_completer,
                                                 enable_fuzzy=self._fuzzy)
        region_completer = WordCompleter(region_names, WORD=True)
        self._region_completer = FuzzyCompleter(region_completer,
                                                enable_fuzzy=self._fuzzy)
        cache_completer = WordCompleter([], WORD=True)
        self._cache_completer = FuzzyCompleter(cache_completer,
                                               WORD=True,
                                               enable_fuzzy=self._fuzzy)
        some_session = self._profile_manager.get_first_session()
        self._query_completer = QueryCompleter(some_session)
        self._aws_completer = AwsCompleter()

        for command in PROFILE_COMMANDS:
            COMMANDS_MAP[command] = self._profile_completer

        for command in REGION_COMMANDS:
            COMMANDS_MAP[command] = self._region_completer

            def is_yml(filename):
                return (os.path.isdir(filename)
                        or
                        filename.endswith(('.yml', '.yaml')))

        COMMANDS_MAP['batch-command'] = PathCompleter(file_filter=is_yml)

    def toggle_fuzzy(self):
        """
        Toggle the fuzzy completions on/off for all of the relevant
        subcompleters. The QueryCompleter and NestedCompleter do not
        support fuzzy completions.
        """
        log.debug('Toggling fuzzy completion.')
        self._fuzzy = not self._fuzzy
        self._profile_completer.enable_fuzzy = to_filter(self._fuzzy)
        self._region_completer.enable_fuzzy = to_filter(self._fuzzy)
        self._cache_completer.enable_fuzzy = to_filter(self._fuzzy)
        self._aws_completer.toggle_fuzzy()

    def toggle_cache(self):
        """Toggle cached resource completion on/off."""
        self._cache.toggle_cache()

    def refresh_cache(self):
        """
        Refresh all of resource cache for every active profile/region.
        """
        log.info('Refreshing resource cache...')
        self._cache.refresh_cache()
        log.info('Cache refreshed.')

    def get_completions(self, document, completion_event):
        """
        Retrieve all possible completions.

        Overrides prompt toolkit Completer's class get_completions.
        Retrieves and then yields any relevant completions provided
        by initialized subcompleters, based on context given by the
        document.

        :param document: a prompt toolkit Document object, upon which
            the completions are done. It contains the input text and
            current cursor position.
        :type Document
        :rtype None
        """
        text = document.text_before_cursor
        words = text.split()
        word = document.get_word_before_cursor(WORD=True)

        # complete custom BAC commands
        if len(words) == 0 or words[0] != 'aws':
            for c in self._nested_completer.get_completions(
                                    document, completion_event):
                yield c
            return

        last = words[-1]
        penultimate = words[-2] if len(words) > 2 else None
        is_ws = (text[-1] == ' ')

        # prevent the command from being overwritten by the suggestion
        if len(words) == 1 and not is_ws:
            return

        # complete cached resources (e.g.: --bucket my-bucket)
        if last in CACHED_OPTIONS:
            self._cache_completer.completer.words = (
                    self._cache.get_cached_resource(last))
            for c in self._cache_completer.get_completions(
                                Document(), completion_event):
                if word and not c.text.startswith(word):
                    c.text = ' %s' % c.text
                yield Completion(
                        c.text, c.start_position, c.display, c.display_meta)
            return

        if penultimate and penultimate in CACHED_OPTIONS and word:
            if not self._cache_completer.completer.words:
                self._cache_completer.completer.words = (
                        self._cache.get_cached_resource(penultimate))
            for c in self._cache_completer.get_completions(
                                Document(word), completion_event):
                yield c
            return

        if self._query_context:
            quote, start = self._query_context

            if (document.cursor_position <= start):
                if document.cursor_position < start:
                    self._query_context = None
                self._query_completer.reset()
                for c in self._query_completer.get_completions(
                        Document(text[start:]), completion_event):
                    yield c

            elif (not quote and (is_ws or last.startswith(('\'', '\"')))):
                self._query_context = None
                self._query_completer.reset()

            elif quote and quote in text[start:]:
                pass

            else:
                for c in self._query_completer.get_completions(
                        Document(text[start:]), completion_event):
                    yield c
                return

        elif last == '--query' and is_ws:
            positionals = extract_positional_args(words)
            if len(positionals) < 3:
                return
            service, operation = positionals[1:3]
            self._query_completer.set_shape_dict(service, operation)
            for c in self._query_completer.get_completions(
                    Document(text_type('')), completion_event):
                yield c
            return

        elif penultimate and penultimate == '--query' and not is_ws:
            if last.startswith(('\'', '\"')):
                start = document.cursor_position
                self._query_context = last[0], start
            else:
                start = document.cursor_position - len(last)
                self._query_context = None, start
            for c in self._query_completer.get_completions(
                    Document(text[start:]), completion_event):
                yield c
            return

        # autocomplete aws-cli commands
        for c in self._aws_completer.get_completions(
                            Document(text), completion_event):
            yield c
        return


class AwsCompleter(Completer):
    """
    Handles aws-cli completions that are returned from the aws-cli
    Completer object.
    """
    def __init__(self):
        self._fuzzy = True
        self._awscli_completer = AwscliCompleter()
        completer = WordCompleter([], WORD=True)
        self._completer = (
                FuzzyCompleter(completer, WORD=True, enable_fuzzy=self._fuzzy))
        self._word_boundary = 0

    def toggle_fuzzy(self):
        """Toggle fuzzy completion on/off."""
        self._fuzzy = not self._fuzzy
        self._completer.enable_fuzzy = to_filter(self._fuzzy)

    def get_completions(self, document, c_e):
        """
        Retrieve all possible aws-cli completions.

        Overrides prompt toolkit Completer's class get_completions.
        Retrieves and then yields completions of aws-cli commands,
        subcommands and arguments.

        :param document: a prompt toolkit Document object, upon which
            the completions are done. It contains the input text and
            current cursor position.
        :type Document
        :rtype None
        """
        text = document.text_before_cursor
        word = document.get_word_before_cursor(WORD=True)

        completions = [text_type(c) for c in self._aws_completion(text)]

        if word:
            if (len(text) < self._word_boundary or
                    not self._completer.completer.words):
                self._completer.completer.words = self._rebuild(text, word)
            elif word == '-':
                self._completer.completer.words = completions
            new_document = Document(text_type(word))
            for c in self._completer.get_completions(new_document, c_e):
                yield Completion(
                        c.text, -len(word), c.display, c.display_meta)
            self._word_boundary = len(text) - len(word)
        else:
            self._completer.completer.words = completions
            for c in completions:
                yield Completion(c, start_position=-len(word))
            self._word_boundary = len(text)

    def _rebuild(self, text, word):
        # Rebuild all available subcommands/arguments.
        offset = None
        if word[0] == '-':
            offset = len(word) - 1
        else:
            offset = len(word)
        leading_text = text[:-offset] if offset else text
        return [text_type(c) for c in self._aws_completion(leading_text)]

    def _aws_completion(self, commands):
        try:
            completions = (self._awscli_completer.complete(
                                                 commands, len(commands)))
        except Exception:
            log.error('Failed to complete aws command.', exc_info=True)
            completions = list()
        return completions
