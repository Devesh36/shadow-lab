"""Reproducible, explicit local-demo scan and three disposable patch verifications."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.agents.workflow import Workflow
from packages.core.models import RepositoryCreate, ScanCreate, Settings, SyntheticFixture, Target
from packages.core.report import report
from packages.core.service import Service
from packages.db.store import Store
from packages.remediation.patches import DEMO, propose


async def validate(args):
    folder = Path(args.output).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    # Separate run state; no operator settings, API token, or credentials are changed.
    os.environ['SHADOWLAB_DATA_DIR'] = str(folder)
    os.environ['SHADOWLAB_REPOSITORY_ROOT'] = str(DEMO.parents[1])
    db = Store(os.getenv('SHADOWLAB_TEST_POSTGRES_URL') or f'sqlite:///{folder / "validation.db"}')
    db.initialize()
    db.save_settings(Settings(targets=[Target(url=args.target, authorized=True, approved=True, allow_loopback=True)],
        fixture=SyntheticFixture(), sandbox_mode='trusted-local', request_budget=150,
        requests_per_second=5, scan_timeout_seconds=180, timeout_seconds=10,
        categories=['authentication', 'bola', 'exposure', 'headers']))
    service = Service(db)
    repo = service.add_repository(RepositoryCreate(path=str(DEMO)))
    scan = service.create_scan(ScanCreate(repository_id=repo['id'], target=args.target, dynamic=True, browser=True))
    await Workflow(db, scan['id']).run()
    results = {}
    for category in ('authentication', 'bola', 'exposure'):
        finding = next(f for f in db.list('finding', scan['id']) if f['category'] == category)
        patch = await propose(db, finding) if finding['state'] == 'CONFIRMED' else None
        results[category] = {'baseline': finding.get('browser'), 'patch_id': patch['id'] if patch else None,
            'patched': patch['verification'] if patch else {'passed': False, 'validation': 'Baseline not confirmed'}}
    (folder / 'report.json').write_text(report(db, scan['id'], 'json'))
    (folder / 'report.md').write_text(report(db, scan['id']))
    (folder / 'results.json').write_text(json.dumps({'scan_id': scan['id'], 'results': results}, indent=2))
    print(json.dumps({'scan_id': scan['id'], 'scan_status': db.get('scan', scan['id'])['status'],
        'cases': {k: {'baseline': v['baseline']['verdict'] if v['baseline'] else 'INCONCLUSIVE',
                      'patch_passed': v['patched']['passed'], 'test_count': v['patched'].get('test_count', 0)}
                  for k, v in results.items()}, 'reports': str(folder)}, indent=2))
    db.engine.dispose()
    return all(v['patched']['passed'] for v in results.values())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True)
    parser.add_argument('--output', default='.shadowlab/browser-validation/native')
    parser.add_argument('--authorize', required=True, action='store_true')
    parser.add_argument('--approve', required=True, action='store_true')
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(validate(args)) else 1)
