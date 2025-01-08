from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.auth.user import optional_current_user
from app.models.user import User
from app.routes import router
from app.templates import templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(router)


@app.middleware("http")
async def catch_unauthorized(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 401:
        response = RedirectResponse(url="/login", status_code=303)
    return response


@app.exception_handler(404)
async def custom_404_handler(
    request, user: User | None = Depends(optional_current_user)
):
    return templates.TemplateResponse(
        request, "404.html", {"user": user}, status_code=404
    )
