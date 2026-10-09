from packages.core.models import Settings, SyntheticFixture, Target
from packages.policies.engine import PolicyDenied, origin


def demo_settings(target):
    scheme, host, _ = origin(target)
    if scheme != "http" or host != "127.0.0.1":
        raise PolicyDenied("The guided demo supports only the bundled IPv4 loopback HTTP application")
    return Settings(targets=[Target(url=target, authorized=True, approved=True, allow_loopback=True)],
                    sandbox_mode="trusted-local", fixture=SyntheticFixture(),
                    categories=["authentication", "bola", "exposure", "headers"],
                    request_budget=150, timeout_seconds=10, scan_timeout_seconds=180, requests_per_second=5)
