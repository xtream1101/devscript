from fastapi import APIRouter

from app.routes.api import router as api_router
from app.routes.web import router as web_router

router = APIRouter()
router.include_router(web_router, prefix="", tags=["web"])
router.include_router(api_router, prefix="/api", tags=["api"])
