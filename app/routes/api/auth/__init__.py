from fastapi import APIRouter

from app.routes.api.auth.github_sso import router as github_sso_router

router = APIRouter(prefix="/auth", tags=["Auth"])
router.include_router(github_sso_router)
