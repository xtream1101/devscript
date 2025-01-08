from fastapi.security import APIKeyCookie, OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.constants import ALGORITHMS
from passlib.context import CryptContext

from app.exceptions import BearAuthException
from app.settings import settings

AUTH_COOKIE = APIKeyCookie(name=settings.COOKIE_NAME, auto_error=False)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def get_password_hash(password):
    return pwd_context.hash(password)


async def create_access_token(email: str, provider: str):
    to_encode = {"email": email}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHMS.HS256)
    return encoded_jwt


async def get_token_payload(session_token: str):
    try:
        payload = jwt.decode(
            session_token, settings.JWT_SECRET, algorithms=[ALGORITHMS.HS256]
        )
        email: str = payload.get("email")
        if email is None:
            raise BearAuthException("Token could not be validated")
        return {"email": email}
    except JWTError:
        raise BearAuthException("Token could not be validated")
