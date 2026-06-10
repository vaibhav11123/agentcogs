import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt
from .config import settings


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def key_last4(key: str) -> str:
    return key[-4:] if len(key) >= 4 else key


def issue_jwt(workspace_id: str, email: str) -> str:
    payload = {
        "sub": workspace_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except Exception:
        return None


def generate_api_key() -> str:
    return f"acg_live_{secrets.token_urlsafe(32)}"
