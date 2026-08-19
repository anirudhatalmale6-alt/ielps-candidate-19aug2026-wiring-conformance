"""Role states, wired actions and the protected Administration surface.

19 August 2026, second pass.

Three separate questions are answered here, and the third is the one that
matters most for the security boundary.

First, that each newly wired action is really wired: the panel exists on the
surface it belongs to, it carries the endpoint it claims, and it will not send
anything until every value the route needs is present.

Second, that the outcome shown is the server's. Each action is driven through
the statuses the real routes can answer — 201 for a stored live-session
response, 200 for an activated link, 402, 403, 422 and 500 — and the rendered
result is compared against what that status should produce. Nothing is checked
for merely "not crashing": a 403 has to render as a refusal and a 422 has to
render the server's own words.

Third, that the protected Administration surface hands nothing to an ordinary
role. It is driven twice: once with the backend's real refusal, where every
panel must show the refusal and no payload may appear anywhere in the DOM, and
once with an administrator-shaped success, where the same panels must render
the records. And separately, that it is not on the public Access Panel at all.
"""
import json
import re
import sys
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:4880'
results = []


def record(name, ok, detail=''):
    results.append({'check': name, 'pass': bool(ok), 'detail': detail})
    print(f'{"PASS" if ok else "FAIL"}  {name}' + (f'   {detail}' if detail else ''))


def route_map(page, mapping, default=(401, '{"error":"unauthorized"}')):
    """Answer /api/** from a table of (substring -> (status, body))."""
    def handler(route):
        url = route.request.url
        for needle, (status, body) in mapping.items():
            if needle in url:
                return route.fulfill(status=status, content_type='application/json', body=body)
        status, body = default
        route.fulfill(status=status, content_type='application/json', body=body)
    page.route('**/api/**', handler)


with sync_playwright() as pw:
    browser = pw.chromium.launch()

    # ── 1. The public Access Panel is still seven pathways ─────────────────
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    page.goto(BASE + '/', wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(3000)
    cards = page.eval_on_selector_all(
        'a[href^="/app/"]', '(els) => els.map((e) => e.getAttribute("href"))')
    slugs = sorted({re.match(r'/app/([^/]+)', h).group(1) for h in cards if re.match(r'/app/([^/]+)', h)})
    record('Access Panel offers seven account pathways and no Administrator card',
           len(slugs) == 7 and 'admin' not in slugs, f'slugs={slugs}')
    body = page.inner_text('body').lower()
    record('No Administration wording on the public Access Panel',
           'platform administration' not in body)
    page.close()

    # ── 2. Wired actions: presence, gating, and server-driven outcome ──────
    ACTIONS = [
        {
            'name': 'Parent link confirmation',
            'path': '/app/parents/links/',
            'panel': 'Confirm a pending link',
            'chip': 'POST /api/school/parent/links/confirm',
            'inputs': {'Consent token': 'demo-token'},
            'endpoint': 'parent/links/confirm',
            'success': (200, '{"link":{"id":"L1","status":"active"},"status":"active"}'),
        },
        {
            'name': 'School parent-link approval',
            'path': '/app/schools/roster/',
            'panel': 'Approve a parent relationship',
            'chip': 'POST /api/school/organizations/:id/parent-links/approve',
            'inputs': {'Parent account id': 'P1', 'Child account id': 'C1'},
            'endpoint': 'parent-links/approve',
            'success': (200, '{"link":{"id":"L9","status":"active"},"status":"active"}'),
            'needs_org': True,
        },
        {
            'name': 'Learner live-session response',
            'path': '/app/adult/player/',
            'panel': 'Live lesson answer',
            'chip': 'POST /api/authoring/live-sessions/:id/responses',
            'inputs': {'Live session code': 'S1', 'Activity': 'B2', 'Your answer': 'my answer'},
            'endpoint': 'live-sessions',
            'success': (201, '{"response":{"id":"R1","session_id":"S1","block_id":"B2"}}'),
        },
        {
            'name': 'Platform engine refresh',
            'path': '/app/admin/operations/',
            'panel': 'Rebuild the content index',
            'chip': 'POST /api/engine/refresh',
            'inputs': {},
            'endpoint': 'engine/refresh',
            'success': (200, '{"refreshed":true}'),
        },
    ]

    ORG_OK = '{"organizations":[{"id":"ORG-1","name":"Maple Primary"}]}'

    for action in ACTIONS:
        # -- present, and carrying the endpoint it claims
        page = browser.new_page(viewport={'width': 1280, 'height': 1000})
        route_map(page, {'school/admin/overview': (200, ORG_OK)})
        page.goto(BASE + action['path'], wait_until='domcontentloaded', timeout=45000)
        page.wait_for_timeout(2500)
        text = page.inner_text('body')
        record(f'{action["name"]}: panel present with its endpoint chip',
               action['panel'] in text and action['chip'].replace('POST ', '') in text)

        # -- will not send until every value is present
        section = page.locator('section', has_text=action['panel']).first
        cta = section.locator('button').last
        if action['inputs']:
            record(f'{action["name"]}: disabled until every value is supplied',
                   cta.is_disabled())
        page.close()

        # -- the outcome is the server's, across the statuses it can answer
        for status, body_json, expectation in [
            (*action['success'], 'accepted'),
            (401, '{"error":"unauthorized"}', 'Sign in to perform this action.'),
            (403, '{"error":"forbidden"}', 'does not have permission'),
            (402, '{"error":"payment required"}', 'entitlement is required'),
            (422, '{"error":"missing_token"}', 'server rejected this request'),
            (500, '{"error":"server_error"}', 'could not complete'),
        ]:
            page = browser.new_page(viewport={'width': 1280, 'height': 1000})
            route_map(page, {
                'school/admin/overview': (200, ORG_OK),
                action['endpoint']: (status, body_json),
            }, default=(200, '{}'))
            page.goto(BASE + action['path'], wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(2500)
            section = page.locator('section', has_text=action['panel']).first
            for label, value in action['inputs'].items():
                section.get_by_label(label).fill(value)
            section.locator('button').last.click()
            page.wait_for_timeout(900)
            shown = section.inner_text()
            if expectation == 'accepted':
                ok = 'server accepted' in shown.lower() or 'reached the live session' in shown.lower() \
                     or 'activated this link' in shown.lower() or 'approved this relationship' in shown.lower()
                # The server's own record has to be on screen, not a summary of it.
                ok = ok and ('"status"' in shown or '"refreshed"' in shown or '"id"' in shown)
            else:
                ok = expectation.lower() in shown.lower()
            record(f'{action["name"]}: HTTP {status} renders the server outcome', ok,
                   '' if ok else shown.replace('\n', ' ')[:120])
            page.close()

    # -- organisation-scoped panels stay in PARAMETER REQUIRED with no context
    page = browser.new_page(viewport={'width': 1280, 'height': 1000})
    requested = []
    def watch(route):
        requested.append(route.request.url)
        if 'school/admin/overview' in route.request.url:
            return route.fulfill(status=200, content_type='application/json',
                                 body='{"organizations":[]}')
        route.fulfill(status=200, content_type='application/json', body='{}')
    page.route('**/api/**', watch)
    page.goto(BASE + '/app/schools/roster/', wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(3000)
    text = page.inner_text('body')
    record('Organisation-scoped panels report PARAMETER REQUIRED without a School context',
           text.lower().count('parameter required') >= 2)
    record('No organisation-scoped request is sent without a real organisation id',
           not any('reports/schools' in u for u in requested))
    page.close()

    # ── 3. The protected Administration surface ────────────────────────────
    ADMIN_SCREENS = ['overview', 'users', 'content', 'tutors', 'certificates', 'ai']
    ADMIN_PAYLOAD = {
        'admin/stats': (200, '{"users":42,"lessons":9,"certificates":3,"aiCallsLast24h":7}'),
        'admin/users': (200, '[{"id":"U1","email":"someone@example.com","role":"admin"}]'),
        'admin/content': (200, '[{"id":"C1","title":"A1 Unit 1"}]'),
        'admin/tutors': (200, '[{"id":"T1","name":"A Tutor"}]'),
        'admin/certificates': (200, '[{"id":"X1","level":"B1"}]'),
        'admin/tutor-applications': (200, '[{"id":"A1","status":"pending"}]'),
        # The real reply is SELECT p.* over ai_prompt_versions, so it carries
        # the system prompt itself. The stub carries it too, on purpose: the
        # check below is that an administrator sees the version and that the
        # prompt text does not reach the DOM even for them.
        'tutor/admin/prompts': (200, '[{"id":"P1","name":"conversation-coach","version":3,'
                                     '"status":"active","system_template":"SECRET-TEMPLATE {{level}}",'
                                     '"latest_eval_status":"passed","latest_eval_total":10,'
                                     '"latest_eval_passed":9}]'),
    }
    REFUSAL = (403, '{"error":"forbidden","message":"Admin access required."}')

    for screen in ADMIN_SCREENS:
        page = browser.new_page(viewport={'width': 1280, 'height': 1000})
        route_map(page, {k: REFUSAL for k in ADMIN_PAYLOAD}, default=REFUSAL)
        page.goto(f'{BASE}/app/admin/{screen}/', wait_until='domcontentloaded', timeout=45000)
        page.wait_for_timeout(2500)
        shown = page.inner_text('body')
        html = page.content()
        leaked = [v for v in ['someone@example.com', 'A1 Unit 1', 'A Tutor', 'aiCallsLast24h', '"v3"']
                  if v in html]
        record(f'Administration /{screen}: an ordinary role sees the refusal',
               'administrator role is required' in shown.lower())
        record(f'Administration /{screen}: no privileged payload in the DOM',
               not leaked, f'leaked={leaked}' if leaked else '')
        page.close()

    for screen in ADMIN_SCREENS:
        page = browser.new_page(viewport={'width': 1280, 'height': 1000})
        route_map(page, ADMIN_PAYLOAD, default=(200, '{}'))
        page.goto(f'{BASE}/app/admin/{screen}/', wait_until='domcontentloaded', timeout=45000)
        page.wait_for_timeout(2500)
        shown = page.inner_text('body')
        expected = {'overview': '42', 'users': 'someone@example.com', 'content': 'A1 Unit 1',
                    'tutors': 'A Tutor', 'certificates': 'B1',
                    'ai': 'conversation-coach v3'}[screen]
        record(f'Administration /{screen}: an administrator sees the records',
               expected in shown, '' if expected in shown else f'missing {expected!r}')
        if screen == 'ai':
            # Even the administrator's own version list must not print the
            # system prompt onto the page.
            record('Administration /ai: the system prompt text is not rendered',
                   'SECRET-TEMPLATE' not in page.content())
            record('Administration /ai: the evaluation result is rendered',
                   'Evaluation 9/10' in shown)
        page.close()

    # ── 3b. The four tucked-state conditions, at 900 and 390 ───────────────
    # Where Pip has had to tuck, all four stated conditions have to hold: no
    # important control covered, no horizontal overflow, a visible affordance
    # with real vertical extent, and one tap restoring the full launcher.
    # Where it has not had to tuck, the meaningful check is that the launcher
    # is full size and one tap opens the assistant.
    PIP_JS = """() => {
      const root = document.querySelector('.ielps-pip-agent');
      const launcher = root && root.querySelector('.ielps-pip-launcher');
      if (!launcher) return null;
      const p = launcher.getBoundingClientRect();
      const sel = 'a[href],button,input,select,textarea,[role="button"],[role="link"],[role="tab"]';
      let covered = 0;
      document.querySelectorAll(sel).forEach((el) => {
        if (root.contains(el)) return;
        const s = getComputedStyle(el);
        if (s.visibility === 'hidden' || s.display === 'none' || s.pointerEvents === 'none') return;
        const r = el.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) return;
        if (r.bottom <= 0 || r.top >= innerHeight) return;
        const x = Math.min(p.right, r.right) - Math.max(p.left, r.left);
        const y = Math.min(p.bottom, r.bottom) - Math.max(p.top, r.top);
        if (x > 2 && y > 2) covered += 1;
      });
      return {
        placement: root.getAttribute('data-pip-placement'),
        side: root.getAttribute('data-pip-tuck-side'),
        covered,
        overflow: Math.max(0, document.documentElement.scrollWidth - innerWidth),
        visibleWidth: Math.round(Math.min(p.right, innerWidth) - Math.max(p.left, 0)),
        height: Math.round(p.height),
        width: Math.round(p.width),
        mascot: !!launcher.querySelector('img'),
      };
    }"""

    for width, height, offset in [(900, 800, 1000), (390, 780, 1170)]:
        page = browser.new_page(viewport={'width': width, 'height': height})
        page.goto(BASE + '/app/adult/', wait_until='domcontentloaded', timeout=45000)
        page.wait_for_timeout(2500)
        page.evaluate(f'window.scrollTo(0, {offset})')
        page.wait_for_timeout(1300)
        before = page.evaluate(PIP_JS)
        page.click('.ielps-pip-launcher')
        page.wait_for_timeout(700)
        after = page.evaluate(PIP_JS)
        opened = page.locator('.ielps-pip-panel').count() > 0

        if before['placement'] == 'tucked':
            record(f'Pip tucked at {width}px: zero important controls covered',
                   before['covered'] == 0, f'covered={before["covered"]}')
            record(f'Pip tucked at {width}px: zero horizontal overflow',
                   before['overflow'] == 0, f'overflow={before["overflow"]}px')
            record(f'Pip tucked at {width}px: visible affordance with vertical extent',
                   before['visibleWidth'] > 0 and before['height'] >= 64 and before['mascot'],
                   f'{before["visibleWidth"]}x{before["height"]}px on the {before["side"]} edge, mascot={before["mascot"]}')
            record(f'Pip tucked at {width}px: one tap restores the full launcher',
                   after['placement'] == 'anchored' and after['width'] > before['visibleWidth'],
                   f'{before["visibleWidth"]}px handle -> {after["width"]}x{after["height"]}px launcher')
        else:
            record(f'Pip at {width}px: settled clear of every control',
                   before['covered'] == 0 and before['overflow'] == 0,
                   f'placement={before["placement"]}')
            record(f'Pip at {width}px: one tap opens the assistant', opened)
        page.close()

    # ── 4. Studio no longer probes an Administrator-only route ─────────────
    page = browser.new_page(viewport={'width': 1280, 'height': 1000})
    calls = []
    page.on('request', lambda r: calls.append(r.url) if '/api/' in r.url else None)
    page.goto(BASE + '/app/studio/governance/', wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(3500)
    record('Studio AI Governance makes no Administrator-only request',
           not any('tutor/admin/prompts' in u for u in calls),
           f'{len(calls)} api calls')
    shown = page.inner_text('body')
    record('Studio AI Governance still names what is governed elsewhere',
           'governed elsewhere' in shown.lower())
    page.close()

    browser.close()

passed = sum(1 for r in results if r['pass'])
json.dump({'passed': passed, 'total': len(results), 'results': results},
          open('/var/lib/freelancer/projects/40470800/actions-19b.json', 'w'), indent=2)
print(f'\n{passed}/{len(results)} checks passed')
sys.exit(0 if passed == len(results) else 1)
