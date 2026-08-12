"""Invocation-address components 2 and 3: the skill directory names and their SKILL.md frontmatter.

ADR 0010 fixed the addresses `iadc-graph:iadc-graph` and `iadc-graph:setup` deliberately — both
`iadc-advisor` and `iadc-tester` call `iadc-graph:setup` directly, so a rename here is a breaking
change for callers outside this repo, not a local refactor.
"""

from conftest import SKILLS_DIR, read_frontmatter


def test_iadc_graph_skill_directory_and_frontmatter_name():
    skill_md = SKILLS_DIR / "iadc-graph" / "SKILL.md"
    assert skill_md.is_file(), "skills/iadc-graph/SKILL.md must exist for iadc-graph:iadc-graph to resolve"
    fields = read_frontmatter(skill_md)
    assert fields.get("name") == "iadc-graph"


def test_setup_skill_directory_and_frontmatter_name():
    skill_md = SKILLS_DIR / "setup" / "SKILL.md"
    assert skill_md.is_file(), "skills/setup/SKILL.md must exist for iadc-graph:setup to resolve"
    fields = read_frontmatter(skill_md)
    assert fields.get("name") == "setup"


def test_setup_skill_is_model_invocable():
    """`setup` writes a credential, but the boundary that makes that safe was never invocation
    posture — it's the explicit-consent gates inside the skill (before the `.gitignore` change, before
    the credential write), which run the same regardless of who or what triggered the skill. Now that
    `iadc-advisor:setup` and `iadc-tester:setup` can chain here directly, the model must be able to
    invoke it — so
    `disable-model-invocation` must be absent from the frontmatter, not merely set to `"false"`, since
    either `"true"` or a stray `"false"` key would still read as present to a caller checking for it."""
    fields = read_frontmatter(SKILLS_DIR / "setup" / "SKILL.md")
    assert "disable-model-invocation" not in fields


def test_no_other_skill_directories_exist():
    """The plugin ships exactly two skills — an extra directory would be a silent third address."""
    names = sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir())
    assert names == ["iadc-graph", "setup"]
