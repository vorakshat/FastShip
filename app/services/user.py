from datetime import timedelta
from typing import Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from passlib.context import CryptContext  # type: ignore
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import app_settings
from app.database.models import User
from app.utils import (
    decode_url_safe_token,
    generate_access_token,
    generate_url_safe_token,
)
from app.worker.tasks import send_email_with_template

from .base import BaseService

password_context = CryptContext(schemes=["bcrypt"])

UserType = TypeVar("UserType", bound=User)

class UserService(BaseService[UserType], Generic[UserType]):
    def __init__(self, model: type[UserType], session: AsyncSession):
        self.model = model
        self.session = session

    async def _add_user(self, data: dict, router_prefix: str) -> UserType:
        user = self.model(
            **data,
            password_hash=password_context.hash(data.pop("password"))
        )

        user = await self._add(user)

        token = generate_url_safe_token(
            {
                "email": user.email,
                "id": str(getattr(user, "id"))  # noqa: B009
            },
            salt="email-verify"
        )

        send_email_with_template.delay(
            recipients=[user.email],
            subject="Verify your account with FastShip",
            context={
                "username": user.name,
                "verification_url": f"http://{app_settings.APP_DOMAIN}/{router_prefix}/verify?token={token}"
            },
            template_name="mail_email_verify.html"
        )

        return user

    async def verify_email(self, token: str):
        token_data = decode_url_safe_token(token, expiry=timedelta(days=1), salt="email-verify")

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )

        user = await self._get(UUID(token_data["id"]))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid User"
            )

        user.email_verified = True

        await self._update(user)

    async def _get_by_email(self, email) -> UserType | None:
        return await self.session.scalar(
            select(self.model).where(self.model.email == email)
        )

    async def _generate_token(self, email, password):
        # Validate the credentials
        user = await self._get_by_email(email)

        if user is None or not password_context.verify(
            password, user.password_hash
        ):
            raise HTTPException(    
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email or password is incorrect",
            )

        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified",
            )
        # seller validated
        # JWT structure -> encoded header.payload.signature, header is basically the algo which we r using, payload can be some user data and signature is the key
        # Note that the token is encoded and not encrypted
        token = generate_access_token(
            data={
                "user": {
                    "name": user.name,
                    "id": str(user.id)
                }
            }
        )

        return token

    async def send_password_reset_link(self, email: EmailStr, router_prefix: str):
        user = await self._get_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User with provided email not found"
            )

        token = generate_url_safe_token({"id": str(getattr(user, "id"))}, salt="password-reset")  # noqa: B009

        send_email_with_template.delay(
            recipients=[user.email],
            subject="Fastship Account Password Reset",
            template_name="mail_password_reset.html",
            context={
                "username": user.name,
                "reset_url": f"http://{app_settings.APP_DOMAIN}{router_prefix}/reset_password_form?token={token}"
            }
        )

    async def reset_password(self, token: str, password: str) -> bool:
        token_data = decode_url_safe_token(
            token=token,
            salt="password-reset",
            expiry=timedelta(days=1)
        )

        if not token_data:
            return False
        
        user = await self._get(UUID(token_data["id"]))

        if not user:
            return False

        user.password_hash = password_context.hash(password)

        await self._update(user)

        return True