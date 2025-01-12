from fastapi import APIRouter

from .views import router as sso_router

router = APIRouter()
router.include_router(sso_router)
