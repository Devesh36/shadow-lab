import json
from pathlib import Path

from packages.analyzers.nextjs import discover
from packages.core.models import RepositoryCreate
from packages.core.service import Service


def test_nextjs_app_and_pages_routes(tmp_path):
    files = {
        "src/app/(private)/api/items/[id]/route.ts": "export const GET = async (request: Request) => { const user = requireAuth(request); return Response.json(await db.findUnique(request.params)); };",
        "pages/api/search.ts": "export default function handler(req, res) { if (req.method === 'POST') return res.json(req.body); }",
        "app/actions.ts": "'use server'; export async function save() { return process.env.DATABASE_URL; }",
        "middleware.ts": "export function middleware(request) { return request; }",
        "node_modules/app/api/ignored/route.ts": "export function GET() {}",
        "package.json": json.dumps({"dependencies": {"next": "16.2.1"}}),
    }
    for name, source in files.items():
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(source)
    (tmp_path / "app/api/leak").parent.mkdir(parents=True)
    (tmp_path / "app/api/leak").symlink_to(Path("/etc"), target_is_directory=True)
    result = discover(tmp_path)
    assert {r["path"] for r in result["routes"]} == {"/api/items/[id]", "/api/search"}
    item = next(r for r in result["routes"] if "items" in r["path"])
    assert item["authentication_observed"] and item["database_calls"] == ["findUnique"]
    assert item["source"]["line"] == 1
    assert result["middleware"] == ["middleware.ts"]
    assert result["server_actions"] == ["app/actions.ts"]
    assert result["dependencies"]["next"] == "16.2.1"


def test_repository_scope_and_deduplication(store):
    service = Service(store)
    first = service.add_repository(RepositoryCreate(path="examples/vulnerable-nextjs"))
    assert service.add_repository(RepositoryCreate(path=first["path"]))["id"] == first["id"]
    import pytest
    with pytest.raises(ValueError):
        service.add_repository(RepositoryCreate(path="/etc"))
