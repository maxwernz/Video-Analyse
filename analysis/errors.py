class AnalysisError(Exception):
    """Base class for Analysis domain and persistence failures."""


class InvalidAnalysisDataError(AnalysisError):
    """The decoded data does not satisfy the Analysis invariants."""


class AnalysisFileError(AnalysisError):
    """An Analysis file could not be read or written."""


class UnsupportedContentError(AnalysisFileError):
    """The file is neither supported JSON nor a supported legacy pickle."""


class UnsafeLegacyAnalysisError(AnalysisFileError):
    """A legacy file contains a global or value that is not allowlisted."""


class MalformedJSONError(AnalysisFileError):
    """JSON-looking content cannot be decoded as JSON."""


class UnsupportedSchemaVersionError(AnalysisFileError):
    """The JSON schema version is not supported by this release."""


class SaveAsRequiredError(AnalysisFileError):
    """The Analysis has no writable current-version file location."""


class LegacySourceOverwriteError(AnalysisFileError):
    """A conversion attempted to overwrite its read-only legacy source."""


class EmptyAnalysisError(AnalysisFileError):
    """An Analysis without a Source video cannot be saved."""
