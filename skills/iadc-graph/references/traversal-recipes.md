# Traversal recipes

Worked call sequences for the review questions this graph gets asked most.
Every recipe assumes a `session_id` from a prior `seed(...)` already in a
queryable state (`"ready"` or `"ready_with_warnings"` — see the skill's
session-lifecycle notes) and a starting `node_id` already in hand — get one
from `find_nodes`/`list_nodes` first if you don't have it; **never** pass a
display name or Appian object name where a `node_id` is expected.

Every read tool returns a JSON string; unwrap it before reading fields.
Session/not-found error shapes are omitted below to keep each recipe focused
on the happy path — see `references/return-shapes-and-errors.md`
for the uniform error dicts every one of these can also return.

## 1. Impact analysis / blast radius — "what breaks if I change X"

**Goal:** every node that transitively depends on X, i.e. everything that
would need re-checking if X's behavior or shape changes.

**Call:**
```
reachable(session_id, node_id=X, direction="in")
```
`direction="in"` walks predecessors transitively — nodes that (directly or
indirectly) reference X. This is the full closure by default (`depth=None`);
pass `depth=1` to cap it to direct dependents only, or raise/drop `limit`
(default 200, `<=0` = uncapped) if the blast radius is large.

**Read off the result:** the `nodes` list is the blast radius, sorted by
`(node_label, id)`. Check `truncated` — if `true`, `total_matching` is the
real count and you're only seeing `returned` of them; re-run with a higher
`limit` before concluding the impact is small.

**One-hop-only variant:** if you just need direct dependents (not the
transitive closure), use `get_edges(session_id, node_id=X, direction="in")` —
the one-hop in-edge set across *every* relation (including `references`,
`secured_by`, `has_field`, ...), as compact edge records (`relation`,
`provenance`, `occurrence_count`). Leave `relation` unset: a dependent can
reach X through a structural relation as well as `references`.

## 2. Dependency analysis — "what does X depend on"

**Goal:** everything X needs to keep working (the inverse of §1).

**Call:**
```
reachable(session_id, node_id=X, direction="out")
```
`direction="out"` walks successors transitively — the full transitive
dependency closure of X. Same `depth`/`limit` knobs as §1.

**One-hop variant:** `get_edges(session_id, node_id=X, direction="out")` for
X's direct out-edges with relation/provenance attached (e.g. to tell a
`references` dependency from a structural `has_field`/`secured_by` link; what
X references is the target node's `kind`/`object_type`). The far ends are the
`target` records; a target joined by two relations appears once per relation.

## 3. Record view -> interface — "what interface renders this record view"

**Goal:** follow a record view to the interface (or boundary node) it
renders via.

**Call:**
```
get_edges(session_id, node_id=<recordView node id>, direction="out", relation="references")
```
A record view's only reference edge is its `uiExpr` reference to the rendering
interface. The edge's `source` is the `recordView` node itself (not the
owning record type — the reference is re-sourced from the view, ADR 0028),
and `target` is the interface (or an
`external`/`dangling`/`unknown` boundary node if it doesn't resolve
in-package).

**To find the record view node id first:** `get_edges(session_id,
node_id=<record type id>, direction="out", relation="has_view")` — each
target is a `recordView` node id. Or `find_nodes(session_id, query=<urlStub
or owner name>, kind="recordView")`.

**Full occurrence detail (SAIL field tag):** if you need the exact
`sail_field` this reference came from, use `get_edge` (§4) on the
view's `references` triple — the reader tags it
`sail_field == "detailViewCfg:{urlStub}"`.

## 4. Path tracing — "how does X reach Y" / "is there a route from X to Y"

**Goal:** the shortest directed route connecting two nodes, or confirmation
none exists.

**Call:**
```
shortest_path(session_id, source=X, target=Y)
```

**Read off the result:** an ordered list of compact node records from X to Y
inclusive (so length-1 means `X == Y`). `{"path": null}` means both nodes
exist but no directed route connects them — distinct from a not-found error,
which means one of the two ids doesn't exist in the graph at all (source is
checked before target, so a not-found error always names the earlier-missing
one first). Direction matters: `shortest_path` only follows edges
source->target, so "is there a route from X to Y" and "...from Y to X" are
different questions — try both directions before concluding no relationship
exists.

## 5. Reference drill-down — exact SAIL source location(s)

**Goal:** given an edge you already know about (e.g. from `get_edges` or
`edges_by_relation`), find every exact place in the SAIL source that produced
it.

**Call:**
```
get_edge(session_id, source, target, relation)
```
Use the exact `source`/`target`/`relation` triple from the edge record you
already have — `get_edge` is the only tool that returns the full
`occurrences` list (the compact edge records from `get_edges`/
`edges_by_relation` only give you `occurrence_count`, the length of that
list, not its contents). Omit `relation` to get every edge between the pair,
each with its occurrences.

**Read off the result:** `occurrences` is a list of
`{sail_field, sail_line, sail_col, raw_ref, ref_kind}` dicts (plus sub-object
detail such as `field`/`hop_depth`/`route` on a resolved leaf — see
`relation-vocabulary.md` §3) — one per distinct source
location that produced this same (source, target, relation) edge (multiple
references to the same target from the same host artifact aggregate onto
ONE edge with multiple occurrences, not multiple edges). `raw_ref` is the
literal reference text as written in the SAIL; `sail_field`/`sail_line`/
`sail_col` pinpoint where in the source object it appears. A record view's
`references` edge's occurrence(s) carry `sail_field == "detailViewCfg:{urlStub}"` rather
than a real SAIL expression field, since the reference is synthesized from
the record view's detail-view config, not authored SAIL.

## 6. Orientation — "what is even in this graph"

**Goal:** a first-look summary before you start drilling into specific
nodes — sizes, shape, how much of the graph is boundary (out-of-package)
material.

**Call:**
```
graph_overview(session_id)
```

**Read off the result:** `node_count_by_kind`/`edge_count_by_relation` give
the shape (e.g. how many `recordField`/`recordAction` nodes vs. plain
`artifact` nodes; how much traffic is `references` vs. each structural
relation).
`occurrence_count_by_provenance` (keyed `"reference"`/`"structural"`) tells
you how much of the edge volume is real SAIL references vs. structural
record-model scaffolding. To gauge how much of the graph is boundary noise
(dangling/external/unknown), sum `node_count_by_kind` entries for
`"external"`, `"dangling"`, `"unknown"` against `total_nodes` — there's no
single boundary-count field, so compute it from the kind breakdown.

## 7. Discovery — finding a starting node_id

**Goal:** every other recipe above needs a `node_id` in hand first. Get one
from a name, or enumerate a category, before traversing.

**By name/label (fuzzy):**
```
find_nodes(session_id, query=<substring>, kind=None, object_type=None, limit=200)
```
`query` is a required case-insensitive substring match against `node_label`,
`node_id`, or the node's `name` attribute (when present) — not a fuzzy or
tokenized search. Narrow with `kind`/`object_type` if you already know the
shape you're after (e.g. `kind="recordField"` to skip artifact matches
entirely). `{"error": "query must be a non-empty string"}` if `query` is
blank.

**By category (exact enumeration):**
```
list_nodes(session_id, kind=None, object_type=None, limit=200)
```
No `query` — use this to enumerate, e.g., every `object_type="recordType"`
artifact or every `kind="sitePage"` node. Remember `object_type` is carried
ONLY by `kind="artifact"` nodes, so filtering by `object_type` silently
excludes every `recordView`/`recordField`/`recordAction`/`recordRelationship`/
`appian_builtin`/boundary node too.

A `kind` outside the 11 node kinds, or an `object_type` this graph has no
node of, returns an error whose `valid` list names what you can pass.

Both share the same paginated envelope
(`{"nodes": [...], "returned", "total_matching", "truncated"}`) — check
`truncated` before assuming you've seen everything; raise `limit` (`<=0` =
uncapped) or add a `kind`/`object_type` filter to narrow instead.

**Relation-first discovery:** to find every edge of a given kind graph-wide
(not anchored to one node), use `edges_by_relation(session_id, relation)`
instead — e.g. `edges_by_relation(session_id, "uses_connected_system")` to
audit every connected-system dependency in the graph at once. It returns the
same envelope, keyed `edges`; check `truncated` or pass `limit=0`. A
misspelled relation is an `unknown relation` error naming the 10 valid ones.
`references` is not a useful graph-wide filter: in one measured 80,910-edge
graph it was 85% of the edges, and 25 MB at `limit=0`. For a reference
question, find the node with `find_nodes`/`list_nodes` and read its
`get_edges`.

## 8. Cheap centrality — "how connected is this node"

**Goal:** a fast fan-in/fan-out signal without running a full `reachable`
traversal — e.g. to eyeball whether a node is a likely hub before deciding
whether a blast-radius query is worth the token cost.

**Call:**
```
get_node(session_id, node_id)
```

**Read off the result:** `in_degree`/`out_degree` are computed and added
on top of the node's full stored attribute dict (along with `node_label`) —
they're not stored attributes, so they won't appear in `find_nodes`/
`list_nodes`/`reachable`'s compact records, only here. High `in_degree`
relative to the rest of the graph is a cheap proxy for "lots of things
depend on this" — worth a full `reachable(direction="in")` (§1) before
touching it.

## 9. Live-refresh loop — keeping a session current after edits

**Goal:** an agent changed some objects in Appian mid-session and wants
subsequent queries against the SAME `session_id` to reflect the new state,
without reseeding the whole graph.

**Call:**
```
report_changes(session_id, uuids=[<changed object uuids>])
```
Report every changed object's Appian uuid — modified or deleted, this tool
can't tell which in advance and figures it out from the fetch result.

**Read off the result:** `{"results": {uuid: {"status": ...}}}`, one entry
per requested uuid — `"patched"`/`"deleted"` mean the graph was updated
in-place; `"rejected"` means the uuid isn't in this session's package at all
(nothing to patch); `"error"` means the live re-fetch itself failed (check
`detail`). **Known gap:** patching a uuid that is itself a record type does
not re-materialize that record type's own fields/views/actions/
relationships — this path is for rules/interfaces/expression rule edits, not
record-model structure changes.

**Then re-query:** immediately re-run whatever read tool you used before
(`get_node`, `get_edges`, `reachable`, ...) against the same
`session_id` — the patch is applied in place, no new session needed. A
`"rejected"`/`"error"` entry means that particular uuid's data in the
session is unchanged (stale), so don't assume a refresh happened for it.

## 10. Record type substructure — "show me everything this record type declares"

**Goal:** a record type's full shape — its fields (and their Display Names),
views, actions, and relationships (with cardinality and target record type)
— in one call, instead of `get_edges` on the record type filtered to four
relations, then a follow-up call per field/relationship.

**Call:**
```
record_model(session_id, record_type_id=<recordType artifact node id>)
```
`record_type_id` must be an in-package artifact with `object_type ==
"recordType"` — find one via `find_nodes(session_id, query=<name>,
kind="artifact", object_type="recordType")` or
`list_nodes(session_id, kind="artifact", object_type="recordType")` first.

**Read off the result:** `{"fields": [...], "views": [...], "actions":
[...], "relationships": [...]}` — see `references/return-shapes-and-errors.md`
for the full shape. Every embedded `id` feeds directly into any other tool
(e.g. `get_edges` on a relationship's `id` if you need more than
cardinality/target). A field only carries a `display_name` key when a
Display Name node is actually materialized for it (ADR 0031) — most fields
won't have one. A record type declaring none of fields/views/actions/
relationships returns empty lists, not an error; passing a node id that
exists but isn't a record type (e.g. a field or relationship id by mistake)
gets its own distinct `{"error": "not a recordType", ...}`, not the
generic not-found dict.

**When to use `get_edges` instead:** `record_model` gives you the
CURATED four-relation shape (fields/views/actions/relationships) with the
one-hop-further Display-Name/target follow-through already done. If you need
a relation this tool doesn't compose (e.g. `secured_by`, or a view's
`uiExpr` reference target — recipe §3), or the full edge metadata
(`provenance`/`occurrence_count`) rather than the compact substructure, drop
back to `get_edges(session_id, record_type_id, direction="out")` directly.
