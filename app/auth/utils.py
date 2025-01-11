import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.constants import ALGORITHMS
from loguru import logger
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.common.db import async_session_maker
from app.common.email import send_email_async
from app.common.exceptions import (
    BearAuthException,
    DuplicateError,
    UserNotVerifiedError,
)
from app.settings import settings

from .models import Provider, User, ValidationToken
from .schemas import UserSignUp

AUTH_COOKIE = APIKeyCookie(name=settings.COOKIE_NAME, auto_error=False)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def get_password_hash(password):
    return pwd_context.hash(password)


async def create_access_token(user_id: str | uuid.UUID, email: str, provider: str):
    user_id = str(user_id)
    to_encode = {"email": email, "provider": provider, "user_id": user_id}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHMS.HS256)
    return encoded_jwt


async def get_token_payload(session_token: str):
    try:
        payload = jwt.decode(
            session_token, settings.JWT_SECRET, algorithms=[ALGORITHMS.HS256]
        )
        email: str = payload.get("email")
        provider: str = payload.get("provider")
        user_id: str = payload.get("user_id")
        if email is None or provider is None or user_id is None:
            raise BearAuthException("Token could not be validated")
        return {"email": email, "provider": provider, "user_id": user_id}
    except JWTError:
        raise BearAuthException("Token could not be validated")


async def send_verification_email(email: str, provider_name: str = None):
    """
    Send a verification email to the user
    """
    async with async_session_maker() as session:
        query = select(ValidationToken)
        if provider_name:
            query = query.join(Provider).filter(
                ValidationToken.email == email,
                Provider.name == provider_name,
            )
        else:
            query = query.filter(
                ValidationToken.email == email, ValidationToken.provider_id.is_(None)
            )
        result = await session.execute(query)
        validation_token = result.scalar_one_or_none()

    await send_email_async(
        email_to=validation_token.email,
        subject="Verify your email",
        # TODO: use the router or request to get the url via url_for
        body=f"Click this link to verify your email: {settings.HOST}/verify?token={validation_token.token}",
    )


async def authenticate_user(
    session, email: str, provider: str, password: str = None
) -> User:
    """Authenticate a user by email and password.

    For SSO providers, use get_user from models.user instead.

    Args:
        session: The database session
        email: User's email
        provider: Provider name (e.g. "local", "github")
        password: User's password
    """
    # Since we treat "local" as a provider, we need to check for it
    query = (
        select(Provider)
        .filter(Provider.email == email, Provider.name == provider)
        .options(selectinload(Provider.user))
    )
    result = await session.execute(query)
    provider = result.scalar_one_or_none()
    if not provider:
        return False

    user = provider.user

    if provider.name == "local":
        # Ensure user exists and has password (not SSO-only)
        if not user or not user.password:
            return False

        is_password_verified = await verify_password(password, user.password)

        if not is_password_verified:
            return False

    # Check after password verification
    if not provider.is_verified:
        raise UserNotVerifiedError(
            email=email,
            provider=provider.name,
        )

    return user


async def get_user_from_session_token(session_token: str, optional: bool = False):
    """
    Get the current authenticated user.
    """
    try:
        if not session_token:
            if optional:
                return None
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        userdata = await get_token_payload(session_token)
        email = userdata.get("email")
        provider_name = userdata.get("provider")
        user_id = userdata.get("user_id")
    except BearAuthException:
        if optional:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        async with async_session_maker() as session:
            query = (
                select(Provider)
                .filter(
                    Provider.email == email,
                    Provider.user_id == user_id,
                    Provider.name == provider_name,
                )
                .options(selectinload(Provider.user))
            )
            result = await session.execute(query)
            provider = result.scalar_one_or_none()
            if not provider:
                if optional:
                    return None
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

            if not provider.is_verified:
                raise UserNotVerifiedError(
                    email=email,
                    provider=provider.name,
                )

            # Query for user to return
            # Needed becuase if provider.user is returned we get the error:
            # "DetachedInstanceError: Parent instance <User at 0x7f8b3c1b3d60> is not bound to a Session; lazy load operation of attribute 'providers' cannot proceed"
            query = (
                select(User)
                .filter(User.id == provider.user_id)
                .options(selectinload(User.providers))
            )
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            return user


async def current_user(session_token: str = Depends(AUTH_COOKIE)):
    """
    Get the current authenticated user. User is required for the page.
    """
    user = await get_user_from_session_token(session_token, optional=False)
    return user


async def optional_current_user(session_token: str = Depends(AUTH_COOKIE)):
    """
    Used when the user object is optional for a page
    """
    user = await get_user_from_session_token(session_token, optional=True)
    return user


async def add_user(
    session,
    user_input: UserSignUp,
    provider_name: str,
    display_name: str,
    is_verified: bool = False,
    existing_user: User = None,
):
    """Add a new user or connect a provider to an existing user.

    Args:
        session: The database session
        user_input: User signup data
        provider_name: Name of the provider (e.g. "github", "local")
        display_name: Display name for the user
        is_verified: Whether the user is verified on signup
        existing_user: Optional existing user to connect provider to
    """
    if provider_name != "local" and user_input.password:
        raise ValueError("A password should not be provided for SSO registers")

    if provider_name == "local" and not user_input.password:
        raise ValueError("A password is required for local registers")

    if existing_user:
        # Used when connecting a provider to a currently logged in user
        user = existing_user
    else:
        # Check if users email exists using a different provider
        does_email_exist = await check_email_exists(session, user_input.email)
        if does_email_exist:
            raise DuplicateError(
                "To add another login method, login into your existing account first"
            )
        user = User(
            email=user_input.email,
            display_name=display_name,
        )
        session.add(user)

    if user_input.password:
        user.password = await get_password_hash(user_input.password)

    # Check if this provider/email is connected to any account
    query = select(Provider).filter(
        Provider.name == provider_name, Provider.email == user_input.email
    )
    result = await session.execute(query)
    existing_provider = result.scalar_one_or_none()

    if existing_provider:
        if existing_provider.user_id == user.id:
            raise DuplicateError(
                f"Provider {provider_name} is already connected to this account"
            )
        else:
            raise DuplicateError(
                f"This {provider_name} account is already connected to a different user"
            )

    provider = Provider(
        name=provider_name,
        email=user_input.email,
        user=user,
        is_verified=is_verified,
    )
    session.add(provider)
    await session.commit()  # Needed to get a provider.id

    validation_token = None
    if is_verified is not True:
        validation_token = ValidationToken(
            user_id=user.id,
            provider_id=provider.id,
            email=user_input.email,
        )
        session.add(validation_token)

    try:
        await session.commit()
        if validation_token:
            await send_verification_email(
                email=user_input.email, provider_name=provider.name
            )

    except IntegrityError:
        logger.exception("Error adding user")
        await session.rollback()
        raise DuplicateError(f"email {user.email} is already registered")
    return user


async def check_email_exists(session, email: str) -> bool:
    """Check if an email exists in either the user or provider tables.

    Args:
        session: The database session
        email: Email address to check

    Returns:
        bool: True if email exists in either table, False otherwise
    """
    # Normalize email
    email = email.lower().strip()
    # Check both user and provider tables
    user_query = select(User).filter(User.email == email)
    user_result = await session.execute(user_query)
    user_exists = user_result.scalar_one_or_none()

    provider_query = select(Provider).filter(Provider.email == email)
    provider_result = await session.execute(provider_query)
    provider_exists = provider_result.scalar_one_or_none()

    return user_exists or provider_exists


async def get_user(session, email: str, provider: str):
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
