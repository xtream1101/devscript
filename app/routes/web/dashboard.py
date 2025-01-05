import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
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
    selected_snippet_id: uuid.UUID | None = None,
    page: int = 1,
    size: int = 20,
    q: str | None = None,
    tags: Annotated[list[str] | None, Query(alias="tag")] = None,
    languages: Annotated[list[str] | None, Query(alias="language")] = None,
    public: Annotated[bool | None, Query(alias="public")] = None,
):
    #  Get a dictionary of all the search query parameters -- this will be used to build URLs
    active_query_params = {
        k: v
        for k, v in request.query_params.items()
        if k not in ["page", "size", "selected_snippet_id"]
    }

    async with async_session_maker() as session:
        items_query = (
            select(Snippet)
            .options(selectinload(Snippet.tags))
            .where(Snippet.user_id == user.id)
        )

        if q:
            items_query = items_query.where(
                or_(
                    Snippet.title.ilike(f"%{q}%"),
                    Snippet.description.ilike(f"%{q}%"),
                    Snippet.content.ilike(f"%{q}%"),
                    Snippet.command_name.ilike(f"%{q}%"),
                )
            )

        if languages:
            items_query = items_query.where(Snippet.language.in_(languages))

        if tags:
            conditions = [Tag.id.ilike(f"%{tag}%") for tag in tags]
            items_query = items_query.where(Snippet.tags.any(or_(*conditions)))

        if public is not None:
            items_query = items_query.where(Snippet.public == public)

        items_query = items_query.order_by(Snippet.created_at.desc())

        page_data = await paginate(
            session, items_query, params=Params(page=page, size=size)
        )

        # Ensure selected_snippet is valid
        selected_snippet = None
        if selected_snippet_id:
            selected_snippet_query = (
                select(Snippet)
                .where(Snippet.id == selected_snippet_id, Snippet.user_id == user.id)
                .options(selectinload(Snippet.tags))
            )
            selected_snippet_result = await session.execute(selected_snippet_query)
            selected_snippet = selected_snippet_result.scalar_one_or_none()

            if not selected_snippet or selected_snippet.id not in [
                item.id for item in page_data.items
            ]:
                return RedirectResponse(
                    request.url_for("dashboard").include_query_params(
                        page=page, size=size, **active_query_params
                    )
                )

        # If there is no selected_snippet, or the selected_snippet is invalid, select the first snippet
        if not selected_snippet:
            selected_snippet = page_data.items[0] if page_data.items else None

    has_next = page_data.page < page_data.pages
    has_prev = page_data.page > 1

    prev_page_url = (
        request.url_for("dashboard").include_query_params(
            page=page - 1,
            size=size,
            **active_query_params,
        )
        if has_prev
        else None
    )
    next_page_url = (
        request.url_for("dashboard").include_query_params(
            page=page + 1,
            size=size,
            **active_query_params,
        )
        if has_next
        else None
    )

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "user": user,
            "page": {
                "selected_snippet": selected_snippet,
                "snippets": page_data.items,
            },
            "search_context": {
                "q": q,
                "tags": tags,
                "languages": languages,
                "public": public,
            },
            "pagination_context": {
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
