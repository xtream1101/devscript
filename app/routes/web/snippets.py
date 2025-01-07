import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.auth.user import current_active_user, optional_current_user
from app.models.common import async_session_maker
from app.models.snippet import Snippet, SnippetView
from app.models.tag import Tag
from app.models.user import User
from app.templates import templates

router = APIRouter(prefix="/snippets", tags=["snippets"])


@router.get("/add")
async def add_snippet(request: Request, user: User = Depends(current_active_user)):
    return templates.TemplateResponse(
        request,
        "snippets/add.html",
        {
            "user": user,
            "snippet": SnippetView(),
        },
    )


@router.post("/add")
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
            )
            session.add(snippet)
            await session.commit()
        except Exception as e:
            # Convert tags back into a list
            tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
            return templates.TemplateResponse(
                request,
                "snippets/add.html",
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
            "snippets/view.html",
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
        "snippets/edit.html",
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
                "snippets/edit.html",
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


@router.post("/{snippet_id}/fork")
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

        # Create the forked snippet
        forked_snippet = Snippet(
            title=f"Copy of {original_snippet.title}",
            subtitle=original_snippet.subtitle,
            content=original_snippet.content,
            language=original_snippet.language,
            description=original_snippet.description,
            command_name=None,  # Set command_name to null for forked snippets
            public=False,  # Default to private for forked snippets
            user_id=user.id,
            forked_from_id=original_snippet.id,
            tags=original_snippet.tags,  # Copy tags from original snippet
        )

        session.add(forked_snippet)
        await session.commit()

        return RedirectResponse(
            url=router.url_path_for("view_snippet", snippet_id=forked_snippet.id),
            status_code=303,
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
