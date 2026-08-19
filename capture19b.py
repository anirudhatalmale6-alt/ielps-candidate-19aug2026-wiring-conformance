"""Evidence captures and text-density measurement, 19 August 2026 (pass B).

Density is characters of visible text per 1000px of page height, at 1280. It is
a blunt measure and is used here only for comparison against the same surfaces
in the previous candidate, which is what "reduce density" has to be judged
against.
"""
import json
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:4880'
OUT = '/var/lib/freelancer/projects/40470800/shots19b'

SHOTS = [
    ('01-access-panel-home', '/', 1280, 800, 0),
    ('02-studio-governance-condensed', '/app/studio/governance/', 1280, 800, 0),
    ('03-studio-credits-condensed', '/app/studio/credits/', 1280, 800, 0),
    ('04-admin-overview', '/app/admin/overview/', 1280, 800, 0),
    ('05-admin-operations', '/app/admin/operations/', 1280, 800, 0),
    ('06-admin-platform-ai', '/app/admin/ai/', 1280, 800, 0),
    ('07-parents-confirm-link', '/app/parents/links/', 1280, 800, 420),
    ('08-schools-approve-and-report', '/app/schools/roster/', 1280, 800, 260),
    ('09-adult-live-session-answer', '/app/adult/player/', 1280, 800, 380),
    ('10-pip-tucked-900', '/app/adult/', 900, 800, 1000),
    ('11-pip-tucked-390', '/app/adult/', 390, 780, 1170),
    ('12-reading-answers-390', '/preview/lesson-interactions/', 390, 780, 900),
]

DENSITY = [
    ('Studio AI governance', '/app/studio/governance/'),
    ('Studio AI Credits', '/app/studio/credits/'),
    ('Access Panel home', '/'),
    ('Schools roster', '/app/schools/roster/'),
    ('Administration overview', '/app/admin/overview/'),
]

import os
os.makedirs(OUT, exist_ok=True)
density = []

with sync_playwright() as pw:
    browser = pw.chromium.launch()

    for name, path, width, height, scroll in SHOTS:
        page = browser.new_page(viewport={'width': width, 'height': height})
        page.goto(BASE + path, wait_until='domcontentloaded', timeout=45000)
        page.wait_for_timeout(2800)
        if scroll:
            page.evaluate(f'window.scrollTo(0, {scroll})')
            page.wait_for_timeout(1300)
        page.screenshot(path=f'{OUT}/{name}.png')
        print('shot', name)
        page.close()

    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    for label, path in DENSITY:
        page.goto(BASE + path, wait_until='domcontentloaded', timeout=45000)
        page.wait_for_timeout(2800)
        stats = page.evaluate("""() => {
          const h = document.documentElement.scrollHeight;
          const t = (document.body.innerText || '').replace(/\\s+/g, ' ').trim();
          return { height: h, chars: t.length };
        }""")
        value = round(stats['chars'] / (stats['height'] / 1000))
        density.append({'surface': label, 'height': stats['height'],
                        'chars': stats['chars'], 'per_1000px': value})
        print(f'{label:26} {stats["chars"]:6} chars / {stats["height"]:5}px = {value}')
    page.close()
    browser.close()

json.dump(density, open('/var/lib/freelancer/projects/40470800/density-19b.json', 'w'), indent=2)
