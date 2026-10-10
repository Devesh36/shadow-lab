"""A guided source-only workflow shared by the console and one-shot CLI."""
from packages.core.repl_commands import display


def run_project_demo(project, output=print):
    output('Project demo: ' + display(project.path))
    output('Source-only workflow: discover routes → analyze source → inspect verdicts → export reports.')
    output('Project scripts, installs, runtime requests and automatic fixes are disabled.')
    scan = project.analyze()
    routes = scan.get('surface', {}).get('routes', [])
    coverage = {
        'route_discovery': {'status': 'completed' if routes else 'unsupported',
                            'reason': 'Next.js route patterns are heuristic.' if routes else
                                      'No recognized Next.js routes; route coverage is unavailable for this source layout.'},
        'source_analysis': {'status': scan['status'], 'reason': 'Static hypotheses require further validation.'},
        'semgrep': {'status': scan.get('scanners', {}).get('semgrep', {}).get('status', 'unavailable')},
        'dependency_advisories': {'status': 'disabled', 'reason': 'Project console mode makes no advisory network calls.'},
        'browser_validation': {'status': 'unsupported', 'reason': 'Browser identity validation supports only the reviewed bundled demo.'},
        'patch_verification': {'status': 'unsupported', 'reason': 'Automatic patches support only disposable bundled demo copies.'},
    }
    project.store.put('scan', {'project_demo': coverage}, id=scan['id'])
    output(f'Discovered routes: {len(routes)}')
    for route in routes[:50]:
        output(display(f"{','.join(route['methods'])} {route['path']} — {route['source']['file']}:{route['source']['line']}"))
    if len(routes) > 50:
        output('Showing the first 50 routes; the JSON report contains the complete saved surface.')
    findings = project.findings
    for number, finding in enumerate(findings, 1):
        output(display(f"{number}. {finding['state']} — {finding['title']} ({finding['endpoint']})"))
    if not findings:
        output('No hypotheses recorded. This does not establish that the repository is secure.')
    for name, result in coverage.items():
        output('Coverage ' + name + ': ' + display(result['status']) +
               (' — ' + display(result['reason']) if result.get('reason') else ''))
    reports = {}
    for format in ('markdown', 'json'):
        reports[format] = str(project.export(format))
        output('Project report: ' + display(reports[format]))
    output('Project demo finished. Review source paths and findings before sharing reports.')
    return {'scan_id': scan['id'], 'project': str(project.path), 'coverage': coverage, 'reports': reports}
