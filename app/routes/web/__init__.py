from fastapi import APIRouter

from app.routes.web.api_keys import router as api_keys_router
from app.routes.web.auth import router as auth_router
from app.routes.web.dashboard import router as dashboard_router
from app.routes.web.github_sso import router as github_sso_router
from app.routes.web.index import router as index_router
from app.routes.web.snippets import router as snippets_router

router = APIRouter()
router.include_router(index_router)
router.include_router(dashboard_router)
router.include_router(snippets_router)
router.include_router(auth_router)
router.include_router(api_keys_router)
router.include_router(github_sso_router)
