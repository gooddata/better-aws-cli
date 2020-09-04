# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import os

import yaml

from six import text_type

from bac.errors import (ArgumentParserDoneException, BACError,
                        InvalidArgumentException, TimeoutException,
                        BatchJobSyntaxException)
from bac.parser import Parser
from bac.utils import ArgumentParser, execute_command, extract_profile

log = logging.getLogger(__name__)


class CommandBatch(object):
    """
    Encapsulates the parse and execution of predefined command batch.
    """
    def __init__(self, global_args, argv, checker):
        """
        :param global_args: Namespace which contains BAC global
            arguments such as "--bac-dry-run".
        :type argparse.Namespace
        :param argv: Argument vector of executed batch-command.
            This usually contains the path command batch definition.
        :type list
        :param checker: The checker object used for command checking.
        :type bac.checker.CLIChecker
        :rtype None
        """
        self._global_args = global_args
        self._args = self._parse_args(argv)
        self._checker = checker
        self._parser = Parser()
        self._commands = list()
        self._run()

    def _run(self):
        if not self._args:
            return
        self._prepare_batch_command()
        self._execute_batch_command(self._args.timeout)

    def _parse_args(self, argv):
        # discard the "batch-command" string
        argv = argv[1:]

        description = ('Parses a YAML defined command batch definition'
                       ' and then sequentially executes assembled commands.')
        parser = ArgumentParser(description=description)
        parser.add_argument(
                'path', type=str, help='Path to the batch command definition')
        parser.add_argument(
                '--timeout', '-t', type=int, dest='timeout', default=30,
                help=('maximum time (in seconds) until execution of'
                      ' a command is interrupted'))
        try:
            return parser.parse_args(argv)
        except ArgumentParserDoneException:
            return

    def _prepare_batch_command(self):
        job_definition = self._load_batch_command(self._args.path)
        try:
            self._commands = self._parser.parse(job_definition)
        except BatchJobSyntaxException as e:
            raise BACError(str(e))

    def _execute_batch_command(self, timeout):
        if self._global_args.check:
            for command in self._commands:
                log.debug('Checking command: "%s"' % ' '.join(command))
                argv = command[1:]
                operation = self._checker.check(argv)
                if self._global_args.priv_check:
                    profile = extract_profile(argv)
                    if profile:
                        self._checker.privilege_check(operation, profile)
                    else:
                        log.warning('Cannot privilege check if no profile'
                                    ' is specified in the command definition')

        if self._global_args.dry_run:
            log.debug('Dry running only, check finished.')
            return

        for command in self._commands:
            log.info('Executing command: "%s"' % command)
            try:
                out, err, exit_code = execute_command(command, timeout)
            except TimeoutException:
                log.error('Timeout of %s seconds reached when executing'
                          ' following command:\n%s' % (timeout, command))
                continue

            if exit_code:
                log.warning('Command "%s" ended with following non-zero exit'
                            ' code: %s' % (command, exit_code))
                if err:
                    err = err.decode('utf-8')
                    log.error('An error occured: "%s"' % text_type(err))
            if out:
                print(out.decode('utf-8'))

    def _load_batch_command(self, path):
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            msg = ('Provided path is invalid or user has insufficient'
                   ' access rights. Path given: %s' % path)
            raise InvalidArgumentException(msg)

        if path.endswith(('.yml', '.yaml')):
            return self._load_yaml(path)

        msg = ('Format given is not supported. Use YAML'
               ' to specify batch command execution.')
        raise InvalidArgumentException(msg)

    def _load_yaml(self, path):
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            msg = ('Failed to load the batch command from "%s".'
                   ' Following error has occured:\n%s' % (path, str(e)))
            raise BACError(msg)
