# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import argparse
import logging
import os
import shlex

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import CompleteStyle
from six import text_type

from bac.bac_completer import BACCompleter
from bac.awscli_receiver import AwsCliReceiver
from bac.batch import CommandBatch
from bac.bindings import Bindings
from bac.checker import CLIChecker
from bac.constants import (BAC_PROMPT, BAC_HISTORY, IGNORED_ENV_VARS,
                           PROFILE_MANAGER_COMMANDS)
from bac.errors import ArgumentParserDoneException, BACError
from bac.profile_manager import ProfileManager
from bac.toolbar import Toolbar
from bac.utils import ArgumentParser, GlobalsParser

log = logging.getLogger(__name__)


def parse_args():
    """Parse arguments and provide help messages."""
    desc = ('Better Aws Cli (BAC) is an interactive shell that'
            ' enhances aws-cli functionality. Users can execute all'
            ' aws-cli commands as usual but are presented with the'
            ' addition of some features and enhancements.\n '
            '\n'
            'With Better Aws Cli, users can manage multiple AWS'
            ' accounts and regions at once. The management of multiple'
            ' AWS accounts is achieved with the help of pre-defined'
            ' aws-cli profiles. Once the profiles are defined as'
            ' desired, users can change which profiles are considered'
            ' active at any time. Executed commands are then applied'
            ' to all currently active profiles unless a different'
            ' profile is provided explicitly using the --profile'
            ' parameter. In such a case, the explicit definition of a'
            ' profile takes precedence before currently active'
            ' profiles. The same principles apply to AWS regions.'
            ' The regions, however, do not need to be predefined'
            ' by the user.')
    parser = ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description=desc)
    commands = add_parser_commands(parser)
    commands.add_parser('aws', help='aws-cli command execution')
    return parser.parse_args


def add_parser_commands(parser):
    """Setup help messages for commands."""
    commands = parser.add_subparsers()
    for command, command_help in PROFILE_MANAGER_COMMANDS.items():
        commands.add_parser(command, help=command_help)
    return commands


class BAC(object):
    """
    The main Better AWS CLI driver.

    Initialization of the tool as well as the delegation of
    all of the "work" is taken care of within this class.
    """
    def __init__(self):
        self._fuzzy = True
        self._cache_completion = True
        self._profile_manager = ProfileManager()
        self._checker = CLIChecker(self._profile_manager.get_first_profile())
        self._aws_cli = AwsCliReceiver(self._profile_manager, self._checker)
        self._bac_global_parser = self._create_bac_global_parser()
        self._completer = BACCompleter(self._profile_manager)
        self._bindings = Bindings(self.toggle_fuzzy,
                                  self.toggle_cache,
                                  self.refresh_cache)
        self._prompt_session = (
                PromptSession(text_type(BAC_PROMPT),
                              history=FileHistory(BAC_HISTORY),
                              completer=self._completer,
                              complete_while_typing=True,
                              complete_style=CompleteStyle.MULTI_COLUMN,
                              key_bindings=self._bindings.bindings,
                              bottom_toolbar=self._get_toolbar_handler()))
        self._env_var_check()

    def toggle_fuzzy(self):
        """Toggle the fuzzy completions on/off."""
        self._completer.toggle_fuzzy()
        self._fuzzy = not self._fuzzy

    def toggle_cache(self):
        """Toggle cached resource completion on/off."""
        self._completer.toggle_cache()
        self._cache_completion = not self._cache_completion

    def refresh_cache(self):
        """Refresh all resource cache."""
        self._completer.refresh_cache()

    def run_cli(self):
        """Run the main Better AWS CLI loop."""
        while True:
            cli_input = self._prompt_session.prompt()
            try:
                argv = shlex.split(text_type(cli_input))
            except ValueError as e:
                print('Invalid command: \"%s\".' % str(e))
                continue

            try:
                self._work_input(argv)
            except KeyboardInterrupt:
                # Interrupt the process/command but do not exit REPL
                log.debug('Interrupt received.')
            except BACError as e:
                log.error('Following exception has been raised: %s' % str(e))

    def _work_input(self, argv):
        if not argv:
            return

        parsed_args, remainder = self._bac_global_parser.parse_known_args(argv)

        if not remainder:
            if parsed_args:
                log.warn('Received global optional argument(s)'
                         ' without any additional action.')
            return

        choice = remainder[0]
        log.debug('Choice made: %s' % choice)

        if choice == 'aws':
            self._aws_cli.execute_awscli_command(remainder, parsed_args)
            return

        if choice == 'batch-command':
            CommandBatch(parsed_args, remainder, self._checker)
            return

        if self._profile_manager.handle_command(choice, remainder):
            return

        try:
            parse_args()(remainder)
        except ArgumentParserDoneException:
            pass

    def _get_toolbar_handler(self):
        toolbar = Toolbar(
                lambda: self._fuzzy,
                lambda: self._cache_completion,
                lambda: self._profile_manager.active_profiles,
                lambda: self._profile_manager.active_regions)
        return toolbar.handler

    def _create_bac_global_parser(self):
        parser = GlobalsParser(add_help=False)
        parser.add_argument(
                '--bac-dry-run', '-d', action='store_true', dest='dry_run',
                help='Do not execute awscli command after it is checked')
        parser.add_argument(
                '--bac-no-check', '-n', action='store_false', dest='check',
                help=('Do not syntax/type check awscli command prior to its'
                      ' execution'))
        parser.add_argument(
                '--bac-priv-check', '-p', action='store_true',
                dest='priv_check', help=('Attempt to check for sufficient'
                                         'privileges before executing an'
                                         ' awscli command'))
        return parser

    def _env_var_check(self):
        ignored = list()
        for var in IGNORED_ENV_VARS:
            if var in os.environ:
                ignored.append(var)
        if ignored:
            log.warn('Following environmental variables have been'
                     ' detected: %s. However, these are not supported'
                     ' by the tool and consequently the tool will'
                     ' behave as if they were not set.' % ignored)
