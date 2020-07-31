# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.
from prompt_toolkit.key_binding import KeyBindings
from six import text_type


class Bindings(object):
    """Handles prompt toolkit hotkeys."""
    def __init__(self, toggle_fuzzy, toggle_cache, refresh_cache):
        """
        :param toggle_fuzzy: A callable that toggles fuzzy completion
            on/off.
        :type: callable
        :param toggle_cache: A callable that toggles resource caching.
            on/off.
        :type: callable
        :param refresh_cache: A callable that refreshes resource cache.
        :type: callable
        :rtype: None
        """
        self.bindings = self._create_bindings(toggle_fuzzy,
                                              toggle_cache,
                                              refresh_cache)

    def _create_bindings(self, toggle_fuzzy, toggle_cache, refresh_cache):

        self.bindings = KeyBindings()

        @self.bindings.add(text_type('f2'))
        def _(event):
            """
            Toggle fuzzy completion.
            """
            toggle_fuzzy()

        @self.bindings.add(text_type('f3'))
        def _(event):
            """
            Toggle cache completion.
            """
            toggle_cache()

        @self.bindings.add(text_type('f5'))
        def _(event):
            """
            Refresh bac_completer resource cache.
            """
            refresh_cache()

        return self.bindings
