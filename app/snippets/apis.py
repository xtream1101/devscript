from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select

from app.auth.apis import get_api_key_user
from app.auth.models import User
from app.common.db import async_session_maker

from .models import Snippet

router = APIRouter()


@router.get(
    "/command/{command_name}", name="api.snippets.command.get", response_class=Response
)
@router.head(  # used to get the snippet language from the header
    "/command/{command_name}", name="api.snippets.command.head", response_class=Response
)
async def get_snippet_by_command_api(
    command_name: str,
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
            content=snippet.content.replace("\r\n", "\n"),
            media_type="text/plain",
            headers={"X-Snippet-Lang": str(snippet.language)},
        )
