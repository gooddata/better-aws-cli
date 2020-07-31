# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
from prompt_toolkit import HTML
from six import text_type


class Toolbar(object):
    """Handles content shown in propt toolkit toolbar."""
    def __init__(self, get_fuzzy, get_caching, get_profiles, get_regions):
        """
        :param get_fuzzy: A callable that retrieves current fuzzy
            completion setting.
        :type: callable
        :param get_caching: A callable that retrieves current resource
            caching setting.
        :type: callable
        :param get_profiles: A callable that retrieves set of currently
            active profiles.
        :type: callable
        :param get_regions: A callable that retrieves set of currently
            active regions.
        :type: callable
        :rtype: None
        """
        self.handler = self._create_toolbar_handler(
                get_fuzzy, get_caching, get_profiles, get_regions)

    def _create_toolbar_handler(self, fuzzy, caching, profiles, regions):

        def get_toolbar():
            p = profiles()
            r = regions()
            active_profiles = len(p) if p else 'None'
            active_regions = len(r) if r else 'default(us-east-1)'
            top_tb = [
                    'Active profiles: %s' % active_profiles,
                    'Active regions: %s' % active_regions
                    ]
            top_tb = '   '.join(top_tb)

            is_fuzzy = 'ON' if fuzzy() else 'OFF'
            is_caching = 'ON' if caching() else 'OFF'
            bottom_tb = [
                    '[F2] Fuzzy: %s' % is_fuzzy,
                    '[F3] Caching: %s' % is_caching,
                    '[F5] Refresh cache'
                    ]
            bottom_tb = '   '.join(bottom_tb)

            tb = HTML(text_type('\n'.join((top_tb, bottom_tb))))
            return tb

        return get_toolbar
