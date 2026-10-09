import pytest

from packages.scanners.tools import semgrep


@pytest.mark.integration
async def test_real_semgrep_reports_unsafe_source(tmp_path, monkeypatch):
    monkeypatch.setenv("SHADOWLAB_DATA_DIR", str(tmp_path / "state"))
    (tmp_path / "route.ts").write_text("export function GET(request: Request) { return db.$queryRawUnsafe(request.query); }")
    result = await semgrep(tmp_path)
    assert result["status"] == "completed"
    assert any("unsafe-sql" in f["rule"] and f["line"] == 1 for f in result["findings"])
