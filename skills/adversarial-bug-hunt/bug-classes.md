# Bug-class taxonomy — hunt prompts

Hand each Hunter the section for its class. Each section = what to look for, the exact-trigger phrasing to demand, and a **Local hotspots** line for you to fill with your own codebase's real traps.

> **Fill this in first.** Add a "Stack facts every Hunter should know" paragraph here: language and concurrency model, data access (ORM or hand-written SQL, and whether calls are synchronous), the date/time library and how the clock is injected, the front-end framework and its state model, and anything **generated** (API clients, types) that can go stale. A Hunter that knows the stack finds real bugs; one that guesses reports noise.

---

## concurrency

Race conditions, TOCTOU (time-of-check/time-of-use), lost updates, shared-state conflicts, non-atomic compound operations, deadlock, starvation.

**Hunt for:**

- Check-then-act on shared state without a lock or a single atomic statement (`if (!Exists(id)) Add(...)` — two callers both pass the check).
- Read-modify-write on a database row with no optimistic-concurrency token or conditional `UPDATE … WHERE`.
- Static, singleton, or captured mutable state touched by concurrent requests.
- Fire-and-forget tasks not awaited, or background work mutating shared state.
- Compound "get count, then act on count" where another writer moves the count between the two.
- A "claim the work" query that lets two runners claim the same row.
- Retry or redelivery paths that let the same message run twice at once.

**Local hotspots:** _<fill in: the job runner, queue consumers, the claim/lease query, any static state, offline sync replay, realtime handlers mutating cached state>_

**Exact trigger demanded:** "request A does X at L\<n> between request B's Y at L\<m> and Z at L\<k>".

---

## non-determinism

Output depends on ordering, timing or environment that is not pinned.

**Hunt for:**

- A `SELECT` consumed as if ordered but with **no `ORDER BY`** (row order is undefined) — including "first row wins" logic and pagination with no stable tiebreak.
- Iterating a dictionary, set or lazy sequence and depending on order.
- Unseeded random, ambient id generation, or clock reads feeding logic or assertions.
- Culture-sensitive parsing or formatting (no invariant culture).
- Parallel accumulation into an order-sensitive structure.

**Local hotspots:** _<fill in: repository methods that take the first row, id generation at construction time, sandboxed or user-supplied code that must be reproducible, tests asserting "first row">_

**Exact trigger demanded:** "when the database returns rows in order B,A instead of A,B, line \<n> picks the wrong one".

---

## date-time

Timezone and DST boundaries, wall-clock versus absolute-instant mix-ups, ambient clock reads.

**Hunt for:**

- A platform date type used in domain code where the project's date library type belongs — and the conversion at the adapter boundary that silently assumes UTC.
- Ambient clock reads (`DateTime.Now`, `new Date()`, `time.Now()`) instead of the injected clock — untestable and non-deterministic.
- An absolute instant rendered or compared as if it were wall-clock local time, or a local date/time treated as an absolute point, with no timezone in between.
- Date arithmetic across a DST boundary done by adding a fixed duration where a zoned calendar add is meant (a "same time next day" shift becomes an hour out).
- Two different duration representations (seconds as integer versus a duration type) mixed in one calculation.
- Half-open versus closed interval slips on windows (end-exclusive versus end-inclusive).

**Local hotspots:** _<fill in: scheduling start/end fields, shift and availability windows, billing periods, anything computing "today" server-side, and the doc that governs date handling>_

**Exact trigger demanded:** "for an entry at 2026-03-29 01:30 Europe/London (DST spring-forward), line \<n> computes \<wrong value>".

---

## transaction/data

Partial-failure corruption, missing or wrong transaction scope, non-idempotent retries, foreign-key order violations.

**Hunt for:**

- Multiple writes (two aggregates, two tables) with no surrounding transaction — the first succeeds, the second throws, the database is left half-written.
- A retry path (queue redelivery, HTTP retry, user re-submit) that is not idempotent and runs the insert twice.
- Inserts in an order that violates foreign-key dependencies (child before parent).
- Side effects (email, push, queue publish, external API call) performed **before** the commit, or a commit that cannot be rolled back after the side effect fired.
- A handler returning success on a path where only part of the write completed.

**Local hotspots:** _<fill in: handlers writing more than one aggregate, linking tables, migration and seed order, send-then-mark-sent paths>_

**Exact trigger demanded:** "if line \<n> (second write) throws, rows from line \<m> are already committed, leaving \<inconsistent state>".

---

## perf/latency

N+1, sync-over-async, per-item external calls without batching, work done inside a transaction or lock.

**Hunt for:**

- A loop that issues one database query, HTTP call or email per iteration (N+1) — including a repository call inside a `foreach`.
- Fetching everything and filtering in memory what the query should filter — the whole table crosses the wire.
- Blocking on async work (`.Result`, `.Wait()`, `await` in a loop that should be parallel) causing thread-pool starvation or deadlock.
- An external call (email, SMS, push, object storage, geocoding, routing, LLM) per record with no batching.
- Heavy CPU or I/O work holding a transaction open.
- Unbounded growth: an append-only list or table with no cap or pruning.

**Local hotspots:** _<fill in: the read paths that fan out per field or per row, notification fan-out, report aggregation, any LLM or third-party call that must be time-capped>_

**Exact trigger demanded:** "for N=\<realistic count> records, this makes N sequential \<calls>, so total ≈ N × \<per-call> — pathological".

---

## error-handling

Swallowed exceptions, over-broad catch, unhandled promise rejection, lost error context.

**Hunt for:**

- `catch { }` or a catch that logs and then continues as if the call succeeded.
- A catch that returns a default or empty response, masking a real failure upstream.
- A handler returning a generic error value the caller cannot tell apart from a different failure.
- Front end: the success flag not checked, or the error list ignored and never mapped to anything the user sees; a subscription with no error arm; a promise neither awaited nor caught.
- Re-throw that drops the stack (`throw ex;` instead of `throw;`).

**Local hotspots:** _<fill in: handlers that swallow "to not break the request", the request pipeline's error middleware, front-end services that only handle the success branch, test runs that pass while writing server errors to a log>_

**Exact trigger demanded:** "when \<dependency> throws at L\<n>, the catch at L\<m> swallows it and the caller sees success with \<wrong/empty data>".

---

## auth/tenant

Authorization holes, intra-tenant IDOR, PII leakage.

**Hunt for:**

- An endpoint or handler registered at a **broader** permission level than it needs — especially anything reachable by a low-privilege or anonymous caller.
- A handler that takes an entity id **from the request** and acts on it without scoping to the authenticated identity — intra-tenant IDOR. Check whether registration is additive and exact-match rather than a hierarchy; one role's registration does not exclude another path reaching the same data.
- A read path that returns more rows than the caller's role should see (list, search, export and report endpoints are the classic offenders).
- PII (names, addresses, coordinates, contact details) in URLs, logs, error messages, or a response field the caller should not have.
- An outbound email, SMS or push recipient resolved from **request input** rather than from a stored record keyed by the authenticated identity.

**Local hotspots:** _<fill in: the authorization registration file, cross-aggregate readers, global search, admin endpoints, anything with zero or one registration line where a sibling has several>_

**Exact trigger demanded:** "a \<low-privilege role> session calls \<endpoint> with `<IdField>` belonging to another \<owner> at L\<n>; nothing checks ownership, so the response contains \<their data>".

---

## async-ui (front end)

State, subscription and render-cycle bugs.

**Hunt for:**

- A subscription with no bound lifetime (no unsubscribe, no teardown on destroy) → memory leak plus stale callbacks after destroy.
- Two calls racing where the **later-started** can resolve first and overwrite (latest-wins not enforced) — search and typeahead are the classic cases.
- Nested subscriptions where a higher-order operator belongs → ordering and cancellation bugs.
- Cache refresh races: a refresh fired after a mutation that resolves after a newer read, so the UI shows stale data; a cache read before its first populate.
- A reactive effect that writes state it also reads, or a computed value with a side effect → loops and render-cycle errors.
- A stale closure capturing an old component field inside a long-lived subscription.
- A component firing a request then navigating away before the response is handled.

**Local hotspots:** _<fill in: the data-service layer, the cache classes, drag-and-drop or scheduler screens, dialogs that save then navigate, realtime updates racing a manual refresh>_

**Exact trigger demanded:** "user types fast: request for 'ab' starts, then 'abc' starts; 'ab' resolves last and overwrites the 'abc' result at L\<n>".

---

## boundary/contract

Caller and callee disagree on nullability, units or shape; off-by-one; unreachable branch.

**Hunt for:**

- A **generated** client out of date with the server's request/response/error types — regeneration is usually a manual step, so drift is routine. A new error value the UI cannot render, or a removed field the UI still reads.
- An optional field on one side treated as guaranteed on the other (or a required field sent as absent).
- A query's column list versus the columns the table actually has (a mapping that compiles and fails at runtime).
- A fake or in-memory implementation whose behaviour diverges from the real one — tests pass, production does not.
- Off-by-one on ranges, pagination and index maths; inclusive versus exclusive slips.
- A condition that can never be true or false (dead branch) — often a real logic slip.
- Units mismatch (pence versus pounds, seconds versus milliseconds).

**Local hotspots:** _<fill in: the generated client directories, the fake/in-memory doubles, hand-written SQL mappings>_

**Exact trigger demanded:** "when the endpoint returns \<field> absent (allowed by the contract), the caller at L\<n> dereferences it → runtime error".

---

## resource-leak

Undisposed connections, sockets, listeners, handles, timers, workers.

**Hunt for:**

- A disposable resource created and never disposed (commands, readers, streams, per-call HTTP clients).
- A connection obtained outside the per-request scope, so it never returns to the pool.
- An event listener or DOM subscription added and never removed.
- A timer, interval, worker or websocket started and never cleared.
- A transaction opened on an early-return path that never commits or rolls back.

**Local hotspots:** _<fill in: raw data-access code, outbound HTTP adapters, front-end listeners and intervals, background sync timers>_

**Exact trigger demanded:** "each call to \<method> opens a \<resource> at L\<n> that is never closed; under load this exhausts \<pool/handles>".
