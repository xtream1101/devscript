import secrets
import uuid
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jwt.exceptions import InvalidTokenError
from loguru import logger
from pydantic import validate_email
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.constants import LOCAL_PROVIDER
from app.common.constants import SUPPORTED_CODE_THEMES
from app.common.db import get_async_session
from app.common.exceptions import (
    AuthDuplicateError,
    FailedRegistrationError,
    UserNotVerifiedError,
    ValidationError,
)
from app.common.templates import templates
from app.common.utils import flash
from app.email.send import send_password_reset_email, send_verification_email
from app.settings import settings

from .models import APIKey, Provider, User
from .providers.views import providers as list_of_sso_providers
from .serializers import TokenDataSerializer, UserSerializer, UserSignUpSerializer
from .utils import (
    add_user,
    admin_required,
    authenticate_user,
    create_token,
    current_user,
    get_token_payload,
    optional_current_user,
    verify_and_get_password_hash,
)

router = APIRouter(tags=["Auth"], include_in_schema=False)


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

    return templates.TemplateResponse(
        "auth/templates/register.html",
        {
            "request": request,
            "list_of_sso_providers": list_of_sso_providers,
            "is_first_user": user_count == 0,
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

        user_signup = UserSignUpSerializer(
            email=email, password=password, confirm_password=confirm_password
        )
        user = await add_user(
            session,
            user_signup,
            LOCAL_PROVIDER,
            user_signup.email.split("@")[0],
        )

        # Make first user an admin
        if is_first_user:
            user.is_admin = True
            await session.commit()
            flash(
                request,
                "Registration successful! You may now log into the admin account",
                "success",
            )
        else:
            flash(
                request,
                "Registration successful! Please check your email to verify your account.",
                "success",
            )
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
                request.url_for("auth.profile"), status_code=status.HTTP_303_SEE_OTHER
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
        request.url_for("auth.profile"), status_code=status.HTTP_303_SEE_OTHER
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
    redirect_url = "auth.profile" if user else "auth.login"

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


@router.get("/profile", name="auth.profile", summary="View user profile")
async def profile_view(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Display the user's profile page with connected providers.
    """

    # Get all active API keys
    query = select(APIKey).where(APIKey.user_id == user.id, APIKey.is_active)
    result = await session.execute(query)
    api_keys = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "auth/templates/profile.html",
        {
            "api_keys": api_keys,
            "list_of_sso_providers": list_of_sso_providers,
            "pending_email": user.pending_email,
            "code_themes": SUPPORTED_CODE_THEMES,
        },
    )


@router.post(
    "/profile/display-name",
    name="auth.update_display_name.post",
    summary="Update display name",
)
async def update_display_name(
    request: Request,
    display_name: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Update the user's display name.
    """
    query = select(User).filter(User.id == user.id)
    result = await session.execute(query)
    db_user = result.scalar_one()

    try:
        db_user.display_name = display_name
    except ValidationError as e:
        flash(request, str(e), "error")
        return RedirectResponse(
            url=request.url_for("auth.profile"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Error updating display name")
        flash(request, "Failed to update display name", "error")
        return RedirectResponse(
            url=request.url_for("auth.profile"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url=request.url_for("auth.profile"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/change-email", name="auth.change_email", summary="Change email form")
async def change_email_view(request: Request, user: User = Depends(current_user)):
    """
    Display the change email form.
    """
    return templates.TemplateResponse(request, "auth/templates/change_email.html")


@router.get(
    "/change-email/cancel",
    name="auth.change_email_cancel",
    summary="Cancel email change",
)
async def change_email_cancel(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Cancel the email change process.
    """

    user_query = select(User).filter(User.id == user.id)
    user_result = await session.execute(user_query)
    db_user = user_result.scalar_one()
    db_user.pending_email = None
    await session.commit()

    flash(request, "Email change has been cancelled", "info")
    return RedirectResponse(
        url=request.url_for("auth.profile"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/change-email", name="auth.change_email.post", summary="Process email change"
)
async def change_email(
    request: Request,
    new_email: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Initiate email change process. Sends verification email to new address.
    """
    new_email = new_email.strip().lower()
    if new_email == user.email:
        flash(request, "No change, email is the same", "info")
        return RedirectResponse(
            url=request.url_for("auth.change_email"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Confirm its a valid email
    try:
        _, new_email = validate_email(new_email)
    except ValueError:
        flash(request, "Invalid email address", "error")
        return RedirectResponse(
            url=request.url_for("auth.change_email"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Check if email is used by any other users in the user or providers table
    user_query = select(User).filter(User.email == new_email, User.id != user.id)
    user_result = await session.execute(user_query)
    provider_query = select(Provider).filter(
        Provider.email == new_email, User.id != user.id
    )
    provider_result = await session.execute(provider_query)

    if user_result.first() or provider_result.first():
        flash(request, "Email is already in use", "error")
        return RedirectResponse(
            url=request.url_for("auth.change_email"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Check if its already a verified email the user has
    user_providers_query = select(Provider).filter(
        Provider.user_id == user.id, Provider.email == new_email
    )
    user_providers_result = await session.execute(user_providers_query)
    user_providers = user_providers_result.scalars().all()
    if user_providers:
        if all(provider.is_verified for provider in user_providers):
            # All providers with this email are already verified
            # Update the users email and return
            user_query = select(User).filter(User.id == user.id)
            user_result = await session.execute(user_query)
            db_user = user_result.scalar_one()
            db_user.email = new_email
            await session.commit()
            return RedirectResponse(
                url=request.url_for("auth.profile"),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        else:
            flash(request, "Must verify the pending provider request", "error")
            return RedirectResponse(
                url=request.url_for("auth.change_email"),
                status_code=status.HTTP_303_SEE_OTHER,
            )

    # Email is good to use, but needs to be verified
    # Update users pending email
    user_query = select(User).filter(User.id == user.id)
    user_result = await session.execute(user_query)
    db_user = user_result.scalar_one()
    db_user.pending_email = new_email
    await session.commit()

    # Create a token for the new email
    validation_token = await create_token(
        TokenDataSerializer(
            user_id=user.id,
            email=user.email,
            new_email=new_email,
            token_type="validation",
        )
    )
    await send_verification_email(
        new_email, validation_token, from_change_email=user.email
    )
    flash(
        request,
        "A verification email has been sent to the new email address",
        "success",
    )
    return RedirectResponse(
        url=request.url_for("auth.profile"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/providers/local/connect",
    name="auth.connect_local",
    summary="Connect local provider",
)
async def connect_local_view(request: Request, user: User = Depends(current_user)):
    """
    Display the connect local provider page.
    """
    return templates.TemplateResponse(
        "auth/templates/connect_local.html",
        {"request": request, "user": user},
    )


@router.post(
    "/providers/local/connect",
    name="auth.connect_local.post",
    summary="Connect local provider",
)
async def connect_local(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    """
    Connect local provider to existing account.
    """
    try:
        if password != confirm_password:
            raise ValidationError("Passwords do not match")

        # Add local provider
        provider = Provider(
            name=LOCAL_PROVIDER,
            email=user.email,
            user_id=user.id,
            is_verified=True,  # Already verified through existing provider
        )
        session.add(provider)

        # Set password for local auth
        # Need to get the user object in this session to update the password
        query = select(User).filter(User.id == user.id)
        result = await session.execute(query)
        db_user = result.scalar_one()
        db_user.password = await verify_and_get_password_hash(password)

        await session.commit()

    except Exception as e:
        if isinstance(e, ValidationError):
            flash(request, str(e), "error")
        else:
            logger.exception(f"Error connecting {LOCAL_PROVIDER} provider")
            flash(request, f"Failed to connect a {LOCAL_PROVIDER} provider", "error")

        await session.rollback()
        return RedirectResponse(
            url=request.url_for("auth.connect_local"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    flash(request, f"{LOCAL_PROVIDER.title()} provider connected", "success")
    return RedirectResponse(
        url=request.url_for("auth.profile"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/providers/{provider}/disconnect",
    name="auth.disconnect_provider.post",
    summary="Disconnect an authentication provider",
)
async def disconnect_provider(
    provider: str,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Disconnect an authentication provider from the user's account.
    Ensures at least one provider remains connected.
    """
    if len(user.providers) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disconnect your only authentication provider.",
        )

    # Find and delete the provider
    query = (
        select(Provider)
        .filter(Provider.user_id == user.id)
        .filter(Provider.name == provider)
        .options(selectinload(Provider.user))
    )
    result = await session.execute(query)
    provider_to_remove = result.scalar_one_or_none()

    if not provider_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
        )

    if provider_to_remove.name == LOCAL_PROVIDER:
        # Clear the password since its only for the local provider
        # Need to use the user object through the provider row as the passed
        # in user object is in a different session
        provider_to_remove.user.password = None

    await session.delete(provider_to_remove)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Error disconnecting provider")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while disconnecting provider.",
        )

    return RedirectResponse(
        url=request.url_for("auth.profile"), status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/api-keys", name="api_key.create.post")
async def create_api_key(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
    name: str = Form(...),
):
    """Create a new API key."""
    try:
        # Generate a random API key
        api_key = secrets.token_urlsafe(32)

        # Create new API key record
        db_api_key = APIKey(key=api_key, name=name, user_id=user.id)
        session.add(db_api_key)
        await session.commit()

    except Exception as e:
        if isinstance(e, ValidationError):
            flash(request, str(e), level="error")
        else:
            flash(request, "An error occurred", level="error")
            logger.exception("Error creating api-key")
    else:
        flash(
            request,
            "API key created successfully",
            level="success",
            format="new_api_key",
            api_key=api_key,
        )

    return RedirectResponse(
        url=request.url_for("auth.profile"), status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/api-keys/{key_id}/revoke", name="api_key.revoke.post")
async def revoke_api_key(
    request: Request,
    key_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Revoke an API key."""
    # First verify the key belongs to the user
    query = select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id)
    result = await session.execute(query)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Update the key to be inactive
    api_key.is_active = False
    await session.commit()

    return RedirectResponse(
        url=request.url_for("auth.profile"), status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/update-code-theme", name="auth.update_code_theme.post")
async def update_code_theme(
    request: Request,
    theme_mode: str = Form(...),
    code_theme: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update the user's code theme."""
    query = select(User).filter(User.id == user.id)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if theme_mode not in ["light", "dark"]:
        flash(request, "Invalid theme mode", "error")
        return RedirectResponse(
            url=request.url_for("auth.profile"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if code_theme not in SUPPORTED_CODE_THEMES:
        flash(request, "Invalid code theme", "error")
        return RedirectResponse(
            url=request.url_for("auth.profile"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if theme_mode == "light":
        db_user.code_theme_light = code_theme
    else:
        db_user.code_theme_dark = code_theme

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Error updating code theme")
        flash(request, "Failed to update code theme", "error")
        return RedirectResponse(
            url=request.url_for("auth.profile"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url=request.url_for("auth.profile"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/reset_code_theme", name="auth.reset_code_theme.post")
async def reset_code_theme(
    request: Request,
    theme_mode: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Reset the user's code theme."""
    query = select(User).filter(User.id == user.id)
    result = await session.execute(query)
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if theme_mode not in ["light", "dark"]:
        flash(request, "Invalid theme mode", "error")
        return RedirectResponse(
            url=request.url_for("auth.profile"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if theme_mode == "light":
        db_user.code_theme_light = None
    else:
        db_user.code_theme_dark = None

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Error resetting code theme")
        flash(request, "Failed to reset code theme", "error")
        return RedirectResponse(
            url=request.url_for("auth.profile"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url=request.url_for("auth.profile"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/delete", name="auth.delete_account.post", summary="Delete user account")
async def delete_account(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Permanently delete a user's account and all associated data.
    """
    try:
        # Delete the user (which will cascade delete providers, snippets, and api_keys)
        user_query = select(User).filter(User.id == user.id)
        result = await session.execute(user_query)
        user_to_delete = result.scalar_one_or_none()

        if not user_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # If user is admin, check if they are the only admin
        if user_to_delete.is_admin:
            admin_count_query = select(User).filter(User.is_admin)
            admin_result = await session.execute(admin_count_query)
            admin_users = admin_result.scalars().all()
            if len(admin_users) <= 1:
                flash(request, "Cannot delete the only admin account", "error")
                return RedirectResponse(
                    url=request.url_for("auth.profile"),
                    status_code=status.HTTP_303_SEE_OTHER,
                )

        await session.delete(user_to_delete)
        await session.commit()

        # Clear session cookie and redirect to home
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(settings.COOKIE_NAME)
        return response

    except Exception:
        logger.exception("Error deleting account")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


@router.get("/admin", name="auth.admin")
@admin_required
async def admin_view(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Admin page for user management."""
    query = select(User).order_by(User.registered_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()

    return templates.TemplateResponse(
        request, "auth/templates/admin.html", {"users": users}
    )


@router.post("/admin/users/{user_id}/ban", name="auth.toggle_user_ban")
@admin_required
async def toggle_user_ban(
    request: Request,
    user_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Toggle user ban status."""
    if user.id == user_id:
        flash(request, "Cannot ban yourself", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    query = select(User).filter(User.id == user_id)
    result = await session.execute(query)
    target_user = result.scalar_one_or_none()

    if not target_user:
        flash(request, "User not found", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if target_user.is_admin:
        flash(request, "Cannot ban admin users", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    target_user.is_banned = not target_user.is_banned
    await session.commit()

    action = "banned" if target_user.is_banned else "unbanned"
    flash(request, f"User {action} successfully", "success")
    return RedirectResponse(
        url=request.url_for("auth.admin"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/admin/users/{user_id}/delete", name="auth.delete_user")
@admin_required
async def delete_user(
    request: Request,
    user_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a user."""
    if user.id == user_id:
        flash(request, "Cannot delete yourself", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    query = select(User).filter(User.id == user_id)
    result = await session.execute(query)
    target_user = result.scalar_one_or_none()

    if not target_user:
        flash(request, "User not found", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if target_user.is_admin:
        flash(request, "Cannot delete admin users", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    await session.delete(target_user)
    await session.commit()

    flash(request, "User deleted successfully", "success")
    return RedirectResponse(
        url=request.url_for("auth.admin"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
