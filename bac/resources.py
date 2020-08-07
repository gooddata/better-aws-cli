# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import csv
import logging
import os

import jmespath

from botocore.exceptions import ClientError
from six import text_type

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
CACHE_PATH = os.path.join(BASE_PATH, 'cache')

log = logging.getLogger(__name__)


class CachedResource(object):
    """
    An abstract class that represents a type of cached AWS resource.

    This class implements methods which handle cache write and load
    from the disk, retrieval of server-side resource data.

    A class which extends the CachedResource, should provide four class
    level constants:
        - resource_type - type of the service. Syntax of this constant
            is "<service_name>-<awscli_optional_parameter>".
            Example: 's3-bucket-name'
        - service - a service which this resource belongs to.
            Example: 's3'
        - operation - an operation to be called on the Client object.
            Example: 'list_buckets'
        - query - a JMESPath query used to parse the operation response
            into a single list of strings.
            Example: 'Buckets[].Name'
    """
    def __init__(self):
        self._data = None

    @property
    def data(self):
        """Get the value of the data attribute."""
        if self._data is None:
            self._data = self._read_cache()
        return self._data

    @data.setter
    def data(self, value):
        """Set the value of the data attribute."""
        self._data = value

    def get_missing_resources(self, client):
        """
        Attempt to retrieve resource data from AWS API.

        The desired client object is receiver, and the method that
        should retrieve the resource data is called upon the client.
        The response is then parsed with the JMESPath query defined
        for the resource into a list. This list is then returned.

        :param client: A boto3 Client used to load resource data.
        :type: botocore.client.BaseClient
        :rtype: list
        """
        try:
            response = getattr(client, self.operation)()
        except ClientError as e:
            if 'UnauthorizedOperation' in str(e):
                log.debug('Failed to receive cache for the %s.'
                          ' Received following error: %s'
                          % (type(self).__name__, str(e)))
                return list()
            raise e

        resources = [
            text_type(resource)
            for resource
            in jmespath.search(self.query, response)
        ]
        return resources

    def write_cache(self, resources):
        """Write resource cache data to disk."""
        if not os.path.exists(CACHE_PATH):
            os.makedirs(CACHE_PATH)

        cache_file = self.resource_type + '.txt'
        path = os.path.join(
                CACHE_PATH, cache_file)

        log.debug('Writing cache to %s.' % path)
        with open(path, 'a') as f:
            writer = csv.writer(f, lineterminator='\n')
            for resource in resources:
                row = list()
                row.append(resource[0])
                row.extend(resource[1])
                writer.writerow(row)
        log.debug('%s cache written succsessfully.'
                  % type(self).__name__)

    def _read_cache(self):
        cache_file = self.resource_type + '.txt'
        path = os.path.join(
                CACHE_PATH, cache_file)
        if not os.path.exists(path):
            log.debug('Failed to locate cache at %s.' % path)
            return dict()

        cached = dict()
        log.debug('Attempting to read cache from %s.' % path)
        with open(path, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                key = row[0]
                resources = [text_type(r) for r in row[1:]]
                cached[key] = resources
        log.debug('Cache read successfully.')
        return cached


class S3BucketName(CachedResource):

    resource_type = 's3-bucket-name'
    service = 's3'
    operation = 'list_buckets'
    query = 'Buckets[].Name'


class IAMUserName(CachedResource):

    resource_type = 'iam-user-name'
    service = 'iam'
    operation = 'list_users'
    query = 'Users[].UserName'


class IAMGroupName(CachedResource):

    resource_type = 'iam-group-name'
    service = 'iam'
    operation = 'list_groups'
    query = 'Groups[].GroupName'


class IAMRoleName(CachedResource):

    resource_type = 'iam-role-name'
    service = 'iam'
    operation = 'list_roles'
    query = 'Roles[].RoleName'


class EC2InstanceIds(CachedResource):

    resource_type = 'ec2-instance-ids'
    service = 'ec2'
    operation = 'describe_instances'
    query = 'Reservations[].Instances[].InstanceId'
