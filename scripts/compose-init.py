"""Generate a local API token without exposing it or replacing configured values."""
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = root / ".env"
if env.is_symlink():
    raise SystemExit("Refusing to modify a symlink")
text = env.read_text() if env.exists() else ""
lines = text.splitlines()
found = False
for index, line in enumerate(lines):
    if line.startswith("SHADOWLAB_API_TOKEN="):
        found = True
        if not line.partition("=")[2].strip():
            lines[index] = "SHADOWLAB_API_TOKEN=" + secrets.token_urlsafe(32)
if not found:
    lines.append("SHADOWLAB_API_TOKEN=" + secrets.token_urlsafe(32))
if not env.exists():
    descriptor = os.open(env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as file:
        file.write("\n".join(lines) + "\n")
elif "\n".join(lines) + "\n" != text:
    env.write_text("\n".join(lines) + "\n")
print("Local API token configured in .env; existing nonempty values preserved.")
