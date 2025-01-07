from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.constants import ALGORITHMS
from sqlalchemy import select

from app.models.common import async_session_maker
from app.models.user import User, verify_password
from app.settings import settings

COOKIE = APIKeyCookie(name=settings.COOKIE_NAME, auto_error=False)


class BearAuthException(Exception):
    pass


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def create_access_token(username: str, provider: str):
    to_encode = {"username": username, "provider": provider}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHMS.HS256)
    return encoded_jwt


async def get_token_payload(session_token: str):
    try:
        payload = jwt.decode(
            session_token, settings.JWT_SECRET, algorithms=[ALGORITHMS.HS256]
        )
        username: str = payload.get("username")
        provider: str = payload.get("provider")
        if username is None or provider is None:
            raise BearAuthException("Token could not be validated")
        return {"username": username, "provider": provider}
    except JWTError:
        raise BearAuthException("Token could not be validated")


async def authenticate_user(session, username: str, password: str, provider: str):
    query = (
        select(User).filter(User.username == username).filter(User.provider == provider)
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return False
    is_verified = await verify_password(password, user.password)
    if not is_verified:
        return False
    return user


async def get_current_user(session_token: str = Depends(COOKIE)):
    try:
        if not session_token:
            return None
        userdata = await get_token_payload(session_token)
        username = userdata.get("username")
        provider = userdata.get("provider")
    except BearAuthException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with async_session_maker() as session:
        query = (
            select(User)
            .filter(User.username == username)
            .filter(User.provider == provider)
        )
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None
        return user
