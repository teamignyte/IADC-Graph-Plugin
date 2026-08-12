"""Shared fixtures and helpers for the iadc-graph plugin test suite.

Everything under skills/ is prose written for Claude to read (SKILL.md files), not executable
code — so these tests check what a markdown-instruction skill can actually be checked for:
manifest shape, invocation-address stability, mirror file-set integrity, and the presence of
safety-critical steps in the setup skill's prose.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
SKILLS_DIR = REPO_ROOT / "skills"


def read_frontmatter(skill_md_path: Path) -> dict:
    """Extract the YAML-ish frontmatter block of a SKILL.md as a flat dict of top-level keys.

    Deliberately not a full YAML parser (no external dependency): every SKILL.md in this repo
    uses simple ``key: value`` frontmatter, optionally quoted, with no nested structures at the
    top level. This is enough to check the fields these tests care about (name, description, and
    whether disable-model-invocation is set at all) without pulling in PyYAML for one narrow use.
    """
    text = skill_md_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError(f"{skill_md_path} has no --- frontmatter block")
    fields = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith(" ") or line.startswith("\t"):
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        fields[key.strip()] = value
    return fields


@pytest.fixture(scope="session")
def plugin_manifest() -> dict:
    return json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def setup_skill_text() -> str:
    """Whitespace-collapsed so a prose sentence wrapped across a source line break (this file
    hand-wraps at ~100 chars) still matches a single-line search phrase."""
    raw = (SKILLS_DIR / "setup" / "SKILL.md").read_text(encoding="utf-8")
    return " ".join(raw.split())
