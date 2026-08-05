"""Regression checks for skills/setup/SKILL.md's credential-write safety gates.

skills/setup/ writes a graph API key into a client repo's .mcp.json, gated behind a chain of git
checks (is `.mcp.json` really ignored, is it tracked, is the ignore rule actually durable) before
anything is written. These tests can't execute the skill directly — it's instructions for Claude,
not a program — so they check the prose itself: that each required gate's literal command is still
present at its documented count, and that 13 of the file's 16 no-write halts are each still paired
with their own "write nothing" consequence in one literal span — the remaining three are named, not
anchored, below — rather than merely checking that some safety-flavored words appear somewhere in
the file. A test that only checks "the phrase exists" can't tell a real gate from a lone reference
to one, and can't tell "don't write" from its own negation.

Every count below was read directly off the current file and is asserted as an exact equality
(not merely "at least one"), so a single deleted or altered occurrence turns the test red — not
just wholesale removal.
"""

from conftest import setup_skill_text  # noqa: F401 (fixture import for clarity)

# Thirteen places across steps 1-4 where the flow stops without writing — either the user declined
# an offered git action, or the skill itself halted on a state it won't write through. Each entry
# pairs that branch's own decision with its own consequence in one literal span, so inverting a
# single branch's outcome (e.g. "write no credential" -> "write the credential anyway") breaks only
# that branch's anchor — a plain word or phrase count can be satisfied by a consequence that
# actually belongs to a *different* branch, which this avoids. Two of step 1's four branches
# (labelled S1c, S1d below) end in byte-identical consequence text; each anchor there also carries
# enough of its own preceding sentence to stay unique. Every phrase below is verified present
# exactly once in the current file.
_DECLINE_CONSEQUENCE_ANCHORS = [
    (
        "step 1, S1a — ambiguous existing entry, user chooses to leave it standing",
        'restarting? On "leave it," stop without writing anything.',
    ),
    (
        "step 1, S1b — untracked existing entry, check-ignore finds no rule at all",
        "added to `.gitignore` and committed. **Report this and stop — don't add the line yourself "
        "and don't ask whether to.**",
    ),
    (
        "step 1, S1c — untracked existing entry, ignore rule present but not durable",
        "Say the entry works, and that it needs a committed, non-negated `.gitignore` rule, "
        "actually compared against the working tree, before it's durable. **Report this and stop, "
        "same as above** — no commit, no asking.",
    ),
    (
        "step 1, S1d — untracked existing entry, HEAD still carries a committed blob",
        "the removal from the index is already staged — it only needs one more commit to become "
        "durable, the same commit step 4's own third gate also requires. **Report this and stop, "
        "same as above** — no commit, no asking.",
    ),
    (
        "step 2 — declines adding the .gitignore rule",
        "**On decline, add nothing, and don't ask again this run** — remember it: step 4 writes "
        "no credential value below.",
    ),
    (
        "step 2 — declines clearing a skip-worktree/assume-unchanged .gitignore",
        "- **Decline** — write no credential this run either, for the same not-yet-durable reason.",
    ),
    (
        "step 3 — tracked-and-committed .mcp.json, declines git rm --cached",
        "- **Decline** → this step ends here. Write **no** credential — leave any `<placeholder>` exactly",
    ),
    (
        "step 3 — tracked-and-committed .mcp.json, accepted rm --cached but declines bundling the "
        "removal commit with other staged work",
        "or decline bundling unrelated staged work** → write **no** credential this run.",
    ),
    (
        "step 3 — staged-only (never committed) .mcp.json, declines git rm --cached",
        "same as the decline branch above: no credential, placeholders left alone, name what's "
        "needed, stop.",
    ),
    (
        "step 3 — second decline on the missing-ignore-rule gate",
        "On a second decline: stop, write no credential, say what's still needed.",
    ),
    (
        "step 4, gate 1 — basic check-ignore fails",
        "Catches a step-2 decline on a repo where step 3 found no tracked file to react to (so "
        "nothing upstream already stopped this run). If it fails, write no credential and point "
        "back at the missing rule.",
    ),
    (
        "step 4, gate 2 — the four-part durability check fails and the offered fix is declined",
        "and if that's declined too, stop for this run.",
    ),
    (
        "step 4, gate 3 — HEAD still carries .mcp.json despite step 3",
        "straight through here, while HEAD still carries the file. If this gate fails, don't "
        "write — say so, show `git status`, and offer to commit the removal now",
    ),
]


def test_every_decline_branch_pairs_with_a_no_write_consequence(setup_skill_text):
    """Turns red if any of these 13 named branches stops saying nothing gets written within its
    anchored span — each anchor spans the decision and its consequence together, so inverting one
    breaks only its own anchor, not the others.

    This is not every stop/decline-shaped sentence in the file. Three are deliberately not anchored
    here: step 2's second "they'd rather commit the .gitignore line themselves" offer, whose
    consequence text is close enough to the step-2 branch already anchored above (both read
    "write no credential ... for the same not-yet-durable reason") that a third near-duplicate
    anchor would add little; step 4's separate malformed-.mcp.json triage stop, a gap this test does
    not close; and the halt for when this repo has no `.git` yet, right after step 2's durability
    check, which stops before any of the checks below it can even run. None of the three should be
    read as "covered" — check the branch directly against skills/setup/SKILL.md rather than assuming
    this list is exhaustive."""
    missing = [
        label for label, phrase in _DECLINE_CONSEQUENCE_ANCHORS if setup_skill_text.count(phrase) != 1
    ]
    assert not missing, f"decline branch(es) with no intact no-write consequence: {missing}"


def test_setup_skill_never_prints_credential_to_transcript(setup_skill_text):
    """Turns red if the no-echo rule for secret values is ever deleted or reworded away
    (single-occurrence anchor)."""
    assert setup_skill_text.count("Never print a credential value back into the transcript") == 1


def test_setup_skill_merges_rather_than_overwrites_mcp_json(setup_skill_text):
    """Turns red if the merge-only-the-iadc-block behavior regresses to a whole-file rewrite,
    which would clobber appian/context7 entries other skills own (single-occurrence anchor)."""
    assert setup_skill_text.count("Every other key") == 1


def test_credential_write_gate_block_heading_intact(setup_skill_text):
    """Turns red if step 4's "Three gates, all required" credential-write block is deleted
    wholesale — this is the single-occurrence heading that introduces it."""
    assert setup_skill_text.count("Three gates, all required") == 1


def test_durability_flag_check_hd_anchor_count_and_polarity(setup_skill_text):
    """Turns red if the durability check (only an `H` — plain cached — entry in `git ls-files -v`
    counts as durable, since `--skip-worktree`/`--assume-unchanged` hide the working tree from git
    entirely) is reversed: either by deleting one of its three documented occurrences (step 1's
    early explanation, step 2's own check, step 4's combined check), or by flipping the grep's
    polarity (`grep -q` -> `grep -qv`), which would keep the `'^H '` literal intact while inverting
    what it means.
    """
    assert setup_skill_text.count("'^H '") == 3
    assert "-qv" not in setup_skill_text, "grep -qv would invert the H-durability check's polarity"


def test_plain_check_ignore_required_alongside_v_output(setup_skill_text):
    """Turns red if the requirement that the bare, non-`-v`, check-ignore exit code must also pass
    — `-v` alone reports a source even for a rule a later line negates back out — is reversed by
    dropping the bare check and testing only `-v` output. The bare check is always joined to the
    `-v` check with `&&` in this file; that joining is exactly what a reversion would remove.
    """
    assert setup_skill_text.count("&& git check-ignore -v") == 3


def test_no_index_flag_present_on_both_halves_of_step2_check(setup_skill_text):
    """Turns red if `--no-index` is dropped from either half of step 2's initial ignore check —
    plain `check-ignore` reports "not ignored" for a path that's currently tracked even when a rule
    covering it exists, which is exactly the case step 2 runs this check *before* step 3 has
    untracked anything.
    """
    assert setup_skill_text.count("check-ignore --no-index -- .mcp.json") == 1
    assert setup_skill_text.count("check-ignore -v --no-index -- .mcp.json") == 1


def test_setup_skill_untracks_a_committed_mcp_json_with_rm_cached(setup_skill_text):
    """Turns red if either of the two `git rm --cached .mcp.json` remediation sites is removed —
    one for a `.mcp.json` HEAD actually committed, one for a staged-only, never-committed file;
    dropping either leaves that specific tracked-file shape with no way to reach step 4."""
    assert setup_skill_text.count("git rm --cached .mcp.json") == 2


def test_setup_skill_requires_explicit_consent_before_any_write(setup_skill_text):
    """Turns red if any of the seven "explicit yes" gates preceding a git change or credential
    write is dropped."""
    assert setup_skill_text.count("explicit yes") == 7


def test_setup_skill_verifies_head_not_just_working_tree(setup_skill_text):
    """Turns red if the durability check (HEAD, not just the index/working tree) is dropped at any
    of its documented sites — the exact gap step 4 calls out as "tempting to skip"."""
    assert setup_skill_text.count("cat-file -e HEAD:.mcp.json") == 6
    assert setup_skill_text.count("cat-file -e HEAD:.gitignore") == 3
