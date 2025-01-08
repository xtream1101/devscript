# from blinker import ANY, signal
import base64
import textwrap

from fastapi import BackgroundTasks
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from fastapi_mail.fastmail import email_dispatched as email_dispatched_signal
from loguru import logger

from app.settings import settings

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
    TEMPLATE_FOLDER="app/common/templates/email/",
    MAIL_DEBUG=settings.SMTP_DEBUG,
    SUPPRESS_SEND=settings.SMTP_LOCAL_DEV,
)


async def send_email_async(subject: str, email_to: str, body: dict):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype="html",
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name="index.html")


def send_email_background(
    background_tasks: BackgroundTasks, subject: str, email_to: str, body: dict
):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype="html",
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message, template_name="index.html")


def email_dispatched(email):
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


email_dispatched_signal.connect(email_dispatched)
