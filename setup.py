# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
import os

from setuptools import find_packages, setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

params = {
    'name': 'better-aws-cli',
    'version': '%s' % os.environ.get('PACKAGE_VERSION', 'dev'),
    'packages': find_packages(),
    'entry_points': {
        'console_scripts': [
            'bac=bac.__main__:main'
        ],
    },
    'install_requires': requirements,
    'url': 'https://github.com/Tjev/better-aws-cli',
    'license': 'BSD License 2.0',
    'author': 'GoodData Corporation',
    'author_email': 'tomas.jevocin@gooddata.com',
    'description': 'Better Aws Cli',
    'long_description': 'GoodData AWS management tool',
    'classifiers': [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Private :: Do not Upload',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6'
    ],
}

setup(**params)
