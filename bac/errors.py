# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.


class TimeoutException(Exception):
    pass


class ArgumentParserDoneException(Exception):
    pass


class ConfigParsingException(Exception):
    def __init__(self, msg):
        super(self.__class__, self).__init__(
            'An error occured while loading profiles: %s' % msg)


class BatchJobSyntaxException(Exception):
    def __init__(self, message, trace):
        msg = ('Invalid batch job syntax found at \"%s\".'
               ' Exception has been raised with following message: %s'
               % ('.'.join(trace), message))
        super(self.__class__, self).__init__(msg)


class NoProfilesError(Exception):
    pass


class BACError(Exception):
    pass


class InvalidAwsCliCommandError(BACError):
    pass


class InvalidArgumentException(BACError):
    pass


class CLICheckerSyntaxError(BACError):
    pass


class CLICheckerPermissionException(BACError):
    pass
