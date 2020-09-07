import datetime
import logging
import os
import shlex
import sys
import unittest

import boto3
import botocore

from testfixtures import log_capture, TempDirectory
from botocore.stub import ANY, Stubber

from tests._utils import _import, captured_output, check_logs, transform
utils = _import('bac', 'utils')
errors = _import('bac', 'errors')


class UtilsTest(unittest.TestCase):
    def setUp(self):
        pass

    @log_capture('bac.utils', level=logging.ERROR)
    def test_arg_parser_help(self, captured_log):
        parser = utils.ArgumentParser()
        argv = ['--help']
        with self.assertRaises(errors.ArgumentParserDoneException):
            with captured_output() as (out, err):
                parser.parse_args(argv)

    def test_globals_parser_help(self):
        parser = utils.GlobalsParser()
        argv = ['--help']
        with captured_output() as (out, err):
            parser.parse_args(argv)

    @log_capture('bac.utils', level=logging.WARNING)
    def test_globals_parser_error(self, captured_log):
        parser = utils.GlobalsParser()
        with captured_output() as (out, err):
            parser.error('Error')
        check_logs(captured_log, 'bac.utils', 'WARNING', 'error: Error\n')

    def test_ensure_path(self):
        with TempDirectory() as d:
            p = utils.ensure_path(d.path, 'foo', 'bar')
            expected = os.path.join(d.path, 'foo', 'bar')
            assert os.path.exists(expected)
            self.assertEqual(p, expected)

    def test_execute_command(self):
        cmd = shlex.split('echo "Hello world!"')
        out, err, exit_code = utils.execute_command(cmd)
        expected = transform(('Hello world!\n', '', 0))
        self.assertEqual((out, err, exit_code), expected)

    def test_execute_timeout(self):
        cmd = shlex.split('sleep 5')
        with self.assertRaises(errors.TimeoutException):
            utils.execute_command(cmd, timeout=1)

    def test_paginate(self):
        config = botocore.config.Config(signature_version=botocore.UNSIGNED)
        ssm = boto3.client('ssm', config=config, region_name='us-east-1')
        response1 = {
            'Parameters': [
                {
                    'ARN': 'string',
                    'DataType': 'text',
                    'LastModifiedDate': datetime.datetime(2015, 1, 1),
                    'Name': 'first',
                    'Type': 'String',
                    'Value': 'uno',
                    'Version': 1,
                },
                {
                    'ARN': 'string',
                    'DataType': 'text',
                    'LastModifiedDate': datetime.datetime(2015, 1, 1),
                    'Name': 'second',
                    'Type': 'String',
                    'Value': 'dos',
                    'Version': 1,
                },
            ],
            'NextToken': '1a2b3c'
        }
        response2 = {
            'Parameters': [
                {
                    'ARN': 'string',
                    'DataType': 'text',
                    'LastModifiedDate': datetime.datetime(2015, 1, 1),
                    'Name': 'third',
                    'Type': 'String',
                    'Value': 'tres',
                    'Version': 1,
                },
                {
                    'ARN': 'string',
                    'DataType': 'text',
                    'LastModifiedDate': datetime.datetime(2015, 1, 1),
                    'Name': 'fourth',
                    'Type': 'String',
                    'Value': 'cuatro',
                    'Version': 1,
                },
            ],
        }

        with Stubber(ssm) as stubber:
            expected_params1 = {'Path': ANY}
            stubber.add_response(
                    'get_parameters_by_path', response1, expected_params1)
            expected_params2 = {'NextToken': ANY, 'Path': ANY}
            stubber.add_response(
                    'get_parameters_by_path', response2, expected_params2)

            path = ('/aws/service/global-infrastructure/services/ec2/regions')
            generator = utils.paginate(ssm.get_parameters_by_path,
                                       jmes_filter='Parameters[].Value',
                                       Path=path)
            results = [i for i in generator]
            expected = ['uno', 'dos', 'tres', 'cuatro']
            self.assertEqual(expected, results)

    def test_extract_positional_args(self):
        command = [
                'aws', '--region', 'us-east-1', 's3api',
                'list-buckets', '--query', 'Buckets[].Name'
                ]
        expected = ['aws', 's3api', 'list-buckets']
        actual = utils.extract_positional_args(command)
        self.assertEqual(actual, expected)

    def test_extract_profile(self):
        command = ['aws', 's3api', 'list-buckets', '--profile', 'uno']
        expected = 'uno'
        actual = utils.extract_profile(command)
        self.assertEqual(actual, expected)

    def _init_level_formatter(self):
        handler = logging.StreamHandler(sys.stdout)
        default_fmt = 'default-> %(levelname)s: %(message)s'
        level_fmts = {
            logging.INFO: '%(message)s',
            logging.DEBUG: '%(levelname)s: %(message)s'
            }
        formatter = utils.LevelFormatter(
                fmt=default_fmt,
                level_fmts=level_fmts)
        handler.setFormatter(formatter)
        logging.root.addHandler(handler)

    def test_level_formatter(self):
        with captured_output() as (out, err):
            self._init_level_formatter()
            log = logging.getLogger()
            log.setLevel(logging.DEBUG)
            log.warning('warning message')
            log.info('info message')
            log.debug('debug message')
            expected = (
                    'default-> WARNING: warning message\n'
                    'info message\n'
                    'DEBUG: debug message\n'
                    )
            self.assertEqual(out.getvalue(), expected)
