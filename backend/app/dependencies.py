"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.guest import Guest
from app.models.user import User
from app.models.enums import UserRole
from app.services.security import decode_token


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    """Extract and validate the current user from the access_token cookie.

    Raises 401 if token is missing, expired, or user not found.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
        )

    payload = decode_token(access_token, expected_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен недействителен или истёк",
        )

    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен",
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    return user


# Typed alias for convenience
CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_guest(
    db: Annotated[AsyncSession, Depends(get_db)],
    guest_token: Annotated[str | None, Cookie()] = None,
) -> Guest:
    """Extract and validate the current guest from the guest_token cookie.

    Raises 401 if token is missing, expired, or guest not found.
    """
    if not guest_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Гость не авторизован",
        )

    payload = decode_token(guest_token, expected_type="guest")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен недействителен или истёк",
        )

    guest_id: str | None = payload.get("sub")
    if guest_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен",
        )

    try:
        result = await db.execute(select(Guest).where(Guest.id == int(guest_id)))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен",
        )
    guest = result.scalar_one_or_none()
    if guest is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Гость не найден",
        )

    return guest


async def get_optional_guest(
    db: Annotated[AsyncSession, Depends(get_db)],
    guest_token: Annotated[str | None, Cookie()] = None,
) -> Guest | None:
    """Return the current guest or None if not authenticated.

    Use this for endpoints that show extra content to authenticated guests
    (e.g. 'Repeat order' button) without blocking anonymous access.
    """
    if not guest_token:
        return None

    payload = decode_token(guest_token, expected_type="guest")
    if payload is None:
        return None

    guest_id: str | None = payload.get("sub")
    if guest_id is None:
        return None

    try:
        result = await db.execute(select(Guest).where(Guest.id == int(guest_id)))
    except ValueError:
        return None
    return result.scalar_one_or_none()


# Typed aliases for convenience
CurrentGuest = Annotated[Guest, Depends(get_current_guest)]
OptionalGuest = Annotated[Guest | None, Depends(get_optional_guest)]


def require_role(*roles: UserRole):
    """Dependency factory that restricts access to users with specific roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.owner))])
    """

    async def _check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return user

    return _check
