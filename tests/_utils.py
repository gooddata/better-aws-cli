# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import os
import sys

from contextlib import contextmanager

from six import StringIO, text_type


def _import(path, module):
    testpath = os.path.join(os.path.dirname(__file__), '..')
    sys.path.insert(0, os.path.abspath(testpath))
    return getattr(__import__(path, fromlist=[module]), module)


def transform(var):
    if isinstance(var, str):
        return text_type(var)
    if isinstance(var, list):
        return [transform(i) for i in var]
    if isinstance(var, tuple):
        return tuple(transform(i) for i in var)
    if isinstance(var, dict):
        for k, v in var.items():
            var[k] = transform(v)
        return var
    return var


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def check_logs(log, source, level, words):
    # Ths is a workaround for different log messages
    # given by Python2 and Python3
    last_log = log.actual()[-1]
    assert source == last_log[0]
    assert level == last_log[1]
    if isinstance(words, str):
        assert words in last_log[2]
    elif isinstance(words, list):
        for word in words:
            assert word in last_log[2]


def check_items_in_result(cls, expected, actual):
    for i in expected:
        cls.assertIn(i, actual)
