from fastapi import APIRouter

from .account import router as account_router
from .admin import router as admin_router
from .api_keys import router as api_keys_router
from .auth import router as auth_router
from .providers import router as providers_router

router = APIRouter(tags=["Auth"], include_in_schema=False)
router.include_router(account_router)
router.include_router(admin_router)
router.include_router(api_keys_router)
router.include_router(auth_router)
router.include_router(providers_router)
