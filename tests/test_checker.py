import mock
import unittest

from six import text_type

from tests._utils import (_import, captured_output)
from tests.fake_session import FakeSession
checker = _import('bac', 'checker')
errors = _import('bac', 'errors')


class CheckerTest(unittest.TestCase):
    def setUp(self):
        def fakeSession(profile=None):
            return FakeSession(profile)

        with mock.patch('bac.checker.Session') as fake_session:
            fake_session.side_effect = fakeSession
            self.checker = checker.CLIChecker('foo')


class CheckerSyntaxTest(CheckerTest):
    def test_standard_successful_check(self):
        cmd = ['s3api', 'list-objects', '--bucket', 'foo']
        self.checker.check(cmd)

    def test_handle_missing_parameter_value(self):
        cmd = ['s3api', 'list-objects', '--bucket']
        with captured_output() as (out, err):
            with self.assertRaises(errors.CLICheckerSyntaxError):
                self.checker.check(cmd)

    def test_handle_missing_parameter(self):
        cmd = ['s3api', 'list-objects']
        with captured_output() as (out, err):
            with self.assertRaises(errors.CLICheckerSyntaxError):
                self.checker.check(cmd)

    def test_handle_custom_s3(self):
        cmd = ['s3', 'ls']
        with captured_output() as (out, err):
            self.checker.check(cmd)
            expected = text_type(
                    'Checks for s3 file commands are not supported.\n')
            self.assertEqual(out.getvalue(), expected)
