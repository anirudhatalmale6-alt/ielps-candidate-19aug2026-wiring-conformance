# Post-83CC wiring and conformance — evidence pack

19 August 2026 · answers the *Post-83CC Final Wiring & Conformance Instruction*
(REAUTHORED, 19 August), §17's twenty-four return items in order.

---

## 1. Release identity (§17.1, §17.23)

| | |
| --- | --- |
| Commit | `bc2c8ca357265367d3ec8c0ad0e2a149f408d03a` |
| Short | `bc2c8ca` |
| Parent | `83cc0600a04503d6013aaebc04b03e7618dc31f4` — the approved working baseline |
| Branch | `visual-direction-20260815` |
| Repository | `10495109/v0-ielps-platform-h4` |
| Build ID | `2PshIk7bkuBVU-dKWDA-C` |
| Source files | 125 tracked (120 at `83cc060` + 5 new) |
| Manifest SHA-256 | `fdee4941b3546e86f6dd6a0b2b5e1cd3c68dbac6acfe306dbb049815eed2891a` |
| Deployment | **NOT DEPLOYED. NOT DEPLOY APPROVED.** |

**Twenty files, fifteen changed and five new.**

| File | Why |
| --- | --- |
| `lib/eilps-http.ts` | Binary POST path for certificates; administrator refusal classified from both server wordings |
| `lib/adapters.ts` | Three unregistered Studio AI declarations removed; engine refresh, administration, partners attribution, practice school report, live-session response, parent-link approval added |
| `lib/apps/types.ts` | `action` panel kind, progressive disclosure, organisation-scoped fetch, protected surface |
| `lib/apps/admin.ts` | **new** — protected Platform Administration |
| `lib/apps/index.ts` | Registers the protected surface without putting it on the Access Panel |
| `lib/apps/studio.ts` | Governance condensed, administrator probe removed, AI Credits condensed |
| `lib/apps/parents.ts` | Parent link confirmation, wired |
| `lib/apps/schools.ts` | Organisation parent-link approval and the practice report, wired |
| `lib/apps/adult.ts` | Live-session response wired; a hard-coded level in a chip corrected |
| `lib/use-school-context.ts` | **new** — the organisation identifier, from the server |
| `lib/referral.ts` | **new** — referral carried across sign-in |
| `components/app/action-panel.tsx` | **new** — the panel that performs a real write |
| `components/app/panel.tsx` | Renders `action`, disclosure, and organisation-scoped fetch |
| `components/app/onboarding-flow.tsx` | Submits the referral after authentication succeeds |
| `components/referral-capture.tsx` | **new** — records a partner-link arrival |
| `components/pip/use-pip-settle.ts` | Tall tucked handle, measured at full height; one-tap restore |
| `components/pip/pip-agent.tsx` | Tuck rendering, restore behaviour, spelling, bounded question |
| `components/pip/pip-mount.tsx` | Spelling |
| `app/globals.css` | Tucked-handle presentation; spelling in the comments |
| `app/layout.tsx` | Mounts the referral capture; spelling |

Everything else is byte-identical to `83cc060`.

---

## 2. TypeScript, lint, build (§17.2)

| | |
| --- | --- |
| `npx tsc --noEmit` | 0 errors |
| `npx eslint .` | 0 errors, 0 warnings |
| `npx next build` | success, 20 static pages, `2PshIk7bkuBVU-dKWDA-C` |

---

## 3. The full API declaration audit (§4, §16, §17.3)

The 87/87 chip result was true and is not what this measures. A visible chip is
one of seven places a route can be declared, and the other six are exactly where
a stale declaration survives unnoticed. Each layer is extracted and reported on
its own.

| Layer | | Declared | Unregistered |
| --- | --- | ---: | ---: |
| A | Visible API chips | 87 | **0** |
| B | Canonical Next adapters | 130 | **0** |
| C | Direct `useEilps` / `fetch` calls | 6 | **0** |
| D | Mini-app endpoint inventories | 80 | **0** |
| E | Legacy `frontend/src/api.js` | 189 | **0** |
| F | Protected Administrator APIs | 45 | **0** |
| G | Backend registered routes | 243 distinct paths | 210 declared by some layer |

Layer G is read from backend source, not probed. Every EILPS router calls
`router.use(authRequired)` before any route matches, so an unauthenticated
request to a path that does not exist answers 401 rather than 404 — a probe
would report an imaginary route as real. The table was re-extracted today and is
identical to the 19 August morning extraction: 266 registrations, 243 distinct
paths, across 32 mounted routers.

### What the audit found that the chip audit could not

**Three adapters declaring routes that do not exist.** All three were in the
Studio AI group, and all three are gone:

| Removed | Why |
| --- | --- |
| `GET /api/studio/ai/quota` | Not registered. `studio_ai_governance.js` mounts one Studio-safe route |
| `GET /api/studio/ai/moderation` | Not registered. The quota and moderation sections come back inside `/api/studio/ai/governance` |
| `PATCH /api/studio/ai/moderation/:id` | Not registered. There is no separate moderation write route |

The chips for these were corrected on 18 August. The adapters were not, and a
chip-only audit had no way to see them. This is §17.15: **zero obsolete or
unregistered Studio AI route declarations remain in deployable adapters.**

No backend route was added to make any of them match. Adding one would have been
a duplicate route created to satisfy a stale frontend declaration, which §16
forbids and which would have been the wrong fix anyway.

**A hard-coded value inside a visible chip.** The Adult certificates panel
declared `GET /api/certificates/eligibility/B1`. The registered route is
`/api/certificates/eligibility/:level`; `B1` was a sample level baked into a
label. Corrected to the parameterised route.

### The 33 registered routes no frontend declares

Not a defect — the rule runs the other way — but each carries a stated reason in
`api-audit-19b.json` rather than being left as an unexplained gap. They fall
into: Teacher/School moderation and checkpoint workflows, data-protection
operations, platform job queues, MFA, third-party sign-in, the server-internal
checkout step, the Personalised $3 Trial checkout (excluded from this pass),
partner test tooling, roster exchange and sync, the tutor time-request
lifecycle, WebRTC provider detail, and coursebook export. All
**INTENTIONALLY NOT EXPOSED**.

---

## 4. `POST /api/engine/refresh` — what I found (§7, §17.4)

§7 asks me to **retain** the explicit Platform Administrator role check on this
route. I went to verify it before building the surface around it, and **it is
not there.**

`backend/src/engine.js`, as deployed today:

```js
const router = express.Router();
router.use(authRequired);
...
router.post('/refresh', asyncHandler(async (req, res) => { await idx.refresh(); res.json({ refreshed: true }); }));
```

`authRequired` is the only gate. There is no role read and nothing
route-specific. So **any signed-in account** can rebuild the whole platform's
content index today — an adult learner, a parent, a teacher, a school member
without a platform role, a Studio creator. §7's table describes what we want,
not what the server currently does, and I would rather say so than build a
frontend that implies otherwise.

I have not changed it. Production is not deploy-approved in this pass, and a
permission change is not something to slip in alongside a frontend release. The
patch is written out in full in `BACKEND-PATCH-PROPOSALS.md` §1, using the
`adminRequired` pattern already in `backend/src/admin.js`, scoped to `/refresh`
alone so the learner-facing engine routes are untouched.

**What is in this candidate**, and it is the part that is mine to do:

- The operation appears on the protected Administration surface and nowhere
  else. Not on the Access Panel, not on any role dashboard.
- The panel renders whatever the server answers, including a refusal. There is
  no browser-side gate, because a browser-side gate on a platform operation is
  decoration.
- The refusal classifier now recognises both server wordings. `admin.js`
  answers `Admin access required.` and the AI governance routes answer with
  `administrator`; only the second was matched before, so a real refusal from
  the administration router would have rendered as an ordinary permission
  message. Both now reach `An administrator role is required`.

The day the backend patch lands, nothing in the candidate has to change: the
403 will simply render as the administrator refusal it already knows how to
show.

**Evidence** (`actions-19b.json`, driven statuses):

| Server answer | What the surface shows |
| --- | --- |
| 200 `{refreshed:true}` | The server accepted the rebuild, with its record |
| 401 | Sign in to perform this action |
| 403 | This account does not have permission |
| 403 with an administrator message | An administrator role is required |
| 402 | An active lesson or subscription entitlement is required |
| 422 | The server's own words |
| 500 | The server could not complete this action |

---

## 5. Certificate issuance: binary POST with refresh and retry (§6, §17.5)

`POST /api/certificates/:level` is `authRequired` plus a premium entitlement and
answers `application/pdf`. It could not go through `ielpsFetch`, which parses
the body as text and would consume the stream before a caller ever saw a Blob.

`ielpsFetchBlob` is the binary path. It sends, and on 401 refreshes the bearer
**once** and sends again — exactly once, because a second 401 after a fresh
token is an authentication failure, not a retryable condition.

What matters as much as the happy path is that nothing else is allowed to look
like a download.

**8/8** (`cert-blob-19b.json`), run against the shipped `lib/eilps-http.ts`
compiled from source:

| Scenario | Result |
| --- | --- |
| Expired token → refresh → retry | PDF Blob, `application/pdf`, body starts `%PDF`, 2 certificate calls |
| Still 401 after refresh | No download, 401 `authentication`, **2** calls — not a loop |
| 402 entitlement | No download, classified `entitlement` |
| 403 permission | No download, classified `permission` |
| 403 `Admin access required.` | No download, classified `admin` |
| 422 validation | No download |
| 500 server error | No download |
| 200 carrying JSON, not a PDF | **No download** — refused on content type |

That last one is not in the brief and I added it deliberately: a 200 with a JSON
error body would otherwise have reached the browser as a PDF and saved as a
corrupt file.

**Why a stub and not the live route.** Proving this needs a 401-then-200
sequence and a 402 on demand, which a live server will not produce to order, and
§10 of the previous instruction is explicit that no live purchase may be made to
turn evidence green. The stub drives the real client code through the real
sequences. Eligibility and entitlement rules are untouched, per §6.

---

## 6. Parent link confirmation (§8, §17.6)

Wired on **Parents → Access & links**, beside the pending list.

`POST /api/school/parent/links/confirm`, body `{ token }`. Two properties of the
real route are worth stating rather than hiding, and the panel copy states the
first of them:

- It matches on `child_user_id = req.user.id`, so it activates only for the
  account the invitation was issued to. A caller it was not issued to gets 404
  `link_not_found_or_expired`.
- A missing token is 422 `missing_token`, not a silent no-op.

**Nothing is marked confirmed until the server confirms it.** The pending list
above continues to read from the server; this panel reports only what came back,
and shows the server's record verbatim.

Verified across 200 / 401 / 403 / 402 / 422 / 500, plus that the action is
disabled until the token is present.

---

## 7. School organisation approval (§8, §17.7)

Wired on **Schools → Roster**.

`POST /api/school/organizations/:id/parent-links/approve`, body
`{ parentUserId, childUserId }`. The backend gates it twice: an organisation
role check (`owner`, `school_admin` or `safeguarding_lead`), then a membership
check that both accounts are active members of that organisation. An ordinary
learner, Parent, Tutor or Studio creator is refused by the server and shown the
refusal — there is no browser-side judgement about who may approve.

The `:id` comes from the signed-in School context and from nowhere else.

Verified across the same six statuses, plus disabled-until-complete.

---

## 8. School practice report (§8, §17.8)

Wired on **Schools → Roster**. `GET /api/practice/reports/schools/:id`, with the
organisation identifier from the signed-in School context.

**No sample id appears anywhere in this path.** With no organisation resolved
the report is not requested at all: the panel reports PARAMETER REQUIRED and no
request leaves the browser. That is checked directly — the test drives
`GET /api/school/admin/overview` to `{"organizations":[]}` and then asserts that
no request to `reports/schools` was made.

The only honest source for the identifier is the server's own answer about which
organisations the caller belongs to. An id invented to make the request succeed
would either fail against a real database or, worse, succeed against somebody
else's organisation.

---

## 9. Learner live-session response (§9, §17.9)

Wired on **Adult → Lesson Player**.

`POST /api/authoring/live-sessions/:id/responses`. The genuine session id
travels through the interaction — it is the code the learner was given when they
joined — and the body carries the block and the answer. The server stores the
response against the signed-in account and answers 201 with the stored record;
that record is what is shown.

There is no alternate response endpoint anywhere in this build and no wrapper
that is declared but never called. Verified across 201 / 401 / 403 / 402 / 422 /
500.

---

## 10. Partner link and payout detail (§10, §17.10)

**CANONICAL ROUTE NOT FOUND — both of them.**

`GET /api/partners/links/:linkId` and `GET /api/partners/payouts/:payoutId` are
not registered. The complete registered partner surface, read from
`backend/src/partners.js`:

```
GET  /api/partners/track/:code
POST /api/partners/attribute
GET  /api/partners/dashboard
POST /api/partners/links
POST /api/partners/withdrawals
GET  /api/partners/fraud-reviews
POST /api/partners/simulate-conversion
```

There is no detail route for an individual link and none for an individual
payout. So neither was declared: a chip or an adapter for a route that does not
exist is exactly the untruthful label the API rule forbids, and adding the
routes to the backend to satisfy a frontend declaration is the duplicate-route
pattern §16 forbids. The finding is recorded in `lib/adapters.ts` as a comment
beside the partners group, so the next person to look does not re-derive it.

If you want those two records reachable, that is a backend change and I will
propose it separately.

---

## 11. Protected Platform Administration (§11, §17.11)

**Not an eighth pathway.** The public Access Panel still offers seven account
choices, and this surface appears on none of them. It has a route,
`/app/admin/...`, and is reachable when the server grants the role.

That intent is in data rather than in a convention someone has to remember:
`protectedSurface: true` on the app, and `PUBLIC_ACCOUNT_APPS` filters it out.
The Access Panel renders `PATHWAYS` from `lib/ielps-data.ts`, which is and stays
seven.

**Seven screens**, covering exactly what §11 lists: Overview (stats), Users,
Content, Tutors and applications, Certificates, Platform AI (prompt versions and
evaluation runs), Operations (the engine refresh).

**The role check stays server-side.** Every panel asks the server; nothing is
rendered from a client-side assumption about who the caller is. There is no
gate to bypass, because there is nothing to gate — the data never arrives.

**Evidence**, each screen driven twice:

| | Result |
| --- | --- |
| Ordinary role (backend's real `403 Admin access required.`) | Every screen shows *An administrator role is required*, on all six |
| Ordinary role — privileged payload in the DOM | **None.** Checked against `page.content()`, not just visible text, on all six |
| Administrator (200 with records) | Every screen renders the records, on all six |

**One thing I changed while building it.** `GET /api/tutor/admin/prompts` returns
`SELECT p.*` over `ai_prompt_versions`, which carries `system_template` — the
system prompt itself. The generic panel normaliser would have put whatever it
found into the row. That panel now selects its fields explicitly: name, version,
status and the latest evaluation result. **The prompt text is never rendered**,
even for an administrator who may be entitled to it: a version list is not the
place to spill it onto a screen, and somebody is usually standing behind them.
Verified — the stub carries `SECRET-TEMPLATE` and it does not appear in the DOM,
while `Evaluation 9/10` does.

---

## 12. Referral attribution across login (§15, §17.12)

The two halves of an attribution happen under different identities. Somebody
arrives from a partner link while signed out; the account the referral belongs
to does not exist yet. Not carrying the reference across authentication simply
loses it, and the partner is not credited for a signup they produced.

What the browser does is narrow, deliberately:

1. On arrival with `?ref=` (or `referral`/`partner`), it records the click
   through `GET /api/partners/track/:code`. That route is unauthenticated by
   design — it counts the click and sets the visitor cookie, and it creates **no
   commercial record of any kind.**
2. After a successful sign-in, and only then, it hands the code over once to
   `POST /api/partners/attribute`, which is authenticated.
3. From there the server owns it entirely: it resolves the code, writes the
   attribution against the now-known account, scores it for risk, and holds it
   for fraud review when the score is high. A self-referral is caught there.

**The browser never awards a commission, never computes one, and never writes to
a commercial ledger.** It carries a string across a login and forgets it. The
code is cleared *before* the request rather than after, so a failed attribution
cannot be re-submitted by a later sign-in on the same device.

The submit point is the authentication step in the onboarding flow — register,
login or student-login — after the server has accepted it.

---

## 13. Safety-report abuse control (§15, §17.13) — proposal, not applied

§15 says that where no approved threshold exists I should return a proposal
rather than guess. `BACKEND-PATCH-PROPOSALS.md` §2 has the patch in full. The
short version:

- `express-rate-limit` is already the house pattern (`apiLimiter` at 600/min,
  `authLimiter` at 30/min), so no new dependency.
- Both existing limiters key on **IP**, which is the wrong key here. A school
  behind one NAT address shares an IP, so an IP-keyed limit on safeguarding
  would let one abuser silence a whole school's ability to report. The proposed
  limiter keys on **account**.
- **Nothing is silently discarded.** Over the bound, the caller gets a 429 that
  says plainly the report was *not* recorded and gives them a route that does
  not depend on this system. A silent drop is worse than no limit, because the
  reporter believes they have reported.

**Values are yours.** My suggestion, offered as a starting point and not
applied: 20 reports per account per hour, both as environment variables so they
can change without a code change. Two alternatives are written out if you would
rather not cap a safeguarding route at all.

---

## 14. Public Agent cost control (§15, §17.14)

I read `backend/src/agent.js` rather than assume where the cost is:

| Route | Cost | Why |
| --- | --- | --- |
| `GET /api/agent/config` | free | Reads the shipped manifest and cached audio URLs |
| `POST /api/agent/chat` | free | `responseFor()` is deterministic from the manifest. No provider is called |
| `POST /api/agent/voice` — cached | free | Returns an existing clip from disk |
| `POST /api/agent/voice` — dynamic | **billable** | Calls ElevenLabs |

So the billable surface is one branch of one route, and everything a visitor
needs in order to navigate is on the free side of it.

**The frontend half is in this release.** Pip calls `/api/agent/chat` only. It
never calls `/api/agent/voice`, never sets `forceDynamic`, and plays only the
cached clip a chat response names. A single question is bounded to 400
characters before the request is built. Both verified: `maxlength=400`, and zero
requests to `/api/agent/voice` across a full session.

**The server half is proposed, not applied** (`BACKEND-PATCH-PROPOSALS.md` §3):
cached-first before any bound is consulted, then a per-caller hourly bound and a
text-length bound on the dynamic branch only, falling back to the caption rather
than an error. **No sign-in is added anywhere** — config, chat and cached voice
stay public and unmetered, which is the point of a public Agent.

Values to approve: `AGENT_DYNAMIC_VOICE_LIMIT` (suggested 15/hour) and
`AGENT_DYNAMIC_TEXT_MAX` (suggested 600 characters).

---

## 15. School roster PARAMETER REQUIRED regression (§17.16)

Preserved. `GET /api/roster/organizations/:id/connections` with PARAMETER
REQUIRED until the School context supplies the organisation id. Checked in the
functional suite, and 109/109 declared chips still match the backend table.

---

## 16. Studio governance, condensed and role-safe (§12, §17.17)

**The primary view is the four responsibilities that are genuinely the
creator's**, in the order §12 lists them:

1. My AI allowance and usage
2. AI service readiness
3. Generated content awaiting my review
4. Human review before publication

plus one concise *Governed elsewhere* treatment, now behind progressive
disclosure rather than as more always-visible text.

**The administrator probe is gone.** The screen no longer calls
`GET /api/tutor/admin/prompts`. From an ordinary Studio account that route could
only ever return 403, and asking for a refusal on every page load in order to
display the refusal is neither useful to the creator nor free. The boundary is
now stated in words — the same information without the request. The route is
still reachable from the protected Administration surface, where the caller may
actually hold the role.

Verified: **zero** requests to `tutor/admin/prompts` from the Studio page.

The condensing is checked in both directions, so "condensed" cannot quietly
become "removed": the boundary text is *not* on screen by default, and one click
reveals it.

---

## 17. AI Credits, condensed (§13, §17.18)

Rebuilt to the information hierarchy you set out:

| Panel | Copy |
| --- | --- |
| Current status | Prepared, not active. |
| How credits work | Included with a Studio subscription. New paid AI generation uses credits. |
| Your balance | Not yet available — server accounting is not active. |
| What does not use credits | Existing content, manual editing, review, and governance. |
| Billing and failed generations | Progressive disclosure |

Checked for **absence**, not just presence, and over the *opened* page so nothing
can hide inside the disclosure: no currency figure, no credit count, no package,
no price, and **no endpoint chip anywhere on the screen** — the credit routes are
proposed, not built.

§14's hold is respected in full: no migration run, no top-up product, no invented
quantity, rate or price. `AI-CREDITS-IMPLEMENTATION-NOTE.md` is updated to record
that hold-then-settle is approved as the future architecture and that the three
remaining questions are commercial and yours.

---

## 18. Pip spelling (§3, §17.19)

Learner-facing spelling is **Pip** throughout — visible labels, accessible names
and explanatory copy. Zero occurrences of `PiP` remain in `app/`, `components/`
or `lib/`.

| | |
| --- | --- |
| Launcher accessible name | `Open Pip assistant` |
| Panel accessible name | `Pip assistant` |
| Close control | `Close Pip` |
| Header | `Pip` |
| Greeting | `Hi, I'm Pip!` |
| Composer | `Ask Pip...` |

Internal identifiers are unchanged by design: `pip-agent`, `use-pip-settle`,
`data-pip-placement`, `.ielps-pip-*`.

Worth noting: the server's agent manifest (`backend/data/agent.common-paths.json`)
never names Pip in any language, so there is no server-side spelling to correct.

---

## 19. Pip settled state and tucked discoverability (§2, §17.20, §17.21)

**168 resting positions**, 12 surfaces × 3 viewports (1280×800, 900×800,
390×780), each measured after the page has been still for well past the 180ms
threshold.

| | |
| --- | --- |
| Controls covered at rest | **0** |
| Stops with horizontal overflow | **0** |
| Anchored — nothing changed at all | 128 |
| Cleared — shrank and moved to a slot on screen | 31 |
| Tucked — no clear slot existed | 9 |

**A correction to my own previous evidence.** The 19 August morning sweep
reported 91 stops with a coarse scroll step, and that step silently skipped the
offsets where Pip actually has to adapt — including every position at 900px
where it tucks. This sweep uses a 200px step and always visits the bottom of the
page, which is why the count doubled and why the 900px tuck is visible now. The
earlier "0 blocked" was true of the stops it visited; it visited too few.

### The tuck, made discoverable

The first version cleared every control but showed a sliver of a circle that did
not read as Pip. The tucked state is now a **tall handle**: the visible width is
still only what the page gutter allows, but it runs 64–72px down the edge,
carries the mascot at twice the visible width so a recognisable slice shows, has
a gold grip below it, and the whole height is the collision search's own box —
so the extra height is proven clear, not assumed.

**All four stated conditions, at both acceptance viewports:**

| | 900×800 | 390×780 |
| --- | --- | --- |
| Zero important controls covered | **0** | **0** |
| Zero horizontal overflow | **0px** | **0px** |
| Visible Pip affordance | 16 × **72**px, right edge, mascot present | 16 × **64**px, right edge, mascot present |
| One tap restores the full launcher | 16px handle → **167 × 66px** launcher | 16px handle → **60 × 60px** launcher |

One tap on the handle restores the full launcher rather than opening the
conversation; the second tap opens it. Settling re-arms on the next scroll or
resize, so a learner who wants Pip back gets it and the page still protects
itself afterwards.

**One honest limitation.** The visible handle is 16px wide because that is the
entire page gutter on that surface — the cards run edge to edge and there is
nothing else to occupy. It is now unmistakably a tab rather than a smudge, but
it is a narrow tab. If you would rather it stayed prominent there and accepted
card overlap on that one surface, that is one line in `findSlot`. Say which.

---

## 20. Public Landing unchanged (§1, §17.22)

Not touched, and provable rather than asserted. Every operation I ran against
the server this pass was a read. The only file modified anywhere under
`~/eilps` since midnight is the Postgres socket lock:

```
find ~/eilps -type f -newermt "2026-08-19 00:00" ! -name "*.log" ! -path "*/node_modules/*"
  → /home/anirudhat/eilps/pgdata/.s.PGSQL.55432.lock
```

Landing dist tree hash for the record:
`b63cd1a20ef48db48f570adc59a49fed0a5041189f2fd9aeb534ce3e11f2bdfd`.

---

## 21. Density (§12, §13)

Characters of visible text per 1000px of page height, at 1280.

| Surface | 19 Aug (`83cc060`) | Now (`bc2c8ca`) | |
| --- | ---: | ---: | --- |
| Studio AI governance | 1292 | **1132** | −12% |
| Studio AI Credits | 1473 | **821** | −44% |
| Access Panel home | 998 | 998 | unchanged |
| Schools roster | — | 1234 | two wired actions added |
| Administration overview | — | 452 | new surface |

Nothing was deleted to get there. The secondary half of both Studio screens is
one click away.

---

## 22. Acceptance gate

| Item | Result |
| --- | --- |
| TypeScript | 0 errors |
| ESLint | 0 problems |
| Build | success, `2PshIk7bkuBVU-dKWDA-C` |
| Functional suite | **59 / 59** |
| Wiring, roles and Administration | **65 / 65** |
| Certificate binary path | **8 / 8** |
| Endpoint chips vs backend | **109 / 109** |
| API declarations, all seven layers | **0** unregistered |
| Pip resting positions | **168**, 0 blocked, 0 overflow |
| Public Landing | unchanged |
| Production | untouched |

---

## 23. Administrator deployment pack (§17.24)

Unchanged in shape from the 19 August pack; the release directory name is the
only difference. Deployment is a systemd unit change and is the Administrator's
to execute. **I have not run any of this.**

**Current unit, verbatim** (`/etc/systemd/system/eilps-learner.service`):

```ini
[Unit]
Description=IELPS immutable A1-C2 learner experience
After=network.target eilps-web.service
Wants=eilps-web.service

[Service]
Type=simple
User=anirudhat
Group=anirudhat
WorkingDirectory=/home/anirudhat/eilps/releases/ielps-a1-c2-learner-20260805-r4-discovery
Environment=NODE_ENV=production
Environment=PORT=4302
Environment=DIST=/home/anirudhat/eilps/releases/ielps-a1-c2-learner-20260805-r4-discovery/out
ExecStart=/usr/bin/node /home/anirudhat/eilps/releases/ielps-a1-c2-learner-20260805-r4-discovery/runtime/learner-server.mjs
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

The live release is a **static export** served from `out/`. This candidate is a
**Next.js standalone build** that runs its own server. That is why a unit change
is unavoidable and why this is not something I can do.

**Four lines change, one is deleted:**

```ini
WorkingDirectory=/home/anirudhat/eilps/releases/ielps-learner-20260819-bc2c8ca
Environment=PORT=4302
Environment=HOSTNAME=127.0.0.1
ExecStart=/usr/bin/node /home/anirudhat/eilps/releases/ielps-learner-20260819-bc2c8ca/server.js
# Environment=DIST=...   ← delete this line, standalone does not use it
```

**Steps:**

1. Unpack the release to
   `/home/anirudhat/eilps/releases/ielps-learner-20260819-bc2c8ca/`. It must
   contain `server.js`, `.next/` and `public/`.
2. Edit the unit as above.
3. `systemctl daemon-reload`
4. `systemctl restart eilps-learner`
5. Run the health checks below.

**Expected interruption:** a few seconds while the service restarts. `/learner/`
is briefly unavailable. Nothing else on the box is affected — `eilps-web` and the
API on 4300 are untouched.

**Health checks, against real URLs.** I ran every one of them locally against
this build first.

| # | Check | Expected |
| --- | --- | --- |
| 1 | `curl -s -o /dev/null -w '%{http_code}' https://eilps.com/learner/` | `200` |
| 2 | `curl -s https://eilps.com/learner/ \| grep -c 'Your chosen level'` | `0` |
| 3 | `curl -s -o /dev/null -w '%{http_code}' https://eilps.com/learner/access/` | `404` |
| 4 | `curl -s -o /dev/null -w '%{http_code}' https://eilps.com/learner/levels/a1/` | `404` |
| 5 | `curl -s https://eilps.com/learner/app/adult/ \| grep -c 'ielps-pip'` | `≥1` |
| 6 | `curl -s https://eilps.com/learner/app/studio/credits/ \| grep -c 'AI Credits'` | `≥1` |
| 7 | `curl -s -o /dev/null -w '%{http_code}' https://eilps.com/learner/app/admin/overview/` | `200` — the page loads; the data is refused server-side without the role |
| 8 | `curl -s https://eilps.com/learner/ \| grep -c 'Platform Administration'` | `0` — not on the Access Panel |

**Rollback:** restore the four lines to the verbatim values above,
`systemctl daemon-reload`, `systemctl restart eilps-learner`. The current release
directory is left in place and untouched, so rollback is a unit edit and a
restart — no file restore, no data change.

---

## 24. Evidence index

| File | What it is |
| --- | --- |
| `SOURCE-SHA256-19b.txt` | Per-file SHA-256, 125 files |
| `backend-routes-19aug-b.txt` | 266 registrations re-extracted from backend source today |
| `api-audit-19b.json` | The seven-layer audit, every declaration with its verdict |
| `actions-19b.json` | 65 checks: wired actions, role states, Administration boundary |
| `functional-19b.json` | 59 functional checks |
| `cert-blob-19b.json` | 8 certificate binary-path scenarios with request logs |
| `pip-settled-19b.json` | All 168 resting measurements and the tuck conditions |
| `density-19b.json` | Text density at 1280 |
| `BACKEND-PATCH-PROPOSALS.md` | The three backend changes, written for approval |
| `AI-CREDITS-IMPLEMENTATION-NOTE.md` | §9/§14 server-side proposal, updated to record the hold |
| `api_audit_19b.py` · `extract_routes_19b.py` | The audit and the route extractor |
| `actions_19b.py` · `functional19b.py` · `pip_settled_19b.py` · `cert_blob_test.mjs` · `verify_chips.py` · `capture19b.py` | The rest of the harness |
| `shots19b/*.png` | Captures at 1280 / 900 / 390 |

---

## 25. Still open

1. **Deployment.** NOT DEPLOY APPROVED. Production stays as it is until you
   approve `bc2c8ca`.
2. **The engine refresh role check.** The backend has none today. Patch written,
   not applied — it needs a deploy approval that covers backend changes.
3. **Two thresholds to approve.** Safety-report limit and window; dynamic-voice
   limit and text bound. Suggested values in the proposals; none applied.
4. **AI Credits commercial values.** Allowance per tier and rollover, conversion
   rate per scenario, whether top-ups are enabled and at what sizes. All on hold
   per §14.
5. **Partner link and payout detail.** No backend routes exist. Say if you want
   them and I will propose them.
6. **The 16px Pip handle.** One line either way.
7. **Lesson Player.** SIGNED-IN TEST OUTSTANDING. It turns green with an
   authorised non-charging QA entitlement; I am not making a live charge.
8. **The Personalised $3 Trial.** Excluded from this pass, per your hold.
