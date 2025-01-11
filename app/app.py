from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api_keys import router as api_keys_router
from app.auth import router as auth_router
from app.auth.models import User
from app.auth.utils import optional_current_user
from app.common.exceptions import (
    FailedLoginError,
    GenericException,
    UserNotVerifiedError,
)
from app.common.templates import templates
from app.snippets import router as snippets_router

app = FastAPI(
    title="Snippets",
    docs_url=None,
    redoc_url="/docs",
    openapi_url="/api/openapi.json",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(snippets_router)
app.include_router(api_keys_router)


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
