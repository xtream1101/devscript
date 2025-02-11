import base64
import logging
import textwrap

from fastapi import BackgroundTasks
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.fastmail import email_dispatched as email_dispatched_signal
from loguru import logger

from app.settings import settings


def is_smtp_configured() -> bool:
    """Check if SMTP settings are configured"""
    return all(
        [
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
            settings.SMTP_FROM,
        ]
    )


# Only create mail config if SMTP is configured
conf = None
if is_smtp_configured():
    conf = ConnectionConfig(
        MAIL_USERNAME=settings.SMTP_USER,
        MAIL_PASSWORD=settings.SMTP_PASSWORD,
        MAIL_FROM=settings.SMTP_FROM,
        MAIL_PORT=settings.SMTP_PORT,
        MAIL_SERVER=settings.SMTP_HOST,
        MAIL_FROM_NAME=settings.SMTP_FROM_NAME,
        MAIL_STARTTLS=settings.SMTP_STARTTLS,
        MAIL_SSL_TLS=settings.SMTP_SSL,
        USE_CREDENTIALS=True,
        TEMPLATE_FOLDER="app/email/templates/",
        MAIL_DEBUG=settings.SMTP_DEBUG,
        SUPPRESS_SEND=settings.SMTP_LOCAL_DEV,
    )


def _create_message(
    subject: str,
    recipients: list,
    template_vars: dict = {},
):
    if not is_smtp_configured():
        logging.info("SMTP not configured, skipping email send")
        return

    if not conf:
        logging.error("Mail configuration not initialized")
        return

    template_vars = {
        "base_url": settings.HOST,
        "docs_url": settings.DOCS_HOST,
        "subject": subject,
        "show_login_btn": True,
        **template_vars,
    }
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        template_body=template_vars,
        subtype=MessageType.html,
    )
    return message


async def send_email_async(
    template_name: str,
    subject: str,
    recipients: list,
    template_vars: dict = {},
):
    if not is_smtp_configured():
        logging.info("SMTP not configured, skipping email send")
        return

    if not conf:
        logging.error("Mail configuration not initialized")
        return

    logging.info(
        "Sending email", extra={"template_name": template_name, "subject": subject}
    )
    fm = FastMail(conf)
    message = _create_message(subject, recipients, template_vars)
    await fm.send_message(message, template_name=template_name)


def send_email_background(
    background_tasks: BackgroundTasks,
    template_name: str,
    subject: str,
    recipients: list,
    template_vars: dict = {},
):
    if not is_smtp_configured():
        logging.info("SMTP not configured, skipping email send")
        return

    if not conf:
        logging.error("Mail configuration not initialized")
        return

    fm = FastMail(conf)
    message = _create_message(subject, recipients, template_vars)
    background_tasks.add_task(fm.send_message, message, template_name=template_name)


def email_terminal_output(email):
    if not settings.SMTP_LOCAL_DEV:
        return

    to = email.get("To")
    from_ = email.get("From")
    body_text = base64.b64decode(email.get_payload(0).get_payload()).decode("utf-8")

    logger.info(
        textwrap.dedent(
            f"""\n
            ## Email dispatched ##
            To:\t{to}
            From:\t{from_}
            Body:\n
            {body_text}
            \n"""
        )
    )


email_dispatched_signal.connect(email_terminal_output)
