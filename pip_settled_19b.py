"""Pip settled-state and tucked-discoverability evidence, 19 August 2026 (pass B).

Two things are measured, and they are separate questions.

The first is the rule itself: at every resting position on every surface, does
Pip cover a control a learner needs to press? The page is walked a viewport at
a time; at each stop the scroll is left alone for well past the 180ms idle
threshold so the settle actually resolves, and then Pip's rectangle is compared
against every reachable control in the viewport. Anything overlapping by more
than 2px on both axes is a failure and is recorded with the element that was
covered, so a failure is diagnosable rather than just a count.

The second is what the review asked for on top: where Pip has had to tuck,
is the handle actually findable and recoverable? That is checked as the four
stated conditions — nothing important covered, no horizontal overflow, a
visible Pip affordance of real vertical extent, and one tap restoring the full
launcher — at the two viewports named in the acceptance test.
"""
import json
import sys
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:4880'

SURFACES = [
    ('Access Panel home', '/'),
    ('Adult mini-app', '/app/adult/'),
    ('Adult dashboard', '/app/adult/dashboard/'),
    ('Adult lesson player', '/app/adult/player/'),
    ('Adult review', '/app/adult/review/'),
    ('Junior mini-app', '/app/junior/'),
    ('Parents links', '/app/parents/links/'),
    ('Schools roster', '/app/schools/roster/'),
    ('Studio governance', '/app/studio/governance/'),
    ('Studio credits', '/app/studio/credits/'),
    ('Administration operations', '/app/admin/operations/'),
    ('Reading interactions', '/preview/lesson-interactions/'),
]

VIEWPORTS = [(1280, 800), (900, 800), (390, 780)]

OVERLAP_JS = """
() => {
  const root = document.querySelector('.ielps-pip-agent');
  const launcher = root && root.querySelector('.ielps-pip-launcher');
  if (!launcher) return { present: false };
  const p = launcher.getBoundingClientRect();
  const sel = 'a[href],button,input,select,textarea,[role="button"],[role="link"],[role="tab"],[role="checkbox"],[role="radio"]';
  const hits = [];
  document.querySelectorAll(sel).forEach((el) => {
    if (root.contains(el)) return;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || s.pointerEvents === 'none') return;
    if (parseFloat(s.opacity) === 0) return;
    if (el.getAttribute('aria-hidden') === 'true' || el.disabled) return;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return;
    if (r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) return;
    const x = Math.min(p.right, r.right) - Math.max(p.left, r.left);
    const y = Math.min(p.bottom, r.bottom) - Math.max(p.top, r.top);
    if (x > 2 && y > 2) {
      hits.push({ tag: el.tagName.toLowerCase(), text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 60), overlap: [Math.round(x), Math.round(y)] });
    }
  });
  return {
    present: true,
    placement: root.getAttribute('data-pip-placement'),
    motion: root.getAttribute('data-pip-motion'),
    obstructed: root.getAttribute('data-pip-obstructed') === 'true',
    side: root.getAttribute('data-pip-tuck-side'),
    rect: { left: Math.round(p.left), top: Math.round(p.top), width: Math.round(p.width), height: Math.round(p.height) },
    visibleWidth: Math.round(Math.min(p.right, innerWidth) - Math.max(p.left, 0)),
    overflow: Math.max(0, document.documentElement.scrollWidth - innerWidth),
    hits,
  };
}
"""

stops = []
tuck_checks = []
failures = []

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for width, height in VIEWPORTS:
        page = browser.new_page(viewport={'width': width, 'height': height})
        for label, path in SURFACES:
            page.goto(BASE + path, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(2500)
            # Read the height after a trip to the bottom: several surfaces grow
            # once their panels hydrate, and measuring too early truncated the
            # sweep so that later stops — including the ones that tuck — were
            # never visited at all.
            page.evaluate('window.scrollTo(0, 99999)')
            page.wait_for_timeout(900)
            total = page.evaluate('() => document.documentElement.scrollHeight')
            # 200px steps, and the very bottom of the page explicitly. A
            # coarser step silently skipped the offsets where Pip actually has
            # to adapt, which made an under-sampled sweep look like a clean one.
            bottom = max(total - height, 0)
            offsets = list(range(0, bottom + 1, 200))
            if offsets[-1] != bottom:
                offsets.append(bottom)
            for offset in offsets:
                page.evaluate(f'window.scrollTo(0, {offset})')
                # Well past the 180ms idle threshold, so the settle has resolved
                # and this is a resting measurement rather than a moving one.
                page.wait_for_timeout(900)
                info = page.evaluate(OVERLAP_JS)
                if not info.get('present'):
                    continue
                record = {
                    'surface': label,
                    'viewport': f'{width}x{height}',
                    'scrollY': offset,
                    'placement': info['placement'],
                    'visibleWidth': info['visibleWidth'],
                    'overflow': info['overflow'],
                    'blocked': len(info['hits']),
                }
                stops.append(record)
                if info['hits'] or info['overflow'] > 0:
                    failures.append({**record, 'hits': info['hits']})
        page.close()

    # ---- tucked-state discoverability, at the two acceptance viewports ------
    # The tuck is a last resort, so it does not occur at a fixed scroll offset.
    # Every surface is swept at each viewport until one is found, and the four
    # stated conditions are then checked there. A viewport where no surface
    # tucks is reported as exactly that rather than as a pass.
    for width, height in [(900, 800), (390, 780)]:
        found = False
        for label, path in SURFACES:
            if found:
                break
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.goto(BASE + path, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(2000)
            page.evaluate('window.scrollTo(0, 99999)')
            page.wait_for_timeout(900)
            total = page.evaluate('() => document.documentElement.scrollHeight')
            bottom = max(total - height, 0)
            sweep = list(range(0, bottom + 1, 100))
            if sweep[-1] != bottom:
                sweep.append(bottom)
            for offset in sweep:
                page.evaluate(f'window.scrollTo(0, {offset})')
                page.wait_for_timeout(800)
                before = page.evaluate(OVERLAP_JS)
                if not before.get('present') or before.get('placement') != 'tucked':
                    continue

                # One tap on the handle must give the full launcher back.
                page.click('.ielps-pip-launcher')
                page.wait_for_timeout(500)
                after = page.evaluate(OVERLAP_JS)

                tuck_checks.append({
                    'viewport': f'{width}x{height}',
                    'reached_tuck': True,
                    'surface': label,
                    'scrollY': offset,
                    'controls_covered': len(before['hits']),
                    'horizontal_overflow': before['overflow'],
                    'visible_width': before['visibleWidth'],
                    'visible_height': before['rect']['height'],
                    'side': before['side'],
                    'restored_placement': after['placement'],
                    'restored_width': round(after['rect']['width']),
                    'restored_height': round(after['rect']['height']),
                    'one_tap_restores': after['placement'] == 'anchored'
                                        and after['rect']['width'] > before['visibleWidth'],
                })
                found = True
                break
            page.close()
        if not found:
            tuck_checks.append({'viewport': f'{width}x{height}', 'reached_tuck': False,
                                'note': 'no surface in the sweep needed the tuck at this width'})

    browser.close()

blocked = sum(s['blocked'] for s in stops)
overflow = sum(1 for s in stops if s['overflow'] > 0)
out = {
    'stops': len(stops),
    'controls_blocked': blocked,
    'stops_with_horizontal_overflow': overflow,
    'placements': {p: sum(1 for s in stops if s['placement'] == p)
                   for p in {s['placement'] for s in stops}},
    'failures': failures,
    'tuck_discoverability': tuck_checks,
    'detail': stops,
}
json.dump(out, open('/var/lib/freelancer/projects/40470800/pip-settled-19b.json', 'w'), indent=2)

print(f'{len(stops)} resting stops · {blocked} controls blocked · {overflow} with horizontal overflow')
print('placements:', out['placements'])
for check in tuck_checks:
    print(' tuck', check)
sys.exit(1 if (blocked or overflow) else 0)
