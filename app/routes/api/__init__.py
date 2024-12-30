from fastapi import APIRouter

from app.routes.api.api_keys import router as api_keys_router
from app.routes.api.snippets import router as snippets_router

router = APIRouter()
router.include_router(api_keys_router, prefix="/api-keys", tags=["api-keys"])
router.include_router(snippets_router, tags=["snippets"])
