import logging
import os
import unittest

from testfixtures import log_capture, TempDirectory

from tests._utils import _import, captured_output
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

    def test_ensure_path(self):
        with TempDirectory() as d:
            p = utils.ensure_path(d.path, 'foo', 'bar')
            expected = os.path.join(d.path, 'foo', 'bar')
            assert os.path.exists(expected)
            self.assertEqual(p, expected)

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
