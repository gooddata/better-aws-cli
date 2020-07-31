# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
"""
Purpose of this module is to help parse aws-cli commands,
check the corectness of their syntax, and provided parameter types.

It can be used to receive the names of AWS API services
and operations, as these differ to their aws-cli command/subcommand
counterparts.

This module is heavily inspired by the implementation of the
awscli \"CLIDriver\", \"ServiceCommand\" and \"ServiceOperation\"
classes. In this module, they are rewritten in order to prevent
various side-effects that succeed the calls of __call__ methods.
"""

import logging

from awscli.argparser import ArgTableArgParser, ServiceArgParser
from awscli.arguments import CustomArgument, UnknownArgumentError
from awscli.clidriver import ServiceCommand, ServiceOperation
from botocore import xform_name
from botocore.compat import copy_kwargs, OrderedDict

from bac.errors import ArgumentParserDoneException

log = logging.getLogger(__name__)


def build_command_table(session):
    """
    Create a command table, which contains all of the commands
    and subcommands that are available to the aws-cli.
    """
    log.debug('Building command table')
    command_table = OrderedDict()
    services = session.get_available_services()
    for service_name in services:
        command_table[service_name] = (
                BACServiceCommand(cli_name=service_name,
                                  session=session,
                                  service_name=service_name))
    # Add the 's3api' to the supported services, as it is equal to
    # botocore's 's3'
    command_table['s3api'] = command_table['s3']
    return command_table


def build_argument_table(cli_data):
    """
    Create an argument table, which contains all of the arguments
    that are available to the aws-cli. This is used in the Checker
    class to ensure correct usage of global aws-cli arguments.
    """
    log.debug('Building command table')
    argument_table = OrderedDict()
    cli_arguments = cli_data.get('options', None)
    for option in cli_arguments:
        option_params = copy_kwargs(cli_arguments[option])
        cli_argument = _create_cli_argument(option, option_params)
        cli_argument.add_to_arg_table(argument_table)
    return argument_table


def _create_cli_argument(option_name, option_params):
    return CustomArgument(
        option_name, help_text=option_params.get('help', ''),
        dest=option_params.get('dest'),
        default=option_params.get('default'),
        action=option_params.get('action'),
        required=option_params.get('required'),
        choices=option_params.get('choices'),
        cli_type_name=option_params.get('type'))


class BACServiceCommand(ServiceCommand):
    def __init__(self, *args, **kwargs):
        super(BACServiceCommand, self).__init__(*args, **kwargs)

    @property
    def command_table(self):
        if self._command_table is None:
            self._command_table = self._create_command_table()
        return self._command_table

    def get_operation_name(self, operation):
        service_operation = self.command_table.get(operation, None)
        if not service_operation:
            return
        return service_operation.operational_name

    def _create_command_table(self):
        command_table = OrderedDict()
        service_model = self._get_service_model()
        for operation_name in service_model.operation_names:
            cli_name = xform_name(operation_name, '-')
            # Receive model of operation (action/subcommand)
            operation_model = service_model.operation_model(operation_name)
            command_table[cli_name] = BACServiceOperation(
                name=cli_name,
                parent_name=self._name,
                session=self.session,
                operation_model=operation_model,
                operation_caller=None
            )
        return command_table

    def _create_parser(self):
        command_table = self.command_table
        return BACServiceArgParser(
                operations_table=command_table, service_name=self._name)


class BACServiceOperation(ServiceOperation):
    def __init__(self, *args, **kwargs):
        super(BACServiceOperation, self).__init__(*args, **kwargs)

    @property
    def operational_name(self):
        return self._operation_model.name

    def __call__(self, args, _):
        operation_parser = self._create_operation_parser(self.arg_table)
        self._add_help(operation_parser)
        parsed_args, remaining = operation_parser.parse_known_args(args)
        if remaining:
            print('unknown argument found')
            raise UnknownArgumentError(
                'Unknown options: %s' % ', '.join(remaining))
        return self.operational_name

    def _create_argument_table(self):
        argument_table = OrderedDict()
        input_shape = self._operation_model.input_shape
        required_arguments = []
        arg_dict = {}

        if input_shape is not None:
            required_arguments = input_shape.required_members
            arg_dict = input_shape.members
        for arg_name, arg_shape in arg_dict.items():
            cli_arg_name = xform_name(arg_name, '-')
            arg_class = self.ARG_TYPES.get(arg_shape.type_name,
                                           self.DEFAULT_ARG_CLASS)
            is_token = arg_shape.metadata.get('idempotencyToken', False)
            is_required = arg_name in required_arguments and not is_token
            arg_object = arg_class(
                name=cli_arg_name,
                argument_model=arg_shape,
                is_required=is_required,
                operation_model=self._operation_model,
                serialized_name=arg_name,
                event_emitter=None)
            arg_object.add_to_arg_table(argument_table)
        return argument_table

    def _create_operation_parser(self, arg_table):
        parser = BACArgTableArgParser(arg_table)
        return parser


class BACServiceArgParser(ServiceArgParser):
    def exit(self, status=0, message=None):
        if message:
            log.error(message)
        raise ArgumentParserDoneException()


class BACArgTableArgParser(ArgTableArgParser):
    def exit(self, status=0, message=None):
        if message:
            log.error(message)
        raise ArgumentParserDoneException()
