# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import glob
import os

from bac import resources

from botocore.exceptions import ClientError
from six import text_type

log = logging.getLogger(__name__)

CACHED_RESOURCES = {
        '--bucket': 'S3BucketName',
        '--user-name': 'IAMUserName',
        '--group-name': 'IAMGroupName',
        '--role-name': 'IAMRoleName',
        '--instance-ids': 'EC2InstanceIds',
        }
REGION_SENSITIVE_OPTIONS = {'--instance-ids'}


class CacheProvider(object):
    """
    Manages resource caching and provides cached data for completions.
    """
    def __init__(self, profile_manager):
        """
        :param profile_manager: an instance of ProfileManager used
            to receive currently active regions and profiles.
        """
        self._profile_manager = profile_manager
        self._enabled = True
        self._cached = dict()
        self._init_resources()

    def toggle_cache(self):
        """Toggle cached resource completion on/off."""
        log.debug('Toggling completion from resource cache.')
        self._enabled = not self._enabled

    def refresh_cache(self):
        """
        Refresh all of resource cache for every active profile/region.
        """
        self._cleanup()
        for option in self._cached.keys():
            self._refresh_resource_cache(option)

    def _init_resources(self):
        for parameter, cached_resource in CACHED_RESOURCES.items():
            resource = getattr(resources, cached_resource)()
            self._cached[parameter] = resource

    def _cleanup(self):
        """
        Cleanup of any previously cached reasources.
        """
        log.debug('Cleaning up old resource cache.')
        to_clean = glob.glob('%s/cache/*' % os.getcwd())
        for f in to_clean:
            os.remove(f)

    def _refresh_resource_cache(self, option):
        cache = self._cached[option]
        cache.data = dict()
        is_regional = option in REGION_SENSITIVE_OPTIONS

        new_resources = list()
        for profile in self._profile_manager.active_profiles:
            account = self._profile_manager.account_names[profile]
            session = self._profile_manager.sessions[profile]
            if is_regional:
                _, resource = (
                        self._load_regional_cache(cache, account, session))
                if resource:
                    new_resources.extend(resource)
            else:
                _, resource = (
                        self._load_nonregional_cache(cache, account, session))
                if resource:
                    new_resources.append(resource)
        cache.write_cache(new_resources)

    def get_cached_resource(self, option):
        cache = self._cached[option]
        is_regional = option in REGION_SENSITIVE_OPTIONS

        completions = list()
        new_resources = list()
        for profile in self._profile_manager.active_profiles:
            account = self._profile_manager.account_names[profile]
            session = self._profile_manager.sessions[profile]

            if is_regional:
                resource, new_resource = (
                    self._load_regional_cache(cache, account, session))
                if new_resource:
                    new_resources.extend(new_resource)
            else:
                resource, new_resource = (
                        self._load_nonregional_cache(cache, account, session))
                if new_resource:
                    new_resources.append(new_resource)

            completions.extend(resource)

        if new_resources:
            cache.write_cache(new_resources)

        return completions

    def _load_nonregional_cache(self, cache, account, session):
        try:
            resource, new_resource = (
                    self._load_cache(cache, account, session))
        except ClientError as e:
            log.debug('Failed to receive cache for %s, for profile %s.'
                      ' Received following error: %s'
                      % (type(cache).__name__, session.profile_name, str(e)))
            resource, new_resource = list(), None
        return resource, new_resource

    def _load_regional_cache(self, cache, account, session):
        completions = list()
        new_resources = list()
        for region in self._profile_manager.active_regions:
            key = '%s:%s' % (account, region)
            try:
                resource, new_resource = (
                        self._load_cache(cache, key, session, region))
            except ClientError as e:
                log.debug('Failed to receive cache for %s, for profile %s,'
                          ' for region %s. Received following error: %s'
                          % (type(cache).__name__, session.profile_name,
                              region, str(e)))
                continue
            completions.extend(resource)
            if new_resource:
                new_resources.append(new_resource)
        return completions, new_resources

    def _load_cache(self, cache, key, session, region=None):
        new_resource = None
        try:
            resource = cache.data[key]
        except KeyError:
            client = session.client(cache.service, region_name=region)
            resource = cache.get_missing_resources(client)
            new_resource = (key, resource)
            resource = [text_type(r) for r in resource]
            cache.data[key] = resource
        return resource, new_resource
