from fastapi import APIRouter

from .github import router as github_router

router = APIRouter()
router.include_router(github_router)
