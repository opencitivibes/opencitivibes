"""
Custom domain exceptions for the application.

These exceptions are raised by the service layer and converted to HTTP exceptions
by centralized exception handlers in main.py, maintaining proper separation of concerns.

The authentication module (auth.py) also uses these domain exceptions to remain
HTTP-agnostic, allowing reuse in non-HTTP contexts (CLI tools, background tasks).

Enhanced with correlation IDs for Sentry integration and user error reporting.
"""

from datetime import datetime

from core.correlation import generate_correlation_id, get_correlation_id


class DomainException(Exception):
    """
    Base class for all domain exceptions.

    Attributes:
        message: Human-readable error message.
        correlation_id: Unique ID for error tracking (auto-generated if not provided).
    """

    def __init__(self, message: str, correlation_id: str | None = None):
        self.message = message
        # Use request correlation ID if available, otherwise generate new one
        self.correlation_id = (
            correlation_id or get_correlation_id() or generate_correlation_id()
        )
        super().__init__(self.message)


class NotFoundException(DomainException):
    """Raised when a requested resource is not found."""

    pass


class PermissionDeniedException(DomainException):
    """Raised when user lacks required permissions."""

    pass


class ValidationException(DomainException):
    """Raised when input validation fails."""

    pass


class ConflictException(DomainException):
    """Raised when operation conflicts with existing data."""

    pass


class AuthenticationException(DomainException):
    """Raised when authentication fails."""

    pass


class AlreadyExistsException(DomainException):
    """Raised when trying to create a resource that already exists."""

    pass


class BusinessRuleException(DomainException):
    """Raised when a business rule is violated."""

    pass


# Specific exceptions for domain entities


class UserNotFoundException(NotFoundException):
    """User not found."""

    pass


class UserAlreadyExistsException(AlreadyExistsException):
    """User already exists."""

    pass


class IdeaNotFoundException(NotFoundException):
    """Idea not found."""

    pass


class CategoryNotFoundException(NotFoundException):
    """Category not found."""

    pass


class CommentNotFoundException(NotFoundException):
    """Comment not found."""

    pass


class VoteNotFoundException(NotFoundException):
    """Vote not found."""

    pass


class QualityNotFoundException(NotFoundException):
    """Quality not found."""

    pass


class InvalidCredentialsException(AuthenticationException):
    """Invalid username or password."""

    pass


class InactiveUserException(PermissionDeniedException):
    """User account is inactive."""

    pass


class InsufficientPermissionsException(PermissionDeniedException):
    """User doesn't have sufficient permissions."""

    pass


class DuplicateVoteException(ConflictException):
    """User has already voted on this idea."""

    pass


class InvalidIdeaStatusException(ValidationException):
    """Invalid idea status."""

    pass


class ContentValidationException(ValidationException):
    """Content validation failed."""

    pass


# Idea deletion exceptions


class IdeaAlreadyDeletedException(BusinessRuleException):
    """Raised when trying to delete an already deleted idea."""

    def __init__(self, idea_id: int) -> None:
        super().__init__(f"Idea {idea_id} is already deleted")
        self.idea_id = idea_id


class CannotDeleteOthersIdeaException(PermissionDeniedException):
    """Raised when user tries to delete an idea they don't own."""

    def __init__(self) -> None:
        super().__init__("You can only delete your own ideas")


class IdeaNotDeletedException(BusinessRuleException):
    """Raised when trying to restore an idea that isn't deleted."""

    def __init__(self, idea_id: int) -> None:
        super().__init__(f"Idea {idea_id} is not deleted")
        self.idea_id = idea_id


# Analytics exceptions


class AnalyticsException(DomainException):
    """Base exception for analytics operations."""

    pass


class InvalidDateRangeException(AnalyticsException):
    """Raised when date range is invalid."""

    pass


class ExportException(AnalyticsException):
    """Raised when export operation fails."""

    pass


# ============================================================================
# Content Moderation Exceptions
# ============================================================================


class FlagException(DomainException):
    """Base exception for flag-related errors."""

    pass


class DuplicateFlagException(FlagException):
    """Raised when user tries to flag same content twice."""

    def __init__(self, message: str = "You have already flagged this content"):
        super().__init__(message)


class CannotFlagOwnContentException(FlagException):
    """Raised when user tries to flag their own content."""

    def __init__(self, message: str = "You cannot flag your own content"):
        super().__init__(message)


class FlagNotFoundException(FlagException):
    """Raised when flag is not found."""

    def __init__(self, flag_id: int):
        super().__init__(f"Flag with ID {flag_id} not found")
        self.flag_id = flag_id


class FlagAlreadyReviewedException(FlagException):
    """Raised when trying to modify an already reviewed flag."""

    def __init__(self, message: str = "This flag has already been reviewed"):
        super().__init__(message)


class PenaltyException(DomainException):
    """Base exception for penalty-related errors."""

    pass


class UserAlreadyPenalizedException(PenaltyException):
    """Raised when user already has an active penalty of same or higher severity."""

    def __init__(self, message: str = "User already has an active penalty"):
        super().__init__(message)


class PenaltyNotFoundException(PenaltyException):
    """Raised when penalty is not found."""

    def __init__(self, penalty_id: int):
        super().__init__(f"Penalty with ID {penalty_id} not found")
        self.penalty_id = penalty_id


class CannotRevokePenaltyException(PenaltyException):
    """Raised when penalty cannot be revoked."""

    def __init__(self, message: str = "This penalty cannot be revoked"):
        super().__init__(message)


class AppealException(DomainException):
    """Base exception for appeal-related errors."""

    pass


class AppealAlreadyExistsException(AppealException):
    """Raised when appeal already exists for a penalty."""

    def __init__(self, message: str = "An appeal already exists for this penalty"):
        super().__init__(message)


class AppealNotFoundException(AppealException):
    """Raised when appeal is not found."""

    def __init__(self, appeal_id: int):
        super().__init__(f"Appeal with ID {appeal_id} not found")
        self.appeal_id = appeal_id


class CannotAppealException(AppealException):
    """Raised when penalty cannot be appealed."""

    def __init__(self, message: str = "This penalty cannot be appealed"):
        super().__init__(message)


class KeywordException(DomainException):
    """Base exception for keyword watchlist errors."""

    pass


class DuplicateKeywordException(KeywordException):
    """Raised when keyword already exists in watchlist."""

    def __init__(self, keyword: str):
        super().__init__(f"Keyword '{keyword}' already exists in watchlist")
        self.keyword = keyword


class KeywordNotFoundException(KeywordException):
    """Raised when keyword is not found."""

    def __init__(self, keyword_id: int):
        super().__init__(f"Keyword with ID {keyword_id} not found")
        self.keyword_id = keyword_id


class InvalidRegexException(KeywordException):
    """Raised when regex pattern is invalid."""

    def __init__(self, pattern: str, error: str):
        super().__init__(f"Invalid regex pattern '{pattern}': {error}")
        self.pattern = pattern
        self.error = error


class AdminNoteException(DomainException):
    """Base exception for admin note errors."""

    pass


class AdminNoteNotFoundException(AdminNoteException):
    """Raised when admin note is not found."""

    def __init__(self, note_id: int):
        super().__init__(f"Admin note with ID {note_id} not found")
        self.note_id = note_id


class UserBannedException(DomainException):
    """Raised when banned user tries to perform restricted action."""

    def __init__(self, expires_at: datetime | None = None):
        if expires_at:
            message = (
                f"Your account is temporarily banned until {expires_at.isoformat()}"
            )
        else:
            message = "Your account has been permanently banned"
        super().__init__(message)
        self.expires_at = expires_at


class CommentRequiresApprovalException(DomainException):
    """Raised when comment is pending approval."""

    def __init__(
        self, message: str = "Your comment is pending approval by a moderator"
    ):
        super().__init__(message)


# ============================================================================
# Rate Limiting Exceptions
# ============================================================================


class RateLimitExceededException(DomainException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after


# ============================================================================
# Email Login Exceptions
# ============================================================================


class EmailLoginException(DomainException):
    """Base exception for email login errors."""

    pass


class EmailLoginCodeExpiredException(EmailLoginException):
    """Raised when login code has expired."""

    def __init__(
        self, message: str = "Login code has expired. Please request a new one."
    ):
        super().__init__(message)


class EmailLoginCodeInvalidException(EmailLoginException):
    """Raised when login code is invalid."""

    def __init__(
        self, message: str = "Invalid login code. Please check and try again."
    ):
        super().__init__(message)


class EmailLoginMaxAttemptsException(EmailLoginException):
    """Raised when maximum verification attempts exceeded."""

    def __init__(
        self, message: str = "Too many failed attempts. Please request a new code."
    ):
        super().__init__(message)


class EmailLoginRateLimitException(EmailLoginException):
    """Raised when rate limit for email login is exceeded."""

    def __init__(
        self,
        message: str = "Too many login code requests. Please try again later.",
        retry_after_seconds: int = 3600,
    ):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class EmailLoginUserNotFoundException(EmailLoginException):
    """Raised when email is not associated with any account."""

    def __init__(self, message: str = "No account found with this email address."):
        super().__init__(message)


class EmailDeliveryException(EmailLoginException):
    """Raised when email fails to send."""

    def __init__(self, message: str = "Failed to send email. Please try again later."):
        super().__init__(message)


# ============================================================================
# Two-Factor Authentication (2FA) Exceptions
# ============================================================================


class TwoFactorException(DomainException):
    """Base exception for 2FA-related errors."""

    pass


class TwoFactorNotEnabledException(TwoFactorException):
    """Raised when 2FA operation requires 2FA but it's not enabled."""

    def __init__(self, message: str = "Two-factor authentication is not enabled."):
        super().__init__(message)


class TwoFactorAlreadyEnabledException(TwoFactorException):
    """Raised when trying to enable 2FA but it's already enabled."""

    def __init__(self, message: str = "Two-factor authentication is already enabled."):
        super().__init__(message)


class TwoFactorInvalidCodeException(TwoFactorException):
    """Raised when TOTP or backup code is invalid."""

    def __init__(self, message: str = "Invalid authentication code."):
        super().__init__(message)


class TwoFactorSetupIncompleteException(TwoFactorException):
    """Raised when trying to complete 2FA setup without pending setup."""

    def __init__(
        self, message: str = "No pending 2FA setup found. Please start setup again."
    ):
        super().__init__(message)


class TwoFactorTempTokenExpiredException(TwoFactorException):
    """Raised when temp token for 2FA verification has expired."""

    def __init__(
        self, message: str = "Verification session expired. Please login again."
    ):
        super().__init__(message)


class TwoFactorConfigurationException(TwoFactorException):
    """Raised when 2FA is not properly configured on the server."""

    def __init__(
        self,
        message: str = "Two-factor authentication is not configured. Contact administrator.",
    ):
        super().__init__(message)


# ============================================================================
# Idea Edit Exceptions
# ============================================================================


class IdeaEditException(DomainException):
    """Base exception for idea edit-related errors."""

    pass


class EditRateLimitException(IdeaEditException):
    """Raised when edit rate limit is exceeded (max 3 edits/month/idea)."""

    def __init__(
        self,
        message: str = "You have reached the maximum number of edits for this idea this month (3). Please try again next month.",
        edits_this_month: int = 0,
        max_edits: int = 3,
    ):
        super().__init__(message)
        self.edits_this_month = edits_this_month
        self.max_edits = max_edits


class EditCooldownException(IdeaEditException):
    """Raised when edit cool-down period hasn't passed (24 hours between edits)."""

    def __init__(
        self,
        message: str = "You must wait 24 hours between edits. Please try again later.",
        retry_after_hours: float = 24.0,
    ):
        super().__init__(message)
        self.retry_after_hours = retry_after_hours


class CannotEditIdeaException(IdeaEditException):
    """Raised when idea cannot be edited due to status constraints."""

    def __init__(
        self,
        message: str = "This idea cannot be edited in its current state.",
    ):
        super().__init__(message)


# ============================================================================
# Trusted Device Exceptions (2FA Remember Device)
# ============================================================================


class TrustedDeviceException(DomainException):
    """Base exception for trusted device-related errors."""

    pass


class TrustedDeviceLimitExceededException(TrustedDeviceException):
    """Raised when maximum number of trusted devices is reached."""

    def __init__(
        self,
        message: str = "Maximum number of trusted devices reached.",
        max_devices: int = 10,
    ):
        super().__init__(message)
        self.max_devices = max_devices


class TrustedDeviceNotFoundException(TrustedDeviceException):
    """Raised when trusted device is not found."""

    def __init__(self, message: str = "Trusted device not found."):
        super().__init__(message)


class TrustedDeviceExpiredException(TrustedDeviceException):
    """Raised when device trust has expired."""

    def __init__(self, message: str = "Device trust has expired."):
        super().__init__(message)
