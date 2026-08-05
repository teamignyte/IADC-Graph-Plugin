# IADC-Graph-Plugin

The **`iadc-graph`** Claude Code plugin — query an Appian application's App Graph over the IADC
graph MCP, and configure the connection to it. Part of the
[IADC](https://github.com/teamignyte/IADC) family; the graph substrate it queries stays in
[IADC-Core](https://github.com/teamignyte/IADC-Core).

You don't install this plugin directly — `iadc-advisor` and `iadc-tester` both declare it as a
dependency, so it arrives automatically with either.

## What's in it

| | |
|---|---|
| `skills/iadc-graph/` | The skill that reads the graph: session lifecycle, node-id forms, the relation vocabulary, return shapes. A byte-identical mirror of `IADC-Core`'s canonical copy. |
| `skills/setup/` | Writes the `iadc` MCP entry (graph URL + API key) into a client repo's `.mcp.json`, with the git-safety sequence a credential write needs. |

Invoked as `iadc-graph:iadc-graph` and `iadc-graph:setup` — see `CLAUDE.md` for why those addresses
are fixed and must not change.

## Tests

```
python3 -m pytest
```

Runs on every push via GitHub Actions (`.github/workflows/ci.yml`).
