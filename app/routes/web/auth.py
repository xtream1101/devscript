from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.schemas import UserCreate, UserRead
from app.users import cookie_backend, fastapi_users

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie-based authentication routes
router.include_router(
    fastapi_users.get_auth_router(cookie_backend), prefix="/cookie", tags=["auth"]
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_reset_password_router(),
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    tags=["auth"],
)


# Web interface auth routes
@router.get("/login")
async def login(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register")
async def register(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("snippetmanagerauth")
    return response
    return response
