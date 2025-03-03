import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_pagination.default import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from loguru import logger
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import User
from app.auth.utils import current_user, optional_current_user
from app.common.db import get_async_session
from app.common.exceptions import ValidationError
from app.common.templates import templates
from app.common.utils import flash

from .models import Snippet, Tag
from .search import SnippetsSearchParser
from .serializers import SnippetSerializer

router = APIRouter(include_in_schema=False)


# =================================================================================
#
# Snippets Index
#       - View and search all snippets (mine, favorites, explore)
#
# =================================================================================


# --------------------------------------------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------------------------------------------
class Tab:
    """
    Class to represent the different tabs on the snippets index page
    """

    MINE = "mine"
    EXPLORE = "explore"
    FAVORITES = "favorites"

    labels = {
        MINE: "My Snippets",
        FAVORITES: "Favorites",
        EXPLORE: "Explore",
    }

    order = [MINE, FAVORITES, EXPLORE]

    # Tabs that require authentication, will show a login prompt if not authenticated
    requires_auth = [MINE, FAVORITES]


# --------------------------------------------------------------------------------------------------------------
# GET | Snippets Index View
# --------------------------------------------------------------------------------------------------------------
@router.get("/", name="snippets.index")
async def index(
    request: Request,
    user: User | None = Depends(optional_current_user),
    session: AsyncSession = Depends(get_async_session),
    q: str = "",
    selected_id: uuid.UUID | str | None = None,
    tab: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
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

    # Build the query based on the current tab and search query
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
        items_query = items_query.where(Snippet.tags.any(Tag.name.ilike(tag)))

    if search_query.is_mine and user:
        items_query = items_query.where(Snippet.user_id == user.id)

    if search_query.is_public:
        items_query = items_query.where(Snippet.public)

    if search_query.is_fork:
        items_query = items_query.where(Snippet.is_fork)

    if search_query.is_favorite and user:
        items_query = items_query.where(Snippet.favorited_by.any(User.id == user.id))

    if search_query.is_command:
        items_query = items_query.where(Snippet.command_name.isnot(None))

    if search_query.is_archived:
        items_query = items_query.where(Snippet.archived)
    else:
        items_query = items_query.where(Snippet.archived.is_(False))

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
                term_regex = rf"\y{term}\y"  # Match whole word - \y is a word boundary
                tag_conditions = [Snippet.tags.any(Tag.name == term.lower())]
            else:
                term_regex = rf".*{term}.*"  # Match any part of the word
                tag_conditions = [Snippet.tags.any(Tag.name.ilike(f"%{term}%"))]

            op = "~*"  # Case-INsensitive regex match
            string_conditions = [field.op(op)(term_regex) for field in filter_fields]

            items_query = items_query.where(or_(*string_conditions, *tag_conditions))

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
    selected_snippet = (
        selected_snippet.to_serializer(user) if selected_snippet else None
    )
    snippet_list = [snippet.to_serializer(user) for snippet in page_data.items]

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


# =================================================================================
#
# Create & Fork Snippet Routes
#
# =================================================================================


# --------------------------------------------------------------------------------------------------------------
# GET | Create Snippet Form View
# --------------------------------------------------------------------------------------------------------------
@router.get("/create", name="snippet.create")
async def create_snippet(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse(
        request,
        "snippets/templates/create.html",
        {
            "snippet": SnippetSerializer(),
        },
    )


# --------------------------------------------------------------------------------------------------------------
# GET | Fork Snippet Form View
# --------------------------------------------------------------------------------------------------------------
@router.get("/{id}/fork", name="snippet.fork")
async def fork_snippet(
    request: Request,
    id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Fork a public snippet."""

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found"
        )

    forked_title = f"Copy of {original_snippet.title}"
    forked_title = forked_title[: Snippet.title.property.columns[0].type.length]

    forked_snippet_view = SnippetSerializer(
        title=forked_title,
        subtitle=original_snippet.subtitle,
        content=original_snippet.content,
        language=original_snippet.language,
        description=original_snippet.description,
        command_name=original_snippet.command_name,
        tags=original_snippet.tags,  # type: ignore
        public=False,  # Default to private for forked snippets
        user_id=str(user.id),
        forked_from_id=str(original_snippet.id),
        is_fork=True,
    )

    return templates.TemplateResponse(
        request,
        "snippets/templates/fork.html",
        {
            "snippet": forked_snippet_view,
        },
    )


# --------------------------------------------------------------------------------------------------------------
# POST | Create & Fork Snippet Form Submission
# --------------------------------------------------------------------------------------------------------------
@router.post("/create", name="snippet.create.post")
@router.post("/{id}/fork", name="snippet.fork.post")
async def create_snippet_post(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
    title: str = Form(...),
    content: str = Form(...),
    language: str = Form(...),
    subtitle: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    command_name: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    public: bool = Form(False),
    archived: bool = Form(False),
    forked_from_id: Optional[str | uuid.UUID] = Form(None),
):
    try:
        if forked_from_id and not isinstance(forked_from_id, uuid.UUID):
            forked_from_id = uuid.UUID(forked_from_id)
        else:
            forked_from_id = None

        snippet = Snippet(
            title=title,
            content=content,
            language=language,
            subtitle=subtitle,
            description=description,
            command_name=command_name,
            public=public,
            archived=archived,
            user_id=user.id,
            forked_from_id=forked_from_id,
            is_fork=bool(forked_from_id),
        )
        snippet.tag_associations = (
            await snippet.bulk_add_tags(session, tags.split(",")) if tags else []
        )
        session.add(snippet)
        await session.commit()

    except Exception as e:
        if isinstance(e, ValidationError):
            flash(request, str(e), level="error")
        else:
            flash(request, "An error occurred", level="error")
            logger.exception("Error creating snippet")

        # Convert tags back into a list
        return templates.TemplateResponse(
            request,
            "snippets/templates/create.html",
            {
                "snippet": SnippetSerializer(
                    title=title,
                    subtitle=subtitle,
                    content=content,
                    language=language,
                    description=description,
                    command_name=command_name,
                    public=public,
                    archived=archived,
                    tags=tags,  # type: ignore
                    forked_from_id=str(forked_from_id) if forked_from_id else None,
                    is_fork=bool(forked_from_id),
                ),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return RedirectResponse(
        request.url_for("snippet.view", id=snippet.id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


# =================================================================================
#
# Snippet View
# NOTE: this route must be placed after the create and fork routes
#      - View a single snippet
#
# =================================================================================
@router.get("/{id}", name="snippet.view")
async def view_snippet(
    request: Request,
    id: str | uuid.UUID,
    user: Optional[User] = Depends(optional_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if isinstance(id, str):
        try:
            id = uuid.UUID(id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found"
            )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found"
        )

    return templates.TemplateResponse(
        request,
        "snippets/templates/snippet.html",
        {
            "snippet": snippet.to_serializer(user),
        },
    )


# =================================================================================
#
# Edit Snippet
#
# =================================================================================


# --------------------------------------------------------------------------------------------------------------
# GET | Edit Snippet Form View
# --------------------------------------------------------------------------------------------------------------
@router.get("/{id}/edit", name="snippet.edit")
async def edit_snippet(
    request: Request,
    id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
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
        return RedirectResponse(
            request.url_for("snippets.index"), status_code=status.HTTP_303_SEE_OTHER
        )

    return templates.TemplateResponse(
        request,
        "snippets/templates/edit.html",
        {
            "snippet": snippet.to_serializer(user),
        },
    )


# --------------------------------------------------------------------------------------------------------------
# POST | Edit Snippet Form Submission
# --------------------------------------------------------------------------------------------------------------
@router.post("/{id}/edit", name="snippet.edit.post")
async def edit_snippet_post(
    request: Request,
    id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
    title: str = Form(...),
    subtitle: Optional[str] = Form(None),
    content: str = Form(...),
    language: str = Form(...),
    description: Optional[str] = Form(None),
    command_name: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    public: bool = Form(False),
    archived: bool = Form(False),
):
    query = (
        select(Snippet)
        .where(Snippet.id == id, Snippet.user_id == user.id)
        .options(
            selectinload(Snippet.user),
            selectinload(Snippet.tags),
            selectinload(Snippet.tag_associations),
            selectinload(Snippet.favorited_by),
        )
    )
    result = await session.execute(query)
    snippet = result.scalar_one_or_none()

    if not snippet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found"
        )

    try:
        snippet.title = title
        snippet.subtitle = subtitle
        snippet.tag_associations = (
            await snippet.bulk_add_tags(session, tags.split(",")) if tags else []
        )
        snippet.content = content
        snippet.language = language
        snippet.description = description
        snippet.command_name = command_name
        snippet.public = public
        snippet.archived = archived

        await session.commit()
    except Exception as e:
        if isinstance(e, ValidationError):
            flash(request, str(e), level="error")
        else:
            logger.exception("Error editing snippet")
            flash(request, "Error editing snippet", level="error")

        # Convert tags back into a list
        return templates.TemplateResponse(
            request,
            "snippets/templates/edit.html",
            {
                "snippet": SnippetSerializer(
                    title=title,
                    subtitle=subtitle,
                    content=content,
                    language=language,
                    description=description,
                    command_name=command_name,
                    public=public,
                    archived=archived,
                    tags=tags,  # type: ignore
                ),
            },
            status_code=400,
        )

    return RedirectResponse(
        request.url_for("snippet.view", id=id), status_code=status.HTTP_303_SEE_OTHER
    )


# =================================================================================
#
# Delete Snippet
#
# =================================================================================
@router.post("/{id}/delete", name="snippet.delete.post")
async def delete_snippet(
    request: Request,
    id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    query = select(Snippet).where(Snippet.id == id, Snippet.user_id == user.id)
    result = await session.execute(query)
    snippet = result.scalar_one_or_none()

    if not snippet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found"
        )

    await session.delete(snippet)
    await session.commit()

    flash(
        request,
        "You've successfully deleted the snippet",
        level="success",
        placement="notification",
    )

    return RedirectResponse(
        request.url_for("snippets.index"), status_code=status.HTTP_303_SEE_OTHER
    )


# =================================================================================
#
# (Un)Favorite Snippet
#
# =================================================================================
@router.post("/{id}/toggle-favorite", name="snippet.toggle_favorite.post")
async def toggle_favorite_snippet(
    request: Request,
    id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        query = (
            select(Snippet)
            .where(Snippet.id == id)
            .where(or_(Snippet.public, Snippet.user_id == user.id))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found"
            )

        user_with_favorites_query = (
            select(User).options(selectinload(User.favorites)).where(User.id == user.id)
        )
        user_with_favorites_result = await session.execute(user_with_favorites_query)
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
        return JSONResponse(
            {"error": "An error occurred"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
