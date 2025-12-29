from __future__ import annotations

from pathlib import Path


def score_match(query: str, path: Path, text: str) -> float:
    q = query.strip().lower()
    if not q:
        return 0.0

    p = str(path).lower()
    hay = text.lower()

    score = 0.0
    if q in p:
        score += 3.0

    cnt = hay.count(q)
    if cnt:
        score += min(5.0, 0.5 * cnt)

    if "def " in hay or "class " in hay:
        score += 0.25

    return score
