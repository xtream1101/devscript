from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.models.db import create_db_and_tables
from app.routes import auth_router, snippet_router, web_router, api_key_router
from app.routes.api import router as api_router

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(snippet_router, prefix="/snippets", tags=["snippets"])
app.include_router(web_router, tags=["web"])
app.include_router(api_key_router, prefix="/api-keys", tags=["api-keys"])
app.include_router(api_router, prefix="/api", tags=["api"])


@app.middleware("http")
async def catch_unauthorized(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 401:
        response = RedirectResponse(url="/auth/login", status_code=303)
    return response


@app.on_event("startup")
async def on_startup():
    # Not needed if you setup a migration system like Alembic
    await create_db_and_tables()
