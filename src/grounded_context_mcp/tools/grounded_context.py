from __future__ import annotations

from pathlib import Path
from typing import List

from .. import mcp
from ..core.fs import read_file_safe


@mcp.tool()
def get_grounded_context(paths: List[str], root: str = ".", max_chars: int = 6000) -> dict:
    """
    Return grounded file content for a set of paths (safe, truncated).
    """
    root_path = Path(root).resolve()
    out = []

    total = 0
    for p in paths:
        abs_path = (root_path / p).resolve()
        content = read_file_safe(abs_path)
        if content is None:
            out.append({"path": p, "ok": False, "error": "unreadable or missing"})
            continue

        remaining = max_chars - total
        if remaining <= 0:
            break

        chunk = content[:remaining]
        total += len(chunk)

        out.append({"path": p, "ok": True, "content": chunk})

    return {"root": str(root_path), "items": out, "max_chars": max_chars}
