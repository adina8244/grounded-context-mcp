from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


def run_git(root: Path, args: List[str]) -> str:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=str(root),
            stderr=subprocess.STDOUT,
            text=True,
        )
        return out
    except Exception as e:
        return f"[git error] {type(e).__name__}: {e}"
