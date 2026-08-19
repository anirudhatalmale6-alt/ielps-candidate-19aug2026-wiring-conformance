"""Re-extract the backend route table from source, 19 August (second pass).

The router files are CommonJS, so module resolution follows `require('./x')`
rather than an ESM import. A required path may be a file, a file missing its
.js, or a directory with an index.js — `src/engine` is the last of those — so
every candidate is tried before the mount is discarded.

Nothing is inferred from a live probe: every EILPS router calls
router.use(authRequired) before any route matches, so an unauthenticated
request to a path that does not exist answers 401, not 404. Route existence is
readable only from source.
"""
import os
import re
import subprocess
import sys

SRC = sys.argv[1]
INDEX = os.path.join(SRC, 'index.js')

# A mount may carry middleware between the prefix and the router
# (`app.use('/api/auth', authLimiter, auth.router)`), so the argument list is
# captured whole and the router identifier taken from the last argument.
mount_re = re.compile(r"app\.use\(\s*['\"]([^'\"]+)['\"]\s*,([^)]*)\)")
req_re = re.compile(r"const\s+(?:\{\s*)?([A-Za-z0-9_$]+)(?:\s*\})?\s*=\s*require\(\s*['\"]\./([^'\"]+)['\"]")
route_re = re.compile(r"router\.(get|post|put|patch|delete)\s*\(\s*['\"`]([^'\"`]*)['\"`]", re.S)


def resolve(rel):
    for candidate in (rel, rel + '.js', os.path.join(rel, 'index.js')):
        path = os.path.join(SRC, candidate)
        if os.path.isfile(path):
            return path
    return None


index = open(INDEX, encoding='utf-8', errors='replace').read()
modules = {name: rel for name, rel in req_re.findall(index)}

routes = set()
mounts = 0
for prefix, args in mount_re.findall(index):
    if not prefix.startswith('/api'):
        continue
    var = args.split(',')[-1].strip().split('.')[0]
    rel = modules.get(var)
    path = resolve(rel) if rel else None
    if not path:
        continue
    mounts += 1
    body = open(path, encoding='utf-8', errors='replace').read()
    for method, route in route_re.findall(body):
        full = (prefix.rstrip('/') + route).rstrip('/') or prefix
        routes.add(f'{method.upper()} {full}')

out = sys.argv[2]
with open(out, 'w') as fh:
    fh.write('\n'.join(sorted(routes)) + '\n')
print(f'{mounts} mounts, {len(routes)} routes -> {out}')
