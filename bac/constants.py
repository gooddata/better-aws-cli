# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import jmespath


BAC_PROMPT = '~> '

BAC_HISTORY = '.history'

BATCH_JOB_SECTIONS = {'command', 'optionals'}

CLI_OPTION_HAS_ARGS = {
        '--debug': False,
        '--endpoint-url': True,
        '--no-verify-ssl': False,
        '--no-paginate': False,
        '--output': True,
        '--query': True,
        '--profile': True,
        '--region': True,
        '--version': True,
        '--color': True,
        '--no-sign-request': False,
        '--ca-bundle': True,
        '--cli-read-timeout': True,
        '--cli-connect-timeout': True
        }

CACHED_OPTIONS = {'--bucket', '--user-name', '--group-name',
                  '--role-name', '--instance-ids'}

CONFIG_FILE = 'AWS_CONFIG_FILE'
CONFIG_PATH = '~/.aws/config'
CREDS_FILE = 'AWS_SHARED_CREDENTIALS_FILE'
CREDS_PATH = '~/.aws/credentials'

EC2_REGIONS_JMES = jmespath.compile('Regions[].RegionName')

IGNORED_ENV_VARS = {'AWS_ACCESS_KEY_ID', 'AWS_PROFILE',
                    'AWS_ROLE_SESSION_NAME', 'AWS_SECRET_ACCESS_KEY',
                    'AWS_SESSION_TOKEN'}

PROFILE_OPTIONS = {'-p', '--profile'}

PROFILE_MANAGER_COMMANDS = {
        'list-available-profiles': 'List all available named profiles',
        'list-available-accounts': 'List all available accounts',
        'list-available-regions': 'List all available regions',
        'list-active-profiles': 'List all currently active named profiles',
        'list-active-regions': 'List all currently active regions',
        'switch-profiles': 'Mark all currently active profiles as disabled'
                           'and mark specified profiles as active',
        'include-profiles': 'Mark specified profiles as active',
        'exclude-profiles': 'Mark specified profiles as inactive',
        'switch-regions': 'Mark all currently active regions as disabled'
                           'and mark specified regions as active',
        'include-regions': 'Mark specified regions as active',
        'exclude-regions': 'Mark specified regions as inactive',
        }

PROFILE_COMMANDS = ['switch-profiles', 'include-profiles', 'exclude-profiles']

REGION_COMMANDS = ['switch-regions', 'include-regions', 'exclude-regions']

REGION_OPTIONS = {'-r', '--region'}
