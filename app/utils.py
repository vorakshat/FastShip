from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import (
    uuid4,  # Unique id for each token to be used when we add them to the blacklist
)

import jwt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import security_settings

_serializer = URLSafeTimedSerializer(security_settings.JWT_SECRET)   # Use to generate token for email verification of user
# Url safe means it can be added in the url , i.e special characters wont bother us, time means we can add age to it before expiration

APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_DIR.joinpath("templates")


def generate_access_token(data: dict, expiry: timedelta = timedelta(days=1)) -> str:
    return jwt.encode(
        algorithm=security_settings.JWT_ALGORITHM,
        payload={
            **data,
            "jti": str(uuid4()),
            "exp": datetime.now(timezone.utc) + expiry   # Tells (decoder) when the token will expire  
        },
        key=security_settings.JWT_SECRET
    )

def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            jwt=token,
            key=security_settings.JWT_SECRET,
            algorithms=[security_settings.JWT_ALGORITHM]
        )
    except jwt.PyJWTError:
        return None

def generate_url_safe_token(data: dict, salt: str | None = None) -> str:
    # generate a token
    return _serializer.dumps(data, salt=salt)

def decode_url_safe_token(token: str, expiry: timedelta | None = None, salt: str | None = None) -> dict | None:
    try:
        return _serializer.loads(
            token,
            max_age=int(expiry.total_seconds()) if expiry else None,
            salt=salt
        )
    except(BadSignature, SignatureExpired):
        return None