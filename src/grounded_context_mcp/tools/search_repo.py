from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .. import mcp
from ..core.fs import iter_text_files
from ..core.scoring import score_match


@mcp.tool()
def search_repo(
    query: str,
    root: str = ".",
    max_results: int = 10,
    file_globs: Optional[List[str]] = None,
) -> dict:
    """
    Search the local repository and return grounded snippets (no network).
    """
    root_path = Path(root).resolve()
    hits = []

    for path, text in iter_text_files(root_path, file_globs=file_globs):
        s = score_match(query, path, text)
        if s > 0:
            hits.append((s, path, text))

    hits.sort(key=lambda x: x[0], reverse=True)
    hits = hits[:max_results]

    results = [
        {
            "path": str(p.relative_to(root_path)),
            "score": float(s),
            "snippet": t[:800],
        }
        for s, p, t in hits
    ]
    return {"query": query, "results": results}
