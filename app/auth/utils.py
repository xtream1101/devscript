import string
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from loguru import logger
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.common.db import async_session_maker
from app.common.exceptions import (
    AuthBannedError,
    AuthDuplicateError,
    FailedRegistrationError,
    UserNotVerifiedError,
    ValidationError,
)
from app.settings import settings

from .constants import LOCAL_PROVIDER
from .models import Provider, User
from .serializers import TokenDataSerializer, UserSignUpSerializer

AUTH_COOKIE = APIKeyCookie(name=settings.COOKIE_NAME, auto_error=False)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def admin_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # request = kwargs.get("request")
        user = kwargs.get("user")

        if not user or not user.is_admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return await func(*args, **kwargs)

    return wrapper


async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def verify_and_get_password_hash(password):
    if (
        len(password) < 8
        or not any(c.isupper() for c in password)
        or not any(c.islower() for c in password)
        or not any(c in string.punctuation for c in password)
        or not any(c.isdigit() for c in password)
    ):
        raise ValidationError(
            "Password must be at least 8 characters long and contain an uppercase, lowercase, number, and a special char",
        )

    return pwd_context.hash(password)


async def create_token(
    data: TokenDataSerializer, expires_delta: timedelta | None = None
):
    to_encode = data.model_dump()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    elif data.token_type == "access":
        expire = datetime.now(timezone.utc) + timedelta(seconds=settings.COOKIE_MAX_AGE)
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            seconds=settings.VALIDATION_LINK_EXPIRATION
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_token_payload(token: str, expected_type: str) -> TokenDataSerializer:
    """Get the payload of a token and validate it

    Args:
        token: The token to decode
        expected_type: The expected token type

    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    token_data = TokenDataSerializer(**payload)
    if token_data.token_type != expected_type:
        raise InvalidTokenError("Invalid token type")

    # Check if token is expired
    if token_data.exp < datetime.now(timezone.utc):
        raise InvalidTokenError("Token has expired")

    return token_data


async def authenticate_user(
    session, email: str, provider: str, password: str | None = None
) -> User | None:
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
        return None

    user = provider.user

    if provider.name == LOCAL_PROVIDER:
        # Ensure user exists and has password (not SSO-only)
        if not user or not user.password:
            return None

        is_password_verified = await verify_password(password, user.password)

        if not is_password_verified:
            return None

    # Check after password verification
    if not provider.is_verified:
        raise UserNotVerifiedError(
            email=email,
            provider=provider.name,
        )

    # Check if user is banned
    if user.is_banned:
        raise AuthBannedError

    # User is allowed to login at this point
    provider.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    return user


async def _get_user_from_session_token(session_token: str, optional: bool = False):
    """
    Get the current authenticated user.
    """
    try:
        if not session_token:
            if optional:
                return None
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        token_data = await get_token_payload(session_token, "access")
    except InvalidTokenError:
        if optional:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate access token",
        )
    else:
        async with async_session_maker() as session:
            query = (
                select(Provider)
                .filter(
                    Provider.email == token_data.email,
                    Provider.user_id == token_data.user_id,
                    Provider.name == token_data.provider_name,
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
                    email=token_data.email,
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
    user = await _get_user_from_session_token(session_token, optional=False)
    if user.is_banned:
        # This will invalidate the users current session
        raise AuthBannedError
    return user


async def optional_current_user(session_token: str = Depends(AUTH_COOKIE)):
    """
    Used when the user object is optional for a page
    """
    user = await _get_user_from_session_token(session_token, optional=True)
    if user and user.is_banned:
        # Since the user is optional, we can just return None
        return None
    return user


async def add_user(
    session,
    user_input: UserSignUpSerializer,
    provider_name: str,
    display_name: str,
    is_verified: bool = False,
    existing_user: User | None = None,
) -> User:
    """Add a new user or connect a provider to an existing user.

    Args:
        session: The database session
        user_input: User signup data
        provider_name: Name of the provider (e.g. "github", "local")
        display_name: Display name for the user
        is_verified: Whether the user is verified on signup
        existing_user: Optional existing user to connect provider to

    Returns:
        User: the user model object
    """
    if provider_name != LOCAL_PROVIDER and user_input.password:
        raise FailedRegistrationError(
            "A password should not be provided for SSO registers"
        )

    if provider_name == LOCAL_PROVIDER and not user_input.password:
        raise FailedRegistrationError("A password is required for local registers")

    if (
        provider_name == LOCAL_PROVIDER
        and user_input.password != user_input.confirm_password
    ):
        raise FailedRegistrationError("Passwords do not match")

    try:
        if existing_user:
            # Used when connecting a provider to a currently logged in user
            user = existing_user
        else:
            # Check if users email exists using a different provider
            does_email_exist = await check_email_exists(session, user_input.email)
            if does_email_exist:
                raise AuthDuplicateError(
                    "To add another login method, login into your existing account first"
                )

            # Trim the dsiplay name here, becuase the model validation will throw an error if it is too long
            if len(display_name) > User.display_name.type.length:
                display_name = display_name[: User.display_name.type.length]

            user = User(email=user_input.email, display_name=display_name)

            session.add(user)

        if user_input.password:
            user.password = await verify_and_get_password_hash(user_input.password)

        # Check if this provider/email is connected to any account
        query = select(Provider).filter(
            Provider.name == provider_name, Provider.email == user_input.email
        )
        result = await session.execute(query)
        existing_provider = result.scalar_one_or_none()

        if existing_provider:
            if existing_provider.user_id == user.id:
                raise AuthDuplicateError(
                    f"Provider {provider_name} is already connected to this account"
                )
            else:
                raise AuthDuplicateError(
                    f"This {provider_name} account is already connected to a different user"
                )

        # Check if this is the first user before creating the new one
        count = await session.execute(select(func.count(User.id)))
        count = count.scalar()

        is_first_user = count == 1  # its 1 because of this user that was created above
        # Set admin and verified status before committing if first user
        provider_is_verified = is_verified
        if is_first_user:
            user.is_admin = True
            provider_is_verified = True

        provider = Provider(
            name=provider_name,
            email=user_input.email,
            user=user,
            is_verified=provider_is_verified,
        )
        session.add(provider)

        await session.commit()
    except IntegrityError:
        logger.exception("Error adding user")
        await session.rollback()
        raise AuthDuplicateError("There was an error adding your user")

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
