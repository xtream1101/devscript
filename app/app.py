from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.middleware.sessions import SessionMiddleware

from app.auth import router as auth_router
from app.auth.models import User
from app.auth.utils import optional_current_user
from app.common.exceptions import (
    FailedLoginError,
    GenericException,
    UserNotVerifiedError,
)
from app.common.templates import templates
from app.settings import settings
from app.snippets import router as snippets_router

app = FastAPI(
    title="devscript",
    summary="A code snippet manager",
    docs_url=None,
    redoc_url=None,
)

# Add session middleware for flash messages
app.add_middleware(
    SessionMiddleware, secret_key=settings.SECRET_KEY
)  # Use a secure key in production

origins = [
    "https://devscript.host",
    "https://docs.devscript.host",
    "https://staging.devscript.host",
    "https://docs-staging.devscript.host",
]

if settings.ENV == "dev":
    origins += [
        "http://localhost:8000",
        "http://localhost:8080",  # Docs
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files on their own app to avoid CORS issues
static_app = FastAPI(
    title="devscript",
    summary="A code snippet manager",
    docs_url=None,
    redoc_url=None,
)
static_app.mount("/", StaticFiles(directory="app/static"), name="static")
app.mount("/static", static_app)


# Include routers
app.include_router(auth_router)
app.include_router(snippets_router)


@app.get("/", name="index", include_in_schema=False)
async def index(request: Request, user: User | None = Depends(optional_current_user)):
    if user:
        return RedirectResponse(request.url_for("snippets.index"))

    return templates.TemplateResponse(request, "common/templates/index.html")


@app.get("/404", name="not_found", include_in_schema=False)
async def not_found(request: Request):
    return templates.TemplateResponse(
        request, "common/templates/404.html", status_code=404
    )


@app.middleware("http")
async def catch_unauthorized(request: Request, call_next):
    response = await call_next(request)

    if response.status_code == 401:
        response = RedirectResponse(request.url_for("auth.login"), status_code=303)

    return response


@app.exception_handler(404)
async def custom_404_handler(
    request, user: User | None = Depends(optional_current_user)
):
    return templates.TemplateResponse(
        request, "common/templates/404.html", status_code=404
    )


@app.exception_handler(UserNotVerifiedError)
async def custom_exception_handler(
    request, exc, user: User | None = Depends(optional_current_user)
):
    return templates.TemplateResponse(
        request,
        "auth/templates/verify_email.html",
        {
            "email": exc.email,
            "provider": exc.provider,
        },
    )


@app.exception_handler(FailedLoginError)
async def failed_login_exception_handler(request, exc):
    return templates.TemplateResponse(
        request,
        "auth/templates/login.html",
        {"request": request, "error": exc.detail},
    )


@app.exception_handler(Exception)
@app.exception_handler(GenericException)
async def generic_exception_handler(request, exc):
    if not isinstance(exc, GenericException):
        logger.exception("An uncaught error occurred", exec_info=exc)

    # TODO: Dont actually show the error to the user
    return templates.TemplateResponse(
        request,
        "common/templates/generic_error.html",
        {"exc": exc},
    )
