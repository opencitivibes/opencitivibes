# ruff: noqa: E402
# E402 disabled: load_dotenv() must run before other imports for Sentry DSN

import os
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import sentry_sdk
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from core.correlation import (
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
)
from core.logging_config import configure_logging
from core.sentry_config import init_sentry
from helpers.rate_limiter import limiter
from helpers.security_headers import SecurityHeadersMiddleware
from models.config import settings
from models.exceptions import (
    AdminNoteNotFoundException,
    AlreadyExistsException,
    AppealAlreadyExistsException,
    AppealNotFoundException,
    AuthenticationException,
    BusinessRuleException,
    CannotAppealException,
    CannotFlagOwnContentException,
    CannotRevokePenaltyException,
    CommentRequiresApprovalException,
    ConflictException,
    DomainException,
    DuplicateFlagException,
    DuplicateKeywordException,
    FlagAlreadyReviewedException,
    FlagNotFoundException,
    InvalidRegexException,
    KeywordNotFoundException,
    NotFoundException,
    PenaltyNotFoundException,
    PermissionDeniedException,
    UserAlreadyPenalizedException,
    UserBannedException,
    ValidationException,
)
from repositories.database import Base, engine
from routers import (
    admin_router,
    analytics_router,
    auth_router,
    categories_router,
    comments_router,
    flags_router,
    ideas_router,
    search_router,
    tags_router,
    votes_router,
)

# Initialize Sentry BEFORE app creation
init_sentry()

# Configure logging with Loguru
configure_logging(os.getenv("ENVIRONMENT", "development"))


def check_schema_version() -> None:
    """Verify database schema version matches expected migration.

    This helps catch cases where the application code expects a newer schema
    than what's deployed in the database.
    """
    from sqlalchemy import text

    from repositories.database import SessionLocal

    # Expected latest migration revision (update when adding new migrations)
    EXPECTED_REVISION = (
        "a5ch44e31f6c"  # add_retention_fields  # pragma: allowlist secret
    )

    db = SessionLocal()
    try:
        result = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        row = result.fetchone()
        if row:
            current_revision = row[0]
            if current_revision != EXPECTED_REVISION:
                logger.warning(
                    f"Database schema mismatch! "
                    f"Current: {current_revision}, Expected: {EXPECTED_REVISION}. "
                    f"Run 'alembic upgrade head' to update the database schema."
                )
            else:
                logger.info(f"Database schema version: {current_revision} (up to date)")
        else:
            logger.warning(
                "No alembic_version found. Database may not be initialized with migrations."
            )
    except Exception as e:
        logger.warning(f"Could not verify schema version: {e}")
    finally:
        db.close()


import asyncio

# Security monitoring shutdown flag
_security_monitor_shutdown = False


async def _security_monitoring_task():
    """
    Background task for security monitoring.

    Runs every 15 minutes to check for suspicious patterns.
    Required by Law 25 Article 3.5 for breach detection.
    """
    from repositories.database import SessionLocal
    from services.security_audit_service import SecurityAuditService
    from services.incident_service import IncidentService
    from services.notification_service import NotificationService
    from models.notification_types import NotificationType
    import json

    while not _security_monitor_shutdown:
        try:
            db = SessionLocal()
            try:
                alerts = SecurityAuditService.detect_suspicious_patterns(db)

                if alerts:
                    logger.warning(f"Security monitoring detected {len(alerts)} alerts")

                    for alert in alerts:
                        if alert.get("severity") == "critical":
                            # Auto-create incident for critical alerts
                            IncidentService.create_incident(
                                db=db,
                                incident_type="suspicious_activity",
                                severity="high",
                                title=f"Automated alert: {alert.get('type')}",
                                description=json.dumps(alert, indent=2),
                            )

                            # Send immediate notification
                            NotificationService.send_fire_and_forget(
                                NotificationType.CRITICAL,
                                f"SECURITY: {alert.get('type')}",
                                json.dumps(alert),
                                priority_override="max",
                            )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Security monitoring error: {e}")

        # Wait 15 minutes before next check
        await asyncio.sleep(15 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    - Verify database schema version matches expected migration.
    - Optionally create tables when `AUTO_CREATE_DB` is enabled (development).
    - Verify and rebuild search index if needed.
    - Start background security monitoring task.
    - Place other startup/shutdown tasks here.
    """
    global _security_monitor_shutdown

    # Check schema version first
    check_schema_version()

    if settings.AUTO_CREATE_DB:
        logger.info(
            "AUTO_CREATE_DB enabled; creating database tables via SQLAlchemy create_all()"
        )
        Base.metadata.create_all(bind=engine)
    else:
        logger.info("AUTO_CREATE_DB disabled; skipping automatic create_all()")

    # Verify and repair search index on startup
    try:
        from repositories.database import SessionLocal
        from services.search import SearchService

        db = SessionLocal()
        try:
            logger.info("Verifying search index...")
            is_ready = SearchService.ensure_index_ready(db)
            if is_ready:
                logger.info("Search index verification complete")
            else:
                logger.warning(
                    "Search index not available - search functionality may be limited"
                )
        except Exception as e:
            logger.error(f"Search index verification failed: {e}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to initialize search service: {e}")

    # Start security monitoring background task
    _security_monitor_shutdown = False
    security_task = asyncio.create_task(_security_monitoring_task())
    logger.info("Security monitoring background task started")

    # Start retention scheduler (Law 25 Phase 3)
    from core.scheduler import setup_scheduler, shutdown_scheduler

    if settings.ENVIRONMENT != "test":
        setup_scheduler()

    try:
        yield
    finally:
        # Shutdown retention scheduler
        if settings.ENVIRONMENT != "test":
            shutdown_scheduler()

        # Signal security monitoring to stop
        _security_monitor_shutdown = True
        security_task.cancel()
        try:
            await security_task
        except asyncio.CancelledError:
            pass
        logger.info("Security monitoring background task stopped")


def _get_api_title() -> str:
    """Get API title from platform configuration."""
    from services.config_service import get_config

    config = get_config()
    default_locale = config.localization.default_locale
    instance_name = config.instance.name.get(default_locale, "OpenCitiVibes")
    return f"{instance_name} API"


app = FastAPI(title=_get_api_title(), lifespan=lifespan)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Inject correlation ID into request context and Sentry."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with correlation ID tracking."""
        # Check for incoming correlation ID (from frontend)
        correlation_id = (
            request.headers.get("X-Correlation-ID") or generate_correlation_id()
        )
        set_correlation_id(correlation_id)

        # Add to Sentry context
        sentry_sdk.set_tag("correlation_id", correlation_id)

        response = await call_next(request)

        # Include in response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests with performance monitoring."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and log timing information."""
        start_time = time.perf_counter()

        # Log request
        client_host = request.client.host if request.client else "unknown"
        logger.info(f"Request: {request.method} {request.url.path} from {client_host}")

        response = await call_next(request)

        # Calculate duration
        duration = time.perf_counter() - start_time

        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration:.3f}s"
        )

        # Warn on slow requests (configurable threshold)
        if duration > settings.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {duration:.2f}s (threshold: {settings.SLOW_REQUEST_THRESHOLD}s)"
            )

        # Add response time header for monitoring
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response


# Add security headers middleware (runs last, so added first)
# Note: Middleware runs in reverse order - security headers should wrap everything
app.add_middleware(SecurityHeadersMiddleware)

# Add correlation ID middleware (runs after security, before logging)
app.add_middleware(CorrelationIdMiddleware)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Configure CORS from environment settings
# In development, allow all origins for mobile/network testing
cors_origins = ["*"] if settings.ENVIRONMENT == "development" else settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True if settings.ENVIRONMENT != "development" else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for avatars
uploads_dir = Path("data/uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/data/uploads", StaticFiles(directory="data/uploads"), name="uploads")


# Global unhandled exception handler (returns generic 500 and logs details)
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch all unhandled exceptions with full Sentry capture."""
    correlation_id = get_correlation_id() or generate_correlation_id()

    # Always capture 5xx errors in Sentry
    sentry_sdk.set_tag("correlation_id", correlation_id)
    sentry_sdk.capture_exception(exc)

    # Log with full context
    # Use repr() to escape curly braces in exception message
    # (loguru's .format() interprets them as placeholders otherwise)
    logger.exception(
        f"Unhandled exception: {exc!r}",
        correlation_id=correlation_id,
        path=str(request.url.path),
        method=request.method,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "correlation_id": correlation_id,
        },
    )


# Centralized exception handlers
@app.exception_handler(NotFoundException)
async def not_found_exception_handler(
    request: Request, exc: NotFoundException
) -> JSONResponse:
    """Handle not found exceptions with Sentry integration."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    sentry_sdk.set_tag("exception_type", exc.__class__.__name__)

    logger.warning(
        f"Not found: {exc.message}",
        correlation_id=exc.correlation_id,
        exception_type=exc.__class__.__name__,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "correlation_id": exc.correlation_id,
        },
    )


@app.exception_handler(AlreadyExistsException)
async def already_exists_exception_handler(
    request: Request, exc: AlreadyExistsException
) -> JSONResponse:
    """Handle already exists exceptions with Sentry integration."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    sentry_sdk.set_tag("exception_type", exc.__class__.__name__)

    logger.warning(
        f"Already exists: {exc.message}",
        correlation_id=exc.correlation_id,
        exception_type=exc.__class__.__name__,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": exc.message,
            "correlation_id": exc.correlation_id,
        },
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(
    request: Request, exc: ValidationException
) -> JSONResponse:
    """Handle validation exceptions with Sentry integration."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    sentry_sdk.set_tag("exception_type", exc.__class__.__name__)

    logger.warning(
        f"Validation error: {exc.message}",
        correlation_id=exc.correlation_id,
        exception_type=exc.__class__.__name__,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": exc.message,
            "correlation_id": exc.correlation_id,
        },
    )


@app.exception_handler(PermissionDeniedException)
async def permission_denied_exception_handler(
    request: Request, exc: PermissionDeniedException
) -> JSONResponse:
    """Handle permission denied exceptions with Sentry integration."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    sentry_sdk.set_tag("exception_type", exc.__class__.__name__)

    logger.warning(
        f"Permission denied: {exc.message}",
        correlation_id=exc.correlation_id,
        exception_type=exc.__class__.__name__,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "detail": exc.message,
            "correlation_id": exc.correlation_id,
        },
    )


@app.exception_handler(AuthenticationException)
async def authentication_exception_handler(
    request: Request, exc: AuthenticationException
) -> JSONResponse:
    """Handle authentication exceptions with Sentry integration."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    sentry_sdk.set_tag("exception_type", exc.__class__.__name__)

    # Auth failures are security-relevant, capture in Sentry
    sentry_sdk.capture_exception(exc)

    logger.warning(
        f"Authentication failed: {exc.message}",
        correlation_id=exc.correlation_id,
        exception_type=exc.__class__.__name__,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "detail": exc.message,
            "correlation_id": exc.correlation_id,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(BusinessRuleException)
async def business_rule_exception_handler(
    request: Request, exc: BusinessRuleException
) -> JSONResponse:
    """Handle business rule exceptions with Sentry integration."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    sentry_sdk.set_tag("exception_type", exc.__class__.__name__)

    logger.warning(
        f"Business rule violation: {exc.message}",
        correlation_id=exc.correlation_id,
        exception_type=exc.__class__.__name__,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.message,
            "correlation_id": exc.correlation_id,
        },
    )


@app.exception_handler(ConflictException)
async def conflict_exception_handler(
    request: Request, exc: ConflictException
) -> JSONResponse:
    """Handle conflict exceptions with Sentry integration."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    sentry_sdk.set_tag("exception_type", exc.__class__.__name__)

    logger.warning(
        f"Conflict: {exc.message}",
        correlation_id=exc.correlation_id,
        exception_type=exc.__class__.__name__,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": exc.message,
            "correlation_id": exc.correlation_id,
        },
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    """Handle generic domain exceptions with Sentry integration."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    sentry_sdk.set_tag("exception_type", exc.__class__.__name__)

    # Capture unexpected domain exceptions
    sentry_sdk.capture_exception(exc)

    logger.warning(
        f"Domain exception: {exc.message}",
        correlation_id=exc.correlation_id,
        exception_type=exc.__class__.__name__,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.message,
            "type": exc.__class__.__name__,
            "correlation_id": exc.correlation_id,
        },
    )


# ============================================================================
# Content Moderation Exception Handlers
# ============================================================================


@app.exception_handler(DuplicateFlagException)
async def duplicate_flag_handler(
    request: Request, exc: DuplicateFlagException
) -> JSONResponse:
    """Handle duplicate flag exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Duplicate flag: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(CannotFlagOwnContentException)
async def cannot_flag_own_handler(
    request: Request, exc: CannotFlagOwnContentException
) -> JSONResponse:
    """Handle cannot flag own content exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(
        f"Cannot flag own content: {exc.message}", path=str(request.url.path)
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(FlagNotFoundException)
async def flag_not_found_handler(
    request: Request, exc: FlagNotFoundException
) -> JSONResponse:
    """Handle flag not found exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Flag not found: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(FlagAlreadyReviewedException)
async def flag_reviewed_handler(
    request: Request, exc: FlagAlreadyReviewedException
) -> JSONResponse:
    """Handle flag already reviewed exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Flag already reviewed: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(UserAlreadyPenalizedException)
async def user_penalized_handler(
    request: Request, exc: UserAlreadyPenalizedException
) -> JSONResponse:
    """Handle user already penalized exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"User already penalized: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(PenaltyNotFoundException)
async def penalty_not_found_handler(
    request: Request, exc: PenaltyNotFoundException
) -> JSONResponse:
    """Handle penalty not found exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Penalty not found: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(CannotRevokePenaltyException)
async def cannot_revoke_handler(
    request: Request, exc: CannotRevokePenaltyException
) -> JSONResponse:
    """Handle cannot revoke penalty exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Cannot revoke penalty: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(AppealAlreadyExistsException)
async def appeal_exists_handler(
    request: Request, exc: AppealAlreadyExistsException
) -> JSONResponse:
    """Handle appeal already exists exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Appeal already exists: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(AppealNotFoundException)
async def appeal_not_found_handler(
    request: Request, exc: AppealNotFoundException
) -> JSONResponse:
    """Handle appeal not found exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Appeal not found: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(CannotAppealException)
async def cannot_appeal_handler(
    request: Request, exc: CannotAppealException
) -> JSONResponse:
    """Handle cannot appeal exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Cannot appeal: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(DuplicateKeywordException)
async def duplicate_keyword_handler(
    request: Request, exc: DuplicateKeywordException
) -> JSONResponse:
    """Handle duplicate keyword exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Duplicate keyword: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(KeywordNotFoundException)
async def keyword_not_found_handler(
    request: Request, exc: KeywordNotFoundException
) -> JSONResponse:
    """Handle keyword not found exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Keyword not found: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(InvalidRegexException)
async def invalid_regex_handler(
    request: Request, exc: InvalidRegexException
) -> JSONResponse:
    """Handle invalid regex exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Invalid regex: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(AdminNoteNotFoundException)
async def note_not_found_handler(
    request: Request, exc: AdminNoteNotFoundException
) -> JSONResponse:
    """Handle admin note not found exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.warning(f"Admin note not found: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


@app.exception_handler(UserBannedException)
async def user_banned_handler(
    request: Request, exc: UserBannedException
) -> JSONResponse:
    """Handle user banned exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    # Capture ban attempts in Sentry for security monitoring
    sentry_sdk.capture_exception(exc)
    logger.warning(f"User banned: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "detail": exc.message,
            "expires_at": exc.expires_at.isoformat() if exc.expires_at else None,
            "correlation_id": exc.correlation_id,
        },
    )


@app.exception_handler(CommentRequiresApprovalException)
async def comment_approval_handler(
    request: Request, exc: CommentRequiresApprovalException
) -> JSONResponse:
    """Handle comment requires approval exception."""
    sentry_sdk.set_tag("correlation_id", exc.correlation_id)
    logger.info(f"Comment pending approval: {exc.message}", path=str(request.url.path))
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"detail": exc.message, "correlation_id": exc.correlation_id},
    )


# ============================================================================
# Rate Limiting Exception Handlers
# ============================================================================


def _register_rate_limit_handler(app_instance: FastAPI) -> None:
    """Register rate limit exception handler with late import."""
    from models.exceptions import RateLimitExceededException

    @app_instance.exception_handler(RateLimitExceededException)
    async def rate_limit_exceeded_handler(
        request: Request, exc: RateLimitExceededException
    ) -> JSONResponse:
        """Handle rate limit exceeded exception."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(
            f"Rate limit exceeded: {exc.message}", path=str(request.url.path)
        )

        headers = {}
        if exc.retry_after:
            headers["Retry-After"] = str(exc.retry_after)

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": exc.message, "correlation_id": exc.correlation_id},
            headers=headers,
        )


# Register rate limit handler
_register_rate_limit_handler(app)


# ============================================================================
# Email Login Exception Handlers
# ============================================================================


def _register_email_login_handlers(app_instance: FastAPI) -> None:
    """Register email login exception handlers with late import."""
    from models.exceptions import (
        EmailDeliveryException,
        EmailLoginCodeExpiredException,
        EmailLoginCodeInvalidException,
        EmailLoginMaxAttemptsException,
        EmailLoginRateLimitException,
        EmailLoginUserNotFoundException,
    )

    @app_instance.exception_handler(EmailLoginCodeExpiredException)
    async def email_code_expired_handler(
        request: Request, exc: EmailLoginCodeExpiredException
    ) -> JSONResponse:
        """Handle expired login code."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(f"Email code expired: {exc.message}", path=str(request.url.path))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": exc.message,
                "type": "email_code_expired",
                "correlation_id": exc.correlation_id,
            },
        )

    @app_instance.exception_handler(EmailLoginCodeInvalidException)
    async def email_code_invalid_handler(
        request: Request, exc: EmailLoginCodeInvalidException
    ) -> JSONResponse:
        """Handle invalid login code."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(f"Email code invalid: {exc.message}", path=str(request.url.path))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": exc.message,
                "type": "email_code_invalid",
                "correlation_id": exc.correlation_id,
            },
        )

    @app_instance.exception_handler(EmailLoginMaxAttemptsException)
    async def email_max_attempts_handler(
        request: Request, exc: EmailLoginMaxAttemptsException
    ) -> JSONResponse:
        """Handle max attempts exceeded."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(
            f"Email login max attempts: {exc.message}", path=str(request.url.path)
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": exc.message,
                "type": "email_max_attempts",
                "correlation_id": exc.correlation_id,
            },
        )

    @app_instance.exception_handler(EmailLoginRateLimitException)
    async def email_rate_limit_handler(
        request: Request, exc: EmailLoginRateLimitException
    ) -> JSONResponse:
        """Handle email login rate limit."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(
            f"Email login rate limit: {exc.message}", path=str(request.url.path)
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": exc.message,
                "type": "email_rate_limit",
                "retry_after_seconds": exc.retry_after_seconds,
                "correlation_id": exc.correlation_id,
            },
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )

    @app_instance.exception_handler(EmailLoginUserNotFoundException)
    async def email_user_not_found_handler(
        request: Request, exc: EmailLoginUserNotFoundException
    ) -> JSONResponse:
        """Handle email not found - use 400 to prevent email enumeration."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(
            f"Email login user not found: {exc.message}", path=str(request.url.path)
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": exc.message,
                "type": "email_user_not_found",
                "correlation_id": exc.correlation_id,
            },
        )

    @app_instance.exception_handler(EmailDeliveryException)
    async def email_delivery_handler(
        request: Request, exc: EmailDeliveryException
    ) -> JSONResponse:
        """Handle email delivery failure."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        sentry_sdk.capture_exception(exc)  # Capture delivery failures
        logger.error(
            f"Email delivery failed: {exc.message}", path=str(request.url.path)
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": exc.message,
                "type": "email_delivery_failed",
                "correlation_id": exc.correlation_id,
            },
        )


# Register email login handlers
_register_email_login_handlers(app)


# ============================================================================
# Two-Factor Authentication (2FA) Exception Handlers
# ============================================================================


def _register_2fa_handlers(app_instance: FastAPI) -> None:
    """Register 2FA exception handlers with late import."""
    from models.exceptions import (
        TwoFactorAlreadyEnabledException,
        TwoFactorConfigurationException,
        TwoFactorInvalidCodeException,
        TwoFactorNotEnabledException,
        TwoFactorSetupIncompleteException,
        TwoFactorTempTokenExpiredException,
    )

    @app_instance.exception_handler(TwoFactorNotEnabledException)
    async def two_factor_not_enabled_handler(
        request: Request, exc: TwoFactorNotEnabledException
    ) -> JSONResponse:
        """Handle 2FA not enabled exception."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(f"2FA not enabled: {exc.message}", path=str(request.url.path))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": exc.message,
                "type": "2fa_not_enabled",
                "correlation_id": exc.correlation_id,
            },
        )

    @app_instance.exception_handler(TwoFactorAlreadyEnabledException)
    async def two_factor_already_enabled_handler(
        request: Request, exc: TwoFactorAlreadyEnabledException
    ) -> JSONResponse:
        """Handle 2FA already enabled exception."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(
            f"2FA already enabled: {exc.message}", path=str(request.url.path)
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": exc.message,
                "type": "2fa_already_enabled",
                "correlation_id": exc.correlation_id,
            },
        )

    @app_instance.exception_handler(TwoFactorInvalidCodeException)
    async def two_factor_invalid_code_handler(
        request: Request, exc: TwoFactorInvalidCodeException
    ) -> JSONResponse:
        """Handle invalid 2FA code exception."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(f"2FA invalid code: {exc.message}", path=str(request.url.path))
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": exc.message,
                "type": "2fa_invalid_code",
                "correlation_id": exc.correlation_id,
            },
        )

    @app_instance.exception_handler(TwoFactorSetupIncompleteException)
    async def two_factor_setup_incomplete_handler(
        request: Request, exc: TwoFactorSetupIncompleteException
    ) -> JSONResponse:
        """Handle 2FA setup incomplete exception."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(
            f"2FA setup incomplete: {exc.message}", path=str(request.url.path)
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": exc.message,
                "type": "2fa_setup_incomplete",
                "correlation_id": exc.correlation_id,
            },
        )

    @app_instance.exception_handler(TwoFactorTempTokenExpiredException)
    async def two_factor_temp_token_expired_handler(
        request: Request, exc: TwoFactorTempTokenExpiredException
    ) -> JSONResponse:
        """Handle 2FA temp token expired exception."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        logger.warning(
            f"2FA temp token expired: {exc.message}", path=str(request.url.path)
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": exc.message,
                "type": "2fa_temp_token_expired",
                "correlation_id": exc.correlation_id,
            },
        )

    @app_instance.exception_handler(TwoFactorConfigurationException)
    async def two_factor_configuration_handler(
        request: Request, exc: TwoFactorConfigurationException
    ) -> JSONResponse:
        """Handle 2FA configuration exception."""
        sentry_sdk.set_tag("correlation_id", exc.correlation_id)
        sentry_sdk.capture_exception(exc)  # Configuration issues are critical
        logger.error(
            f"2FA configuration error: {exc.message}", path=str(request.url.path)
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": exc.message,
                "type": "2fa_configuration_error",
                "correlation_id": exc.correlation_id,
            },
        )


# Register 2FA handlers
_register_2fa_handlers(app)


# Include routers
app.include_router(auth_router.router, prefix="/api")
app.include_router(categories_router.router, prefix="/api")
app.include_router(ideas_router.router, prefix="/api")
app.include_router(votes_router.router, prefix="/api")
app.include_router(comments_router.router, prefix="/api")
app.include_router(tags_router.router, prefix="/api")
app.include_router(search_router.router, prefix="/api")
app.include_router(admin_router.router, prefix="/api")
app.include_router(analytics_router.router, prefix="/api")
app.include_router(flags_router.router, prefix="/api")

# Import appeals_router here to avoid linter removing unused import at top
from routers import appeals_router

app.include_router(appeals_router.router, prefix="/api")

# Import moderation_router here to avoid linter removing unused import at top
from routers import moderation_router

app.include_router(moderation_router.router, prefix="/api")

# Import officials_router here to avoid linter removing unused import at top
from routers import officials_router

app.include_router(officials_router.router, prefix="/api")

# Import sitemap_router for SEO
from routers import sitemap_router

app.include_router(sitemap_router.router, prefix="/api")

# Import config_router for platform configuration
from routers import config_router
from services.config_service import get_config, get_instance_name

app.include_router(config_router.router, prefix="/api")

# Import legal_router for legal content (Terms of Service, Privacy Policy)
from routers import legal_router

app.include_router(legal_router.router, prefix="/api")

# Import email_login_router for passwordless authentication
from routers import email_login_router

app.include_router(email_login_router.router, prefix="/api")

# Import totp_router for 2FA authentication
from routers import totp_router

app.include_router(totp_router.router, prefix="/api")

# Import notifications_router for admin notification viewer
from routers import notifications_router

app.include_router(notifications_router.router, prefix="/api")

# Import errors_router for frontend error reporting to ntfy
from routers import errors_router

app.include_router(errors_router.router, prefix="/api")

# Import security_router for security audit logs and incident management (Law 25)
from routers import security_router

app.include_router(security_router.router, prefix="/api")

# Import users_router for public profile endpoints (Law 25 - Phase 4: Privacy Settings)
from routers import users_router

app.include_router(users_router.router, prefix="/api")


@app.get("/")
def root() -> dict:
    """Root endpoint with instance-aware message."""
    config = get_config()
    instance_name = get_instance_name(config.localization.default_locale)
    return {
        "message": f"Welcome to {instance_name} API",
        "platform": config.platform.get("name", "OpenCitiVibes"),
        "version": config.platform.get("version", "1.0.0"),
    }


@app.get("/api/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}
