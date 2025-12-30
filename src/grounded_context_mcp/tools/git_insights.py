from __future__ import annotations

from pathlib import Path

from ..core.git import run_git
from .. import mcp


def _parse_status_files(status_lines: list[str]) -> list[str]:
    """
    Parse 'git status --porcelain' output lines into a stable list of file paths.
    Keeps original order and removes duplicates.
    """
    files: list[str] = []
    for line in status_lines:
        line = line.rstrip("\n")
        if not line:
            continue

        # Porcelain format is: "XY path"
        # (We intentionally keep this simple/deterministic.)
        if len(line) >= 4:
            files.append(line[3:].strip())

    seen: set[str] = set()
    out: list[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


@mcp.tool()
def git_insights(root: str = ".") -> dict:
    """
    Lightweight git metadata for the repository.
    """
    root_path = Path(root).resolve()

    branch = run_git(root_path, ["rev-parse", "--abbrev-ref", "HEAD"], timeout_s=2.0)
    last_commit = run_git(
        root_path,
        ["log", "-1", "--pretty=format:%h %s (%an)"],
        timeout_s=2.0,
    )
    status = run_git(root_path, ["status", "--porcelain"], timeout_s=2.0)

    # Files changed in HEAD (useful "diff signal" for debugging context)
    last_commit_files = run_git(
        root_path,
        ["show", "--name-only", "--pretty=format:", "HEAD"],
        timeout_s=2.0,
    )

    status_lines = status.splitlines()
    last_commit_files_lines = [ln.strip() for ln in last_commit_files.splitlines() if ln.strip()]

    return {
        "ok": True,
        "root": str(root_path),
        "branch": branch.strip(),
        "last_commit": last_commit.strip(),
        "dirty": bool(status.strip()),
        # Keep the original raw status preview (stable + bounded)
        "status_porcelain": status_lines[:50],
        # New: clean lists for "Context Diff Mode"
        "worktree_changed_files": _parse_status_files(status_lines[:200]),
        "last_commit_files": last_commit_files_lines[:200],
    }
