"""Bound request bodies before the multipart parser spools data to disk."""
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from app.core.auth import current_owner
from app.core.config import settings


class UploadGuard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/api/v1/documents/upload":
            return await self.app(scope, receive, send)
        scheme, _, token = Headers(scope=scope).get("authorization", "").partition(" ")
        try:
            current_owner(HTTPAuthorizationCredentials(scheme=scheme, credentials=token)
                          if scheme.lower() == "bearer" and token else None)
        except HTTPException:
            return await JSONResponse({"detail": "Authentication required"}, 401,
                headers={"WWW-Authenticate": "Bearer"})(scope, receive, send)
        # Small multipart envelope allowance in addition to the file's stricter limit.
        limit = settings.max_upload_bytes + 64 * 1024
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > limit:
                return await JSONResponse({"detail": "Request body too large"}, 413)(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}
        await self.app(scope, bounded_receive, send)
