
# Work Log: feat/trusted-proxy-identity

## Header

- Branch: `feat/trusted-proxy-identity`
- Classification: `feature`
- Classified by: `claude-opus-5`
- Frozen: `2026-09-02`
- Created Date: `2026-09-02`
- Owner: `KbWen`
- Guardrails Mode: `Full`
- Current Phase: `test`
- Diff Base SHA: `edf9050` <!-- immutable: set once on first /implement -->
- Checkpoint SHA: `pending` <!-- mutable: refresh each commit -->
- Recommended Skills: `none`
- Primary Domain Snapshot: `api`
- SSoT Sequence: `11`

---

## Session Info

> Written by /bootstrap. Update on each new session.

- Agent: `claude-opus-5`
- Session: `2026-09-02 17:00 UTC`
- Platform: `claude-code`
- Files Read: `0` (optional — running count of file reads across this session for token-budget instrumentation; bootstrap may seed `0`, later phases may increment when material).

---

## Task Description

Unknown Is Not Zero epic #2 (GH #16). `backend/limiter.py` keys rate limits on the connecting
address, so behind any reverse proxy every user shares one bucket and the second user gets a 429.
The fix the issue asks for -- prefer `X-Forwarded-For` -- would be worse: that header is set by the
client. Spec: `docs/specs/trusted-proxy-client-identity.md`.

---

## Phase Sequence

> Record each phase entry in order. Update `Current Phase` in the Header on entry.

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-09-02 | `feature`; spec frozen |
| plan | done | 2026-09-02 | Hop count from the right, default 0, fail closed |
| implement | done | 2026-09-02 | 13 tests; 6 mutations caught |
| review | done | 2026-09-02 | Both NOT READY; a real bypass and a DoS path this change introduced |
| test | done | 2026-09-02 | 393 backend; 6 more mutations caught; order guard added |
| handoff | pending | — | — |
| ship | pending | — | — |

---

## Phase Summary

**bootstrap** — `feature`. Corrected the write-up's premise before freezing: the backlog said "the
documented Nginx/Docker deployment", but this project documents **no** proxy deployment
(`docker-compose.yml` publishes 8000 directly). The narrower true statement still carries the
feature — its commented `CORS_ORIGINS` anticipates a separate frontend, and a proxy is the ordinary
way to add TLS.

**plan** — Hop count, not an address allow-list: an operator can state the number of proxies they
run without inspecting their network, and in container deployments the proxy address is often
dynamic. Read from the **right** (each proxy appends what it saw), default `0`, fail closed.

**implement** — `TRUSTED_PROXY_COUNT` with an import-time guard; `client_identity()` replaces
`get_remote_address` as the `key_func`. One test premise was wrong and the code was right: a chain
longer than declared still selects the client correctly, so that case moved from fail-closed to its
own assertion rather than being weakened.

**review** — Both `NOT READY`, and each found something the other did not.

The reviewer found an **exploitable bypass**: `request.headers.get` returns only the first of
repeated header lines, and `X-Forwarded-For` is list-typed, so repeated lines are one comma-joined
value. A caller sending its own line **ahead** of the proxy's got an identity of its choosing —
demonstrated as four requests against a 1/minute budget, all `200`. Fixed with `getlist` + join.

The tenth-man found a **failure mode this change introduced**: a forwarded identity is chosen by
whoever writes the header, and slowapi keeps one in-process counter per identity with an O(total
keys) expiry sweep on a 0.01s timer. Measured on the shipped branch: 2000 requests → 2000 keys, all
`200`, where the pre-change code produced exactly **one** key behind a proxy. The key space is now
bounded, so a forged chain degrades to the old shared bucket instead of growing without limit.

**And "fails closed / never open" was simply false** — my sentence, in the code, the spec and two
docs. The function checks the chain's **length**, never who wrote it, so an over-declared count is
undetectable from inside the app. The claim in the code also had the threat backwards: a spoofing
attempt sends a **long** header, not a short one. Both corrected, and the docs now state the three
conditions the design depends on — every counted proxy appends (**nginx does not by default**), the
origin is unreachable except through them, and the count is right.

⚡ ACX

---

## Gate Evidence

> Gate receipts written by each phase. Format: `- Gate: <phase> | Verdict: PASS | Classification: <type> | Timestamp: <ISO>`
> **Critical**: `|` pipe separators are mandatory. Receipts placed inside markdown code fences are silently masked and NOT counted by validate.sh — always write receipts as plain list lines.
> Receipt order-of-appearance is authoritative for phase progression.

- Gate: bootstrap | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T17:00:00Z
- Gate: plan | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T17:05:00Z
- Gate: implement | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T17:40:00Z
- Gate: review | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T19:00:00Z
- Gate: test | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T19:10:00Z

---

## External References

> Links to specs, ADRs, issues, PRs, or design docs relevant to this task.

| Type | Path / URL | Notes |
|---|---|---|
| Spec | `docs/specs/trusted-proxy-client-identity.md` | Frozen 2026-09-02 |
| Backlog | `docs/specs/_product-backlog.md` #2 | Unknown Is Not Zero epic |
| Issue | https://github.com/KbWen/smart-stock/issues/16 | Source |
| ADR | — | No architecture decision; `slowapi`'s key_func contract is unchanged |
| PR | — | filled at ship |

---

## Known Risk

Root Cause: the limiter answered "who is this?" with "whoever opened the socket", which is only the
client when nothing sits in front.

- **Setting the count too high is the dangerous direction** and looks as harmless as setting it too
  low. Documented in both directions in `docs/CONFIGURATION.md`; there is no way to detect it from
  inside the app.
- **A hop count is cruder than an address allow-list** and misidentifies clients if the operator
  states the wrong number. Accepted: it is the form an operator can get right from their own compose
  file.
- **The default changes nothing**, so nobody behind a proxy is helped until they act. That is the
  only safe default — a default that trusts a client-set header is not one.

---

## Decisions

> Optional (`/decide` §2): record trade-offs/constraints as `### D-N: <title>` with Decision/Reason/Alternatives/Impact lines. At `/ship`, every entry gets one disposition marker: `→ promoted: ADR-<id>` / `→ consolidated: L2 <domain>` / `→ local`.

none

---

## Conflict Resolution

> Record skill conflicts resolved during bootstrap (from skill_conflict_matrix.md). Format: `<skill-A> vs <skill-B>: <chosen approach>`.

none

---

## Skill Notes

> Cache for loaded skills. Written by phase-entry skill loading. Leave as `none` until populated.

none

---

## Drift Log

> Record deviations from the original plan, reclassifications, or unexpected scope changes.

none

---

## Review Feedback

> Written by /review (fix suggestions + NOT READY findings).

All resolved, each pinned by a test that fails when the fix is reverted.

| # | Finding | Raised by | Resolution |
|---|---|---|---|
| H1 | `headers.get` reads only the first of repeated `X-Forwarded-For` lines — a caller sending its line ahead of the proxy's got an identity of its choosing and no limit (4 requests, 1/min budget, all 200) | reviewer | `",".join(headers.getlist(...))` + a regression test using real repeated header lines |
| H2 | A forged chain could mint one limiter key per request; slowapi's store is in-process with an O(n) sweep on a 0.01s timer. 2000 requests → 2000 keys. **The pre-change code produced one key.** | tenth-man | `MAX_TRACKED_FORWARDED_CLIENTS` per window; past the cap new identities are limited per peer, established ones keep their budget |
| H3 | "fails closed / never open" is false: the app checks chain **length**, never authorship — and the code had the threat backwards (a spoof sends a **long** header) | tenth-man | Claim removed from code, spec and both docs; replaced with what is true and the three conditions the design needs |
| M1 | `docs/guides/rate-limiting.md` still taught `get_remote_address` as the key | reviewer | Rewritten; `troubleshooting.md`'s 429 entry now points at `TRUSTED_PROXY_COUNT` |
| M2 | Nothing surfaces a mis-declared count in either direction | tenth-man | Startup line naming the mode + one-time warning per condition |
| M3 | `<ip>:<port>` entries (Azure App Gateway) parsed as invalid → silent no-op | tenth-man | `_parse_address` accepts `ipv4:port` and `[ipv6]:port` |
| M4 | New test file order-dependent — passes only because its name sorts after `test_backtest.py` | tenth-man | `sys.modules.pop("core.data")` guard, matching `test_transparency.py` |
| M5 | AC6 asked for a real limited endpoint; the proof ran on the fixture's route | reviewer | Behavioural assertions added against `/api/transparency` on `backend.main.app` |
| M6 | `int()` accepts `"1_0"` as 10 — over-declaration by typo, silently | reviewer | Strict `re.fullmatch(r"\d+", ...)` with an explanatory error |
| L1 | CHANGELOG overstated the symptom; spec miscounted the affected endpoints; a docstring absolute was untrue | reviewer | All three corrected |
| L2 | `.env.example` did not mention the variable | tenth-man | Added with both failure directions |

---

## Red Team Findings

> Written by /review and /test when adversarial testing runs. HIGH findings do not block but MUST record a risk decision here.

none

---

## Design Reference

> Populated by /plan for UI tasks. If not a UI task, write `none`.
> Format: `Link: <DSoT URL or file path> | Tool: <Stitch | Figma | Pencil | other>`

none

---

## Observability

> Populated by /ship for feature/architecture-change tasks. Document the production error sink used in changed code.
> Format: `Sink: <logger name or API> | Scope: <files> | Verified: <yes/no>`

none

---

## Resume

> Populated by /handoff for feature/architecture-change tasks. Required: `State`, `Completed`, `Next`, `Context` fields; then `### Read Map`, `### Skip List`, `### Context Snapshot`; optionally `### Backlog Status`. validate.sh enforces the three `###` headings. Leave as `none` until /handoff runs.

none

---

## Test Gate Results

> Test-phase gate outcome.

- `python -m pytest -q` -> **393 passed / 0 failed** (master: 369)
- `validate.sh` pass=105 warn=15 **fail=0**
- Order independence checked: alone, full suite, and forced after `test_backtest.py` (which was
  the failing order before the guard).

---

## Evidence

> Reproducible evidence.

- **The bypass, on the shipped branch**: `TRUSTED_PROXY_COUNT=1`, a 1/minute route, each request
  carrying the caller's own `X-Forwarded-For` line ahead of the proxy's -> `200, 200, 200, 200`
  with `seen` following the caller's forged value. After `getlist`: `200, 429, 429`, `seen` = the
  proxy's entry.
- **The key space, on the shipped branch**: `TRUSTED_PROXY_COUNT=2`, 2000 requests with an invented
  leading entry -> `{200: 2000}`, 2000 distinct storage keys. Pre-change: 200 requests ->
  `{200: 20, 429: 180}`, **1** key. Measured 296 B/key and a 14.3 ms O(n) sweep at 100k keys.
- **Twelve mutations, each killed**: read-from-left, `chain[0]`, `hops<=0`->`hops<0`, drop the
  short-chain guard, drop IP validation, drop `.strip()`, revert `key_func`, constant fallback,
  drop the negative-count guard, default `1`, remove the key-space bound, evict the established
  client, drop the `ip:port` recovery, and a startup line that stops naming the mode.
