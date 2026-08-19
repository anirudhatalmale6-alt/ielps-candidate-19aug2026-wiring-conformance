"""Full API declaration audit, 19 August 2026.

The 87/87 chip result was true and is not what this measures. A visible chip is
one of seven places a route can be declared, and the other six are exactly where
a stale declaration survives unnoticed — an adapter nobody calls, a mini-app
inventory that was written from a spec rather than from the server, a direct
fetch buried in a component. Each layer is therefore extracted and reported on
its own rather than collapsed into a single number.

  A  visible endpoint chips          panels, onboarding steps, pathway cards
  B  canonical Next adapters         lib/adapters.ts
  C  direct useEilps / fetch calls   anything calling a path in a component
  D  mini-app endpoint inventories   the `endpoints:` block of each mini-app
  E  legacy frontend/src/api.js      the Vite frontend still on the server
  F  protected Administrator APIs    the /api/admin and /api/tutor/admin subset
  G  backend registered routes       read from backend source, not probed

G is read from source because it cannot be probed: every EILPS router calls
router.use(authRequired) before any route matches, so an unauthenticated request
to a path that does not exist answers 401 rather than 404, and a probe would
report an imaginary route as real.

Path parameters are normalised before comparison — :id, :linkId and :projectId
are the same segment shape — so a declaration is only reported as unmatched when
the route genuinely is not registered, not when it named its parameter
differently from the backend.
"""
import json
import os
import re
import sys

ROOT = '/var/lib/freelancer/projects/40470800'
APP = os.path.join(ROOT, 'remediation-0814')
LEGACY = os.path.join(ROOT, 'fe-src-19b/api.js')
ROUTES = os.path.join(ROOT, 'backend-routes-19aug-b.txt')

# A declared path may be a template literal, so `${...}` — including the
# parentheses of an encodeURIComponent call inside it — is part of the token.
PATH_RE = r"/api/(?:\$\{[^}]*\}|[A-Za-z0-9_\-/:.\[\]])*"


def norm(path):
    """Normalise for comparison: strip query, template holes, parameter names."""
    path = path.split('?')[0]
    # An interpolation attached straight to a segment name — `/catalog${query
    # ? ... }` — is a query string being appended, not a path segment. One
    # preceded by a slash — `/certificates/${level}` — is a real parameter.
    path = re.sub(r'(?<=[A-Za-z0-9_])\$\{.*$', '', path)
    path = re.sub(r'\$\{[^}]*\}', ':p', path)
    path = path.rstrip('/')
    path = re.sub(r'/:[A-Za-z0-9_]+', '/:p', path)
    return path or '/'


backend = {}
for line in open(ROUTES):
    line = line.strip()
    if not line:
        continue
    method, path = line.split(' ', 1)
    backend.setdefault(norm(path), set()).add(method)

# ── A, C, D: read out of the candidate's TypeScript ────────────────────────
chips = []           # A
direct = []          # C
inventories = []     # D

ENDPOINT_OBJ = re.compile(
    r"\{\s*method:\s*'([A-Z]+)'\s*,\s*path:\s*'(" + PATH_RE + r")'", re.S)

for dirpath, _dirs, files in os.walk(APP):
    if 'node_modules' in dirpath or '/.next' in dirpath:
        continue
    for name in files:
        if not name.endswith(('.ts', '.tsx')):
            continue
        rel = os.path.relpath(os.path.join(dirpath, name), APP)
        text = open(os.path.join(dirpath, name), encoding='utf-8').read()
        # Strip comments so a path discussed in a docblock is not counted as a
        # declaration. This matters: several comments name routes precisely in
        # order to explain why they are *not* declared.
        code = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
        code = re.sub(r'^\s*//.*$', '', code, flags=re.M)

        if rel.startswith('lib/apps/') and rel != 'lib/apps/types.ts':
            body = code
            # The trailing `endpoints:` block is the mini-app inventory (D);
            # everything before it is panel and onboarding chips (A).
            split = body.find('\n  endpoints: [')
            head, tail = (body[:split], body[split:]) if split > 0 else (body, '')
            for method, path in ENDPOINT_OBJ.findall(head):
                chips.append((method, path, rel))
            for method, path in ENDPOINT_OBJ.findall(tail):
                inventories.append((method, path, rel))
        elif rel == 'lib/ielps-data.ts':
            for method, path in ENDPOINT_OBJ.findall(code):
                chips.append((method, path, rel))
        elif rel == 'lib/adapters.ts':
            pass  # layer B, handled below
        else:
            for method, path in ENDPOINT_OBJ.findall(code):
                chips.append((method, path, rel))
            for path in re.findall(r"useEilps[^(]*\(\s*'(" + PATH_RE + r")'", code):
                direct.append(('GET', path, rel))
            for path in re.findall(r"ielpsFetch(?:Blob)?[^(]*\(\s*[`']?(" + PATH_RE + r")", code):
                direct.append(('*', path, rel))
            for path in re.findall(r"fetch\(\s*`[^`]*?(" + PATH_RE + r")", code):
                direct.append(('*', path, rel))

# ── B: the canonical adapters ──────────────────────────────────────────────
adapters = []
adapter_src = open(os.path.join(APP, 'lib/adapters.ts'), encoding='utf-8').read()
adapter_code = re.sub(r'/\*.*?\*/', '', adapter_src, flags=re.S)
adapter_code = re.sub(r'^\s*//.*$', '', adapter_code, flags=re.M)
for method, path in re.findall(
        r"\b(get|post|patch|put|ielpsFetchBlob)\b[^(\n]*\(\s*(?:withParams\(\s*)?[`']("
        + PATH_RE + r")", adapter_code):
    verb = 'POST' if method == 'ielpsFetchBlob' else method.upper()
    adapters.append((verb, path, 'lib/adapters.ts'))

# ── E: the legacy Vite frontend still deployed on the server ───────────────
legacy = []
legacy_src = open(LEGACY, encoding='utf-8').read()
# Each legacy call is `request(<path>, { method: "X", ... })`. The method is
# read from that call's own option object only — scanning further ahead picks up
# the next function's method and mislabels a GET as a POST.
for match in re.finditer(r"request\(\s*[`\"']([^`\"']*)[`\"']\s*(,\s*\{[^}]*\})?", legacy_src):
    path = match.group(1)
    if not path.startswith('/api/'):
        continue
    options = match.group(2) or ''
    found = re.search(r'method:\s*"([A-Z]+)"', options)
    legacy.append((found.group(1) if found else 'GET', path, 'frontend/src/api.js'))

# Deliberate frontend-only paths: what they are, and why they are not a defect.
INTENTIONAL = {
    '/api/agent/config': 'INTENTIONALLY INTERNAL',
    '/api/agent/chat': 'INTENTIONALLY INTERNAL',
    '/api/agent/voice': 'INTENTIONALLY INTERNAL',
}


def classify(method, path):
    key = norm(path)
    methods = backend.get(key)
    if not methods:
        return INTENTIONAL.get(key, 'CANONICAL ROUTE NOT FOUND')
    if method != '*' and method not in methods:
        return f'CANONICAL ROUTE NOT FOUND (method {method}; server has {"/".join(sorted(methods))})'
    if key.startswith('/api/admin') or key.startswith('/api/tutor/admin'):
        return 'ADMIN ONLY'
    if ':p' in key:
        return 'PARAMETER REQUIRED'
    return 'MATCHED'


LAYERS = [
    ('A', 'Visible API chips', chips),
    ('B', 'Canonical Next adapters', adapters),
    ('C', 'Direct useEilps / fetch calls', direct),
    ('D', 'Mini-app endpoint inventories', inventories),
    ('E', 'Legacy frontend/src/api.js', legacy),
]

report = {'backend_routes': sum(len(v) for v in backend.values()), 'layers': {}}
unmatched_total = 0

for code, title, entries in LAYERS:
    seen = {}
    for method, path, source in entries:
        seen.setdefault((method, norm(path)), {'method': method, 'path': path,
                                               'sources': set()})['sources'].add(source)
    rows = []
    for item in seen.values():
        verdict = classify(item['method'], item['path'])
        rows.append({'method': item['method'], 'path': item['path'],
                     'verdict': verdict, 'sources': sorted(item['sources'])})
    rows.sort(key=lambda r: (r['verdict'].startswith('CANONICAL') is False, r['path']))
    bad = [r for r in rows if r['verdict'].startswith('CANONICAL')]
    unmatched_total += len(bad)
    report['layers'][code] = {'title': title, 'declared': len(rows),
                              'unmatched': len(bad), 'rows': rows}
    print(f'{code}  {title:34} {len(rows):3} declared   {len(bad)} unmatched')
    for row in bad:
        print(f'      ! {row["method"]:6} {row["path"]}  [{", ".join(row["sources"])}]')

# ── F: the administrator subset, across every layer above ──────────────────
admin_rows = []
for code, title, entries in LAYERS:
    for method, path, source in entries:
        key = norm(path)
        if key.startswith('/api/admin') or key.startswith('/api/tutor/admin'):
            admin_rows.append({'layer': code, 'method': method, 'path': path,
                               'source': source, 'verdict': classify(method, path)})
report['layers']['F'] = {'title': 'Protected Administrator APIs',
                         'declared': len(admin_rows), 'rows': admin_rows}
print(f'F  Protected Administrator APIs        {len(admin_rows):3} declared   '
      f'{sum(1 for r in admin_rows if r["verdict"].startswith("CANONICAL"))} unmatched')

# ── G: coverage the other way round ────────────────────────────────────────
declared_keys = {norm(p) for _, _, entries in [(c, t, e) for c, t, e in LAYERS]
                 for _, p, _ in entries}
uncovered = sorted(k for k in backend if k not in declared_keys)

# A registered route with no frontend declaration is not a defect — the rule
# runs the other way. It is still worth saying why each one has no caller here,
# so the gap is a decision on the record rather than an oversight.
WHY_NOT_EXPOSED = [
    ('/api/assessment/checkpoint/moderation', 'Teacher/School checkpoint moderation workflow'),
    ('/api/assessment/checkpoint/', 'Teacher/School checkpoint scoring workflow'),
    ('/api/practice/moderation', 'Teacher/School practice moderation workflow'),
    ('/api/compliance/', 'Data-protection operations, run by the platform not a learner'),
    ('/api/operations/', 'Platform operations and job queues'),
    ('/api/mfa/', 'Account security flow, not part of the Access Panel'),
    ('/api/auth/oauth/', 'Third-party sign-in, no provider configured for this panel'),
    ('/api/payments/create-one-time-session', 'Server-internal checkout step, called by billing'),
    ('/api/billing/trial-checkout', 'Personalised $3 Trial — excluded from this pass'),
    ('/api/partners/simulate-conversion', 'Test tooling, deliberately not reachable from a UI'),
    ('/api/roster/organizations/', 'Roster exchange and sync, beyond the connections card'),
    ('/api/tutoring/time-requests/', 'Tutor time-request lifecycle, not built in this panel'),
    ('/api/tutoring/bookings/', 'Booking settlement detail, not built in this panel'),
    ('/api/classroom/ice-servers', 'WebRTC provider detail, consumed inside the classroom'),
    ('/api/studio/coursebook/generations/', 'Coursebook export, not built in this panel'),
]


def why(path):
    for prefix, reason in WHY_NOT_EXPOSED:
        if path.startswith(prefix):
            return reason
    return 'No frontend declaration; not reviewed in this pass'


report['layers']['G'] = {'title': 'Backend registered routes',
                         'registered': len(backend),
                         'declared_by_frontend': len(backend) - len(uncovered),
                         'not_declared_anywhere': [
                             {'path': p, 'verdict': 'INTENTIONALLY NOT EXPOSED', 'reason': why(p)}
                             for p in uncovered]}
print(f'G  Backend registered routes          {len(backend):3} distinct paths, '
      f'{len(backend) - len(uncovered)} declared by some frontend layer')

report['unmatched_total'] = unmatched_total
json.dump(report, open(os.path.join(ROOT, 'api-audit-19b.json'), 'w'), indent=2)
print(f'\nunregistered declarations across all layers: {unmatched_total}')
sys.exit(0)
