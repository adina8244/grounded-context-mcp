from __future__ import annotations
from pathlib import Path
from ..core.git import run_git
from ..server import mcp


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

    return {
        "root": str(root_path),
        "branch": branch.strip(),
        "last_commit": last_commit.strip(),
        "dirty": bool(status.strip()),
        "status_porcelain": status.splitlines()[:50],
    }
