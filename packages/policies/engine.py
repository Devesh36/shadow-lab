import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

from packages.core.models import Settings, TestPlan


class PolicyDenied(ValueError):
    pass


def origin(url: str):
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise PolicyDenied("Only credential-free HTTP(S) origins are allowed")
    if parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise PolicyDenied("Target must be an origin")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.scheme, parsed.hostname.lower(), port


class PolicyEngine:
    def __init__(self, settings: Settings, target: str, audit=None):
        self.settings = settings
        self.target = origin(target)
        self.scope = next((t for t in settings.targets if origin(str(t.url)) == self.target), None)
        self.used = 0
        self.addresses = None
        self.audit = audit or (lambda **kwargs: None)

    async def check(self, plan: TestPlan):
        try:
            if self.settings.sandbox_mode != "trusted-local":
                raise PolicyDenied("Dynamic testing requires trusted-local mode; untrusted code needs a VM")
            if not self.scope or not self.scope.authorized:
                raise PolicyDenied("Target is not explicitly authorized")
            if not self.scope.approved:
                raise PolicyDenied("Target execution approval is required")
            if plan.category not in self.settings.categories:
                raise PolicyDenied("Test category is denied")
            if self.used >= self.settings.request_budget:
                raise PolicyDenied("Request budget exhausted")
            if (not plan.path.startswith("/") or plan.path.startswith("//") or ".." in plan.path
                    or "\\" in plan.path or "%" in plan.path or "?" in plan.path or "#" in plan.path
                    or any(ord(c) < 32 for c in plan.path)):
                raise PolicyDenied("Unsafe test path")
            if plan.identity != "anonymous" and not self.settings.fixture:
                raise PolicyDenied("Synthetic test fixture is required")
            host = self.target[1]
            loop = asyncio.get_running_loop()
            records = await loop.getaddrinfo(host, self.target[2], type=socket.SOCK_STREAM)
            addresses = frozenset(r[4][0] for r in records)
            if not addresses:
                raise PolicyDenied("Target DNS returned no addresses")
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if ip.is_loopback and self.scope.allow_loopback:
                    continue
                if not ip.is_global:
                    raise PolicyDenied("Private, link-local, metadata, and reserved destinations are denied")
            if self.addresses is not None and self.addresses != addresses:
                raise PolicyDenied("DNS changed during execution")
            self.addresses = addresses
            self.used += 1
            self.audit(decision="allow", plan=plan.model_dump(), request_number=self.used)
            return sorted(addresses)[0]
        except (ValueError, OSError) as exc:
            self.audit(decision="deny", reason=str(exc), plan=plan.model_dump())
            raise PolicyDenied(str(exc)) from exc
