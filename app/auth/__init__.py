from fastapi import APIRouter

from .apis import router as api_router
from .providers import router as providers_router
from .views import router as view_router

router = APIRouter()
# Include routers on the top level w/  no prefix
router.include_router(view_router, prefix="", tags=["Auth"])
router.include_router(providers_router, prefix="/auth", tags=["Auth/Providers"])
router.include_router(api_router, prefix="/api/auth", tags=["Auth"])
