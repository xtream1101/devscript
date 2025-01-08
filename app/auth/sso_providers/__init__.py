from fastapi import APIRouter

from .github_sso import router as github_sso_router

router = APIRouter()
router.include_router(github_sso_router)
