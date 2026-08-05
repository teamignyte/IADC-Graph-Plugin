# IADC-Graph-Plugin

This repo holds exactly one Claude Code plugin: **`iadc-graph`**. It is the client-facing home for
the plugin that queries the App Graph — the graph substrate itself stays in `IADC-Core`
(family [ADR 0002](https://github.com/teamignyte/IADC/blob/main/docs/adr/0002-app-graph-stays-in-iadc-core.md)).
This file is repo-local; family-wide facts (the umbrella, the other repos, the shared Jira board)
live in the umbrella's own `CLAUDE.md`, which still loads on the walk up the directory tree from
here.

## What's here

Plugin-root layout — `.claude-plugin/plugin.json` sits at the repo root, matching `IADC-Tester`'s
shape rather than `IADC-Advisor`'s workshop/deliverable split, because this repo holds nothing but
the plugin: no separate dev environment, no second product to keep out of the shipped tree.

```
.claude-plugin/plugin.json   name "iadc-graph" — do not rename; see "Invocation addresses" below
skills/iadc-graph/           the mirror — a byte-identical copy of IADC-Core's canonical skill
skills/setup/                hand-written here — writes the `iadc` MCP entry into a client's .mcp.json
tests/                       structural + safety-invariant checks (see "Tests" below)
```

## The mirror: `skills/iadc-graph/`

**Never hand-edit this directory.** It is a wholesale copy of `IADC-Core`'s
`.claude/skills/iadc-graph/`, refreshed only by the procedure in `IADC-Core`'s
`docs/marketplace-mirror-refresh.md` (the file name predates this repo and still describes the
refresh; it now targets this repo instead of `IADC-Marketplace`). A fix belongs upstream in
`IADC-Core`, where a drift-guard test binds the skill to the graph server's real tool roster on
every commit — that guard is this repo's whole reason to trust the copy. The mirror may lag the
deployed graph server; it must never lead it (family
[ADR 0003](https://github.com/teamignyte/IADC/blob/main/docs/adr/0003-shared-skills-ship-as-pinned-marketplace-plugins.md)).

## `skills/setup/`: hand-written here, and the reason this repo exists

`skills/setup/SKILL.md` is the one place in the family that writes the `iadc` graph credential
into a client repo's `.mcp.json`. It used to live in `IADC-Marketplace`, which has no test suite,
no CI and no build — so every hardening of its credential-write logic landed by prose review alone.
This repo exists to give that skill a place that can check itself instead (family epic IV-397).

## Invocation addresses — do not change

Callers reach this plugin's skills as **`iadc-graph:iadc-graph`** and **`iadc-graph:setup`**,
fixed deliberately by family
[ADR 0010](https://github.com/teamignyte/IADC/blob/main/docs/adr/0010-graph-plugin-owns-graph-configuration.md).
Both `iadc-advisor` and `iadc-tester` call `iadc-graph:setup` directly, so the address is a public
contract. It derives from three things, none of which may change without a family-wide coordinated
update:

1. `.claude-plugin/plugin.json`'s `name` field — must stay `"iadc-graph"`.
2. The `skills/iadc-graph/` directory name (and its `SKILL.md` frontmatter `name: "iadc-graph"`).
3. The `skills/setup/` directory name (and its `SKILL.md` frontmatter `name: setup`).

`tests/test_skill_addresses.py` and `tests/test_plugin_manifest.py` check all three per commit.

## Tests

`skills/` holds prose (`SKILL.md` instructions for Claude, not executable code), so the suite
checks what a markdown-instruction skill can actually be checked for: the plugin manifest is valid
and unchanged in shape, the invocation-address components above haven't drifted, the mirror's file
set matches what `IADC-Core` ships, and the `setup` skill's safety-critical steps (the git-ignore
check, the tracked-file handling, the explicit-consent gates, "never print a credential back into
the transcript") are still present in prose — a regression net for a skill that has been hardened
four separate times (IV-378, IV-382, IV-385, IV-388) with no mechanism to catch a future one
slipping back out.

```
python3 -m pytest
```

## `.worktrees/`

Gitignored from this repo's first commit. Manual worktrees for concurrent work go under
`.worktrees/<name>`; see the umbrella's "Working across repos" and `IADC-Core`'s "Git worktrees"
note for the mechanics — plain `git worktree add .worktrees/<name> -b <branch>`.
