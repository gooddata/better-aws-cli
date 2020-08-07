# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import boto3
import logging
import json
import os

from botocore.exceptions import BotoCoreError, ClientError
from six.moves.configparser import (ParsingError, RawConfigParser,
                                    NoOptionError)

from bac.constants import (CONFIG_FILE, CONFIG_PATH, CREDS_FILE, CREDS_PATH,
                           EC2_REGIONS_JMES)
from bac.errors import ConfigParsingException, NoProfilesError

log = logging.getLogger(__name__)
env = os.environ
AWS_CREDENTIALS = os.path.expanduser(env.get(CREDS_FILE, CREDS_PATH))
AWS_CONFIG = os.path.expanduser(env.get(CONFIG_FILE, CONFIG_PATH))
ACCOUNT_MAP = '/etc/aws_user_list/account_mapping.json'


class ProfileManager(object):
    """
    Loads and manages available profiles and regions.

    ProfileManager is initialized by parsing the AWS credentials and
    config files, initializing a Boto3 Session object for each
    profile, and receiving list of available regions.

    It is responsible for managing the state of active profiles and
    regions, which then affect the rest of BAC logic.
    """
    def __init__(self, args):
        """
        :param args: A namspace that can contain so-called
            "account map" if it was provided on tool's startup.
        :type: argparse.Namespace
        :rtype: None
        """
        self._args = args
        self.active_profiles = set()
        self.active_regions = set()
        self.account_names = dict()
        self._load_users()
        self._load_account_names()
        self._load_roles()
        self._load_regions()
        self._initialize_cmd_dicts()

    def get_first_profile(self):
        """
        Returns first profile from loaded profiles.

        This is used, when loading service information.
        """
        return next(iter(self.sessions.keys()))

    def get_first_session(self):
        """
        Returns first session from loaded profiles.

        This is used, when any session is needed, usually to load
        some AWS API data.
        """
        return next(iter(self.sessions.values()))

    def list_available_accounts(self):
        """Lists all currently available accounts."""
        if self.account_names:
            print('\t'.join(self.account_names.values()))
        else:
            print('No available accounts found')

    def list_available_profiles(self):
        """Lists all currently available profiles."""
        print('\t'.join(self.sessions.keys()))

    def list_active_profiles(self):
        """Lists all currently active profiles."""
        if self.active_profiles:
            print('\t'.join(self.active_profiles))
        else:
            print('No profiles active at the moment.')

    def list_available_regions(self):
        """Lists all currently available regions."""
        print('\t'.join(self.available_regions))

    def list_active_regions(self):
        """Lists all currently active regions."""
        if self.active_regions:
            print('\t'.join(self.active_regions))
        else:
            print('No regions active at the moment.')

    def switch_profiles(self, profiles):
        """Switch to desired set of profiles."""
        if '*' in profiles:
            self.active_profiles = self.sessions.keys()
        else:
            self.active_profiles = self._check_profiles(profiles)

    def include_profiles(self, profiles):
        """Include profiles to the set of currently active profiles."""
        if '*' in profiles:
            self.active_profiles = set(self.sessions.keys())
        else:
            valid = self._check_profiles(profiles)
            self.active_profiles = self.active_profiles.union(valid)

    def exclude_profiles(self, profiles):
        """Exclude profiles from the set of currently active profiles."""
        if '*' in profiles:
            self.active_profiles = set()
        else:
            self.active_profiles = self.active_profiles.difference(
                                     set(profiles))

    def switch_regions(self, regions):
        """Switch to desired set of regions."""
        if '*' in regions:
            self.active_regions = self.available_regions
        else:
            self.active_regions = self._check_regions(regions)

    def include_regions(self, regions):
        """Include regions to the set of currently active regions."""
        if '*' in regions:
            self.active_regions = self.available_regions
        else:
            valid = self._check_regions(regions)
            self.active_regions = self.active_regions.union(valid)

    def exclude_regions(self, regions):
        """Exclude regions from the set of currently active regions."""
        if '*' in regions:
            self.active_regions = set()
        else:
            self.active_regions = self.active_regions.difference(regions)

    def handle_command(self, command, args):
        """Attempt to call a corresponding method for given command."""
        cmd = self._cmd_argless.get(command, None)
        if cmd:
            cmd()
            return True
        cmd = self._cmd_argful.get(command, None)
        if cmd:
            cmd(args[1:])
            return True
        return False

    def _parse_file(self, parser, path):
        if not os.path.exists(path):
            msg = 'File not found at following path: %s' % path
            raise ConfigParsingException(msg)

        try:
            parser.read(path)
        except ParsingError as e:
            msg = ('Following error occured while parsing %s: %s'
                   % (path, str(e)))
            raise ConfigParsingException(msg)

    def _load_users(self):
        """
        Load AWS profiles from aws credentials file and create
        a seperate aws session for each profile.
        """
        credentials = RawConfigParser()

        try:
            self._parse_file(credentials, AWS_CREDENTIALS)
        except ConfigParsingException as e:
            log.error('Failed to parse user profiles: %s. Exiting BAC.'
                      % str(e))
            raise NoProfilesError()

        profile_creds = credentials.sections()
        if 'default' in profile_creds:
            profile_creds.remove('default')

        self.sessions = dict()
        for profile in profile_creds:
            try:
                self.sessions[profile] = (
                        boto3.session.Session(profile_name=profile))
            except BotoCoreError as e:
                log.warn('Failed to load %s profile.'
                         ' Following error was raised: %s'
                         % (profile, str(e)))

        if not self.sessions:
            log.error('No valid profiles found in %s. Exiting BAC.'
                      % AWS_CREDENTIALS)
            raise NoProfilesError()

    def _load_roles(self):
        """
        Load assumable roles from aws config file and create
        a separate aws session for each such role.
        """
        config = RawConfigParser()

        try:
            self._parse_file(config, AWS_CONFIG)
        except ConfigParsingException as e:
            msg = 'Failed to parse role profiles: %s' % str(e)
            log.error(msg)
            return

        for section in config.sections():
            if 'profile' in section and config.has_option(section, 'role_arn'):
                profile = section.split()[1]
                self.sessions[profile] = boto3.session.Session(
                                                    profile_name=profile)
                # as role name set the user defined session name
                try:
                    self.account_names[profile] = config.get(
                            section, 'role_session_name')
                # if not defined, extract role name from ARN
                except NoOptionError:
                    role_name = config.get(section, 'role_arn').split('/')[-1]
                    self.account_names[profile] = role_name

    def _load_account_names(self):
        """Attempt to read account names from the account map file."""
        accounts = dict()
        if self._args.account_map is not None:
            try:
                with open(self._args.account_map, 'r') as accounts_json:
                    accounts = json.load(accounts_json)['accounts']
            except IOError:
                # File not found, or insufficient permissions
                log.warn('Failed to locate or open the file'
                         ' containing the desired account mapping.'
                         ' Continuing without it.')

        for profile, session in self.sessions.items():
            account_id = session.client('sts') \
                         .get_caller_identity() \
                         .get('Account')
            account_name = self._get_account_name(session, account_id)
            self.account_names[profile] = (
                    accounts.get(account_id, account_name))

    def _get_account_name(self, session, account_id):
        """
        Attempt to get AWS Account name. Store Account ID on failure.
        """
        try:
            account_name = session.client('organizations') \
                           .describe_account(AccountId=account_id) \
                           .get('Account') \
                           .get('Name')
        except ClientError:
            # If the script user does not have satisfactory privileges
            # needed in order to call the AWS Organizations API,
            # store only the AWS Account ID
            log.debug('Failed to receive account name for %s,'
                      'using the AccountID instead.' % account_id)
            account_name = account_id
        return account_name

    def _check_regions(self, regions):
        given = set(regions)
        valid = given.intersection(set(self.available_regions))
        invalid = given.difference(valid)
        if invalid:
            log.warn('Following regions have not been found: {%s}'
                     % ', '.join(invalid))
        return set(valid)

    def _load_regions(self):
        self.available_regions = None

        session = self.get_first_session()
        ec2 = session.client('ec2', region_name='us-east-1')

        regions = ec2.describe_regions(AllRegions=True)
        parsed = EC2_REGIONS_JMES.search(regions)
        self.available_regions = parsed

    def _check_profiles(self, profiles):
        given = set(profiles)
        valid = given.intersection(set(self.sessions.keys()))
        invalid = given.difference(valid)
        if invalid:
            log.warn('Following profiles/roles have not been found: {%s}'
                     % ', '.join(invalid))
        return valid

    def _initialize_cmd_dicts(self):
        self._cmd_argless = {
            'list-available-profiles': self.list_available_profiles,
            'list-available-accounts': self.list_available_accounts,
            'list-active-profiles': self.list_active_profiles,
            'list-available-regions': self.list_available_regions,
            'list-active-regions': self.list_active_regions,
            }

        self._cmd_argful = {
            'switch-profiles': self.switch_profiles,
            'include-profiles': self.include_profiles,
            'exclude-profiles': self.exclude_profiles,
            'switch-regions': self.switch_regions,
            'include-regions': self.include_regions,
            'exclude-regions': self.exclude_regions,
            }
