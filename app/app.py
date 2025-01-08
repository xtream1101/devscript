from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api_keys import router as api_keys_router
from app.auth import router as auth_router
from app.auth.models import User
from app.auth.utils import optional_current_user
from app.common.templates import templates
from app.snippets import router as snippets_router

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(snippets_router)
app.include_router(api_keys_router)


@app.get("/", name="index")
async def index(request: Request):
    return RedirectResponse(request.url_for("snippets.index"))


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
