# Three backend changes this pass needs, written up for approval

19 August 2026 · prepared against `~/eilps/backend/src` as it runs today.

**None of this has been applied.** Production is untouched and deployment is
not approved. Each item below states what I found, what I propose, and what it
would change for a caller — so the decision can be made from the text rather
than from a diff.

---

## 1. `POST /api/engine/refresh` has no administrator check to retain

§7 says the explicit Platform Administrator role check on this route should be
retained, and that authentication alone is not sufficient. I went to check it
before building the surface around it, and it is not there.

`backend/src/engine.js`, as deployed:

```js
const router = express.Router();
router.use(authRequired);
...
router.post('/refresh', asyncHandler(async (req, res) => { await idx.refresh(); res.json({ refreshed: true }); }));
```

`authRequired` is the only gate. There is no role read, no `adminRequired`, and
nothing route-specific. So today **any signed-in account** — an adult learner, a
parent, a teacher, a school member without a platform role, a Studio creator —
can rebuild the whole platform's content index by posting to this route. The
expected results table in §7 describes the behaviour we want, not the behaviour
the server currently has, and I would rather say so than quietly build a
frontend that implies otherwise.

I have not changed it, because production is not deploy-approved in this pass
and a permission change is not something to slip in alongside a frontend
release.

**Proposed patch.** The platform already has exactly the pattern needed, in
`backend/src/admin.js`, so this introduces nothing new:

```js
// backend/src/engine.js
const { asyncHandler, authRequired } = require('./middleware');
const { query } = require('./db');

// Same RBAC as the /api/admin router: authenticated AND role='admin' in the
// database. Declared here rather than router-wide so the learner-facing engine
// routes are unaffected.
const adminRequired = asyncHandler(async (req, res, next) => {
  const { rows } = await query('SELECT role FROM users WHERE id=$1', [req.user.id]);
  if (!rows[0] || rows[0].role !== 'admin') {
    return res.status(403).json({ error: 'forbidden', message: 'Administrator role required.' });
  }
  next();
});

router.post('/refresh', adminRequired, asyncHandler(async (req, res) => {
  await idx.refresh();
  res.json({ refreshed: true });
}));
```

**What each caller would then get**, which is §7's table exactly:

| Caller | Result |
| --- | --- |
| Signed out | 401 — `authRequired` refuses before the handler |
| Adult learner | 403 |
| Parent | 403 |
| Teacher | 403 |
| School role without Platform Administrator | 403 |
| Studio creator | 403 |
| Platform Administrator | 200 `{ refreshed: true }` |

**What it does not touch.** Only `/refresh`. `GET /api/engine/next`, `/mastery`,
`/schedule`, `/path`, `/review-queue` and `POST /api/engine/attempts` are the
learner's own adaptive engine and keep exactly the authentication they have.

**Message wording.** `Administrator role required.` is deliberate: the panel's
classifier reads the word `administrator` to distinguish an administrator
refusal from an ordinary permission refusal. I have also widened the classifier
this pass so the existing `Admin access required.` from `admin.js` is recognised
too, so the frontend is correct either way and the day this patch lands nothing
in the candidate has to change.

---

## 2. `POST /api/compliance/safety-reports` needs a per-user bound, and a threshold I am not going to guess

§15 asks for an established per-user abuse or rate control that prevents
flooding without silently discarding a legitimate safeguarding report, and says
that where no approved threshold exists I should return a proposal rather than
pick one. So here is the proposal, and the number is yours.

**What exists today.** `backend/src/index.js`:

```js
const apiLimiter = rateLimit({ windowMs: 60_000, limit: Number(process.env.API_RATE_LIMIT_PER_MINUTE || 600), ... });
app.use('/api', apiLimiter);
const authLimiter = rateLimit({ windowMs: 60_000, limit: 30, ... });
app.use('/api/auth', authLimiter, auth.router);
```

Two things follow. `express-rate-limit` is already the house pattern, so this
needs no new dependency. And both existing limiters key on IP, which is the
wrong key here: a school behind one NAT address shares an IP, so an IP-keyed
limit on safeguarding would let one abuser silence a whole school's ability to
report. The limit has to be per account.

**Proposed patch**, in `backend/src/compliance.js`:

```js
const rateLimit = require('express-rate-limit');

const safetyReportLimiter = rateLimit({
  windowMs: Number(process.env.SAFETY_REPORT_WINDOW_MS || 3_600_000),
  limit: Number(process.env.SAFETY_REPORT_LIMIT || 20),
  standardHeaders: true,
  legacyHeaders: false,
  // Per account, never per IP: a school shares one address, and one abuser
  // must not be able to stop everybody else reporting.
  keyGenerator: (req) => String(req.user?.id || req.ip),
  handler: (req, res) => res.status(429).json({
    error: 'rate_limited',
    message: 'Too many reports from this account in a short period. This report was not recorded. If this is urgent, contact your safeguarding lead directly.',
  }),
});

router.post('/safety-reports', safetyReportLimiter, asyncHandler(async (req, res) => { ... }));
```

**The property that matters.** Nothing is silently discarded. A caller over the
bound gets a 429 that says plainly that the report was **not** recorded and
gives them a route that does not depend on this system. A silent drop would be
worse than no limit at all, because the reporter would believe they had
reported.

**The values are for you to set, and are environment variables so they can be
changed without a code change.** My suggestion, offered as a starting point and
not applied: **20 reports per account per hour**. A genuine reporter filing for
several learners after an incident stays well inside it; a script does not.
Both numbers are `SAFETY_REPORT_LIMIT` and `SAFETY_REPORT_WINDOW_MS`.

Two options if you would rather not cap a safeguarding route at all: raise the
limit and add a review flag instead of a refusal, or keep the limit but exempt
accounts holding a safeguarding role. Say which and I will write it that way.

---

## 3. Public Agent: separate free navigation from the billable branch

§15 asks that the public multilingual Agent stay public, that low-cost public
navigation be separated from potentially billable dynamic provider work, and
that bounded cost protection be applied to the latter rather than requiring
sign-in for ordinary navigation.

**What is actually billable.** I read `backend/src/agent.js` rather than assume:

| Route | Cost | Why |
| --- | --- | --- |
| `GET /api/agent/config` | free | Reads the shipped manifest and cached audio URLs |
| `POST /api/agent/chat` | free | `responseFor()` is deterministic, from the manifest. No provider is called |
| `POST /api/agent/voice` — cached | free | Returns an existing `audioUrl` from disk |
| `POST /api/agent/voice` — dynamic | **billable** | Calls ElevenLabs. Reached by `forceDynamic: true`, free `text`, or a script/language with no cached clip |

So the billable surface is one branch of one route, and everything a visitor
needs in order to navigate the site is on the free side of it.

**What the candidate already does.** Pip calls `/api/agent/chat` only. It never
calls `/api/agent/voice`, never sets `forceDynamic`, and plays only the cached
clip a chat response names. It also bounds a single question to 400 characters
before the request is built. That is the frontend half, and it is in this
release.

**Proposed patch**, the server half, in `backend/src/agent.js`:

```js
const rateLimit = require('express-rate-limit');

// Bounds the paid branch only. Cached playback and navigation never reach it.
const dynamicVoiceLimiter = rateLimit({
  windowMs: 3_600_000,
  limit: Number(process.env.AGENT_DYNAMIC_VOICE_LIMIT || 15),
  keyGenerator: (req) => String(req.user?.id || req.ip),
  handler: (req, res) => res.status(429).json({ error: 'rate_limited' }),
});

router.post('/voice', asyncHandler(async (req, res) => {
  const language = languageFromRequest(req, req.body.language || req.body.browserLanguage);
  const scriptId = safeScriptId(req.body.scriptId || 'welcome');
  const cached = cachedAudio(scriptId, language);
  // Cached first, always, and before any bound is consulted.
  if (cached.audioUrl && !req.body.forceDynamic) {
    return res.json({ ...cached, provider: manifest.provider.name });
  }
  // Only now is this billable, so only now does the bound apply.
  return dynamicVoiceLimiter(req, res, () => generateAndRespond(req, res, { scriptId, language }));
}));
```

with two bounds inside the dynamic branch: refuse text longer than
`AGENT_DYNAMIC_TEXT_MAX` (suggested 600 characters), and on refusal fall back to
the caption rather than to an error, so a visitor loses the voice and keeps the
answer.

**No sign-in is added anywhere.** Config, chat and cached voice stay public and
unmetered, which is the whole point: navigation is what the public Agent is for.

**Values to approve:** `AGENT_DYNAMIC_VOICE_LIMIT` (suggested 15 per hour per
caller) and `AGENT_DYNAMIC_TEXT_MAX` (suggested 600 characters). Both
environment variables, both yours to set.

---

## What I would need in order to apply any of this

A deploy approval that covers backend changes, which this pass does not have.
Each of the three is small, reversible by reverting one file, and independent of
the other two, so they can be approved separately or in any order.
