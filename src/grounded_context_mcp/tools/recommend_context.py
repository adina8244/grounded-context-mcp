from __future__ import annotations

from pathlib import Path
from typing import Literal

from ..core.fs import iter_text_files, read_file_safe
from ..core.scoring import score_match
from ..server import mcp
from .env_specs import env_specs
from .git_insights import git_insights

Intent = Literal["implement", "debug", "validate"]

_SKIP_SUBSTRINGS = (
    "\\.egg-info\\",
    "\\__pycache__\\",
    "\\.venv\\",
    "\\.git\\",
    "\\dist\\",
    "\\build\\",
)


def _norm_path(p: Path) -> str:
    """Normalize paths for cross-platform substring checks."""
    return str(p).replace("/", "\\").lower()


def _should_skip(path: Path) -> bool:
    """Skip noisy/unhelpful directories and build artifacts."""
    p = _norm_path(path)
    return any(x in p for x in _SKIP_SUBSTRINGS)


def _safe_in_repo(root: Path, candidate: Path) -> bool:
    """Prevent path traversal: candidate must be within root."""
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def _apply_intent_boosts(
    base_score: float,
    path: Path,
    intent: Intent,
    *,
    is_git_ok: bool,
    git_meta: dict,
) -> float:
    """
    Apply intent-specific score adjustments (deterministic heuristics).
    Only applied if base_score > 0 (keeps noise down).
    """
    if base_score <= 0:
        return base_score

    p = _norm_path(path)

    if intent == "debug":
        if any(k in p for k in ("auth", "middleware", "error", "exception", "logging", "trace", "bug", "fix")):
            base_score += 0.75
        if is_git_ok and git_meta.get("dirty"):
            base_score += 0.25

    elif intent == "validate":
        if any(k in p for k in ("pyproject.toml", "requirements", "environment", "docker", "compose", "config")):
            base_score += 0.75

    else:  # implement
        if any(k in p for k in ("router", "api", "service", "handler", "controller", "endpoint")):
            base_score += 0.5

    return base_score


def _compute_confidence(recommended_files: list[dict]) -> float:
    if not recommended_files:
        return 0.25
    top = float(recommended_files[0].get("score", 0.0))
    return max(0.35, min(0.95, 0.35 + (top / 10.0)))


def _build_why(intent: Intent, has_results: bool) -> list[str]:
    why: list[str] = []
    if intent == "debug":
        why.append("Debug intent: boosted likely hot paths and recent activity signals (when available).")
    elif intent == "validate":
        why.append("Validate intent: boosted config/dependency files to check support and constraints.")
    else:
        why.append("Implement intent: boosted common API/service/router patterns.")

    if has_results:
        why.append("Selected top matches based on query presence in path/content and deterministic heuristics.")
    else:
        why.append("No strong matches found; consider refining query keywords.")
    return why


def _build_warnings(intent: Intent, env: dict | None, query: str) -> list[str]:
    warnings: list[str] = []
    if intent != "validate":
        return warnings

    scope = (env or {}).get("scope", "")
    if "local" in str(scope).lower() and any(k in query.lower() for k in ("github", "http", "api", "network")):
        warnings.append("Environment is local-only; network/GitHub API usage may be unsupported.")
    return warnings


def _tokenize_query(query: str) -> list[str]:
    """Tokenize query into whitespace-separated tokens (deterministic)."""
    return [t for t in query.replace("\n", " ").split() if t]


@mcp.tool()
async def recommend_context(
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
      - debug: boost likely hot paths (and recent activity signals if git is available)
      - validate: prioritize env constraints and surface "unsupported" risks
    """
    root_path = Path(root).resolve()

    # 1) Environment info
    env = env_specs()

    # 2) Git signal (optional; never blocks)
    try:
        git_meta = git_insights(str(root_path))
        if isinstance(git_meta, dict):
            git_meta.setdefault("ok", True)
    except Exception as e:
        git_meta = {"ok": False, "error": f"Failed to get git insights: {e}"}

    is_git_ok = bool(git_meta.get("ok"))

    # 3) PASS 1: score all files
    all_files: list[tuple[Path, str, float]] = []
    tokens = _tokenize_query(query)

    for path, text in iter_text_files(root_path):
        if _should_skip(path):
            continue

        s = sum(score_match(t, path, text) for t in tokens) if tokens else 0.0
        all_files.append((path, text, s))

    # 4) PASS 2: apply intent heuristics deterministically (no linkage boosts)
    hits: list[tuple[float, Path, str]] = []
    for path, text, s in all_files:
        s = _apply_intent_boosts(s, path, intent, is_git_ok=is_git_ok, git_meta=git_meta)
        if s > 0:
            hits.append((s, path, text))

    hits.sort(key=lambda x: x[0], reverse=True)
    hits = hits[:max_results]

    # 5) Build recommended_files (previews)
    recommended_files: list[dict] = []
    for s, p, t in hits:
        rel = str(p.relative_to(root_path))
        recommended_files.append(
            {
                "path": rel,
                "score": float(s),
                "snippet_preview": t[:400],
            }
        )

    # 6) Grounded context for top N files
    items: list[dict] = []
    total = 0

    for rec in recommended_files[:max_files_for_context]:
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

    # 7) Explainability
    why_selected = _build_why(intent, bool(recommended_files))
    warnings = _build_warnings(intent, env, query)
    confidence = round(float(_compute_confidence(recommended_files)), 2)

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
        "why_selected": why_selected,
        "confidence": confidence,
        "sources": [{"type": "repo", "path": r["path"]} for r in recommended_files],
    }
