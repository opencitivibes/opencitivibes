from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
import jwt
from sqlalchemy.orm import Session

import models.schemas as schemas
import repositories.db_models as db_models
from models.config import settings
from models.exceptions import (
    AuthenticationException,
    InactiveUserException,
    InsufficientPermissionsException,
)
from repositories.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
optional_oauth2_scheme = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def authenticate_user(db: Session, email: str, password: str) -> db_models.User | None:
    user = db.query(db_models.User).filter(db_models.User.email == email).first()
    if not user:
        return None
    if not verify_password(password, str(user.hashed_password)):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> db_models.User:
    """
    Get the current authenticated user from the JWT token.

    Raises:
        AuthenticationException: If credentials are invalid or user not found.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email_value = payload.get("sub")
        if email_value is None:
            raise AuthenticationException("Could not validate credentials")
        email: str = str(email_value)
        token_data = schemas.TokenData(email=email)
    except jwt.exceptions.InvalidTokenError:
        raise AuthenticationException("Could not validate credentials")

    user = (
        db.query(db_models.User)
        .filter(db_models.User.email == token_data.email)
        .first()
    )
    if user is None:
        raise AuthenticationException("Could not validate credentials")
    return user


async def get_current_active_user(
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> db_models.User:
    """
    Get the current active user and verify they are not banned.

    Raises:
        InactiveUserException: If the user account has been deactivated.
        UserBannedException: If the user is currently banned.
    """
    if not bool(current_user.is_active):
        raise InactiveUserException("Account has been deactivated")

    # Check for active ban (inline import to avoid circular deps)
    from models.exceptions import UserBannedException
    from services.penalty_service import PenaltyService

    ban = PenaltyService.check_user_banned(db, int(current_user.id))
    if ban:
        raise UserBannedException(ban.expires_at)

    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        optional_oauth2_scheme
    ),
    db: Session = Depends(get_db),
) -> Optional[db_models.User]:
    """
    Get current user if authenticated, otherwise return None.

    If no credentials are provided, returns None (anonymous access).
    If credentials are provided but expired, raises AuthenticationException
    so the user knows to re-login (returns 401).
    If credentials are malformed or invalid, returns None.
    """
    if credentials is None:
        return None

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        email_value = payload.get("sub")
        if email_value is None:
            return None
        email: str = str(email_value)
        user = db.query(db_models.User).filter(db_models.User.email == email).first()
        return user
    except jwt.exceptions.ExpiredSignatureError:
        # Token was provided but expired - user should re-login
        raise AuthenticationException("Session expired. Please log in again.")
    except jwt.exceptions.InvalidTokenError:
        # Other JWT errors (malformed token, etc.) - treat as anonymous
        return None


def check_admin_permission(
    user: db_models.User, category_id: Optional[int], db: Session
) -> bool:
    """Check if user has admin permission for a category or globally."""
    if bool(user.is_global_admin):
        return True

    if category_id is None:
        return False

    # Check if user has admin role for this specific category
    admin_role = (
        db.query(db_models.AdminRole)
        .filter(
            db_models.AdminRole.user_id == user.id,
            db_models.AdminRole.category_id == category_id,
        )
        .first()
    )

    return admin_role is not None


async def get_admin_user(
    current_user: db_models.User = Depends(get_current_user),
) -> db_models.User:
    """
    Require global admin permissions.

    Raises:
        InsufficientPermissionsException: If user is not a global admin.
    """
    if not bool(current_user.is_global_admin):
        raise InsufficientPermissionsException("Not enough permissions")
    return current_user


async def get_official_user(
    current_user: db_models.User = Depends(get_current_active_user),
) -> db_models.User:
    """
    Require official or global admin permissions.

    Officials have read-only analytics access.
    Global admins also have this access.

    Raises:
        InsufficientPermissionsException: If user is not an official or global admin.
    """
    if not (bool(current_user.is_official) or bool(current_user.is_global_admin)):
        raise InsufficientPermissionsException("Official or admin permissions required")
    return current_user


async def get_official_or_admin_user(
    current_user: db_models.User = Depends(get_current_active_user),
) -> db_models.User:
    """
    Alias for get_official_user for clarity in router usage.

    Raises:
        InsufficientPermissionsException: If user is not an official or global admin.
    """
    return await get_official_user(current_user)
