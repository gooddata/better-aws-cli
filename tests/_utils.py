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
        return [text_type(i) for i in var]
    if isinstance(var, dict):
        for k, v in var.items():
            var[k] = transform(v)
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
