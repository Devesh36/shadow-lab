import asyncio
import json
import time

import httpx

from packages.core.models import TestPlan
from packages.evidence.sanitize import response_body, sensitive_keys
from packages.policies.engine import PolicyDenied, PolicyEngine


class Gateway:
    """Bounded GET-only tools. The model never receives a shell or HTTP client."""

    def __init__(self, policy: PolicyEngine, cancelled: asyncio.Event):
        self.policy = policy
        self.cancelled = cancelled
        self.last_request = 0
        self.lock = asyncio.Lock()

    async def request(self, plan: TestPlan):
        async with self.lock:
            if self.cancelled.is_set():
                raise asyncio.CancelledError
            await asyncio.sleep(max(0, 1 / self.policy.settings.requests_per_second
                                    - (time.monotonic() - self.last_request)))
            if self.cancelled.is_set():
                raise asyncio.CancelledError
            ip = await self.policy.check(plan)
            scheme, host, port = self.policy.target
            original = httpx.URL(f"{scheme}://{host}:{port}{plan.path}")
            pinned = original.copy_with(host=ip)
            headers = {"Host": original.netloc.decode(), "Accept": "application/json", "Accept-Encoding": "identity"}
            fixture = self.policy.settings.fixture
            if plan.identity != "anonymous":
                token = fixture.owner_token if plan.identity == "owner" else fixture.other_token
                headers["Authorization"] = f"Bearer {token}"
            self.last_request = time.monotonic()
            # Direct connections use the validated IP, never a second DNS lookup or a proxy.
            async with asyncio.timeout(self.policy.settings.timeout_seconds):
                async with httpx.AsyncClient(trust_env=False, follow_redirects=False,
                                             timeout=self.policy.settings.timeout_seconds) as client:
                    async with client.stream("GET", pinned, headers=headers,
                                             extensions={"sni_hostname": host}) as response:
                        if 300 <= response.status_code < 400:
                            raise PolicyDenied("Redirects are denied, including in-scope redirects")
                        if response.headers.get("content-encoding", "identity").lower() != "identity":
                            raise PolicyDenied("Encoded responses are denied to bound decompression memory")
                        raw = bytearray()
                        async for chunk in response.aiter_raw(chunk_size=16384):
                            if self.cancelled.is_set():
                                raise asyncio.CancelledError
                            raw.extend(chunk)
                            if len(raw) > 65536:
                                raise PolicyDenied("Response exceeds 64 KiB evidence budget")
                        try:
                            fields = sensitive_keys(json.loads(raw))
                        except (ValueError, UnicodeDecodeError):
                            fields = []
                        return {"method": "GET", "path": plan.path, "identity": plan.identity,
                                "status": response.status_code, "body": response_body(bytes(raw)),
                                "sensitive_fields": sorted(set(fields)),
                                "security_headers": {k: response.headers.get(k) for k in (
                                    "content-security-policy", "x-content-type-options",
                                    "referrer-policy", "strict-transport-security")}}
