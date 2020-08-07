# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.


class ArgumentParserDoneException(Exception):
    """Raised when --help recieved or an exception occurs."""
    pass


class BatchJobSyntaxException(Exception):
    """
    Raised if invalid syntax is encountered during batch-command parse.
    """
    def __init__(self, message, trace):
        msg = ('Invalid batch job syntax found at \"%s\".'
               ' Exception has been raised with following message: %s'
               % ('.'.join(trace), message))
        super(self.__class__, self).__init__(msg)


class ConfigParsingException(Exception):
    """
    Raised if some errors occurs during parse of aws config files.
    """
    def __init__(self, msg):
        super(self.__class__, self).__init__(
            'An error occured while loading profiles: %s' % msg)


class ModelLoadingError(Exception):
    """Raised on service or operation model loading failures."""
    pass


class NoProfilesError(Exception):
    """Raised if no named profiles are specified."""
    pass


class NullIntervalException(Exception):
    """Raised on query completer context errors."""
    def __init__(self, pos, **kwds):
        self.pos = pos
        super(NullIntervalException, self).__init__(**kwds)


class TimeoutException(Exception):
    """
    Raised if timeout is exceeded during subprocess command execution.
    """
    pass


class BACError(Exception):
    """
    General error, used mainly for derivation of other exceptions.
    """
    pass


class CLICheckerPermissionException(BACError):
    """Raised if explicit deny is received by policy simulation."""
    pass


class CLICheckerSyntaxError(BACError):
    """Raised if invalid awscli command syntax is encountered."""
    pass


class InvalidArgumentException(BACError):
    """Raised if batch-command is called with invalid arguments."""
    pass


class InvalidAwsCliCommandError(BACError):
    """Raised if awscli command call is malformed or invalid."""
    pass
