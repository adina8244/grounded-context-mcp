from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from ..server import mcp
from ..core.fs import iter_text_files, read_file_safe
from ..core.scoring import score_match
from .env_specs import env_specs
from .git_insights import git_insights


Intent = Literal["implement", "debug", "validate"]


def _safe_in_repo(root: Path, candidate: Path) -> bool:
    """Prevent path traversal: candidate must be within root."""
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


@mcp.tool()
def recommend_context(
    query: str,
    intent: Intent = "implement",
    root: str = ".",
    max_results: int = 5,
    max_files_for_context: int = 3,
    max_chars: int = 6000,
) -> dict:
    """
    Recommend the most relevant files/snippets for a given coding task,
    then return grounded context for top files.

    intent:
      - implement: prefer stable patterns + file/path matches
      - debug: boost recently-changed areas (if git is available)
      - validate: prioritize env constraints and surface "unsupported" risks
    """
    root_path = Path(root).resolve()

    # 1) Always return env info (helps validate intent)
    env = env_specs()

    # 2) Try git insights (may fail gracefully if not a git repo)
    git_meta = git_insights(str(root_path))
    is_git_ok = bool(git_meta.get("ok", True)) and not str(git_meta.get("branch", "")).startswith("[git error]")

    # 3) Search across repo using current scoring
    hits = []
    for path, text in iter_text_files(root_path):
        s = score_match(query, path, text)

        # intent-specific scoring adjustments
        if s > 0:
            # debug: small boost to likely hot files (heuristic)
            if intent == "debug":
                # Boost files that look like auth/middleware/logging or tests around errors
                p = str(path).lower()
                if any(k in p for k in ("auth", "middleware", "error", "exception", "logging", "trace", "bug", "fix")):
                    s += 0.75
                # If git exists and repo is dirty, slight boost to everything (focus on active work)
                if is_git_ok and git_meta.get("dirty"):
                    s += 0.25

            # validate: boost config/deps files
            if intent == "validate":
                p = str(path).lower()
                if any(k in p for k in ("pyproject.toml", "requirements", "environment", "docker", "compose", "config")):
                    s += 0.75

            # implement: boost typical app structure files
            if intent == "implement":
                p = str(path).lower()
                if any(k in p for k in ("router", "api", "service", "handler", "controller", "endpoint")):
                    s += 0.5

            hits.append((s, path, text))

    hits.sort(key=lambda x: x[0], reverse=True)
    hits = hits[: max_results]

    recommended_files = []
    for s, p, t in hits:
        rel = str(p.relative_to(root_path))
        recommended_files.append(
            {
                "path": rel,
                "score": float(s),
                "snippet_preview": t[:400],
            }
        )

    # 4) Build grounded context for top N files
    items = []
    total = 0
    for rec in recommended_files[: max_files_for_context]:
        rel = rec["path"]
        abs_path = (root_path / rel).resolve()

        if not _safe_in_repo(root_path, abs_path):
            items.append({"path": rel, "ok": False, "error": "Path outside root"})
            continue

        content = read_file_safe(abs_path)
        if content is None:
            items.append({"path": rel, "ok": False, "error": "unreadable or missing"})
            continue

        remaining = max_chars - total
        if remaining <= 0:
            break

        chunk = content[:remaining]
        total += len(chunk)
        items.append({"path": rel, "ok": True, "content": chunk})

    # 5) Generate explanation + confidence (simple, deterministic-ish)
    why = []
    if intent == "debug":
        why.append("Debug intent: boosted likely hot paths and recent activity signals (when available).")
    elif intent == "validate":
        why.append("Validate intent: boosted config/dependency files to check support and constraints.")
    else:
        why.append("Implement intent: boosted common API/service/router patterns.")

    if recommended_files:
        why.append("Selected top matches based on query presence in path/content and lightweight heuristics.")
    else:
        why.append("No strong matches found; consider refining query keywords.")

    confidence = 0.25
    if recommended_files:
        top = recommended_files[0]["score"]
        # heuristic confidence scaling
        confidence = max(0.35, min(0.95, 0.35 + (top / 10.0)))

    # validate: if env says "local repo only" + query hints at network, warn (example)
    warnings = []
    if intent == "validate":
        scope = (env or {}).get("scope", "")
        if "local" in str(scope).lower() and any(k in query.lower() for k in ("github", "http", "api", "network")):
            warnings.append("Environment is local-only; network/GitHub API usage may be unsupported.")

    summary = (
        f"Recommended {len(recommended_files)} file(s) for intent='{intent}'. "
        f"Returning grounded context for top {len(items)} file(s)."
    )

    return {
        "summary": summary,
        "intent": intent,
        "query": query,
        "env": env,
        "git": git_meta,
        "warnings": warnings,
        "recommended_files": recommended_files,
        "recommended_context": {
            "root": str(root_path),
            "items": items,
            "max_chars": max_chars,
        },
        "why_selected": why,
        "confidence": round(float(confidence), 2),
        "sources": [{"type": "repo", "path": r["path"]} for r in recommended_files],
    }
