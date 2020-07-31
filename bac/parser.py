# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import shlex

from six import string_types

from bac.constants import BATCH_JOB_SECTIONS
from bac.errors import BatchJobSyntaxException

log = logging.getLogger(__name__)


class Parser(object):
    """
    Encapsulates parsing and syntax checking of batch commands.

    Parser object which encapsulates the parsing and syntax checking
    of yaml batch job definitions.
    """
    def __init__(self):
        pass

    def parse(self, job_definition):
        """
        Parse the batch command definition.

        Method takes dict parsed from yaml definition as an argument.
        This definition should contain two main sections:
        - command: aws <command> <subcommand>
        - optionals: {nested dictionaries}

        For example:
            ---
            command: aws <command> <subcommand>
            optionals:
              "--profile":
                testing:
                  "--region":
                    - us-east-1
                    - eu-west-1
                dev:
                  "--region":
                    - us-east-1
                    - eu-west-1
                    ... etc. ...

        Method returns a list of assembled commands.

        :param job_definition: A parsed YAML command definition
        :type: dict
        :rtype: list
        """
        self._syntax_check(job_definition)

        log.info('Parsing batch job definition...')
        commands_dicts = list()

        def parse_dict(ns, dic):
            n_dict = dict()
            list_dict = dict()

            for k, v in dic.items():
                # Optional parameter with single value
                if isinstance(v, string_types):
                    ns[k] = v.strip()
                if isinstance(v, int):
                    ns[k] = v
                # Boolean toggle optional parameter
                if isinstance(v, bool):
                    if v:
                        ns[k] = ''
                # If value is False, null or missing,
                # it means this command opted out of fallback for that option
                if not v:
                    if k in ns:
                        del ns[k]
                # Prepare nested dictionaries for additional parsing
                if isinstance(v, dict):
                    n_dict[k] = v
                # List of variations of arguments for optional parameter
                if isinstance(v, list):
                    list_dict[k] = v

            # Reached maximum nesting, add
            # created command dictionary to collection
            if not (n_dict or list_dict):
                commands_dicts.append(dict(ns))
                return

            for k, v in n_dict.items():
                parse_param_dict(dict(ns), k, v)

            for k, lst in list_dict.items():
                parse_param_list(dict(ns), k, lst)

        def parse_param_dict(ns, key, dic):
            for k, v in dic.items():
                ns[key] = k
                parse_dict(dict(ns), v)

        def parse_param_list(ns, key, lst):
            for item in lst:
                ns[key] = item
                commands_dicts.append(dict(ns))

        parse_dict(dict(), job_definition['optionals'])

        base_cmd = shlex.split(job_definition['command'])
        commands = list()
        for optionals in commands_dicts:
            command = list(base_cmd)
            for optional in optionals.items():
                command.extend(optional)
            commands.append(command)

        return commands

    def _syntax_check(self, job_definition):
        log.debug('Checking syntax validity of batch job definition...')
        given = set(job_definition.keys())
        difference = given.symmetric_difference(BATCH_JOB_SECTIONS)
        if difference:
            msg = ('Either additional section definitions were given,'
                   ' or they are missing. Received: %s  Required: %s'
                   % (given, BATCH_JOB_SECTIONS))
            raise BatchJobSyntaxException(msg, ['main_body'])

        self._check_optionals_syntax(job_definition['optionals'])
        log.debug('Success. Syntax is valid.')

    def _check_optionals_syntax(self, dictionary):

        def check_option_dict(dic, trace, last_trace=None):
            if last_trace:
                trace.append(last_trace)
            for k, v in dic.items():
                if isinstance(v, dict):
                    check_arg_dict(v, list(trace), k)
                if isinstance(v, list):
                    check_arg_list(v, list(trace), k)

        def check_arg_dict(dic, trace, last_trace):
            trace.append(last_trace)
            for k, v in dic.items():
                if not isinstance(v, dict):
                    msg = ('Dictionary values of optional arguments'
                           ' always have to be dictionaries.')
                    raise BatchJobSyntaxException(msg, trace)
                check_option_dict(v, list(trace), k)

        def check_arg_list(lst, trace, last_trace):
            trace.append(last_trace)
            for i in lst:
                if isinstance(i, (list, dict, set)):
                    msg = ('List cannot contain dictionaries, sets'
                           ' or another lists.')
                    raise BatchJobSyntaxException(msg, trace)

        check_option_dict(dictionary, ['optionals'])
