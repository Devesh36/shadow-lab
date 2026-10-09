import json

from packages.agents.workflow import classify
from packages.core.models import FindingState
from packages.evidence.sanitize import response_body, sanitize


def test_recursive_redaction_and_nonjson_omission():
    data = {"passwordHash": "abc", "nested": [{"apiKey": "def"}], "note": "Bearer sensitive"}
    sanitized = response_body(json.dumps(data).encode())
    assert sanitized["passwordHash"] == "[REDACTED]"
    assert sanitized["nested"][0]["apiKey"] == "[REDACTED]"
    assert "sensitive" not in json.dumps(sanitized)
    assert "secret" not in str(response_body(b"<html>secret</html>"))
    assert len(sanitize("x" * 10000)) == 4096


def response(owner, id, status=200):
    return {"status": status, "body": {"ownerId": owner, "id": id}}


def test_bola_requires_distinct_baseline_and_same_resource():
    owner = response("alice", "alice-record")
    bob = response("bob", "bob-record")
    assert classify("bola", [owner, bob, owner])[0] == FindingState.CONFIRMED
    assert classify("bola", [owner, owner, owner])[0] == FindingState.INCONCLUSIVE
    assert classify("bola", [owner, bob, bob])[0] == FindingState.INCONCLUSIVE
    assert classify("bola", [owner, bob, response("", "", 403)])[0] == FindingState.NOT_REPRODUCED
    assert classify("authentication", [owner, owner])[0] == FindingState.CONFIRMED


def test_generic_success_does_not_confirm_access():
    assert classify("authentication", [{"status": 200, "body": {"ok": True}}] * 2)[0] == FindingState.INCONCLUSIVE
