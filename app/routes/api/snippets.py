from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select


from app.models import async_session_maker
from app.models.user import User
from app.models.snippet import Snippet
from app.routes.api.api_keys import get_api_key_user

router = APIRouter()


@router.get(
    "/snippets/command/{command_name}", response_class=Response, tags=["snippets"]
)
@router.head(  # used to get the snippet language fro the header
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
            content=snippet.content.replace("\r\n", "\n"),
            media_type="text/plain",
            headers={"X-Snippet-Lang": str(snippet.language)},
        )
