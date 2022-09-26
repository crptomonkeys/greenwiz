class InvalidInput(UserWarning):
    """The user provided input is invalid."""


class InvalidResponse(ValueError):
    """A response from an external API was invalid."""


class UnableToCompleteRequestedAction(Exception):
    """I was unable to complete the requested action and it was my fault."""
