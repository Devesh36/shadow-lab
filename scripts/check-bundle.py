"""Check that a distribution contains its complete runtime and no generated/private state."""
import json
import sys
from zipfile import ZipFile

with ZipFile(sys.argv[1]) as wheel:
    names = set(wheel.namelist())
    files = json.loads(wheel.read('packages/core/bundle-files.json'))
    for name in files:
        assert name in names, f'Missing runtime asset: {name}'
    for name in names:
        assert not set(name.split('/')) & {'.env', '.shadowlab', 'node_modules', '.next', '__pycache__', '.git'}, name
    entries = wheel.read('shadowlab-0.1.0.dist-info/entry_points.txt').decode()
    assert 'shadow = packages.core.cli:main' in entries
    assert 'shadowlab = packages.core.cli:main' in entries
print(f'Package valid: {len(files)} runtime assets; no private/generated directories')
