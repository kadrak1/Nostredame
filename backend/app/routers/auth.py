"""Authentication router — login, refresh, me."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.audit import log_action
from app.services.brute_force import login_guard
from app.services.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.utils import get_client_ip

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie settings
_COOKIE_KWARGS = {
    "httponly": True,
    "samesite": "strict",
    "secure": settings.app_env == "production",
    "path": "/",
}


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate admin user and return JWT tokens.

    - Access token returned in the JSON body AND set as httpOnly cookie.
    - Refresh token set as httpOnly cookie only.
    """
    ip = get_client_ip(request)

    # --- Brute-force check ---
    if login_guard.is_blocked(ip, body.login):
        remaining = login_guard.remaining_block_seconds(ip, body.login)
        logger.warning("login_blocked", login=body.login, remaining_s=remaining)
        await log_action(
            db,
            "login_blocked",
            details=f"login={body.login} remaining={remaining}s",
            ip_address=ip,
        )
        # Commit before raise so the audit record survives the session rollback
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Слишком много попыток. Попробуйте через {remaining // 60 + 1} мин.",
        )

    # --- Find user ---
    result = await db.execute(select(User).where(User.login == body.login))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        login_guard.record_failure(ip, body.login)
        logger.warning("login_failure", login=body.login)
        await log_action(
            db,
            "login_failure",
            details=f"login={body.login}",
            ip_address=ip,
        )
        # Commit before raise so the audit record survives the session rollback
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    # --- Success ---
    login_guard.record_success(ip, body.login)

    token_data = {
        "sub": str(user.id),
        "venue_id": user.venue_id,
        "role": user.role.value,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        **_COOKIE_KWARGS,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        **_COOKIE_KWARGS,
    )

    logger.info("login_success", user_id=user.id, login=user.login)
    await log_action(
        db,
        "login_success",
        user_id=user.id,
        details=f"login={user.login}",
        ip_address=ip,
    )

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Refresh access token using the refresh_token cookie."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token отсутствует",
        )

    payload = decode_token(token, expected_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token недействителен или истёк",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный refresh token",
        )

    # Verify user still exists
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    token_data = {
        "sub": str(user.id),
        "venue_id": user.venue_id,
        "role": user.role.value,
    }
    new_access = create_access_token(token_data)

    response.set_cookie(
        key="access_token",
        value=new_access,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        **_COOKIE_KWARGS,
    )

    logger.info("token_refresh", user_id=user.id)
    return TokenResponse(access_token=new_access)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    """Return the current authenticated user's profile."""
    return UserResponse.model_validate(user)


@router.post("/logout")
async def logout(
    response: Response,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Clear auth cookies and record logout in audit log."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    logger.info("logout", user_id=user.id)
    await log_action(db, "logout", user_id=user.id)
    return {"detail": "ok"}
