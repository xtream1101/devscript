from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi_pagination.default import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.auth.middleware import current_active_user
from app.models.common import async_session_maker
from app.models.snippet import Snippet
from app.models.tag import Tag
from app.models.user import User

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", name="dashboard")
async def dashboard(
    request: Request,
    user: User = Depends(current_active_user),
    page: int = 1,
    size: int = 20,
    q: str | None = None,
    tags: Annotated[list[str] | None, Query(alias="tag")] = None,
    languages: Annotated[list[str] | None, Query(alias="language")] = None,
    public: Annotated[bool | None, Query(alias="public")] = None,
):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .options(selectinload(Snippet.tags))
            .where(Snippet.user_id == user.id)
        )

        if q:
            query = query.where(
                or_(
                    Snippet.title.ilike(f"%{q}%"),
                    Snippet.description.ilike(f"%{q}%"),
                    Snippet.content.ilike(f"%{q}%"),
                    Snippet.command_name.ilike(f"%{q}%"),
                )
            )

        if languages:
            query = query.where(Snippet.language.in_(languages))

        if tags:
            conditions = [Tag.id.ilike(f"%{tag}%") for tag in tags]
            query = query.where(Snippet.tags.any(or_(*conditions)))

        if public is not None:
            query = query.where(Snippet.public == public)

        query = query.order_by(Snippet.created_at.desc())

        page_data = await paginate(session, query, params=Params(page=page, size=size))

    has_next = page_data.page < page_data.pages
    has_prev = page_data.page > 1

    set_query_params = {
        k: v for k, v in request.query_params.items() if k != "page" and k != "size"
    }
    prev_page_url = (
        request.url_for("dashboard").include_query_params(
            page=page - 1,
            size=size,
            **set_query_params,
        )
        if has_prev
        else None
    )
    next_page_url = (
        request.url_for("dashboard").include_query_params(
            page=page + 1,
            size=size,
            **set_query_params,
        )
        if has_next
        else None
    )

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "user": user,
            "snippets": page_data.items,
            "search_context": {
                "q": q,
                "tags": tags,
                "languages": languages,
                "public": public,
            },
            "page_context": {
                "num_pages": page_data.pages,
                "num_snippets": page_data.total,
                "size": page_data.size,
                "page": page_data.page,
                "has_next": has_next,
                "has_prev": has_prev,
                "next_page_url": next_page_url,
                "prev_page_url": prev_page_url,
            },
        },
    )
