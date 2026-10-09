import json
import re
import subprocess
from pathlib import Path

import tree_sitter_typescript as ts
from tree_sitter import Language, Parser

from packages.core.models import Route, SourceRef

IGNORED = {".git", "node_modules", ".next", ".venv", ".shadowlab", "dist", "build"}


def safe_files(root: Path):
    # No symlink following, no dependency/build traversal, bounded repository analysis.
    count = 0
    pending = [root]
    while pending:
        directory = pending.pop()
        for item in sorted(directory.iterdir()):
            if item.is_symlink() or item.name in IGNORED:
                continue
            if item.is_dir():
                pending.append(item)
            elif item.is_file():
                count += 1
                if count > 10000:
                    raise ValueError("Repository exceeds 10,000-file analysis budget")
                yield item


def discover(root: Path):
    root = root.resolve(strict=True)
    parser = Parser(Language(ts.language_tsx()))
    routes = []
    middleware = []
    actions = []
    parse_errors = []
    for file in safe_files(root):
        if file.suffix not in {".ts", ".tsx", ".js", ".jsx"} or file.stat().st_size > 1_000_000:
            continue
        relative = file.relative_to(root).as_posix()
        source = file.read_text(errors="replace")
        tree = parser.parse(source.encode())
        if tree.root_node.has_error:
            parse_errors.append(relative)
        if file.stem == "middleware":
            middleware.append(relative)
        if re.search(r"['\"]use server['\"]", source):
            actions.append(relative)
        parts = list(file.relative_to(root).parts)
        router = "app" if "app" in parts else "pages" if "pages" in parts else None
        if not router:
            continue
        relevant = parts[parts.index(router) + 1:]
        stem = file.stem
        if router == "app" and stem not in {"route", "page"}:
            continue
        if router == "pages" and (stem.startswith("_") or not relevant):
            continue
        segments = relevant[:-1] if router == "app" or stem == "index" else [*relevant[:-1], stem]
        segments = [s for s in segments if not s.startswith("(") and not s.startswith("@")]
        path = "/" + "/".join(segments)
        methods = re.findall(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b", source)
        methods += re.findall(r"export\s+const\s+(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b", source)
        if router == "pages" and relevant[0] == "api":
            methods = re.findall(r"(?:req|request)\.method\s*===?\s*['\"]([A-Z]+)['\"]", source) or ["UNKNOWN"]
        methods = sorted(set(methods)) or ["GET"]
        # Tree-sitter establishes source locations, framework adapters classify patterns heuristically.
        first_export = next((n for n in tree.root_node.children if n.type == "export_statement"), None)
        line = first_export.start_point.row + 1 if first_export else 1
        routes.append(Route(path=path, methods=methods, source=SourceRef(file=relative, line=line), router=router,
                            authentication_observed=bool(re.search(r"getServerSession\(|auth\(|getSession\(|requireAuth\(|session\.user", source)),
                            ownership_observed=bool(re.search(r"ownerId\s*!==|userId\s*!==|ownerId:\s*(?:user|session)|where:.*userId", source)),
                            inputs=sorted({a or b for a, b in re.findall(r"(?:request|req)\.(json|body|query|params|headers)|\b(params|searchParams)\b", source)}),
                            database_calls=sorted(set(re.findall(r"\.(findMany|findUnique|query|execute|findFirst|\$queryRawUnsafe)\b", source))),
                            sensitive_fields=sorted(set(re.findall(r"\b(password|passwordHash|apiKey|secret|accessToken)\b", source))),
                            environment_variables=sorted(set(re.findall(r"process\.env\.([A-Z_][A-Z_0-9]*)", source))),
                            server_action=relative in actions))
    manifest = root / "package.json"
    dependencies = {}
    if manifest.is_file() and not manifest.is_symlink() and manifest.stat().st_size < 1_000_000:
        package = json.loads(manifest.read_text())
        dependencies = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    return {"routes": [r.model_dump() for r in routes], "middleware": middleware,
            "server_actions": actions, "dependencies": dependencies, "parse_errors": parse_errors,
            "commit": commit.stdout.strip() if commit.returncode == 0 else None,
            "analysis_limitations": "Framework patterns are heuristic; middleware, imported helpers, aliases, roles, and data flows need review.",
            "graph": {"nodes": [{"id": r.path, "kind": "route", "source": r.source.model_dump(),
                                 "authentication_observed": r.authentication_observed,
                                 "sensitive_resources": r.sensitive_fields} for r in routes],
                      "edges": [{"from": r.path, "to": r.source.file, "relation": "implemented_by"} for r in routes]}}
