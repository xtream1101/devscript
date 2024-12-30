from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import async_session_maker
from app.models.user import User
from app.models.snippet import Snippet
from app.users import current_active_user

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


@router.get("/")
@router.get("/dashboard")
async def dashboard(request: Request, user: User = Depends(current_active_user)):
    async with async_session_maker() as session:
        query = (
            select(Snippet)
            .where(Snippet.user_id == user.id)
            .order_by(Snippet.created_at.desc())
            .options(selectinload(Snippet.tags))
        )
        result = await session.execute(query)
        snippets = result.scalars().all()

    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": user, "snippets": snippets}
    )
