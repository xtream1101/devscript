from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.middleware.sessions import SessionMiddleware

from app.auth import router as auth_router
from app.auth.models import User
from app.auth.utils import optional_current_user
from app.common.exceptions import UserNotVerifiedError
from app.common.templates import templates
from app.common.utils import flash
from app.logger import init_logging
from app.settings import settings
from app.snippets import router as snippets_router

app = FastAPI(
    title="devscript",
    summary="A code snippet manager",
    docs_url=None,
    redoc_url=None,
)

init_logging()  # Must be called directly after app creation and before everything else

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(snippets_router)


@app.get("/", name="index", include_in_schema=False)
async def index(request: Request, user: User | None = Depends(optional_current_user)):
    if user:
        return RedirectResponse(request.url_for("snippets.index"))

    return templates.TemplateResponse(request, "common/templates/index.html")


@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def custom_404_handler(request, exc):
    return templates.TemplateResponse(
        request, "common/templates/404.html", status_code=status.HTTP_404_NOT_FOUND
    )


@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def catch_unauthorized(request, exc):
    return RedirectResponse(
        request.url_for("auth.login"), status_code=status.HTTP_303_SEE_OTHER
    )


@app.exception_handler(UserNotVerifiedError)
async def custom_exception_handler(request, exc):
    flash(request, str(exc), "error")
    return RedirectResponse(
        url=request.url_for("auth.resend_verification").include_query_params(
            email=exc.email, provider=exc.provider
        ),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Request validation error",
    )


@app.middleware("http")
async def exception_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("An uncaught error occurred")
        flash(request, "An error occurred", "error")
        return templates.TemplateResponse(
            request, "common/templates/404.html", status_code=status.HTTP_404_NOT_FOUND
        )


# Add session middleware for flash messages (PUT ON LAST LINE!!!!)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
