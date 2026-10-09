"""Small guided console. Commands are fixed actions, never Python or shell evaluation."""
import os
import shutil
import time
import webbrowser

from packages.core.demo_runtime import DemoRuntime

MENU = "1  Demo     2  Check setup     help     quit"
HELP = "demo [browser] · findings · fix NUMBER · report · stop · doctor · help · quit"


def run(input_fn=input, output=None, runtime_factory=DemoRuntime):
    output = output or (lambda message: print(message, flush=True))
    output("ShadowLab — evidence-driven security investigations")
    output(MENU)
    runtime = None
    scan = None
    findings = []
    try:
        while True:
            try:
                words = input_fn("shadow> ").strip().lower().split()
            except (EOFError, KeyboardInterrupt):
                output("\nClosing ShadowLab.")
                break
            if not words:
                continue
            command = words[0]
            if command in ("quit", "exit", "q"):
                break
            if command in ("help", "?"):
                output(HELP)
                output("Choosing Demo authorizes bounded checks of the bundled synthetic local app.")
                output("fix NUMBER explicitly approves a disposable patch experiment; every patch needs review.")
                continue
            if command in ("2", "doctor"):
                output("Setup: " + ", ".join(f"{tool} {'found' if shutil.which(tool) else 'missing'}"
                                             for tool in ("node", "npm", "git")))
                output("Demo needs Node.js 22+, npm and Git. Browser demo also needs Playwright Chromium.")
                continue
            if command == "stop":
                if runtime:
                    runtime.close()
                    runtime = None
                scan, findings = None, []
                output("Local demo stopped. Saved evidence remains in its private run directory.")
                continue
            try:
                if command in ("1", "demo"):
                    if words[1:] not in ([], ["browser"]):
                        output("Use demo or demo browser.")
                        continue
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
                    if len(words) != 2 or not words[1].isdigit() or not 1 <= int(words[1]) <= len(findings):
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
                    path = runtime.run_dir / ("report-" + scan["id"] + ".md")
                    path.write_text(runtime.request("GET", "/reports/" + scan["id"]).text)
                    output("Sanitized report: " + str(path))
                else:
                    output("Choose Demo first, or type help for commands.")
            except KeyboardInterrupt:
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
                output(f"Demo incomplete ({type(exc).__name__}): {exc}" if isinstance(exc, (ValueError, TimeoutError))
                       else f"Demo incomplete ({type(exc).__name__}); check setup and private service logs.")
                if runtime:
                    runtime.close()
                    runtime = None
                scan, findings = None, []
    finally:
        if runtime:
            runtime.close()
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
        output(f"{number}. {finding['state']} — {finding['title']} ({finding['endpoint']})")
    output("Confirmed findings have runtime evidence. Inconclusive findings need further validation.")
