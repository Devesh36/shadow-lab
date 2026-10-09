import json


def report(store, scan_id, format="markdown"):
    scan = store.get("scan", scan_id)
    if not scan:
        raise ValueError("Scan not found")
    findings = store.list("finding", scan_id)
    if format == "json":
        return json.dumps({"scan": scan, "findings": findings,
                           "patches": {f["id"]: store.list("patch", f["id"]) for f in findings}}, indent=2)
    text = ["# ShadowLab security report", "", f"Scan: {scan_id}", f"Status: {scan['status']}",
            f"Commit: {scan.get('commit') or 'uncommitted / unavailable'}",
            f"Target: {scan.get('target') or 'static analysis only'}", "",
            "Static hypotheses are not confirmed vulnerabilities. Results apply only to the supplied fixtures.", ""]
    for finding in findings:
        text += [f"## {finding['title']}", "", f"Severity: {finding['severity']} | State: {finding['state']}",
                 f"Category: {finding['category']} | CWE: {finding.get('cwe') or 'n/a'}",
                 f"Component: `{finding['endpoint']}`", "", finding["validation"], "",
                 "Root cause: " + finding["root_cause"], "", "Remediation: " + finding["remediation"], "",
                 "Reproduction conditions: " + "; ".join(finding["conditions"]), ""]
        for ref in finding["sources"]:
            text.append(f"Source: `{ref['file']}:{ref['line']}`")
        text += ["", "```json", json.dumps(finding["evidence"], indent=2), "```", ""]
        for patch in store.list("patch", finding["id"]):
            text += ["### Proposed patch (developer review required)", "", "```diff", patch["diff"], "```", "",
                     "Regression result:", "```json", json.dumps(patch["verification"], indent=2), "```", ""]
    return "\n".join(text)
