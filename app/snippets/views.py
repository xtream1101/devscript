import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_pagination.default import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from app.auth.models import User
from app.auth.utils import current_user, optional_current_user
from app.common.constants import SUPPORTED_LANGUAGES
from app.common.db import async_session_maker
from app.common.templates import templates

from .models import Snippet, Tag
from .schemas import SnippetView
from .search import SnippetsSearchParser

router = APIRouter()


@router.get("/", name="snippets.index")
async def index(
    request: Request,
    user: User = Depends(current_user),
    q: str = "",
    selected_id: uuid.UUID | str | None = None,
    mode: str = "mine",
    page: int = 1,
    size: int = 20,
):
    modes = {
        "MINE_MODE": "mine",
        "EXPLORE_MODE": "explore",
        "FAVORITES_MODE": "favorites",
    }
    supported_modes = modes.values()

    if mode not in supported_modes:
        return RedirectResponse(request.url_for("snippets.index"))

    if isinstance(selected_id, str):
        selected_id = uuid.UUID(selected_id)

    search_query = SnippetsSearchParser(q=q)

    async with async_session_maker() as session:
        items_query = select(Snippet).options(
            selectinload(Snippet.tags), selectinload(Snippet.favorited_by)
        )

        if mode == modes["EXPLORE_MODE"]:
            items_query = items_query.where(Snippet.public)
        elif mode == modes["FAVORITES_MODE"]:
            items_query = items_query.where(
                Snippet.favorited_by.any(User.id == user.id)
            )
        else:
            items_query = items_query.where(Snippet.user_id == user.id)

        for lang in search_query.languages:
            items_query = items_query.where(Snippet.language == lang)

        for tag in search_query.tags:
            items_query = items_query.where(Snippet.tags.any(Tag.id.ilike(tag)))

        if search_query.is_mine:
            items_query = items_query.where(Snippet.user_id == user.id)
        if search_query.is_public:
            items_query = items_query.where(Snippet.public)
        if search_query.is_fork:
            items_query = items_query.where(Snippet.is_fork)
        if search_query.is_favorite:
            items_query = items_query.where(
                Snippet.favorited_by.any(User.id == user.id)
            )

        if len(search_query.search_terms) > 0:
            filter_fields = (
                Snippet.title,
                Snippet.description,
                Snippet.content,
                Snippet.command_name,
                Snippet.subtitle,
                Snippet.language,
            )

            for term in search_query.search_terms:
                should_exact_match = term.startswith('"') and term.endswith('"')

                # https://www.postgresql.org/docs/current/functions-matching.html#POSIX-CONSTRAINT-ESCAPES-TABLE
                if should_exact_match:
                    term = term[1:-1]
                    op = "~"  # Case-sensitive regex match
                    term_regex = (
                        rf"\y{term}\y"  # Match whole word - \y is a word boundary
                    )
                    tag_conditions = [Snippet.tags.any(Tag.id == term.lower())]
                else:
                    op = "~*"  # Case-INsensitive regex match
                    term_regex = rf".*{term}.*"  # Match any part of the word
                    tag_conditions = [Snippet.tags.any(Tag.id.ilike(f"%{term}%"))]

                string_conditions = [
                    field.op(op)(term_regex) for field in filter_fields
                ]

                items_query = items_query.where(
                    or_(*string_conditions, *tag_conditions)
                )

        items_query = items_query.order_by(Snippet.updated_at.desc())

        page_data = await paginate(
            session, items_query, params=Params(page=page, size=size)
        )

        # Ensure selected_snippet is valid
        selected_snippet = None
        if selected_id:
            selected_snippet_query = (
                select(Snippet)
                .where(Snippet.id == selected_id, Snippet.user_id == user.id)
                .options(selectinload(Snippet.tags), selectinload(Snippet.favorited_by))
            )
            selected_snippet_result = await session.execute(selected_snippet_query)
            selected_snippet = selected_snippet_result.scalar_one_or_none()

            if not selected_snippet or selected_snippet.id not in [
                item.id for item in page_data.items
            ]:
                return RedirectResponse(
                    request.url_for("snippets.index").include_query_params(
                        mode=mode,
                        page=page,
                        size=size,
                        q=q,
                    )
                )

        # If there is no selected_snippet, or the selected_snippet is invalid, select the first snippet
        if not selected_snippet:
            selected_snippet = page_data.items[0] if page_data.items else None

    has_next = page_data.page < page_data.pages
    has_prev = page_data.page > 1

    prev_page_url = (
        request.url_for("snippets.index").include_query_params(
            mode=mode,
            page=page - 1,
            size=size,
            q=q,
        )
        if has_prev
        else None
    )
    next_page_url = (
        request.url_for("snippets.index").include_query_params(
            mode=mode,
            page=page + 1,
            size=size,
            q=q,
        )
        if has_next
        else None
    )

    selected_snippet = selected_snippet.to_view(user) if selected_snippet else None
    snippet_list = [snippet.to_card_view(user) for snippet in page_data.items]

    start_index = (page_data.page * page_data.size) - (page_data.size - 1)
    end_index = start_index + len(snippet_list) - 1

    tabs = [
        {
            "name": "My Snippets",
            "mode": modes["MINE_MODE"],
            "url": request.url_for("snippets.index").include_query_params(
                mode=modes["MINE_MODE"]
            ),
            "selected": mode == modes["MINE_MODE"],
        },
        {
            "name": "Favorites",
            "mode": modes["FAVORITES_MODE"],
            "url": request.url_for("snippets.index").include_query_params(
                mode=modes["FAVORITES_MODE"],
            ),
            "selected": mode == modes["FAVORITES_MODE"],
        },
        {
            "name": "Explore",
            "mode": modes["EXPLORE_MODE"],
            "url": request.url_for("snippets.index").include_query_params(
                mode=modes["EXPLORE_MODE"],
            ),
            "selected": mode == modes["EXPLORE_MODE"],
        },
    ]
    selected_tab = next(tab for tab in tabs if tab["selected"])

    return templates.TemplateResponse(
        request,
        "snippets/templates/index.html",
        {
            "mode": mode,
            "modes": modes,
            "tabs": tabs,
            "selected_tab": selected_tab,
            "selected_snippet": selected_snippet,
            "snippets": snippet_list,
            "search_context": search_query,
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


@router.get("/create", name="snippet.create")
async def create_snippet(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse(
        request,
        "snippets/templates/create.html",
        {
            "snippet": SnippetView(
                language=SUPPORTED_LANGUAGES.PLAINTEXT.name,
            ),
        },
    )


@router.post("/create", name="snippet.create.post")
@router.post("/{id}/fork", name="snippet.fork.post")
async def create_snippet_post(
    request: Request,
    user: User = Depends(current_user),
    title: str = Form(...),
    content: str = Form(...),
    language: str = Form(...),
    subtitle: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    command_name: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    public: bool = Form(False),
    forked_from_id: Optional[str | uuid.UUID] = Form(None),
):
    async with async_session_maker() as session:
        try:
            # Process tags
            tag_list = []
            if tags:
                tag_list = await Tag.bulk_add_tags(session, tags.split(","))

            if forked_from_id and not isinstance(forked_from_id, uuid.UUID):
                forked_from_id = uuid.UUID(forked_from_id)
            elif not forked_from_id:
                forked_from_id = None

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
                forked_from_id=forked_from_id,
                is_fork=bool(forked_from_id),
            )
            session.add(snippet)
            await session.commit()
        except Exception as e:
            # Convert tags back into a list
            tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
            return templates.TemplateResponse(
                request,
                "snippets/templates/create.html",
                {
                    "snippet": SnippetView(
                        title=title,
                        subtitle=subtitle,
                        content=content,
                        language=language,
                        description=description,
                        command_name=command_name,
                        public=public,
                        tags=tag_list,
                        forked_from_id=forked_from_id,
                        is_fork=bool(forked_from_id),
                    ),
                    "error": str(e),
                },
                status_code=400,
            )

    return RedirectResponse(
        request.url_for("snippet.view", id=snippet.id), status_code=303
    )


@router.get("/{id}", name="snippet.view")
async def view_snippet(
    request: Request,
    id: str | uuid.UUID,
    user: Optional[User] = Depends(optional_current_user),
):
    if isinstance(id, str):
        try:
            id = uuid.UUID(id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Snippet not found")

    async with async_session_maker() as session:
        is_public = and_(Snippet.id == id, Snippet.public)
        is_owned = and_(Snippet.id == id, Snippet.user_id == user.id) if user else False

        query = (
            select(Snippet)
            .where(is_public | is_owned)
            .options(selectinload(Snippet.tags), selectinload(Snippet.favorited_by))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        return templates.TemplateResponse(
            request,
            "snippets/templates/snippet.html",
            {
                "snippet": snippet.to_view(user),
            },
        )


@router.get("/{id}/edit", name="snippet.edit")
async def edit_snippet(
    request: Request, id: uuid.UUID, user: User = Depends(current_user)
):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.id == id, Snippet.user_id == user.id)
            .options(selectinload(Snippet.tags), selectinload(Snippet.favorited_by))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            return RedirectResponse(request.url_for("snippets.index"), status_code=303)

    return templates.TemplateResponse(
        request,
        "snippets/templates/edit.html",
        {
            "snippet": snippet.to_view(user),
        },
    )


@router.post("/{id}/edit", name="snippet.edit.post")
async def edit_snippet_post(
    request: Request,
    id: uuid.UUID,
    user: User = Depends(current_user),
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
            .where(Snippet.id == id, Snippet.user_id == user.id)
            .options(selectinload(Snippet.tags), selectinload(Snippet.favorited_by))
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

    return RedirectResponse(request.url_for("snippet.view", id=id), status_code=303)


@router.get("/{id}/fork", name="snippet.fork")
async def fork_snippet(
    request: Request,
    id: uuid.UUID,
    user: User = Depends(current_user),
):
    """Fork a public snippet."""
    async with async_session_maker() as session:
        # Get the original snippet

        is_public = and_(Snippet.id == id, Snippet.public)
        is_owned = and_(Snippet.id == id, Snippet.user_id == user.id) if user else False

        query = (
            select(Snippet)
            .where(is_public | is_owned)
            .options(selectinload(Snippet.tags), selectinload(Snippet.favorited_by))
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
            forked_from_id=original_snippet.id,
            is_fork=True,
        )

        return templates.TemplateResponse(
            request,
            "snippets/templates/fork.html",
            {
                "snippet": forked_snippet_view,
            },
        )


@router.post("/{id}/delete", name="snippet.delete")
async def delete_snippet(
    request: Request,
    id: uuid.UUID,
    user: User = Depends(current_user),
):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.id == id, Snippet.user_id == user.id)
            .options(selectinload(Snippet.tags), selectinload(Snippet.favorited_by))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        await session.delete(snippet)
        await session.commit()

    return RedirectResponse(request.url_for("snippets.index"), status_code=303)


@router.post("/{id}/toggle-favorite", name="snippet.toggle_favorite")
async def toggle_favorite_snippet(
    request: Request,
    id: uuid.UUID,
    user: User = Depends(current_user),
):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.id == id)
            .options(selectinload(Snippet.tags), selectinload(Snippet.favorited_by))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        user_favorite_query = (
            select(User)
            .options(selectinload(User.favorites))
            .where(User.id == user.id, User.favorites.any(Snippet.id == id))
        )
        user_favorite_result = await session.execute(user_favorite_query)
        user_favorite = user_favorite_result.scalar_one_or_none()

        if user_favorite:
            is_favorite = False
            snippet.favorited_by.remove(user_favorite)
        else:
            is_favorite = True
            snippet.favorited_by.append(user)

        await session.commit()

        return JSONResponse({"is_favorite": is_favorite})
