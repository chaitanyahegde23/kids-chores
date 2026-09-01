import hashlib
import hmac
import secrets
import time
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import HouseholdSecurity

PARENT_COOKIE = "kids_chores_parent"


def verify_pin(candidate: str, expected: str) -> bool:
    return hmac.compare_digest(candidate.encode(), expected.encode())


def _pin_digest(pin: str, salt: bytes) -> str:
    return hashlib.scrypt(pin.encode(), salt=salt, n=2**14, r=8, p=1).hex()


def verify_configured_pin(session: Session, candidate: str, fallback_pin: str) -> bool:
    override = session.scalar(select(HouseholdSecurity).limit(1))
    if override is None:
        return verify_pin(candidate, fallback_pin)
    try:
        salt = bytes.fromhex(override.pin_salt)
    except ValueError:
        return False
    return hmac.compare_digest(_pin_digest(candidate, salt), override.pin_hash)


def change_configured_pin(session: Session, new_pin: str) -> None:
    salt = secrets.token_bytes(16)
    override = session.scalar(select(HouseholdSecurity).limit(1))
    if override is None:
        override = HouseholdSecurity(pin_salt=salt.hex(), pin_hash=_pin_digest(new_pin, salt))
        session.add(override)
    else:
        override.pin_salt = salt.hex()
        override.pin_hash = _pin_digest(new_pin, salt)
    session.commit()


def create_parent_token(settings: Settings) -> str:
    expires = str(int(time.time()) + settings.parent_session_seconds)
    nonce = secrets.token_urlsafe(18)
    payload = f"{expires}.{nonce}"
    signature = hmac.new(
        settings.session_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{signature}"


def verify_parent_token(token: str | None, settings: Settings) -> bool:
    if not token:
        return False
    try:
        expires, nonce, signature = token.split(".", maxsplit=2)
        if int(expires) < int(time.time()):
            return False
    except (TypeError, ValueError):
        return False
    payload = f"{expires}.{nonce}"
    expected = hmac.new(
        settings.session_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def require_parent(
    settings: SettingsDependency,
    parent_cookie: Annotated[str | None, Cookie(alias=PARENT_COOKIE)] = None,
) -> None:
    if not verify_parent_token(parent_cookie, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Parent PIN required")
