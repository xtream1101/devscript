import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_pagination.default import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from loguru import logger
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from app.auth.models import User
from app.auth.utils import current_user, optional_current_user
from app.common.constants import SUPPORTED_LANGUAGES
from app.common.db import async_session_maker
from app.common.templates import templates
from app.common.utils import flash

from .models import Snippet, Tag
from .schemas import SnippetView
from .search import SnippetsSearchParser

router = APIRouter(include_in_schema=False)


class Tab:
    MINE = "mine"
    EXPLORE = "explore"
    FAVORITES = "favorites"

    order = [MINE, FAVORITES, EXPLORE]
    labels = {
        MINE: "My Snippets",
        FAVORITES: "Favorites",
        EXPLORE: "Explore",
    }
    requires_auth = [MINE, FAVORITES]


@router.get("/", name="snippets.index")
async def index(
    request: Request,
    user: User | None = Depends(optional_current_user),
    q: str = "",
    selected_id: uuid.UUID | str | None = None,
    tab: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    logger.info(f"User: {user}")
    logger.warning("ahhh!!")
    if not tab:
        tab = Tab.MINE if user else Tab.EXPLORE

    if tab is None or tab not in Tab.order:
        return RedirectResponse(request.url_for("snippets.index"))

    tabs = [
        {
            "label": Tab.labels[tab],
            "value": tab,
            "url": request.url_for("snippets.index").include_query_params(tab=tab),
        }
        for tab in Tab.order
    ]

    if isinstance(selected_id, str):
        selected_id = uuid.UUID(selected_id)

    search_query = SnippetsSearchParser(q=q)

    async with async_session_maker() as session:
        items_query = select(Snippet).options(
            selectinload(Snippet.user),
            selectinload(Snippet.tags),
            selectinload(Snippet.favorited_by),
        )

        if tab == Tab.EXPLORE:
            items_query = items_query.where(Snippet.public)
        elif user:
            if tab == Tab.FAVORITES:
                items_query = items_query.where(
                    Snippet.favorited_by.any(User.id == user.id)
                )
                items_query = items_query.where(
                    or_(Snippet.public, Snippet.user_id == user.id)
                )
            elif tab == Tab.MINE:
                items_query = items_query.where(Snippet.user_id == user.id)
        else:
            items_query = None

        if items_query is None:
            page_data = None
            return templates.TemplateResponse(
                request,
                "snippets/templates/index.html",
                {
                    "tabs": tabs,
                    "selected_tab": tab,
                    "supported_tabs": Tab,
                    "snippets": [],
                    "selected_snippet": None,
                    "search_context": search_query,
                    "pagination_context": {
                        "total_pages": 0,
                        "total_items": 0,
                        "page_size": 0,
                        "page": 1,
                        "start_index": 0,
                        "end_index": 0,
                        "has_next": False,
                        "has_prev": False,
                        "next_page_url": None,
                        "prev_page_url": None,
                    },
                },
            )

        for lang in search_query.languages:
            items_query = items_query.where(Snippet.language == lang)

        for tag in search_query.tags:
            items_query = items_query.where(Snippet.tags.any(Tag.id.ilike(tag)))

        if search_query.is_mine and user:
            items_query = items_query.where(Snippet.user_id == user.id)
        if search_query.is_public:
            items_query = items_query.where(Snippet.public)
        if search_query.is_fork:
            items_query = items_query.where(Snippet.is_fork)
        if search_query.is_favorite and user:
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
                    term_regex = (
                        rf"\y{term}\y"  # Match whole word - \y is a word boundary
                    )
                    tag_conditions = [Snippet.tags.any(Tag.id == term.lower())]
                else:
                    term_regex = rf".*{term}.*"  # Match any part of the word
                    tag_conditions = [Snippet.tags.any(Tag.id.ilike(f"%{term}%"))]

                op = "~*"  # Case-INsensitive regex match
                string_conditions = [
                    field.op(op)(term_regex) for field in filter_fields
                ]

                items_query = items_query.where(
                    or_(*string_conditions, *tag_conditions)
                )

        items_query = items_query.order_by(Snippet.updated_at.desc())

        page_data = await paginate(
            session,
            items_query,
            params=Params(page=page, size=page_size),
        )

        # find selected snippet in the page data
        default_snippet = page_data.items[0] if page_data.items else None
        selected_snippet = None
        if selected_id:
            for snippet in page_data.items:
                if snippet.id == selected_id:
                    selected_snippet = snippet
                    break

            if not selected_snippet:
                return RedirectResponse(
                    request.url_for("snippets.index").include_query_params(
                        tab=tab,
                        page=page,
                        page_size=page_size,
                        q=q,
                    )
                )

        selected_snippet = selected_snippet or default_snippet
        selected_snippet = selected_snippet.to_view(user) if selected_snippet else None
        snippet_list = [snippet.to_card_view(user) for snippet in page_data.items]

        has_prev = page_data.page > 1
        prev_page_url = (
            request.url_for("snippets.index").include_query_params(
                tab=tab,
                page=page - 1,
                page_size=page_size,
                q=q,
            )
            if has_prev
            else None
        )
        has_next = page_data.page < page_data.pages
        next_page_url = (
            request.url_for("snippets.index").include_query_params(
                tab=tab,
                page=page + 1,
                page_size=page_size,
                q=q,
            )
            if has_next
            else None
        )
        start_index = (page_data.page * page_data.size) - (page_data.size - 1)
        end_index = start_index + len(page_data.items) - 1

        return templates.TemplateResponse(
            request,
            "snippets/templates/index.html",
            {
                "tabs": tabs,
                "selected_tab": tab,
                "supported_tabs": Tab,
                "snippets": snippet_list,
                "selected_snippet": selected_snippet,
                "search_context": search_query,
                "pagination_context": {
                    "total_pages": page_data.pages,
                    "total_items": page_data.total,
                    "page_size": page_data.size,
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
            flash(request, str(e), level="error")

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
            .options(
                selectinload(Snippet.user),
                selectinload(Snippet.tags),
                selectinload(Snippet.favorited_by),
            )
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
            .options(
                selectinload(Snippet.user),
                selectinload(Snippet.tags),
                selectinload(Snippet.favorited_by),
            )
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
            .options(
                selectinload(Snippet.user),
                selectinload(Snippet.tags),
                selectinload(Snippet.favorited_by),
            )
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
            flash(request, str(e), level="error")

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
            .options(
                selectinload(Snippet.user),
                selectinload(Snippet.tags),
                selectinload(Snippet.favorited_by),
            )
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
            command_name=original_snippet.command_name,
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
            .options(
                selectinload(Snippet.user),
                selectinload(Snippet.tags),
                selectinload(Snippet.favorited_by),
            )
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        await session.delete(snippet)
        await session.commit()

        flash(
            request,
            "You've successfully deleted the snippet",
            level="success",
            placement="notification",
        )

    return RedirectResponse(request.url_for("snippets.index"), status_code=303)


@router.post("/{id}/toggle-favorite", name="snippet.toggle_favorite")
async def toggle_favorite_snippet(
    request: Request,
    id: uuid.UUID,
    user: User = Depends(current_user),
):
    try:
        async with async_session_maker() as session:
            query = (
                select(Snippet)
                .where(Snippet.id == id)
                .where(or_(Snippet.public, Snippet.user_id == user.id))
            )
            result = await session.execute(query)
            snippet = result.scalar_one_or_none()

            if not snippet:
                raise HTTPException(status_code=404, detail="Snippet not found")

            user_with_favorites_query = (
                select(User)
                .options(selectinload(User.favorites))
                .where(User.id == user.id)
            )
            user_with_favorites_result = await session.execute(
                user_with_favorites_query
            )
            user_with_favorites = user_with_favorites_result.scalar_one_or_none()

            if not user_with_favorites:
                return JSONResponse({"is_favorite": False})

            if snippet in user_with_favorites.favorites:
                is_favorite = False
                user_with_favorites.favorites.remove(snippet)
            else:
                is_favorite = True
                user_with_favorites.favorites.append(snippet)

            await session.commit()

            return JSONResponse({"is_favorite": is_favorite})
    except Exception:
        logger.exception("Error toggling favorite")
        return JSONResponse({"error": "An error occurred"}, status_code=400)
