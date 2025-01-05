import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import async_session_maker
from app.models.snippet import Snippet
from app.models.tag import Tag
from app.models.user import User
from app.users import current_active_user, optional_current_user

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/snippets", tags=["snippets"])


@router.get("/add")
async def add_snippet_view(request: Request, user: User = Depends(current_active_user)):
    return templates.TemplateResponse(
        "snippets/add.html", {"request": request, "user": user}
    )


@router.post("/add")
async def add_snippet_submit(
    request: Request,
    user: User = Depends(current_active_user),
    title: str = Form(...),
    content: str = Form(...),
    language: str = Form(...),
    description: Optional[str] = Form(None),
    command_name: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    public: bool = Form(False),
):
    async with async_session_maker() as session:
        # Only check command name if one is provided
        # if command_name:
        #     command_exists = await Snippet.check_command_name_exists(
        #         user.id, command_name
        #     )
        #     if command_exists:
        #         # Command name already exists for this user
        #         # Create a snippet object with the form data to pass back
        #         snippet = Snippet(
        #             title=title,
        #             content=content,
        #             language=language,
        #             description=description,
        #             command_name=command_name,
        #             public=public,
        #             user_id=user.id,
        #         )
        #         return templates.TemplateResponse(
        #             "snippets/add.html",
        #             {
        #                 "request": request,
        #                 "user": user,
        #                 "error": "Command name already exists",
        #                 "snippet": snippet,
        #             },
        #             status_code=400,
        #         )

        # Process tags
        tag_list = []
        if tags:
            # Split by comma and clean up each tag
            tag_names = [t.strip() for t in tags.split(",") if t.strip()]
            # Truncate to max length and remove duplicates
            tag_names = list(set(t[:16] for t in tag_names))

            # Get all existing tags in one query
            existing_tags = await session.execute(
                select(Tag).where(Tag.id.in_(tag_names))
            )
            existing_tags = existing_tags.scalars().all()
            existing_tag_ids = {tag.id for tag in existing_tags}

            # Create new tags for any that don't exist
            new_tags = []
            for tag_name in tag_names:
                if tag_name not in existing_tag_ids:
                    tag = Tag(name=tag_name)
                    new_tags.append(tag)
                    session.add(tag)

            tag_list = list(existing_tags) + new_tags

        snippet = Snippet(
            title=title,
            content=content,
            language=language,
            description=description,
            command_name=command_name,
            tags=tag_list,
            public=public,
            user_id=user.id,
        )

        session.add(snippet)
        await session.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/{snippet_id}")
async def view_snippet(
    request: Request,
    snippet_id: uuid.UUID,
    user: Optional[User] = Depends(optional_current_user),
):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.id == snippet_id)
            .options(selectinload(Snippet.tags))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        # Check if user can view this snippet
        if not snippet.public and (not user or snippet.user_id != user.id):
            raise HTTPException(
                status_code=403, detail="Not authorized to view this snippet"
            )

        return templates.TemplateResponse(
            "snippets/view.html", {"request": request, "snippet": snippet, "user": user}
        )


@router.get("/{snippet_id}/edit")
async def edit_snippet_form(
    request: Request, snippet_id: uuid.UUID, user: User = Depends(current_active_user)
):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.id == snippet_id)
            .options(selectinload(Snippet.tags))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            return RedirectResponse(url="/dashboard", status_code=303)

        # Ensure user can only edit their own snippets
        if snippet.user_id != user.id:
            return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse(
        "snippets/edit.html", {"request": request, "snippet": snippet, "user": user}
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
        query = (
            select(Snippet)
            .where(Snippet.id == snippet_id)
            .options(selectinload(Snippet.tags))
        )
        result = await session.execute(query)
        original_snippet = result.scalar_one_or_none()

        if not original_snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        if not original_snippet.public:
            raise HTTPException(status_code=403, detail="Cannot fork private snippets")

        if original_snippet.user_id == user.id:
            raise HTTPException(status_code=400, detail="Cannot fork your own snippet")

        # Create the forked snippet
        forked_snippet = Snippet(
            title=original_snippet.title,
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

        return RedirectResponse(url=f"/snippets/{forked_snippet.id}", status_code=303)


@router.post("/{snippet_id}/edit")
async def edit_snippet(
    request: Request,
    snippet_id: uuid.UUID,
    user: User = Depends(current_active_user),
    title: str = Form(...),
    content: str = Form(...),
    language: str = Form(...),
    description: Optional[str] = Form(None),
    command_name: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    public: bool = Form(False),
):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.id == snippet_id)
            .options(selectinload(Snippet.tags))
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet or snippet.user_id != user.id:
            return RedirectResponse(url="/dashboard", status_code=303)

        try:
            # Process tags
            if tags is not None:
                # Clear existing tags
                snippet.tags = []

                # Split by comma and clean up each tag
                tag_names = [t.strip() for t in tags.split(",") if t.strip()]
                # Truncate to max length and remove duplicates
                tag_names = list(set(t[:16] for t in tag_names))

                # Get all existing tags in one query
                existing_tags = await session.execute(
                    select(Tag).where(Tag.id.in_(tag_names))
                )
                existing_tags = existing_tags.scalars().all()
                existing_tag_ids = {tag.id for tag in existing_tags}

                # Create new tags for any that don't exist
                new_tags = []
                for tag_name in tag_names:
                    if tag_name not in existing_tag_ids:
                        tag = Tag(name=tag_name)
                        new_tags.append(tag)
                        session.add(tag)

                # Combine existing and new tags
                snippet.tags = list(existing_tags) + new_tags

            # Update snippet fields
            snippet.title = title
            snippet.content = content
            snippet.language = language
            snippet.description = description
            snippet.command_name = command_name
            snippet.public = public
            await session.commit()
        except Exception as e:
            return templates.TemplateResponse(
                "snippets/edit.html",
                {
                    "request": request,
                    "snippet": snippet,
                    "user": user,
                    "error": str(e),
                },
                status_code=400,
            )

    return RedirectResponse(url="/dashboard", status_code=303)
