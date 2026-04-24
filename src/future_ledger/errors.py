"""FutureLedger exception hierarchy."""


class FutureLedgerError(Exception):
    """Base exception for all FutureLedger errors."""


class SourceError(FutureLedgerError):
    """Raised when an upstream data source fails or returns unexpected data."""


class ValidationError(FutureLedgerError):
    """Raised when input validation fails."""


class ConfigError(FutureLedgerError):
    """Raised when CLI configuration or file paths are invalid."""
