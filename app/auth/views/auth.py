from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jwt.exceptions import InvalidTokenError
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.db import get_async_session
from app.common.exceptions import (
    AuthBannedError,
    AuthDuplicateError,
    FailedRegistrationError,
    UserNotVerifiedError,
    ValidationError,
)
from app.common.templates import templates
from app.common.utils import flash
from app.email.send import send_password_reset_email, send_verification_email
from app.settings import settings

from ...auth.providers.views import providers as list_of_sso_providers
from ..constants import LOCAL_PROVIDER
from ..models import Invitation, Provider, User
from ..serializers import TokenDataSerializer, UserSerializer, UserSignUpSerializer
from ..utils import (
    add_user,
    authenticate_user,
    create_token,
    get_token_payload,
    optional_current_user,
    verify_and_get_password_hash,
)

router = APIRouter(tags=["Auth"])


@router.get("/logout", name="auth.logout", summary="Logout a user")
@router.post("/logout", name="auth.logout.post", summary="Logout a user")
async def logout(request: Request):
    """
    Logout a user.
    """
    try:
        response = RedirectResponse(
            url=request.url_for("index"), status_code=status.HTTP_303_SEE_OTHER
        )
        response.delete_cookie(settings.COOKIE_NAME)
        return response
    except Exception:
        logger.exception("Error logging user out")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


@router.get("/login", name="auth.login", summary="Login as a user")
async def login_view(
    request: Request,
    user: Optional[User] = Depends(optional_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if user:
        return RedirectResponse(
            url=request.url_for("index"), status_code=status.HTTP_303_SEE_OTHER
        )

    # Check if there are any users
    user_count = await session.execute(select(func.count(User.id)))
    user_count = user_count.scalar()
    if user_count == 0:
        # Redirect to register if no users exist
        flash(request, "Please register the first user account", "info")
        return RedirectResponse(
            url=request.url_for("auth.register"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request,
        "auth/templates/login.html",
        {"list_of_sso_providers": list_of_sso_providers},
    )


@router.post("/login", name="auth.login.post", summary="Login as a user")
async def local_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Logs in a user using the local provider
    """
    try:
        user = await authenticate_user(
            session, email=email, password=password, provider=LOCAL_PROVIDER
        )
        if not user:
            flash(request, "Invalid email or password", "error")
            return RedirectResponse(
                url=request.url_for("auth.login"),
                status_code=status.HTTP_303_SEE_OTHER,
            )

        access_token = await create_token(
            TokenDataSerializer(
                user_id=user.id,
                email=user.email,
                provider_name=LOCAL_PROVIDER,
                token_type="access",
            ),
        )
        response = RedirectResponse(
            url=request.url_for("index"), status_code=status.HTTP_303_SEE_OTHER
        )
        response.set_cookie(settings.COOKIE_NAME, access_token)
        return response

    except UserNotVerifiedError:
        # Is caught and handled in the global app exception handler
        raise

    except ValidationError as e:
        flash(request, str(e), "error")
        return RedirectResponse(
            url=request.url_for("auth.login"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except AuthBannedError:
        # Let the global app exception handler handle this
        raise

    except Exception:
        logger.exception("Error logging user in")
        flash(request, "Failed to log in", "error")
        return RedirectResponse(
            url=request.url_for("auth.login"),
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.get(
    "/forgot-password", name="auth.forgot_password", summary="Forgot password form"
)
async def forgot_password_view(
    request: Request, user: Optional[User] = Depends(optional_current_user)
):
    """Display the forgot password form."""
    if user:
        return RedirectResponse(
            url=request.url_for("index"), status_code=status.HTTP_303_SEE_OTHER
        )

    return templates.TemplateResponse(
        request,
        "auth/templates/forgot_password.html",
    )


@router.post(
    "/forgot-password",
    name="auth.forgot_password.post",
    summary="Process forgot password",
)
async def forgot_password(
    request: Request,
    email: str = Form(...),
    user: Optional[User] = Depends(optional_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Process forgot password request and send reset email."""
    if user:
        return RedirectResponse(
            url=request.url_for("index"), status_code=status.HTTP_303_SEE_OTHER
        )

    email = email.lower().strip()
    # Find the local provider for this email
    query = (
        select(Provider)
        .filter(Provider.email == email, Provider.name == LOCAL_PROVIDER)
        .options(selectinload(Provider.user))
    )
    result = await session.execute(query)
    provider = result.scalar_one_or_none()

    if not provider or not provider.user:
        # Don't reveal if email exists
        flash(
            request,
            "If your email is registered, you will receive password reset instructions",
            "success",
        )
        return RedirectResponse(
            url=request.url_for("auth.forgot_password"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Generate reset token
    reset_token = await create_token(
        TokenDataSerializer(
            user_id=provider.user.id,
            email=provider.email,
            provider_name=provider.name,
            token_type="reset",
        ),
        expires_delta=timedelta(seconds=settings.PASSWORD_RESET_LINK_EXPIRATION),
    )

    # Send reset email
    try:
        await send_password_reset_email(email, reset_token)
    except Exception:
        logger.exception("Error sending password reset email")
        flash(request, "Failed to send password reset email", "error")
        return RedirectResponse(
            url=request.url_for("auth.forgot_password"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    flash(
        request,
        "If your email is registered, you will receive password reset instructions",
        "success",
    )
    return RedirectResponse(
        url=request.url_for("auth.login"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/reset-password/{token}", name="auth.reset_password", summary="Reset password form"
)
async def reset_password_view(request: Request, token: str):
    """Display the reset password form."""
    try:
        await get_token_payload(token, "reset")
    except InvalidTokenError:
        flash(request, "Invalid or expired reset link. Please try again.", "error")
        return RedirectResponse(
            url=request.url_for("auth.forgot_password"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        "auth/templates/reset_password.html",
        {"request": request, "token": token},
    )


@router.post(
    "/reset-password/{token}",
    name="auth.reset_password.post",
    summary="Process password reset",
)
async def reset_password(
    request: Request,
    token: str,
    password: str = Form(...),
    confirm_password: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Process password reset request."""
    if password != confirm_password:
        flash(request, "Passwords do not match", "error")
        return RedirectResponse(
            url=request.url_for("auth.reset_password", token=token),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        token_data = await get_token_payload(token, "reset")
    except InvalidTokenError:
        flash(request, "Invalid or expired reset link. Please try again.", "error")
        return RedirectResponse(
            url=request.url_for("auth.forgot_password"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Update the user's password
    query = select(User).filter(User.id == token_data.user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        flash(request, "Invalid reset link. Please try again.", "error")
        return RedirectResponse(
            url=request.url_for("auth.forgot_password"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user.password = await verify_and_get_password_hash(password)
    try:
        await session.commit()
    except Exception:
        logger.exception("Error resetting password")
        flash(request, "Failed to reset password", "error")
        return RedirectResponse(
            url=request.url_for("auth.reset_password", token=token),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    flash(request, "Password has been reset successfully", "success")
    return RedirectResponse(
        url=request.url_for("auth.login"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/register", name="auth.register", summary="Register a user")
async def register_view(
    request: Request,
    token: Optional[str] = None,
    user: Optional[User] = Depends(optional_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if user:
        return RedirectResponse(
            url=request.url_for("index"), status_code=status.HTTP_303_SEE_OTHER
        )

    # Check if there are any users
    user_count = await session.execute(select(func.count(User.id)))
    user_count = user_count.scalar()

    # Check if registration is allowed
    registration_allowed = False
    invitation = None
    invited_email = None

    if user_count == 0:
        # First user is always allowed to register
        registration_allowed = True
    elif not settings.DISABLE_REGISTRATION:
        # Registration is enabled for everyone
        registration_allowed = True
    elif token:
        # Check invitation token
        query = select(Invitation).filter(
            Invitation.token == token,
            Invitation.expires_at > datetime.now(timezone.utc),
            Invitation.used_at.is_(None),
        )
        result = await session.execute(query)
        invitation = result.scalar_one_or_none()

        if invitation:
            registration_allowed = True
            invited_email = invitation.email
        else:
            flash(request, "Invalid or expired invitation link", "error")
            return RedirectResponse(
                url=request.url_for("auth.login"),
                status_code=status.HTTP_303_SEE_OTHER,
            )

    if not registration_allowed:
        flash(request, "Registration is currently disabled", "error")
        return RedirectResponse(
            url=request.url_for("auth.login"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        "auth/templates/register.html",
        {
            "request": request,
            "list_of_sso_providers": list_of_sso_providers,
            "is_first_user": user_count == 0,
            "invitation": invitation,
            "invited_email": invited_email,
        },
    )


@router.post(
    "/register",
    name="auth.register.post",
    response_model=UserSerializer,
    summary="Register a user",
)
async def local_register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    token: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Registers a user.
    """
    try:
        # Check if this is the first user
        query = select(User)
        result = await session.execute(query)
        is_first_user = result.first() is None

        # Check if registration is allowed
        registration_allowed = False
        invitation = None

        if is_first_user:
            # First user is always allowed to register
            registration_allowed = True
        elif not settings.DISABLE_REGISTRATION:
            # Registration is enabled for everyone
            registration_allowed = True
        elif token:
            # Check invitation token
            query = select(Invitation).filter(
                Invitation.token == token,
                Invitation.expires_at > datetime.now(timezone.utc),
                Invitation.used_at.is_(None),
            )
            result = await session.execute(query)
            invitation = result.scalar_one_or_none()

            if invitation and invitation.email.lower() == email.lower():
                registration_allowed = True
            else:
                flash(
                    request,
                    "Invalid invitation or email does not match invitation",
                    "error",
                )
                return RedirectResponse(
                    url=request.url_for("auth.register"),
                    status_code=status.HTTP_303_SEE_OTHER,
                )

        if not registration_allowed:
            flash(request, "Registration is currently disabled", "error")
            return RedirectResponse(
                url=request.url_for("auth.login"),
                status_code=status.HTTP_303_SEE_OTHER,
            )

        user_signup = UserSignUpSerializer(
            email=email, password=password, confirm_password=confirm_password
        )
        _ = await add_user(
            session,
            user_signup,
            LOCAL_PROVIDER,
            user_signup.email.split("@")[0],
        )

        # Mark invitation as used if present
        if invitation:
            invitation.used_at = datetime.now(timezone.utc)
            await session.commit()

        # Make first user an admin
        if is_first_user:
            flash(
                request,
                "Registration successful! You may now log into the admin account",
                "success",
            )
        else:
            flash(request, "Registration successful!", "success")
        return RedirectResponse(
            url=request.url_for("auth.login"), status_code=status.HTTP_303_SEE_OTHER
        )

    except (FailedRegistrationError, AuthDuplicateError, ValidationError) as e:
        flash(request, str(e), "error")
        return RedirectResponse(
            url=request.url_for("auth.register"), status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception:
        await session.rollback()
        logger.exception("Error creating user")
        flash(request, "An unexpected error occurred", "error")
        return RedirectResponse(
            url=request.url_for("auth.register"), status_code=status.HTTP_303_SEE_OTHER
        )


@router.get("/verify", name="auth.verify_email", summary="Verify a user's email")
async def verify_email(
    request: Request, token: str, session: AsyncSession = Depends(get_async_session)
):
    """
    Verify a user's email.
    """
    try:
        token_data = await get_token_payload(token, "validation")
    except InvalidTokenError as e:
        flash(request, str(e), "error")
        return RedirectResponse(
            request.url_for("auth.login"), status_code=status.HTTP_303_SEE_OTHER
        )

    if token_data.provider_name is not None:
        # Validating a provider email
        provider_query = select(Provider).filter(
            Provider.name == token_data.provider_name,
            Provider.email == token_data.email,
        )
        result = await session.execute(provider_query)
        provider = result.scalar_one()
        provider.is_verified = True

    elif token_data.new_email is not None:
        new_email = token_data.new_email.lower().strip()
        # Validating a user email
        user_query = select(User).filter(
            User.id == token_data.user_id, User.pending_email == new_email
        )
        result = await session.execute(user_query)
        user = result.scalar_one_or_none()
        if not user:
            flash(request, "Invalid email verification link", "error")
            return RedirectResponse(
                request.url_for("auth.account_settings"),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        user.email = new_email
        user.pending_email = None

        # Check if there is a local provider that needs to get updated as well
        local_provider_query = select(Provider).filter(
            Provider.user_id == user.id, Provider.name == LOCAL_PROVIDER
        )
        result = await session.execute(local_provider_query)
        local_provider = result.scalar_one_or_none()
        if local_provider:
            local_provider.email = new_email

    try:
        await session.commit()
    except Exception:
        logger.exception("Error verifying email")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )

    flash(request, "Email has been verified", "success")
    return RedirectResponse(
        request.url_for("auth.account_settings"), status_code=status.HTTP_303_SEE_OTHER
    )


@router.post(
    "/verify/send",
    name="auth.send_verify_email.post",
    summary="Re-send a user's verification email",
)
async def resend_verification_email(
    request: Request,
    email: str = Form(...),
    provider_name: str = Form(...),
    user: User = Depends(optional_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> RedirectResponse:
    # Always say the email has been sent, even if nothign was sent
    flash(request, "Verification email has been sent", "success")
    redirect_url = "auth.account_settings" if user else "auth.login"

    # First check if email is in our system and its already verified
    provider_query = select(Provider).filter(
        Provider.email == email,
        Provider.name == provider_name,
        Provider.is_verified,
    )
    result = await session.execute(provider_query)
    provider = result.scalar_one_or_none()

    if provider:
        return RedirectResponse(
            request.url_for(redirect_url), status_code=status.HTTP_303_SEE_OTHER
        )

    # Good to send the email verification
    validation_token = await create_token(
        TokenDataSerializer(
            email=email,
            provider_name=provider_name,
            token_type="validation",
        )
    )
    await send_verification_email(email, validation_token)
    return RedirectResponse(
        request.url_for(redirect_url), status_code=status.HTTP_303_SEE_OTHER
    )


@router.get(
    "/resend-verification",
    name="auth.resend_verification",
    summary="Resend verification email",
)
async def resend_verification_view(
    request: Request,
    provider: str,
    email: str,
    user: User = Depends(optional_current_user),
):
    """
    Display the resend verification email page.
    """
    if user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "auth/templates/resend_verification.html",
        {"request": request, "provider": provider, "email": email},
    )
