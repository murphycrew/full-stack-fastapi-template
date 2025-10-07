from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy import text
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.core.rls import IdentityContext
from app.models import TokenPayload, User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    """Get database session with RLS context management."""
    with Session(engine) as session:
        try:
            yield session
        finally:
            # Clear any RLS context when session closes
            try:
                session.execute(text("SET app.user_id = NULL"))
                session.execute(text("SET app.role = NULL"))
            except Exception:
                # Ignore errors when clearing context
                pass


def get_db_with_rls_context(user: User) -> Generator[Session, None, None]:
    """Get database session with RLS identity context set."""
    with Session(engine) as session:
        try:
            # Set RLS context based on user role
            role = "admin" if user.is_superuser else "user"
            identity_context = IdentityContext(user.id, role)
            identity_context.set_session_context(session)

            yield session
        finally:
            # Clear RLS context when session closes
            try:
                session.execute(text("SET app.user_id = NULL"))
                session.execute(text("SET app.role = NULL"))
            except Exception:
                # Ignore errors when clearing context
                pass


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


# RLS-aware dependencies
def get_rls_session(current_user: CurrentUser) -> Generator[Session, None, None]:
    """Get database session with RLS context set for the current user."""
    yield from get_db_with_rls_context(current_user)


def get_admin_session(current_user: CurrentUser) -> Generator[Session, None, None]:
    """Get database session with admin context for superusers."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    yield from get_db_with_rls_context(current_user)


def get_read_only_admin_session(
    current_user: CurrentUser,
) -> Generator[Session, None, None]:
    """Get database session with read-only admin context for superusers."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    # For read-only admin, we could implement a separate context
    # For now, use regular admin context
    yield from get_db_with_rls_context(current_user)


RLSSessionDep = Annotated[Session, Depends(get_rls_session)]
AdminSessionDep = Annotated[Session, Depends(get_admin_session)]
ReadOnlyAdminSessionDep = Annotated[Session, Depends(get_read_only_admin_session)]
