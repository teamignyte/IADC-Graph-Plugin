"""The plugin manifest: valid JSON, required fields, and the documented duplicate-registration trap.

`IADC-Marketplace`'s own README and `IADC-Advisor`'s CLAUDE.md both record the same bug: declaring
`skills` or `hooks` in plugin.json when they're already auto-discovered from the `skills/`/`hooks/`
directories makes the plugin "install successfully but load nothing" — silently. Nothing catches
that at install time (`claude plugin validate` passes on the broken manifest), which is exactly why
it belongs in this repo's own test suite instead.
"""

import json

from conftest import PLUGIN_JSON


def test_plugin_json_is_valid_json_with_required_fields(plugin_manifest):
    for field in ("name", "version", "description", "author"):
        assert field in plugin_manifest, f"plugin.json is missing required field {field!r}"
    assert isinstance(plugin_manifest["author"], dict) and plugin_manifest["author"].get("name")


def test_plugin_name_is_iadc_graph(plugin_manifest):
    """Invocation-address component 1/3: the plugin half of `iadc-graph:iadc-graph` / `iadc-graph:setup`."""
    assert plugin_manifest["name"] == "iadc-graph", (
        "the plugin name derives both invocation addresses (ADR 0010) — renaming it here "
        "breaks iadc-advisor's and iadc-tester's `iadc-graph:setup` calls"
    )


def test_plugin_json_does_not_declare_skills_or_hooks():
    raw = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    assert "skills" not in raw, "skills/ is auto-discovered — declaring it too breaks loading silently"
    assert "hooks" not in raw, "hooks/ is auto-discovered — declaring it too breaks loading silently"
