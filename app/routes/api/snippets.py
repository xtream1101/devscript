from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from pydantic import BaseModel

from app.models import async_session_maker
from app.models.user import User
from app.models.snippet import Snippet
from app.routes.api.api_keys import get_api_key_user

router = APIRouter()


class SnippetCreate(BaseModel):
    title: str
    content: str
    language: str
    description: Optional[str] = None
    command_name: Optional[str] = None
    public: bool = False


class SnippetUpdate(SnippetCreate):
    pass


@router.get("/snippets", response_model=List[dict], tags=["snippets"])
async def list_snippets_api(
    x_api_key: str = Header(..., alias="X-API-Key"),
    user: User = Depends(get_api_key_user),
):
    """List all snippets for the authenticated API user."""
    async with async_session_maker() as session:
        query = select(Snippet).where(Snippet.user_id == user.id)
        result = await session.execute(query)
        snippets = result.scalars().all()

        return [
            {
                "id": str(snippet.id),
                "title": snippet.title,
                "content": snippet.content,
                "language": snippet.language,
                "description": snippet.description,
                "command_name": snippet.command_name,
                "public": snippet.public,
                "created_at": snippet.created_at,
                "updated_at": snippet.updated_at,
                "forked_from_id": str(snippet.forked_from_id)
                if snippet.forked_from_id
                else None,
            }
            for snippet in snippets
        ]


@router.post("/snippets", response_model=dict, tags=["snippets"])
async def create_snippet_api(
    snippet: SnippetCreate,
    x_api_key: str = Header(..., alias="X-API-Key"),
    user: User = Depends(get_api_key_user),
):
    """Create a new snippet for the authenticated API user."""
    async with async_session_maker() as session:
        # Check for duplicate command name
        if await Snippet.check_command_name_exists(user.id, snippet.command_name):
            raise HTTPException(status_code=400, detail="Command name already exists")

        new_snippet = Snippet(
            title=snippet.title,
            content=snippet.content,
            language=snippet.language,
            description=snippet.description,
            command_name=snippet.command_name,
            public=snippet.public,
            user_id=user.id,
        )

        session.add(new_snippet)
        await session.commit()
        await session.refresh(new_snippet)

        return {
            "id": str(new_snippet.id),
            "title": new_snippet.title,
            "content": new_snippet.content,
            "language": new_snippet.language,
            "description": new_snippet.description,
            "command_name": new_snippet.command_name,
            "public": new_snippet.public,
            "created_at": new_snippet.created_at,
            "updated_at": new_snippet.updated_at,
            "forked_from_id": str(new_snippet.forked_from_id)
            if new_snippet.forked_from_id
            else None,
        }


@router.put("/snippets/{snippet_id}", response_model=dict, tags=["snippets"])
async def update_snippet_api(
    snippet_id: str,
    snippet: SnippetUpdate,
    x_api_key: str = Header(..., alias="X-API-Key"),
    user: User = Depends(get_api_key_user),
):
    """Update a snippet for the authenticated API user."""
    async with async_session_maker() as session:
        # Get existing snippet
        query = select(Snippet).where(Snippet.id == snippet_id)
        result = await session.execute(query)
        existing_snippet = result.scalar_one_or_none()

        if not existing_snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        if existing_snippet.user_id != user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to update this snippet"
            )

        # Check for duplicate command name
        if await Snippet.check_command_name_exists(
            user.id, snippet.command_name, snippet_id
        ):
            raise HTTPException(status_code=400, detail="Command name already exists")

        # Update snippet fields
        existing_snippet.title = snippet.title
        existing_snippet.content = snippet.content
        existing_snippet.language = snippet.language
        existing_snippet.description = snippet.description
        existing_snippet.command_name = snippet.command_name
        existing_snippet.public = snippet.public

        await session.commit()
        await session.refresh(existing_snippet)

        return {
            "id": str(existing_snippet.id),
            "title": existing_snippet.title,
            "content": existing_snippet.content,
            "language": existing_snippet.language,
            "description": existing_snippet.description,
            "command_name": existing_snippet.command_name,
            "public": existing_snippet.public,
            "created_at": existing_snippet.created_at,
            "updated_at": existing_snippet.updated_at,
            "forked_from_id": str(existing_snippet.forked_from_id)
            if existing_snippet.forked_from_id
            else None,
        }


@router.get(
    "/snippets/command/{command_name}", response_class=Response, tags=["snippets"]
)
async def get_snippet_by_command_api(
    command_name: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    user: User = Depends(get_api_key_user),
):
    """Get a snippet's content by command name for the authenticated API user."""
    async with async_session_maker() as session:
        query = select(Snippet).where(
            Snippet.user_id == user.id, Snippet.command_name == command_name
        )
        result = await session.execute(query)
        snippet = result.scalar_one_or_none()

        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")

        return Response(
            content=snippet.content.replace("\r\n", "\n"), media_type="text/plain"
        )


@router.get("/snippets/public", response_model=List[dict], tags=["snippets"])
async def list_public_snippets_api():
    """List all public snippets."""
    async with async_session_maker() as session:
        query = select(Snippet).where(Snippet.public == True)
        result = await session.execute(query)
        snippets = result.scalars().all()

        return [
            {
                "id": str(snippet.id),
                "title": snippet.title,
                "content": snippet.content,
                "language": snippet.language,
                "description": snippet.description,
                "command_name": snippet.command_name,
                "public": snippet.public,
                "created_at": snippet.created_at,
                "updated_at": snippet.updated_at,
                "forked_from_id": str(snippet.forked_from_id)
                if snippet.forked_from_id
                else None,
            }
            for snippet in snippets
        ]


@router.post("/snippets/{snippet_id}/fork", response_model=dict, tags=["snippets"])
async def fork_snippet_api(
    snippet_id: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    user: User = Depends(get_api_key_user),
):
    """Fork a public snippet."""
    async with async_session_maker() as session:
        # Get the original snippet
        query = select(Snippet).where(Snippet.id == snippet_id)
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
        )

        session.add(forked_snippet)
        await session.commit()
        await session.refresh(forked_snippet)

        return {
            "id": str(forked_snippet.id),
            "title": forked_snippet.title,
            "content": forked_snippet.content,
            "language": forked_snippet.language,
            "description": forked_snippet.description,
            "command_name": forked_snippet.command_name,
            "public": forked_snippet.public,
            "created_at": forked_snippet.created_at,
            "updated_at": forked_snippet.updated_at,
            "forked_from_id": str(forked_snippet.forked_from_id),
        }
