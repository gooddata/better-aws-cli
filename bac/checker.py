# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import sys

from awscli.argparser import MainArgParser
from awscli.arguments import CustomArgument
from botocore.exceptions import BotoCoreError, ClientError
from botocore.session import Session

from bac.data_tables import build_command_table, build_argument_table
from bac.errors import (ArgumentParserDoneException, BACError,
                        CLICheckerSyntaxError, CLICheckerPermissionException)

log = logging.getLogger(__name__)


class CLIChecker(object):
    """
    Provides syntax, type and privilege checks for commands.

    This class is inspired by awscli.driver.CLIDriver class.
    It mimicks the way, in which the aws-cli commands are parsed,
    but if the parsing is successful, it doesn't execute the command.
    """
    def __init__(self, profile):
        """
        :param profile: Arbitrary valid profile name, which is used
            to load data needed for providing the checks.
        :type: str
        :rtype: None
        """
        self._cli_data = None
        self._command_table = None
        self._argument_table = None
        self._parser = None
        self._sessions = dict()
        self._session = self._init_dataloader_session(profile)

    def _init_dataloader_session(self, profile):
        """
        Initialization of arbitrary session is needed here.
        This session is then used to get AWS service data.
        Which profile/identity this session belongs to
        is not important here.
        """
        session = Session(profile=profile)
        self._sessions[profile] = session
        return session

    def _get_profile_session(self, profile):
        if profile not in self._sessions:
            self._sessions[profile] = Session(profile=profile)
        return self._sessions[profile]

    def _get_cli_data(self):
        # Data in here is needed in the BACMainArgParser
        if self._cli_data is None:
            self._cli_data = self._session.get_data('cli')
        return self._cli_data

    @property
    def command_table(self):
        if self._command_table is None:
            self._command_table = build_command_table(self._session)
        return self._command_table

    @property
    def argument_table(self):
        if self._argument_table is None:
            cli_data = self._get_cli_data()
            self._argument_table = build_argument_table(cli_data)
        return self._argument_table

    @property
    def parser(self):
        if self._parser is None:
            self._parser = self._create_parser(self.command_table)
        return self._parser

    def _create_cli_argument(self, option_name, option_params):
        return CustomArgument(
            option_name, help_text=option_params.get('help', ''),
            dest=option_params.get('dest'),
            default=option_params.get('default'),
            action=option_params.get('action'),
            required=option_params.get('required'),
            choices=option_params.get('choices'),
            cli_type_name=option_params.get('type'))

    def _create_parser(self, command_table):
        cli_data = self._get_cli_data()
        parser = BACMainArgParser(
                command_table, self._session.user_agent(),
                cli_data.get('description', None),
                self.argument_table,
                prog='aws')
        return parser

    def check(self, args):
        """
        Check syntax and type correctness of recieved aws-cli command.

        This is simillar to how aws-cli commands are parsed within
        the awscli.driver.CLIDriver class. Except, the actual
        execution is omitted, and name of parsed operation is returned
        for further use.

        :param args: received aws-cli command arguments
        :type: list
        :rtype: str
        """
        log.debug('Syntax checking following aws command: %s' % args)
        command_table = self.command_table
        try:
            parsed_args, remaining = self.parser.parse_known_args(args)
        except ArgumentParserDoneException:
            msg = ('When parsing awscli global optional arguments and service'
                   ' an exception was raised with following arguments: %s '
                   % args)
            raise CLICheckerSyntaxError(msg)

        # Syntax and permission check for awscli s3 commands not supported.
        if parsed_args.command == 's3':
            print('Checks for s3 file commands are not supported.')
            return
        # Change 's3api' to 's3', since botocore doesn't recognize 's3api'
        if parsed_args.command == 's3api':
            parsed_args.command = 's3'

        command = parsed_args.command
        try:
            action_name = command_table[command](remaining, parsed_args)
        except ArgumentParserDoneException:
            msg = ('When parsing %s arguments, an exception was raised'
                   'with following arguments: %s ' % (command, args))
            raise CLICheckerSyntaxError(msg)
        operation = '%s:%s' % (command, action_name)
        return operation

    def privilege_check(self, operation, profile):
        """
        Check if profile has sufficient privileges to execute command.

        Method attempts to retrieve needed information about recieved
        profile (User ARN), and then makes call to the IAM API
        SimulatePrincipalPolicy operation, which checks if recieved
        operation can be executed by the profile.
        This usually does not work for assumed Role profiles, as they
        usually do not have sufficient permissions to make the STS and
        IAM operation calls that are needed.

        :param operation: AWS API operation name, which is used to
            call the SimulatePrincipalPolicy operation.
        :type: str
        :param profile: profile name to check privileges for
        :type: str
        :rtype: None
        """
        session = self._get_profile_session(profile)
        log.debug('Simulating policies for %s.' % operation)
        try:
            self._simulate_policies(operation, session)
        except (BotoCoreError, ClientError) as e:
            msg = ('Failed to check for sufficient privileges.'
                   ' Check done for %s profile, %s operation.'
                   ' Following erorr occured: %s.'
                   % (profile, operation, str(e)))
            raise BACError(msg)

    def _simulate_policies(self, operation, session):
        # Does not usually work for assumed roles. :(
        sts = session.create_client('sts')
        response = sts.get_caller_identity()
        identity = response['Arn']

        iam = session.create_client('iam')
        response = iam.simulate_principal_policy(PolicySourceArn=identity,
                                                 ActionNames=[operation])
        log.debug('Policy simulation for %s returned following response: %s'
                  % (operation, response))

        results = next(iter(response['EvaluationResults']))
        if results['EvalDecision'] != 'allowed':
            self._handle_deny(results)
        log.debug('Received "allowed" for "%s"' % operation)

    def _handle_deny(self, result):
        action = result['EvalActionName']
        decision = result['EvalDecision']
        msg = ('API Action %s received %s when checking for privileges.'
               % (action, decision))
        raise CLICheckerPermissionException(msg)


class BACMainArgParser(MainArgParser):
    """
    Overrides the exit method of the argparse.ArgumentParser.

    This is done to prevent the calls of sys.exit method.
    """
    def exit(self, status=0, message=None):
        raise ArgumentParserDoneException(message)
