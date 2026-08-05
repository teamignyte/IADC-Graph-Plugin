# Node kinds & object_types

Canonical source: `resolver/node_kinds.py` (the `NODE_KIND_SCHEMAS` registry)
and `graph/builder.py` (what actually assigns `kind`/`object_type` at build
time). A drift-guard test enforces this file matches the code — if you change
a kind's meaning, update both.

Every node has exactly one `kind`. Only `kind == "artifact"` nodes also carry
`object_type`. These are two separate axes: `kind` is the node's *shape*
(what fields it carries, how its label is composed); `object_type` is *which
kind of Appian design object* an artifact node represents.

## `kind` — the 10 values

| `kind` | What it is |
|---|---|
| `artifact` | The generic top-level Appian object node — any exported design object (rule, interface, record type, constant, etc.). Carries `object_type` (below). Also synthesized (not just Reader-emitted) for `translationString` targets not already present, via `_ensure_artifact_node`. |
| `appian_builtin` | An Appian built-in function (`a!queryRecordType`, etc.), id `f"appian:{name}"`. Carries `name`, `deprecated`. Never carries `object_type`. |
| `external` | A reference that resolved outside the package but to a real/plausible object (e.g. a system record type, a plugin function). Carries optional `triage_category`, `name`. |
| `dangling` | A reference to an in-package UUID that *should* exist but doesn't — an export gap, not a real external. |
| `unknown` | A reference the resolver couldn't classify at all (malformed ref, unrecognized shape). |
| `recordField` | A record type field (table-backed: bare UUID; view-backed synthetic: `{rt_uuid}/{fieldName}`). Schema-registered — see below. |
| `recordView` | A record type detail view, id `f"{rt_uuid}/{urlStub}"` (synthetic — Appian assigns no view UUID). Schema-registered. |
| `recordAction` | A record type action, bare UUID (`refId-<uuid>`). Schema-registered. Same node is targeted by both `defines_action` (structural, declaring RT → action) and `invokes_record_action` (reference, caller → action) — never duplicated. |
| `recordRelationship` | A record type relationship, bare UUID. Schema-registered. |
| `recordFieldDisplayName` | A record field's configured Appian Display Name (`<displayName>`), id `f"{fieldNodeId}/displayName"` (synthetic — composes over the owning field's own id, which handles both the bare-UUID table-backed and `{rt_uuid}/{fieldName}` view-backed forms). Schema-registered. **Reference-only** — unlike the other three record-model kinds below, this one is NOT full-schema materialized; it exists only when a `urn:appian:record-field-properties` SAIL reference to it actually resolves, never for every declared field's Display Name. |

`external`/`dangling`/`unknown` are the three **boundary** kinds — anything
the resolver couldn't materialize as a full in-package node. Which one a
given unresolved reference gets is a resolver classification call, not
something this file's node-kind axis encodes further; treat all three as
"not a real node in this package, handle with care."

The 5 record-model kinds (`recordView`, `recordField`, `recordAction`,
`recordRelationship`, `recordFieldDisplayName`) are the ones registered in
`NODE_KIND_SCHEMAS` — each has a defined attribute set, a label composer, a
`patch_authoritative` flag, and (except `recordFieldDisplayName`, which is
reference-only — see above) a structural fan-out contribution. This is the
single place their shape is defined; if a tool result's fields for one of
these kinds look surprising, check its schema entry in
`resolver/node_kinds.py` before assuming a bug.

## `object_type` — present ONLY on `kind == "artifact"` nodes

Not a fixed closed enum — it's whatever type discriminator the Reader
extracted at symbol-table build time (an XML tag localname or export folder
name). Observed/mapped vocabulary:

| `object_type` | Source |
|---|---|
| `rule` | Expression rule (`content/` folder). |
| `interface` | Interface (`content/` folder). |
| `decision` | Decision (`content/` folder). |
| `constant` | Constant (`content/` folder). |
| `outboundIntegration` | Integration (`content/` folder). |
| `recordType` | Record type (attribute-uuid folder). |
| `processModel` | Process model (identity parsed separately via `read_process_model_identity`). |
| `site` | Site (attribute-uuid folder). |
| `portal` | Portal (attribute-uuid folder). |
| `translationString` | Translation string (attribute-uuid folder, attribute-based — no name element; often synthesized rather than Reader-emitted, see `kind=artifact` above). |

Other object_types exist in the wild (`connectedSystem`, `dataStore`,
`group`, `aiSkill`, `datatype`, `groupType`, `translationSet`,
`processModelFolder`, and anything else the Reader encounters under
`content/`) — this list is not exhaustive, and `object_type` is a string, not
a validated enum. Don't assume a fixed vocabulary when filtering.

`recordRelationship` and `recordAction` also appear as *reference-resolution*
`object_type` values (`_OBJECT_UUID_TYPE_MAP` in `graph/relations.py`) when
classifying what a `resolved_via="object_uuid"` reference points at — but
that's classifying the *reference*, not labeling a node; the node itself
ends up `kind="recordRelationship"`/`kind="recordAction"`, not
`kind="artifact", object_type="recordRelationship"`.

## Why this matters for tool calls

`list_nodes`/`find_nodes`/`reachable` accept both `kind` and `object_type`
filters. Since only `artifact` nodes carry `object_type`, filtering by
`object_type` silently excludes every `appian_builtin`, boundary, and
record-model node too — combine with `kind="artifact"` if that's not what
you want, or omit `object_type` and post-filter.
