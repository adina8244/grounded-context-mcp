from __future__ import annotations

from pathlib import Path

from ..server import mcp
from ..core.git import run_git


@mcp.tool()
def git_insights(root: str = ".") -> dict:
    """
    Lightweight git metadata for the repo (branch, last commit, status).
    """
    root_path = Path(root).resolve()

    branch = run_git(root_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    last_commit = run_git(root_path, ["log", "-1", "--pretty=format:%h %s (%an)"])
    status = run_git(root_path, ["status", "--porcelain"])

    return {
        "root": str(root_path),
        "branch": branch.strip(),
        "last_commit": last_commit.strip(),
        "dirty": bool(status.strip()),
        "status_porcelain": status.splitlines()[:50],
    }
