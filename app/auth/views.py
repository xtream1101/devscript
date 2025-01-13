from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jwt.exceptions import InvalidTokenError
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.common.db import async_session_maker
from app.common.exceptions import DuplicateError, FailedLoginError, GenericException
from app.common.templates import templates
from app.common.utils import flash
from app.settings import settings

from .models import Provider
from .models import User as UserModel
from .providers.views import providers as list_of_sso_providers
from .schemas import TokenData, User, UserSignUp
from .utils import (
    add_user,
    authenticate_user,
    create_token,
    current_user,
    get_password_hash,
    get_token_payload,
    optional_current_user,
    send_password_reset_email,
    send_verification_email,
)

router = APIRouter(tags=["Auth"], include_in_schema=False)


@router.post(
    "/profile/display-name",
    name="auth.update_display_name",
    summary="Update display name",
)
async def update_display_name(
    request: Request,
    display_name: str = Form(...),
    user: User = Depends(current_user),
):
    """
    Update the user's display name.
    """
    if not display_name.strip():
        flash(request, "Display name cannot be empty", "error")
        return RedirectResponse(
            url=request.url_for("auth.profile"),
            status_code=status.HTTP_302_FOUND,
        )

    async with async_session_maker() as session:
        query = select(UserModel).filter(UserModel.id == user.id)
        result = await session.execute(query)
        db_user = result.scalar_one_or_none()

        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        db_user.display_name = display_name.strip()
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Error updating display name")
            flash(request, "Failed to update display name", "error")
            return RedirectResponse(
                url=request.url_for("auth.profile"),
                status_code=status.HTTP_302_FOUND,
            )

        return RedirectResponse(
            url=request.url_for("auth.profile"),
            status_code=status.HTTP_302_FOUND,
        )


@router.get("/change-email", name="auth.change_email", summary="Change email form")
async def change_email_view(request: Request, user: User = Depends(current_user)):
    """
    Display the change email form.
    """
    return templates.TemplateResponse(
        "auth/templates/change_email.html",
        {"request": request, "user": user},
    )


@router.post(
    "/change-email", name="auth.change_email.post", summary="Process email change"
)
async def change_email(
    request: Request,
    new_email: str = Form(...),
    user: User = Depends(current_user),
):
    """
    Initiate email change process. Sends verification email to new address.
    """
    new_email = new_email.strip().lower()
    if new_email == user.email:
        flash(request, "New email must be different from current email", "error")
        return RedirectResponse(
            url=request.url_for("auth.change_email"),
            status_code=status.HTTP_302_FOUND,
        )

    async with async_session_maker() as session:
        # Check if email is used by any other users in the user or providers table
        user_query = select(UserModel).filter(
            UserModel.email == new_email, UserModel.id != user.id
        )
        user_result = await session.execute(user_query)
        provider_query = select(Provider).filter(
            Provider.email == new_email, UserModel.id != user.id
        )
        provider_result = await session.execute(provider_query)

        if user_result.first() or provider_result.first():
            flash(request, "Email is already in use", "error")
            return RedirectResponse(
                url=request.url_for("auth.change_email"),
                status_code=status.HTTP_302_FOUND,
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
                user_query = select(UserModel).filter(UserModel.id == user.id)
                user_result = await session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                db_user.email = new_email
                await session.commit()
                return RedirectResponse(
                    url=request.url_for("auth.profile"),
                    status_code=status.HTTP_302_FOUND,
                )
            else:
                flash(request, "Must verify the pending provider request", "error")
                return RedirectResponse(
                    url=request.url_for("auth.change_email"),
                    status_code=status.HTTP_302_FOUND,
                )
        else:
            validation_token = await create_token(
                TokenData(
                    user_id=user.id,
                    email=user.email,
                    new_email=new_email,
                    token_type="validation",
                )
            )
            await send_verification_email(new_email, validation_token)
            return RedirectResponse(
                url=request.url_for("auth.profile"),
                status_code=status.HTTP_302_FOUND,
            )


@router.get("/profile", name="auth.profile", summary="View user profile")
async def profile_view(request: Request, user: User = Depends(current_user)):
    """
    Display the user's profile page with connected providers.
    """
    return templates.TemplateResponse(
        "auth/templates/profile.html",
        {
            "request": request,
            "user": user,
            "list_of_sso_providers": list_of_sso_providers,
        },
    )


@router.post(
    "/providers/{provider}/disconnect",
    name="auth.disconnect_provider",
    summary="Disconnect an authentication provider",
)
async def disconnect_provider(
    provider: str,
    request: Request,
    user: User = Depends(current_user),
):
    """
    Disconnect an authentication provider from the user's account.
    Ensures at least one provider remains connected.
    """
    if len(user.providers) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot disconnect your only authentication provider.",
        )

    async with async_session_maker() as session:
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
            raise HTTPException(status_code=404, detail="Provider not found")

        if provider_to_remove.name == "local":
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
                status_code=500,
                detail="An unexpected error occurred while disconnecting provider.",
            )

        return RedirectResponse(
            url=request.url_for("auth.profile"), status_code=status.HTTP_302_FOUND
        )


@router.get("/verify", name="auth.verify_email", summary="Verify a user's email")
async def verify_email(request: Request, token: str):
    """
    Verify a user's email.
    """
    async with async_session_maker() as session:
        try:
            token_data = await get_token_payload(token, "validation")
        except InvalidTokenError:
            flash(request, "Token has expired or is invalid", "error")
            raise GenericException("Token has expired or is invalid")

        if token_data.provider_name is not None:
            # Validating a provider email
            provider_query = select(Provider).filter(
                Provider.name == token_data.provider_name,
                Provider.email == token_data.email,
            )
            result = await session.execute(provider_query)
            provider = result.scalar_one_or_none()
            provider.is_verified = True

        elif token_data.new_email is not None:
            new_email = token_data.new_email.lower().strip()
            # Validating a user email
            user_query = select(UserModel).filter(UserModel.id == token_data.user_id)
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()
            user.email = new_email

            # Check if there is a local provider that needs to get updated as well
            local_provider_query = select(Provider).filter(
                Provider.user_id == user.id, Provider.name == "local"
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
                status_code=500,
                detail="An unexpected error occurred.",
            )

        return RedirectResponse(
            request.url_for("auth.profile"), status_code=status.HTTP_302_FOUND
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
) -> RedirectResponse:
    validation_token = await create_token(
        TokenData(
            email=email,
            provider_name=provider_name,
            token_type="validation",
        )
    )
    await send_verification_email(email, validation_token)

    # TODO: Pass message to redirect page saying the email has been sent
    if user:
        return RedirectResponse(
            request.url_for("auth.profile"), status_code=status.HTTP_302_FOUND
        )

    else:
        return RedirectResponse(
            request.url_for("auth.login"), status_code=status.HTTP_302_FOUND
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
    password: str = Form(...),
):
    """
    Connect local provider to existing account.
    """
    async with async_session_maker() as session:
        try:
            # Add local provider
            provider = Provider(
                name="local",
                email=user.email,
                user_id=user.id,
                is_verified=True,  # Already verified through existing provider
            )
            session.add(provider)

            # Set password for local auth
            query = select(UserModel).filter(UserModel.id == user.id)
            result = await session.execute(query)
            db_user = result.scalar_one_or_none()
            if not db_user:
                raise HTTPException(status_code=404, detail="User not found")

            db_user.password = await get_password_hash(password)
            await session.commit()

            return RedirectResponse(
                url=request.url_for("auth.profile"),
                status_code=status.HTTP_302_FOUND,
            )

        except Exception as e:
            await session.rollback()
            logger.exception("Error connecting local provider")
            flash(request, str(e), "error")
            return RedirectResponse(
                url=request.url_for("auth.connect_local"),
                status_code=status.HTTP_302_FOUND,
            )


@router.get("/register", name="auth.register", summary="Register a user")
async def register_view(
    request: Request, user: Optional[User] = Depends(optional_current_user)
):
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        "auth/templates/register.html", {"request": request}
    )


@router.post(
    "/register",
    name="auth.register.post",
    response_model=User,
    summary="Register a user",
)
async def register(request: Request, user_signup: UserSignUp):
    """
    Registers a user.
    """
    async with async_session_maker() as session:
        try:
            user_created = await add_user(
                session,
                user_signup,
                "local",
                user_signup.email.split("@")[0],
            )
            return user_created

        except DuplicateError as e:
            flash(request, str(e), "error")
            raise HTTPException(status_code=403, detail=f"{e}")

        except ValueError as e:
            flash(request, str(e), "error")
            raise HTTPException(status_code=400, detail=f"{e}")

        except Exception:
            logger.exception("Error creating user")
            flash(request, "An unexpected error occurred", "error")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred.",
            )


@router.get("/login", name="auth.login", summary="Login as a user")
async def login_view(
    request: Request,
    user: Optional[User] = Depends(optional_current_user),
    error: str = None,
):
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request,
        "auth/templates/login.html",
        {"error": error, "list_of_sso_providers": list_of_sso_providers.keys()},
    )


@router.post("/login", name="auth.login.post", summary="Login as a user")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    """
    Logs in a user.
    """
    async with async_session_maker() as session:
        user = await authenticate_user(
            session, email=email, password=password, provider="local"
        )
        if not user:
            flash(request, "Invalid email or password", "error")
            raise FailedLoginError(detail="Invalid email or password.")
        try:
            access_token = await create_token(
                TokenData(
                    user_id=user.id,
                    email=user.email,
                    provider_name="local",
                    token_type="access",
                ),
            )
            response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            response.set_cookie(settings.COOKIE_NAME, access_token)
            return response

        except Exception:
            logger.exception("Error logging user in")
            flash(request, "Failed to log in", "error")
            raise FailedLoginError(detail="An unexpected error occurred.")


@router.get(
    "/forgot-password", name="auth.forgot_password", summary="Forgot password form"
)
async def forgot_password_view(request: Request):
    """Display the forgot password form."""
    error = request.query_params.get("error")
    success = request.query_params.get("success")
    return templates.TemplateResponse(
        "auth/templates/forgot_password.html",
        {"request": request, "error": error, "success": success},
    )


@router.post(
    "/forgot-password",
    name="auth.forgot_password.post",
    summary="Process forgot password",
)
async def forgot_password(
    request: Request,
    email: str = Form(...),
):
    """Process forgot password request and send reset email."""
    email = email.lower().strip()
    async with async_session_maker() as session:
        # Find the local provider for this email
        query = (
            select(Provider)
            .filter(Provider.email == email, Provider.name == "local")
            .options(selectinload(Provider.user))
        )
        result = await session.execute(query)
        provider = result.scalar_one_or_none()

        if not provider or not provider.user:
            # Don't reveal if email exists
            return RedirectResponse(
                url=str(request.url_for("auth.forgot_password"))
                + "?success=If your email is registered, you will receive password reset instructions",
                status_code=status.HTTP_302_FOUND,
            )

        # Generate reset token
        reset_token = await create_token(
            TokenData(
                user_id=provider.user.id,
                email=provider.email,
                provider_name=provider.name,
                token_type="reset",
            ),
            expires_delta=timedelta(hours=1),
        )

        # Send reset email
        try:
            await send_password_reset_email(request, email, reset_token)
        except Exception:
            logger.exception("Error sending password reset email")
            flash(request, "Failed to send password reset email", "error")
            return RedirectResponse(
                url=request.url_for("auth.forgot_password"),
                status_code=status.HTTP_302_FOUND,
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
            status_code=status.HTTP_302_FOUND,
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
):
    """Process password reset request."""
    if password != confirm_password:
        flash(request, "Passwords do not match", "error")
        return RedirectResponse(
            url=request.url_for("auth.reset_password", token=token),
            status_code=status.HTTP_302_FOUND,
        )

    try:
        token_data = await get_token_payload(token, "reset")
    except InvalidTokenError:
        flash(request, "Invalid or expired reset link. Please try again.", "error")
        return RedirectResponse(
            url=request.url_for("auth.forgot_password"),
            status_code=status.HTTP_302_FOUND,
        )

    async with async_session_maker() as session:
        # Update the user's password
        query = select(UserModel).filter(UserModel.id == token_data.user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            flash(request, "Invalid reset link. Please try again.", "error")
            return RedirectResponse(
                url=request.url_for("auth.forgot_password"),
                status_code=status.HTTP_302_FOUND,
            )

        user.password = await get_password_hash(password)
        try:
            await session.commit()
        except Exception:
            logger.exception("Error resetting password")
            flash(request, "Failed to reset password", "error")
            return RedirectResponse(
                url=request.url_for("auth.reset_password", token=token),
                status_code=status.HTTP_302_FOUND,
            )

        flash(request, "Password has been reset successfully", "success")
        return RedirectResponse(
            url=request.url_for("auth.login"),
            status_code=status.HTTP_302_FOUND,
        )


@router.get("/logout", name="auth.logout", summary="Logout a user")
@router.post("/logout", name="auth.logout.post", summary="Logout a user")
async def logout():
    """
    Logout a user.
    """
    try:
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.delete_cookie(settings.COOKIE_NAME)
        return response
    except Exception:
        logger.exception("Error logging user out")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred.",
        )


@router.post("/delete", name="auth.delete_account", summary="Delete user account")
async def delete_account(request: Request, user: User = Depends(current_user)):
    """
    Permanently delete a user's account and all associated data.
    """
    try:
        async with async_session_maker() as session:
            # Delete the user (which will cascade delete providers, snippets, and api_keys)
            user_query = select(UserModel).filter(UserModel.id == user.id)
            result = await session.execute(user_query)
            user_to_delete = result.scalar_one_or_none()

            if not user_to_delete:
                raise HTTPException(status_code=404, detail="User not found")

            await session.delete(user_to_delete)
            await session.commit()

            # Clear session cookie and redirect to home
            response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            response.delete_cookie(settings.COOKIE_NAME)
            return response

    except Exception:
        logger.exception("Error deleting account")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred.",
        )
