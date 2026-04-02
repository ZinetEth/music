import base64
import hashlib
import hmac
import json
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.settings import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _json_dumps(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def create_access_token(user_id: int, expires_in_seconds: int | None = None) -> str:
    settings = get_settings()
    now = int(time.time())
    ttl = expires_in_seconds or settings.access_token_ttl_seconds
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "exp": now + ttl,
        "iat": now,
        "sub": str(user_id),
        "type": "access",
    }

    encoded_header = _b64url_encode(_json_dumps(header))
    encoded_payload = _b64url_encode(_json_dumps(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    encoded_signature = _b64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(token: str) -> dict:
    settings = get_settings()

    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token format") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    try:
        provided_signature = _b64url_decode(encoded_signature)
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token payload") from exc

    if not hmac.compare_digest(provided_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    exp = payload.get("exp")
    sub = payload.get("sub")
    token_type = payload.get("type")

    if token_type != "access" or not isinstance(sub, str):
        raise HTTPException(status_code=401, detail="Invalid token claims")
    if not isinstance(exp, int) or exp <= int(time.time()):
        raise HTTPException(status_code=401, detail="Token has expired")

    return payload


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = decode_access_token(credentials.credentials)
    try:
        return int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc
