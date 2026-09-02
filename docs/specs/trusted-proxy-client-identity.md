---
status: frozen
title: Trusted-Proxy Client Identity
source: external
source_doc: _product-backlog.md #2 (2026-09-02 issue triage, GH #16)
created: 2026-09-02
frozen: 2026-09-02
primary_domain: api
secondary_domains: [security]
---

# Trusted-Proxy Client Identity

Unknown Is Not Zero epic **#2** (review-finding, P1). The rate limiter identifies every request by the
address of whatever connected to it, so behind a reverse proxy the whole world is one client.

## The defect

`backend/limiter.py`:

```python
limiter = Limiter(key_func=get_remote_address)
```

`get_remote_address` reads `request.client.host`. With a proxy in front that is the proxy's own
address, so every user shares one rate-limit bucket: `/api/backtest`, `/api/v4/sniper/candidates`,
`/api/v4/meta` and the five `/api/strategies` mutations all become first-come-first-served across the
entire user base, and an innocent second user gets 429.

**A correction to how this was first written up.** The backlog and the triage note said "the
documented Nginx/Docker deployment". This project documents **no** reverse-proxy deployment:
`docker-compose.yml` publishes `8000:8000` directly. What is true is narrower and still sufficient —
the shipped compose file carries a commented `CORS_ORIGINS` for a separately-hosted frontend, and
putting a proxy in front is the ordinary way to add TLS to a container that speaks plain HTTP. Anyone
who does so loses per-client rate limiting **silently**, because nothing errors and the limiter keeps
working; it just counts everyone as one person.

## Why the obvious fix is worse than the bug

GH #16 asks for `X-Forwarded-For` to be preferred when present. **That header is set by the client.**
Trusting it unconditionally means anyone can send a random address per request and never be limited
at all — trading "innocent users are blocked" for "rate limiting does nothing", on the endpoints that
run a backtest and retrain-adjacent work.

The header is also not a single value. Each proxy **appends** the address it received from, so with
`client → CDN → nginx → app` the app sees `X-Forwarded-For: <client>, <cdn>` and
`request.client.host = nginx`. Entries are trustworthy from the **right**, one per proxy under our
control; everything to the left of that came from outside and can say anything.

## Goal

An operator running behind their own proxy can get correct per-client rate limiting by stating how
many proxies they run. An operator who does nothing keeps today's behaviour exactly. Neither can be
bypassed by a header a stranger sets.

## Acceptance Criteria

1. **[FROM-SOURCE]** `TRUSTED_PROXY_COUNT` (`core/config.py`, env-overridable, **default `0`**)
   declares how many proxies of ours sit in front of the app.

2. **[FROM-SOURCE]** At `0` the key is `request.client.host`, byte-identical to today. Doing nothing
   must not change behaviour, and a default that trusts a header is not a safe default.

3. **[FROM-SOURCE]** At `N > 0` the key is the **Nth entry from the right** of `X-Forwarded-For` —
   the boundary between the proxies we run and the world. Entries left of it are ignored.

4. **[INFERRED]** It **fails closed**. If the header is absent, has fewer than `N` entries, or the
   selected entry is not a valid IP address, the key falls back to `request.client.host`. A request
   that did not arrive through the declared chain is not trusted to describe itself — and a shorter
   header is exactly what an attacker sends.

5. **[INFERRED]** A negative or non-integer `TRUSTED_PROXY_COUNT` is a configuration error and fails
   at import, not at request time. A limiter that silently mis-parses its own configuration is worse
   than one that is off.

6. **[INFERRED]** The selected identity is what `@limiter.limit` actually keys on. A test must
   exercise a real limited endpoint through the app and observe that two clients behind one proxy
   get **separate** budgets while today they share one — asserting on the helper alone would not
   prove the wiring.

7. **[INFERRED]** Documented where an operator will look: a `TRUSTED_PROXY_COUNT` row in
   `docs/CONFIGURATION.md`, a commented entry in `docker-compose.yml`, and a sentence saying what
   goes wrong in **both** directions — leaving it at `0` behind a proxy limits everyone as one, and
   setting it higher than the real number of proxies lets a client choose its own identity.

8. **[INFERRED]** No new dependency. `slowapi`'s `key_func` contract is unchanged; this replaces the
   function, not the mechanism.

## Non-goals

- **Trusting proxies by address.** A `TRUSTED_PROXY_IPS` allow-list is the more precise design and a
  larger one: it needs CIDR parsing, and in the container deployments this project targets the proxy
  address is frequently dynamic. The hop count is the standard reduced form and is what an operator
  can state correctly without inspecting their network.
- **`Forwarded` (RFC 7239) or `X-Real-IP`.** One header, one rule. Accepting several would multiply
  the ways a chain can be mis-declared for no gain to anyone.
- **Changing any rate limit.** The values in `core/config.py` are untouched; only who they are
  counted against changes.
- **Using the identity for anything but rate limiting.** No logging, storage, or per-user behaviour
  is derived from it.

## Constraints

- **The default must not be exploitable.** `0` is the only value that requires no trust.
- **No secrets, no PII storage.** The identity is used for an in-memory counter and never persisted.
- `backend/limiter.py` exists to avoid a circular import between `main.py` and `routes/*` — it must
  stay free of route imports.

## Domain Decisions

- **[DECISION]** Count from the **right**, never the left. `X-Forwarded-For[0]` is the value most
  guides reach for and is the one entry an attacker fully controls.
- **[CONSTRAINT]** Fail closed on a short header. Falling back to `request.client.host` when the
  chain does not match means a spoofing attempt is rate-limited as the proxy — degraded, not open.
- **[DECISION]** Configuration errors are import-time failures. A rate limiter that starts with a
  mis-parsed trust boundary offers protection it does not have.
- **[TRADEOFF]** A hop count is cruder than an address allow-list and misidentifies clients if the
  operator states the wrong number. Chosen because it is the form an operator can get right from
  their own compose file, and because the failure mode is disclosed rather than silent.
- **[CONSTRAINT]** This is a **correctness** fix for the deployments it applies to, not a security
  hardening of the default. At `0` the app is exactly as exposed as it was.

## File Relationship

INDEPENDENT. Touches no spec's behaviour; `backend/limiter.py` has never had one.
