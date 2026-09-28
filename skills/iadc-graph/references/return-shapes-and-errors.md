# Return shapes & errors

Canonical source: `graph_mcp/tools.py` (the shapes) and `graph_mcp/__main__.py`
(the JSON-string wrapping + session error dicts). `tests/test_graph_mcp_docs_drift_guard.py`
guards this file **token-level only**: every wire key `node_label`,
`occurrence_count`, `total_matching` and every error string
`unknown or expired session`, `node not found`, `session not ready` must
appear backtick-wrapped somewhere below, forward-coupled from the code that
produces them (named error constants; wire keys verified against real
return values — a sibling check in the same suite also guards the 15-tool
roster against `SKILL.md`'s own enumeration). It does **not** enforce full
prose/shape equality — if a shape's structure changes beyond these guarded
tokens, update this file by hand, same as before.

**Sessions are no longer principal-scoped (IV-342, 2026-08-05).** A session
used to be readable only by the principal that seeded it, with a third error
dict (`session does not belong to this caller`) for a mismatch. That check
is retired — `session_id` alone is the capability, any caller may read any
known session — so that error dict no longer exists; only the two below.

**Every one of the 15 tools returns a JSON string**, not a raw object —
`mcp.tool()` functions all end in `json.dumps(...)`. Parse the string before
reading any field. Everything below describes the shape *after* you
`json.loads()` it.

**Errors are dicts, never raised exceptions across the MCP boundary** — with
one exception: `seed(export_ref=...)`'s own validation
(`graph_mcp/session.py::seed_export`) raises a `ValueError` that surfaces as
an MCP-level tool error (`mcp.server.fastmcp.exceptions.ToolError`, message =
the exception text) when the path doesn't resolve to an existing directory,
or (HTTP callers only) doesn't resolve under one of this server's allowed
export roots. See `references/session-lifecycle.md`'s `export_ref` section
for what those roots are.

## The compact enriched record

The atomic unit almost every read tool returns, standalone or embedded in an
edge record (built by `enrich_node`):

```json
{"id": "<node_id>", "kind": "<kind>", "node_label": "<str>", "object_type": "<str>"}
```

- **The label key is `node_label` — not `name`, not `display_name`.** Don't
  guess at either of those; they aren't on the wire. (`display_name` was the
  pre-ADR-0028 key — if you see it in older docs/code comments, treat it as
  historical, not current.)
- `object_type` is present **only** on `kind == "artifact"` nodes — omitted
  entirely on every other kind (never sent as `null`). Check for the key's
  presence, don't assume it's always there.
- `kind` can be `null` (IV-250, defensive fallback — not expected to occur
  in practice) for a node whose attribute dict is unexpectedly empty.
  `node_label` still renders in that case, falling back to the raw node id.
- Lists of these records are sorted by `(node_label, id)` (ties broken by id)
  — `list_nodes`, `find_nodes`, `reachable`. `shortest_path` returns them in
  path order.

## The compact edge record

Returned by `get_edges` (a list) and `edges_by_relation` (inside its envelope, below):

```json
{
  "source": {"id": "...", "kind": "...", "node_label": "...", "object_type": "..."},
  "target": {"id": "...", "kind": "...", "node_label": "...", "object_type": "..."},
  "relation": "<str>",
  "provenance": "reference" | "structural",
  "occurrence_count": 3
}
```

`occurrence_count` is `len(occurrences)` — **the full `occurrences` list is
deliberately omitted here** to keep list payloads bounded. If you need the
actual occurrence data (source locations / call-site detail) for a specific
edge, follow up with `get_edge(session_id, source, target, relation)` using
the exact `source`/`target`/`relation` you just read off this record.

One record per edge: a pair joined by two relations (say a record type's
`has_field` edge and a `references` edge to the same field) appears twice,
told apart by `relation`.

Sort order puts the far end first:
- `get_edges(direction="out")`: `(target.node_label, target.id, relation)`.
- `get_edges(direction="in")`: `(source.node_label, source.id, relation)`.
- `edges_by_relation`: `(source.node_label, source.id, target.node_label,
  target.id)`, before the `limit` cap.

`get_edges` takes an optional `relation` to keep one relation's edges:
`get_edges(node, direction="out", relation="references")` answers "what does
this reference", `get_edges(field, direction="in", relation="has_field")`
"which record type declares this field". A relation outside the vocabulary is
an `unknown relation` error (below), not an empty list.

## The discovery / pagination envelope

Shared by `list_nodes`, `find_nodes`, `reachable` (key `nodes`) and
`edges_by_relation` (key `edges`, holding compact edge records):

```json
{
  "nodes": [<compact enriched record>, ...],
  "returned": 200,
  "total_matching": 743,
  "truncated": true
}
```

- `nodes` is sorted by `(node_label, id)`; `edges` as listed above.
- `total_matching` is the count **before** the `limit` cap; `returned` is the
  count after. `truncated = total_matching > returned`.
- `limit <= 0` means no cap — you get everything, and `truncated` is always
  `false` in that case (`returned == total_matching`).
- An empty result here is `{"nodes": [], "returned": 0, "total_matching": 0,
  "truncated": false}` — not an error. A valid filter that matches nothing is a
  valid, real answer.

## `graph_overview` — graph-wide counts

```json
{
  "node_count_by_kind": {"artifact": 812, "external": 40, ...},
  "node_count_by_object_type": {"processModel": 120, "queryRule": 340, ...},
  "edge_count_by_relation": {"references": 1500, ...},
  "occurrence_count_by_relation": {"references": 2100, ...},
  "occurrence_count_by_provenance": {"reference": 2100, "structural": 900},
  "total_nodes": 900,
  "total_edges": 1900
}
```

- `node_count_by_object_type` is a **further partition of the `artifact` kind
  only** — every other `kind` (external, appian_builtin, dangling, recordField,
  etc.) carries no `object_type` and contributes nothing to this map. Summing
  its values equals `node_count_by_kind["artifact"]` exactly — it does not
  change `total_nodes`, which stays the sum of `node_count_by_kind`.
- `total_nodes`/`total_edges` are computed sums (`sum(node_count_by_kind.values())`
  / `sum(edge_count_by_relation.values())`), not independently tracked counters.

## `record_model` — one-call record type substructure

Read-only composition of a record type's `has_field`/`has_display_name`/
`has_view`/`defines_action`/`declares`/`targets` edges — the nested
substructure in one call instead of an out-edges-then-per-child dance:

```json
{
  "fields": [
    {
      "id": "<field node id>", "kind": "recordField", "node_label": "Enrollment.status",
      "resolved_via": "table_uuid",
      "display_name": {"id": "...", "kind": "...", "node_label": "Enrollment.status \"Status\""}
    },
    {"id": "...", "kind": "recordField", "node_label": "Enrollment.notes", "resolved_via": "table_uuid"}
  ],
  "views": [{"id": "...", "kind": "recordView", "node_label": "Enrollment: Summary"}],
  "actions": [{"id": "...", "kind": "recordAction", "node_label": "Enrollment: Assign Task"}],
  "relationships": [
    {
      "id": "<relationship node id>", "kind": "...", "node_label": "Enrollment →(MANY_TO_ONE) User [createdByUser]",
      "cardinality": "MANY_TO_ONE", "update_behavior": "NONE",
      "target": {"id": "<target RT id>", "kind": "artifact", "node_label": "User", "object_type": "recordType"}
    }
  ]
}
```

- Every embedded record's `id` is a real node id — feed it straight into
  `get_node`/`get_edges`/etc., same as any other tool's output.
- A field's `display_name` key is present **only** when a Display Name node
  is actually materialized for that field (ADR 0031 — reference-only
  materialization, not every field gets one); absent, never `null`, when
  there isn't one.
- `cardinality`/`update_behavior` on a relationship record are read off that
  relationship node's own attrs (ADR 0028) — not derived from the target.
- A record type with none of these (no fields/views/actions/relationships)
  returns empty lists for each — a real, valid answer, not an error.
- Errors: the standard not-found dict when `record_type_id` is absent, PLUS
  one unique to this tool — `{"error": "not a recordType", "id": "..."}` —
  when the node exists but isn't an artifact with `object_type ==
  "recordType"` (e.g. you passed a field/view/relationship id, or an
  unrelated artifact, by mistake).

## `get_sail` — a node's SAIL, field-keyed

SAIL is already retained in the session (`SessionEntry.context.artifacts`)
but no other tool exposes the expression body — every other tool describes
*relationships between* objects, not the SAIL text itself. `get_sail` is the
read-only lookup for that text:

```json
{
  "node_id": "<node_id>",
  "node_label": "<str>",
  "sail": [{"field": "expr", "text": "a!x()"}, {"field": "expr", "text": "a!y()"}]
}
```

- For an **artifact** node: `sail` is that artifact's own `sail_strings`, in
  original XML-document order — NOT sorted, and duplicate `field` values are
  kept as separate entries (e.g. a processModel artifact with several node
  `expr` slots returns one entry per slot).
- For a **recordView** node (the composite `{rt_uuid}/{urlStub}` id, ADR 0028
  slice A3): the view itself carries no SAIL — `sail` is the OWNING record
  type artifact's entries whose `field` matches that exact
  `detailViewCfg:{urlStub}` tag, same order/duplicates-kept semantics.
- For every other kind (`appian_builtin`, the three boundary kinds
  `external`/`dangling`/`unknown`, the four non-view record-model kinds
  `recordField`/`recordAction`/`recordRelationship`/`recordFieldDisplayName`,
  and `sitePage`) — kinds that structurally never carry a SAIL body —
  plus an artifact or recordView owner missing from the session's
  extracted artifacts (e.g. a synthesized node with no corresponding
  Reader-extracted `Artifact`), or a node with no `kind` attribute at all
  (IV-250, defensive fallback — not expected to occur in practice):

```json
{"node_id": "<node_id>", "node_label": "<str>", "sail": [], "reason": "..."}
```

**`sail: []` alone is not an error signal** — a real artifact with genuinely
no SAIL (e.g. a `constant`) also returns `sail: []`, but WITHOUT a `reason`
key. Check for the `reason` key's presence to distinguish "this kind/node
structurally has no SAIL to show" from "this artifact really has none."

Errors: the standard not-found dict when `node_id` is absent from the graph
entirely (see "Node-not-found" below) — there is no distinct wrong-kind
error the way `record_model` has one; every kind gets a real (possibly
empty-with-reason) answer.

**Freshness:** `get_sail` reads `SessionEntry.sail_map`, which a successful
`report_changes` patch/delete rehydrates in place (IV-246) — a `get_sail`
call after reporting a change on that same uuid sees the freshened SAIL (or,
for a delete, the node-not-found error), not a stale pre-patch read.

## `get_node` — the full record

`get_node` does not use the compact shape. It returns the **complete stored
attribute dict** for the node (whatever kind-specific attrs it has — these
vary by `kind`, see `references/node-kinds.md`) **plus three computed keys
added on top**:

```json
{
  "...every stored attribute...": "...",
  "node_label": "<str>",
  "in_degree": 4,
  "out_degree": 12
}
```

`node_label`, `in_degree`, `out_degree` are computed at call time, not stored
node attributes — don't expect them in, say, a `get_edge`'s embedded node
data (there is none; edges embed nothing but their own attrs).

## `get_edge` — the full record

The drill-down tool, and the only one that gives you the full `occurrences`
list. With a `relation`, it returns that edge's **complete attribute dict**:

```json
{
  "relation": "references",
  "provenance": "reference",
  "occurrences": [ {"...": "..."}, ... ],
  "...other stored edge attrs...": "..."
}
```

Without a `relation`, it returns every edge from `source` to `target`, each
the same full dict, sorted by `relation`:

```json
{"edges": [{"relation": "has_field", ...}, {"relation": "references", ...}]}
```

Edges are directional: `get_edge(A, B)` does not return a `B → A` edge.
No `source`/`target` are echoed back and no enriched node records are
embedded — if you need the endpoints' `node_label`/`kind`, call `get_node` on
each id, or read them off the compact edge record you drilled in from.

## Session-resolution errors (uniform across every read tool)

Every read tool (`get_node`, `shortest_path`, `get_edges`, `get_edge`,
`edges_by_relation`, `list_nodes`, `find_nodes`, `graph_overview`,
`reachable`, `report_changes`, `record_model`, `get_sail`) funnels through the same session-resolution check first and returns one of
these two dicts verbatim on failure — check for `"error"` in the parsed
JSON before assuming you got a real result shape:

```json
{"error": "unknown or expired session", "session_id": "<id>"}
```
Unknown, already-closed, or TTL-expired `session_id`. Indistinguishable from
a typo'd id — there's no way to tell "never existed" from "existed once."
Any known session resolves regardless of who is asking; see
`references/session-lifecycle.md`.

```json
{"error": "session not ready", "session_id": "<id>", "state": "<current SessionState>"}
```
Session is known, but its `state` isn't one of the two queryable terminal
states (`"ready"`/`"ready_with_warnings"`) — still in an in-progress phase
(`"queued"`/`"exporting"`/`"downloading"`/`"building"`) or ended in a
failure state (`"export_failed"`/`"export_timed_out"`/`"build_failed"`/
`"failed"`). Poll `seed_status` instead of retrying the read tool. **Not
returned by `seed_status` itself** — `seed_status` is the one call designed
to resolve a session in any state, precisely so you have something
non-rejecting to poll.

`seed_status` and `close` only ever return the first of these two (they
never check readiness) — see their own sections below.

## `close` — collapsed boolean, not the two-way error above

```json
{"closed": true}
```
Session existed and was removed — regardless of who seeded it — also cancels an in-flight `application_uuid` build if the session was
still in an in-progress phase.

```json
{"closed": false}
```
Unknown, already-closed, or expired `session_id`.

## `seed_status` errors — only one, no readiness dict

```json
{"error": "unknown or expired session", "session_id": "<id>"}
```
Same shape as above. There is no "not ready" error here — any non-terminal
or failure `state` is a normal (non-error) response body for this tool
specifically: `{"state": <SessionState>, "message": str|None}`,
where `<SessionState>` is one of `"queued"`/`"exporting"`/`"downloading"`/
`"building"` (in-progress), `"ready"`/`"ready_with_warnings"` (terminal
success), or `"export_failed"`/`"export_timed_out"`/`"build_failed"`/
`"failed"` (terminal failure).

## Node-not-found

```json
{"error": "node not found", "id": "<node_id>"}
```
Used by `get_node`, `get_edges`, `reachable`, `record_model`, `get_sail` for an
absent `node_id` — the
`node not found` error. For `shortest_path`, the same shape is used for
whichever of `source`/`target` is missing — **`source` is checked first**,
so if both are absent you'll see
`source` named, not `target`. `record_model` additionally has its own
distinct wrong-kind error — see its own section above, not this one.

## Edge-not-found

```json
{"error": "edge not found", "source": "...", "target": "...", "relation": "..."}
```
`get_edge` only: no edge from `source` to `target` with that relation, or —
with `relation` omitted, and then without the `"relation"` key — no edge
from `source` to `target` at all. The nodes may both exist. A misspelled
relation (`"reference"` for `"references"`) is an `unknown relation` error
instead (below).

## No-path — distinct from not-found

```json
{"path": null}
```
`shortest_path` only, when both `source` and `target` exist but no directed
route connects them. Don't confuse this with the node-not-found dict above —
`{"path": null}` means the graph was searched and came up empty; the
not-found dict means the search never started because an endpoint is
missing. `source == target` (both present) is the trivial case and returns a
**single-element list**, not `{"path": null}`.

## Empty result vs. error — tool-by-tool

A `[]` (or an empty `nodes`/`edges` array in the pagination envelope) is a
real, successful answer, not a failure — don't retry or treat it as broken:

| Tool | `[]` / empty means | Error dict instead when |
|---|---|---|
| `get_edges` | node exists, no edges that direction, or none with the given `relation` | unknown `direction`, unknown `relation`, node absent |
| `edges_by_relation` | a valid relation with no edges in this graph | unknown `relation` |
| `list_nodes` / `find_nodes` | filter matched nothing | unknown `kind` / `object_type` (`find_nodes` also errors on empty `query`) |
| `reachable` | node exists, nothing reachable that direction | unknown `direction`, node absent |

An empty result is never a typo: a misspelled filter value is an error that
names the valid values (next section).

## Unknown-value errors

Every parameter with a fixed vocabulary is checked before the query runs.
A value outside it returns the parameter's name, the value you sent, and the
valid values:

```json
{"error": "unknown relation", "relation": "reference", "valid": ["contains_page", "declares", "..."]}
```

| Parameter | Tools | `valid` holds |
|---|---|---|
| `direction` | `get_edges`, `reachable` | `["in", "out"]` |
| `relation` | `get_edges`, `get_edge`, `edges_by_relation` | the 10 relations (`references/relation-vocabulary.md`) |
| `kind` | `list_nodes`, `find_nodes` | the 11 node kinds (`references/node-kinds.md`) |
| `object_type` | `list_nodes`, `find_nodes` | the object types present in **this session's** graph — the keys of `graph_overview`'s `node_count_by_object_type` |

`get_edges` checks `direction`, then `relation`, then the node. `find_nodes`
checks `query` before the filters.

## Bad-input errors

```json
{"error": "query must be a non-empty string"}
```
`find_nodes` only, when `query` is empty or whitespace-only. No `session_id`
in this one (input is rejected before session resolution would even matter).

```json
{"error": "seed requires exactly one of export_ref, application_uuid"}
```
`seed` only, when neither or both of `export_ref`/`application_uuid` are
given.

## `report_changes` — its own envelope, plus a config error

Success (or partial success) shape wraps per-uuid outcomes, not a bare error
or a bare list:

```json
{"results": {"<uuid>": {"status": "patched"|"deleted"|"rejected"|"error", "detail": "..."}, ...}}
```

- `"patched"` / `"deleted"` — no `detail` key.
- `"rejected"` — uuid isn't in this session's package membership; `detail`
  explains that.
- `"error"` — the live re-fetch or patch itself raised (LCP auth/network
  failure, an object_type the patcher can't handle); `detail` is `str(exc)`.

If the session itself doesn't resolve, you get one of the standard session
dicts — `unknown or expired session` / `session not ready` (see
"Session-resolution errors" above) — at the top level instead of a
`results` envelope, same as every other read tool: `report_changes` funnels
through the same session-resolution check, so both apply.

One more top-level (non-`results`) error unique to this tool, when no
`ObjectFetcher` was injected and the LCP env vars aren't all set:

```json
{"error": "LCP credentials not configured (set LCP_URL, LCP_USERNAME, LCP_PASSWORD) — cannot fetch live object versions", "session_id": "<id>"}
```

This short-circuits the *entire* call — none of the requested uuids were
attempted, so don't look for a partial `results` dict alongside it.
