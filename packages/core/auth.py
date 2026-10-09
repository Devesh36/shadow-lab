import os
import secrets
from pathlib import Path


def api_token(data_dir: Path):
    configured = os.getenv("SHADOWLAB_API_TOKEN")
    if configured:
        if len(configured) < 24:
            raise ValueError("SHADOWLAB_API_TOKEN must contain at least 24 characters")
        return configured
    token_file = data_dir / "api-token"
    if token_file.is_symlink():
        raise ValueError("Token file must not be a symlink")
    try:
        descriptor = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        token = token_file.read_text().strip()
        if len(token) < 24:
            raise ValueError("Stored API token is invalid; configure SHADOWLAB_API_TOKEN securely")
        return token
    token = secrets.token_urlsafe(32)
    with os.fdopen(descriptor, "w") as file:
        file.write(token)
    return token
