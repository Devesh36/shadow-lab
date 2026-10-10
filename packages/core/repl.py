"""Small guided console. Commands are fixed actions, never Python or shell evaluation."""
import os
import shlex
import time
import webbrowser
from collections import Counter

from packages.core.demo_runtime import DemoRuntime
from packages.core.doctor import show_setup
from packages.core.project import ProjectSession
from packages.core.repl_commands import COMMANDS, canonical, display, interactive, show_help, terminal_input, unknown, validate

MENU = "1  Demo     2  Check setup     /init     /project PATH     /help     /quit"


def run(input_fn=input, output=None, runtime_factory=DemoRuntime, project_factory=ProjectSession):
    output = output or (lambda message: print(message, flush=True))
    with terminal_input(interactive(input_fn)):
        return console(input_fn, output, runtime_factory, project_factory)


def console(input_fn, output, runtime_factory, project_factory):
    output("ShadowLab — evidence-driven security investigations")
    output(MENU)
    output('Type /help to explore commands. Start with /demo or /init. Ctrl+C cancels active work.')
    runtime = None
    scan = None
    findings = []
    project = None
    try:
        while True:
            try:
                prompt = 'shadow[project]> ' if project else 'shadow[demo]> ' if runtime else 'shadow> '
                words = shlex.split(input_fn(prompt).strip())
            except ValueError:
                output('Unclosed quote. Use project "My Project" for paths with spaces.')
                continue
            except (EOFError, KeyboardInterrupt):
                output("\nClosing ShadowLab.")
                break
            if not words:
                continue
            command = canonical(words[0])
            if command not in COMMANDS:
                unknown(command, output)
                continue
            if not validate(command, words[1:]):
                output('Use /' + COMMANDS[command].usage + '. Type /help ' + command + ' for details.')
                continue
            if command == 'init':
                command, words = 'project', ['project', '.']
            if command == 'quit':
                break
            if command == 'help':
                show_help(output, words[1] if len(words) == 2 else None)
                continue
            if command == 'clear':
                output('\033[2J\033[H' if interactive(input_fn) and os.getenv('TERM') != 'dumb'
                       else 'Display clearing is available in an interactive terminal. Session and results retained.')
                continue
            if command == 'doctor':
                show_setup(output)
                continue
            if command == "stop":
                if runtime:
                    runtime.close()
                    runtime = None
                if project:
                    project.close()
                    project = None
                scan, findings = None, []
                output("Session stopped. Saved evidence and project history remain in private storage.")
                continue
            try:
                if command == 'status':
                    show_status(project, runtime, scan, findings, output)
                elif command == 'inspect':
                    selected = project.findings if project else findings
                    number = int(words[1])
                    if not 1 <= number <= len(selected):
                        output('Choose a finding number from /findings. Run /scan or /demo first if none are saved.')
                    else:
                        show_detail(selected[number - 1], number, output)
                elif command == 'project':
                    selected = project_factory(words[1], output=output)
                    if runtime:
                        runtime.close()
                        runtime = None
                    if project:
                        project.close()
                    project = selected
                    scan, findings = None, []
                    output('Project selected: ' + display(project.path))
                    output('Source-only mode. Next: scan · routes · findings · history · use NUMBER · report [json]')
                elif project and command in ('scan', 'routes', 'findings', 'history', 'use', 'report', 'fix'):
                    if command == 'fix':
                        output('Project patches are disabled. fix NUMBER approves only shipped demo experiments.')
                    elif command == 'scan':
                        project.analyze()
                        show_findings(project.findings, output)
                    elif command == 'findings':
                        show_findings(project.findings, output)
                    elif command == 'routes':
                        routes = (project.scan or {}).get('surface', {}).get('routes', [])
                        for route in routes:
                            output(display(f"{','.join(route['methods'])} {route['path']} — {route['source']['file']}:{route['source']['line']}"))
                        output(f'{len(routes)} routes saved in the selected scan. Run scan to refresh.')
                    elif command == 'history':
                        history = project.history()
                        for number, saved in enumerate(history, 1):
                            output(f"{number}. {saved['status']} · {saved['created_at']} · {saved['id']}" +
                                   (' · selected' if saved['id'] == project.scan_id else ''))
                        if not history:
                            output('No saved scans. Run scan first.')
                    elif command == 'use':
                        saved = project.use(int(words[1]))
                        output(f"Selected scan: {saved['id']} · {saved['status']}")
                        show_findings(project.findings, output)
                    elif command == 'report':
                        output('Project report: ' + display(project.export('json' if words[1:] else 'markdown')))
                        output('Review source paths and findings before sharing. Static results are hypotheses.')
                elif command == 'demo':
                    if project:
                        project.close()
                        project = None
                    # A failed new investigation must not inherit a previous scan's results.
                    scan, findings = None, []
                    output("Running bounded checks against the bundled synthetic local app. No fixes are applied.")
                    if not runtime:
                        runtime = runtime_factory(output=output)
                        runtime.start()
                    scan = runtime.request("POST", "/demo/start", json={"approved": True,
                                                                          "browser": words[1:] == ["browser"]}).json()
                    url = runtime.web_url + "/app?scan=" + scan["id"]
                    output("Follow the investigation: " + url)
                    if os.getenv("SHADOWLAB_NO_OPEN") != "1":
                        try:
                            webbrowser.open(url)
                        except (webbrowser.Error, OSError):
                            output("Open the workspace URL above in your browser.")
                    wait_for_scan(runtime, scan["id"], output)
                    scan = runtime.request("GET", "/scans/" + scan["id"]).json()
                    findings = scan["findings"]
                    show_findings(findings, output)
                    output("Next: findings · fix NUMBER · report · demo browser · quit")
                elif command == "findings" and runtime and scan:
                    show_findings(findings, output)
                elif command == "fix" and runtime and scan:
                    if not 1 <= int(words[1]) <= len(findings):
                        output("Choose a finding number from findings, e.g. fix 1.")
                        continue
                    finding = findings[int(words[1]) - 1]
                    if finding['category'] not in ('authentication', 'bola', 'exposure'):
                        output("Verified demo patches cover authentication, object authorization and sensitive fields.")
                        continue
                    output("Approving a disposable demo patch experiment. The source app stays unchanged.")
                    patch = runtime.request("POST", f"/findings/{finding['id']}/propose-fix").json()
                    output("Patch verification: " + ("passed; awaiting review" if patch["verification"]["passed"] else "incomplete or failed") + ". Review the diff in the workspace.")
                    findings = runtime.request("GET", "/scans/" + scan["id"]).json()["findings"]
                elif command == "report" and runtime and scan:
                    json_format = words[1:] == ['json']
                    path = runtime.run_dir / ("report-" + scan["id"] + ('.json' if json_format else '.md'))
                    response = runtime.request('GET', '/reports/' + scan['id'],
                                               params={'format': 'json' if json_format else 'markdown'})
                    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
                        stream.write(response.text)
                    output("Sanitized report: " + display(path))
                else:
                    output('No compatible context for /' + command + '. Use /init or /project PATH for project commands; /demo for demo checks.')
            except KeyboardInterrupt:
                if project:
                    output('Cancelled. Project coverage is incomplete; type scan to retry or history to inspect.')
                    continue
                if runtime and scan:
                    try:
                        runtime.request("POST", f"/scans/{scan['id']}/cancel")
                    except Exception:
                        pass
                if runtime:
                    runtime.close()
                    runtime = None
                scan, findings = None, []
                output("Cancelled. Local demo services stopped; type demo to start again.")
            except Exception as exc:
                if project or command == 'project':
                    output(f"Project command incomplete ({type(exc).__name__}): {display(exc)}" if isinstance(exc, (ValueError, TimeoutError))
                           else f"Project command incomplete ({type(exc).__name__}); inspect private logs. Coverage is incomplete.")
                    continue
                output(f"Demo incomplete ({type(exc).__name__}): {display(exc)}" if isinstance(exc, (ValueError, TimeoutError))
                       else f"Demo incomplete ({type(exc).__name__}); check setup and private service logs.")
                if runtime:
                    runtime.close()
                    runtime = None
                scan, findings = None, []
    finally:
        if runtime:
            runtime.close()
        if project:
            project.close()
    output("ShadowLab closed. Local demo services stopped.")


def wait_for_scan(runtime, scan_id, output):
    deadline = time.monotonic() + 200
    last = None
    while time.monotonic() < deadline:
        scan = runtime.request("GET", "/scans/" + scan_id).json()
        if scan["stage"] != last:
            last = scan["stage"]
            output("Investigation: " + last)
        if scan["status"] not in ("queued", "running"):
            if scan["status"] != "completed":
                raise ValueError("Investigation " + scan["status"] + "; coverage is incomplete")
            return
        time.sleep(0.5)
    runtime.request("POST", "/scans/" + scan_id + "/cancel")
    raise TimeoutError("Investigation exceeded the console time limit and was cancelled")


def show_findings(findings, output):
    if not findings:
        output("No findings in this investigation.")
    for number, finding in enumerate(findings, 1):
        output(display(f"{number}. {finding['state']} — {finding['title']} ({finding['endpoint']})"))
    output("Confirmed findings have runtime evidence. Inconclusive findings need further validation.")
    if findings:
        output('Next: /inspect NUMBER for details · /report [json] to export.')


def show_status(project, runtime, scan, findings, output):
    if project:
        output('Context: project · ' + display(project.path))
        output('Mode: source-only · project execution, patches, LLM and OSV network checks disabled.')
        selected, findings = project.scan, project.findings
    elif runtime:
        output('Context: bundled synthetic demo · trusted local checks')
        output('Fixes require /fix NUMBER approval and subsequent diff review.')
        selected = scan
    else:
        output('Context: none. Use /init, /project PATH or /demo.')
        return
    if not selected:
        output('No selected scan. Run /scan in project mode or /demo for the demo.')
        return
    output(display(f"Scan: {selected['id']} · {selected['status']} · stage {selected.get('stage', 'unknown')}"))
    output(f'Findings: {len(findings)} · completion does not establish full security coverage.')
    if findings:
        counts = Counter(finding.get('state', 'unknown') for finding in findings)
        output('Verdicts: ' + ' · '.join(display(state) + '=' + str(count) for state, count in sorted(counts.items())))
    browser = selected.get('browser')
    if browser is not None:
        output('Browser validation requested: ' + ('yes' if browser else 'no'))
    if selected.get('coverage'):
        output('Coverage: ' + display(selected['coverage']))
    for name, result in selected.get('scanners', {}).items():
        output('Scanner ' + display(name) + ': ' + display(result.get('status', 'unknown')))


def show_detail(finding, number, output):
    # Deliberately exclude raw evidence, response values, settings and identity tokens.
    output(display(f"Finding {number}: {finding['title']}"))
    for key, label in [('state', 'Verdict'), ('severity', 'Severity'), ('category', 'Category'),
                       ('cwe', 'CWE'), ('endpoint', 'Component'), ('root_cause', 'Root cause'),
                       ('validation', 'Validation')]:
        if finding.get(key):
            output(label + ': ' + display(finding[key]))
    for source in finding.get('sources', [])[:20]:
        output('Source: ' + display(f"{source['file']}:{source['line']}"))
    browser = finding.get('browser') or {}
    for key in ('status', 'verdict'):
        if browser.get(key):
            output('Browser ' + key + ': ' + display(browser[key]))
    output('Static hypotheses need runtime evidence. Export /report for recorded evidence and coverage.')
