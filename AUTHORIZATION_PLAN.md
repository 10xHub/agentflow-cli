# Scalable Object-Level Authorization — Design & Plan

Status: DONE (all steps implemented, tested, documented)
Scope: `agentflow-api` (auth layer) + `agentflow` core (`aget_thread_owner` source-of-truth lookup)

## Goal

Owner-only access to threads, enforced on **every** thread-touching step (invoke, stream,
stop, fix, and all checkpointer read/write/delete), **on by default in production** when the
developer enables auth, fully overridable, and **scalable** — no database round-trip per
request.

## Design principles

1. **Ownership is immutable.** A thread's owner is set at creation and never changes; only
   deletion removes it. Therefore the owner is safe to cache aggressively (cache-forever)
   and we essentially never re-hit the DB for a known thread.
2. **Single decision point.** One `AuthorizationBackend`, invoked before every handler. No
   per-endpoint bespoke checks.
3. **Secure by construction.** No route can ship unprotected (enforced at boot).
4. **Graceful degradation.** No checkpointer / a checkpointer that can't resolve ownership →
   warn + allow (nothing persisted to protect). Redis is optional.

## Components

### 1. Source of truth: `aget_thread_owner` (core) — DONE

`BaseCheckpointer.aget_thread_owner(thread_id) -> user_id | None`:
- base: raises `NotImplementedError` (so a backend can't silently report "no owner", which
  would defeat owner-based authorization).
- `PgCheckpointer`: `SELECT user_id FROM threads WHERE thread_id = $1`.
- `InMemoryCheckpointer`, `SqliteCheckpointer`: read the stored thread record's `user_id`.

This is the DB-level lookup the cache sits in front of. Already implemented + unit tested.

### 2. `ThreadOwnershipResolver` (the scalable cache) — NEW (`agentflow-api`)

- **L1**: in-process LRU, bounded (default 10_000), immutable owners cached with **no TTL**.
- **L2**: Redis, reusing the app's existing Redis client when configured; key
  `af:authz:owner:{thread_id}`. Gracefully L1-only when Redis is absent.
- `owner_of(thread_id) -> str | None`: L1 → L2 (fill L1) → DB `aget_thread_owner` (fill L2+L1).
  **Only positive results are cached; `None` is never cached** — a nonexistent thread can
  become owned by the very next request, so caching `None` would open a TOCTOU hole.
- `evict(thread_id)`: clears L1+L2. Called when a thread is deleted.
- Cost: first touch of a thread = 1 lookup; every subsequent request = in-process hit.

### 3. `OwnershipAuthorizationBackend` — rewire to use the resolver

Decision table (cached; no raw DB call):
- no `user_id` → deny
- non-thread resource (`store`, `files`) → allow (they self-scope)
- no `resource_id` → allow (list/create endpoints)
- `owner = resolver.owner_of(resource_id)`:
  - `None` → allow (brand-new session / empty read)
  - `owner == user_id` → allow
  - `owner != user_id` → **deny, for every action including invoke/stream**
- resolver reports unsupported backend → warn + allow; resolver error → fail closed (deny).

### 4. Secure-by-construction enforcement (fail-closed at boot)

`assert_all_routes_protected(app)` runs at startup: walk every route; any non-public route
(allowlist: `/ping`) whose dependency tree lacks `RequirePermission` makes the server
**refuse to start** with a clear error. Keeps precise per-handler `(resource, action)`, adds
zero per-request overhead, and turns a forgotten guard into a deploy-time failure instead of
a silently-open production endpoint. (Delivers the "authorization on every step" guarantee
more robustly than a literal router dependency, which cannot cleanly derive each route's
action.)

### 5. Invalidation

`CheckpointerService.delete_thread` (and the `aclean_thread` path) calls
`resolver.evict(thread_id)`.

### 6. Config surface (unchanged)

`"authorization"`: `"ownership"` | `"allow_all"`/`"default"`/`"none"` | `"module:attr"` |
unset → `ownership` in production, `allow_all` in development. Developer choice always wins.

## Test plan

- Resolver: L1 hit, L2 promote-to-L1, DB fill, negative-not-cached, evict, LRU bound.
- Backend: full decision table over the cached path.
- Startup invariant: a route missing `RequirePermission` → boot raises; allowlist passes.
- Integration: non-owner invoke/stream/read/delete → 403; owner → ok; second call served from
  cache (asserted with a call-counting fake checkpointer — no second DB hit).
- Core: `aget_thread_owner` for in-memory/sqlite (done).

## Docs

Update `docs/how-to/api-cli/add-auth.md` and `agentflow-api/CLAUDE.md`: caching model,
immutability, Redis opt-in, boot-time guarantee.

## Execution order

1. ThreadOwnershipResolver + unit tests.
2. Rewire OwnershipAuthorizationBackend onto the resolver + update tests.
3. Wire resolver into DI (loader) and evict on delete_thread.
4. Startup invariant `assert_all_routes_protected` + boot wiring + tests.
5. Integration tests (owner-only + cache-hit assertion).
6. Docs.
7. Full suite (api + core) green with coverage.
