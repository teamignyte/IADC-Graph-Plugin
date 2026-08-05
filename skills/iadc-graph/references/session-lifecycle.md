# Session lifecycle

The `iadc` graph MCP is **session-based**: it starts with no graph loaded.
Every read tool (`get_node`, `get_neighbors`, `find_nodes`, `list_nodes`,
`callers_of`, `shortest_path`, `get_out_edges`/`get_in_edges`/`get_edge`,
`edges_by_relation`, `graph_overview`, `reachable`) takes a `session_id` as
its first argument and resolves against that session's graph. You always
start by calling `seed(...)`, and you thread the returned `session_id`
through every subsequent call in the conversation/task — one seed, many
reads against the same id.

## The two front doors — and who can use which

`seed` takes **exactly one** of `export_ref` / `application_uuid`. Passing
neither or both returns `{"error": "seed requires exactly one of export_ref,
application_uuid"}` — no partial/best-guess behavior.

### `export_ref` — synchronous, server-local

A path to an **already-extracted Appian export directory on the MCP
server's own filesystem**. Only usable by a caller co-located with the
server. If you're a remote client (a dev agent talking to the hosted MCP
over HTTP), you almost certainly do not have a path on the server's disk to
hand it — use `application_uuid` instead.

**Over HTTP, the path is also restricted (IV-321).** A caller reaching this
tool through the Graph service's HTTP transport (i.e. anyone other than a
local `python -m graph_mcp` stdio process) must pass a path that resolves
under one of two directories on the server: the Graph service's own data
directory, or its read-only export-staging mount — the documented,
operator-populated home for this exact front door (`docs/environments.md`
surface A; `GRAPH_EXPORTS_DIR`, default `/data/graph-exports` inside the
container, bind-mounted from `~/iadc/graph-exports` on the host). An
operator stages an export there (`~/iadc/graph-exports/<name>/`) before you
call this tool with the **container-side** path,
`export_ref="/data/graph-exports/<name>"` — the host-side path is not
something the MCP process can see. Any other path is rejected with an error
naming no roots (a stdio process invoking `python -m graph_mcp
--export-root <path>` directly is exempt from this restriction — it already
has whatever filesystem access it has).

Builds and registers the session **synchronously**: the call blocks until
the resolver→builder pipeline finishes, and the response state is always
`"ready"`. There is no polling step for this path.

```
seed(export_ref="/path/on/server/to/extracted-export") -> {"session_id": "...", "state": "ready"}
```

The build itself runs off the server's event loop in a worker thread (IV-316)
— from YOUR call's point of view nothing changes (it's still one blocking
round trip, same shape as above), but on the Graph service's shared HTTP
transport, another principal's concurrent call (a read against an existing
session, `/health`, etc.) is no longer frozen out for the whole build
duration (IV-316). A SECOND concurrent `export_ref` seed normally queues
behind this one (a dedicated lock caps concurrent heavy builds on this
process) — only the reverse (other calls blocked BY a build) changed. That
cap is a normal-case guarantee, not an absolute one: cancelling a seed
mid-build (e.g. an MCP cancellation or client disconnect on the in-flight
seed call) releases the lock while its worker thread keeps running to
completion (a thread can't be stopped from outside), so a second seed can
briefly build concurrently with it.

### `application_uuid` — asynchronous, remote dev-agent path

An **Appian application UUID**. This is the path a remote dev agent uses —
no filesystem access to the server required. `seed` registers a `"queued"`
placeholder session immediately and returns *before* the work is done; a
background task then runs the whole-application export via the Appian
Deployment API, downloads and extracts it, and builds the graph.

```
seed(application_uuid="<appian-app-uuid>") -> {"session_id": "...", "state": "queued"}
```

A session in any in-progress or failure state is **not queryable yet** —
every read tool rejects it with `{"error": "session not ready",
"session_id": ..., "state": "<current state>"}`. Poll:

```
seed_status(session_id) -> {"state": <SessionState>, "message": str|None}
```

`<SessionState>` is one of ten values, walked through roughly in this order:

- **In-progress** (the worker hasn't finished yet): `"queued"` (placeholder
  registered, worker not yet started) -> `"exporting"` (triggering + polling
  the Deployment API) -> `"downloading"` (fetching the export zip) ->
  `"building"` (extract + build + gap-fill).
- **Terminal success** (both queryable by the read tools): `"ready"` (clean
  completion) or `"ready_with_warnings"` (the export completed with errors
  and build-time gap-fill ran — `message` describes what happened).
- **Terminal failure** (never queryable; no graph ever attaches):
  `"export_failed"` (the Deployment API reported `FAILED`, or a
  credentials/API error), `"export_timed_out"` (polling never reached a
  terminal status within budget), `"build_failed"` (the downloaded zip
  failed to extract/build), or the catch-all `"failed"` (an unexpected
  error).

`seed_status` is the one call that deliberately resolves a session in *any*
state — it's what you poll while waiting, not an error path. Keep polling
until `state` is `"ready"`/`"ready_with_warnings"` (then start reading) or
one of the four failure states (`message` carries the reason — no graph
will ever attach; re-`seed` if you want to retry). There's no push/webhook —
poll on your own cadence.

An `export_ref` session's `seed_status` will just immediately confirm
`"ready"` — harmless to call, never necessary.

## TTL and eviction

Sessions are evicted **lazily** on idle timeout: `DEFAULT_SESSION_TTL_SECONDS = 1800`
(30 minutes) since `last_accessed`. Every read/seed call refreshes
`last_accessed`, so a session under active use never expires; one left idle
for 30+ minutes gets swept the next time *anything* touches the registry
(not necessarily your own next call) — the deployed service additionally
runs a periodic background sweep (IV-298), so a session can also be
reclaimed with no traffic at all. Either way, once evicted, the
`session_id` behaves exactly like one that was never issued — same
`"unknown or expired session"` error as a typo'd id. There is no way to
"extend" or "keep alive" a session other than using it.

Practical implication: don't seed once at the start of a long task and sit
on the session_id for a long time before your first read — if more than 30
idle minutes pass, re-seed.

## Principal binding

A session is bound to the principal that created it (whoever/whatever
called `seed`). Every later call presenting that `session_id` must come
from the same principal, or it's rejected with a *different* error than an
unknown id: `{"error": "session does not belong to this caller",
"session_id": ...}` vs `{"error": "unknown or expired session",
"session_id": ...}`. You cannot hand a `session_id` to another agent/caller
and have them read it — each caller needs its own `seed`. (Under stdio
there's effectively one fixed local principal, so this only bites under the
Graph service's HTTP transport with distinct authenticated callers.)

## Closing a session

```
close(session_id) -> {"closed": true|false}
```

Frees the session's graph/context early — call it when you're done with a
session rather than waiting out the TTL, especially for large graphs.
`closed: false` covers both "never existed / already closed / expired" and
"belongs to a different principal" — it deliberately doesn't distinguish
those (closing never confirms or denies the existence of a session you
don't own).

**`close` on a session still in an in-progress phase (`"queued"`/
`"exporting"`/`"downloading"`/`"building"`) cancels the in-flight
`application_uuid` build.** There's no separate "cancel seed" tool — if you
seeded via `application_uuid` and no longer want the build to finish (wrong
app, changed your mind, taking too long), call `close(session_id)` while
it's still in progress. This tears down the background worker and its temp
export directory; the session_id then behaves as closed.

## Single-worker constraint (context, not something you control)

The session registry is in-memory and process-local on the MCP server —
this only matters if you're the one operating the server (see the
`iadc-ops` skill), not to a caller driving it. Mentioned here only so you
don't misdiagnose a "session not found" as a client-side bug: if the server
were ever run under multiple worker processes, a session seeded on one
worker would be invisible to a request landing on another. The deployed
Graph service runs single-worker specifically to avoid this; it's not
something a graph-MCP caller needs to reason about beyond knowing sessions
aren't resilient to a server restart either way.

## Live refresh: `report_changes` — the write path

Once a session is `"ready"`, its graph is a point-in-time snapshot. If a
dev agent then edits objects in Appian, the session's graph goes stale
unless you refresh it. `report_changes` is that refresh, scoped to the
*same session* — there's no re-seed-from-scratch step:

```
report_changes(session_id, uuids=["<uuid1>", "<uuid2>", ...])
-> {"results": {"<uuid1>": {"status": "patched"|"deleted"|"rejected"|"error", "detail"?: "..."}, ...}}
```

The calling dev agent reports the UUIDs of objects it just changed (it
doesn't need to know if each was modified or deleted — the tool fetches
the current live version and figures that out: found → `"patched"` in
place; gone → `"deleted"`). The graph is patched, not rebuilt — after this
call returns, keep using the **same `session_id`** for reads; they'll see
the freshened nodes/edges immediately.

Per-uuid outcomes:
- `"patched"` / `"deleted"` — applied.
- `"rejected"` — that uuid isn't part of this session's package membership
  (reporting a change to an object the session never knew about is a no-op,
  not an error).
- `"error"` — the live re-fetch or patch itself failed (LCP auth/network
  issue, or an object_type the patcher doesn't know how to apply); `detail`
  carries the exception text.

Known gap worth knowing before you rely on this: **reporting a record
type's own UUID does not re-materialise that record type's fields, views,
actions, or relationships** — the patch only refreshes the record type's
own artifact attributes, not its structural children. `report_changes` is
built for rule/interface/expression-rule-style content edits; a record
type's structure changing under you means the field/view/action/
relationship graph around it is what's stale, and this tool won't fix that
for you. Treat any record-model *structure* edit as a reason to re-seed
rather than report.

A missing-credentials condition short-circuits the whole call rather than
failing per-uuid: if no `ObjectFetcher` is configured and
`LCP_URL`/`LCP_USERNAME`/`LCP_PASSWORD` aren't all set, you get a single
top-level `{"error": "LCP credentials not configured (set LCP_URL,
LCP_USERNAME, LCP_PASSWORD) — cannot fetch live object versions",
"session_id": ...}` instead of a `results` envelope — none of the uuids
were attempted.
