"""Every endpoint label the platform draws, checked against the routes the live
backend actually registers.

The frontend declares its chips in three shapes:
  lib/ielps-data.ts   pathway cards, adult flow steps, placement strip
  lib/apps/*.ts       mini-app panels and lesson-player step strips
Each is { method, path }. The backend table is extracted from the running
~/eilps/backend/src/index.js mounts plus each router's own registrations.

A declared path matches a backend route when their segments agree, treating any
":param" segment on either side as a wildcard. Query strings are ignored for
matching (they are not part of a route) but reported.
"""
import json
import re
import subprocess
from pathlib import Path

REPO = Path('/var/lib/freelancer/projects/40470800/remediation-0814')
TABLE = Path('/var/lib/freelancer/projects/40470800/backend-routes-19aug-b.txt')

backend = []
for line in TABLE.read_text().splitlines():
    line = line.strip()
    if not line or ' ' not in line:
        continue
    m, p = line.split(None, 1)
    backend.append((m.upper(), p))


def segs(path):
    return [s for s in path.split('?')[0].split('/') if s]


def matches(method, path):
    want = segs(path)
    for bm, bp in backend:
        if bm != method:
            continue
        have = segs(bp)
        if len(have) != len(want):
            continue
        ok = True
        for a, b in zip(want, have):
            if a.startswith(':') or b.startswith(':'):
                continue
            if a != b:
                ok = False
                break
        if ok:
            return bp
    return None


# Collect every declared chip with the file it is declared in.
DECL = re.compile(r"method:\s*'(GET|POST|PUT|PATCH|DELETE)'\s*,\s*path:\s*'([^']+)'")
found = {}
for f in sorted(list((REPO / 'lib').rglob('*.ts'))):
    if 'node_modules' in str(f):
        continue
    for m, p in DECL.findall(f.read_text()):
        found.setdefault((m, p), set()).add(str(f.relative_to(REPO)))

rows = []
for (m, p), files in sorted(found.items()):
    hit = matches(m, p)
    rows.append({
        'method': m,
        'path': p,
        'backend': hit,
        'status': 'MATCHED' if hit else 'NOT FOUND IN BACKEND',
        'declared_in': sorted(files),
    })

ok = [r for r in rows if r['backend']]
bad = [r for r in rows if not r['backend']]
print(f'declared chips: {len(rows)}   matched: {len(ok)}   unmatched: {len(bad)}')
print()
for r in bad:
    print('  UNMATCHED', r['method'], r['path'], '  <-', ', '.join(r['declared_in']))

Path('/var/lib/freelancer/projects/40470800/chip-audit-19aug.json').write_text(
    json.dumps(rows, indent=2)
)
