"""FutureLedger exception hierarchy."""


class FutureLedgerError(Exception):
    """Base exception for all FutureLedger errors."""


class SourceError(FutureLedgerError):
    """Raised when an upstream data source or source-layer artifact fails."""

    def __init__(
        self,
        message: str,
        *,
        stage: str | None = None,
        raw_detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.raw_detail = raw_detail


class ValidationError(FutureLedgerError):
    """Raised when input validation fails."""


class ConfigError(FutureLedgerError):
    """Raised when CLI configuration or file paths are invalid."""
