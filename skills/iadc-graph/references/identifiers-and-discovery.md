# Identifiers & discovery

This is the most important reference in this skill. Every read tool takes a
`node_id` (or `source`/`target`) — get this wrong and you get `{"error": "node
not found", "id": ...}`, not a helpful nudge. There is no fuzzy resolution
anywhere in the read path; ids are matched exactly.

## The node-id model

Ids are **UUID-first, but not always UUIDs.** Which form a given node has
depends on its `kind` (see `references/node-kinds.md` for the full kind
list):

| Node shape | Id form | Example shape |
|---|---|---|
| `artifact` (rule, interface, record type, constant, …) | The Appian object UUID, verbatim | `a1b2c3d4-...` |
| Table-backed / UUID-backed record-model nodes (table-backed `recordField`, `recordRelationship`, `recordAction`) | The Appian object UUID, verbatim | `a1b2c3d4-...` |
| `appian_builtin` | `f"appian:{name}"` — synthesized, not an Appian id | `appian:a!queryRecordType` |
| `recordView` / view-backed `recordField` | `f"{rt_uuid}/{stub}"` composite — synthesized, Appian assigns no id here | `a1b2c3d4-.../myUrlStub` |
| `sitePage` | `f"{site_uuid}/{page_uuid}"` composite — synthesized, keyed on the page's own uuid (matches the `site-page`/`portal-page` URN family's identity), NOT the page's urlStub | `a1b2c3d4-.../e5f6g7h8-...` |
| Boundary nodes (`external`/`dangling`/`unknown`) | Priority-ordered: uuid, then name, then raw ref text | Varies — could be a UUID, an `appian:{name}` form, or literal malformed ref text |

Full priority rules for boundary nodes (`ResolvedReference.boundary_node_id()`
in the resolver): `dangling` always has a uuid; `unknown` is `appian:{name}`
if a name was recovered, else the raw ref text; `external` tries uuid, then
name, then raw ref text, in that order. You don't need to compute any of
this yourself — it's context for why boundary-node ids look inconsistent,
not a formula to apply.

**The takeaway:** never assume a `node_id` is a UUID and never pattern-match
on its shape to decide what to do with it. Treat every `id` as an opaque
token you got from a tool response.

## `node_label` is output-only

Every compact record includes a `node_label` — a human-readable string
computed for display (ADR 0019/0028; see `resolver/node_label.py`). It is
**never a valid input.** Do not pass `node_label` back into `node_id`,
`source`, or `target` on any call — it is frequently NOT the node's id (an
`appian_builtin`'s label is its IDE-form name like `a!queryRecordType`, not
the stored `appian:a!queryRecordType` id; a `recordField`'s label is
`"{ownerRTName}.{fieldName}"`, not its UUID; a boundary node's label is
`"⊘ {kind}:{node_id}"` when no name is recoverable — the id appears inside
the label string but the label as a whole is not the id — or `"⊘ {name}
[{kind}]"` when one is (IV-173: e.g. `⊘ User.username [external]`,
`⊘ CC_uiViewRecordDocuments [dangling]`) — neither form is the id).

**The rule that matters in practice: always pass `id` exactly as returned by
another tool call — never one you typed, guessed, or extracted from a label
string.** This mirrors the `appian` skill's own UUID discipline for its tool
calls — never invent, guess, or reuse a UUID from a different environment;
if you don't have one, stop and retrieve it — same
failure mode (silent 404-style `"node not found"`), same fix (retrieve,
don't guess).

## The bootstrapping problem: how do you get a first `node_id`?

You almost never have one at the start of a task — a human says "the Case
record type" or "the `LogSubmission` rule," not a UUID. Three ways to turn
that into a real, verified `node_id`, in the order to reach for them:

### 1. Search inside the already-seeded graph (primary path)

If the object you care about is plausibly part of the seeded package, this
is the first thing to try — no other MCP involved:

- **`find_nodes(session_id, query, kind?, object_type?, limit?)`** —
  case-insensitive substring search. `query` matches if it's a substring of
  the node's `node_label`, its `node_id`, or its `name` attribute (when
  present — most `artifact` nodes have one). This is the general-purpose
  "I have a name or partial name" entry point.
- **`list_nodes(session_id, kind?, object_type?, limit?)`** — enumerate by
  structural filters instead of text. Use when you know the shape you want
  (e.g. `kind="recordType"` — actually `kind="artifact", object_type="recordType"`,
  since only `artifact` nodes carry `object_type`; see
  `references/node-kinds.md`) but not the name, or want to browse everything
  of a kind.

Both return the same discovery envelope: `{"nodes": [{id, kind, node_label,
object_type?}, ...], "returned", "total_matching", "truncated"}`. **Read the
`id` field off the matching record** — that's your verified starting point.
If `truncated: true` and your match isn't in the returned page, narrow the
query/filters rather than assuming it doesn't exist.

If nothing matches, the object may not be part of this session's package —
move to step 2.

### 2. The Appian-MCP name→UUID handoff (object not yet in the seeded graph, only where that server is configured)

**Only if the `appian` MCP is configured in this session** — not every
install has it; a Tester-only install carries no Appian credentials and
never configures this server, so this whole step is unavailable there and
step 1 above (or step 3 below) is as far as such a session can go. Where it
is configured: when you have a human-given name for an Appian design object
that isn't (yet) in this session's graph — or you're not sure it is, and
want to resolve the name authoritatively before searching — resolve it via
the `appian` MCP:

- `listRecordTypes` / `getRecordType` — record types
- `listInterfaces` — interfaces
- `listExpressionRules` — expression rules
- equivalent `list*`/`get*` tools for other object types (constants, process
  models, sites, integrations, …)

Filter the results by `name`, confirm the matched name is actually the
object you meant (same verification step the `appian` skill calls out —
don't grab the first result), and read the `uuid` off the match. That UUID
is very likely also the graph `node_id` for that object (artifact nodes are
keyed by the Appian object UUID verbatim) — but it's only a *candidate*
`node_id` until the graph confirms it. Feed it to `get_node(session_id,
node_id)` or `find_nodes(session_id, query=<uuid>)` to check it's actually a
node in this session's graph before treating it as one (it may not be, if
the object is outside the seeded package — it would then show up, if at
all, as a boundary node under a different id per the priority rules above,
or not be reachable at all).

**Never fabricate a UUID.** If you don't have one from a tool response —
either the graph's own `find_nodes`/`list_nodes`, or — where the `appian`
MCP is configured — its `list*`/`get*` tools — stop and retrieve it.
Guessing a UUID format, reusing one from a different session/environment, or
inventing a placeholder produces a silent `"node not found"` at best and a
wrong-node mixup at worst if you guess a real id in the wrong graph.

### 3. `edges_by_relation` as a no-arg-needed enumeration fallback

**`edges_by_relation(session_id, relation)`** needs only a relation name —
no starting node at all. Useful when you don't have any name or id to search
on, but you know the *kind of connection* you're interested in (e.g. "show
me everything that calls a built-in," `relation="calls_builtin"`, or
"show me every record-type relationship," `relation="declares"`). Each
returned edge record carries a fully enriched `source`/`target`
(`{id, kind, node_label, object_type?}`), so this doubles as a discovery
tool — grab the `id` off whichever end you need and proceed. An
unrecognized/misspelled relation returns `[]`, not an error, so check the
relation string against `references/relation-vocabulary.md` if you get
nothing back and expected results.

## After you have a verified `node_id`

Every subsequent traversal call (`get_neighbors`, `get_node`, `callers_of`,
`shortest_path`, `get_out_edges`/`get_in_edges`, `get_edge`, `reachable`)
takes that same `id` unchanged. Their own compact-record outputs (`{id,
kind, node_label, object_type?}`) are themselves valid inputs for the next
hop — chaining `get_neighbors` → pick an `id` from the result → `get_node`
on it is the normal pattern. You only re-enter the bootstrapping steps above
when you need a node you have no path to yet (a fresh name, or a relation
you haven't explored).
