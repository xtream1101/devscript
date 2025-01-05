from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi_pagination.default import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.middleware import current_active_user
from app.models.common import async_session_maker
from app.models.snippet import Snippet
from app.models.user import User

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", name="dashboard")
async def index(
    request: Request,
    user: User = Depends(current_active_user),
    q: str | None = None,
    tags: Annotated[list[str] | None, Query()] = None,
    page: int = 1,
    size: int = 20,
):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.user_id == user.id)
            .order_by(Snippet.created_at.desc())
            .options(selectinload(Snippet.tags))
        )
        page_data = await paginate(session, query, params=Params(page=page, size=size))
        print(vars(page_data))

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "user": user,
            "snippets": page_data.items,
            "pagination": {
                "size": page_data.size,
                "page": page_data.page,
                "has_next": page_data.page < page_data.pages,
                "has_prev": page_data.page > 1,
                "num_pages": page_data.pages,
                "num_snippets": page_data.total,
            },
        },
    )
