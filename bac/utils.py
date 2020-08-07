# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import argparse
import logging
import os

import subprocess32

from subprocess32 import PIPE

from bac.constants import CLI_OPTION_HAS_ARGS, PROFILE_OPTIONS
from bac.errors import ArgumentParserDoneException, TimeoutException

log = logging.getLogger(__name__)


class ArgumentParser(argparse.ArgumentParser):
    """
    Overrides the exit method of the argparse.ArgumentParser.

    This is done to prevent the calls of sys.exit method.
    """
    def exit(self, status=0, message=None):
        """Raise exception on recieving --help or parse error."""
        if message:
            log.error(message)
        raise ArgumentParserDoneException(message)


class GlobalsParser(argparse.ArgumentParser):
    """
    Overrides the exit method of the argparse.ArgumentParser.

    This is done to prevent the calls of sys.exit method.
    """
    def exit(self, status=0, message=None):
        """Log a message on error."""
        if message:
            log.warning(message)


def ensure_path(*args):
    """Ensure that the given path exists, if not, create it."""
    path = os.path.join(*args)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def execute_command(command, timeout=None):
    """Execute command with a timeout."""
    with subprocess32.Popen(command, stdout=PIPE, stderr=PIPE) as process:
        try:
            (out, err) = process.communicate(timeout=timeout)
        except subprocess32.TimeoutExpired as e:
            process.kill()
            raise TimeoutException(e)
        finally:
            return_code = process.wait()
    return out.decode('utf-8'), err.decode('utf-8'), return_code


def paginate(method, jmes_filter=None, **kwargs):
    """Paginate the AWS API output, if it's too large."""
    client = method.__self__
    paginator = client.get_paginator(method.__name__)
    page_iterator = paginator.paginate(**kwargs)
    iterator = (page_iterator.search(jmes_filter)
                if jmes_filter else page_iterator)
    for page in iterator:
        yield page


def extract_positional_args(command):
    """Extract positional arguments from aws-cli command."""
    cmd = []
    iter_command = iter(command)
    for argument in iter_command:
        if argument.startswith('-') and argument in CLI_OPTION_HAS_ARGS:
            # Ignore word if it is known option
            if CLI_OPTION_HAS_ARGS[argument]:
                # Ignore the next word if option takes argument
                next(iter_command, None)
        else:
            cmd.append(argument)
    return cmd


def extract_profile(command):
    """Extract profile name from aws-cli command."""
    iter_command = iter(command)
    for argument in iter_command:
        if argument in PROFILE_OPTIONS:
            profile = next(iter_command, None)
    return profile


class LevelFormatter(logging.Formatter):
    """
    Handles different formatting for different log levels.

    Custom log formatter which changes how log messages are formatted
    based on their log level.
    Taken from SO: https://stackoverflow.com/questions/28635679/python-logging-different-formatters-for-the-same-log-file # noqa
    """
    def __init__(self, fmt=None, datefmt=None, level_fmts={}):
        self._level_formatters = {}
        for level, format in level_fmts.items():
            self._level_formatters[level] = (
                    logging.Formatter(fmt=format, datefmt=datefmt))
        super(LevelFormatter, self).__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record):
        if record.levelno in self._level_formatters:
            return self._level_formatters[record.levelno].format(record)

        return super(LevelFormatter, self).format(record)
