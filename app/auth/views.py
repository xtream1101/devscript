from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.common.db import async_session_maker
from app.common.exceptions import DuplicateError, FailedLoginError
from app.common.templates import templates
from app.settings import settings

from .models import Provider, ValidationToken
from .models import User as UserModel
from .schemas import User, UserSignUp
from .utils import (
    add_user,
    authenticate_user,
    create_access_token,
    current_user,
    get_password_hash,
    optional_current_user,
    send_verification_email,
)

router = APIRouter(tags=["Auth"])


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
        return RedirectResponse(
            url=str(request.url_for("auth.profile"))
            + "?error=Display name cannot be empty",
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
            return RedirectResponse(
                url=str(request.url_for("auth.profile"))
                + "?error=Failed to update display name",
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
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        "auth/templates/change_email.html",
        {"request": request, "user": user, "error": error},
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
        return RedirectResponse(
            url=str(request.url_for("auth.change_email"))
            + "?error=New email must be different from current email",
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
            return RedirectResponse(
                url=str(request.url_for("auth.change_email"))
                + "?error=Email is already in use",
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
                return RedirectResponse(
                    url=str(request.url_for("auth.change_email"))
                    + "?error=Must verify the pending provider request",
                    status_code=status.HTTP_302_FOUND,
                )
        else:
            # Check if user has another pending email validation request
            delete_old_requests = delete(ValidationToken).where(
                ValidationToken.user_id == user.id,
                ValidationToken.provider_id.is_(None),
            )
            await session.execute(delete_old_requests)

            # Add a new validation request and send an email
            validation_token = ValidationToken(
                user_id=user.id,
                email=new_email,
            )
            session.add(validation_token)

            await session.commit()
            await send_verification_email(email=new_email)
            return RedirectResponse(
                url=request.url_for("auth.profile"),
                status_code=status.HTTP_302_FOUND,
            )


@router.get("/profile", name="auth.profile", summary="View user profile")
async def profile_view(request: Request, user: User = Depends(current_user)):
    """
    Display the user's profile page with connected providers.
    """
    error = request.query_params.get("error")
    async with async_session_maker() as session:
        query = select(ValidationToken).filter(
            ValidationToken.user_id == user.id, ValidationToken.provider_id.is_(None)
        )
        result = await session.execute(query)
        pending_email = result.scalar_one_or_none()
    return templates.TemplateResponse(
        "auth/templates/profile.html",
        {
            "request": request,
            "user": user,
            "error": error,
            "pending_email": pending_email.email if pending_email else None,
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
        query = select(ValidationToken).filter(ValidationToken.token == token)
        result = await session.execute(query)
        validation_token = result.scalar_one_or_none()
        if not validation_token:
            # Do not raise any alerms, just ignore it
            return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

        if validation_token.expires_at < datetime.now(timezone.utc):
            # TODO: Add a way to resend the verification email
            # TODO: Have this redirect to a more useful page, maybe by custom exception or just render a template here?
            raise HTTPException(status_code=400, detail="Token has expired")

        if validation_token.provider_id is not None:
            # Validating a provider email
            provider_query = select(Provider).filter(
                Provider.id == validation_token.provider_id
            )
            result = await session.execute(provider_query)
            provider = result.scalar_one_or_none()
            provider.is_verified = True
        else:
            # Validating a user email
            user_query = select(UserModel).filter(
                UserModel.id == validation_token.user_id
            )
            result = await session.execute(user_query)
            user = result.scalar_one_or_none()
            user.email = validation_token.email

            # Check if there is a lcoal provider that needs to get updated as well
            local_provider_query = select(Provider).filter(
                Provider.user_id == user.id, Provider.name == "local"
            )
            result = await session.execute(local_provider_query)
            local_provider = result.scalar_one_or_none()
            if local_provider:
                local_provider.email = validation_token.email

        # Cleanup the validation token
        await session.delete(validation_token)

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
    await send_verification_email(email=email, provider_name=provider_name)

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
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        "auth/templates/connect_local.html",
        {"request": request, "user": user, "error": error},
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
            return RedirectResponse(
                url=str(request.url_for("auth.connect_local")) + f"?error={str(e)}",
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
async def register(user_signup: UserSignUp):
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
            raise HTTPException(status_code=403, detail=f"{e}")

        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"{e}")

        except Exception:
            logger.exception("Error creating user")
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
        request, "auth/templates/login.html", {"error": error}
    )


@router.post("/login", name="auth.login.post", summary="Login as a user")
async def login(
    response: RedirectResponse, email: str = Form(...), password: str = Form(...)
):
    """
    Logs in a user.
    """
    async with async_session_maker() as session:
        user = await authenticate_user(
            session, email=email, password=password, provider="local"
        )
        if not user:
            raise FailedLoginError(detail="Invalid email or password.")
        try:
            access_token = await create_access_token(
                user_id=user.id, email=user.email, provider="local"
            )
            response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            response.set_cookie(settings.COOKIE_NAME, access_token)
            return response

        except Exception:
            logger.exception("Error logging user in")
            raise FailedLoginError(detail="An unexpected error occurred.")


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
