from fastapi import BackgroundTasks
from fastapi_mail import (
    ConnectionConfig,
    FastMail,
    MessageSchema,
    MessageType,
    NameEmail,
)
from pydantic import EmailStr
from twilio.http.async_http_client import AsyncTwilioHttpClient  # type: ignore
from twilio.rest import Client  # type: ignore

from app.config import notification_settings
from app.utils import TEMPLATE_DIR


class NotificationService:
    def __init__(self, tasks: BackgroundTasks):
        self.tasks = tasks
        self.fastmail = FastMail(
            ConnectionConfig(
                **notification_settings.model_dump(
                    exclude={"TWILIO_SID", "TWILIO_AUTH_TOKEN", "TWILIO_NUMBER"}
                ),
                TEMPLATE_FOLDER=TEMPLATE_DIR,
            )
        )
        async_http_client = AsyncTwilioHttpClient()

        self.twilio_client = Client(
            notification_settings.TWILIO_SID,
            notification_settings.TWILIO_AUTH_TOKEN,
            http_client=async_http_client
        )


    async def send_email(
        self,
        recipients: list[EmailStr],
        subject: str,
        body: str,
    ):
        # Convert EmailStr items into NameEmail objects
        name_email_recipients = [
            NameEmail(name="", email=email) for email in recipients
        ]

        self.tasks.add_task(
            self.fastmail.send_message,
            message=MessageSchema(
                recipients=name_email_recipients,
                subject=subject,
                body=body,
                subtype=MessageType.plain,
            )
        )

    async def send_email_with_template(
        self,
        recipients: list[EmailStr],
        subject: str,
        context: dict,
        template_name: str,
    ):
        # Convert EmailStr items into NameEmail objects
        name_email_recipients = [
            NameEmail(name="", email=email) for email in recipients
        ]
        
        self.tasks.add_task(
            self.fastmail.send_message,
            message=MessageSchema(
                recipients=name_email_recipients,
                subject=subject,
                template_body=context,
                subtype=MessageType.html,
            ),
            template_name=template_name            
        )

    async def send_sms(self, to: str, body: str):
        await self.twilio_client.messages.create_async(
            from_=notification_settings.TWILIO_NUMBER,
            to=to,
            body=body
        )
    