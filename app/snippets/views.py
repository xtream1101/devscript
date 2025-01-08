import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi_pagination.default import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from app.auth.models import User
from app.auth.utils import current_active_user, optional_current_user
from app.common.db import async_session_maker
from app.constants import SUPPORTED_LANGUAGES
from app.templates import templates

from .models import Snippet, Tag
from .schemas import SnippetView

router = APIRouter()


@router.get("/", name="dashboard")
async def index(
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

        items_query = items_query.order_by(Snippet.updated_at.desc())

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

    selected_snippet = selected_snippet.to_view() if selected_snippet else None
    snippet_list = [snippet.to_card_view() for snippet in page_data.items]

    start_index = (page_data.page * page_data.size) - (page_data.size - 1)
    end_index = start_index + len(snippet_list) - 1

    return templates.TemplateResponse(
        request,
        "snippets/templates/index.html",
        {
            "user": user,
            "selected_snippet": selected_snippet,
            "snippets": snippet_list,
            "search_context": {
                "q": q,
                "tags": tags,
                "languages": languages,
                "public": public,
            },
            "pagination_context": {
                "total_pages": page_data.pages,
                "total_items": page_data.total,
                "size": page_data.size,
                "page": page_data.page,
                "start_index": start_index,
                "end_index": end_index,
                "has_next": has_next,
                "has_prev": has_prev,
                "next_page_url": next_page_url,
                "prev_page_url": prev_page_url,
            },
        },
    )


@router.get("/add")
async def add_snippet(request: Request, user: User = Depends(current_active_user)):
    return templates.TemplateResponse(
        request,
        "snippets/add.html",
        {
            "user": user,
            "snippet": SnippetView(
                language=SUPPORTED_LANGUAGES.PLAINTEXT.name,
            ),
        },
    )


@router.post("/add")
@router.post("/{snippet_id}/fork")
async def add_snippet_submit(
    request: Request,
    user: User = Depends(current_active_user),
    title: str = Form(...),
    content: str = Form(...),
    language: str = Form(...),
    subtitle: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    command_name: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    public: bool = Form(False),
    forked_from_id: Optional[str] = Form(None),
):
    async with async_session_maker() as session:
        try:
            # Process tags
            tag_list = []
            if tags:
                tag_list = await Tag.bulk_add_tags(session, tags.split(","))

            snippet = Snippet(
                title=title,
                content=content,
                language=language,
                subtitle=subtitle,
                description=description,
                command_name=command_name,
                tags=tag_list,
                public=public,
                user_id=user.id,
                forked_from_id=forked_from_id if forked_from_id else None,
            )
            session.add(snippet)
            await session.commit()
        except Exception as e:
            # Convert tags back into a list
            tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
            return templates.TemplateResponse(
                request,
                "snippets/templates/add.html",
                {
                    "user": user,
                    "snippet": SnippetView(
                        title=title,
                        subtitle=subtitle,
                        content=content,
                        language=language,
                        description=description,
                        command_name=command_name,
                        public=public,
                        tags=tag_list,
                        forked_from_id=str(forked_from_id) if forked_from_id else None,
                    ),
                    "error": str(e),
                },
                status_code=400,
            )

    return RedirectResponse(
        url=router.url_path_for("view_snippet", snippet_id=snippet.id), status_code=303
    )


@router.get("/{snippet_id}")
async def view_snippet(
    request: Request,
    snippet_id: uuid.UUID,
    user: Optional[User] = Depends(optional_current_user),
):
    async with async_session_maker() as session:
        is_public = and_(Snippet.id == snippet_id, Snippet.public)
        is_owned = (
            and_(Snippet.id == snippet_id, Snippet.user_id == user.id)
            if user
            else False
        )

        query = (
            select(Snippet)
            .where(is_public | is_owned)
            .options(selectinload(Snippet.tags))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        return templates.TemplateResponse(
            request,
            "snippets/templates/snippet.html",
            {
                "user": user,
                "snippet": snippet.to_view(),
            },
        )


@router.get("/{snippet_id}/edit")
async def edit_snippet(
    request: Request, snippet_id: uuid.UUID, user: User = Depends(current_active_user)
):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.id == snippet_id, Snippet.user_id == user.id)
            .options(selectinload(Snippet.tags))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request,
        "snippets/templates/edit.html",
        {
            "user": user,
            "snippet": snippet.to_view(),
        },
    )


@router.post("/{snippet_id}/edit")
async def edit_snippet_submit(
    request: Request,
    snippet_id: uuid.UUID,
    user: User = Depends(current_active_user),
    title: str = Form(...),
    subtitle: Optional[str] = Form(None),
    content: str = Form(...),
    language: str = Form(...),
    description: Optional[str] = Form(None),
    command_name: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    public: bool = Form(False),
):
    # Create an input snippet dict to pass to the template that can be resused in other functions

    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.id == snippet_id, Snippet.user_id == user.id)
            .options(selectinload(Snippet.tags))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        try:
            if tags:
                snippet.tags = await Tag.bulk_add_tags(session, tags.split(","))

            snippet.title = title
            snippet.subtitle = subtitle
            snippet.content = content
            snippet.language = language
            snippet.description = description
            snippet.command_name = command_name
            snippet.public = public

            await session.commit()
        except Exception as e:
            # Convert tags back into a list
            tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
            return templates.TemplateResponse(
                request,
                "snippets/templates/edit.html",
                {
                    "user": user,
                    "snippet": SnippetView(
                        title=title,
                        subtitle=subtitle,
                        content=content,
                        language=language,
                        description=description,
                        command_name=command_name,
                        public=public,
                        tags=tag_list,
                    ),
                    "error": str(e),
                },
                status_code=400,
            )

    return RedirectResponse(
        url=router.url_path_for("view_snippet", snippet_id=snippet_id), status_code=303
    )


@router.get("/{snippet_id}/fork")
async def fork_snippet(
    request: Request,
    snippet_id: uuid.UUID,
    user: User = Depends(current_active_user),
):
    """Fork a public snippet."""
    async with async_session_maker() as session:
        # Get the original snippet

        is_public = and_(Snippet.id == snippet_id, Snippet.public)
        is_owned = (
            and_(Snippet.id == snippet_id, Snippet.user_id == user.id)
            if user
            else False
        )

        query = (
            select(Snippet)
            .where(is_public | is_owned)
            .options(selectinload(Snippet.tags))
        )
        result = await session.execute(query)
        original_snippet = result.scalar_one_or_none()

        if not original_snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        forked_title = f"Copy of {original_snippet.title}"
        forked_title = forked_title[: Snippet.title.property.columns[0].type.length]

        forked_snippet_view = SnippetView(
            title=forked_title,
            subtitle=original_snippet.subtitle,
            content=original_snippet.content,
            language=original_snippet.language,
            description=original_snippet.description,
            command_name=None,  # Set command_name to null for forked snippets
            public=False,  # Default to private for forked snippets
            user_id=str(user.id),
            forked_from_id=str(original_snippet.id),
        )

        return templates.TemplateResponse(
            request,
            "snippets/templates/fork.html",
            {
                "user": user,
                "snippet": forked_snippet_view,
            },
        )


@router.post("/{snippet_id}/delete")
async def delete_snippet(
    request: Request,
    snippet_id: uuid.UUID,
    user: User = Depends(current_active_user),
):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.id == snippet_id, Snippet.user_id == user.id)
            .options(selectinload(Snippet.tags))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        await session.delete(snippet)
        await session.commit()

    return RedirectResponse(url="/", status_code=303)
