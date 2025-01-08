from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import router

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(router)

templates = Jinja2Templates(directory="app/templates")


@app.middleware("http")
async def catch_unauthorized(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 401:
        response = RedirectResponse(url="/login", status_code=303)
    return response


@app.exception_handler(404)
async def custom_404_handler(request, __):
    return templates.TemplateResponse("404.html", {"request": request})
