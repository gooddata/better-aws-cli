import mock

import botocore

from botocore.compat import OrderedDict

GET_DATA = {
    'cli': {
        'description': 'description',
        'synopsis': 'usage: foo',
        'options': {
            "debug": {
                "action": "store_true",
                "help": "Turn on debug logging"
            },
            "output": {
                "choices": [
                    "json",
                    "text",
                    "table"
                ],
                "metavar": "output_format"
            },
            "query": {
                "help": ""
            },
            "profile": {
                "help": "",
                "metavar": "profile_name"
            },
            "region": {
                "metavar": "region_name"
            },
            "endpoint-url": {
                "help": "",
                "metavar": "endpoint_url"
            },
            "no-verify-ssl": {
                "action": "store_false",
                "dest": "verify_ssl",
                "help": "",
            },
            "no-paginate": {
                "action": "store_false",
                "help": "",
                "dest": "paginate"
            },
            "page-size": {
                "type": "int",
                "help": "",
            },
            "read-timeout": {
                "type": "int",
                "help": ""
            },
            "connect-timeout": {
                "type": "int",
                "help": ""
            }
        }
    },
}

GET_VARIABLE = {
    'provider': 'aws',
    'output': 'json',
    'api_versions': {}
}


MINI_SERVICE = {
  "metadata": {
    "apiVersion": "2006-03-01",
    "endpointPrefix": "s3",
    "globalEndpoint": "s3.amazonaws.com",
    "signatureVersion": "s3",
    "protocol": "rest-xml"
  },
  "operations": {
    "ListObjects": {
      "name": "ListObjects",
      "http": {
        "method": "GET",
        "requestUri": "/{Bucket}"
      },
      "input": {"shape": "ListObjectsRequest"},
      "output": {"shape": "ListObjectsOutput"},
    },
    "IdempotentOperation": {
      "name": "IdempotentOperation",
      "http": {
        "method": "GET",
        "requestUri": "/{Bucket}"
      },
      "input": {"shape": "IdempotentOperationRequest"},
      "output": {"shape": "ListObjectsOutput"},
    },
  },
  "shapes": {
    "ListObjectsOutput": {
      "type": "structure",
      "members": {
        "IsTruncated": {
          "shape": "IsTruncated",
          "documentation": ""
        },
        "NextMarker": {
          "shape": "NextMarker",
        },
        "Contents": {"shape": "Contents"},
      },
    },
    "IdempotentOperationRequest": {
      "type": "structure",
      "required": "token",
      "members": {
        "token": {
          "shape": "Token",
          "idempotencyToken": True,
        },
      }
    },
    "ListObjectsRequest": {
      "type": "structure",
      "required": ["Bucket"],
      "members":  OrderedDict([
        ("Bucket", {
          "shape": "BucketName",
          "location": "uri",
          "locationName": "Bucket"
        }),
        ("Marker", {
          "shape": "Marker",
          "location": "querystring",
          "locationName": "marker",
        }),
        ("MaxKeys", {
          "shape": "MaxKeys",
          "location": "querystring",
          "locationName": "max-keys",
        }),
      ]),
    },
    "BucketName": {"type": "string"},
    "MaxKeys": {"type": "integer"},
    "Marker": {"type": "string"},
    "IsTruncated": {"type": "boolean"},
    "NextMarker": {"type": "string"},
    "Contents": {"type": "string"},
    "Token": {"type": "string"},
  }
}


class FakeSession(object):
    def __init__(self, profile=None):
        self.operation = None
        self.profile = profile
        self.stream_logger_args = None
        self.credentials = 'fakecredentials'
        self.session_vars = {}

    def get_component(self, name):
        if name == 'event_emitter':
            return self.emitter

    def create_client(self, *args, **kwargs):
        client = mock.Mock()
        client.list_objects.return_value = {}
        client.can_paginate.return_value = False
        return client

    def get_available_services(self):
        return ['s3']

    def get_data(self, name):
        return GET_DATA[name]

    def get_config_variable(self, name):
        if name in GET_VARIABLE:
            return GET_VARIABLE[name]
        return self.session_vars[name]

    def get_service_model(self, name, api_version=None):
        return botocore.model.ServiceModel(
            MINI_SERVICE, service_name='s3')

    def user_agent(self):
        return 'user_agent'

    def set_stream_logger(self, *args, **kwargs):
        self.stream_logger_args = (args, kwargs)

    def get_credentials(self):
        return self.credentials

    def set_config_variable(self, name, value):
        if name == 'profile':
            self.profile = value
        else:
            self.session_vars[name] = value
