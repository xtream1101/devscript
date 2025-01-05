from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routes import router

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(router)


@app.middleware("http")
async def catch_unauthorized(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 401:
        response = RedirectResponse(url="/auth/login", status_code=303)
    return response
