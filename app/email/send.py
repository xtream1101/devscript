from app.settings import settings

from .config import send_email_async


async def send_password_reset_email(request, email: str, reset_token: str):
    """Send a password reset email to the user"""
    reset_url = str(request.url_for("auth.reset_password", token=reset_token))
    await send_email_async(
        email_to=email,
        subject="Reset Your Password",
        template_vars={"reset_url": reset_url},
        template_name="reset_password.html",
    )


async def send_welcome_email(request, email: str):
    """Send a password reset email to the user"""
    await send_email_async(
        email_to=email,
        subject="Welcome to devscript",
        template_vars={"welcome_url": str(request.url_for("auth.login"))},
        template_name="welcome_email.html",
    )


async def send_verification_email(email: str, validation_token: str):
    """
    Send a verification email to the user
    """
    await send_email_async(
        email_to=email,
        subject="Please verify your email",
        template_vars={
            "verify_url": f"{settings.HOST}/verify?token={validation_token}"
        },
        template_name="verify_email.html",
    )
