"""skills/iadc-graph/ is a wholesale mirror of IADC-Core's canonical skill and carries zero local
patches (IADC-Core's docs/marketplace-mirror-refresh.md). This repo can't reach across to
IADC-Core to diff content in CI, but it can guard the mirror's own file-set shape: an unexpected
extra or missing file here is exactly what would make the upstream `diff -r` byte-identity check
fail at the next refresh.
"""

from conftest import SKILLS_DIR

EXPECTED_REFERENCE_FILES = {
    "identifiers-and-discovery.md",
    "node-kinds.md",
    "relation-vocabulary.md",
    "return-shapes-and-errors.md",
    "session-lifecycle.md",
    "traversal-recipes.md",
}


def test_mirror_reference_files_present():
    references_dir = SKILLS_DIR / "iadc-graph" / "references"
    assert references_dir.is_dir()
    actual = {p.name for p in references_dir.iterdir() if p.is_file()}
    assert actual == EXPECTED_REFERENCE_FILES


def test_mirror_has_no_extra_top_level_files():
    """Only SKILL.md and references/ belong directly under skills/iadc-graph/ — a stray file here
    would silently ship as part of "the mirror" without ever having come from IADC-Core.
    """
    top_level = {p.name for p in (SKILLS_DIR / "iadc-graph").iterdir()}
    assert top_level == {"SKILL.md", "references"}
