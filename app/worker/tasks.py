from time import sleep

from asgiref.sync import async_to_sync
from celery import Celery
from fastapi_mail import (
    ConnectionConfig,
    FastMail,
    MessageSchema,
    MessageType,
    NameEmail,
)
from pydantic import EmailStr
from twilio.rest import Client  # type: ignore[import-untyped]

from app.config import database_settings, notification_settings
from app.utils import TEMPLATE_DIR

app = Celery(
    "api tasks",
    broker=database_settings.REDIS_URL(9),
    backend=database_settings.REDIS_URL(9)
)

# 2. Instantiate the Twilio client
twilio_client = Client(
    notification_settings.TWILIO_SID,
    notification_settings.TWILIO_AUTH_TOKEN
)

fast_mail = FastMail(
    ConnectionConfig(
        **notification_settings.model_dump(
            exclude={"TWILIO_SID", "TWILIO_AUTH_TOKEN", "TWILIO_NUMBER"}
        ),
        TEMPLATE_FOLDER=TEMPLATE_DIR,
    )
)

send_message = async_to_sync(fast_mail.send_message)

@app.task
def send_mail(
    recipients: list[EmailStr],
    subject: str,
    body: str
):
    name_email_recipients = [
        NameEmail(name="", email=email) for email in recipients
    ]

    send_message(MessageSchema(
        recipients=name_email_recipients,
        subject=subject,
        body=body,
        subtype=MessageType.plain
    ))

@app.task
def send_email_with_template(
    recipients: list[EmailStr],
    subject: str,
    context: dict,
    template_name: str,
):
    name_email_recipients = [
        NameEmail(name="", email=email) for email in recipients
    ]
    
    send_message(
        message=MessageSchema(
            recipients=name_email_recipients,
            subject=subject,
            template_body=context,
            subtype=MessageType.html,
        ),
        template_name=template_name            
    )

# 3. Add task-level retries & error handling for network resilience
@app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_sms(self, to: str, body: str):
    try:
        message = twilio_client.messages.create(
            from_=notification_settings.TWILIO_NUMBER,
            to=to,
            body=body,
        )
        return message.sid
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)

@app.task
def background_task(name: str, data: dict):
    sleep(5)
    return name