"""Small deployment: per-user opaque tokens, hashes only in server configuration."""
import hashlib
import hmac
import re
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings

bearer = HTTPBearer(auto_error=False)

def validate_auth_config():
    values = settings.auth_token_hashes
    if not values or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", k) or
                         not re.fullmatch(r"[0-9a-f]{64}", v) for k, v in values.items()):
        raise RuntimeError("Set AUTH_TOKEN_HASHES to owner -> SHA256 token hashes; see SECURITY.md")
    if len(set(values.values())) != len(values):
        raise RuntimeError("Each owner must have a unique token")

def current_owner(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if credentials and len(credentials.credentials) <= 512:
        digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        for owner, expected in settings.auth_token_hashes.items():
            if hmac.compare_digest(digest, expected):
                return owner
    raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
