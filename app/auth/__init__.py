from fastapi import APIRouter

from .providers import router as providers_router
from .views import router as view_router

router = APIRouter()
# Include routers on the top level w/  no prefix
router.include_router(view_router, prefix="", tags=["web", "auth"])
router.include_router(providers_router, prefix="/auth", tags=["auth", "sso-providers"])
