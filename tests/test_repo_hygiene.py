"""Repo-hygiene invariants: .worktrees/ must be gitignored, so a manual worktree plus a broad
`git add -A` never commits a nested checkout by accident.
"""

import subprocess

from conftest import REPO_ROOT


def test_worktrees_directory_is_gitignored():
    """Checks the actual property — would git ignore a path under .worktrees/ — via
    `git check-ignore`, rather than a substring search on .gitignore's text. A substring check
    passes just as well on `# .worktrees/` (commented out) or `!.worktrees/` (negated back in) as
    on a real rule; `git check-ignore`'s exit code does not.
    """
    result = subprocess.run(
        ["git", "check-ignore", "-q", ".worktrees/some-worktree/HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    assert result.returncode == 0, (
        "git does not ignore paths under .worktrees/ — check .gitignore for a missing, "
        "commented-out, or negated rule"
    )
