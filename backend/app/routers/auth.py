"""
Auth routes:
  POST /v1/auth/signup
  POST /v1/auth/login
  POST /v1/auth/logout
  GET  /v1/auth/me
  POST /v1/auth/verify-email
  POST /v1/auth/resend-verification
  POST /v1/auth/forgot-password
  POST /v1/auth/reset-password
  POST /v1/auth/change-password
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

import structlog
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import APIRouter, BackgroundTasks, Query, Request, Response
from sqlalchemy import select, update

from app.config import settings
from app.crypto import encrypt_email, email_search_hash, generate_token, hash_token, decrypt_email
from app.dependencies import DBDep, AuthDep
from app.exceptions import UnauthorizedError, ValidationError
from app.models.user import User
from app.models.tokens import PasswordResetToken, EmailVerificationToken
from app.models.workspace import WorkspaceMember
from app.schemas.auth import (
    SignupRequest, LoginRequest, UserResponse,
    PasswordResetRequestBody, PasswordResetConfirmBody, ChangePasswordBody,
)
from app.services.email_service import (
    send_verification_email, send_password_reset_email, send_already_registered_email
)
from app.services.pwned_passwords import is_password_pwned
from app.services.rate_limiter import RateLimiter
from app.services.session import SessionService

log = structlog.get_logger()
router = APIRouter(prefix="/v1/auth", tags=["auth"])
ph = PasswordHasher()

# Generate dummy hash at startup so it always matches live PasswordHasher params
_DUMMY_HASH: str = ph.hash("dummy-password-do-not-use")

_SESSION_MAX_AGE = settings.session_absolute_days * 86400


def _set_session_cookie(response: Response, signed_sid: str) -> None:
    response.set_cookie(
        "sid", signed_sid, httponly=True, secure=True, samesite="lax", max_age=_SESSION_MAX_AGE
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie("sid", httponly=True, secure=True, samesite="lax")


@router.post("/signup", status_code=201, response_model=UserResponse)
async def signup(
    body: SignupRequest, request: Request, response: Response, db: DBDep,
    background_tasks: BackgroundTasks,
) -> UserResponse:
    rl = RateLimiter()
    client_ip = request.client.host if request.client else "unknown"
    email_domain = body.email.split("@")[1]
    await rl.check_signup(client_ip, email_domain)

    search_hash = email_search_hash(body.email)
    existing = await db.execute(select(User).where(User.email_search_hash == search_hash))
    if existing.scalar_one_or_none():
        # Uniform 201 — no enumeration oracle. Notify the address owner out-of-band.
        background_tasks.add_task(send_already_registered_email, body.email)
        return UserResponse(
            id=uuid.uuid4(), email=body.email, email_verified=False, has_workspace=False
        )

    if await is_password_pwned(body.password):
        raise ValidationError("This password has appeared in a known data breach. Please choose a different one.")

    now = datetime.now(timezone.utc)
    password_hash = await asyncio.to_thread(ph.hash, body.password)
    user = User(
        id=uuid.uuid4(),
        email_ciphertext=encrypt_email(body.email),
        email_search_hash=search_hash,
        password_hash=password_hash,
        session_version=1,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()

    raw_token, token_hash = generate_token()
    evt = EmailVerificationToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(hours=settings.email_verification_expiry_hours),
        created_at=now,
        updated_at=now,
    )
    db.add(evt)

    svc = SessionService()
    signed_sid = await svc.create(user.id, user.session_version)
    _set_session_cookie(response, signed_sid)

    # Enqueue as BackgroundTask — handler returns immediately; SES round-trip does not block response
    background_tasks.add_task(send_verification_email, body.email, raw_token)

    return UserResponse(id=user.id, email=body.email, email_verified=False, has_workspace=False)


@router.post("/login", response_model=UserResponse)
async def login(body: LoginRequest, response: Response, db: DBDep) -> UserResponse:
    search_hash = email_search_hash(body.email)
    rl = RateLimiter()
    await rl.check_login_attempt(search_hash)

    result = await db.execute(select(User).where(User.email_search_hash == search_hash))
    user = result.scalar_one_or_none()

    try:
        await asyncio.to_thread(
            ph.verify, user.password_hash if user else _DUMMY_HASH, body.password
        )
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        # Increment lockout counter unconditionally — avoids state-based enumeration (RT-BE-010):
        # if only real accounts ever reach 429, an attacker can distinguish them from fake ones.
        await rl.record_failed_login(search_hash)
        raise UnauthorizedError("Invalid email or password.") from None

    # Explicit null guard — satisfies mypy and future-proofs control-flow changes
    if user is None:
        raise UnauthorizedError("Invalid email or password.")

    await rl.clear_login_attempts(search_hash)

    now = datetime.now(timezone.utc)
    await db.execute(
        update(User).where(User.id == user.id).values(last_login_at=now, updated_at=now)
    )

    svc = SessionService()
    signed_sid = await svc.create(user.id, user.session_version)
    _set_session_cookie(response, signed_sid)

    member = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.removed_at.is_(None),
        )
    )
    has_workspace = member.scalar_one_or_none() is not None
    email = decrypt_email(user.email_ciphertext)

    return UserResponse(
        id=user.id, email=email,
        email_verified=user.email_verified_at is not None,
        has_workspace=has_workspace,
    )


@router.post("/logout", status_code=204)
async def logout(response: Response, request: Request) -> None:
    sid = request.cookies.get("sid")
    if sid:
        svc = SessionService()
        await svc.delete(sid)
    _clear_session_cookie(response)


@router.get("/me", response_model=UserResponse)
async def me(ctx: AuthDep, db: DBDep) -> UserResponse:
    result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError()

    member = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.removed_at.is_(None),
        )
    )
    has_workspace = member.scalar_one_or_none() is not None
    email = decrypt_email(user.email_ciphertext)

    return UserResponse(
        id=user.id, email=email,
        email_verified=user.email_verified_at is not None,
        has_workspace=has_workspace,
    )


@router.post("/verify-email", status_code=204)
async def verify_email(db: DBDep, token: str = Query(...)) -> None:
    """Token in query param — matched by the email link and consumed on first use only."""
    token_hash = hash_token(token)
    result = await db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
    )
    evt = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not evt or evt.consumed_at is not None:
        raise ValidationError("This link has expired. Sign in and we'll send a fresh one.")
    if now > evt.expires_at.replace(tzinfo=timezone.utc):
        raise ValidationError("This link has expired. Sign in and we'll send a fresh one.")

    evt.consumed_at = now
    evt.updated_at = now

    user_result = await db.execute(select(User).where(User.id == evt.user_id))
    user = user_result.scalar_one()
    user.email_verified_at = now
    user.updated_at = now


@router.post("/resend-verification", status_code=204)
async def resend_verification(ctx: AuthDep, db: DBDep, background_tasks: BackgroundTasks) -> None:
    rl = RateLimiter()
    await rl.check_resend_verification(str(ctx.user_id))

    result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one()
    if user.email_verified_at is not None:
        return

    now = datetime.now(timezone.utc)
    raw_token, token_hash = generate_token()
    evt = EmailVerificationToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(hours=settings.email_verification_expiry_hours),
        created_at=now,
        updated_at=now,
    )
    db.add(evt)
    email = decrypt_email(user.email_ciphertext)
    background_tasks.add_task(send_verification_email, email, raw_token)


@router.post("/forgot-password", status_code=204)
async def forgot_password(
    body: PasswordResetRequestBody, request: Request, db: DBDep, background_tasks: BackgroundTasks
) -> None:
    search_hash = email_search_hash(body.email)
    rl = RateLimiter()
    client_ip = request.client.host if request.client else "unknown"
    await rl.check_password_reset(search_hash, client_ip)

    result = await db.execute(select(User).where(User.email_search_hash == search_hash))
    user = result.scalar_one_or_none()
    if not user:
        return  # Do not reveal whether email exists

    now = datetime.now(timezone.utc)
    # Invalidate any outstanding unused tokens (only the most-recent is valid)
    existing_tokens = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.consumed_at.is_(None),
        )
    )
    for t in existing_tokens.scalars().all():
        t.consumed_at = now
        t.updated_at = now

    raw_token, token_hash = generate_token()
    prt = PasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(minutes=settings.password_reset_expiry_minutes),
        created_at=now,
        updated_at=now,
    )
    db.add(prt)
    await db.flush()

    email = decrypt_email(user.email_ciphertext)
    background_tasks.add_task(send_password_reset_email, email, raw_token)


@router.post("/reset-password", status_code=204)
async def reset_password(body: PasswordResetConfirmBody, response: Response, db: DBDep) -> None:
    token_hash = hash_token(body.token)
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    prt = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not prt or prt.consumed_at is not None:
        raise ValidationError("This reset link is no longer valid. Request a new one.")
    if now > prt.expires_at.replace(tzinfo=timezone.utc):
        raise ValidationError("This reset link is no longer valid. Request a new one.")

    if await is_password_pwned(body.new_password):
        raise ValidationError("This password has appeared in a known data breach. Please choose a different one.")

    prt.consumed_at = now
    prt.updated_at = now

    user_result = await db.execute(select(User).where(User.id == prt.user_id))
    user = user_result.scalar_one()
    user.password_hash = await asyncio.to_thread(ph.hash, body.new_password)
    user.session_version += 1
    if user.email_verified_at is None:
        user.email_verified_at = now  # Reset proves control of inbox
    user.updated_at = now

    svc = SessionService()
    signed_sid = await svc.create(user.id, user.session_version)
    _set_session_cookie(response, signed_sid)


@router.post("/change-password", status_code=204)
async def change_password(body: ChangePasswordBody, ctx: AuthDep, response: Response, db: DBDep) -> None:
    result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one()

    try:
        await asyncio.to_thread(ph.verify, user.password_hash, body.current_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        raise ValidationError("Current password is incorrect.") from None

    if await is_password_pwned(body.new_password):
        raise ValidationError("This password has appeared in a known data breach. Please choose a different one.")

    now = datetime.now(timezone.utc)
    user.password_hash = await asyncio.to_thread(ph.hash, body.new_password)
    user.session_version += 1
    user.updated_at = now

    svc = SessionService()
    signed_sid = await svc.create(user.id, user.session_version)
    _set_session_cookie(response, signed_sid)
