from humanfriendly import format_timespan

from app.settings import settings

from .config import send_email_async


async def send_password_reset_email(request, email: str, reset_token: str):
    """Send a password reset email to the user"""
    reset_url = str(request.url_for("auth.reset_password", token=reset_token))
    await send_email_async(
        template_name="reset_password.html",
        recipients=[email],
        subject="Reset Your Password",
        template_vars={
            "reset_url": reset_url,
            "expiration_time": format_timespan(settings.PASSWORD_RESET_LINK_EXPIRATION),
        },
    )


async def send_welcome_email(request, email: str):
    """Send a password reset email to the user"""
    await send_email_async(
        template_name="welcome_email.html",
        recipients=[email],
        subject="Welcome to devscript",
        template_vars={"welcome_url": str(request.url_for("auth.login"))},
    )


async def send_verification_email(
    request, email: str, validation_token: str, from_change_email: bool = False
):
    """
    Send a verification email to the user
    """
    verify_url = str(
        request.url_for("auth.verify_email").include_query_params(
            token=validation_token
        )
    )
    await send_email_async(
        template_name="verify_email.html",
        recipients=[email],
        subject="Verify your devscript email address",
        template_vars={
            "from_change_email": from_change_email,
            "verify_url": verify_url,
            "expiration_time": format_timespan(settings.VALIDATION_LINK_EXPIRATION),
        },
    )
