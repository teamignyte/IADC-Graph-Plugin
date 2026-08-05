"""Repo-hygiene invariants called out explicitly in this repo's own brief: .worktrees/ must be
gitignored from the first commit. IADC (the umbrella), IADC-Advisor and IADC-Tester all still
lack this line — a worktree plus `git add -A` in one of them commits a nested checkout. Guard
against repeating that here.
"""

from conftest import REPO_ROOT


def test_worktrees_directory_is_gitignored():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".worktrees/" in gitignore
