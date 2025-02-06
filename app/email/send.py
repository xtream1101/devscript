from humanfriendly import format_timespan
from sqlalchemy import event, func, select

from app.auth.models import Provider
from app.auth.serializers import TokenDataSerializer
from app.auth.utils import create_token
from app.common import utils
from app.common.db import async_session_maker
from app.settings import settings

from .config import send_email_async


async def send_password_reset_email(email: str, reset_token: str):
    """Send a password reset email to the user"""
    from app.app import app

    reset_url = settings.HOST + str(
        app.url_path_for("auth.reset_password", token=reset_token)
    )
    await send_email_async(
        template_name="reset_password.html",
        recipients=[email],
        subject="Reset your devscript password",
        template_vars={
            "reset_url": reset_url,
            "expiration_time": format_timespan(settings.PASSWORD_RESET_LINK_EXPIRATION),
            "show_login_btn": False,
        },
    )


async def send_welcome_email(email: str):
    """Send a welcome email to the user"""
    from app.app import app

    welcome_url = settings.HOST + str(app.url_path_for("auth.login"))
    await send_email_async(
        template_name="welcome.html",
        recipients=[email],
        subject="Welcome to devscript!",
        template_vars={
            "welcome_url": welcome_url,
            "show_login_btn": True,
        },
    )


async def send_verification_email(
    email: str, validation_token: str, from_change_email: str = None
):
    """
    Send a verification email to the user
    """
    from app.app import app

    verify_url = (
        settings.HOST
        + str(app.url_path_for("auth.verify_email"))
        + f"?token={validation_token}"
    )
    await send_email_async(
        template_name="verify.html",
        recipients=[email],
        subject="Verify your devscript email address",
        template_vars={
            "verify_url": verify_url,
            "expiration_time": format_timespan(settings.VALIDATION_LINK_EXPIRATION),
            "from_change_email": from_change_email,
            "show_login_btn": False,
        },
    )
    # Also send email to the old email address if it was changed
    if from_change_email:
        await send_email_async(
            template_name="verify_old_email.html",
            recipients=[from_change_email],
            subject="Your devscript email address was changed",
            template_vars={
                "new_email": email,
            },
        )


async def _send_verify_or_welcome_email(
    incoming_data: Provider, is_new: bool = False
) -> None:
    """
    Based on what data changed, send the correct email to the user

    Args:
        incoming_data: The provider being created/updated
        is_new: Whether this is a new provider being created
    """
    # Get the old is_verified value for existing providers
    previous_is_verified = None
    if not is_new:
        async with async_session_maker() as session:
            query = select(Provider.is_verified).where(Provider.id == incoming_data.id)
            result = await session.execute(query)
            previous_is_verified = result.scalar_one_or_none()

    if (
        previous_is_verified is not None
        and previous_is_verified == incoming_data.is_verified
    ):
        # Only proceed if is_verified changed
        return

    async with async_session_maker() as session:
        # Get count of verified providers for this user
        query = select(func.count(Provider.id)).where(
            Provider.user_id == incoming_data.user_id,
            Provider.is_verified,
            Provider.id != incoming_data.id,  # Exclude current provider
        )
        result = await session.execute(query)
        verified_provider_count = result.scalar()

        is_only_provider = verified_provider_count == 0

        if not incoming_data.is_verified:
            # Send verification email if provider is being set to not verified
            validation_token = await create_token(
                TokenDataSerializer(
                    user_id=incoming_data.user_id,
                    email=incoming_data.email,
                    provider_name=incoming_data.name,
                    token_type="validation",
                )
            )
            await send_verification_email(
                email=incoming_data.email,
                validation_token=validation_token,
            )
        elif incoming_data.is_verified and is_only_provider:
            print("Sending welcome email")
            print(f"Email: {incoming_data.email}")
            print(f"Verified provider count: {verified_provider_count}")
            print(f"Is new: {is_new}")
            print(f"Previous is verified: {previous_is_verified}")
            print(f"Current is verified: {incoming_data.is_verified}")
            # Send welcome email if this is becoming the only verified provider
            await send_welcome_email(
                email=incoming_data.email,
            )


@event.listens_for(Provider, "before_update")
def provider_before_update(mapper, connection, target):
    try:
        with utils.sync_await() as await_:
            _ = await_(_send_verify_or_welcome_email(target))
    except Exception as exc:
        raise exc


@event.listens_for(Provider, "before_insert")
def provider_before_insert(mapper, connection, target):
    try:
        with utils.sync_await() as await_:
            _ = await_(_send_verify_or_welcome_email(target, is_new=True))
    except Exception as exc:
        raise exc
