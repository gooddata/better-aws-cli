# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import os
import subprocess

from botocore.exceptions import ClientError

from bac.constants import (EC2_REGIONS_JMES, IGNORED_ENV_VARS,
                           PROFILE_OPTIONS, REGION_OPTIONS)
from bac.errors import InvalidAwsCliCommandError
from bac.utils import extract_positional_args, extract_profile, paginate

log = logging.getLogger(__name__)


class AwsCliReceiver(object):
    """
    Handles the execution of aws-cli commands.

    This class serves as the receiver of aws-cli commands.
    Commands are checked, appended with "--profile"/"--region"
    parameters as needed and finally executed by calling the underlying
    shell, where the assembled commands are handled by the aws-cli.
    """
    def __init__(self, profile_manager, checker):
        """
        :param profile_manager: an instance of ProfileManager used
            to receive currently active regions and profiles.
        :type: bac.profile_manager.ProfileManager
        :param checker: An object which is responsible for syntax and
            privilege checking of the aws-cli command before its
            execution.
        :type: bac.checker.CLIChecker
        :rtype: None
        """
        self._profile_manager = profile_manager
        self._checker = checker
        self._initialize_environment()

    def _initialize_environment(self):
        self._env = dict(os.environ)
        dropped_vars = list()
        for variable in IGNORED_ENV_VARS:
            if variable in self._env:
                var = self._env.pop(variable)
                dropped_vars.append(var)

        if dropped_vars:
            log.debug('Dropping following enviromental'
                      ' variables: %s' % dropped_vars)

    def execute_awscli_command(self, command, args):
        """
        Handle the execution of an aws-cli command.

        :param command: aws-cli command to be executed across specified
            profiles and regions.
        :type: list
        :param args: namespace which contains custom BAC parameters.
        :type: argparse.Namespace
        :rtype: None
        """
        if 'help' in command:
            subprocess.call(command, env=self._env)
            return

        vars(args)['profiles'] = self._profile_manager.active_profiles
        vars(args)['regions'] = self._profile_manager.active_regions

        vars(args)['profile'] = None
        # check if profile is provided explicitly (--profile/-p)
        if any(arg in command for arg in PROFILE_OPTIONS):
            vars(args)['profiles'] = set()
            profile = extract_profile(command)
            self._check_profile_validity(profile)
            vars(args)['profile'] = profile
        elif not args.profiles:
            log.warning('No profiles specified or active.'
                        ' Please specify or activate some profiles first.')
            return

        # check of region is provided explicitly (--region/-r)
        if any(arg in command for arg in REGION_OPTIONS):
            vars(args)['regions'] = set()
        elif not args.regions:
            vars(args)['regions'] = {'us-east-1'}
            log.warning('No region specified or active,'
                        ' using "us-east-1" instead.')

        if args.check:
            self._check(command, args)
        if args.dry_run:
            return

        commands = self._prepare_commands(command, args)
        self._run(commands)

    def _run(self, commands):
        for data in commands:
            cmd, profile, region = data
            log.info('Executing for: Profile=%s,  Region=%s, Command:\n"%s"'
                     % (profile, region, ' '.join(cmd)))
            subprocess.call(cmd, env=self._env)

    def _check(self, command, args):
        # These may end command execution by raising an exception
        operation = self._checker.check(command[1:])
        if args.priv_check:
            self._check_privileges(operation, args)

    def _prepare_commands(self, command, args):
        if not args.profiles:
            commands = self._apply_regions(command, args.regions, args.profile)
            return commands

        commands = list()
        for profile in args.profiles:
            cmd = list(command)
            cmd.extend(['--profile', profile])
            regional_commands = self._apply_regions(cmd, args.regions, profile)
            commands.extend(regional_commands)
        return commands

    def _apply_regions(self, command, regions, profile):
        commands = list()
        regions = self._filter_regions(regions, command, profile)
        for region in regions:
            cmd = list(command)
            cmd.extend(['--region', region])
            data = (cmd, profile, region)
            commands.append(data)
        return commands

    def _check_privileges(self, operation, args):
        # Could be parallel (needs to use clients, not sessions)
        if not args.profiles:
            self._checker.privilege_check(operation, args.profile)
            return
        for profile in args.profiles:
            self._checker.privilege_check(operation, profile)

    def _filter_regions(self, regions, command, profile):
        try:
            filtered = self._filter(regions, command, profile)
        except ClientError as e:
            log.warning('Region filtering is not supported for "%s"'
                        ' profile. This is most probably caused by'
                        ' insufficient privileges. Continuing with all'
                        ' active regions.' % profile)
            log.debug('Following error received when'
                      ' filtering regions: %s' % str(e))
            return regions

        if not filtered:
            log.warning('None of the provided regions are available/valid'
                        ' for the "%s" profile.' % profile)
        return filtered

    def _filter(self, regions, command, profile):
        session = self._profile_manager.sessions[profile]
        enabled = self._get_enabled_regions(session)
        service_name = self._extract_service_name(command)
        available = (
                self._filter_supported_regions(enabled, service_name, session))
        discarded = regions.difference(available)
        if discarded:
            log.warning('Some regions ignored, because they are disabled'
                        ' for profile "%s" or not supported by "%s".'
                        'Ignored regions: %s'
                        % (profile, service_name, discarded))
        filtered = regions.intersection(available)
        return filtered

    def _get_enabled_regions(self, session):
        ec2 = session.client('ec2', region_name='us-east-1')
        response = ec2.describe_regions()
        enabled = set(EC2_REGIONS_JMES.search(response))
        return enabled

    def _filter_supported_regions(self, regions, service, session):
        ssm = session.client('ssm', region_name='us-east-1')
        path = ('/aws/service/global-infrastructure/services/%s/regions'
                % service)
        generator = paginate(ssm.get_parameters_by_path,
                             jmes_filter='Parameters[].Value',
                             Path=path)
        service_supported = {region for region in generator}
        filtered = regions.intersection(service_supported)
        return filtered

    def _check_profile_validity(self, profile):
        known_profiles = self._profile_manager.sessions.keys()
        if not profile or profile not in known_profiles:
            msg = 'Invalid profile given: "%s"' % profile
            raise InvalidAwsCliCommandError(msg)

    def _extract_service_name(self, command):
        cmd = extract_positional_args(command)
        service_name = cmd[1]
        if service_name.startswith('-'):
            msg = ('Following invalid command was given: %s'
                   ' Invalid option provided before the service'
                   ' has been specified.' % command)
            raise InvalidAwsCliCommandError(msg)
        # Handle s3api special case
        if service_name == 's3api':
            return 's3'
        return service_name
