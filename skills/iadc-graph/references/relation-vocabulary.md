# Relation vocabulary

**Canonical source: `graph/relations.py`.** This file is a thin summary for
quick lookup — when it and the code disagree, the code wins. A drift-guard
test enforces this coupling, so do not let this list get out of sync.

A `relation` parameter (`get_edges`, `get_edge`, `edges_by_relation`) is
matched exactly against the strings below — no fuzzy or prefix matching. A
value outside them returns `{"error": "unknown relation", "relation": ...,
"valid": [...]}` naming all 10; an empty result means the relation is valid
and nothing in this graph has it.

There are **10 relations**: one reference relation and nine structural ones
(ADR 0050). Every edge also carries `provenance`: `"reference"` for
`references`, `"structural"` for the nine in §2 (the two-ledger conservation
invariant, ADR 0016).

**What was referenced is the target node, not the relation.** A `references`
edge to a `rule` node is a rule call; to a `constant` node, a constant use; to
an `appian_builtin` node, a built-in function call; to a `recordField` node, a
field read. Read the target's `kind` and `object_type` (from `get_node`, or the
enriched endpoint records every edge tool returns). At a boundary node
(`external`/`dangling`/`unknown`, no `object_type`), the occurrence's
`ref_kind` (§3) says what the reference looked like.

## 1. Reference relation (1) — `provenance == "reference"`

| Constant | String value | When it applies |
|---|---|---|
| `REFERENCES` | `references` | The source object mentions the target — in SAIL, in a static typed reference (a process-model node input, a record action's launch target, a site/portal page's `<uiObject>`), resolved or not. Resolved targets are artifact nodes, `appian_builtin` nodes, or record-model nodes (`recordField`, `recordAction`, `recordRelationship`, `recordFieldDisplayName`); unresolved ones are boundary nodes. Two references from the same source to the same target share **one** edge whose `occurrences` list holds both. |

The source is the object whose definition holds the mention, with these
re-routings (ADR 0028/0031/0033/0034, kept by ADR 0050):

- A record view's `uiExpr` interface reference is sourced from the
  `recordView` node (`{rt_uuid}/{urlStub}`), not the record type.
- A record action's `<a:target xsi:type="a:ProcessModel">` is sourced from the
  `recordAction` node.
- A site/portal page's `<uiObject>` is sourced from the declared `sitePage`
  node (`{site_uuid}/{page_uuid}`), falling back to the site/portal artifact
  when no page is declared for it.
- A record field's Display Name reference (`urn:appian:record-field-properties`)
  targets the `recordFieldDisplayName` node (`{fieldNodeId}/displayName`), with
  a structural `has_display_name` edge from the field node.
- A record-field or Display Name reference that walks N relationship hops also
  gets one host-sourced `references` edge to each traversed
  `recordRelationship` node, in addition to the leaf edge; a 0-hop reference
  (the common case) gets none.
- A record-relationship reference targets the relationship's owning record
  type (`resolved_rt_uuid`), not the relationship node.

## 2. Structural relations (9) — `provenance == "structural"`

| Constant | String value | When it applies |
|---|---|---|
| `USES_CONNECTED_SYSTEM` | `uses_connected_system` | `artifact.connected_system_uuid` is set (integrations / CS-backed record types). |
| `SECURED_BY` | `secured_by` | One occurrence per `{group_uuid, role}` group-kind entry in `artifact.security`; multiple roles for the same group aggregate onto one edge. |
| `DECLARES` | `declares` | Owning record type to its `recordRelationship` node, one per in-package relationship config. |
| `TARGETS` | `targets` | `recordRelationship` node to its target record type (in-package artifact node, or external boundary node for `SYSTEM_*`/out-of-package targets). |
| `HAS_FIELD` | `has_field` | Owning record type to a declared field node, for every field regardless of whether any SAIL references it. |
| `HAS_VIEW` | `has_view` | Owning record type to a declared view node (`<a:detailViewCfg>` with a non-empty `urlStub`). |
| `DEFINES_ACTION` | `defines_action` | Owning record type to a declared action node; the same node a resolved record-action reference targets. |
| `HAS_DISPLAY_NAME` | `has_display_name` | Owning `recordField` node to its `recordFieldDisplayName` node; emitted only when the Display Name node exists (alongside the first reference to it) — unlike the other structural relations above, NOT declared-field-driven. |
| `CONTAINS_PAGE` | `contains_page` | Owning site/portal to a declared `sitePage` node (IV-444), for every `<page>`/`<navigationNode>` container carrying an `@a:uuid`, regardless of whether it renders a watched `<uiObject>` or any `<uiObject>` at all — NOT record-type-sourced, unlike every structural relation above it. |

A `references` edge and a structural edge between the same pair stay two
edges (e.g. `recordType → recordField` via both `has_field` and a field
reference), told apart by `relation` and `provenance`.

## 3. Reference occurrences

`get_edge` returns an edge's full `occurrences` list. Every reference
occurrence carries its location — `sail_field`, `sail_line`, `sail_col`,
`raw_ref` — and `ref_kind`, the resolver's lexical intent for the reference:
one of `function`, `record_field`, `record_relationship`, `record_action`,
`record_type`, `user_filter`, `site_page`, `portal_page`, `translation`,
`constant`, `rule`, `datatype`, `object_uuid`, `other`.

A **resolved leaf** occurrence also carries its sub-object detail:

| Reference | Occurrence detail |
|---|---|
| Record field (`record_field`, not a Display Name) | `field` (field name), `hop_depth`, `route` (the raw reference when `hop_depth > 0`, else `null`) |
| Record relationship (`record_relationship`) | `relationship` (relationship name), `hop_depth`, `route` |
| User filter (`user_filter`) | `user_filter` (the filter UUID) |
| Site/portal page (`site_page`, `portal_page`) | `page` (the page UUID) |

Hop fan-out occurrences, Display Name occurrences and boundary occurrences
carry location + `ref_kind` only. A hop fan-out occurrence's `ref_kind` is its
leaf reference's, `record_field`, although its edge targets a
`recordRelationship` node. Structural occurrences carry no location:
`secured_by` has `{"role": ...}` per role, `uses_connected_system` has
`{"link": "connected_system"}`, and the rest are `{}`.

## 4. Lookup entry point in the source

- `relation_for(resolved_via, object_type)` — maps a RESOLVED reference to
  `references`; `None` if unmapped (an `object_uuid` reference to an object
  type outside `_REFERENCEABLE_OBJECT_TYPES` — a conservation hole the builder
  raises on, never silently drops).
