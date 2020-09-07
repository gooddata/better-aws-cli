#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
from __future__ import absolute_import

import argparse
import logging.config
import sys

from bac.errors import NoProfilesError
from bac.shell import BAC
from bac.utils import LevelFormatter


def parse_entry_point_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '-v', '--verbose', action='count', default=0,
            help='Verbosity level; can be specified 0-2 times')
    return parser.parse_args()


def main():
    args = parse_entry_point_args()
    setup_logging(args.verbose)

    try:
        BAC().run_cli()
    except (EOFError, KeyboardInterrupt):
        sys.exit()
    except NoProfilesError:
        sys.exit(1)


def setup_logging(verbosity):
    handler = logging.StreamHandler(sys.stdout)
    default_fmt = '%(levelname)s: %(message)s'
    level_fmts = {
            logging.INFO: '%(message)s',
            logging.DEBUG: '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
            }
    formatter = LevelFormatter(
                    fmt=default_fmt,
                    datefmt='%H:%M:%S',
                    level_fmts=level_fmts)
    handler.setFormatter(formatter)
    logging.root.addHandler(handler)

    level_main, level_other = {
        1: (logging.DEBUG, logging.INFO),
        2: (logging.DEBUG, logging.DEBUG)
    }.get(verbosity, (logging.INFO, logging.WARNING))

    logging.root.setLevel(level_main)
    logging.getLogger('botocore').setLevel(level_other)


if __name__ == '__main__':
    main()
