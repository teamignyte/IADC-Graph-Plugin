"""Repo-hygiene invariants: .worktrees/ must be gitignored, so a manual worktree plus a broad
`git add -A` never commits a nested checkout by accident.
"""

import subprocess

from conftest import REPO_ROOT

_PROBE_PATH = ".worktrees/some-worktree/HEAD"


def test_worktrees_directory_is_gitignored():
    """Checks the actual property — would git ignore a path under .worktrees/, and does that
    coverage trace to the tracked .gitignore — rather than a substring search on .gitignore's text
    or a bare `check-ignore` exit code.

    A substring check passes just as well on `# .worktrees/` (commented out) or `!.worktrees/`
    (negated back in) as on a real rule; `git check-ignore -q`'s exit code does not. But exit code
    alone has its own blind spot, the same one skills/setup/SKILL.md documents for `.mcp.json`:
    `.git/info/exclude` and `core.excludesFile` can make a path report as ignored exactly the way a
    `.gitignore` rule does, and neither one travels with a clone or a coworker — so a `.gitignore`
    rule could be deleted entirely and this check would still pass on a machine with a leftover
    local exclude. `check-ignore -v`'s reported source is what tells the two apart.
    """
    plain = subprocess.run(
        ["git", "check-ignore", "-q", "--", _PROBE_PATH],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    assert plain.returncode in (0, 1), (
        f"git check-ignore -q exited {plain.returncode} (a fatal/usage error, not the ignored/"
        f"not-ignored 0/1 this check expects) for {_PROBE_PATH!r}: "
        f"{plain.stderr.decode(errors='replace').strip()}"
    )
    assert plain.returncode == 0, f"git does not ignore paths under .worktrees/ ({_PROBE_PATH!r})"

    verbose = subprocess.run(
        ["git", "check-ignore", "-v", "--", _PROBE_PATH],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert verbose.stdout.startswith(".gitignore:"), (
        f"{_PROBE_PATH!r} is ignored, but not by the tracked .gitignore — git check-ignore -v "
        f"reports {verbose.stdout.strip()!r}, which traces to .git/info/exclude or "
        "core.excludesFile instead; neither travels with a clone or a coworker"
    )
