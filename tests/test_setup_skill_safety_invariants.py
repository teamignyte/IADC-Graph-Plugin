"""Safety-critical steps in skills/setup/SKILL.md, checked as prose invariants.

skills/setup/ writes a graph API key into a client repo's .mcp.json — the family's most
security-bearing artifact, per IV-397. It has been hardened four separate times (IV-378, IV-382,
IV-385, IV-388) by prose review alone, because it lived in IADC-Marketplace, which has no test
suite. That is the entire reason this repo exists. These tests can't execute the skill (it's
instructions for Claude, not a program, and there's no live git-safety scenario to run it against
in CI) — but they can catch a future edit silently deleting one of its safety gates, by asserting
each gate's prose is still present. Each assertion names the exact fact it protects and the phrase
whose removal would turn it red.
"""

from conftest import setup_skill_text  # noqa: F401 (fixture import for clarity)


def test_setup_skill_never_prints_credential_to_transcript(setup_skill_text):
    """Turns red if the no-echo rule for secret values is ever deleted or reworded away."""
    assert "Never print a credential value back into the transcript" in setup_skill_text


def test_setup_skill_checks_git_ignore_status(setup_skill_text):
    """Turns red if the skill stops checking whether .mcp.json is actually ignored before writing."""
    assert "git check-ignore" in setup_skill_text


def test_setup_skill_untracks_a_committed_mcp_json_with_rm_cached(setup_skill_text):
    """Turns red if the tracked-file remediation (git rm --cached) is removed."""
    assert "git rm --cached .mcp.json" in setup_skill_text


def test_setup_skill_requires_explicit_consent_before_any_write(setup_skill_text):
    """Turns red if a git change or credential write is no longer gated on the user's explicit yes."""
    assert "explicit yes" in setup_skill_text


def test_setup_skill_verifies_head_not_just_working_tree(setup_skill_text):
    """Turns red if the durability check (HEAD, not just the index/working tree) is dropped —
    the exact gap step 4 calls out as "tempting to skip"."""
    assert "git cat-file -e HEAD:.mcp.json" in setup_skill_text
    assert "git cat-file -e HEAD:.gitignore" in setup_skill_text


def test_setup_skill_merges_rather_than_overwrites_mcp_json(setup_skill_text):
    """Turns red if the merge-only-the-iadc-block behavior regresses to a whole-file rewrite,
    which would clobber appian/context7 entries other skills own."""
    assert "merge" in setup_skill_text.lower()
    assert "Every other key" in setup_skill_text
