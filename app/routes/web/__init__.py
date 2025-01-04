from fastapi import APIRouter

from app.routes.web.api_key_routes import router as api_key_router
from app.routes.web.auth_routes import router as auth_router
from app.routes.web.snippet_routes import router as snippet_router
from app.routes.web.web_routes import router as web_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(snippet_router, prefix="/snippets", tags=["snippets"])
router.include_router(web_router, tags=["web"])
router.include_router(api_key_router, prefix="/api-keys", tags=["api-keys"])
