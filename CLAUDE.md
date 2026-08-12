# IADC-Graph-Plugin

This repo holds exactly one Claude Code plugin: **`iadc-graph`**. It queries an Appian
application's App Graph over the IADC graph MCP, and configures the connection to it. This file is
repo-local; family-wide facts (the umbrella, the other repos, the shared Jira board) live in the
umbrella's own `CLAUDE.md`, which still loads on the walk up the directory tree from here.

## What's here

Plugin-root layout — `.claude-plugin/plugin.json` sits at the repo root, matching `IADC-Tester`'s
shape rather than `IADC-Advisor`'s workshop/deliverable split, because this repo holds nothing but
the plugin: no separate dev environment, no second product to keep out of the shipped tree.

```
.claude-plugin/plugin.json   name "iadc-graph" — do not rename; see "Invocation addresses" below
skills/iadc-graph/           reads the graph: session lifecycle, node-id forms, relation vocabulary
skills/setup/                writes the `iadc` MCP entry into a client's .mcp.json
tests/                       see "Tests" below
```

## The mirror: `skills/iadc-graph/`

**Never hand-edit this directory.** Its canonical source lives upstream, alongside the graph
service itself. A fix belongs there; this copy is refreshed wholesale, not patched in place.

## `skills/setup/`

Writes the `iadc` graph credential (a URL and an API key) into a client repo's `.mcp.json`,
merging rather than overwriting, and only after the user has explicitly agreed and a set of git
checks confirm the file is actually protected from being committed. It never prints the credential
value back into the conversation.

## Invocation addresses — do not change

Callers reach this plugin's skills as **`iadc-graph:iadc-graph`** and **`iadc-graph:setup`**. Both
`iadc-advisor` and `iadc-tester` call `iadc-graph:setup` directly, so the address is a public
contract. It derives from three things, none of which may change without a coordinated update
across those callers:

1. `.claude-plugin/plugin.json`'s `name` field — must stay `"iadc-graph"`.
2. The `skills/iadc-graph/` directory name (and its `SKILL.md` frontmatter `name: "iadc-graph"`).
3. The `skills/setup/` directory name (and its `SKILL.md` frontmatter `name: setup`).

`tests/test_skill_addresses.py` and `tests/test_plugin_manifest.py` check all three per commit.

**Publish order.** A version of `iadc-advisor` or `iadc-tester` that chains into `iadc-graph:setup`
directly — rather than telling the user to type it — must not publish before this repo's own
model-invocable flip (IV-441 phase 1) does. Until that flip ships, `skills/setup/SKILL.md` carries
`disable-model-invocation: true`, which strips it from every other skill's reach — "only the human
typing its name can invoke it, and no other skill can" — so a chain instruction against it fails
outright. Neither caller pins a version on its `iadc-graph` dependency (`"dependencies":
["iadc-graph"]` in both `plugin.json`s), so nothing mechanical enforces the order; publish here
first.

## Tests

`skills/` holds prose (`SKILL.md` instructions for Claude, not executable code), so the suite
checks what a markdown-instruction skill can actually be checked for: the plugin manifest is valid
and unchanged in shape, the invocation-address components above haven't drifted, the mirror's file
set is the shape upstream ships, and `skills/setup/`'s required steps — the ignore-rule check, the
tracked-file handling, the explicit-consent gates before any write, and the no-echo rule for
credential values — are still present and still connected the way the prose describes.

```
python3 -m pytest
```

Runs on every push via GitHub Actions (`.github/workflows/ci.yml`).

## `.worktrees/`

Gitignored from this repo's first commit. Manual worktrees for concurrent work go under
`.worktrees/<name>` — plain `git worktree add .worktrees/<name> -b <branch>`.
