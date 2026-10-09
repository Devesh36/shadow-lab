import httpx


async def passive_alerts(daemon_url: str, api_key: str, target: str):
    """Optional trusted ZAP daemon adapter. Never starts an active scan or spider.

    Called only by an operator, outside the agent tool set. The daemon must already
    have captured traffic for the target in an isolated, authorized environment.
    """
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        result = await client.get(daemon_url.rstrip("/") + "/JSON/core/view/alerts/",
                                  params={"apikey": api_key, "baseurl": target, "start": 0, "count": 100})
        result.raise_for_status()
        # Only metadata is returned; attack payloads and raw responses are not retained.
        return [{key: alert.get(key) for key in ("name", "risk", "confidence", "cweid")}
                for alert in result.json().get("alerts", [])]
