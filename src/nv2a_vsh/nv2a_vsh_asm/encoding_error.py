"""Provides error reporting functionality for the encoder."""

from enum import IntEnum, auto


class EncodingErrorSubtype(IntEnum):
    GENERAL = auto()

    # A #uniform was used without being defined.
    UNDEFINED_UNIFORM = auto()

    # A bracket offset was used on a uniform that goes beyond the end of the uniform. E.g., for a matrix uniform,
    # `#matrix[4]`
    UNIFORM_OFFSET_OUT_OF_RANGE = auto()


class EncodingError(Exception):
    """Represents a fatal error during encoding."""

    def __init__(self, *args, subtype: EncodingErrorSubtype = EncodingErrorSubtype.GENERAL, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtype = subtype
