import asyncio
import socket

import pytest

from packages.core.models import Settings, SyntheticFixture, Target, TestPlan as Plan
from packages.execution.gateway import Gateway
from packages.policies.engine import PolicyDenied, PolicyEngine


def configured(url="http://127.0.0.1:3001", **overrides):
    return Settings(targets=[Target(url=url, authorized=True, approved=True, allow_loopback=True)],
                    sandbox_mode="trusted-local", **overrides)


@pytest.mark.parametrize("settings", [Settings(), Settings(targets=[Target(url="http://127.0.0.1:3001")]),
    Settings(targets=[Target(url="http://127.0.0.1:3001", authorized=True)], sandbox_mode="trusted-local")])
async def test_deny_default_and_missing_approval(settings):
    with pytest.raises(PolicyDenied):
        await PolicyEngine(settings, "http://127.0.0.1:3001").check(Plan(category="headers", path="/"))


@pytest.mark.parametrize("path", ["//evil.test", "/../x", "/%2fetc", "/x?redirect=bad", "/\\x", "/x\n"])
async def test_path_scope(path):
    with pytest.raises(PolicyDenied):
        await PolicyEngine(configured(), "http://127.0.0.1:3001").check(Plan(category="headers", path=path))


async def test_budget_category_audit_and_exact_port():
    audit = []
    settings = configured(request_budget=1, categories=["headers"])
    policy = PolicyEngine(settings, "http://127.0.0.1:3001", audit=lambda **x: audit.append(x))
    assert await policy.check(Plan(category="headers", path="/")) == "127.0.0.1"
    with pytest.raises(PolicyDenied, match="budget"):
        await policy.check(Plan(category="headers", path="/"))
    assert [e["decision"] for e in audit] == ["allow", "deny"]
    with pytest.raises(PolicyDenied):
        await PolicyEngine(settings, "http://127.0.0.1:3002").check(Plan(category="headers", path="/"))
    with pytest.raises(PolicyDenied, match="category"):
        await PolicyEngine(configured(categories=["headers"]), "http://127.0.0.1:3001").check(Plan(category="bola", path="/"))


async def test_private_and_metadata_denied():
    for url in ("http://169.254.169.254", "http://10.0.0.1", "http://192.168.1.1", "http://[::ffff:127.0.0.1]"):
        with pytest.raises(PolicyDenied):
            await PolicyEngine(configured(url), url).check(Plan(category="headers", path="/"))


async def test_dns_rebinding(monkeypatch):
    loop = asyncio.get_running_loop()
    responses = iter(["93.184.216.34", "93.184.216.35"])
    async def resolve(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (next(responses), 80))]
    monkeypatch.setattr(loop, "getaddrinfo", resolve)
    policy = PolicyEngine(configured("http://example.test"), "http://example.test")
    await policy.check(Plan(category="headers", path="/"))
    with pytest.raises(PolicyDenied, match="DNS changed"):
        await policy.check(Plan(category="headers", path="/"))


@pytest.mark.parametrize("mode", ["redirect", "timeout", "large", "compressed"])
async def test_real_http_redirect_timeout_and_response_budget(mode):
    async def handler(reader, writer):
        try:
            await reader.read(8192)
            if mode == "timeout":
                await asyncio.sleep(0.3)
            elif mode == "redirect":
                writer.write(b"HTTP/1.1 302 Found\r\nLocation: http://169.254.169.254/\r\nContent-Length: 0\r\n\r\n")
            elif mode == "compressed":
                import gzip
                body = gzip.compress(b"x" * 1_000_000)
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\nContent-Length: "
                             + str(len(body)).encode() + b"\r\n\r\n" + body)
            else:
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 70000\r\n\r\n" + b"x" * 70000)
            await writer.drain()
        finally:
            writer.close()
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    url = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}"
    try:
        gateway = Gateway(PolicyEngine(configured(url, timeout_seconds=0.1), url), asyncio.Event())
        with pytest.raises((PolicyDenied, TimeoutError, __import__("httpx").TimeoutException)):
            await gateway.request(Plan(category="headers", path="/"))
    finally:
        server.close()
        await server.wait_closed()


async def test_cancellation_and_fixture_requirements():
    cancellation = asyncio.Event()
    cancellation.set()
    with pytest.raises(asyncio.CancelledError):
        await Gateway(PolicyEngine(configured(), "http://127.0.0.1:3001"), cancellation).request(Plan(category="headers", path="/"))
    with pytest.raises(PolicyDenied, match="fixture"):
        await PolicyEngine(configured(), "http://127.0.0.1:3001").check(Plan(category="bola", path="/", identity="other"))
    with pytest.raises(ValueError):
        SyntheticFixture(owner_token="same", other_token="same")
