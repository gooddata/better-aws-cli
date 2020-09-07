# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import logging
import mock
import unittest

import yaml

from six import text_type
from testfixtures import LogCapture, log_capture

from tests._utils import _import, captured_output, check_logs
batch = _import('bac', 'batch')
errors = _import('bac', 'errors')
utils = _import('bac', 'utils')


COMMAND1 = ['aws', 's3api', 'list-buckets', '--profile',
            'uno', '--region', 'us-east-1']
COMMAND2 = ['aws', 's3api', 'list-buckets', '--profile',
            'uno', '--region', 'eu-west-1']
COMMAND3 = ['aws', 's3api', 'list-buckets', '--profile',
            'dos', '--region', 'us-east-1']
COMMAND4 = ['aws', 's3api', 'list-buckets', '--profile',
            'dos', '--region', 'eu-west-1']
VALID_DEF_PATH = 'tests/valid_batch_command.yml'
INVALID_DEF_PATH = 'tests/invalid_batch_command.yml'
ARGV = ['batch-command', VALID_DEF_PATH]


class BatchCommandTest(unittest.TestCase):
    def setUp(self):
        self.argv = list(ARGV)
        self.checker = mock.Mock()
        global_args = mock.Mock()
        global_args.dry_run = False
        self.globals = global_args

    @log_capture('bac.utils', level=logging.ERROR)
    def test_handle_no_commands(self, captured_log):
        self.argv = self.argv[:1]
        with captured_output() as (out, err):
            batch.CommandBatch(self.globals, self.argv, self.checker)
        check_logs(captured_log, 'bac.utils', 'ERROR', 'arguments')

    @log_capture('bac.utils', level=logging.ERROR)
    def test_handle_no_path(self, captured_log):
        self.argv[1] = '--bac-no-check'
        with captured_output() as (out, err):
            batch.CommandBatch(self.globals, self.argv, self.checker)
        check_logs(captured_log, 'bac.utils', 'ERROR', 'arguments')

    def test_handle_bad_path_exc(self):
        self.argv[1] = 'some/bad/path.yml'
        with self.assertRaises(errors.InvalidArgumentException):
            batch.CommandBatch(self.globals, self.argv, self.checker)

    @mock.patch('yaml.safe_load')
    def test_yaml_load_exc(self, mock_load):
        mock_load.side_effect = yaml.YAMLError()
        with self.assertRaises(errors.BACError):
            batch.CommandBatch(self.globals, ARGV, self.checker)

    @mock.patch('os.path.exists', mock.Mock(return_value=True))
    def test_handle_unsupported_format(self):
        self.argv[1] = 'some/path/to/file.json'
        with self.assertRaises(errors.InvalidArgumentException):
            batch.CommandBatch(self.globals, self.argv, self.checker)

    def test_handle_parser_exc(self):
        self.argv[1] = INVALID_DEF_PATH
        with self.assertRaises(errors.BACError):
            batch.CommandBatch(self.globals, self.argv, self.checker)

    def test_dry_run(self):
        self.globals.dry_run = True
        with mock.patch('bac.batch.execute_command') as execute_command:
            batch.CommandBatch(self.globals, self.argv, self.checker)
        execute_command.assert_not_called()

    def test_command_calls(self):
        m = mock.Mock()
        m.return_value = ('', '', 0)
        # 30 here, stands for 30 seconds timeout, which is the default value
        results = [
                mock.call(COMMAND1, 30),
                mock.call(COMMAND2, 30),
                mock.call(COMMAND3, 30),
                mock.call(COMMAND4, 30)
                ]
        with mock.patch('bac.batch.execute_command', m) as execute_command:
            batch.CommandBatch(self.globals, self.argv, self.checker)
            execute_command.assert_has_calls(results, any_order=True)

    @mock.patch('bac.batch.Parser.parse', mock.Mock(return_value=['foo']))
    @mock.patch('bac.batch.execute_command')
    def test_handle_output(self, execute_command):
        execute_command.return_value = (b'Some output', '', 0)
        with captured_output() as (out, err):
            batch.CommandBatch(self.globals, self.argv, self.checker)
            expected = text_type('Some output\n')
            self.assertEqual(out.getvalue(), expected)

    @mock.patch('bac.batch.Parser.parse', mock.Mock(return_value=['foo']))
    @mock.patch('bac.batch.execute_command')
    def test_handle_timeout(self, execute_command):
        execute_command.side_effect = errors.TimeoutException()
        with LogCapture(level=logging.ERROR) as captured_log:
            batch.CommandBatch(self.globals, self.argv, self.checker)
        check_logs(captured_log, 'bac.batch', 'ERROR',
                   ['Timeout of 30 seconds reached when'
                    ' executing following command:\n', 'foo'])

    @mock.patch('bac.batch.Parser.parse', mock.Mock(return_value=['foo']))
    @mock.patch('bac.batch.execute_command')
    def test_handle_exit_code(self, execute_command):
        execute_command.return_value = ('', '', 1)
        with LogCapture(level=logging.WARNING) as captured_log:
            batch.CommandBatch(self.globals, self.argv, self.checker)
        check_logs(captured_log, 'bac.batch', 'WARNING',
                   ['Command', 'foo',
                    'ended with following non-zero exit code:', '1'])

    @mock.patch('bac.batch.Parser.parse', mock.Mock(return_value=['foo']))
    @mock.patch('bac.batch.execute_command')
    def test_handle_execution_error(self, execute_command):
        err = b'error message'
        execute_command.return_value = ('', err, 1)
        with LogCapture(level=logging.ERROR) as captured_log:
            batch.CommandBatch(self.globals, self.argv, self.checker)
        check_logs(captured_log, 'bac.batch', 'ERROR',
                   ['An error occured: ', 'error message'])
