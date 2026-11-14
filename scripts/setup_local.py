"""Run locally once. Never send generated tokens to logs/shared transcripts."""
import hashlib
import json
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
token = secrets.token_urlsafe(32)
digest = hashlib.sha256(token.encode()).hexdigest()
text = (root / ".env.example").read_text()
text = text.replace("AUTH_TOKEN_HASHES={}", "AUTH_TOKEN_HASHES='" + json.dumps({"local": digest}) + "'")
text = text.replace("DEBUG=true", "DEBUG=false")
try:
    fd = os.open(root / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit(".env already exists. Preserve it; follow SECURITY.md for manual configuration.")
with os.fdopen(fd, "w") as stream:
    stream.write(text)
print("Created private .env. Configure your own model key there before normal use.")
print("Save this local access token in your password manager; paste into the browser login:")
print(token)
