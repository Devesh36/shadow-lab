import argparse
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(prog="shadow", description="Evidence-driven application security testing")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    analyze = commands.add_parser("analyze")
    analyze.add_argument("path")
    scan = commands.add_parser("scan")
    scan.add_argument("--repository", default="examples/vulnerable-nextjs")
    scan.add_argument("--target")
    scan.add_argument("--authorize", action="store_true", help="Explicit permission to test this exact origin")
    scan.add_argument("--approve", action="store_true", help="Approve bounded execution against a trusted app")
    scan.add_argument("--demo-fixtures", action="store_true", help="Use only the shipped demo's synthetic tokens")
    scan.add_argument("--browser", action="store_true", help="Validate the reviewed local demo with three isolated browser identities")
    findings = commands.add_parser("findings")
    findings.add_argument('--project', nargs='?', const='.', help='Read the latest private project scan (default path: launch directory)')
    export = commands.add_parser("report")
    export.add_argument("--scan-id")
    export.add_argument("--format", choices=["markdown", "json"], default="markdown")
    export.add_argument('--project', nargs='?', const='.', help='Read a private project scan instead of operator state')
    commands.add_parser("doctor")
    commands.add_parser("repl", help="Open the guided ShadowLab console")
    demo = commands.add_parser('demo', help='Run the project walkthrough or explicitly choose the bundled demo')
    demo.add_argument('path', nargs='?', help='Project path (default: launch directory)')
    demo.add_argument('--bundled', action='store_true', help='Use the reviewed synthetic app, not a source project')
    demo.add_argument('--browser', action='store_true', help='Add isolated browser checks; requires --bundled')
    argv = sys.argv[1:] or ['repl']
    if argv and argv[0].casefold() == "repl":
        argv[0] = "repl"
    args = parser.parse_args(argv)
    if args.command == "repl":
        from packages.core.repl import run
        run()
        return
    if args.command == 'demo' or getattr(args, 'project', None) is not None:
        if args.command == 'demo' and args.browser and not args.bundled:
            parser.error('--browser requires --bundled; arbitrary-project browser adapters are unsupported')
        if args.command == 'demo' and args.bundled and args.path is not None:
            parser.error('A project path cannot be combined with --bundled')
        from packages.core.repl_commands import display
        try:
            if args.command == 'demo' and args.bundled:
                from packages.core.repl import run_bundled_demo
                run_bundled_demo(browser=args.browser)
            else:
                from packages.core.project import ProjectSession
                from packages.core.project_demo import run_project_demo
                path = args.path if args.command == 'demo' else args.project
                project = ProjectSession(str(Path(path).expanduser().absolute()) if path else os.getcwd())
                try:
                    if args.command == 'demo':
                        run_project_demo(project)
                    elif args.command == 'findings':
                        if not project.scan_id:
                            raise ValueError('No project scans available; run shadow demo first')
                        print(json.dumps(project.findings, indent=2))
                    else:
                        from packages.core.report import report
                        if args.scan_id:
                            if not project.store.get('scan', args.scan_id):
                                raise ValueError('Scan is not available in this project')
                            project.scan_id = args.scan_id
                        if not project.scan_id:
                            raise ValueError('No project scans available; run shadow demo first')
                        print(report(project.store, project.scan_id, args.format))
                finally:
                    project.close()
        except KeyboardInterrupt:
            parser.exit(130, 'Demo cancelled; coverage is incomplete. Owned processes stopped.\n')
        except Exception as exc:
            detail = display(exc) if isinstance(exc, (ValueError, OSError, TimeoutError)) else type(exc).__name__
            parser.exit(2, 'Demo incomplete: ' + detail + '\n')
        return
    from packages.agents.workflow import Workflow
    from packages.analyzers.nextjs import discover
    from packages.core.auth import api_token
    from packages.core.models import RepositoryCreate, ScanCreate, Settings, SyntheticFixture, Target
    from packages.core.report import report
    from packages.core.service import Service
    from packages.db.store import Store
    store = Store()
    store.initialize()
    try:
        if args.command == "init":
            api_token(store.data_dir)
            if not store.get("settings", "settings"):
                store.save_settings(Settings())
            print(f"Initialized {store.data_dir}; execution permissions are managed in saved settings.")
        elif args.command == "analyze":
            repo = Service(store).add_repository(RepositoryCreate(path=args.path))
            print(json.dumps(discover(Path(repo["path"])), indent=2))
        elif args.command == "scan":
            service = Service(store)
            repo = service.add_repository(RepositoryCreate(path=args.repository))
            if args.target and args.authorize and args.approve:
                settings = store.settings()
                target = Target(url=args.target, authorized=True, approved=True,
                                allow_loopback=args.demo_fixtures)
                settings.targets = [t for t in settings.targets if str(t.url) != str(target.url)] + [target]
                settings.sandbox_mode = "trusted-local"
                if args.demo_fixtures:
                    settings.fixture = SyntheticFixture()
                store.save_settings(settings)
            scan = service.create_scan(ScanCreate(repository_id=repo["id"], target=args.target,
                                                  dynamic=bool(args.target), browser=args.browser))
            asyncio.run(Workflow(store, scan["id"]).run())
            result = store.get("scan", scan["id"])
            print(json.dumps(result, indent=2))
            if result["status"] != "completed":
                raise SystemExit(1)
        elif args.command == "findings":
            print(json.dumps(store.list("finding"), indent=2))
        elif args.command == "report":
            scans = store.list("scan")
            if not args.scan_id and not scans:
                raise ValueError("No scans available")
            print(report(store, args.scan_id or scans[-1]["id"], args.format))
        elif args.command == "doctor":
            from packages.core.doctor import launcher_checks
            def present(tool):
                return bool(shutil.which(tool) or Path(sys.executable).with_name(tool).is_file()
                            or (store.data_dir / "tools" / tool).is_file())
            print(json.dumps({"database": "connected" if store.list("repository") is not None else "failed",
                              "tools": {t: present(t) for t in ("git", "node", "semgrep", "osv-scanner", "docker", "chromium")},
                              "llm_key_configured": bool(os.getenv("SHADOWLAB_LLM_API_KEY")),
                              "mode": store.settings().sandbox_mode,
                              "launcher": launcher_checks()}, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
