# Relation vocabulary

**Canonical source: `graph/relations.py`.** This file is a thin summary for
quick lookup — when it and the code disagree, the code wins. A drift-guard
test enforces this coupling, so do not let this list get out of sync.

A `relation` parameter (`edges_by_relation`, and the `relation` field on every
edge record) is an **exact-match free string** — there is no server-side enum
and no fuzzy/prefix matching. `edges_by_relation` with an unknown or
misspelled relation name returns `[]`, not an error: a filter matching
nothing is a valid empty result, indistinguishable from a typo. If you get an
unexpected `[]`, check the spelling against the exact strings below before
assuming the relation doesn't occur in this graph.

Every edge also carries `provenance`: `"reference"` for the 16 relations in
§1, `"structural"` for the 8 in §2 (the two-ledger conservation invariant,
ADR 0016/0028/0031/0034).

## 1. Reference relations (16) — `provenance == "reference"`

| Constant | String value | When it applies |
|---|---|---|
| `CALLS` | `calls` | Host artifact invokes a rule, interface, decision, or process-model object (`resolved_via=="object_uuid"`, `object_type` one of those four). A bare-UUID process-model reference (e.g. `startProcess3(processModel: #"<uuid>")`) is a `calls` edge to the `processModel` artifact node. A record action's `<a:target xsi:type="a:ProcessModel">` (the action's launch target) is ALSO reachable via this same relation — sourced from the **static typed-reference channel** (ADR 0034/IV-191), re-sourced onto the owning `recordAction` node (the re-sourcing precedent `renders_via` established), so the edge is `recordAction --calls--> processModel`, never the owning record type. A site/portal page's `<uiObject>` element (the object the page renders — xsi:type local-name `ContentFreeformRule` or `ProcessModel`) is ALSO reachable here — same typed-reference channel (ADR 0034/IV-192), NO re-source (the edge stays sourced on the site/portal artifact — no per-page node exists yet); `ContentFreeformRule` resolves via the symbol table to `interface` or `rule`, both landing on `calls`. |
| `CALLS_BUILTIN` | `calls_builtin` | Host artifact calls an Appian built-in function (`resolved_via=="appian_name"`); target is an `appian_builtin` node. |
| `USES_CONSTANT` | `uses_constant` | Host artifact references a constant (`resolved_via=="object_uuid"`, `object_type=="constant"`). Reachable via either a SAIL `cons!` reference OR a processModel node input's static typed reference (`xsi:type` local-name `Constant`, ADR 0034/IV-190) — both land on this same relation; a host referencing the same constant both ways gets two separate occurrences on one edge, never a collision. |
| `USES_RECORD_TYPE` | `uses_record_type` | Host artifact references a record type directly, or via a relationship (edge retargeted to the relationship's target RT, not the relationship's own UUID). |
| `USES_RECORD_FIELD` | `uses_record_field` | Host artifact references a record field (`resolved_via` `table_uuid` or `cdt_name`); edge target is the leaf `recordField` node, never the owning record type. |
| `INVOKES_RECORD_ACTION` | `invokes_record_action` | Host artifact invokes a record action; target is the same bare-UUID `recordAction` node `defines_action` points at when the action is declared in-package. |
| `CALLS_INTEGRATION` | `calls_integration` | Host artifact calls an outbound integration (`object_type=="outboundIntegration"`). Reachable via either a SAIL reference OR a processModel Call-Integration node input's static typed reference (`xsi:type` local-name `OutboundIntegration`, ADR 0034/IV-190) — both land on this same relation; an integration called by both a rule and a PM node input gets an in-edge from each, counted separately. |
| `USES_TRANSLATION` | `uses_translation` | Host artifact references a translation string. |
| `USES_AI_SKILL` | `uses_ai_skill` | Host processModel artifact references an AI Skill via a node input (`object_type=="aiSkill"`). Sourced from the **static typed-reference channel** (ADR 0034), NOT a SAIL parse — a UUID in an `@a:id` attribute plus `xsi:type` naming the target type, resolved directly by UUID (`resolver.urns.resolve_typed_ref`). Same `resolved_via=="object_uuid"` discriminator as a SAIL-derived reference. Source is the owning processModel (interior `processNode` nodes don't exist yet); the occurrence's `sail_field` carries `pmNode:{node_uuid}:acp:{acpName}` for a future re-source onto the interior node (IV-157/159), the same convention `renders_via` uses. |
| `USES_DOCUMENT` | `uses_document` | Host artifact references a Document (`object_type=="document"`) — a processModel node input (ADR 0034, IV-190; same channel as `uses_ai_skill`) or a site/portal page's `<uiObject xsi:type="a:CollaborationDocument">` (ADR 0034, IV-192, no re-source — the relation's host is unconstrained, same as `uses_folder`). |
| `USES_FOLDER` | `uses_folder` | Host artifact references a Folder via a node input (`object_type=="folder"`). Same static typed-reference channel (ADR 0034, IV-190) — `xsi:type` local-name `CollaborationFolder`. Source is a processModel node input; REUSED by a later slice with an `outboundIntegration` source — the relation's source object_type is unconstrained. |
| `REFERENCES_PAGE` | `references_page` | Reference to a page within a site or portal (`resolved_via=="composite"`); edge target is the head object before `/`, page name is edge metadata. |
| `REFERENCES` | `references` | Generic fallback for a boundary reference (external/dangling/unknown target) whose lexical `ref_kind` is type-opaque or unrecognised — intent lives in the relation, outcome in the target node's `kind`. |
| `RENDERS_VIA` | `renders_via` | A record view's `uiExpr` reference to the interface that renders it; source is the `recordView` node (re-sourced from `calls`), not the owning record type. |
| `USES_DISPLAY_NAME` | `uses_display_name` | Host artifact references a record field's configured Display Name (`urn:appian:record-field-properties`); edge target is the `recordFieldDisplayName` node (`{fieldNodeId}/displayName`). Reference-only — the node/edge exist only when such a reference actually resolves. |
| `TRAVERSES_RELATIONSHIP` | `traverses_relationship` | Host artifact traversed a `recordRelationship` node en route to a multi-hop record-field or Display Name reference's leaf; one edge per traversed hop, in ADDITION to the leaf edge. Applies uniformly to `uses_record_field` and `uses_display_name` references. A 0-hop reference (the common case) emits none. |

## 2. Structural relations (8) — `provenance == "structural"`

| Constant | String value | When it applies |
|---|---|---|
| `USES_CONNECTED_SYSTEM` | `uses_connected_system` | `artifact.connected_system_uuid` is set (integrations / CS-backed record types). |
| `SECURED_BY` | `secured_by` | One occurrence per `{group_uuid, role}` group-kind entry in `artifact.security`; multiple roles for the same group aggregate onto one edge. |
| `DECLARES` | `declares` | Owning record type to its `recordRelationship` node, one per in-package relationship config. |
| `TARGETS` | `targets` | `recordRelationship` node to its target record type (in-package artifact node, or external boundary node for `SYSTEM_*`/out-of-package targets). |
| `HAS_FIELD` | `has_field` | Owning record type to a declared field node, for every field regardless of whether any SAIL references it. |
| `HAS_VIEW` | `has_view` | Owning record type to a declared view node (`<a:detailViewCfg>` with a non-empty `urlStub`). |
| `DEFINES_ACTION` | `defines_action` | Owning record type to a declared action node; same node `invokes_record_action` reuses when the action is also called from SAIL. |
| `HAS_DISPLAY_NAME` | `has_display_name` | Owning `recordField` node to its `recordFieldDisplayName` node; emitted only when the Display Name node exists (alongside the first `uses_display_name` reference to it) — unlike the other structural relations above, NOT declared-field-driven. |

## 3. Lookup entry points in the source

- `relation_for(resolved_via, object_type)` — maps a RESOLVED reference to its
  relation; `None` if unmapped (a conservation hole the builder raises on,
  never silently drops).
- `relation_for_ref_kind(ref_kind)` — maps a boundary reference's lexical
  `ref_kind` to its relation; always returns a string, defaulting to
  `REFERENCES`.
