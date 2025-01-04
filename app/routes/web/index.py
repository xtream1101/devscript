from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="", tags=["index"])


@router.get("/")
async def index():
    return RedirectResponse(url="/dashboard")
