from fastapi import APIRouter

from .apis import router as api_router
from .signals import *  # noqa
from .views import router as view_router

router = APIRouter()
router.include_router(view_router, prefix="/snippets", tags=["Snippets"])
router.include_router(api_router, prefix="/api/snippets", tags=["Snippets"])
