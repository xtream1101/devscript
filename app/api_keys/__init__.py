from fastapi import APIRouter

from .apis import router as api_router
from .views import router as view_router

router = APIRouter()
router.include_router(view_router, prefix="/api-keys", tags=["API Keys"])
router.include_router(api_router, prefix="/api/api-keys", tags=["API Keys"])
