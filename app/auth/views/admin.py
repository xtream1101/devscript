import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_async_session
from app.common.templates import templates
from app.common.utils import flash
from app.email.send import send_invitation_email
from app.settings import settings

from ..models import Invitation, User
from ..utils import admin_required, current_user

router = APIRouter(tags=["Admin"])


@router.get("/admin", name="auth.admin")
@admin_required
async def admin_view(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Admin page for user management."""
    query = select(User).order_by(User.registered_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()

    # Get active invitations if registration is disabled
    invitations = []
    if settings.DISABLE_REGISTRATION:
        query = (
            select(Invitation)
            .order_by(Invitation.created_at.desc())
            .where(
                Invitation.expires_at > datetime.now(timezone.utc),
                Invitation.used_at.is_(None),
            )
        )
        result = await session.execute(query)
        invitations = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "auth/templates/admin.html",
        {"users": users, "invitations": invitations},
    )


@router.post("/admin/invite", name="auth.invite_user")
@admin_required
async def invite_user(
    request: Request,
    email: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new invitation."""
    if not settings.DISABLE_REGISTRATION:
        flash(request, "Registration is not disabled", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Check if user already exists
    query = select(User).filter(User.email == email.lower().strip())
    result = await session.execute(query)
    if result.scalar_one_or_none():
        flash(request, "User with this email already exists", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Check for existing non-expired invitation
    query = select(Invitation).filter(
        Invitation.email == email.lower().strip(),
        Invitation.expires_at > datetime.now(timezone.utc),
        Invitation.used_at.is_(None),
    )
    result = await session.execute(query)
    if result.scalar_one_or_none():
        flash(request, "An active invitation already exists for this email", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Create invitation
    invitation = Invitation(email=email, created_by_id=user.id)
    session.add(invitation)
    await session.commit()

    # Send invitation email if SMTP is configured
    if settings.SMTP_HOST:
        try:
            await send_invitation_email(
                email=invitation.email,
                invitation_link=invitation.get_invitation_link(request),
            )
            invitation.email_sent = True
            await session.commit()
            flash(request, "Invitation sent successfully", "success")
        except Exception as e:
            flash(
                request,
                f"Invitation created but email could not be sent: {str(e)}",
                "warning",
            )
    else:
        flash(
            request,
            "Invitation created. Email sending is not configured - share the invitation link manually.",
            "warning",
        )

    return RedirectResponse(
        url=request.url_for("auth.admin"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/admin/invitations/{invitation_id}/resend", name="auth.resend_invitation")
@admin_required
async def resend_invitation(
    request: Request,
    invitation_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Resend an invitation email."""
    if not settings.SMTP_HOST:
        flash(request, "Email sending is not configured", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    query = select(Invitation).filter(Invitation.id == invitation_id)
    result = await session.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        flash(request, "Invitation not found", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if invitation.is_used:
        flash(request, "Invitation has already been used", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if invitation.is_expired:
        flash(request, "Invitation has expired", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        await send_invitation_email(
            email=invitation.email,
            invitation_link=invitation.get_invitation_link(request),
        )
        invitation.email_sent = True
        await session.commit()
        flash(request, "Invitation email resent successfully", "success")
    except Exception as e:
        flash(request, f"Failed to send invitation email: {str(e)}", "error")

    return RedirectResponse(
        url=request.url_for("auth.admin"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/admin/users/{user_id}/ban", name="auth.toggle_user_ban")
@admin_required
async def toggle_user_ban(
    request: Request,
    user_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Toggle user ban status."""
    if user.id == user_id:
        flash(request, "Cannot ban yourself", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    query = select(User).filter(User.id == user_id)
    result = await session.execute(query)
    target_user = result.scalar_one_or_none()

    if not target_user:
        flash(request, "User not found", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if target_user.is_admin:
        flash(request, "Cannot ban admin users", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    target_user.is_banned = not target_user.is_banned
    await session.commit()

    action = "banned" if target_user.is_banned else "unbanned"
    flash(request, f"User {action} successfully", "success")
    return RedirectResponse(
        url=request.url_for("auth.admin"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/admin/users/{user_id}/delete", name="auth.delete_user")
@admin_required
async def delete_user(
    request: Request,
    user_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a user."""
    if user.id == user_id:
        flash(request, "Cannot delete yourself", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    query = select(User).filter(User.id == user_id)
    result = await session.execute(query)
    target_user = result.scalar_one_or_none()

    if not target_user:
        flash(request, "User not found", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if target_user.is_admin:
        flash(request, "Cannot delete admin users", "error")
        return RedirectResponse(
            url=request.url_for("auth.admin"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    await session.delete(target_user)
    await session.commit()

    flash(request, "User deleted successfully", "success")
    return RedirectResponse(
        url=request.url_for("auth.admin"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
