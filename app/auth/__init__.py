from fastapi import APIRouter

# from .apis import router as api_router
from .sso_providers import router as sso_providers_router
from .views import router as view_router

router = APIRouter()
router.include_router(view_router, prefix="/auth", tags=["web", "auth"])
# router.include_router(api_router, prefix="/api/auth", tags=["api", "auth"])
router.include_router(
    sso_providers_router, prefix="/auth", tags=["auth", "sso-providers"]
)
