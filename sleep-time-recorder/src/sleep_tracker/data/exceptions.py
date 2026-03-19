"""Custom exceptions for the data layer."""


class SleepTrackerDataError(Exception):
    """Base exception for persistence-related failures."""


class DatabaseInitializationError(SleepTrackerDataError):
    """Raised when schema setup or migration fails."""


class SessionNotFoundError(SleepTrackerDataError):
    """Raised when a session id cannot be found."""


class SessionStateError(SleepTrackerDataError):
    """Raised when session state does not allow requested operation."""


class ActiveSessionExistsError(SessionStateError):
    """Raised when starting a session while another one is active."""


class NoActiveSessionError(SessionStateError):
    """Raised when ending a session but no active session exists."""
