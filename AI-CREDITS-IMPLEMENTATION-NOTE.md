# Studio AI Credits — proposed server-side flow and the exact changes it needs

19 August 2026 · prepared to §9 of the *Final Pre-Deployment Corrections
(Revised Pip Rule)*, and revised the same day against §14 of the *Post-83CC
Final Wiring & Conformance Instruction*.

**Status after that review.** The hold-then-settle shape below is approved as
the future accounting architecture, for the reason it was proposed: failed
provider work must not leave an unjustified final charge. Everything else is on
hold — the migration is not to be run, no top-up product is to be created, and
no monthly quantity, conversion rate or package price is to be invented. That
is exactly the state this note is in.

**Nothing in this note has been applied.** No migration has been run, no route
has been added, no Stripe object has been created and no price appears anywhere.
The UI half of §9 is in the candidate as `/app/studio/credits/`; this is the
server half, written up for approval rather than built.

---

## 1. What is being metered, and what is not

The approved model is: a Studio subscription includes a monthly allowance of AI
Credits, billable AI generation consumes them, and top-ups are optional where
enabled. Two consequences drive the whole design.

**A credit is only ever spent when a paid provider workload actually starts.**
Opening AI Governance costs nothing. Nor does creating or opening a project,
listing or reading generations you already have, editing by hand, human review,
or previewing before publication. None of those calls a provider, so none of
them touches the ledger.

**Credits are the creator-facing unit.** Tokens, voice characters and message
counts stay where they already live — `ai_usage` — and are never shown to a
creator as the thing they are buying. The conversion from provider units to
credits is a server-side rate that an administrator sets; it is not a price, and
this note does not propose a value for it.

## 2. The credit-event flow

The flow is a hold-then-settle, because §9 requires that failed provider work
must not leave an unjustified final charge. A single "deduct on request" write
cannot satisfy that: if the provider fails after the deduction, the creator has
paid for nothing.

```
  creator asks for a generation
        │
        ▼
  1. server checks the balance                  ── ledger read, no write
        │  insufficient → 402, nothing is spent, nothing is queued
        ▼
  2. server writes a HOLD                       ── ledger row, status 'held'
        │     estimated cost, from the workload type and size
        ▼
  3. provider workload runs
        │
        ├── usable output ──▶ 4a. SETTLE        ── status 'settled', amount
        │                          rewritten to the actual measured cost
        │                          from ai_usage; any difference between the
        │                          estimate and the real cost is released
        │
        └── failure, timeout, ──▶ 4b. RELEASE   ── status 'released', amount 0
            or unusable output         the hold is voided, balance restored
        │
        ▼
  5. balance = grant rows + top-up rows − settled rows − open holds
```

Points worth stating plainly:

- **The server is the only authority.** The balance is never computed in the
  browser and never sent as an input. `/app/studio/credits/` reads it and
  displays it; it does not calculate it.
- **The ledger is append-only.** A hold is not deleted when it settles; its
  status changes and the amount is rewritten to the measured cost. Every state
  a charge has been in is recoverable.
- **Holds expire.** A workload that never reports back must not pin a creator's
  credits forever. A hold older than a fixed window is released by the same job
  that already sweeps `operations/jobs`.
- **Idempotency.** Each ledger row carries the generation id it belongs to, with
  a unique constraint, so a retried request cannot double-charge.
- **A grant is a row, not a counter.** The monthly allowance is written as a
  ledger entry when the subscription period rolls over, which means an
  allowance change is auditable and a mistaken grant can be reversed by a
  compensating row rather than by editing a total.

## 3. Database changes

One new migration, `migrations/025_studio_ai_credits.sql`, following the shape
already used by `006_partners.sql` for `partner_ledger`. Two tables and one
index; no existing table is altered and no existing column changes meaning.

```sql
-- Every movement of credits, append-only.
CREATE TABLE IF NOT EXISTS ai_credit_ledger (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind          text NOT NULL,        -- 'grant' | 'topup' | 'spend' | 'adjustment'
  credits       integer NOT NULL,     -- positive adds, negative consumes
  status        text NOT NULL DEFAULT 'settled',  -- 'held' | 'settled' | 'released'
  generation_id text,                 -- the workload this belongs to, if any
  scenario      text,                 -- mirrors ai_usage.scenario
  note          text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  settled_at    timestamptz
);
CREATE INDEX IF NOT EXISTS ai_credit_ledger_user
  ON ai_credit_ledger(user_id, created_at DESC);
-- One ledger row per workload: a retry cannot charge twice.
CREATE UNIQUE INDEX IF NOT EXISTS ai_credit_ledger_generation
  ON ai_credit_ledger(generation_id) WHERE generation_id IS NOT NULL;

-- What a tier includes, and how provider units convert. Administrator-set.
CREATE TABLE IF NOT EXISTS ai_credit_policy (
  tier                text PRIMARY KEY,      -- matches subscriptions.tier
  monthly_credits     integer NOT NULL DEFAULT 0,
  rollover_allowed    boolean NOT NULL DEFAULT false,
  topups_enabled      boolean NOT NULL DEFAULT false,
  updated_at          timestamptz NOT NULL DEFAULT now()
);
```

`ai_credit_policy` deliberately ships **empty**. Nothing here assumes an
allowance for any tier; the table exists so that the values can be set once
approved, in one place, rather than being scattered through code.

The per-scenario conversion rate belongs alongside it — either a third small
table or a `jsonb` column on `ai_credit_policy` — but the choice depends on
whether rates vary by tier, which is a commercial question, so it is left open.

## 4. Billing changes

Two, and only two.

**Grant on period rollover.** `billing.js` already handles the Stripe
subscription lifecycle and writes to `subscriptions`. Where it updates
`current_period_end`, it also writes one `kind='grant'` row for the tier's
`monthly_credits`. Nothing new is added to the webhook surface, and no new
webhook event type is subscribed to.

**Top-up purchase.** Only when top-ups are switched on. It reuses the existing
one-time payment path — `POST /api/payments/create-one-time-session` — rather
than introducing a second checkout mechanism, and on the existing
`checkout.session.completed` handling it writes one `kind='topup'` row. Because
`billing_events` already stores every Stripe event by id, replay protection is
inherited rather than reinvented.

**Not proposed:** no Stripe Product, no Price, no package definition and no
figure of any kind. Those are the commercial values §9 keeps separately
approval-gated, and none is assumed here.

## 5. Routes

Three, all under the existing `/api/studio/ai` mount, so no new router and no
new prefix:

| Route | Purpose |
| --- | --- |
| `GET /api/studio/ai/credits` | balance, current period, recent ledger rows |
| `POST /api/studio/ai/credits/hold` | internal to a generation request; not called by the browser directly |
| `POST /api/studio/ai/credits/settle` | internal; settles or releases a hold |

The two `POST` routes are server-internal steps in the generation path, not a
creator-facing API. They are listed for completeness, not as a surface a Studio
user calls.

**No chip for any of these appears in the candidate.** They do not exist yet,
and a visible label for a route that is not registered is exactly what the API
truthfulness rule forbids. `/app/studio/credits/` therefore carries no endpoint
chip at all, and its balance panel says in plain words that it will read the
figure once the endpoint is built, rather than showing an example one.

## 6. Permissions

`studio_ai_governance.js` already gates on `authRequired` plus a Studio account
check, and the credit routes sit behind the same two. A creator can read their
own balance and their own ledger, and nothing else: no other account's rows, no
provider cost, no rate configuration, no administrator policy.

Setting `ai_credit_policy` is administrator-only and is not exposed to Studio in
any form.

## 7. What is still needed before any of this can be built

The design question is closed: hold-then-settle is approved. What remains is
commercial, and none of it is mine to choose. Nothing here has been assumed, and
the tables above ship empty precisely so that these can be set once, in one
place, rather than being scattered through code.

1. The allowance per tier, and whether unused credits roll over.
2. The conversion rate from provider work to credits, per scenario.
3. Whether top-ups are enabled at all, and if so the package sizes and prices.

Until those arrive, `/app/studio/credits/` shows the prepared model and says
plainly that server accounting is not active. It carries no balance, no price,
no package and no endpoint chip, because none of those exist yet.
