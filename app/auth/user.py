import uuid

from fastapi import Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.auth import AUTH_COOKIE, get_password_hash, get_token_payload, verify_password
from app.email import send_email_async
from app.exceptions import BearAuthException, DuplicateError
from app.models.common import async_session_maker
from app.models.user import Provider, User
from app.schemas import UserSignUp
from app.settings import settings


async def send_verification_email(email: str):
    """
    Send a verification email to the user
    """
    async with async_session_maker() as session:
        query = (
            select(Provider)
            .filter(Provider.email == email)
            .filter(Provider.name == "local")
        )
        result = await session.execute(query)
        provider = result.scalar_one_or_none()

        token = provider.verify_token

        # Send verification email
        await send_email_async(
            email_to=email,
            subject="Verify your email",
            body=f"Click this link to verify your email: {settings.HOST}/verify?token={token}",
        )


async def authenticate_user(session, email: str, password: str):
    """Authenticate a user by email and password.

    For SSO providers, use get_user from models.user instead.
    """
    # Since we treat "local" as a provider, we need to check for it
    query = (
        select(Provider)
        .filter(Provider.email == email, Provider.name == "local")
        .options(selectinload(Provider.user))
    )
    result = await session.execute(query)
    provider = result.scalar_one_or_none()
    if not provider:
        return False

    user = provider.user

    # Ensure user exists and has password (not SSO-only)
    if not user or not user.password:
        return False

    is_password_verified = await verify_password(password, user.password)

    if not is_password_verified:
        return False

    # Check after password verification
    if not provider.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not verified. Please verify your email.",
        )

    return user


# TODO: create a shared fn for these two
async def current_active_user(session_token: str = Depends(AUTH_COOKIE)):
    """
    User is required for the page
    """
    try:
        if not session_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        userdata = await get_token_payload(session_token)
        email = userdata.get("email")
    except BearAuthException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        async with async_session_maker() as session:
            query = select(User).filter(User.email == email)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

            return user


async def optional_current_user(session_token: str = Depends(AUTH_COOKIE)):
    """
    Used when the user object is optional for a page
    """
    try:
        if not session_token:
            return None
        userdata = await get_token_payload(session_token)
        email = userdata.get("email")
    except BearAuthException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with async_session_maker() as session:
        query = select(User).filter(User.email == email)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None
        return user


async def add_user(session, user_input: UserSignUp, provider_name: str):
    if provider_name != "local" and user_input.password:
        raise ValueError("A password should not be provided for SSO registers")

    if user_input.password:
        password = await get_password_hash(user_input.password)
    else:
        password = None

    # Check if user exists using a different provider_name
    query = (
        select(Provider)
        .filter(Provider.email == user_input.email)
        .options(selectinload(Provider.user))
    )
    result = await session.execute(query)
    provider = result.scalar_one_or_none()
    if provider:
        user = provider.user
    else:
        user = User(
            email=user_input.email,
            password=password,
            display_name=user_input.display_name,
        )
        session.add(user)

    provider = Provider(
        name=provider_name,
        email=user.email,
        user=user,
        is_verified=user_input.is_verified,
    )
    if provider.name == "local":
        # Only local providers need to be verified
        # TODO: should this token be more complex?
        provider.verify_token = str(uuid.uuid4())

    session.add(provider)

    try:
        await session.commit()
        if provider.verify_token:
            await send_verification_email(user.email)
    except IntegrityError:
        logger.exception("Error adding user {e}")
        await session.rollback()
        raise DuplicateError(f"email {user.email} is already registered")
    return user


async def get_user(session, email: str, provider: str):
    # Join load the user relationship to avoid lazy loading issues
    query = (
        select(Provider)
        .filter(Provider.email == email, Provider.name == provider)
        .options(selectinload(Provider.user))
    )
    result = await session.execute(query)
    provider = result.scalar_one_or_none()
    if provider:
        return provider.user
    return None
